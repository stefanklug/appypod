'''This file contains the main Generator class used for generating a
   Plone 2.5-compliant product.'''

# ------------------------------------------------------------------------------
import os, os.path, re, sys
import appy.gen
from appy.gen import *
from appy.gen.po import PoMessage, PoFile, PoParser
from appy.gen.generator import Generator as AbstractGenerator
from model import ModelClass, PodTemplate, Flavour, Tool
from descriptors import ArchetypeFieldDescriptor, ArchetypesClassDescriptor, \
                        WorkflowDescriptor, ToolClassDescriptor, \
                        FlavourClassDescriptor, PodTemplateClassDescriptor, \
                        CustomToolClassDescriptor, CustomFlavourClassDescriptor

# Common methods that need to be defined on every Archetype class --------------
COMMON_METHODS = '''
    def getTool(self): return self.%s
    def getProductConfig(self): return Products.%s.config
'''
# ------------------------------------------------------------------------------
class Generator(AbstractGenerator):
    '''This generator generates a Plone 2.5-compliant product from a given
       appy application.'''
    poExtensions = ('.po', '.pot')

    def __init__(self, *args, **kwargs):
        Flavour._appy_clean()
        AbstractGenerator.__init__(self, *args, **kwargs)
        # i18n labels to generate
        self.labels = [] # i18n labels
        self.toolName = '%sTool' % self.applicationName
        self.flavourName = '%sFlavour' % self.applicationName
        self.toolInstanceName = 'portal_%s' % self.applicationName.lower()
        self.podTemplateName = '%sPodTemplate' % self.applicationName
        self.portletName = '%s_portlet' % self.applicationName.lower()
        self.queryName = '%s_query' % self.applicationName.lower()
        self.skinsFolder = 'skins/%s' % self.applicationName
        # The following dict, pre-filled in the abstract generator, contains a
        # series of replacements that need to be applied to file templates to
        # generate files.
        commonMethods = COMMON_METHODS % \
                        (self.toolInstanceName, self.applicationName)
        self.repls.update(
            {'toolName': self.toolName, 'flavourName': self.flavourName,
             'portletName': self.portletName, 'queryName': self.queryName,
             'toolInstanceName': self.toolInstanceName,
             'podTemplateName': self.podTemplateName,
             'commonMethods': commonMethods})
        # Predefined class descriptors
        self.toolDescr = ToolClassDescriptor(Tool, self)
        self.flavourDescr = FlavourClassDescriptor(Flavour, self)
        self.podTemplateDescr = PodTemplateClassDescriptor(PodTemplate,self)
        self.referers = {}

    versionRex = re.compile('(.*?\s+build)\s+(\d+)')
    def initialize(self):
        # Use customized class descriptors
        self.classDescriptor = ArchetypesClassDescriptor
        self.workflowDescriptor = WorkflowDescriptor
        self.customToolClassDescriptor = CustomToolClassDescriptor
        self.customFlavourClassDescriptor = CustomFlavourClassDescriptor
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
            msg('workflow_state', '', msg.WORKFLOW_STATE),
            msg('phase', '', msg.PHASE),
            msg('root_type', '', msg.ROOT_TYPE),
            msg('workflow_comment', '', msg.WORKFLOW_COMMENT),
            msg('choose_a_value', '', msg.CHOOSE_A_VALUE),
            msg('choose_a_doc', '', msg.CHOOSE_A_DOC),
            msg('min_ref_violated', '', msg.MIN_REF_VIOLATED),
            msg('max_ref_violated', '', msg.MAX_REF_VIOLATED),
            msg('no_ref', '', msg.REF_NO),
            msg('add_ref', '', msg.REF_ADD),
            msg('ref_name', '', msg.REF_NAME),
            msg('ref_actions', '', msg.REF_ACTIONS),
            msg('move_up', '', msg.REF_MOVE_UP),
            msg('move_down', '', msg.REF_MOVE_DOWN),
            msg('query_create', '', msg.QUERY_CREATE),
            msg('query_import', '', msg.QUERY_IMPORT),
            msg('query_no_result', '', msg.QUERY_NO_RESULT),
            msg('query_consult_all', '', msg.QUERY_CONSULT_ALL),
            msg('import_title', '', msg.IMPORT_TITLE),
            msg('import_show_hide', '', msg.IMPORT_SHOW_HIDE),
            msg('import_already', '', msg.IMPORT_ALREADY),
            msg('import_many', '', msg.IMPORT_MANY),
            msg('import_done', '', msg.IMPORT_DONE),
            msg('ref_invalid_index', '', msg.REF_INVALID_INDEX),
            msg('bad_int', '', msg.BAD_INT),
            msg('bad_float', '', msg.BAD_FLOAT),
            msg('bad_email', '', msg.BAD_EMAIL),
            msg('bad_url', '', msg.BAD_URL),
            msg('bad_alphanumeric', '', msg.BAD_ALPHANUMERIC),
            msg('select_delesect', '', msg.SELECT_DESELECT),
            msg('no_elem_selected', '', msg.NO_SELECTION),
            msg('delete_confirm', '', msg.DELETE_CONFIRM),
            msg('delete_done', '', msg.DELETE_DONE),
            msg('goto_first', '', msg.GOTO_FIRST),
            msg('goto_previous', '', msg.GOTO_PREVIOUS),
            msg('goto_next', '', msg.GOTO_NEXT),
            msg('goto_last', '', msg.GOTO_LAST),
        ]
        # Create basic files (config.py, Install.py, etc)
        self.generateTool()
        self.generateConfig()
        self.generateInit()
        self.generateInstall()
        self.generateWorkflows()
        self.generateWrappers()
        self.generateTests()
        if self.config.frontPage == True:
            self.labels.append(msg('front_page_text', '', msg.FRONT_PAGE_TEXT))
            self.copyFile('frontPage.pt', self.repls,
                          destFolder=self.skinsFolder,
                          destName='%sFrontPage.pt' % self.applicationName)
        self.copyFile('configure.zcml', self.repls)
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
        removedLabels = potFile.update(self.labels, self.options.i18nClean,
                                       not self.options.i18nSort)
        if removedLabels:
            print 'Warning: %d messages were removed from translation ' \
                  'files: %s' % (len(removedLabels), str(removedLabels))
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
        # Generate i18n po files for other potential files
        for poFile in self.i18nFiles.itervalues():
            if not poFile.generated:
                poFile.generate()

    ploneRoles = ('Manager', 'Member', 'Owner', 'Reviewer')
    def getAllUsedRoles(self, appOnly=False):
        '''Produces a list of all the roles used within all workflows defined
           in this application. If p_appOnly is True, it returns only roles
           which are specific to this application (ie it removes predefined
           Plone roles like Member, Manager, etc.'''
        res = []
        for wfDescr in self.workflows:
            # Browse states and transitions
            for attr in dir(wfDescr.klass):
                attrValue = getattr(wfDescr.klass, attr)
                if isinstance(attrValue, State) or \
                   isinstance(attrValue, Transition):
                    res += attrValue.getUsedRoles()
        res = list(set(res))
        if appOnly:
            for ploneRole in self.ploneRoles:
                if ploneRole in res:
                    res.remove(ploneRole)
        return res

    def addReferer(self, fieldDescr, relationship):
        '''p_fieldDescr is a Ref type definition. We will create in config.py a
           dict that lists all back references, by type.'''
        k = fieldDescr.appyType.klass
        if issubclass(k, ModelClass):
            refClassName = self.applicationName + k.__name__
        elif issubclass(k, appy.gen.Tool):
            refClassName = '%sTool' % self.applicationName
        elif issubclass(k, appy.gen.Flavour):
            refClassName = '%sFlavour' % self.applicationName
        else:
            refClassName = ArchetypesClassDescriptor.getClassName(k)
        if not self.referers.has_key(refClassName):
            self.referers[refClassName] = []
        self.referers[refClassName].append( (fieldDescr, relationship))

    def generateConfig(self):
        # Compute referers
        referers = ''
        for className, refInfo in self.referers.iteritems():
            referers += '"%s":[' % className
            for fieldDescr, relationship in refInfo:
                refClass = fieldDescr.classDescr.klass
                if issubclass(refClass, ModelClass):
                    refClassName = 'Extensions.appyWrappers.%s' % \
                                   refClass.__name__
                else:
                    refClassName = '%s.%s' % (refClass.__module__,
                                              refClass.__name__)
                referers += '(%s.%s' % (refClassName, fieldDescr.fieldName)
                referers += ',"%s"' % relationship
                referers += '),'
            referers += '],\n'
        # Compute workflow instances initialisation
        wfInit = ''
        for workflowDescr in self.workflows:
            k = workflowDescr.klass
            className = '%s.%s' % (k.__module__, k.__name__)
            wfInit += 'wf = %s()\n' % className
            wfInit += 'wf._transitionsMapping = {}\n'
            for transition in workflowDescr.getTransitions():
                tName = workflowDescr.getNameOf(transition)
                tNames = workflowDescr.getTransitionNamesOf(tName, transition)
                for trName in tNames:
                    wfInit += 'wf._transitionsMapping["%s"] = wf.%s\n' % \
                              (trName, tName)
            # We need a new attribute that stores states in order
            wfInit += 'wf._states = []\n'
            for stateName in workflowDescr.getStateNames(ordered=True):
                wfInit += 'wf._states.append("%s")\n' % stateName
            wfInit += 'workflowInstances[%s] = wf\n' % className
        # Compute imports
        imports = ['import %s' % self.applicationName]
        classDescrs = self.classes[:]
        if self.customToolDescr:
            classDescrs.append(self.customToolDescr)
        if self.customFlavourDescr:
            classDescrs.append(self.customFlavourDescr)
        for classDescr in (classDescrs + self.workflows):
            theImport = 'import %s' % classDescr.klass.__module__
            if theImport not in imports:
                imports.append(theImport)
        # Compute root classes
        rootClasses = ''
        for classDescr in self.classes:
            if classDescr.isRoot():
                rootClasses += "'%s'," % classDescr.name
        # Compute list of add permissions
        addPermissions = ''
        for classDescr in self.classes:
            addPermissions += '    "%s":"%s: Add %s",\n' % (classDescr.name,
                self.applicationName, classDescr.name)
        repls = self.repls.copy()
        # Compute list of used roles for registering them if needed
        repls['roles'] = ','.join(['"%s"' % r for r in \
                                  self.getAllUsedRoles(appOnly=True)])
        repls['rootClasses'] = rootClasses
        repls['referers'] = referers
        repls['workflowInstancesInit'] = wfInit
        repls['imports'] = '\n'.join(imports)
        repls['defaultAddRoles'] = ','.join(
            ['"%s"' % r for r in self.config.defaultCreators])
        repls['addPermissions'] = addPermissions
        self.copyFile('config.py', repls)

    def generateInit(self):
        # Compute imports
        imports = ['    import %s' % self.toolName,
                   '    import %s' % self.flavourName,
                   '    import %s' % self.podTemplateName]
        for c in self.classes:
            importDef = '    import %s' % c.name
            if importDef not in imports:
                imports.append(importDef)
        repls = self.repls.copy()
        repls['imports'] = '\n'.join(imports)
        self.copyFile('__init__.py', repls)

    def generateInstall(self):
        # Compute lists of class names
        allClassNames = '"%s",' % self.flavourName
        allClassNames += '"%s",' % self.podTemplateName
        appClassNames = ','.join(['"%s"' % c.name for c in self.classes])
        allClassNames += appClassNames
        # Compute imports
        imports = []
        for classDescr in self.classes:
            theImport = 'import %s' % classDescr.klass.__module__
            if theImport not in imports:
                imports.append(theImport)
        # Compute list of application classes
        appClasses = []
        for classDescr in self.classes:
            k = classDescr.klass
            appClasses.append('%s.%s' % (k.__module__, k.__name__))
        # Compute classes whose instances must not be catalogued.
        catalogMap = ''
        blackClasses = [self.toolName, self.flavourName, self.podTemplateName]
        for blackClass in blackClasses:
            catalogMap += "catalogMap['%s'] = {}\n" % blackClass
            catalogMap += "catalogMap['%s']['black'] = " \
                          "['portal_catalog']\n" % blackClass
        # Compute workflows
        workflows = ''
        allClasses = self.classes[:]
        if self.customToolDescr:
            allClasses.append(self.customToolDescr)
        if self.customFlavourDescr:
            allClasses.append(self.customFlavourDescr)
        for classDescr in allClasses:
            if hasattr(classDescr.klass, 'workflow'):
                wfName = WorkflowDescriptor.getWorkflowName(
                    classDescr.klass.workflow)
                workflows += '\n    "%s":"%s",' % (classDescr.name, wfName)
        # Generate the resulting file.
        repls = self.repls.copy()
        repls['allClassNames'] = allClassNames
        repls['appClassNames'] = appClassNames
        repls['catalogMap'] = catalogMap
        repls['imports'] = '\n'.join(imports)
        repls['appClasses'] = "[%s]" % ','.join(appClasses)
        repls['minimalistPlone'] = self.config.minimalistPlone
        repls['showPortlet'] = self.config.showPortlet
        repls['appFrontPage'] = self.config.frontPage == True
        repls['workflows'] = workflows
        self.copyFile('Install.py', repls, destFolder='Extensions')

    def generateWorkflows(self):
        '''Generates the file that contains one function by workflow.
           Those functions are called by Plone for registering the workflows.'''
        workflows = ''
        for wfDescr in self.workflows:
            # Compute state names & info, transition names & infos, managed
            # permissions
            stateNames=','.join(['"%s"' % sn for sn in wfDescr.getStateNames()])
            stateInfos = wfDescr.getStatesInfo(asDumpableCode=True)
            transitionNames = ','.join(['"%s"' % tn for tn in \
                                        wfDescr.getTransitionNames()])
            transitionInfos = wfDescr.getTransitionsInfo(asDumpableCode=True)
            managedPermissions = ','.join(['"%s"' % tn for tn in \
                                          wfDescr.getManagedPermissions()])
            wfName = WorkflowDescriptor.getWorkflowName(wfDescr.klass)
            workflows += '%s\ndef create_%s(self, id):\n    ' \
                'stateNames = [%s]\n    ' \
                'stateInfos = %s\n    ' \
                'transitionNames = [%s]\n    ' \
                'transitionInfos = %s\n    ' \
                'managedPermissions = [%s]\n    ' \
                'return WorkflowCreator("%s", DCWorkflowDefinition, ' \
                'stateNames, "%s", stateInfos, transitionNames, ' \
                'transitionInfos, managedPermissions, PROJECTNAME, ' \
                'ExternalMethod).run()\n' \
                'addWorkflowFactory(create_%s,\n    id="%s",\n    ' \
                'title="%s")\n\n' % (wfDescr.getScripts(), wfName, stateNames,
                stateInfos, transitionNames, transitionInfos,
                managedPermissions, wfName, wfDescr.getInitialStateName(),
                wfName, wfName, wfName)
        repls = self.repls.copy()
        repls['workflows'] = workflows
        self.copyFile('workflows.py', repls, destFolder='Extensions')

    def generateWrapperProperty(self, attrName, appyType):
        '''Generates the getter for attribute p_attrName having type
           p_appyType.'''
        res = '    def get_%s(self):\n' % attrName
        blanks = ' '*8
        getterName = 'get%s%s' % (attrName[0].upper(), attrName[1:])
        if isinstance(appyType, Ref):
            res += blanks + 'return self.o._appy_getRefs("%s", ' \
                   'noListIfSingleObj=True).objects\n' % attrName
        elif isinstance(appyType, Computed):
            res += blanks + 'appyType = getattr(self.klass, "%s")\n' % attrName
            res += blanks + 'return self.o.getComputedValue(' \
                            'appyType.__dict__)\n'
        elif isinstance(appyType, File):
            res += blanks + 'v = self.o.%s()\n' % getterName
            res += blanks + 'if not v: return None\n'
            res += blanks + 'else: return FileWrapper(v)\n'
        elif isinstance(appyType, String) and appyType.isMultiValued():
            res += blanks + 'return list(self.o.%s())\n' % getterName
        else:
            if attrName in ArchetypeFieldDescriptor.specialParams:
                getterName = attrName.capitalize()
            res += blanks + 'return self.o.%s()\n' % getterName
        res += '    %s = property(get_%s)\n\n' % (attrName, attrName)
        return res

    def generateWrapperPropertyBack(self, attrName, rel):
        '''Generates a wrapper property for accessing the back reference named
           p_attrName through Archetypes relationship p_rel.'''
        res = '    def get_%s(self):\n' % attrName
        blanks = ' '*8
        res += blanks + 'return self.o._appy_getRefsBack("%s", "%s", ' \
                   'noListIfSingleObj=True)\n' % (attrName, rel)
        res += '    %s = property(get_%s)\n\n' % (attrName, attrName)
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
        allClasses = self.classes[:]
        # Add predefined classes (Tool, Flavour, PodTemplate)
        allClasses += [self.toolDescr, self.flavourDescr, self.podTemplateDescr]
        if self.customToolDescr:
            allClasses.append(self.customToolDescr)
        if self.customFlavourDescr:
            allClasses.append(self.customFlavourDescr)
        for c in self.getClassesInOrder(allClasses):
            if not c.predefined:
                moduleImport = 'import %s' % c.klass.__module__
                if moduleImport not in imports:
                    imports.append(moduleImport)
            # Determine parent wrapper and class
            parentWrapper = 'AbstractWrapper'
            parentClass = '%s.%s' % (c.klass.__module__, c.klass.__name__)
            if c.predefined:
                parentClass = c.klass.__name__
            if c.klass.__bases__:
                baseClassName = c.klass.__bases__[0].__name__
                for k in allClasses:
                    if k.klass.__name__ == baseClassName:
                        parentWrapper = '%s_Wrapper' % k.name
            wrapperDef = 'class %s_Wrapper(%s, %s):\n' % \
                         (c.name, parentWrapper, parentClass)
            wrapperDef += '    security = ClassSecurityInfo()\n'
            titleFound = False
            for attrName in c.orderedAttributes:
                if attrName == 'title':
                    titleFound = True
                attrValue = getattr(c.klass, attrName)
                if isinstance(attrValue, Type):
                    wrapperDef += self.generateWrapperProperty(attrName,
                                                               attrValue)
            # Generate properties for back references
            if self.referers.has_key(c.name):
                for refDescr, rel in self.referers[c.name]:
                    attrName = refDescr.appyType.back.attribute
                    wrapperDef += self.generateWrapperPropertyBack(attrName,rel)
            if not titleFound:
                # Implicitly, the title will be added by Archetypes. So I need
                # to define a property for it.
                wrapperDef += self.generateWrapperProperty('title', String())
            if isinstance(c, CustomToolClassDescriptor) or \
               isinstance(c, CustomFlavourClassDescriptor):
                # For custom tool and flavour, add a call to a method that
                # allows to customize elements from the base class.
                wrapperDef += "    if hasattr(%s, 'update'):\n        " \
                    "%s.update(%s.__bases__[1])\n" % (
                    parentClass, parentClass, parentWrapper)
                # For custom tool and flavour, add security declaration that
                # will allow to call their methods from ZPTs.
                wrapperDef += "    for elem in dir(%s):\n        " \
                    "if not elem.startswith('_'): security.declarePublic" \
                    "(elem)\n" % (parentClass)
            # Register the class in Zope.
            wrapperDef += 'InitializeClass(%s_Wrapper)\n' % c.name
            wrappers.append(wrapperDef)
        repls = self.repls.copy()
        repls['imports'] = '\n'.join(imports)
        repls['wrappers'] = '\n'.join(wrappers)
        repls['toolBody'] = Tool._appy_getBody()
        repls['flavourBody'] = Flavour._appy_getBody()
        repls['podTemplateBody'] = PodTemplate._appy_getBody()
        self.copyFile('appyWrappers.py', repls, destFolder='Extensions')

    def generateTests(self):
        '''Generates the file needed for executing tests.'''
        repls = self.repls.copy()
        modules = self.modulesWithTests
        repls['imports'] = '\n'.join(['import %s' % m for m in modules])
        repls['modulesWithTests'] = ','.join(modules)
        self.copyFile('testAll.py', repls, destFolder='tests')

    def generateTool(self):
        '''Generates the Plone tool that corresponds to this application.'''
        # Generate the tool class in itself and related i18n messages
        t = self.toolName
        Msg = PoMessage
        repls = self.repls.copy()
        # Manage predefined fields
        Tool.flavours.klass = Flavour
        if self.customFlavourDescr:
            Tool.flavours.klass = self.customFlavourDescr.klass
        self.toolDescr.generateSchema()
        repls['predefinedFields'] = self.toolDescr.schema
        repls['predefinedMethods'] = self.toolDescr.methods
        # Manage custom fields
        repls['fields'] = ''
        repls['methods'] = ''
        repls['wrapperClass'] = '%s_Wrapper' % self.toolDescr.name
        if self.customToolDescr:
            repls['fields'] = self.customToolDescr.schema
            repls['methods'] = self.customToolDescr.methods
            wrapperClass = '%s_Wrapper' % self.customToolDescr.name
            repls['wrapperClass'] = wrapperClass
        self.copyFile('ToolTemplate.py', repls, destName='%s.py'% self.toolName)
        repls = self.repls.copy()
        # Create i18n-related messages
        self.labels += [
            Msg(self.toolName, '', Msg.CONFIG % self.applicationName),
            Msg('%s_edit_descr' % self.toolName, '', ' ')]
        # Before generating the Flavour class, finalize it with query result
        # columns, with fields to propagate, workflow-related fields.
        for classDescr in self.classes:
            for fieldName, fieldType in classDescr.flavourFieldsToPropagate:
                for childDescr in classDescr.getChildren():
                    childFieldName = fieldName % childDescr.name
                    fieldType.group = childDescr.klass.__name__
                    Flavour._appy_addField(childFieldName,fieldType,childDescr)
            if classDescr.isRoot():
                # We must be able to configure query results from the
                # flavour.
                Flavour._appy_addQueryResultColumns(classDescr)
        Flavour._appy_addWorkflowFields(self.flavourDescr)
        Flavour._appy_addWorkflowFields(self.podTemplateDescr)
        # Generate the flavour class and related i18n messages
        self.flavourDescr.generateSchema()
        self.labels += [ Msg(self.flavourName, '', Msg.FLAVOUR),
                         Msg('%s_edit_descr' % self.flavourName, '', ' ')]
        repls = self.repls.copy()
        repls['predefinedFields'] = self.flavourDescr.schema
        repls['predefinedMethods'] = self.flavourDescr.methods
        # Manage custom fields
        repls['fields'] = ''
        repls['methods'] = ''
        repls['wrapperClass'] = '%s_Wrapper' % self.flavourDescr.name
        if self.customFlavourDescr:
            repls['fields'] = self.customFlavourDescr.schema
            repls['methods'] = self.customFlavourDescr.methods
            wrapperClass = '%s_Wrapper' % self.customFlavourDescr.name
            repls['wrapperClass'] = wrapperClass
        repls['metaTypes'] = [c.name for c in self.classes]
        self.copyFile('FlavourTemplate.py', repls,
                      destName='%s.py'% self.flavourName)
        # Generate the PodTemplate class
        self.podTemplateDescr.generateSchema()
        self.labels += [ Msg(self.podTemplateName, '', Msg.POD_TEMPLATE),
                         Msg('%s_edit_descr' % self.podTemplateName, '', ' ')]
        repls = self.repls.copy()
        repls['fields'] = self.podTemplateDescr.schema
        repls['methods'] = self.podTemplateDescr.methods
        repls['wrapperClass'] = '%s_Wrapper' % self.podTemplateDescr.name
        self.copyFile('PodTemplate.py', repls,
                        destName='%s.py' % self.podTemplateName)

    def generateClass(self, classDescr):
        '''Is called each time an Appy class is found in the application, for
           generating the corresponding Archetype class and schema.'''
        k = classDescr.klass
        print 'Generating %s.%s (gen-class)...' % (k.__module__, k.__name__)
        # Add, for this class, the needed configuration attributes on Flavour
        if classDescr.isPod():
            Flavour._appy_addPodField(classDescr)
        if not classDescr.isAbstract():
            Flavour._appy_addWorkflowFields(classDescr)
        # Determine base archetypes schema and class
        baseClass = 'BaseContent'
        baseSchema = 'BaseSchema'
        if classDescr.isFolder():
            baseClass = 'OrderedBaseFolder'
            baseSchema = 'OrderedBaseFolderSchema'
        parents = [baseClass, 'ClassMixin']
        imports = []
        implements = [baseClass]
        for baseClass in classDescr.klass.__bases__:
            if self.determineAppyType(baseClass) == 'class':
                bcName = ArchetypesClassDescriptor.getClassName(baseClass)
                parents.remove('ClassMixin')
                parents.append(bcName)
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
        classDescr.addGenerateDocMethod() # For POD
        repls = self.repls.copy()
        repls.update({
          'imports': '\n'.join(imports), 'parents': parents,
          'className': classDescr.klass.__name__,
          'genClassName': classDescr.name,
          'classDoc': classDoc, 'applicationName': self.applicationName,
          'fields': classDescr.schema, 'methods': classDescr.methods,
          'implements': implements, 'baseSchema': baseSchema,
          'register': register, 'toolInstanceName': self.toolInstanceName})
        fileName = '%s.py' % classDescr.name
        # Create i18n labels (class name, description and plural form)
        poMsg = PoMessage(classDescr.name, '', classDescr.klass.__name__)
        poMsg.produceNiceDefault()
        self.labels.append(poMsg)
        poMsgDescr = PoMessage('%s_edit_descr' % classDescr.name, '', ' ')
        self.labels.append(poMsgDescr)
        poMsgPl = PoMessage('%s_plural' % classDescr.name, '',
            classDescr.klass.__name__+'s')
        poMsgPl.produceNiceDefault()
        self.labels.append(poMsgPl)
        # Create i18n labels for flavoured variants
        for i in range(2, self.config.numberOfFlavours+1):
            poMsg = PoMessage('%s_%d' % (classDescr.name, i), '',
                              classDescr.klass.__name__)
            poMsg.produceNiceDefault()
            self.labels.append(poMsg)
            poMsgDescr = PoMessage('%s_%d_edit_descr' % (classDescr.name, i),
                                   '', ' ')
            self.labels.append(poMsgDescr)
            poMsgPl = PoMessage('%s_%d_plural' % (classDescr.name, i), '',
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
        self.copyFile('ArchetypesTemplate.py', repls, destName=fileName)

    def generateWorkflow(self, wfDescr):
        '''This method does not generate the workflow definition, which is done
           in self.generateWorkflows. This method just creates the i18n labels
           related to the workflow described by p_wfDescr.'''
        k = wfDescr.klass
        print 'Generating %s.%s (gen-workflow)...' % (k.__module__, k.__name__)
        # Identify Plone workflow name
        wfName = WorkflowDescriptor.getWorkflowName(wfDescr.klass)
        # Add i18n messages for states and transitions
        for sName in wfDescr.getStateNames():
            poMsg = PoMessage('%s_%s' % (wfName, sName), '', sName)
            poMsg.produceNiceDefault()
            self.labels.append(poMsg)
        for tName, tLabel in wfDescr.getTransitionNames(withLabels=True):
            poMsg = PoMessage('%s_%s' % (wfName, tName), '', tLabel)
            poMsg.produceNiceDefault()
            self.labels.append(poMsg)
        for transition in wfDescr.getTransitions():
            if transition.notify:
                # Appy will send a mail when this transition is triggered.
                # So we need 2 i18n labels for every DC transition corresponding
                # to this Appy transition: one for the mail subject and one for
                # the mail body.
                tName = wfDescr.getNameOf(transition) # Appy name
                tNames = wfDescr.getTransitionNamesOf(tName, transition) # DC
                # name(s)
                for tn in tNames:
                    subjectLabel = '%s_%s_mail_subject' % (wfName, tn)
                    poMsg = PoMessage(subjectLabel, '', PoMessage.EMAIL_SUBJECT)
                    self.labels.append(poMsg)
                    bodyLabel = '%s_%s_mail_body' % (wfName, tn)
                    poMsg = PoMessage(bodyLabel, '', PoMessage.EMAIL_BODY)
                    self.labels.append(poMsg)
# ------------------------------------------------------------------------------
