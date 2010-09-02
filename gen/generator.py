# ------------------------------------------------------------------------------
import os, os.path, sys, parser, symbol, token, types
from appy.gen import Type, State, Config, Tool, Flavour, User
from appy.gen.descriptors import *
from appy.gen.utils import produceNiceMessage
import appy.pod, appy.pod.renderer
from appy.shared.utils import FolderDeleter

# ------------------------------------------------------------------------------
class GeneratorError(Exception): pass

# I need the following classes to parse Python classes and find in which
# order the attributes are defined. --------------------------------------------
class AstMatcher:
    '''Allows to find a given pattern within an ast (part).'''
    def _match(pattern, node):
        res = None
        if pattern[0] == node[0]:
            # This level matches
            if len(pattern) == 1:
                return node
            else:
                if type(node[1]) == tuple:
                    return AstMatcher._match(pattern[1:], node[1])
        return res
    _match = staticmethod(_match)
    def match(pattern, node):
        res = []
        for subNode in node[1:]:
            # Do I find the pattern among the subnodes ?
            occurrence = AstMatcher._match(pattern, subNode)
            if occurrence:
                res.append(occurrence)
        return res
    match = staticmethod(match)

# ------------------------------------------------------------------------------
class AstClass:
    '''Python class.'''
    def __init__(self, node):
        # Link to the Python ast node
        self.node = node
        self.name = node[2][1]
        self.attributes = [] # We are only interested in parsing static
        # attributes to now their order
        if sys.version_info[:2] >= (2,5):
            self.statementPattern = (
              symbol.stmt, symbol.simple_stmt, symbol.small_stmt,
              symbol.expr_stmt, symbol.testlist, symbol.test, symbol.or_test, 
              symbol.and_test, symbol.not_test, symbol.comparison, symbol.expr,
              symbol.xor_expr, symbol.and_expr, symbol.shift_expr, 
              symbol.arith_expr, symbol.term, symbol.factor, symbol.power)
        else:
            self.statementPattern = (
              symbol.stmt, symbol.simple_stmt, symbol.small_stmt,
              symbol.expr_stmt, symbol.testlist, symbol.test, symbol.and_test,
              symbol.not_test, symbol.comparison, symbol.expr, symbol.xor_expr,
              symbol.and_expr, symbol.shift_expr, symbol.arith_expr,
              symbol.term, symbol.factor, symbol.power)
        for subNode in node[1:]:
            if subNode[0] == symbol.suite:
                # We are in the class body
                self.getStaticAttributes(subNode)

    def getStaticAttributes(self, classBody):
        statements = AstMatcher.match(self.statementPattern, classBody)
        for statement in statements:
            if len(statement) == 2 and statement[1][0] == symbol.atom and \
               statement[1][1][0] == token.NAME:
                attrName = statement[1][1][1]
                self.attributes.append(attrName)

    def __repr__(self):
        return '<class %s has attrs %s>' % (self.name, str(self.attributes))

# ------------------------------------------------------------------------------
class Ast:
    '''Python AST.'''
    classPattern = (symbol.stmt, symbol.compound_stmt, symbol.classdef)
    def __init__(self, pyFile):
        f = file(pyFile)
        fContent = f.read()
        f.close()
        fContent = fContent.replace('\r', '')
        ast = parser.suite(fContent).totuple()
        # Get all the classes defined within this module.
        self.classes = {}
        classNodes = AstMatcher.match(self.classPattern, ast)
        for node in classNodes:
            astClass = AstClass(node)
            self.classes[astClass.name] = astClass

# ------------------------------------------------------------------------------
WARN_NO_TEMPLATE = 'Warning: the code generator should have a folder "%s" ' \
                   'containing all code templates.'
CODE_HEADER = '''# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
'''
class Generator:
    '''Abstract base class for building a generator.'''
    def __init__(self, application, outputFolder, options):
        self.application = application
        # Determine application name
        self.applicationName = os.path.basename(application)
        if application.endswith('.py'):
            self.applicationName = self.applicationName[:-3]
        # Determine output folder (where to store the generated product)
        self.outputFolder = '%s/%s' % (outputFolder, self.applicationName)
        self.options = options
        # Determine templates folder
        exec 'import %s as genModule' % self.__class__.__module__
        self.templatesFolder = os.path.join(os.path.dirname(genModule.__file__),
                                            'templates')
        if not os.path.exists(self.templatesFolder):
            print WARN_NO_TEMPLATE % self.templatesFolder
        # Default descriptor classes
        self.descriptorClasses = {
            'class': ClassDescriptor, 'tool': ClassDescriptor,
            'flavour': ClassDescriptor, 'user': ClassDescriptor,
            'workflow': WorkflowDescriptor}
        # The following dict contains a series of replacements that need to be
        # applied to file templates to generate files.
        self.repls = {'applicationName': self.applicationName,
                      'applicationPath': os.path.dirname(self.application),
                      'codeHeader': CODE_HEADER}
        # List of Appy classes and workflows found in the application
        self.classes = []
        self.tool = None
        self.flavour = None
        self.user = None
        self.workflows = []
        self.initialize()
        self.config = Config.getDefault()
        self.modulesWithTests = set()
        self.totalNumberOfTests = 0

    def determineAppyType(self, klass):
        '''Is p_klass an Appy class ? An Appy workflow? None of this ?
           If it (or a parent) declares at least one appy type definition,
           it will be considered an Appy class. If it (or a parent) declares at
           least one state definition, it will be considered an Appy
           workflow.'''
        res = 'none'
        for attrValue in klass.__dict__.itervalues():
            if isinstance(attrValue, Type):
                res = 'class'
            elif isinstance(attrValue, State):
                res = 'workflow'
        if not res:
            for baseClass in klass.__bases__:
                baseClassType = self.determineAppyType(baseClass)
                if baseClassType != 'none':
                    res = baseClassType
                    break
        return res

    def containsTests(self, moduleOrClass):
        '''Returns True if p_moduleOrClass contains doctests. This method also
           counts tests and updates self.totalNumberOfTests.'''
        res = False
        docString = moduleOrClass.__doc__
        if docString and (docString.find('>>>') != -1):
            self.totalNumberOfTests += 1
            res = True
        # Count also docstring in methods
        if type(moduleOrClass) == types.ClassType:
            for name, elem in moduleOrClass.__dict__.iteritems():
                if type(elem) in (staticmethod, classmethod):
                    elem = elem.__get__(name)
                if hasattr(elem, '__doc__') and elem.__doc__ and \
                   (elem.__doc__.find('>>>') != -1):
                    res = True
                    self.totalNumberOfTests += 1
        return res

    IMPORT_ERROR = 'Warning: error while importing module %s (%s)'
    SYNTAX_ERROR = 'Warning: error while parsing module %s (%s)'
    def walkModule(self, moduleName):
        '''Visits a given (sub-*)module into the application.'''
        try:
            exec 'import %s' % moduleName
            exec 'moduleObj = %s' % moduleName
            moduleFile = moduleObj.__file__
            if moduleFile.endswith('.pyc'):
                moduleFile = moduleFile[:-1]
            astClasses = Ast(moduleFile).classes
        except ImportError, ie:
            # True import error or, simply, this is a simple folder within
            # the application, not a sub-module.
            print self.IMPORT_ERROR % (moduleName, str(ie))
            return
        except SyntaxError, se:
            print self.SYNTAX_ERROR % (moduleName, str(se))
            return
        if self.containsTests(moduleObj):
            self.modulesWithTests.add(moduleObj.__name__)
        classType = type(Generator)
        # Find all classes in this module
        for moduleElemName in moduleObj.__dict__.keys():
            exec 'moduleElem = moduleObj.%s' % moduleElemName
            if (type(moduleElem) == classType) and \
               (moduleElem.__module__ == moduleObj.__name__):
                # We have found a Python class definition in this module.
                appyType = self.determineAppyType(moduleElem)
                if appyType != 'none':
                    # Produce a list of static class attributes (in the order
                    # of their definition).
                    attrs = astClasses[moduleElem.__name__].attributes
                    if appyType == 'class':
                        # Determine the class type (standard, tool, flavour...)
                        if issubclass(moduleElem, Tool):
                            if not self.tool:
                                klass = self.descriptorClasses['tool']
                                self.tool = klass(moduleElem, attrs, self)
                            else:
                                self.tool.update(moduleElem, attrs)
                        elif issubclass(moduleElem, Flavour):
                            if not self.flavour:
                                klass = self.descriptorClasses['flavour']
                                self.flavour = klass(moduleElem, attrs, self)
                            else:
                                self.flavour.update(moduleElem, attrs)
                        elif issubclass(moduleElem, User):
                            if not self.user:
                                klass = self.descriptorClasses['user']
                                self.user = klass(moduleElem, attrs, self)
                            else:
                                self.user.update(moduleElem, attrs)
                        else:
                            descriptorClass = self.descriptorClasses['class']
                            descriptor = descriptorClass(moduleElem,attrs, self)
                            self.classes.append(descriptor)
                        # Manage classes containing tests
                        if self.containsTests(moduleElem):
                            self.modulesWithTests.add(moduleObj.__name__)
                    elif appyType == 'workflow':
                        descriptorClass = self.descriptorClasses['workflow']
                        descriptor = descriptorClass(moduleElem, attrs, self)
                        self.workflows.append(descriptor)
                        if self.containsTests(moduleElem):
                            self.modulesWithTests.add(moduleObj.__name__)
            elif isinstance(moduleElem, Config):
                self.config = moduleElem

        # Walk potential sub-modules
        if moduleFile.find('__init__.py') != -1:
            # Potentially, sub-modules exist
            moduleFolder = os.path.dirname(moduleFile)
            for elem in os.listdir(moduleFolder):
                if elem.startswith('.'): continue
                subModuleName, ext = os.path.splitext(elem)
                if ((ext == '.py') and (subModuleName != '__init__')) or \
                   os.path.isdir(os.path.join(moduleFolder, subModuleName)):
                    # Submodules may be sub-folders or Python files
                    subModuleName = '%s.%s' % (moduleName, subModuleName)
                    self.walkModule(subModuleName)

    def walkApplication(self):
        '''This method walks into the application and creates the corresponding
           meta-classes in self.classes, self.workflows, etc.'''
        # Where is the application located ?
        containingFolder = os.path.dirname(self.application)
        sys.path.append(containingFolder)
        # What is the name of the application ?
        appName = os.path.basename(self.application)
        if os.path.isfile(self.application):
            appName = os.path.splitext(appName)[0]
        self.walkModule(appName)
        sys.path.pop()

    def generateClass(self, classDescr):
        '''This method is called whenever a Python class declaring Appy type
           definition(s) is encountered within the application.'''

    def generateWorkflow(self, workflowDescr):
        '''This method is called whenever a Python class declaring states and
           transitions is encountered within the application.'''

    def initialize(self):
        '''Called before the old product is removed (if any), in __init__.'''

    def finalize(self):
        '''Called at the end of the generation process.'''

    def copyFile(self, fileName, replacements, destName=None, destFolder=None,
                 isPod=False):
        '''This method will copy p_fileName from self.templatesFolder to
           self.outputFolder (or in a subFolder if p_destFolder is given)
           after having replaced all p_replacements. If p_isPod is True,
           p_fileName is a POD template and the copied file is the result of
           applying p_fileName with context p_replacements.'''
        # Get the path of the template file to copy
        templatePath = os.path.join(self.templatesFolder, fileName)
        # Get (or create if needed) the path of the result file
        destFile = fileName
        if destName: destFile = destName
        if destFolder: destFile = '%s/%s' % (destFolder, destFile)
        absDestFolder = self.outputFolder
        if destFolder:
            absDestFolder = os.path.join(self.outputFolder, destFolder)
        if not os.path.exists(absDestFolder):
            os.makedirs(absDestFolder)
        resultPath = os.path.join(self.outputFolder, destFile)
        if os.path.exists(resultPath): os.remove(resultPath)
        if not isPod:
            # Copy the template file to result file after having performed some
            # replacements
            f = file(templatePath)
            fileContent = f.read()
            f.close()
            if not fileName.endswith('.png'):
                for rKey, rValue in replacements.iteritems():
                    fileContent = fileContent.replace(
                        '<!%s!>' % rKey, str(rValue))
            f = file(resultPath, 'w')
            f.write(fileContent)
            f.close()
        else:
            # Call the POD renderer to produce the result
            rendererParams = {'template': templatePath,
                              'context': replacements,
                              'result': resultPath}
            renderer = appy.pod.renderer.Renderer(**rendererParams)
            renderer.run()

    def run(self):
        self.walkApplication()
        for descriptor in self.classes: self.generateClass(descriptor)
        for descriptor in self.workflows: self.generateWorkflow(descriptor)
        self.finalize()
        msg = ''
        if self.totalNumberOfTests:
            msg = ' (number of tests found: %d)' % self.totalNumberOfTests
        print 'Done%s.' % msg
# ------------------------------------------------------------------------------
