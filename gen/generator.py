# ------------------------------------------------------------------------------
import os, os.path, re, sys, parser, symbol, token, types
import appy.pod, appy.pod.renderer
from appy.shared.utils import FolderDeleter
#from appy.gen import *
from po import PoMessage, PoFile, PoParser
from descriptors import *
from utils import produceNiceMessage, getClassName
from model import ModelClass, User, Group, Tool, Translation

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
        # Determine output folder (where to store the generated product)
        self.outputFolder = outputFolder
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
                if callable(elem) and (type(elem) != types.ClassType) and \
                   hasattr(elem, '__doc__') and elem.__doc__ and \
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
                        # Determine the class type (standard, tool, user...)
                        if issubclass(moduleElem, Tool):
                            if not self.tool:
                                klass = self.descriptorClasses['tool']
                                self.tool = klass(moduleElem, attrs, self)
                            else:
                                self.tool.update(moduleElem, attrs)
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
class ZopeGenerator(Generator):
    '''This generator generates a Zope-compliant product from a given Appy
       application.'''
    poExtensions = ('.po', '.pot')

    def __init__(self, *args, **kwargs):
        Tool._appy_clean()
        Generator.__init__(self, *args, **kwargs)
        # Set our own Descriptor classes
        self.descriptorClasses['class'] = ClassDescriptor
        # Create our own Tool, User, Group and Translation instances
        self.tool = ToolClassDescriptor(Tool, self)
        self.user = UserClassDescriptor(User, self)
        self.group = GroupClassDescriptor(Group, self)
        self.translation = TranslationClassDescriptor(Translation, self)
        # i18n labels to generate
        self.labels = [] # i18n labels
        self.referers = {}

    versionRex = re.compile('(.*?\s+build)\s+(\d+)')
    def initialize(self):
        # Determine version number
        self.version = '0.1 build 1'
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
                    poParser = PoParser(os.path.join(i18nFolder, fileName))
                    self.i18nFiles[fileName] = poParser.parse()

    def finalize(self):
        # Some useful aliases
        msg = PoMessage
        app = self.applicationName
        # Some global i18n messages
        poMsg = msg(app, '', app); poMsg.produceNiceDefault()
        self.labels += [poMsg,
            msg('workflow_state',       '', msg.WORKFLOW_STATE),
            msg('appy_title',           '', msg.APPY_TITLE),
            msg('data_change',          '', msg.DATA_CHANGE),
            msg('modified_field',       '', msg.MODIFIED_FIELD),
            msg('previous_value',       '', msg.PREVIOUS_VALUE),
            msg('phase',                '', msg.PHASE),
            msg('root_type',            '', msg.ROOT_TYPE),
            msg('workflow_comment',     '', msg.WORKFLOW_COMMENT),
            msg('choose_a_value',       '', msg.CHOOSE_A_VALUE),
            msg('choose_a_doc',         '', msg.CHOOSE_A_DOC),
            msg('min_ref_violated',     '', msg.MIN_REF_VIOLATED),
            msg('max_ref_violated',     '', msg.MAX_REF_VIOLATED),
            msg('no_ref',               '', msg.REF_NO),
            msg('add_ref',              '', msg.REF_ADD),
            msg('ref_actions',          '', msg.REF_ACTIONS),
            msg('action_ok',            '', msg.ACTION_OK),
            msg('action_ko',            '', msg.ACTION_KO),
            msg('move_up',              '', msg.REF_MOVE_UP),
            msg('move_down',            '', msg.REF_MOVE_DOWN),
            msg('query_create',         '', msg.QUERY_CREATE),
            msg('query_import',         '', msg.QUERY_IMPORT),
            msg('query_no_result',      '', msg.QUERY_NO_RESULT),
            msg('query_consult_all',    '', msg.QUERY_CONSULT_ALL),
            msg('import_title',         '', msg.IMPORT_TITLE),
            msg('import_show_hide',     '', msg.IMPORT_SHOW_HIDE),
            msg('import_already',       '', msg.IMPORT_ALREADY),
            msg('import_many',          '', msg.IMPORT_MANY),
            msg('import_done',          '', msg.IMPORT_DONE),
            msg('search_title',         '', msg.SEARCH_TITLE),
            msg('search_button',        '', msg.SEARCH_BUTTON),
            msg('search_objects',       '', msg.SEARCH_OBJECTS),
            msg('search_results',       '', msg.SEARCH_RESULTS),
            msg('search_results_descr', '', ' '),
            msg('search_new',           '', msg.SEARCH_NEW),
            msg('search_from',          '', msg.SEARCH_FROM),
            msg('search_to',            '', msg.SEARCH_TO),
            msg('search_or',            '', msg.SEARCH_OR),
            msg('search_and',           '', msg.SEARCH_AND),
            msg('ref_invalid_index',    '', msg.REF_INVALID_INDEX),
            msg('bad_long',             '', msg.BAD_LONG),
            msg('bad_float',            '', msg.BAD_FLOAT),
            msg('bad_date',             '', msg.BAD_DATE),
            msg('bad_email',            '', msg.BAD_EMAIL),
            msg('bad_url',              '', msg.BAD_URL),
            msg('bad_alphanumeric',     '', msg.BAD_ALPHANUMERIC),
            msg('bad_select_value',     '', msg.BAD_SELECT_VALUE),
            msg('select_delesect',      '', msg.SELECT_DESELECT),
            msg('no_elem_selected',     '', msg.NO_SELECTION),
            msg('delete_confirm',       '', msg.DELETE_CONFIRM),
            msg('delete_done',          '', msg.DELETE_DONE),
            msg('goto_first',           '', msg.GOTO_FIRST),
            msg('goto_previous',        '', msg.GOTO_PREVIOUS),
            msg('goto_next',            '', msg.GOTO_NEXT),
            msg('goto_last',            '', msg.GOTO_LAST),
            msg('goto_source',          '', msg.GOTO_SOURCE),
            msg('whatever',             '', msg.WHATEVER),
            msg('yes',                  '', msg.YES),
            msg('no',                   '', msg.NO),
            msg('field_required',       '', msg.FIELD_REQUIRED),
            msg('field_invalid',        '', msg.FIELD_INVALID),
            msg('file_required',        '', msg.FILE_REQUIRED),
            msg('image_required',       '', msg.IMAGE_REQUIRED),
            msg('odt',                  '', msg.FORMAT_ODT),
            msg('pdf',                  '', msg.FORMAT_PDF),
            msg('doc',                  '', msg.FORMAT_DOC),
            msg('rtf',                  '', msg.FORMAT_RTF),
            msg('front_page_text',      '', msg.FRONT_PAGE_TEXT),
        ]
        # Create a label for every role added by this application
        for role in self.getAllUsedRoles():
            self.labels.append(msg('role_%s' % role.name,'', role.name,
                                   niceDefault=True))
        # Create basic files (config.py, etc)
        self.generateTool()
        self.generateInit()
        self.generateTests()
        self.generateConfigureZcml()
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
        # Decline i18n labels into versions for child classes
        for classDescr in self.classes:
            for poMsg in classDescr.labelsToPropagate:
                for childDescr in classDescr.getChildren():
                    childMsg = poMsg.clone(classDescr.name, childDescr.name)
                    if childMsg not in self.labels:
                        self.labels.append(childMsg)
        # Generate i18n pot file
        potFileName = '%s.pot' % self.applicationName
        if self.i18nFiles.has_key(potFileName):
            potFile = self.i18nFiles[potFileName]
        else:
            fullName = os.path.join(self.application, 'tr', potFileName)
            potFile = PoFile(fullName)
            self.i18nFiles[potFileName] = potFile
        # We update the POT file with our list of automatically managed labels.
        removedLabels = potFile.update(self.labels, self.options.i18nClean,
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
            pageLabels.append(msg(msgId, '', 'Page %d' % (i+2)))
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
                poFile = PoFile(fullName)
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

    def getAllUsedRoles(self, plone=None, local=None, grantable=None):
        '''Produces a list of all the roles used within all workflows and
           classes defined in this application.

           If p_plone is True, it keeps only Plone-standard roles; if p_plone
           is False, it keeps only roles which are specific to this application;
           if p_plone is None it has no effect (so it keeps both roles).

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
                if isinstance(attrValue, State) or \
                   isinstance(attrValue, Transition):
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
        for p in ('plone', 'local', 'grantable'):
            if eval(p) != None:
                res = [r for r in res if eval('r.%s == %s' % (p, p))]
        return res

    def addReferer(self, fieldDescr):
        '''p_fieldDescr is a Ref type definition.'''
        k = fieldDescr.appyType.klass
        refClassName = getClassName(k, self.applicationName)
        if not self.referers.has_key(refClassName):
            self.referers[refClassName] = []
        self.referers[refClassName].append(fieldDescr)

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
                          classes (tool, user, group, translation)
           * "allButTool" it includes the same descriptors, the tool excepted
           * "custom"     it includes descriptors for the config-related classes
                          for which the user has created a sub-class.'''
        if not include: return self.classes
        res = self.classes[:]
        configClasses = [self.tool, self.user, self.group, self.translation]
        if include == 'all':
            res += configClasses
        elif include == 'allButTool':
            res += configClasses[1:]
        elif include == 'custom':
            res += [c for c in configClasses if c.customized]
        elif include == 'predefined':
            res = configClasses
        return res

    def generateConfigureZcml(self):
        '''Generates file configure.zcml.'''
        repls = self.repls.copy()
        # Note every class as "deprecated".
        depr = ''
        for klass in self.getClasses(include='all'):
            depr += '<five:deprecatedManageAddDelete class=".%s.%s"/>\n' % \
                    (klass.name, klass.name)
        repls['deprecated'] = depr
        self.copyFile('configure.zcml', repls)

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
            # Any backward attributes to append?
            if classDescr.name in self.referers:
                for field in self.referers[classDescr.name]:
                    names.append(field.appyType.back.attribute)
            qNames = ['"%s"' % name for name in names]
            attributes.append('"%s":[%s]' % (classDescr.name, ','.join(qNames)))
        repls['attributes'] = ',\n    '.join(attributes)
        # Compute list of used roles for registering them if needed
        specificRoles = self.getAllUsedRoles(plone=False)
        repls['roles'] = ','.join(['"%s"' % r.name for r in specificRoles])
        globalRoles = self.getAllUsedRoles(plone=False, local=False)
        repls['gRoles'] = ','.join(['"%s"' % r.name for r in globalRoles])
        grantableRoles = self.getAllUsedRoles(local=False, grantable=True)
        repls['grRoles'] = ','.join(['"%s"' % r.name for r in grantableRoles])
        # Generate configuration options
        repls['languages'] = ','.join('"%s"' % l for l in self.config.languages)
        repls['languageSelector'] = self.config.languageSelector
        repls['sourceLanguage'] = self.config.sourceLanguage
        self.copyFile('config.py', repls)

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
        self.copyFile('__init__.py', repls)

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
        self.copyFile('wrappers.py', repls)

    def generateTests(self):
        '''Generates the file needed for executing tests.'''
        repls = self.repls.copy()
        modules = self.modulesWithTests
        repls['imports'] = '\n'.join(['import %s' % m for m in modules])
        repls['modulesWithTests'] = ','.join(modules)
        self.copyFile('testAll.py', repls, destFolder='tests')

    def generateTool(self):
        '''Generates the Plone tool that corresponds to this application.'''
        Msg = PoMessage
        # Create Tool-related i18n-related messages
        msg = Msg(self.tool.name, '', Msg.CONFIG % self.applicationName)
        self.labels.append(msg)

        # Tune the Ref field between Tool->User and Group->User
        Tool.users.klass = User
        if self.user.customized:
            Tool.users.klass = self.user.klass
            Group.users.klass = self.user.klass

        # Generate the Tool-related classes (User, Group, Translation)
        for klass in (self.user, self.group, self.translation):
            klassType = klass.name[len(self.applicationName):]
            klass.generateSchema()
            self.labels += [ Msg(klass.name, '', klassType),
                             Msg('%s_plural' % klass.name,'', klass.name+'s')]
            repls = self.repls.copy()
            repls.update({'methods': klass.methods, 'genClassName': klass.name,
              'baseMixin':'BaseMixin', 'parents': 'BaseMixin, SimpleItem',
              'classDoc': 'Standard Appy class', 'icon':'object.gif'})
            self.copyFile('Class.py', repls, destName='%s.py' % klass.name)

        # Before generating the Tool class, finalize it with query result
        # columns, with fields to propagate, workflow-related fields.
        for classDescr in self.getClasses(include='allButTool'):
            for fieldName, fieldType in classDescr.toolFieldsToPropagate:
                for childDescr in classDescr.getChildren():
                    childFieldName = fieldName % childDescr.name
                    fieldType.group = childDescr.klass.__name__
                    self.tool.addField(childFieldName, fieldType)
            if classDescr.isRoot():
                # We must be able to configure query results from the tool.
                self.tool.addQueryResultColumns(classDescr)
                # Add the search-related fields.
                self.tool.addSearchRelatedFields(classDescr)
                importMean = classDescr.getCreateMean('Import')
                if importMean:
                    self.tool.addImportRelatedFields(classDescr)
        self.tool.addWorkflowFields(self.user)
        self.tool.generateSchema()

        # Generate the Tool class
        repls = self.repls.copy()
        repls.update({'methods': self.tool.methods,
          'genClassName': self.tool.name, 'baseMixin':'ToolMixin',
          'parents': 'ToolMixin, Folder', 'icon': 'folder.gif',
          'classDoc': 'Tool class for %s' % self.applicationName})
        self.copyFile('Class.py', repls, destName='%s.py' % self.tool.name)

    def generateClass(self, classDescr):
        '''Is called each time an Appy class is found in the application, for
           generating the corresponding Archetype class.'''
        k = classDescr.klass
        print 'Generating %s.%s (gen-class)...' % (k.__module__, k.__name__)
        if not classDescr.isAbstract():
            self.tool.addWorkflowFields(classDescr)
        # Determine base Zope class
        isFolder = classDescr.isFolder()
        baseClass = isFolder and 'Folder' or 'SimpleItem'
        icon = isFolder and 'folder.gif' or 'object.gif'
        parents = 'BaseMixin, %s' % baseClass
        classDoc = classDescr.klass.__doc__ or 'Appy class.'
        repls = self.repls.copy()
        classDescr.generateSchema()
        repls.update({
          'parents': parents, 'className': classDescr.klass.__name__,
          'genClassName': classDescr.name, 'baseMixin':'BaseMixin',
          'classDoc': classDoc, 'applicationName': self.applicationName,
          'methods': classDescr.methods, 'icon':icon})
        fileName = '%s.py' % classDescr.name
        # Create i18n labels (class name and plural form)
        poMsg = PoMessage(classDescr.name, '', classDescr.klass.__name__)
        poMsg.produceNiceDefault()
        self.labels.append(poMsg)
        poMsgPl = PoMessage('%s_plural' % classDescr.name, '',
            classDescr.klass.__name__+'s')
        poMsgPl.produceNiceDefault()
        self.labels.append(poMsgPl)
        # Create i18n labels for searches
        for search in classDescr.getSearches(classDescr.klass):
            searchLabel = '%s_search_%s' % (classDescr.name, search.name)
            labels = [searchLabel, '%s_descr' % searchLabel]
            if search.group:
                grpLabel = '%s_searchgroup_%s' % (classDescr.name, search.group)
                labels += [grpLabel, '%s_descr' % grpLabel]
            for label in labels:
                default = ' '
                if label == searchLabel: default = search.name
                poMsg = PoMessage(label, '', default)
                poMsg.produceNiceDefault()
                if poMsg not in self.labels:
                    self.labels.append(poMsg)
        # Generate the resulting Archetypes class.
        self.copyFile('Class.py', repls, destName=fileName)

    def generateWorkflow(self, wfDescr):
        '''This method creates the i18n labels related to the workflow described
           by p_wfDescr.'''
        k = wfDescr.klass
        print 'Generating %s.%s (gen-workflow)...' % (k.__module__, k.__name__)
        # Identify workflow name
        wfName = WorkflowDescriptor.getWorkflowName(wfDescr.klass)
        # Add i18n messages for states
        for name in dir(wfDescr.klass):
            if not isinstance(getattr(wfDescr.klass, name), State): continue
            poMsg = PoMessage('%s_%s' % (wfName, name), '', name)
            poMsg.produceNiceDefault()
            self.labels.append(poMsg)
        # Add i18n messages for transitions
        for name in dir(wfDescr.klass):
            transition = getattr(wfDescr.klass, name)
            if not isinstance(transition, Transition): continue
            poMsg = PoMessage('%s_%s' % (wfName, name), '', name)
            poMsg.produceNiceDefault()
            self.labels.append(poMsg)
            if transition.confirm:
                # We need to generate a label for the message that will be shown
                # in the confirm popup.
                label = '%s_%s_confirm' % (wfName, name)
                poMsg = PoMessage(label, '', PoMessage.CONFIRM)
                self.labels.append(poMsg)
            if transition.notify:
                # Appy will send a mail when this transition is triggered.
                # So we need 2 i18n labels: one for the mail subject and one for
                # the mail body.
                subjectLabel = '%s_%s_mail_subject' % (wfName, name)
                poMsg = PoMessage(subjectLabel, '', PoMessage.EMAIL_SUBJECT)
                self.labels.append(poMsg)
                bodyLabel = '%s_%s_mail_body' % (wfName, name)
                poMsg = PoMessage(bodyLabel, '', PoMessage.EMAIL_BODY)
                self.labels.append(poMsg)
# ------------------------------------------------------------------------------
