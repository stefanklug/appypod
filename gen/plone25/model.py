'''This file contains basic classes that will be added into any user
   application for creating the basic structure of the application "Tool" which
   is the set of web pages used for configuring the application. The "Tool" is
   available to administrators under the standard Plone link "site setup". Plone
   itself is shipped with several tools used for conguring the various parts of
   Plone (content types, catalogs, workflows, etc.)'''

# ------------------------------------------------------------------------------
import types
from appy.gen import *

# ------------------------------------------------------------------------------
class ModelClass:
    '''This class is the abstract class of all predefined application classes
       used in the Appy model: Tool, User, etc. All methods and attributes of
       those classes are part of the Appy machinery and are prefixed with _appy_
       in order to avoid name conflicts with user-defined parts of the
       application model.'''
    _appy_attributes = [] # We need to keep track of attributes order.
    # When creating a new instance of a ModelClass, the following attributes
    # must not be given in the constructor (they are computed attributes).
    _appy_notinit = ('id', 'type', 'pythonType', 'slaves', 'isSelect',
                     'hasLabel', 'hasDescr', 'hasHelp', 'master_css',
                     'required', 'filterable', 'validable', 'backd', 'isBack',
                     'sync', 'pageName')

    @classmethod
    def _appy_getTypeBody(klass, appyType):
        '''This method returns the code declaration for p_appyType.'''
        typeArgs = ''
        for attrName, attrValue in appyType.__dict__.iteritems():
            if attrName in ModelClass._appy_notinit: continue
            if attrName == 'layouts':
                if klass.__name__ == 'Tool': continue
                # For Tool attributes we do not copy layout info. Indeed, most
                # fields added to the Tool are config-related attributes whose
                # layouts must be standard.
                attrValue = appyType.getInputLayouts()
            elif isinstance(attrValue, basestring):
                attrValue = '"%s"' % attrValue
            elif isinstance(attrValue, Ref):
                if not attrValue.isBack: continue
                attrValue = klass._appy_getTypeBody(attrValue)
            elif type(attrValue) == type(ModelClass):
                moduleName = attrValue.__module__
                if moduleName.startswith('appy.gen'):
                    attrValue = attrValue.__name__
                else:
                    attrValue = '%s.%s' % (moduleName, attrValue.__name__)
            elif isinstance(attrValue, Selection):
                attrValue = 'Selection("%s")' % attrValue.methodName
            elif isinstance(attrValue, Group):
                attrValue = 'Group("%s")' % attrValue.name
            elif isinstance(attrValue, Page):
                attrValue = 'pages["%s"]' % attrValue.name
            elif callable(attrValue):
                attrValue = '%sWrapper.%s'% (klass.__name__, attrValue.__name__)
            typeArgs += '%s=%s,' % (attrName, attrValue)
        return '%s(%s)' % (appyType.__class__.__name__, typeArgs)

    @classmethod
    def _appy_getBody(klass):
        '''This method returns the code declaration of this class. We will dump
           this in appyWrappers.py in the resulting product.'''
        res = 'class %s(%sWrapper):\n' % (klass.__name__, klass.__name__)
        if klass.__name__ == 'Tool':
            res += '    folder=True\n'
        # First, scan all attributes, determine all used pages and create a
        # dict with it. It will prevent us from creating a new Page instance
        # for every field.
        pages = {}
        for attrName in klass._appy_attributes:
            exec 'appyType = klass.%s' % attrName
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
        for attrName in klass._appy_attributes:
            exec 'appyType = klass.%s' % attrName
            res += '    %s=%s\n' % (attrName, klass._appy_getTypeBody(appyType))
        return res

# The User class ---------------------------------------------------------------
class User(ModelClass):
    # In a ModelClass we need to declare attributes in the following list.
    _appy_attributes = ['title', 'name', 'firstName', 'login', 'password1',
                        'password2', 'roles']
    # All methods defined below are fake. Real versions are in the wrapper.
    title = String(show=False, indexed=True)
    gm = {'group': 'main', 'multiplicity': (1,1)}
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

# The Translation class --------------------------------------------------------
class Translation(ModelClass):
    _appy_attributes = ['po', 'title']
    # All methods defined below are fake. Real versions are in the wrapper.
    def getPoFile(self): pass
    po = Action(action=getPoFile, page=Page('actions', show='view'),
                result='filetmp')
    title = String(show=False, indexed=True)
    def computeLabel(self): pass
    def showField(self, name): pass

# The Tool class ---------------------------------------------------------------
# Here are the prefixes of the fields generated on the Tool.
toolFieldPrefixes = ('defaultValue', 'podTemplate', 'formats', 'resultColumns',
                     'enableAdvancedSearch', 'numberOfSearchColumns',
                     'searchFields', 'optionalFields', 'showWorkflow',
                     'showWorkflowCommentField', 'showAllStatesInPhase')
defaultToolFields = ('users', 'translations', 'enableNotifications',
                     'unoEnabledPython', 'openOfficePort',
                     'numberOfResultsPerPage', 'listBoxesMaximumWidth')

class Tool(ModelClass):
    # In a ModelClass we need to declare attributes in the following list.
    _appy_attributes = list(defaultToolFields)

    # Tool attributes
    def validPythonWithUno(self, value): pass # Real method in the wrapper
    unoEnabledPython = String(group="connectionToOpenOffice",
                              validator=validPythonWithUno)
    openOfficePort = Integer(default=2002, group="connectionToOpenOffice")
    numberOfResultsPerPage = Integer(default=30)
    listBoxesMaximumWidth = Integer(default=100)
    # First arg of Ref field below is None because we don't know yet if it will
    # link to the predefined User class or a custom class defined in the
    # application.
    users = Ref(None, multiplicity=(0,None), add=True, link=False,
                back=Ref(attribute='toTool'), page='users', queryable=True,
                queryFields=('login',), showHeaders=True,
                shownInfo=('login', 'title', 'roles'))
    translations = Ref(Translation, multiplicity=(0,None), add=False,link=False,
                       back=Ref(attribute='trToTool', show=False), show='view',
                       page=Page('translations', show='view'))
    enableNotifications = Boolean(default=True, page='notifications')

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
