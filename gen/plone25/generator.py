'''This file contains the main Generator class used for generating a
   Plone 2.5-compliant product.'''

# ------------------------------------------------------------------------------
import os, os.path, re, sys
import appy.gen
from appy.gen import *
from appy.gen.po import PoMessage, PoFile, PoParser
from appy.gen.generator import Generator as AbstractGenerator
from model import ModelClass, PodTemplate, Flavour, Tool
from descriptors import FieldDescriptor, ClassDescriptor, \
                        WorkflowDescriptor, ToolClassDescriptor, \
                        FlavourClassDescriptor, PodTemplateClassDescriptor

# Common methods that need to be defined on every Archetype class --------------
COMMON_METHODS = '''
    def getTool(self): return self.%s
    def getProductConfig(self): return Products.%s.config
    def skynView(self):
       """Redirects to skyn/view."""
       return self.REQUEST.RESPONSE.redirect(self.getUrl())
'''
# ------------------------------------------------------------------------------
class Generator(AbstractGenerator):
    '''This generator generates a Plone 2.5-compliant product from a given
       appy application.'''
    poExtensions = ('.po', '.pot')

    def __init__(self, *args, **kwargs):
        Flavour._appy_clean()
        AbstractGenerator.__init__(self, *args, **kwargs)
        # Set our own Descriptor classes
        self.descriptorClasses['class'] = ClassDescriptor
        self.descriptorClasses['workflow']  = WorkflowDescriptor
        # Create our own Tool, Flavour and PodTemplate instances
        self.tool = ToolClassDescriptor(Tool, self)
        self.flavour = FlavourClassDescriptor(Flavour, self)
        self.podTemplate = PodTemplateClassDescriptor(PodTemplate, self)
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
            msg('ref_name',             '', msg.REF_NAME),
            msg('ref_actions',          '', msg.REF_ACTIONS),
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
            msg('confirm',              '', msg.CONFIRM),
            msg('yes',                  '', msg.YES),
            msg('no',                   '', msg.NO),
            msg('field_required',       '', msg.FIELD_REQUIRED),
            msg('file_required',        '', msg.FILE_REQUIRED),
            msg('image_required',       '', msg.IMAGE_REQUIRED),
        ]
        # Create a label for every role added by this application
        for role in self.getAllUsedRoles(appOnly=True):
            self.labels.append(msg('role_%s' % role,'', role, niceDefault=True))
        # Create basic files (config.py, Install.py, etc)
        self.generateTool()
        self.generateConfig()
        self.generateInit()
        self.generateInstall()
        self.generateWorkflows()
        self.generateWrappers()
        self.generateTests()
        if self.config.frontPage:
            self.generateFrontPage()
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

    ploneRoles = ('Manager', 'Member', 'Owner', 'Reviewer', 'Anonymous')
    def getAllUsedRoles(self, appOnly=False):
        '''Produces a list of all the roles used within all workflows and
           classes defined in this application. If p_appOnly is True, it
           returns only roles which are specific to this application (ie it
           removes predefined Plone roles like Member, Manager, etc.'''
        res = []
        for wfDescr in self.workflows:
            # Browse states and transitions
            for attr in dir(wfDescr.klass):
                attrValue = getattr(wfDescr.klass, attr)
                if isinstance(attrValue, State) or \
                   isinstance(attrValue, Transition):
                    res += attrValue.getUsedRoles()
        for cDescr in self.getClasses(include='all'):
            res += cDescr.getCreators()
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
            refClassName = ClassDescriptor.getClassName(k)
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

    def generateConfig(self):
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
        classDescrs = self.getClasses(include='custom')
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
        # Compute the list of ordered attributes (foward and backward, inherited
        # included) for every Appy class.
        attributes = []
        attributesDict = []
        for classDescr in self.getClasses(include='all'):
            titleFound = False
            attrs = []
            attrNames = []
            for name, appyType, klass in classDescr.getOrderedAppyAttributes():
                attrs.append(self.getAppyTypePath(name, appyType, klass))
                attrNames.append(name)
                if name == 'title': titleFound = True
            # Add the "title" mandatory field if not found
            if not titleFound:
                attrs.insert(0, 'copy.deepcopy(appy.gen.title)')
                attrNames.insert(0, 'title')
            # Any backward attributes to append?
            if classDescr.name in self.referers:
                for field, rel in self.referers[classDescr.name]:
                    try:
                        getattr(field.classDescr.klass, field.fieldName)
                        klass = field.classDescr.klass
                    except AttributeError:
                        klass = field.classDescr.modelClass
                    attrs.append(self.getAppyTypePath(field.fieldName,
                        field.appyType, klass, isBack=True))
                    attrNames.append(field.appyType.back.attribute)
            attributes.append('"%s":[%s]' % (classDescr.name,','.join(attrs)))
            aDict = ''
            i = -1
            for attr in attrs:
                i += 1
                aDict += '"%s":attributes["%s"][%d],' % \
                         (attrNames[i], classDescr.name, i)
            attributesDict.append('"%s":{%s}' % (classDescr.name, aDict))
        # Compute list of used roles for registering them if needed
        repls['roles'] = ','.join(['"%s"' % r for r in \
                                  self.getAllUsedRoles(appOnly=True)])
        repls['rootClasses'] = rootClasses
        repls['workflowInstancesInit'] = wfInit
        repls['imports'] = '\n'.join(imports)
        repls['attributes'] = ',\n    '.join(attributes)
        repls['attributesDict'] = ',\n    '.join(attributesDict)
        repls['defaultAddRoles'] = ','.join(
            ['"%s"' % r for r in self.config.defaultCreators])
        repls['addPermissions'] = addPermissions
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
        for classDescr in self.getClasses(include='all'):
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
        repls['appFrontPage'] = bool(self.config.frontPage)
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

    def generateWrapperProperty(self, name):
        '''Generates the getter for attribute p_name.'''
        res = '    def get_%s(self):\n        ' % name
        if name == 'title':
            res += 'return self.o.Title()\n'
        else:
            res += 'return self.o.getAppyType("%s").getValue(self.o)\n' % name
        res += '    %s = property(get_%s)\n\n' % (name, name)
        return res

    def getClasses(self, include=None):
        '''Returns the descriptors for all the classes in the generated
           gen-application. If p_include is "all", it includes the descriptors
           for the config-related classes (tool, flavour, etc); if
           p_include is "custom", it includes descriptors for the
           config-related classes for which the user has created a sub-class.'''
        if not include: return self.classes
        else:
            res = self.classes[:]
            configClasses = [self.tool, self.flavour, self.podTemplate]
            if include == 'all':
                res += configClasses
            elif include == 'custom':
                res += [c for c in configClasses if c.customized]
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
            titleFound = False
            for attrName in c.orderedAttributes:
                if attrName == 'title':
                    titleFound = True
                try:
                    attrValue = getattr(c.klass, attrName)
                except AttributeError:
                    attrValue = getattr(c.modelClass, attrName)
                if isinstance(attrValue, Type):
                    wrapperDef += self.generateWrapperProperty(attrName)
            # Generate properties for back references
            if self.referers.has_key(c.name):
                for refDescr, rel in self.referers[c.name]:
                    attrName = refDescr.appyType.back.attribute
                    wrapperDef += self.generateWrapperProperty(attrName)
            if not titleFound:
                # Implicitly, the title will be added by Archetypes. So I need
                # to define a property for it.
                wrapperDef += self.generateWrapperProperty('title')
            if c.customized:
                # For custom tool and flavour, add a call to a method that
                # allows to customize elements from the base class.
                wrapperDef += "    if hasattr(%s, 'update'):\n        " \
                    "%s.update(%s)\n" % (parentClasses[1], parentClasses[1],
                                         parentClasses[0])
                # For custom tool and flavour, add security declaration that
                # will allow to call their methods from ZPTs.
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

    def generateFrontPage(self):
        fp = self.config.frontPage
        repls = self.repls.copy()
        if fp == True:
            # We need a front page, but no specific one has been given.
            # So we will create a basic one that will simply display
            # some translated text.
            self.labels.append(msg('front_page_text', '', msg.FRONT_PAGE_TEXT))
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
        self.copyFile('frontPage.pt', repls, destFolder=self.skinsFolder,
                      destName='%sFrontPage.pt' % self.applicationName)

    def generateTool(self):
        '''Generates the Plone tool that corresponds to this application.'''
        # Generate the tool class in itself and related i18n messages
        t = self.toolName
        Msg = PoMessage
        repls = self.repls.copy()
        # Manage predefined fields
        Tool.flavours.klass = Flavour
        if self.flavour.customized:
            Tool.flavours.klass = self.flavour.klass
        self.tool.generateSchema()
        repls['fields'] = self.tool.schema
        repls['methods'] = self.tool.methods
        repls['wrapperClass'] = '%s_Wrapper' % self.tool.name
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
                # We must be able to configure query results from the flavour.
                Flavour._appy_addQueryResultColumns(classDescr)
                # Add the search-related fields.
                Flavour._appy_addSearchRelatedFields(classDescr)
                importMean = classDescr.getCreateMean('Import')
                if importMean:
                    Flavour._appy_addImportRelatedFields(classDescr)
        Flavour._appy_addWorkflowFields(self.flavour)
        Flavour._appy_addWorkflowFields(self.podTemplate)
        # Complete self.flavour.orderedAttributes from the attributes that we
        # just added to the Flavour model class.
        for fieldName in Flavour._appy_attributes:
            if fieldName not in self.flavour.orderedAttributes:
                self.flavour.orderedAttributes.append(fieldName)
        # Generate the flavour class and related i18n messages
        self.flavour.generateSchema()
        self.labels += [ Msg(self.flavourName, '', Msg.FLAVOUR),
                         Msg('%s_edit_descr' % self.flavourName, '', ' ')]
        repls = self.repls.copy()
        repls['fields'] = self.flavour.schema
        repls['methods'] = self.flavour.methods
        repls['wrapperClass'] = '%s_Wrapper' % self.flavour.name
        repls['metaTypes'] = [c.name for c in self.classes]
        self.copyFile('FlavourTemplate.py', repls,
                      destName='%s.py'% self.flavourName)
        # Generate the PodTemplate class
        self.podTemplate.generateSchema()
        self.labels += [ Msg(self.podTemplateName, '', Msg.POD_TEMPLATE),
                         Msg('%s_edit_descr' % self.podTemplateName, '', ' ')]
        repls = self.repls.copy()
        repls['fields'] = self.podTemplate.schema
        repls['methods'] = self.podTemplate.methods
        repls['wrapperClass'] = '%s_Wrapper' % self.podTemplate.name
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
                bcName = ClassDescriptor.getClassName(baseClass)
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
        repls = self.repls.copy()
        classDescr.generateSchema()
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
