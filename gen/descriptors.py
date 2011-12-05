'''Descriptor classes defined in this file are "intermediary" classes that
   gather, from the user application, information about found gen- or workflow-
   classes.'''

# ------------------------------------------------------------------------------
import types, copy
import appy.gen as gen
from po import PoMessage
from model import ModelClass, toolFieldPrefixes
from utils import produceNiceMessage, getClassName
TABS = 4 # Number of blanks in a Python indentation.

# ------------------------------------------------------------------------------
class Descriptor: # Abstract
    def __init__(self, klass, orderedAttributes, generator):
        # The corresponding Python class
        self.klass = klass
        # The names of the static appy-compliant attributes declared in
        # self.klass
        self.orderedAttributes = orderedAttributes
        # A reference to the code generator.
        self.generator = generator

    def __repr__(self): return '<Class %s>' % self.klass.__name__

class ClassDescriptor(Descriptor):
    '''This class gives information about an Appy class.'''

    def __init__(self, klass, orderedAttributes, generator):
        Descriptor.__init__(self, klass, orderedAttributes, generator)
        self.methods = '' # Needed method definitions will be generated here
        # We remember here encountered pages and groups defined in the Appy
        # type. Indeed, after having parsed all application classes, we will
        # need to generate i18n labels for every child class of the class
        # that declared pages and groups.
        self.labelsToPropagate = [] #~[PoMessage]~ Some labels (like page,
        # group or action names) need to be propagated in children classes
        # (because they contain the class name). But at this time we don't know
        # yet every sub-class. So we store those labels here; the Generator
        # will propagate them later.
        self.toolFieldsToPropagate = [] # For this class, some fields have
        # been defined on the Tool class. Those fields need to be defined
        # for child classes of this class as well, but at this time we don't
        # know yet every sub-class. So we store field definitions here; the
        # Generator will propagate them later.
        self.name = getClassName(self.klass, generator.applicationName)
        self.predefined = False
        self.customized = False
        # Phase and page names will be calculated later, when first required.
        self.phases = None
        self.pages = None

    def getOrderedAppyAttributes(self, condition=None):
        '''Returns the appy types for all attributes of this class and parent
           class(es). If a p_condition is specified, ony Appy types matching
           the condition will be returned. p_condition must be a string
           containing an expression that will be evaluated with, in its context,
           "self" being this ClassDescriptor and "attrValue" being the current
           Type instance.
           
           Order of returned attributes already takes into account type's
           "move" attributes.'''
        attrs = []
        # First, get the attributes for the current class
        for attrName in self.orderedAttributes:
            try:
                attrValue = getattr(self.klass, attrName)
                hookClass = self.klass
            except AttributeError:
                attrValue = getattr(self.modelClass, attrName)
                hookClass = self.modelClass
            if isinstance(attrValue, gen.Type):
                if not condition or eval(condition):
                    attrs.append( (attrName, attrValue, hookClass) )
        # Then, add attributes from parent classes
        for baseClass in self.klass.__bases__:
            # Find the classDescr that corresponds to baseClass
            baseClassDescr = None
            for classDescr in self.generator.classes:
                if classDescr.klass == baseClass:
                    baseClassDescr = classDescr
                    break
            if baseClassDescr:
                attrs = baseClassDescr.getOrderedAppyAttributes() + attrs
        # Modify attributes order by using "move" attributes
        res = []
        for name, appyType, klass in attrs:
            if appyType.move:
                newPosition = len(res) - abs(appyType.move)
                if newPosition <= 0:
                    newPosition = 0
                res.insert(newPosition, (name, appyType, klass))
            else:
                res.append((name, appyType, klass))
        return res

    def getChildren(self):
        '''Returns, among p_allClasses, the classes that inherit from p_self.'''
        res = []
        for classDescr in self.generator.classes:
            if (classDescr.klass != self.klass) and \
               issubclass(classDescr.klass, self.klass):
                res.append(classDescr)
        return res

    def getPhases(self):
        '''Lazy-gets the phases defined on fields of this class.'''
        if not hasattr(self, 'phases') or (self.phases == None):
            self.phases = []
            for fieldName, appyType, klass in self.getOrderedAppyAttributes():
                if appyType.page.phase in self.phases: continue
                self.phases.append(appyType.page.phase)
        return self.phases

    def getPages(self):
        '''Lazy-gets the page names defined on fields of this class.'''
        if not hasattr(self, 'pages') or (self.pages == None):
            self.pages = []
            for fieldName, appyType, klass in self.getOrderedAppyAttributes():
                if appyType.page.name in self.pages: continue
                self.pages.append(appyType.page.name)
        return self.pages

    def getParents(self, allClasses):
        parentWrapper = 'AbstractWrapper'
        parentClass = '%s.%s' % (self.klass.__module__, self.klass.__name__)
        if self.klass.__bases__:
            baseClassName = self.klass.__bases__[0].__name__
            for k in allClasses:
                if self.klass.__name__ == baseClassName:
                    parentWrapper = '%s_Wrapper' % k.name
        return (parentWrapper, parentClass)

    def generateSchema(self, configClass=False):
        '''Generates i18n and other related stuff for this class. If this class
           is in the configuration (tool, user, etc) we must avoid having
           attributes that rely on the configuration (ie attributes that are
           optional, with editDefault=True, etc).'''
        for attrName in self.orderedAttributes:
            try:
                attrValue = getattr(self.klass, attrName)
            except AttributeError:
                attrValue = getattr(self.modelClass, attrName)
            if isinstance(attrValue, gen.Type):
                if configClass:
                    attrValue = copy.copy(attrValue)
                    attrValue.optional = False
                    attrValue.editDefault = False
                FieldDescriptor(attrName, attrValue, self).generate()

    def isAbstract(self):
        '''Is self.klass abstract?'''
        res = False
        if self.klass.__dict__.has_key('abstract'):
            res = self.klass.__dict__['abstract']
        return res

    def isRoot(self):
        '''Is self.klass root? A root class represents some kind of major
           concept into the application. For example, creating instances
           of such classes will be easy from the user interface.'''
        res = False
        if self.klass.__dict__.has_key('root'):
            res = self.klass.__dict__['root']
        return res

    def isFolder(self, klass=None):
        '''Must self.klass be a folder? If klass is not None, this method tests
           it on p_klass instead of self.klass.'''
        res = False
        theClass = self.klass
        if klass:
            theClass = klass
        if theClass.__dict__.has_key('folder'):
            res = theClass.__dict__['folder']
        else:
            if theClass.__bases__:
                res = self.isFolder(theClass.__bases__[0])
        return res

    def getCreators(self):
        '''Gets the specific creators defined for this class.'''
        res = []
        if self.klass.__dict__.has_key('creators') and self.klass.creators:
            for creator in self.klass.creators:
                if isinstance(creator, gen.Role):
                    if creator.local:
                        raise 'Local role "%s" cannot be used as a creator.' % \
                              creator.name
                    res.append(creator)
                else:
                    res.append(gen.Role(creator))
        return res

    def getCreateMean(self, type='Import'):
        '''Returns the mean for this class that corresponds to p_type, or
           None if the class does not support this create mean.'''
        if not self.klass.__dict__.has_key('create'): return None
        else:
            means = self.klass.create
            if not means: return None
            if not isinstance(means, tuple) and not isinstance(means, list):
                means = [means]
            for mean in means:
                exec 'found = isinstance(mean, %s)' % type
                if found: return mean
        return None

    @staticmethod
    def getSearches(klass):
        '''Returns the list of searches that are defined on this class.'''
        res = []
        if klass.__dict__.has_key('search'):
            searches = klass.__dict__['search']
            if isinstance(searches, basestring):
                res.append(gen.Search(searches))
            elif isinstance(searches, gen.Search):
                res.append(searches)
            else:
                # It must be a list of searches.
                for search in searches:
                    if isinstance(search, basestring):
                        res.append(gen.Search(search))
                    else:
                        res.append(search)
        return res

    @staticmethod
    def getSearch(klass, searchName):
        '''Gets the search named p_searchName.'''
        for search in ClassDescriptor.getSearches(klass):
            if search.name == searchName:
                return search
        return None

    def addIndexMethod(self, field):
        '''For indexed p_field, this method generates a method that allows to
           get the value of the field as must be copied into the corresponding
           index.'''
        m = self.methods
        spaces = TABS
        n = field.fieldName
        m += '\n' + ' '*spaces + 'def get%s%s(self):\n' % (n[0].upper(), n[1:])
        spaces += TABS
        m += ' '*spaces + "'''Gets indexable value of field \"%s\".'''\n" % n
        m += ' '*spaces + 'return self.getAppyType("%s").getIndexValue(' \
             'self)\n' % n
        self.methods = m

    def addField(self, fieldName, fieldType):
        '''Adds a new field to the Tool.'''
        exec "self.modelClass.%s = fieldType" % fieldName
        if fieldName in self.modelClass._appy_attributes:
            print 'Warning, field "%s" is already existing on class "%s"' % \
                  (fieldName, self.modelClass.__name__)
            return
        self.modelClass._appy_attributes.append(fieldName)
        self.orderedAttributes.append(fieldName)

# ------------------------------------------------------------------------------
class WorkflowDescriptor(Descriptor):
    '''This class gives information about an Appy workflow.'''
    @staticmethod
    def getWorkflowName(klass):
        '''Returns the name of this workflow.'''
        res = klass.__module__.replace('.', '_') + '_' + klass.__name__
        return res.lower()

# ------------------------------------------------------------------------------
class FieldDescriptor:
    '''This class gathers information about a specific typed attribute defined
       in a gen-class.'''

    # Although Appy allows to specify a multiplicity[0]>1 for those types, it is
    # not currently. So we will always generate single-valued type definitions
    # for them.
    singleValuedTypes = ('Integer', 'Float', 'Boolean', 'Date', 'File')

    def __init__(self, fieldName, appyType, classDescriptor):
        self.appyType = appyType
        self.classDescr = classDescriptor
        self.generator = classDescriptor.generator
        self.applicationName = classDescriptor.generator.applicationName
        self.fieldName = fieldName
        self.fieldParams = {'name': fieldName}
        self.widgetParams = {}
        self.fieldType = None
        self.widgetType = None

    def __repr__(self):
        return '<Field %s, %s>' % (self.fieldName, self.classDescr)

    def getToolFieldMessage(self, fieldName):
        '''Some attributes generated on the Tool class need a specific
           default message, returned by this method.'''
        res = fieldName
        for prefix in toolFieldPrefixes:
            fullPrefix = prefix + 'For'
            if fieldName.startswith(fullPrefix):
                messageId = 'MSG_%s' % prefix
                res = getattr(PoMessage, messageId)
                if res.find('%s') != -1:
                    # I must complete the message with the field name.
                    res = res % fieldName.split('_')[-1]
                break
        return res

    def produceMessage(self, msgId, isLabel=True):
        '''Gets the default label, description or help (depending on p_msgType)
           for i18n message p_msgId.'''
        default = ' '
        produceNice = False
        if isLabel:
            produceNice = True
            default = self.fieldName
            # Some attributes need a specific predefined message
            if isinstance(self.classDescr, ToolClassDescriptor):
                default = self.getToolFieldMessage(self.fieldName)
                if default != self.fieldName: produceNice = False
        msg = PoMessage(msgId, '', default)
        if produceNice:
            msg.produceNiceDefault()
        return msg

    def walkString(self):
        '''How to generate an Appy String?'''
        if self.appyType.isSelect and \
           (type(self.appyType.validator) in (list, tuple)):
            # Generate i18n messages for every possible value if the list
            # of values is fixed.
            for value in self.appyType.validator:
                msgLabel = '%s_%s_list_%s' % (self.classDescr.name,
                    self.fieldName, value)
                poMsg = PoMessage(msgLabel, '', value)
                poMsg.produceNiceDefault()
                self.generator.labels.append(poMsg)

    def walkAction(self):
        '''Generates the i18n-related label.'''
        if self.appyType.confirm:
            label = '%s_%s_confirm' % (self.classDescr.name, self.fieldName)
            msg = PoMessage(label, '', PoMessage.CONFIRM)
            self.generator.labels.append(msg)

    def walkRef(self):
        '''How to generate a Ref?'''
        # Update the list of referers
        self.generator.addReferer(self)
        # Add the widget label for the back reference
        back = self.appyType.back
        refClassName = getClassName(self.appyType.klass, self.applicationName)
        if back.hasLabel:
            backLabel = "%s_%s" % (refClassName, self.appyType.back.attribute)
            poMsg = PoMessage(backLabel, '', self.appyType.back.attribute)
            poMsg.produceNiceDefault()
            self.generator.labels.append(poMsg)
        # Add the label for the confirm message if relevant
        if self.appyType.addConfirm:
            label = '%s_%s_addConfirm' % (self.classDescr.name, self.fieldName)
            msg = PoMessage(label, '', PoMessage.CONFIRM)
            self.generator.labels.append(msg)

    def walkPod(self):
        # Add i18n-specific messages
        if self.appyType.askAction:
            label = '%s_%s_askaction' % (self.classDescr.name, self.fieldName)
            msg = PoMessage(label, '', PoMessage.POD_ASKACTION)
            self.generator.labels.append(msg)
            self.classDescr.labelsToPropagate.append(msg)
        # Add the POD-related fields on the Tool
        self.generator.tool.addPodRelatedFields(self)

    def walkList(self):
        # Add i18n-specific messages
        for name, field in self.appyType.fields:
            label = '%s_%s_%s' % (self.classDescr.name, self.fieldName, name)
            msg = PoMessage(label, '', name)
            msg.produceNiceDefault()
            self.generator.labels.append(msg)

    def walkAppyType(self):
        '''Walks into the Appy type definition and gathers data about the
           i18n labels.'''
        # Manage things common to all Appy types
        # - optional ?
        if self.appyType.optional:
            self.generator.tool.addOptionalField(self)
        # - edit default value ?
        if self.appyType.editDefault:
            self.generator.tool.addDefaultField(self)
        # - put an index on this field?
        if self.appyType.indexed and (self.fieldName != 'title'):
            self.classDescr.addIndexMethod(self)
        # i18n labels
        messages = self.generator.labels
        if not self.appyType.label:
            # Create labels for generating them in i18n files, only if required.
            i18nPrefix = "%s_%s" % (self.classDescr.name, self.fieldName)
            if self.appyType.hasLabel:
                messages.append(self.produceMessage(i18nPrefix))
            if self.appyType.hasDescr:
                descrId = i18nPrefix + '_descr'
                messages.append(self.produceMessage(descrId,isLabel=False))
            if self.appyType.hasHelp:
                helpId = i18nPrefix + '_help'
                messages.append(self.produceMessage(helpId, isLabel=False))
        # Create i18n messages linked to pages and phases, only if there is more
        # than one page/phase for the class.
        ppMsgs = []
        if len(self.classDescr.getPhases()) > 1:
            # Create the message for the name of the phase
            phaseName = self.appyType.page.phase
            msgId = '%s_phase_%s' % (self.classDescr.name, phaseName)
            ppMsgs.append(PoMessage(msgId, '', produceNiceMessage(phaseName)))
        if len(self.classDescr.getPages()) > 1:
            # Create the message for the name of the page
            pageName = self.appyType.page.name
            msgId = '%s_page_%s' % (self.classDescr.name, pageName)
            ppMsgs.append(PoMessage(msgId, '', produceNiceMessage(pageName)))
        for poMsg in ppMsgs:
            if poMsg not in messages:
                messages.append(poMsg)
                self.classDescr.labelsToPropagate.append(poMsg)
        # Create i18n messages linked to groups
        group = self.appyType.group
        if group and not group.label:
            group.generateLabels(messages, self.classDescr, set())
        # Manage things which are specific to String types
        if self.appyType.type == 'String': self.walkString()
        # Manage things which are specific to Actions
        elif self.appyType.type == 'Action': self.walkAction()
        # Manage things which are specific to Ref types
        elif self.appyType.type == 'Ref': self.walkRef()
        # Manage things which are specific to Pod types
        elif self.appyType.type == 'Pod': self.walkPod()
        # Manage things which are specific to List types
        elif self.appyType.type == 'List': self.walkList()

    def generate(self):
        '''Generates the i18n labels for this type.'''
        self.walkAppyType()

# ------------------------------------------------------------------------------
class ToolClassDescriptor(ClassDescriptor):
    '''Represents the POD-specific fields that must be added to the tool.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False

    def getParents(self, allClasses=()):
        res = ['Tool']
        if self.customized:
            res.append('%s.%s' % (self.klass.__module__, self.klass.__name__))
        return res

    def update(self, klass, attributes):
        '''This method is called by the generator when he finds a custom tool
           definition. We must then add the custom tool elements in this default
           Tool descriptor.'''
        self.orderedAttributes += attributes
        self.klass = klass
        self.customized = True

    def isFolder(self, klass=None): return True
    def isRoot(self): return False
    def generateSchema(self):
        ClassDescriptor.generateSchema(self, configClass=True)

    def addOptionalField(self, fieldDescr):
        className = fieldDescr.classDescr.name
        fieldName = 'optionalFieldsFor%s' % className
        fieldType = getattr(self.modelClass, fieldName, None)
        if not fieldType:
            fieldType = String(multiplicity=(0,None))
            fieldType.validator = []
            self.addField(fieldName, fieldType)
        fieldType.validator.append(fieldDescr.fieldName)
        fieldType.page.name = 'data'
        fieldType.group = gen.Group(fieldDescr.classDescr.klass.__name__)

    def addDefaultField(self, fieldDescr):
        className = fieldDescr.classDescr.name
        fieldName = 'defaultValueFor%s_%s' % (className, fieldDescr.fieldName)
        fieldType = fieldDescr.appyType.clone()
        self.addField(fieldName, fieldType)
        fieldType.page.name = 'data'
        fieldType.group = gen.Group(fieldDescr.classDescr.klass.__name__)

    def addPodRelatedFields(self, fieldDescr):
        '''Adds the fields needed in the Tool for configuring a Pod field.'''
        className = fieldDescr.classDescr.name
        # On what page and group to display those fields ?
        pg = {'page': 'documentGeneration',
              'group':gen.Group(fieldDescr.classDescr.klass.__name__,['50%']*2)}
        # Add the field that will store the pod template.
        fieldName = 'podTemplateFor%s_%s' % (className, fieldDescr.fieldName)
        fieldType = gen.File(**pg)
        self.addField(fieldName, fieldType)
        # Add the field that will store the output format(s)
        fieldName = 'formatsFor%s_%s' % (className, fieldDescr.fieldName)
        fieldType = gen.String(validator=gen.Selection('getPodOutputFormats'),
                               multiplicity=(1,None), default=('odt',), **pg)
        self.addField(fieldName, fieldType)

    def addQueryResultColumns(self, classDescr):
        '''Adds, for class p_classDescr, the attribute in the tool that allows
           to select what default columns will be shown on query results.'''
        className = classDescr.name
        fieldName = 'resultColumnsFor%s' % className
        fieldType = gen.String(multiplicity=(0,None), validator=gen.Selection(
            '_appy_getAllFields*%s' % className), page='userInterface',
            group=classDescr.klass.__name__)
        self.addField(fieldName, fieldType)

    def addSearchRelatedFields(self, classDescr):
        '''Adds, for class p_classDescr, attributes related to the search
           functionality for class p_classDescr.'''
        className = classDescr.name
        # Field that defines if advanced search is enabled for class
        # p_classDescr or not.
        fieldName = 'enableAdvancedSearchFor%s' % className
        fieldType = gen.Boolean(default=True, page='userInterface',
                                group=classDescr.klass.__name__)
        self.addField(fieldName, fieldType)
        # Field that defines how many columns are shown on the custom search
        # screen.
        fieldName = 'numberOfSearchColumnsFor%s' % className
        fieldType = gen.Integer(default=3, page='userInterface',
                                group=classDescr.klass.__name__)
        self.addField(fieldName, fieldType)
        # Field that allows to select, among all indexed fields, what fields
        # must really be used in the search screen.
        fieldName = 'searchFieldsFor%s' % className
        defaultValue = [a[0] for a in classDescr.getOrderedAppyAttributes(
            condition='attrValue.indexed')]
        fieldType = gen.String(multiplicity=(0,None), validator=gen.Selection(
            '_appy_getSearchableFields*%s' % className), default=defaultValue,
            page='userInterface', group=classDescr.klass.__name__)
        self.addField(fieldName, fieldType)

    def addImportRelatedFields(self, classDescr):
        '''Adds, for class p_classDescr, attributes related to the import
           functionality for class p_classDescr.'''
        className = classDescr.name
        # Field that defines the path of the files to import.
        fieldName = 'importPathFor%s' % className
        defValue = classDescr.getCreateMean('Import').path
        fieldType = gen.String(page='data', multiplicity=(1,1),
                               default=defValue,group=classDescr.klass.__name__)
        self.addField(fieldName, fieldType)

    def addWorkflowFields(self, classDescr):
        '''Adds, for a given p_classDescr, the workflow-related fields.'''
        className = classDescr.name
        groupName = classDescr.klass.__name__
        # Adds a field allowing to show/hide completely any workflow-related
        # information for a given class.
        defaultValue = False
        if classDescr.isRoot() or issubclass(classDescr.klass, ModelClass):
            defaultValue = True
        fieldName = 'showWorkflowFor%s' % className
        fieldType = gen.Boolean(default=defaultValue, page='userInterface',
                                group=groupName)
        self.addField(fieldName, fieldType)
        # Adds the boolean field for showing or not the field "enter comments".
        fieldName = 'showWorkflowCommentFieldFor%s' % className
        fieldType = gen.Boolean(default=defaultValue, page='userInterface',
                                group=groupName)
        self.addField(fieldName, fieldType)
        # Adds the boolean field for showing all states in current state or not.
        # If this boolean is True but the current phase counts only one state,
        # we will not show the state at all: the fact of knowing in what phase
        # we are is sufficient. If this boolean is False, we simply show the
        # current state.
        defaultValue = False
        if len(classDescr.getPhases()) > 1:
            defaultValue = True
        fieldName = 'showAllStatesInPhaseFor%s' % className
        fieldType = gen.Boolean(default=defaultValue, page='userInterface',
                                group=groupName)
        self.addField(fieldName, fieldType)

class UserClassDescriptor(ClassDescriptor):
    '''Appy-specific class for representing a user.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False
    def getParents(self, allClasses=()):
        res = ['User']
        if self.customized:
            res.append('%s.%s' % (self.klass.__module__, self.klass.__name__))
        return res
    def update(self, klass, attributes):
        '''This method is called by the generator when he finds a custom user
           definition. We must then add the custom user elements in this
           default User descriptor.'''
        self.orderedAttributes += attributes
        self.klass = klass
        self.customized = True
    def isFolder(self, klass=None): return False
    def generateSchema(self):
        ClassDescriptor.generateSchema(self, configClass=True)

class GroupClassDescriptor(ClassDescriptor):
    '''Represents the class that corresponds to the Group for the generated
       application.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False
    def getParents(self, allClasses=()):
        res = ['Group']
        if self.customized:
            res.append('%s.%s' % (self.klass.__module__, self.klass.__name__))
        return res
    def update(self, klass, attributes):
        '''This method is called by the generator when he finds a custom group
           definition. We must then add the custom group elements in this
           default Group descriptor.

           NOTE: currently, it is not possible to define a custom Group
           class.'''
        self.orderedAttributes += attributes
        self.klass = klass
        self.customized = True
    def isFolder(self, klass=None): return False
    def generateSchema(self):
        ClassDescriptor.generateSchema(self, configClass=True)

class TranslationClassDescriptor(ClassDescriptor):
    '''Represents the set of translation ids for a gen-application.'''

    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False

    def getParents(self, allClasses=()): return ('Translation',)

    def generateSchema(self):
        ClassDescriptor.generateSchema(self, configClass=True)

    def addLabelField(self, messageId, page):
        '''Adds a Computed field that will display, in the source language, the
           content of the text to translate.'''
        field = gen.Computed(method=self.modelClass.label, plainText=False,
                             page=page, show=self.modelClass.show, layouts='f')
        self.addField('%s_label' % messageId, field)

    def addMessageField(self, messageId, page, i18nFiles):
        '''Adds a message field corresponding to p_messageId to the Translation
           class, on a given p_page. We need i18n files p_i18nFiles for
           fine-tuning the String type to generate for this field (one-line?
           several lines?...)'''
        params = {'page':page, 'layouts':'f', 'show': self.modelClass.show}
        appName = self.generator.applicationName
        # Scan all messages corresponding to p_messageId from all translation
        # files. We will define field length from the longer found message
        # content.
        maxLine = 100 # We suppose a line is 100 characters long.
        width = 0
        height = 0
        for fileName, poFile in i18nFiles.iteritems():
            if not fileName.startswith('%s-' % appName) or \
               not i18nFiles[fileName].messagesDict.has_key(messageId):
                # In this case this is not one of our Appy-managed translation
                # files.
                continue
            msgContent = i18nFiles[fileName].messagesDict[messageId].msg
            # Compute width
            width = max(width, len(msgContent))
            # Compute height (a "\n" counts for one line)
            mHeight = int(len(msgContent)/maxLine) + msgContent.count('<br/>')
            height = max(height, mHeight)
        if height < 1:
            # This is a one-line field.
            params['width'] = width
        else:
            # This is a multi-line field, or a very-long-single-lined field
            params['format'] = gen.String.TEXT
            params['height'] = height
        self.addField(messageId, gen.String(**params))
# ------------------------------------------------------------------------------
