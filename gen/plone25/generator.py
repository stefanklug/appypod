'''This file contains the main Generator class used for generating a
   Plone 2.5-compliant product.'''

# ------------------------------------------------------------------------------
import os, os.path, re, sys
import appy.gen
from appy.gen import *
from appy.gen.po import PoMessage, PoFile, PoParser
from appy.gen.generator import Generator as AbstractGenerator
from appy.gen.utils import getClassName
from appy.gen.descriptors import WorkflowDescriptor
from descriptors import ClassDescriptor, ToolClassDescriptor, \
                        UserClassDescriptor, TranslationClassDescriptor
from model import ModelClass, User, Tool, Translation

# Common methods that need to be defined on every Archetype class --------------
COMMON_METHODS = '''
    def getTool(self): return self.%s
    def getProductConfig(self): return Products.%s.config
    def skynView(self):
       """Redirects to skyn/view. Transfers the status message if any."""
       rq = self.REQUEST
       msg = rq.get('portal_status_message', '')
       if msg:
           url = self.getUrl(portal_status_message=msg)
       else:
           url = self.getUrl()
       return rq.RESPONSE.redirect(url)
'''
# ------------------------------------------------------------------------------
class Generator(AbstractGenerator):
    '''This generator generates a Plone 2.5-compliant product from a given
       appy application.'''
    poExtensions = ('.po', '.pot')

    def __init__(self, *args, **kwargs):
        Tool._appy_clean()
        AbstractGenerator.__init__(self, *args, **kwargs)
        # Set our own Descriptor classes
        self.descriptorClasses['class'] = ClassDescriptor
        # Create our own Tool, User and Translation instances
        self.tool = ToolClassDescriptor(Tool, self)
        self.user = UserClassDescriptor(User, self)
        self.translation = TranslationClassDescriptor(Translation, self)
        # i18n labels to generate
        self.labels = [] # i18n labels
        self.toolInstanceName = 'portal_%s' % self.applicationName.lower()
        self.portletName = '%s_portlet' % self.applicationName.lower()
        self.skinsFolder = 'skins/%s' % self.applicationName
        # The following dict, pre-filled in the abstract generator, contains a
        # series of replacements that need to be applied to file templates to
        # generate files.
        commonMethods = COMMON_METHODS % \
                        (self.toolInstanceName, self.applicationName)
        self.repls.update(
            {'toolInstanceName': self.toolInstanceName,
            'commonMethods': commonMethods})
        self.referers = {}

    versionRex = re.compile('(.*?\s+build)\s+(\d+)')
    def initialize(self):
        # Determine version number of the Plone product
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
        i18nFolder = os.path.join(self.outputFolder, 'i18n')
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
        ]
        # Create a label for every role added by this application
        for role in self.getAllUsedRoles():
            self.labels.append(msg('role_%s' % role.name,'', role.name,
                                   niceDefault=True))
        # Create basic files (config.py, Install.py, etc)
        self.generateTool()
        self.generateInit()
        self.generateTests()
        if self.config.frontPage: self.generateFrontPage()
        self.copyFile('Install.py', self.repls, destFolder='Extensions')
        self.generateConfigureZcml()
        self.copyFile('import_steps.xml', self.repls,
                      destFolder='profiles/default')
        self.copyFile('ProfileInit.py', self.repls, destFolder='profiles',
                      destName='__init__.py')
        self.copyFile('Portlet.pt', self.repls,
            destName='%s.pt' % self.portletName, destFolder=self.skinsFolder)
        self.copyFile('tool.gif', {})
        self.copyFile('Styles.css.dtml',self.repls, destFolder=self.skinsFolder,
                      destName = '%s.css.dtml' % self.applicationName)
        self.copyFile('IEFixes.css.dtml',self.repls,destFolder=self.skinsFolder)
        if self.config.minimalistPlone:
            self.copyFile('colophon.pt', self.repls,destFolder=self.skinsFolder)
            self.copyFile('footer.pt', self.repls, destFolder=self.skinsFolder)
        # Create version.txt
        f = open(os.path.join(self.outputFolder, 'version.txt'), 'w')
        f.write(self.version)
        f.close()
        # Make Extensions and tests Python packages
        for moduleFolder in ('Extensions', 'tests'):
            initFile = '%s/%s/__init__.py' % (self.outputFolder, moduleFolder)
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
            fullName = os.path.join(self.outputFolder, 'i18n/%s' % potFileName)
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
                fullName = os.path.join(self.outputFolder,
                                        'i18n/%s' % poFileName)
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
        # Generate i18n po files for other potential files
        for poFile in self.i18nFiles.itervalues():
            if not poFile.generated:
                poFile.generate()
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

    def addReferer(self, fieldDescr, relationship):
        '''p_fieldDescr is a Ref type definition. We will create in config.py a
           dict that lists all back references, by type.'''
        k = fieldDescr.appyType.klass
        refClassName = getClassName(k, self.applicationName)
        if not self.referers.has_key(refClassName):
            self.referers[refClassName] = []
        self.referers[refClassName].append( (fieldDescr, relationship))

    def getAppyTypePath(self, name, appyType, klass, isBack=False):
        '''Gets the path to the p_appyType when a direct reference to an
           appyType must be generated in a Python file.'''
        if issubclass(klass, ModelClass):
            res = 'wraps.%s.%s' % (klass.__name__, name)
        else:
            res = '%s.%s.%s' % (klass.__module__, klass.__name__, name)
        if isBack: res += '.back'
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
        for classDescr in classesButTool:
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
        # Compute classes whose instances must not be catalogued.
        catalogMap = ''
        blackClasses = [self.tool.name]
        for blackClass in blackClasses:
            catalogMap += "catalogMap['%s'] = {}\n" % blackClass
            catalogMap += "catalogMap['%s']['black'] = " \
                          "['portal_catalog']\n" % blackClass
        repls['catalogMap'] = catalogMap
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
                for field, rel in self.referers[classDescr.name]:
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
        repls['showPortlet'] = self.config.showPortlet
        repls['languages'] = ','.join('"%s"' % l for l in self.config.languages)
        repls['languageSelector'] = self.config.languageSelector
        repls['minimalistPlone'] = self.config.minimalistPlone
        repls['appFrontPage'] = bool(self.config.frontPage)
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

    def getClasses(self, include=None):
        '''Returns the descriptors for all the classes in the generated
           gen-application. If p_include is:
           * "all"        it includes the descriptors for the config-related
                          classes (tool, user, translation)
           * "allButTool" it includes the same descriptors, the tool excepted
           * "custom"     it includes descriptors for the config-related classes
                          for which the user has created a sub-class.'''
        if not include: return self.classes
        res = self.classes[:]
        configClasses = [self.tool, self.user, self.translation]
        if include == 'all':
            res += configClasses
        elif include == 'allButTool':
            res += configClasses[1:]
        elif include == 'custom':
            res += [c for c in configClasses if c.customized]
        elif include == 'predefined':
            res = configClasses
        return res

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
        self.copyFile('appyWrappers.py', repls, destFolder='Extensions')

    def generateTests(self):
        '''Generates the file needed for executing tests.'''
        repls = self.repls.copy()
        modules = self.modulesWithTests
        repls['imports'] = '\n'.join(['import %s' % m for m in modules])
        repls['modulesWithTests'] = ','.join(modules)
        self.copyFile('testAll.py', repls, destFolder='tests')

    def generateFrontPage(self):
        fp = self.config.frontPage
        repls = self.repls.copy()
        template = 'frontPage.pt'
        if self.config.frontPageTemplate== 'appy': template = 'frontPageAppy.pt'
        if fp == True:
            # We need a front page, but no specific one has been given.
            # So we will create a basic one that will simply display
            # some translated text.
            self.labels.append(PoMessage('front_page_text', '',
                                         PoMessage.FRONT_PAGE_TEXT))
            repls['pageContent'] = '<span tal:replace="structure python: ' \
                'tool.translateWithMapping(\'front_page_text\')"/>'
        else:
            # The user has specified a macro to show. So in the generated front
            # page, we will call this macro. The user will need to add itself
            # a .pt file containing this macro in the skins folder of the
            # generated Plone product.
            page, macro = fp.split('/')
            repls['pageContent'] = '<metal:call use-macro=' \
                                   '"context/%s/macros/%s"/>' % (page, macro)
        self.copyFile(template, repls, destFolder=self.skinsFolder,
                      destName='%sFrontPage.pt' % self.applicationName)

    def generateTool(self):
        '''Generates the Plone tool that corresponds to this application.'''
        Msg = PoMessage
        # Create Tool-related i18n-related messages
        msg = Msg(self.tool.name, '', Msg.CONFIG % self.applicationName)
        self.labels.append(msg)

        # Tune the Ref field between Tool and User
        Tool.users.klass = User
        if self.user.customized:
            Tool.users.klass = self.user.klass

        # Generate the Tool-related classes (User, Translation)
        for klass in (self.user, self.translation):
            klassType = klass.name[len(self.applicationName):]
            klass.generateSchema()
            self.labels += [ Msg(klass.name, '', klassType),
                             Msg('%s_plural' % klass.name,'', klass.name+'s')]
            repls = self.repls.copy()
            repls.update({'fields': klass.schema, 'methods': klass.methods,
              'genClassName': klass.name, 'imports': '','baseMixin':'BaseMixin',
              'baseSchema': 'BaseSchema', 'global_allow': 1,
              'parents': 'BaseMixin, BaseContent', 'static': '',
              'classDoc': 'User class for %s' % self.applicationName,
              'implements': "(getattr(BaseContent,'__implements__',()),)",
              'register': "registerType(%s, '%s')" % (klass.name,
                                                      self.applicationName)})
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
        repls.update({'fields': self.tool.schema, 'methods': self.tool.methods,
          'genClassName': self.tool.name, 'imports':'', 'baseMixin':'ToolMixin',
          'baseSchema': 'OrderedBaseFolderSchema', 'global_allow': 0,
          'parents': 'ToolMixin, UniqueObject, OrderedBaseFolder',
          'classDoc': 'Tool class for %s' % self.applicationName,
          'implements': "(getattr(UniqueObject,'__implements__',()),) + " \
                        "(getattr(OrderedBaseFolder,'__implements__',()),)",
          'register': "registerType(%s, '%s')" % (self.tool.name,
                                                  self.applicationName),
          'static': "left_slots = ['here/portlet_prefs/macros/portlet']\n    " \
                    "right_slots = []\n    " \
                    "def __init__(self, id=None):\n    " \
                    "    OrderedBaseFolder.__init__(self, '%s')\n    " \
                    "    self.setTitle('%s')\n" % (self.toolInstanceName,
                                                   self.applicationName)})
        self.copyFile('Class.py', repls, destName='%s.py' % self.tool.name)

    def generateClass(self, classDescr):
        '''Is called each time an Appy class is found in the application, for
           generating the corresponding Archetype class and schema.'''
        k = classDescr.klass
        print 'Generating %s.%s (gen-class)...' % (k.__module__, k.__name__)
        if not classDescr.isAbstract():
            self.tool.addWorkflowFields(classDescr)
        # Determine base archetypes schema and class
        baseClass = 'BaseContent'
        baseSchema = 'BaseSchema'
        if classDescr.isFolder():
            baseClass = 'OrderedBaseFolder'
            baseSchema = 'OrderedBaseFolderSchema'
        parents = ['BaseMixin', baseClass]
        imports = []
        implements = [baseClass]
        for baseClass in classDescr.klass.__bases__:
            if self.determineAppyType(baseClass) == 'class':
                bcName = getClassName(baseClass)
                parents.remove('BaseMixin')
                parents.insert(0, bcName)
                implements.append(bcName)
                imports.append('from %s import %s' % (bcName, bcName))
                baseSchema = '%s.schema' % bcName
                break
        parents = ','.join(parents)
        implements = '+'.join(['(getattr(%s,"__implements__",()),)' % i \
                               for i in implements])
        classDoc = classDescr.klass.__doc__
        if not classDoc:
            classDoc = 'Class generated with appy.gen.'
        # If the class is abstract I will not register it
        register = "registerType(%s, '%s')" % (classDescr.name,
                                               self.applicationName)
        if classDescr.isAbstract():
            register = ''
        repls = self.repls.copy()
        classDescr.generateSchema()
        repls.update({
          'imports': '\n'.join(imports), 'parents': parents,
          'className': classDescr.klass.__name__, 'global_allow': 1,
          'genClassName': classDescr.name, 'baseMixin':'BaseMixin',
          'classDoc': classDoc, 'applicationName': self.applicationName,
          'fields': classDescr.schema, 'methods': classDescr.methods,
          'implements': implements, 'baseSchema': baseSchema, 'static': '',
          'register': register, 'toolInstanceName': self.toolInstanceName})
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
        # Generate the resulting Archetypes class and schema.
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
