'''Descriptor classes defined in this file are "intermediary" classes that
   gather, from the user application, information about concepts (like Archetype
   classes or DC workflow definitions) that will eventually be dumped into the
   generated application. Typically they have methods named "generate..." that
   produce generated code.'''

# ------------------------------------------------------------------------------
import types, copy
from model import ModelClass, Flavour, flavourAttributePrefixes
from utils import stringify
import appy.gen
import appy.gen.descriptors
from appy.gen.po import PoMessage
from appy.gen import Date, String, State, Transition, Type
from appy.gen.utils import GroupDescr, PageDescr, produceNiceMessage
TABS = 4 # Number of blanks in a Python indentation.

# ------------------------------------------------------------------------------
class ArchetypeFieldDescriptor:
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
        self.walkAppyType()

    def __repr__(self):
        return '<Field %s, %s>' % (self.fieldName, self.classDescr)

    def getFlavourAttributeMessage(self, fieldName):
        '''Some attributes generated on the Flavour class need a specific
           default message, returned by this method.'''
        res = fieldName
        for prefix in flavourAttributePrefixes:
            if fieldName.startswith(prefix):
                messageId = 'MSG_%s' % prefix
                res = getattr(PoMessage, messageId)
                if res.find('%s') != -1:
                    # I must complete the message with the field name.
                    res = res % fieldName.split('_')[-1]
                break
        return res

    def produceMessage(self, msgId, isLabel=True):
        '''Gets the default label or description (if p_isLabel is False) for
           i18n message p_msgId.'''
        default = ' '
        produceNice = False
        if isLabel:
            produceNice = True
            default = self.fieldName
            # Some attributes need a specific predefined message
            if isinstance(self.classDescr, FlavourClassDescriptor):
                default = self.getFlavourAttributeMessage(self.fieldName)
                if default != self.fieldName: produceNice = False
        msg = PoMessage(msgId, '', default)
        if produceNice:
            msg.produceNiceDefault()
        return msg

    def walkBasicType(self):
        '''How to dump a basic type?'''
        self.fieldType = '%sField' % self.appyType.type
        self.widgetType = "%sWidget" % self.appyType.type
        if self.appyType.type == 'Date':
            self.fieldType = 'DateTimeField'
            self.widgetType = 'CalendarWidget'
            if self.appyType.format == Date.WITHOUT_HOUR:
                self.widgetParams['show_hm'] = False
        elif self.appyType.type == 'Float':
            self.widgetType = 'DecimalWidget'
        elif self.appyType.type == 'File':
            if self.appyType.isImage:
                self.fieldType = 'ImageField'
                self.widgetType = 'ImageWidget'
            self.fieldParams['storage'] = 'python:AttributeStorage()'

    def walkString(self):
        '''How to generate an Appy String?'''
        if self.appyType.format == String.LINE:
            if self.appyType.isSelection():
                if self.appyType.isMultiValued():
                    self.fieldType = 'LinesField'
                    self.widgetType = 'MultiSelectionWidget'
                    self.fieldParams['multiValued'] = True
                else:
                    self.fieldType = 'StringField'
                    self.widgetType = 'SelectionWidget'
                    self.widgetParams['format'] = 'select'
                # Elements common to all selection fields
                methodName = 'list_%s_values' % self.fieldName
                self.fieldParams['vocabulary'] = methodName
                self.classDescr.addSelectMethod(
                    methodName, self, self.appyType.isMultiValued())
                self.fieldParams['enforceVocabulary'] = True
            else:
                self.fieldType = 'StringField'
                self.widgetType = 'StringWidget'
                self.widgetParams['size'] = 50
                if self.appyType.width:
                    self.widgetParams['size'] = self.appyType.width
            # Manage index
            if self.appyType.searchable:
                self.fieldParams['index'] = 'FieldIndex'
        elif self.appyType.format == String.TEXT:
            self.fieldType = 'TextField'
            self.widgetType = 'TextAreaWidget'
            if self.appyType.height:
                self.widgetParams['rows'] = self.appyType.height
        elif self.appyType.format == String.XHTML:
            self.fieldType = 'TextField'
            self.widgetType = 'RichWidget'
            self.fieldParams['allowable_content_types'] = ('text/html',)
            self.fieldParams['default_output_type'] = "text/html"
        else:
            self.fieldType = 'StringField'
            self.widgetType = 'StringWidget'
        # Manage searchability
        if self.appyType.searchable:
            self.fieldParams['searchable'] = True

    def walkComputed(self):
        '''How to generate a computed field? We generate an Archetypes String
           field.'''
        self.fieldType = 'StringField'
        self.widgetType = 'StringWidget'
        self.widgetParams['visible'] = False # Archetypes will believe the
        # field is invisible; we will display it ourselves (like for Ref fields)

    def walkAction(self):
        '''How to generate an action field ? We generate an Archetypes String
           field.'''
        self.fieldType = 'StringField'
        self.widgetType = 'StringWidget'
        self.widgetParams['visible'] = False # Archetypes will believe the
        # field is invisible; we will display it ourselves (like for Ref fields)
        # Add action-specific i18n messages
        for suffix in ('ok', 'ko'):
            label = '%s_%s_action_%s' % (self.classDescr.name, self.fieldName,
                                         suffix)
            msg = PoMessage(label, '',
                            getattr(PoMessage, 'ACTION_%s' % suffix.upper()))
            self.generator.labels.append(msg)
            self.classDescr.labelsToPropagate.append(msg)

    def walkRef(self):
        '''How to generate a Ref?'''
        relationship = '%s_%s_rel' % (self.classDescr.name, self.fieldName)
        self.fieldType = 'ReferenceField'
        self.widgetType = 'ReferenceWidget'
        self.fieldParams['relationship'] = relationship
        if self.appyType.isMultiValued():
            self.fieldParams['multiValued'] = True
        self.widgetParams['visible'] = False
        # Update the list of referers
        self.generator.addReferer(self, relationship)
        # Add the widget label for the back reference
        refClassName = ArchetypesClassDescriptor.getClassName(
            self.appyType.klass)
        if issubclass(self.appyType.klass, ModelClass):
            refClassName = self.applicationName + self.appyType.klass.__name__
        elif issubclass(self.appyType.klass, appy.gen.Tool):
            refClassName = '%sTool' % self.applicationName
        elif issubclass(self.appyType.klass, appy.gen.Flavour):
            refClassName = '%sFlavour' % self.applicationName
        backLabel = "%s_%s_back" % (refClassName, self.appyType.back.attribute)
        poMsg = PoMessage(backLabel, '', self.appyType.back.attribute)
        poMsg.produceNiceDefault()
        self.generator.labels.append(poMsg)

    def walkInfo(self):
        '''How to generate an Info field? We generate an Archetypes String
           field.'''
        self.fieldType = 'StringField'
        self.widgetType = 'StringWidget'
        self.widgetParams['visible'] = False # Archetypes will believe the
        # field is invisible; we will display it ourselves (like for Ref fields)

    alwaysAValidatorFor = ('Ref', 'Integer', 'Float')
    def walkAppyType(self):
        '''Walks into the Appy type definition and gathers data about the
           Archetype elements to generate.'''
        # Manage things common to all Appy types
        # - special accessor for fields "title" and "description"
        if self.fieldName in self.specialParams:
            self.fieldParams['accessor'] = self.fieldName.capitalize()
        # - default value
        if self.appyType.default != None:
            self.fieldParams['default'] = self.appyType.default
        # - required?
        if self.appyType.multiplicity[0] >= 1:
            if self.appyType.type != 'Ref':
                # Indeed, if it is a ref appy will manage itself field updates
                # in at_post_create_script, so Archetypes must not enforce
                # required=True
                self.fieldParams['required'] = True
        # - optional ?
        if self.appyType.optional:
            Flavour._appy_addOptionalField(self)
            self.widgetParams['condition'] = ' python: ' \
                'here.fieldIsUsed("%s")'% self.fieldName
        # - edit default value ?
        if self.appyType.editDefault:
            Flavour._appy_addDefaultField(self)
            methodName = 'getDefaultValueFor%s' % self.fieldName
            self.fieldParams['default_method'] = methodName
            self.classDescr.addDefaultMethod(methodName, self)
        # - searchable ?
        if self.appyType.searchable and (self.appyType.type != 'String'):
            self.fieldParams['index'] = 'FieldIndex'
        # - slaves ?
        if self.appyType.slaves:
            self.widgetParams['visible'] = False # Archetypes will believe the
            # field is invisible; we will display it ourselves (like for Ref
            # fields)
        # - need to generate a field validator?
        # In all cases, add an i18n message for the validation error for this
        # field.
        label = '%s_%s_valid' % (self.classDescr.name, self.fieldName)
        poMsg = PoMessage(label, '', PoMessage.DEFAULT_VALID_ERROR)
        self.generator.labels.append(poMsg)
        if (type(self.appyType.validator) == types.FunctionType) or \
           (type(self.appyType.validator) == type(String.EMAIL)) or \
           (self.appyType.type in self.alwaysAValidatorFor):
            # For references, we always add a validator because gen validates
            # itself things like multiplicities;
            # For integers and floats, we also need validators because, by
            # default, Archetypes produces an exception if the field value does
            # not have the correct type, for example.
            methodName = 'validate_%s' % self.fieldName
            # Add a validate method for this
            specificType = None
            if self.appyType.type in self.alwaysAValidatorFor:
                specificType = self.appyType.type
            self.classDescr.addValidateMethod(methodName, label, self,
                specificType=specificType)
        # Manage specific permissions
        permFieldName = '%s %s' % (self.classDescr.name, self.fieldName)
        if self.appyType.specificReadPermission:
            self.fieldParams['read_permission'] = '%s: Read %s' % \
                (self.generator.applicationName, permFieldName)
        if self.appyType.specificWritePermission:
            self.fieldParams['write_permission'] = '%s: Write %s' % \
                (self.generator.applicationName, permFieldName)
        # i18n labels
        i18nPrefix = "%s_%s" % (self.classDescr.name, self.fieldName)
        wp = self.widgetParams
        wp['label'] = self.fieldName
        wp['label_msgid'] = '%s' % i18nPrefix
        wp['description'] = '%sDescr' % i18nPrefix
        wp['description_msgid'] = '%s_descr' % i18nPrefix
        wp['i18n_domain'] = self.applicationName
        # Create labels for generating them in i18n files.
        messages = self.generator.labels
        messages.append(self.produceMessage(wp['label_msgid']))
        messages.append(self.produceMessage(wp['description_msgid'],
                        isLabel=False))
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
        if self.appyType.group:
            groupName, cols = GroupDescr.getGroupInfo(self.appyType.group)
            msgId = '%s_group_%s' % (self.classDescr.name, groupName)
            poMsg = PoMessage(msgId, '', groupName)
            poMsg.produceNiceDefault()
            if poMsg not in messages:
                messages.append(poMsg)
                self.classDescr.labelsToPropagate.append(poMsg)
        # Manage schemata
        if self.appyType.page != 'main':
            self.fieldParams['schemata'] = self.appyType.page
        # Manage things which are specific to basic types
        if self.appyType.type in self.singleValuedTypes: self.walkBasicType()
        # Manage things which are specific to String types
        elif self.appyType.type == 'String': self.walkString()
        # Manage things which are specific to Computed types
        elif self.appyType.type == 'Computed': self.walkComputed()
        # Manage things which are specific to Actions
        elif self.appyType.type == 'Action': self.walkAction()
        # Manage things which are specific to reference types
        elif self.appyType.type == 'Ref': self.walkRef()
        # Manage things which are specific to info types
        elif self.appyType.type == 'Info': self.walkInfo()

    def generate(self):
        '''Produces the Archetypes field definition as a string.'''
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
        self.flavourFieldsToPropagate = [] # For this class, some fields have
        # been defined on the Flavour class. Those fields need to be defined
        # for child classes of this class as well, but at this time we don't
        # know yet every sub-class. So we store field definitions here; the
        # Generator will propagate them later.

    def generateSchema(self):
        '''Generates the corresponding Archetypes schema in self.schema.'''
        for attrName in self.orderedAttributes:
            attrValue = getattr(self.klass, attrName)
            if isinstance(attrValue, Type):
                field = ArchetypeFieldDescriptor(attrName, attrValue, self)
                self.schema += '\n' + field.generate()

    def addSelectMethod(self, methodName, fieldDescr, isMultivalued=False):
        '''For the selection field p_fieldDescr I need to generate a method
           named p_methodName that will generate the vocabulary for
           p_fieldDescr.'''
        # Generate the method signature
        m = self.methods
        s = stringify
        spaces = TABS
        m += '\n' + ' '*spaces + 'def %s(self):\n' % methodName
        spaces += TABS
        appyType = fieldDescr.appyType
        if type(appyType.validator) in (list, tuple):
            # Generate i18n messages for every possible value
            f = fieldDescr
            labels = []
            for value in appyType.validator:
                msgLabel = '%s_%s_list_%s' % (f.classDescr.name, f.fieldName,
                                              value)
                labels.append(msgLabel) # I will need it later
                poMsg = PoMessage(msgLabel, '', value)
                poMsg.produceNiceDefault()
                self.generator.labels.append(poMsg)
            # Generate a method that returns a DisplayList
            appName = self.generator.applicationName
            allValues = appyType.validator
            if not isMultivalued:
                allValues = [''] + appyType.validator
                labels.insert(0, 'choose_a_value')
            m += ' '*spaces + 'return self._appy_getDisplayList' \
                 '(%s, %s, %s)\n' % (s(allValues), s(labels), s(appName))
        self.methods = m

    def addValidateMethod(self, methodName, label, fieldDescr,
                          specificType=None):
        '''For the field p_fieldDescr I need to generate a validation method.
           If p_specificType is not None, it corresponds to the name of a type
           like Ref, Integer or Float, for which specific validation is needed,
           beyond the potential custom validation specified by a user-defined
           validator method.'''
        # Generate the method signature
        m = self.methods
        s = stringify
        spaces = TABS
        m += '\n' + ' '*spaces + 'def %s(self, value):\n' % methodName
        spaces += TABS
        m += ' '*spaces + 'return self._appy_validateField(%s, value, %s, ' \
             '%s)\n' %  (s(fieldDescr.fieldName), s(label), s(specificType))
        self.methods = m

    def addDefaultMethod(self, methodName, fieldDescr):
        '''When the default value of a field may be edited, we must add a method
           that will gather the default value from the flavour.'''
        m = self.methods
        spaces = TABS
        m += '\n' + ' '*spaces + 'def %s(self):\n' % methodName
        spaces += TABS
        m += ' '*spaces + 'return self.getDefaultValueFor("%s")\n' % \
             fieldDescr.fieldName
        self.methods = m

class ArchetypesClassDescriptor(ClassDescriptor):
    '''Represents an Archetypes-compliant class that corresponds to an
       application class.'''
    predefined = False
    def __init__(self, klass, orderedAttributes, generator):
        ClassDescriptor.__init__(self, klass, orderedAttributes, generator)
        if not hasattr(self, 'name'):
            self.name = self.getClassName(klass)
        self.generateSchema()

    def getClassName(klass):
        '''Generates the name of the corresponding Archetypes class.'''
        return klass.__module__.replace('.', '_') + '_' + klass.__name__
    getClassName = staticmethod(getClassName)

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

    def isPod(self):
        '''May this class be associated with POD templates?.'''
        res = False
        if self.klass.__dict__.has_key('pod') and self.klass.__dict__['pod']:
            res = True
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

    def addGenerateDocMethod(self):
        m = self.methods
        spaces = TABS
        m += '\n' + ' '*spaces + 'def generateDocument(self):\n'
        spaces += TABS
        m += ' '*spaces + "'''Generates a document from p_self.'''\n"
        m += ' '*spaces + 'return self._appy_generateDocument()\n'
        self.methods = m

class ToolClassDescriptor(ClassDescriptor):
    '''Represents the POD-specific fields that must be added to the tool.'''
    predefined = True
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self, klass, klass._appy_attributes, generator)
        self.name = '%sTool' % generator.applicationName
    def isFolder(self, klass=None): return True
    def isRoot(self): return False
    def addUnoValidator(self):
        m = self.methods
        spaces = TABS
        m += '\n' + ' '*spaces + 'def validate_unoEnabledPython(self, value):\n'
        spaces += TABS
        m += ' '*spaces + 'return self._appy_validateUnoEnabledPython(value)\n'
        self.methods = m
    def generateSchema(self):
        ClassDescriptor.generateSchema(self)
        self.addUnoValidator()

class FlavourClassDescriptor(ClassDescriptor):
    '''Represents an Archetypes-compliant class that corresponds to the Flavour
       for the generated application.'''
    predefined = True
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self, klass, klass._appy_attributes, generator)
        self.name = '%sFlavour' % generator.applicationName
        self.attributesByClass = klass._appy_classes
        # We don't generate the schema automatically here because we need to
        # add more fields.
    def isFolder(self, klass=None): return True
    def isRoot(self): return False

class PodTemplateClassDescriptor(ClassDescriptor):
    '''Represents a POD template.'''
    predefined = True
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self, klass, klass._appy_attributes, generator)
        self.name = '%sPodTemplate' % generator.applicationName
    def isRoot(self): return False

class CustomToolClassDescriptor(ArchetypesClassDescriptor):
    '''If the user defines a class that inherits from Tool, we will add those
       fields to the tool.'''
    predefined = False
    def __init__(self, *args):
        self.name = '%sTool' % args[2].applicationName
        ArchetypesClassDescriptor.__init__(self, *args)
    def generateSchema(self):
        '''Custom tool fields may not use the variability mechanisms, ie
           'optional' or 'editDefault' attributes.'''
        for attrName in self.orderedAttributes:
            attrValue = getattr(self.klass, attrName)
            if isinstance(attrValue, Type):
                attrValue = copy.copy(attrValue)
                attrValue.optional = False
                attrValue.editDefault = False
                field = ArchetypeFieldDescriptor(attrName, attrValue, self)
                self.schema += '\n' + field.generate()

class CustomFlavourClassDescriptor(CustomToolClassDescriptor):
    def __init__(self, *args):
        self.name = '%sFlavour' % args[2].applicationName
        ArchetypesClassDescriptor.__init__(self, *args)

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
                    permissionsMapping[plonePerm] = roles
            # Add 'Review portal content' to anyone; this is not a security
            # problem because we limit the triggering of every transition
            # individually.
            allRoles = self.generator.getAllUsedRoles()
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
