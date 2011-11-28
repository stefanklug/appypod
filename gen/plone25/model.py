'''This file contains basic classes that will be added into any user
   application for creating the basic structure of the application "Tool" which
   is the set of web pages used for configuring the application. The "Tool" is
   available to administrators under the standard Plone link "site setup". Plone
   itself is shipped with several tools used for conguring the various parts of
   Plone (content types, catalogs, workflows, etc.)'''

# ------------------------------------------------------------------------------
import types
from appy.gen import *
Grp=Group # Avoid name clash between appy.gen.Group and class Group below

# Prototypical instances of every type -----------------------------------------
class Protos:
    protos = {}
    # List of attributes that can't be given to a Type constructor
    notInit = ('id', 'type', 'pythonType', 'slaves', 'isSelect', 'hasLabel',
               'hasDescr', 'hasHelp', 'required', 'filterable', 'validable',
               'backd', 'isBack', 'sync', 'pageName', 'shownInfoWidths',
               'masterName')
    @classmethod
    def get(self, appyType):
        '''Returns a prototype instance for p_appyType.'''
        className = appyType.__class__.__name__
        isString = (className == 'String')
        if isString:
            # For Strings, we create one prototype per format, because default
            # values may change according to format.
            className += str(appyType.format)
        if className in self.protos: return self.protos[className]
        # The prototype does not exist yet: create it
        if isString:
            proto = appyType.__class__(format=appyType.format)
            # Now, we fake to be able to detect default values
            proto.format = 0
        else:
            proto = appyType.__class__()
        self.protos[className] = proto
        return proto

# ------------------------------------------------------------------------------
class ModelClass:
    '''This class is the abstract class of all predefined application classes
       used in the Appy model: Tool, User, etc. All methods and attributes of
       those classes are part of the Appy machinery and are prefixed with _appy_
       in order to avoid name conflicts with user-defined parts of the
       application model.'''
    _appy_attributes = [] # We need to keep track of attributes order.

    @classmethod
    def _appy_getTypeBody(klass, appyType, wrapperName):
        '''This method returns the code declaration for p_appyType.'''
        typeArgs = ''
        proto = Protos.get(appyType)
        for name, value in appyType.__dict__.iteritems():
            # Some attrs can't be given to the constructor
            if name in Protos.notInit: continue
            # If the given value corresponds to the default value, don't give it
            if value == getattr(proto, name): continue
            if name == 'layouts':
                # For Tool attributes we do not copy layout info. Indeed, most
                # fields added to the Tool are config-related attributes whose
                # layouts must be standard.
                if klass.__name__ == 'Tool': continue
                layouts = appyType.getInputLayouts()
                # For the Translation class that has potentially thousands of
                # attributes, the most used layout is cached in a global var in
                # named "tfw" in appyWrappers.py.
                if (klass.__name__ == 'Translation') and \
                   (layouts == '{"edit":"f","cell":"f","view":"f",}'):
                    value = 'tfw'
                else:
                    value = appyType.getInputLayouts()
            elif isinstance(value, basestring):
                value = '"%s"' % value
            elif isinstance(value, Ref):
                if not value.isBack: continue
                value = klass._appy_getTypeBody(value, wrapperName)
            elif type(value) == type(ModelClass):
                moduleName = value.__module__
                if moduleName.startswith('appy.gen'):
                    value = value.__name__
                else:
                    value = '%s.%s' % (moduleName, value.__name__)
            elif isinstance(value, Selection):
                value = 'Selection("%s")' % value.methodName
            elif isinstance(value, Grp):
                value = 'Grp("%s")' % value.name
            elif isinstance(value, Page):
                value = 'pages["%s"]' % value.name
            elif callable(value):
                value = '%s.%s' % (wrapperName, value.__name__)
            typeArgs += '%s=%s,' % (name, value)
        return '%s(%s)' % (appyType.__class__.__name__, typeArgs)

    @classmethod
    def _appy_getBody(klass):
        '''This method returns the code declaration of this class. We will dump
           this in appyWrappers.py in the resulting product.'''
        className = klass.__name__
        # Determine the name of the class and its wrapper. Because so much
        # attributes can be generated on a TranslationWrapper, shortcutting it
        # to 'TW' may reduce the generated file from several kilobytes.
        if className == 'Translation': wrapperName = 'WT'
        else: wrapperName = 'W%s' % className
        res = 'class %s(%s):\n' % (className, wrapperName)
        # Tool must be folderish
        if className == 'Tool': res += '    folder=True\n'
        # First, scan all attributes, determine all used pages and create a
        # dict with it. It will prevent us from creating a new Page instance
        # for every field.
        pages = {}
        layouts = []
        for name in klass._appy_attributes:
            exec 'appyType = klass.%s' % name
            if appyType.page.name not in pages:
                pages[appyType.page.name] = appyType.page
        res += '    pages = {'
        for page in pages.itervalues():
            # Determine page show
            pageShow = page.show
            if isinstance(pageShow, basestring): pageShow='"%s"' % pageShow
            res += '"%s":Page("%s", show=%s),'% (page.name, page.name, pageShow)
        res += '}\n'
        # Secondly, dump every attribute
        for name in klass._appy_attributes:
            exec 'appyType = klass.%s' % name
            typeBody = klass._appy_getTypeBody(appyType, wrapperName)
            res += '    %s=%s\n' % (name, typeBody)
        return res

# The User class ---------------------------------------------------------------
class User(ModelClass):
    # In a ModelClass we need to declare attributes in the following list.
    _appy_attributes = ['title', 'name', 'firstName', 'login', 'password1',
                        'password2', 'roles']
    # All methods defined below are fake. Real versions are in the wrapper.
    title = String(show=False, indexed=True)
    gm = {'group': 'main', 'multiplicity': (1,1), 'width': 25}
    name = String(**gm)
    firstName = String(**gm)
    def showLogin(self): pass
    def validateLogin(self): pass
    login = String(show=showLogin, validator=validateLogin, indexed=True, **gm)
    def showPassword(self): pass
    def validatePassword(self): pass
    password1 = String(format=String.PASSWORD, show=showPassword,
                       validator=validatePassword, **gm)
    password2 = String(format=String.PASSWORD, show=showPassword, **gm)
    gm['multiplicity'] = (0, None)
    roles = String(validator=Selection('getGrantableRoles'), indexed=True, **gm)

# The Group class --------------------------------------------------------------
class Group(ModelClass):
    # In a ModelClass we need to declare attributes in the following list.
    _appy_attributes = ['title', 'login', 'roles', 'users']
    # All methods defined below are fake. Real versions are in the wrapper.
    m = {'group': 'main', 'width': 25, 'indexed': True}
    title = String(multiplicity=(1,1), **m)
    def showLogin(self): pass
    def validateLogin(self): pass
    login = String(show=showLogin, validator=validateLogin,
                   multiplicity=(1,1), **m)
    roles = String(validator=Selection('getGrantableRoles'),
                   multiplicity=(0,None), **m)
    users = Ref(User, multiplicity=(0,None), add=False, link=True,
                back=Ref(attribute='groups', show=True),
                showHeaders=True, shownInfo=('title', 'login'))

# The Translation class --------------------------------------------------------
class Translation(ModelClass):
    _appy_attributes = ['po', 'title']
    # All methods defined below are fake. Real versions are in the wrapper.
    def getPoFile(self): pass
    po = Action(action=getPoFile, page=Page('actions', show='view'),
                result='filetmp')
    title = String(show=False, indexed=True)
    def label(self): pass
    def show(self, name): pass

# The Tool class ---------------------------------------------------------------
# Here are the prefixes of the fields generated on the Tool.
toolFieldPrefixes = ('defaultValue', 'podTemplate', 'formats', 'resultColumns',
                     'enableAdvancedSearch', 'numberOfSearchColumns',
                     'searchFields', 'optionalFields', 'showWorkflow',
                     'showWorkflowCommentField', 'showAllStatesInPhase')
defaultToolFields = ('users', 'groups', 'translations', 'enableNotifications',
                     'unoEnabledPython', 'openOfficePort',
                     'numberOfResultsPerPage', 'listBoxesMaximumWidth',
                     'appyVersion', 'refreshSecurity')

class Tool(ModelClass):
    # In a ModelClass we need to declare attributes in the following list.
    _appy_attributes = list(defaultToolFields)

    # Tool attributes
    def validPythonWithUno(self, value): pass # Real method in the wrapper
    unoEnabledPython = String(group="connectionToOpenOffice",
                              validator=validPythonWithUno)
    openOfficePort = Integer(default=2002, group="connectionToOpenOffice")
    numberOfResultsPerPage = Integer(default=30, show=False)
    listBoxesMaximumWidth = Integer(default=100, show=False)
    appyVersion = String(show=False, layouts='f')
    def refreshSecurity(self): pass # Real method in the wrapper
    refreshSecurity = Action(action=refreshSecurity, confirm=True)
    # Ref(User) will maybe be transformed into Ref(CustomUserClass).
    users = Ref(User, multiplicity=(0,None), add=True, link=False,
                back=Ref(attribute='toTool', show=False),
                page=Page('users', show='view'),
                queryable=True, queryFields=('title', 'login'),
                showHeaders=True, shownInfo=('title', 'login', 'roles'))
    groups = Ref(Group, multiplicity=(0,None), add=True, link=False,
                 back=Ref(attribute='toTool2', show=False),
                 page=Page('groups', show='view'),
                 queryable=True, queryFields=('title', 'login'),
                 showHeaders=True, shownInfo=('title', 'login', 'roles'))
    translations = Ref(Translation, multiplicity=(0,None),add=False,link=False,
                       back=Ref(attribute='trToTool', show=False), show='view',
                       page=Page('translations', show='view'))
    enableNotifications = Boolean(default=True,
                                  page=Page('notifications', show=False))

    @classmethod
    def _appy_clean(klass):
        toClean = []
        for k, v in klass.__dict__.iteritems():
            if not k.startswith('__') and (not k.startswith('_appy_')):
                if k not in defaultToolFields:
                    toClean.append(k)
        for k in toClean:
            exec 'del klass.%s' % k
        klass._appy_attributes = list(defaultToolFields)
# ------------------------------------------------------------------------------
