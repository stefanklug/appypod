'''This file contains basic classes that will be added into any user
   application for creating the basic structure of the application "Tool" which
   is the set of web pages used for configuring the application. The "Tool" is
   available to administrators under the standard Plone link "site setup". Plone
   itself is shipped with several tools used for conguring the various parts of
   Plone (content types, catalogs, workflows, etc.)'''

# ------------------------------------------------------------------------------
import copy, types
from appy.gen import Type, Integer, String, File, Ref, Boolean

# ------------------------------------------------------------------------------
class ModelClass:
    '''This class is the abstract class of all predefined application classes
       used in the Appy model: Tool, Flavour, PodTemplate, etc. All methods and
       attributes of those classes are part of the Appy machinery and are
       prefixed with _appy_ in order to avoid name conflicts with user-defined
       parts of the application model.'''
    _appy_attributes = [] # We need to keep track of attributes order.
    _appy_notinit = ('id', 'type', 'pythonType', 'slaves', 'selfClass',
                     'phase', 'pageShow', 'isSelect') # When creating a new
                     # instance of a ModelClass, those attributes must not be
                     # given in the constructor.

    def _appy_addField(klass, fieldName, fieldType, classDescr):
        exec "klass.%s = fieldType" % fieldName
        klass._appy_attributes.append(fieldName)
        if hasattr(klass, '_appy_classes'):
            klass._appy_classes[fieldName] = classDescr.name
    _appy_addField = classmethod(_appy_addField)

    def _appy_getTypeBody(klass, appyType):
        '''This method returns the code declaration for p_appyType.'''
        typeArgs = ''
        for attrName, attrValue in appyType.__dict__.iteritems():
            if attrName in ModelClass._appy_notinit:
                continue
            if isinstance(attrValue, basestring):
                attrValue = '"%s"' % attrValue
            elif isinstance(attrValue, Type):
                attrValue = klass._appy_getTypeBody(attrValue)
            elif type(attrValue) == type(ModelClass):
                moduleName = attrValue.__module__
                if moduleName.startswith('appy.gen'):
                    attrValue = attrValue.__name__
                else:
                    attrValue = '%s.%s' % (moduleName, attrValue.__name__)
            typeArgs += '%s=%s,' % (attrName, attrValue)
        return '%s(%s)' % (appyType.__class__.__name__, typeArgs)
    _appy_getTypeBody = classmethod(_appy_getTypeBody)

    def _appy_getBody(klass):
        '''This method returns the code declaration of this class. We will dump
           this in appyWrappers.py in the resulting product.'''
        res = ''
        for attrName in klass._appy_attributes:
            exec 'appyType = klass.%s' % attrName
            res += '    %s=%s\n' % (attrName, klass._appy_getTypeBody(appyType))
        return res
    _appy_getBody = classmethod(_appy_getBody)

class PodTemplate(ModelClass):
    description = String(format=String.TEXT)
    podTemplate = File(multiplicity=(1,1))
    podFormat = String(validator=['odt', 'pdf', 'rtf', 'doc'],
                       multiplicity=(1,1), default='odt')
    phase = String(default='main')
    _appy_attributes = ['description', 'podTemplate', 'podFormat', 'phase']

defaultFlavourAttrs = ('number', 'enableNotifications')
flavourAttributePrefixes = ('optionalFieldsFor', 'defaultValueFor',
    'podTemplatesFor', 'podMaxShownTemplatesFor', 'resultColumnsFor',
    'showWorkflowFor', 'showWorkflowCommentFieldFor', 'showAllStatesInPhaseFor')
# Attribute prefixes of the fields generated on the Flavour for configuring
# the application classes.

class Flavour(ModelClass):
    '''For every application, the Flavour may be different (it depends on the
       fields declared as optional, etc). Instead of creating a new way to
       generate the Archetypes Flavour class, we create a silly
       FlavourStub instance and we will use the standard Archetypes
       generator that generates classes from the application to generate the
       flavour class.'''
    number = Integer(default=1, show=False)
    enableNotifications = Boolean(default=True, page='notifications')
    _appy_classes = {} # ~{s_attributeName: s_className}~
    # We need to remember the original classes related to the flavour attributes
    _appy_attributes = list(defaultFlavourAttrs)
    
    def _appy_clean(klass):
        toClean = []
        for k, v in klass.__dict__.iteritems():
            if not k.startswith('__') and (not k.startswith('_appy_')):
                if k not in defaultFlavourAttrs:
                    toClean.append(k)
        for k in toClean:
            exec 'del klass.%s' % k
        klass._appy_attributes = list(defaultFlavourAttrs)
        klass._appy_classes = {}
    _appy_clean = classmethod(_appy_clean)

    def _appy_copyField(klass, appyType):
        '''From a given p_appyType, produce a type definition suitable for
           storing the default value for this field.'''
        res = copy.copy(appyType)
        res.editDefault = False
        res.optional = False
        res.show = True
        res.phase = 'main'
        res.specificReadPermission = False
        res.specificWritePermission = False
        res.multiplicity = (0, appyType.multiplicity[1])
        if type(res.validator) == types.FunctionType:
            # We will not be able to call this function from the flavour.
            res.validator = None
        if isinstance(appyType, Ref):
            res.link = True
            res.add = False
            res.back = copy.copy(appyType.back)
            res.back.attribute += 'DefaultValue'
            res.back.show = False
            res.select = None # Not callable from flavour
        return res
    _appy_copyField = classmethod(_appy_copyField)

    def _appy_addOptionalField(klass, fieldDescr):
        className = fieldDescr.classDescr.name
        fieldName = 'optionalFieldsFor%s' % className
        fieldType = getattr(klass, fieldName, None)
        if not fieldType:
            fieldType = String(multiplicity=(0,None))
            fieldType.validator = []
            klass._appy_addField(fieldName, fieldType, fieldDescr.classDescr)
        fieldType.validator.append(fieldDescr.fieldName)
        fieldType.page = 'data'
        fieldType.group = fieldDescr.classDescr.klass.__name__
    _appy_addOptionalField = classmethod(_appy_addOptionalField)

    def _appy_addDefaultField(klass, fieldDescr):
        className = fieldDescr.classDescr.name
        fieldName = 'defaultValueFor%s_%s' % (className, fieldDescr.fieldName)
        fieldType = klass._appy_copyField(fieldDescr.appyType)
        klass._appy_addField(fieldName, fieldType, fieldDescr.classDescr)
        fieldType.page = 'data'
        fieldType.group = fieldDescr.classDescr.klass.__name__
    _appy_addDefaultField = classmethod(_appy_addDefaultField)

    def _appy_addPodField(klass, classDescr):
        '''Adds a POD field to the flavour and also an integer field that will
           determine the maximum number of documents to show at once on consult
           views. If this number is reached, a list is displayed.'''
        # First, add the POD field that will hold PodTemplates.
        fieldType = Ref(PodTemplate, multiplicity=(0,None), add=True,
                        link=False, back = Ref(attribute='flavour'),
                        page="documentGeneration",
                        group=classDescr.klass.__name__)
        fieldName = 'podTemplatesFor%s' % classDescr.name
        klass._appy_addField(fieldName, fieldType, classDescr)
        # Then, add the integer field
        fieldType = Integer(default=1, page='userInterface',
                            group=classDescr.klass.__name__)
        fieldName = 'podMaxShownTemplatesFor%s' % classDescr.name
        klass._appy_addField(fieldName, fieldType, classDescr)
        classDescr.flavourFieldsToPropagate.append(
            ('podMaxShownTemplatesFor%s', copy.copy(fieldType)) )
    _appy_addPodField = classmethod(_appy_addPodField)

    def _appy_addQueryResultColumns(klass, classDescr):
        className = classDescr.name
        fieldName = 'resultColumnsFor%s' % className
        attrNames = [a[0] for a in classDescr.getOrderedAppyAttributes()]
        attrNames.append('workflowState') # Object state from workflow
        if 'title' in attrNames:
            attrNames.remove('title') # Included by default.
        fieldType = String(multiplicity=(0,None), validator=attrNames,
                           page='userInterface',
                           group=classDescr.klass.__name__)
        klass._appy_addField(fieldName, fieldType, classDescr)
    _appy_addQueryResultColumns = classmethod(_appy_addQueryResultColumns)

    def _appy_addWorkflowFields(klass, classDescr):
        '''Adds, for a given p_classDescr, the workflow-related fields.'''
        className = classDescr.name
        groupName = classDescr.klass.__name__
        # Adds a field allowing to show/hide completely any workflow-related
        # information for a given class.
        defaultValue = False
        if classDescr.isRoot() or issubclass(classDescr.klass, ModelClass):
            defaultValue = True
        fieldName = 'showWorkflowFor%s' % className
        fieldType = Boolean(default=defaultValue, page='userInterface',
                            group=groupName)
        klass._appy_addField(fieldName, fieldType, classDescr)
        # Adds the boolean field for showing or not the field "enter comments".
        fieldName = 'showWorkflowCommentFieldFor%s' % className
        fieldType = Boolean(default=defaultValue, page='userInterface',
                            group=groupName)
        klass._appy_addField(fieldName, fieldType, classDescr)
        # Adds the boolean field for showing all states in current state or not.
        # If this boolean is True but the current phase counts only one state,
        # we will not show the state at all: the fact of knowing in what phase
        # we are is sufficient. If this boolean is False, we simply show the
        # current state.
        defaultValue = False
        if len(classDescr.getPhases()) > 1:
            defaultValue = True
        fieldName = 'showAllStatesInPhaseFor%s' % className
        fieldType = Boolean(default=defaultValue, page='userInterface',
                            group=groupName)
        klass._appy_addField(fieldName, fieldType, classDescr)
        
    _appy_addWorkflowFields = classmethod(_appy_addWorkflowFields)

class Tool(ModelClass):
    flavours = Ref(None, multiplicity=(1,None), add=True, link=False,
                   back=Ref(attribute='tool'))
                   # First arg is None because we don't know yet if it will link
                   # to the predefined Flavour class or a custom class defined
                   # in the application.
    unoEnabledPython = String(group="connectionToOpenOffice")
    openOfficePort = Integer(default=2002, group="connectionToOpenOffice")
    numberOfResultsPerPage = Integer(default=30)
    listBoxesMaximumWidth = Integer(default=100)
    _appy_attributes = ['flavours', 'unoEnabledPython', 'openOfficePort',
                        'numberOfResultsPerPage', 'listBoxesMaximumWidth']
# ------------------------------------------------------------------------------