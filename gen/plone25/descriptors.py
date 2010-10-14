'''Descriptor classes defined in this file are "intermediary" classes that
   gather, from the user application, information about concepts (like Archetype
   classes or DC workflow definitions) that will eventually be dumped into the
   generated application. Typically they have methods named "generate..." that
   produce generated code.'''

# ------------------------------------------------------------------------------
import types, copy
from model import ModelClass, Tool, toolFieldPrefixes
from utils import stringify
import appy.gen
import appy.gen.descriptors
from appy.gen.po import PoMessage
from appy.gen import Date, String, State, Transition, Type, Search, \
                     Selection, Import, Role
from appy.gen.utils import GroupDescr, PageDescr, produceNiceMessage, \
     sequenceTypes, getClassName
TABS = 4 # Number of blanks in a Python indentation.

# ------------------------------------------------------------------------------
class FieldDescriptor:
    '''This class allows to gather information needed to generate an Archetypes
       definition (field + widget) from an Appy type. An Appy type is used for
       defining the type of attributes defined in the user application.'''

    singleValuedTypes = ('Integer', 'Float', 'Boolean', 'Date', 'File')
    # Although Appy allows to specify a multiplicity[0]>1 for those types, it is
    # not supported by Archetypes. So we will always generate single-valued type
    # definitions for them.
    specialParams = ('title', 'description')

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
        '''Generates the i18n-related labels.'''
        for suffix in ('ok', 'ko'):
            label = '%s_%s_action_%s' % (self.classDescr.name, self.fieldName,
                                         suffix)
            msg = PoMessage(label, '',
                            getattr(PoMessage, 'ACTION_%s' % suffix.upper()))
            self.generator.labels.append(msg)
            self.classDescr.labelsToPropagate.append(msg)
        if self.appyType.confirm:
            label = '%s_%s_confirm' % (self.classDescr.name, self.fieldName)
            msg = PoMessage(label, '', PoMessage.CONFIRM)
            self.generator.labels.append(msg)

    def walkRef(self):
        '''How to generate a Ref?'''
        relationship = '%s_%s_rel' % (self.classDescr.name, self.fieldName)
        self.fieldType = 'ReferenceField'
        self.widgetType = 'ReferenceWidget'
        self.fieldParams['relationship'] = relationship
        if self.appyType.isMultiValued():
            self.fieldParams['multiValued'] = True
        # Update the list of referers
        self.generator.addReferer(self, relationship)
        # Add the widget label for the back reference
        refClassName = getClassName(self.appyType.klass, self.applicationName)
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
        Tool._appy_addPodRelatedFields(self)

    notToValidateFields = ('Info', 'Computed', 'Action', 'Pod')
    def walkAppyType(self):
        '''Walks into the Appy type definition and gathers data about the
           i18n labels.'''
        # Manage things common to all Appy types
        # - optional ?
        if self.appyType.optional:
            Tool._appy_addOptionalField(self)
        # - edit default value ?
        if self.appyType.editDefault:
            Tool._appy_addDefaultField(self)
        # - put an index on this field?
        if self.appyType.indexed and \
           (self.fieldName not in ('title', 'description')):
            self.classDescr.addIndexMethod(self)
        # - searchable ? TODO
        #if self.appyType.searchable: self.fieldParams['searchable'] = True
        # - need to generate a field validator?
        # In all cases excepted for "immutable" fields, add an i18n message for
        # the validation error for this field.
        if self.appyType.type not in self.notToValidateFields:
            label = '%s_%s_valid' % (self.classDescr.name, self.fieldName)
            poMsg = PoMessage(label, '', PoMessage.DEFAULT_VALID_ERROR)
            self.generator.labels.append(poMsg)
        # i18n labels
        i18nPrefix = "%s_%s" % (self.classDescr.name, self.fieldName)
        # Create labels for generating them in i18n files.
        messages = self.generator.labels
        if self.appyType.hasLabel:
            messages.append(self.produceMessage(i18nPrefix))
        if self.appyType.hasDescr:
            descrId = i18nPrefix + '_descr'
            messages.append(self.produceMessage(descrId,isLabel=False))
        if self.appyType.hasHelp:
            helpId = i18nPrefix + '_help'
            messages.append(self.produceMessage(helpId, isLabel=False))
        # Create i18n messages linked to pages and phases
        messages = self.generator.labels
        pageMsgId = '%s_page_%s' % (self.classDescr.name, self.appyType.page)
        phaseMsgId = '%s_phase_%s' % (self.classDescr.name, self.appyType.phase)
        pagePoMsg = PoMessage(pageMsgId, '',
                              produceNiceMessage(self.appyType.page))
        phasePoMsg = PoMessage(phaseMsgId, '',
                               produceNiceMessage(self.appyType.phase))
        for poMsg in (pagePoMsg, phasePoMsg):
            if poMsg not in messages:
                messages.append(poMsg)
                self.classDescr.labelsToPropagate.append(poMsg)
        # Create i18n messages linked to groups
        group = self.appyType.group
        if group:
            group.generateLabels(messages, self.classDescr, set())
        # Manage things which are specific to String types
        if self.appyType.type == 'String': self.walkString()
        # Manage things which are specific to Actions
        elif self.appyType.type == 'Action': self.walkAction()
        # Manage things which are specific to Ref types
        elif self.appyType.type == 'Ref': self.walkRef()
        # Manage things which are specific to Pod types
        elif self.appyType.type == 'Pod': self.walkPod()

    def generate(self):
        '''Generates the i18n labels for this type.'''
        self.walkAppyType()
        if self.appyType.type != 'Ref': return
        res = ''
        s = stringify
        spaces = TABS
        # Generate field name
        res += ' '*spaces + self.fieldType + '(\n'
        # Generate field parameters
        spaces += TABS
        for fParamName, fParamValue in self.fieldParams.iteritems():
            res += ' '*spaces + fParamName + '=' + s(fParamValue) + ',\n'
        # Generate widget
        res += ' '*spaces + 'widget=%s(\n' % self.widgetType
        spaces += TABS
        for wParamName, wParamValue in self.widgetParams.iteritems():
            res += ' '*spaces + wParamName + '=' + s(wParamValue) + ',\n'
        # End of widget definition
        spaces -= TABS
        res += ' '*spaces + ')\n'
        # End of field definition
        spaces -= TABS
        res += ' '*spaces + '),\n'
        return res

class ClassDescriptor(appy.gen.descriptors.ClassDescriptor):
    '''Represents an Archetypes-compliant class.'''
    def __init__(self, klass, orderedAttributes, generator):
        appy.gen.descriptors.ClassDescriptor.__init__(self, klass,
            orderedAttributes, generator)
        self.schema = '' # The archetypes schema will be generated here
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
        '''Generates the corresponding Archetypes schema in self.schema. If we
           are generating a schema for a class that is in the configuration
           (tool, user, etc) we must avoid having attributes that rely on
           the configuration (ie attributes that are optional, with
           editDefault=True, etc).'''
        for attrName in self.orderedAttributes:
            try:
                attrValue = getattr(self.klass, attrName)
            except AttributeError:
                attrValue = getattr(self.modelClass, attrName)
            if isinstance(attrValue, Type):
                if configClass:
                    attrValue = copy.copy(attrValue)
                    attrValue.optional = False
                    attrValue.editDefault = False
                field = FieldDescriptor(attrName, attrValue, self)
                fieldDef = field.generate()
                if fieldDef:
                    # Currently, we generate Archetypes fields for Refs only.
                    self.schema += '\n' + fieldDef

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
                if isinstance(creator, Role):
                    if creator.local:
                        raise 'Local role "%s" cannot be used as a creator.' % \
                              creator.name
                    res.append(creator)
                else:
                    res.append(Role(creator))
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
            if isinstance(searches, basestring): res.append(Search(searches))
            elif isinstance(searches, Search):   res.append(searches)
            else:
                # It must be a list of searches.
                for search in searches:
                    if isinstance(search, basestring):res.append(Search(search))
                    else:                             res.append(search)
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
        m += ' '*spaces + 'return self.getAppyType("%s").getValue(self)\n' % n
        self.methods = m

class ToolClassDescriptor(ClassDescriptor):
    '''Represents the POD-specific fields that must be added to the tool.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.attributesByClass = klass._appy_classes
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

class UserClassDescriptor(ClassDescriptor):
    '''Represents an Archetypes-compliant class that corresponds to the User
       for the generated application.'''
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
    def isFolder(self, klass=None): return True
    def isRoot(self): return False
    def generateSchema(self):
        ClassDescriptor.generateSchema(self, configClass=True)

class WorkflowDescriptor(appy.gen.descriptors.WorkflowDescriptor):
    '''Represents a workflow.'''
    # How to map Appy permissions to Plone permissions ?
    appyToPlonePermissions = {
      'read': ('View', 'Access contents information'),
      'write': ('Modify portal content',),
      'delete': ('Delete objects',),
    }
    def getPlonePermissions(self, permission):
        '''Returns the Plone permission(s) that correspond to
           Appy p_permission.'''
        if self.appyToPlonePermissions.has_key(permission):
            res = self.appyToPlonePermissions[permission]
        elif isinstance(permission, basestring):
            res = [permission]
        else:
            # Permission if an Appy permission declaration
            className, fieldName = permission.fieldDescriptor.rsplit('.', 1)
            if className.find('.') == -1:
                # The related class resides in the same module as the workflow
                fullClassName = '%s_%s' % (
                    self.klass.__module__.replace('.', '_'), className)
            else:
                # className contains the full package name of the class
                fullClassName = className.replace('.', '_')
            # Read or Write ?
            if permission.__class__.__name__ == 'ReadPermission':
                access = 'Read'
            else:
                access = 'Write'
            permName = '%s: %s %s %s' % (self.generator.applicationName,
                                         access, fullClassName, fieldName)
            res = [permName]
        return res

    def getWorkflowName(klass):
        '''Generates the name of the corresponding Archetypes workflow.'''
        res = klass.__module__.replace('.', '_') + '_' + klass.__name__
        return res.lower()
    getWorkflowName = staticmethod(getWorkflowName)

    def getStatesInfo(self, asDumpableCode=False):
        '''Gets, in a dict, information for configuring states of the workflow.
           If p_asDumpableCode is True, instead of returning a dict, this
           method will return a string containing the dict that can be dumped
           into a Python code file.'''
        res = {}
        transitions = self.getTransitions()
        for state in self.getStates():
            stateName = self.getNameOf(state)
            # We need the list of transitions that start from this state
            outTransitions = state.getTransitions(transitions,
                                                  selfIsFromState=True)
            tNames = self.getTransitionNames(outTransitions,
                                             limitToFromState=state)
            # Compute the permissions/roles mapping for this state
            permissionsMapping = {}
            for permission, roles in state.getPermissions().iteritems():
                for plonePerm in self.getPlonePermissions(permission):
                    permissionsMapping[plonePerm] = [r.name for r in roles]
            # Add 'Review portal content' to anyone; this is not a security
            # problem because we limit the triggering of every transition
            # individually.
            allRoles = [r.name for r in self.generator.getAllUsedRoles()]
            if 'Manager' not in allRoles: allRoles.append('Manager')
            permissionsMapping['Review portal content'] = allRoles
            res[stateName] = (tNames, permissionsMapping)
        if not asDumpableCode:
            return res
        # We must create the "Python code" version of this dict
        newRes = '{'
        for stateName, stateInfo in res.iteritems():
            transitions = ','.join(['"%s"' % tn for tn in stateInfo[0]])
            # Compute permissions
            permissions = ''
            for perm, roles in stateInfo[1].iteritems():
                theRoles = ','.join(['"%s"' % r for r in roles])
                permissions += '"%s": [%s],' % (perm, theRoles)
            newRes += '\n    "%s": ([%s], {%s}),' % \
                (stateName, transitions, permissions)
        return newRes + '}'

    def getTransitionsInfo(self, asDumpableCode=False):
        '''Gets, in a dict, information for configuring transitions of the
           workflow. If p_asDumpableCode is True, instead of returning a dict,
           this method will return a string containing the dict that can be
           dumped into a Python code file.'''
        res = {}
        for tName in self.getTransitionNames():
            res[tName] = self.getEndStateName(tName)
        if not asDumpableCode:
            return res
        # We must create the "Python code" version of this dict
        newRes = '{'
        for transitionName, endStateName in res.iteritems():
            newRes += '\n    "%s": "%s",' % (transitionName, endStateName)
        return newRes + '}'

    def getManagedPermissions(self):
        '''Returns the Plone permissions of all Appy permissions managed by this
           workflow.'''
        res = set()
        res.add('Review portal content')
        for state in self.getStates():
            for permission in state.permissions.iterkeys():
                for plonePerm in self.getPlonePermissions(permission):
                    res.add(plonePerm)
        return res

    def getScripts(self):
        res = ''
        wfName = WorkflowDescriptor.getWorkflowName(self.klass)
        for tName in self.getTransitionNames():
            scriptName = '%s_do%s%s' % (wfName, tName[0].upper(), tName[1:])
            res += 'def %s(self, stateChange, **kw): do("%s", ' \
                   'stateChange, logger)\n' % (scriptName, tName)
        return res
# ------------------------------------------------------------------------------
