# ------------------------------------------------------------------------------
import os, os.path, re, sys, parser, symbol, token, types
import appy.pod, appy.pod.renderer
from appy.shared.utils import FolderDeleter
import appy.gen as gen
import po
from descriptors import *
from utils import getClassName
from model import ModelClass, User, Group, Tool, Translation, Page

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
    utf8prologue = '# -*- coding: utf-8 -*-'
    def __init__(self, pyFile):
        f = file(pyFile)
        fContent = f.read()
        f.close()
        # For some unknown reason, when an UTF-8 encoding is declared, parsing
        # does not work.
        if fContent.startswith(self.utf8prologue):
            fContent = fContent[len(self.utf8prologue):]
        fContent = fContent.replace('\r', '')
        ast = parser.suite(fContent).totuple()
        # Get all the classes defined within this module.
        self.classes = {}
        classNodes = AstMatcher.match(self.classPattern, ast)
        for node in classNodes:
            astClass = AstClass(node)
            self.classes[astClass.name] = astClass

# ------------------------------------------------------------------------------
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
    def __init__(self, application, options):
        self.application = application
        # Determine application name
        self.applicationName = os.path.basename(application)
        # Determine output folder (where to store the generated product)
        self.outputFolder = os.path.join(application, 'zope',
                                         self.applicationName)
        self.options = options
        # Determine templates folder
        genFolder = os.path.dirname(__file__)
        self.templatesFolder = os.path.join(genFolder, 'templates')
        # Default descriptor classes
        self.descriptorClasses = {
            'class': ClassDescriptor, 'tool': ClassDescriptor,
            'user': ClassDescriptor,  'workflow': WorkflowDescriptor}
        # The following dict contains a series of replacements that need to be
        # applied to file templates to generate files.
        self.repls = {'applicationName': self.applicationName,
                      'applicationPath': os.path.dirname(self.application),
                      'codeHeader': CODE_HEADER}
        # List of Appy classes and workflows found in the application
        self.classes = []
        self.tool = None
        self.user = None
        self.workflows = []
        self.initialize()
        self.config = gen.Config.getDefault()
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
            if isinstance(attrValue, gen.Type):
                res = 'class'
            elif isinstance(attrValue, gen.State):
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
                if callable(elem) and (type(elem) != types.ClassType) and \
                   hasattr(elem, '__doc__') and elem.__doc__ and \
                   (elem.__doc__.find('>>>') != -1):
                    res = True
                    self.totalNumberOfTests += 1
        return res

    def walkModule(self, moduleName, module):
        '''Visits a given module of the application.'''
        # Create the AST for this module. Producing an AST allows us to retrieve
        # class attributes in the order of their definition, which is not
        # possible by introspecting dict-based class objects.
        moduleFile = module.__file__
        if moduleFile.endswith('.pyc'):
            moduleFile = moduleFile[:-1]
        astClasses = Ast(moduleFile).classes
        # Check if tests are present in this module
        if self.containsTests(module):
            self.modulesWithTests.add(module.__name__)
        classType = type(Generator)
        # Find all classes in this module
        for name in module.__dict__.keys():
            exec 'moduleElem = module.%s' % name
            if (type(moduleElem) == classType) and \
               (moduleElem.__module__ == module.__name__):
                # We have found a Python class definition in this module.
                appyType = self.determineAppyType(moduleElem)
                if appyType == 'none': continue
                # Produce a list of static class attributes (in the order
                # of their definition).
                attrs = astClasses[moduleElem.__name__].attributes
                # Collect non-parsable attrs = back references added
                # programmatically
                moreAttrs = []
                for eName, eValue in moduleElem.__dict__.iteritems():
                    if isinstance(eValue, gen.Type) and (eName not in attrs):
                        moreAttrs.append(eName)
                # Sort them in alphabetical order: else, order would be random
                moreAttrs.sort()
                if moreAttrs: attrs += moreAttrs
                # Add attributes added as back references
                if appyType == 'class':
                    # Determine the class type (standard, tool, user...)
                    if issubclass(moduleElem, gen.Tool):
                        if not self.tool:
                            klass = self.descriptorClasses['tool']
                            self.tool = klass(moduleElem, attrs, self)
                        else:
                            self.tool.update(moduleElem, attrs)
                    elif issubclass(moduleElem, gen.User):
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
                        self.modulesWithTests.add(module.__name__)
                elif appyType == 'workflow':
                    descriptorClass = self.descriptorClasses['workflow']
                    descriptor = descriptorClass(moduleElem, attrs, self)
                    self.workflows.append(descriptor)
                    if self.containsTests(moduleElem):
                        self.modulesWithTests.add(module.__name__)
            elif isinstance(moduleElem, gen.Config):
                self.config = moduleElem

    def walkApplication(self):
        '''This method walks into the application and creates the corresponding
           meta-classes in self.classes, self.workflows, etc.'''
        # Where is the application located ?
        containingFolder = os.path.dirname(self.application)
        sys.path.append(containingFolder)
        # What is the name of the application ?
        appName = os.path.basename(self.application)
        # Collect modules (only a the first level) in this application. Import
        # them all, to be sure class definitions are complete (ie, back
        # references are set from one class to the other). Moreover, potential
        # syntax or import errors will raise an exception and abort the
        # generation process before we do any undoable action.
        modules = []
        for fileName in os.listdir(self.application):
            # Ignore non Python files
            if not fileName.endswith('.py'): continue
            moduleName = '%s.%s' % (appName, os.path.splitext(fileName)[0])
            exec 'import %s' % moduleName
            modules.append(eval(moduleName))
        # Parse imported modules
        for module in modules:
            self.walkModule(moduleName, module)
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
class ZopeGenerator(Generator):
    '''This generator generates a Zope-compliant product from a given Appy
       application.'''
    poExtensions = ('.po', '.pot')

    def __init__(self, *args, **kwargs):
        Tool._appy_clean()
        Generator.__init__(self, *args, **kwargs)
        # Set our own Descriptor classes
        self.descriptorClasses['class'] = ClassDescriptor
        # Create Tool, User, Group, Translation and Page instances.
        self.tool = ToolClassDescriptor(Tool, self)
        self.user = UserClassDescriptor(User, self)
        self.group = GroupClassDescriptor(Group, self)
        self.translation = TranslationClassDescriptor(Translation, self)
        self.page = PageClassDescriptor(Page, self)
        # i18n labels to generate
        self.labels = po.PoMessages()

    def i18n(self, id, default, nice=True):
        '''Shorthand for adding a new message into self.labels.'''
        self.labels.append(id, default, nice=nice)

    versionRex = re.compile('(.*?\s+build)\s+(\d+)')
    def initialize(self):
        # Determine version number
        self.version = '0.1.0 build 1'
        versionTxt = os.path.join(self.outputFolder, 'version.txt')
        if os.path.exists(versionTxt):
            f = file(versionTxt)
            oldVersion = f.read().strip()
            f.close()
            res = self.versionRex.search(oldVersion)
            self.version = res.group(1) + ' ' + str(int(res.group(2))+1)
        # Existing i18n files
        self.i18nFiles = {} #~{p_fileName: PoFile}~
        # Retrieve existing i18n files if any
        i18nFolder = os.path.join(self.application, 'tr')
        if os.path.exists(i18nFolder):
            for fileName in os.listdir(i18nFolder):
                name, ext = os.path.splitext(fileName)
                if ext in self.poExtensions:
                    poParser = po.PoParser(os.path.join(i18nFolder, fileName))
                    self.i18nFiles[fileName] = poParser.parse()

    def finalize(self):
        # Add a label for the application name
        self.i18n(self.applicationName, self.applicationName)
        # Add default Appy i18n messages
        for id, default in po.appyLabels:
            self.i18n(id, default, nice=False)
        # Add a label for every role added by this application (we ensure role
        # 'Manager' was added even if not mentioned anywhere).
        self.i18n('role_Manager', 'Manager')
        for role in self.getAllUsedRoles():
            self.i18n('role_%s' % role.name, role.name)
        # Create basic files (config.py, etc)
        self.generateTool()
        self.generateInit()
        self.generateTests()
        # Create version.txt
        f = open(os.path.join(self.outputFolder, 'version.txt'), 'w')
        f.write(self.version)
        f.close()
        # Make folder "tests" a Python package
        initFile = '%s/tests/__init__.py' % self.outputFolder
        if not os.path.isfile(initFile):
            f = open(initFile, 'w')
            f.write('')
            f.close()
        # Generate i18n pot file
        potFileName = '%s.pot' % self.applicationName
        if self.i18nFiles.has_key(potFileName):
            potFile = self.i18nFiles[potFileName]
        else:
            fullName = os.path.join(self.application, 'tr', potFileName)
            potFile = po.PoFile(fullName)
            self.i18nFiles[potFileName] = potFile
        # We update the POT file with our list of automatically managed labels.
        removedLabels = potFile.update(self.labels.get(),self.options.i18nClean,
                                       not self.options.i18nSort)
        if removedLabels:
            print 'Warning: %d messages were removed from translation ' \
                  'files: %s' % (len(removedLabels), str(removedLabels))
        # Before generating the POT file, we still need to add one label for
        # every page for the Translation class. We've not done it yet because
        # the number of pages depends on the total number of labels in the POT
        # file.
        pageLabels = []
        nbOfPages = int(len(potFile.messages)/self.config.translationsPerPage)+1
        for i in range(nbOfPages):
            msgId = '%s_page_%d' % (self.translation.name, i+2)
            pageLabels.append(po.PoMessage(msgId, '', 'Page %d' % (i+2)))
        potFile.update(pageLabels, keepExistingOrder=False)
        potFile.generate()
        # Generate i18n po files
        for language in self.config.languages:
            # I must generate (or update) a po file for the language(s)
            # specified in the configuration.
            poFileName = potFile.getPoFileName(language)
            if self.i18nFiles.has_key(poFileName):
                poFile = self.i18nFiles[poFileName]
            else:
                fullName = os.path.join(self.application, 'tr', poFileName)
                poFile = po.PoFile(fullName)
                self.i18nFiles[poFileName] = poFile
            poFile.update(potFile.messages, self.options.i18nClean,
                          not self.options.i18nSort)
            poFile.generate()
        # Generate corresponding fields on the Translation class
        page = 'main'
        i = 0
        for message in potFile.messages:
            i += 1
            # A computed field is used for displaying the text to translate.
            self.translation.addLabelField(message.id, page)
            # A String field will hold the translation in itself.
            self.translation.addMessageField(message.id, page, self.i18nFiles)
            if (i % self.config.translationsPerPage) == 0:
                # A new page must be defined.
                if page == 'main':
                    page = '2'
                else:
                    page = str(int(page)+1)
        self.generateWrappers()
        self.generateConfig()

    def getAllUsedRoles(self, zope=None, local=None, grantable=None):
        '''Produces a list of all the roles used within all workflows and
           classes defined in this application.

           If p_zope is True, it keeps only Zope-standard roles; if p_zope
           is False, it keeps only roles which are specific to this application;
           if p_zope is None it has no effect (so it keeps both roles).

           If p_local is True, it keeps only local roles (ie, roles that can
           only be granted locally); if p_local is False, it keeps only "global"
           roles; if p_local is None it has no effect (so it keeps both roles).

           If p_grantable is True, it keeps only roles that the admin can
           grant; if p_grantable is False, if keeps only ungrantable roles (ie
           those that are implicitly granted by the system like role
           "Authenticated"); if p_grantable is None it keeps both roles.'''
        allRoles = {} # ~{s_roleName:Role_role}~
        # Gather roles from workflow states and transitions
        for wfDescr in self.workflows:
            for attr in dir(wfDescr.klass):
                attrValue = getattr(wfDescr.klass, attr)
                if isinstance(attrValue, gen.State) or \
                   isinstance(attrValue, gen.Transition):
                    for role in attrValue.getUsedRoles():
                        if role.name not in allRoles:
                            allRoles[role.name] = role
        # Gather roles from "creators" attributes from every class
        for cDescr in self.getClasses(include='all'):
            for role in cDescr.getCreators():
                if role.name not in allRoles:
                    allRoles[role.name] = role
        res = allRoles.values()
        # Filter the result according to parameters
        for p in ('zope', 'local', 'grantable'):
            if eval(p) != None:
                res = [r for r in res if eval('r.%s == %s' % (p, p))]
        return res

    def getAppyTypePath(self, name, appyType, klass, isBack=False):
        '''Gets the path to the p_appyType when a direct reference to an
           appyType must be generated in a Python file.'''
        if issubclass(klass, ModelClass):
            res = 'wrappers.%s.%s' % (klass.__name__, name)
        else:
            res = '%s.%s.%s' % (klass.__module__, klass.__name__, name)
        if isBack: res += '.back'
        return res

    def getClasses(self, include=None):
        '''Returns the descriptors for all the classes in the generated
           gen-application. If p_include is:
           * "all"        it includes the descriptors for the config-related
                          classes (tool, user, group, translation, page)
           * "allButTool" it includes the same descriptors, the tool excepted
           * "custom"     it includes descriptors for the config-related classes
                          for which the user has created a sub-class.'''
        if not include: return self.classes
        res = self.classes[:]
        configClasses = [self.tool, self.user, self.group, self.translation,
                         self.page]
        if include == 'all':
            res += configClasses
        elif include == 'allButTool':
            res += configClasses[1:]
        elif include == 'custom':
            res += [c for c in configClasses if c.customized]
        elif include == 'predefined':
            res = configClasses
        return res

    def generateConfig(self):
        repls = self.repls.copy()
        # Get some lists of classes
        classes = self.getClasses()
        classesWithCustom = self.getClasses(include='custom')
        classesButTool = self.getClasses(include='allButTool')
        classesAll = self.getClasses(include='all')
        # Compute imports
        imports = ['import %s' % self.applicationName]
        for classDescr in (classesWithCustom + self.workflows):
            theImport = 'import %s' % classDescr.klass.__module__
            if theImport not in imports:
                imports.append(theImport)
        repls['imports'] = '\n'.join(imports)
        # Compute default add roles
        repls['defaultAddRoles'] = ','.join(
                              ['"%s"' % r for r in self.config.defaultCreators])
        # Compute list of add permissions
        addPermissions = ''
        for classDescr in classesAll:
            addPermissions += '    "%s":"%s: Add %s",\n' % (classDescr.name,
                self.applicationName, classDescr.name)
        repls['addPermissions'] = addPermissions
        # Compute root classes
        repls['rootClasses'] = ','.join(["'%s'" % c.name \
                                        for c in classesButTool if c.isRoot()])
        # Compute list of class definitions
        repls['appClasses'] = ','.join(['%s.%s' % (c.klass.__module__, \
                                       c.klass.__name__) for c in classes])
        # Compute lists of class names
        repls['appClassNames'] = ','.join(['"%s"' % c.name \
                                           for c in classes])
        repls['allClassNames'] = ','.join(['"%s"' % c.name \
                                           for c in classesButTool])
        # Compute the list of ordered attributes (forward and backward,
        # inherited included) for every Appy class.
        attributes = []
        for classDescr in classesAll:
            titleFound = False
            names = []
            for name, appyType, klass in classDescr.getOrderedAppyAttributes():
                names.append(name)
                if name == 'title': titleFound = True
            # Add the "title" mandatory field if not found
            if not titleFound: names.insert(0, 'title')
            # Add the 'state' attribute
            names.append('state')
            qNames = ['"%s"' % name for name in names]
            attributes.append('"%s":[%s]' % (classDescr.name, ','.join(qNames)))
        repls['attributes'] = ',\n    '.join(attributes)
        # Compute list of used roles for registering them if needed
        specificRoles = self.getAllUsedRoles(zope=False)
        repls['roles'] = ','.join(['"%s"' % r.name for r in specificRoles])
        globalRoles = self.getAllUsedRoles(zope=False, local=False)
        repls['gRoles'] = ','.join(['"%s"' % r.name for r in globalRoles])
        grantableRoles = self.getAllUsedRoles(local=False, grantable=True)
        repls['grRoles'] = ','.join(['"%s"' % r.name for r in grantableRoles])
        # Generate configuration options
        repls['languages'] = ','.join('"%s"' % l for l in self.config.languages)
        repls['languageSelector'] = self.config.languageSelector
        repls['sourceLanguage'] = self.config.sourceLanguage
        repls['enableSessionTimeout'] = self.config.enableSessionTimeout
        repls['ogone'] = repr(self.config.ogone)
        repls['activateForgotPassword'] = self.config.activateForgotPassword
        self.copyFile('config.pyt', repls, destName='config.py')

    def generateInit(self):
        # Compute imports
        imports = []
        classNames = []
        for c in self.getClasses(include='all'):
            importDef = '    import %s' % c.name
            if importDef not in imports:
                imports.append(importDef)
                classNames.append("%s.%s" % (c.name, c.name))
        repls = self.repls.copy()
        repls['imports'] = '\n'.join(imports)
        repls['classes'] = ','.join(classNames)
        repls['totalNumberOfTests'] = self.totalNumberOfTests
        self.copyFile('__init__.pyt', repls, destName='__init__.py')

    def getClassesInOrder(self, allClasses):
        '''When generating wrappers, classes mut be dumped in order (else, it
           generates forward references in the Python file, that does not
           compile).'''
        res = [] # Appy class descriptors
        resClasses = [] # Corresponding real Python classes
        for classDescr in allClasses:
            klass = classDescr.klass
            if not klass.__bases__ or \
               (klass.__bases__[0].__name__ == 'ModelClass'):
                # This is a root class. We dump it at the begin of the file.
                res.insert(0, classDescr)
                resClasses.insert(0, klass)
            else:
                # If a child of this class is already present, we must insert
                # this klass before it.
                lowestChildIndex = sys.maxint
                for resClass in resClasses:
                    if klass in resClass.__bases__:
                        lowestChildIndex = min(lowestChildIndex,
                                               resClasses.index(resClass))
                if lowestChildIndex != sys.maxint:
                    res.insert(lowestChildIndex, classDescr)
                    resClasses.insert(lowestChildIndex, klass)
                else:
                    res.append(classDescr)
                    resClasses.append(klass)
        return res

    def generateWrappers(self):
        # We must generate imports and wrapper definitions
        imports = []
        wrappers = []
        allClasses = self.getClasses(include='all')
        for c in self.getClassesInOrder(allClasses):
            if not c.predefined or c.customized:
                moduleImport = 'import %s' % c.klass.__module__
                if moduleImport not in imports:
                    imports.append(moduleImport)
            # Determine parent wrapper and class
            parentClasses = c.getParents(allClasses)
            wrapperDef = 'class %s_Wrapper(%s):\n' % \
                         (c.name, ','.join(parentClasses))
            wrapperDef += '    security = ClassSecurityInfo()\n'
            if c.customized:
                # For custom tool, add a call to a method that allows to
                # customize elements from the base class.
                wrapperDef += "    if hasattr(%s, 'update'):\n        " \
                    "%s.update(%s)\n" % (parentClasses[1], parentClasses[1],
                                         parentClasses[0])
                # For custom tool, add security declaration that will allow to
                # call their methods from ZPTs.
                for parentClass in parentClasses:
                    wrapperDef += "    for elem in dir(%s):\n        " \
                        "if not elem.startswith('_'): security.declarePublic" \
                        "(elem)\n" % (parentClass)
            # Register the class in Zope.
            wrapperDef += 'InitializeClass(%s_Wrapper)\n' % c.name
            wrappers.append(wrapperDef)
        repls = self.repls.copy()
        repls['imports'] = '\n'.join(imports)
        repls['wrappers'] = '\n'.join(wrappers)
        for klass in self.getClasses(include='predefined'):
            modelClass = klass.modelClass
            repls['%s' % modelClass.__name__] = modelClass._appy_getBody()
        self.copyFile('wrappers.pyt', repls, destName='wrappers.py')

    def generateTests(self):
        '''Generates the file needed for executing tests.'''
        repls = self.repls.copy()
        modules = self.modulesWithTests
        repls['imports'] = '\n'.join(['import %s' % m for m in modules])
        repls['modulesWithTests'] = ','.join(modules)
        self.copyFile('testAll.pyt', repls, destName='testAll.py',
                      destFolder='tests')

    def generateTool(self):
        '''Generates the tool that corresponds to this application.'''
        # Create Tool-related i18n-related messages
        self.i18n(self.tool.name, po.CONFIG % self.applicationName, nice=False)
        # Tune the Ref field between Tool->User and Group->User
        Tool.users.klass = User
        if self.user.customized:
            Tool.users.klass = self.user.klass
            Group.users.klass = self.user.klass

        # Generate the Tool-related classes (User, Group, Translation, Page)
        for klass in (self.user, self.group, self.translation, self.page):
            klassType = klass.name[len(self.applicationName):]
            klass.generateSchema()
            self.i18n(klass.name, klassType, nice=False)
            self.i18n('%s_plural' % klass.name, klass.name+'s', nice=False)
            repls = self.repls.copy()
            if klass.isFolder():
                parents = 'BaseMixin, Folder'
                icon = 'folder.gif'
            else:
                parents = 'BaseMixin, SimpleItem'
                icon = 'object.gif'
            repls.update({'methods': klass.methods, 'genClassName': klass.name,
                          'baseMixin':'BaseMixin', 'parents': parents,
                          'classDoc': 'Standard Appy class', 'icon': icon})
            self.copyFile('Class.pyt', repls, destName='%s.py' % klass.name)

        # Before generating the Tool class, finalize it with query result
        # columns, search-related and import-related fields.
        for classDescr in self.getClasses(include='allButTool'):
            if not classDescr.isRoot(): continue
            # We must be able to configure query results from the tool.
            self.tool.addQueryResultColumns(classDescr)
            # Add the search-related fields.
            self.tool.addSearchRelatedFields(classDescr)
            importMean = classDescr.getCreateMean('Import')
            if importMean:
                self.tool.addImportRelatedFields(classDescr)
        self.tool.generateSchema()

        # Generate the Tool class
        repls = self.repls.copy()
        repls.update({'methods': self.tool.methods,
          'genClassName': self.tool.name, 'baseMixin':'ToolMixin',
          'parents': 'ToolMixin, Folder', 'icon': 'folder.gif',
          'classDoc': 'Tool class for %s' % self.applicationName})
        self.copyFile('Class.pyt', repls, destName='%s.py' % self.tool.name)

    def generateClass(self, classDescr):
        '''Is called each time an Appy class is found in the application, for
           generating the corresponding Archetype class.'''
        k = classDescr.klass
        print 'Generating %s.%s (gen-class)...' % (k.__module__, k.__name__)
        # Determine base Zope class
        isFolder = classDescr.isFolder()
        baseClass = isFolder and 'Folder' or 'SimpleItem'
        icon = isFolder and 'folder.gif' or 'object.gif'
        parents = 'BaseMixin, %s' % baseClass
        classDoc = k.__doc__ or 'Appy class.'
        repls = self.repls.copy()
        classDescr.generateSchema()
        repls.update({
          'parents': parents, 'className': k.__name__,
          'genClassName': classDescr.name, 'baseMixin':'BaseMixin',
          'classDoc': classDoc, 'applicationName': self.applicationName,
          'methods': classDescr.methods, 'icon':icon})
        fileName = '%s.py' % classDescr.name
        # Create i18n labels (class name and plural form)
        self.i18n(classDescr.name, k.__name__)
        self.i18n('%s_plural' % classDescr.name, k.__name__+'s')
        # Create i18n labels for searches
        for search in classDescr.getSearches(k):
            label = '%s_search_%s' % (classDescr.name, search.name)
            self.i18n(label, search.name)
            self.i18n('%s_descr' % label, ' ', nice=False)
            # Generate labels for groups of searches
            if search.group and not search.group.label:
                search.group.generateLabels(self.labels, classDescr, set(),
                                            forSearch=True)
        # Generate the resulting Zope class.
        self.copyFile('Class.pyt', repls, destName=fileName)

    def generateWorkflow(self, wfDescr):
        '''This method creates the i18n labels related to the workflow described
           by p_wfDescr.'''
        k = wfDescr.klass
        print 'Generating %s.%s (gen-workflow)...' % (k.__module__, k.__name__)
        # Identify workflow name
        wfName = WorkflowDescriptor.getWorkflowName(wfDescr.klass)
        # Add i18n messages for states
        for name in dir(wfDescr.klass):
            if not isinstance(getattr(wfDescr.klass, name), gen.State): continue
            self.i18n('%s_%s' % (wfName, name), name)
        # Add i18n messages for transitions
        for name in dir(wfDescr.klass):
            transition = getattr(wfDescr.klass, name)
            if not isinstance(transition, gen.Transition): continue
            self.i18n('%s_%s' % (wfName, name), name)
            if transition.show and transition.confirm:
                # We need to generate a label for the message that will be shown
                # in the confirm popup.
                self.i18n('%s_%s_confirm'%(wfName, name),po.CONFIRM, nice=False)
            if transition.notify:
                # Appy will send a mail when this transition is triggered.
                # So we need 2 i18n labels: one for the mail subject and one for
                # the mail body.
                self.i18n('%s_%s_mail_subject' % (wfName, name),
                          po.EMAIL_SUBJECT, nice=False)
                self.i18n('%s_%s_mail_body' % (wfName, name),
                          po.EMAIL_BODY, nice=False)
# ------------------------------------------------------------------------------
