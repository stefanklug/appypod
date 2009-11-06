# ------------------------------------------------------------------------------
import re, time
from appy.gen.utils import sequenceTypes, PageDescr

# Default Appy permissions -----------------------------------------------------
r, w, d = ('read', 'write', 'delete')
digits = ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')

# Descriptor classes used for refining descriptions of elements in types
# (pages, groups,...) ----------------------------------------------------------
class Page:
    '''Used for describing a page, its related phase, show condition, etc.'''
    def __init__(self, name, phase='main', show=True):
        self.name = name
        self.phase = phase
        self.show = show

class Import:
    '''Used for describing the place where to find the data to use for creating
       an object.'''
    def __init__(self, path, columnMethod=None, columnHeaders=(),
                 sortMethod=None):
        self.id = 'import'
        self.path = path
        self.columnMethod = columnMethod
        # This method allows to split every element into subElements that can
        # be shown as column values in a table.
        self.columnHeaders = columnHeaders
        self.sortMethod = sortMethod

class Search:
    '''Used for specifying a search for a given type.'''
    def __init__(self, name, group=None, sortBy='', limit=None, **fields):
        self.name = name
        self.group = group # Searches may be visually grouped in the portlet
        self.sortBy = sortBy
        self.limit = limit
        self.fields = fields # This is a dict whose keys are indexed field
        # names and whose values are search values.

# ------------------------------------------------------------------------------
class Type:
    '''Basic abstract class for defining any appy type.'''
    def __init__(self, validator, multiplicity, index, default, optional,
                 editDefault, show, page, group, move, indexed, searchable,
                 specificReadPermission, specificWritePermission, width,
                 height, master, masterValue, focus):
        # The validator restricts which values may be defined. It can be an
        # interval (1,None), a list of string values ['choice1', 'choice2'],
        # a regular expression, a custom function, a Selection instance, etc.
        self.validator = validator
        # Multiplicity is a tuple indicating the minimum and maximum
        # occurrences of values.
        self.multiplicity = multiplicity
        # Type of the index on the values. If you want to represent a simple
        # (ordered) list of values, specify None. If you want to
        # index your values with unordered integers or with other types like
        # strings (thus creating a dictionary of values instead of a list),
        # specify a type specification for the index, like Integer() or
        # String(). Note that this concept of "index" has nothing to do with
        # the concept of "database index" (see fields "indexed" and
        # "searchable" below). self.index is not yet used.
        self.index = index
        # Default value
        self.default = default
        # Is the field optional or not ?
        self.optional = optional
        # May the user configure a default value ?
        self.editDefault = editDefault
        # Must the field be visible or not?
        self.show = show
        # When displaying/editing the whole object, on what page and phase must
        # this field value appear? Default is ('main', 'main'). pageShow
        # indicates if the page must be shown or not.
        self.page, self.phase, self.pageShow = PageDescr.getPageInfo(page, Page)
        # Within self.page, in what group of fields must this field value
        # appear?
        self.group = group
        # The following attribute allows to move a field back to a previous
        # position (useful for content types that inherit from others).
        self.move = move
        # If indexed is True, a database index will be set on the field for
        # fast access.
        self.indexed = indexed
        # If specified "searchable", the field will be added to some global
        # index allowing to perform application-wide, keyword searches.
        self.searchable = searchable
        # Normally, permissions to read or write every attribute in a type are
        # granted if the user has the global permission to read or
        # create/edit instances of the whole type. If you want a given attribute
        # to be protected by specific permissions, set one or the 2 next boolean
        # values to "True".
        self.specificReadPermission = specificReadPermission
        self.specificWritePermission = specificWritePermission
        # Widget width and height
        self.width = width
        self.height = height
        # The behaviour of this field may depend on another, "master" field
        self.master = master
        if master:
            self.master.slaves.append(self)
        # When master has some value(s), there is impact on this field.
        self.masterValue = masterValue
        # If a field must retain attention in a particular way, set focus=True.
        # It will be rendered in a special way.
        self.focus = focus
        self.id = id(self)
        self.type = self.__class__.__name__
        self.pythonType = None # The True corresponding Python type
        self.slaves = [] # The list of slaves of this field
        self.selfClass = None # The Python class to which this Type definition
        # is linked. This will be computed at runtime.

    def isMultiValued(self):
        '''Does this type definition allow to define multiple values?'''
        res = False
        maxOccurs = self.multiplicity[1]
        if (maxOccurs == None) or (maxOccurs > 1):
            res = True
        return res

class Integer(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 master=None, masterValue=None, focus=False):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.pythonType = long

class Float(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 master=None, masterValue=None, focus=False):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.pythonType = float

class String(Type):
    # Some predefined regular expressions that may be used as validators
    c = re.compile
    EMAIL = c('[a-zA-Z][\w\.-]*[a-zA-Z0-9]@[a-zA-Z0-9][\w\.-]*[a-zA-Z0-9]\.' \
              '[a-zA-Z][a-zA-Z\.]*[a-zA-Z]')
    ALPHANUMERIC = c('[\w-]+')
    URL = c('(http|https):\/\/[a-z0-9]+([\-\.]{1}[a-z0-9]+)*(\.[a-z]{2,5})?' \
            '(([0-9]{1,5})?\/.*)?')

    # Some predefined functions that may also be used as validators
    @staticmethod
    def _MODULO_97(obj, value, complement=False):
        '''p_value must be a string representing a number, like a bank account.
           this function checks that the 2 last digits are the result of
           computing the modulo 97 of the previous digits. Any non-digit
           character is ignored. If p_complement is True, it does compute the
           complement of modulo 97 instead of modulo 97. p_obj is not used;
           it will be given by the Appy validation machinery, so it must be
           specified as parameter. The function returns True if the check is
           successful.'''
        if not value: return True # Plone calls me erroneously for
        # non-mandatory fields.
        # First, remove any non-digit char
        v = ''
        for c in value:
            if c in digits: v += c
        # There must be at least 3 digits for performing the check
        if len(v) < 3: return False
        # Separate the real number from the check digits
        number = int(v[:-2])
        checkNumber = int(v[-2:])
        # Perform the check
        if complement:
            return (97 - (number % 97)) == checkNumber
        else:
            return (number % 97) == checkNumber
    @staticmethod
    def MODULO_97(obj, value): return String._MODULO_97(obj, value)
    @staticmethod
    def MODULO_97_COMPLEMENT(obj, value):
        return String._MODULO_97(obj, value, True)

    # Possible values for "format"
    LINE = 0
    TEXT = 1
    XHTML = 2
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, format=LINE,
                 show=True, page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 master=None, masterValue=None, focus=False):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, move, indexed, searchable,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.format = format
    def isSelection(self):
        '''Does the validator of this type definition define a list of values
           into which the user must select one or more values?'''
        res = True
        if type(self.validator) in (list, tuple):
            for elem in self.validator:
                if not isinstance(elem, basestring):
                    res = False
                    break
        else:
            if not isinstance(self.validator, Selection):
                res = False
        return res

class Boolean(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 master=None, masterValue=None, focus=False):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, move, indexed, searchable,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.pythonType = bool

class Date(Type):
    # Possible values for "format"
    WITH_HOUR = 0
    WITHOUT_HOUR = 1
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False,
                 format=WITH_HOUR, startYear=time.localtime()[0]-10,
                 endYear=time.localtime()[0]+10, show=True, page='main',
                 group=None, move=0, indexed=False, searchable=False,
                 specificReadPermission=False, specificWritePermission=False,
                 width=None, height=None, master=None, masterValue=None,
                 focus=False):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, move, indexed, searchable,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.format = format
        self.startYear = startYear
        self.endYear = endYear

class File(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 master=None, masterValue=None, focus=False, isImage=False):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.isImage = isImage

class Ref(Type):
    def __init__(self, klass=None, attribute=None, validator=None,
                 multiplicity=(0,1), index=None, default=None, optional=False,
                 editDefault=False, add=False, link=True, unlink=False,
                 back=None, isBack=False, show=True, page='main', group=None,
                 showHeaders=False, shownInfo=(), wide=False, select=None,
                 maxPerPage=30, move=0, indexed=False, searchable=False,
                 specificReadPermission=False, specificWritePermission=False,
                 width=None, height=None, master=None, masterValue=None,
                 focus=False):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.klass = klass
        self.attribute = attribute
        self.add = add # May the user add new objects through this ref ?
        self.link = link # May the user link existing objects through this ref?
        self.unlink = unlink # May the user unlink existing objects?
        self.back = back
        self.isBack = isBack # Should always be False
        self.showHeaders = showHeaders # When displaying a tabular list of
        # referenced objects, must we show the table headers?
        self.shownInfo = shownInfo # When displaying referenced object(s),
        # we will display its title + all other fields whose names are listed
        # in this attribute.
        self.wide = wide # If True, the table of references will be as wide
        # as possible
        self.select = select # If a method is defined here, it will be used to
        # filter the list of available tied objects.
        self.maxPerPage = maxPerPage # Maximum number of referenced objects
        # shown at once.

class Computed(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 method=None, plainText=True, master=None, masterValue=None,
                 focus=False):
        Type.__init__(self, None, multiplicity, index, default, optional,
                      False, show, page, group, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.method = method # The method used for computing the field value
        self.plainText = plainText # Does field computation produce pain text
        # or XHTML?

class Action(Type):
    '''An action is a workflow-independent Python method that can be triggered
       by the user on a given gen-class. For example, the custom installation
       procedure of a gen-application is implemented by an action on the custom
       tool class. An action is rendered as a button.'''
    def __init__(self, validator=None, multiplicity=(1,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 action=None, result='computation', master=None,
                 masterValue=None, focus=False):
        Type.__init__(self, None, (0,1), index, default, optional,
                      False, show, page, group, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)
        self.action = action # Can be a single method or a list/tuple of methods
        self.result = result # 'computation' means that the action will simply
        # compute things and redirect the user to the same page, with some
        # status message about execution of the action. 'file' means that the
        # result is the binary content of a file that the user will download.

    def __call__(self, obj):
        '''Calls the action on p_obj.'''
        try:
            if type(self.action) in sequenceTypes:
                # There are multiple Python methods
                res = [True, '']
                for act in self.action:
                    actRes = act(obj)
                    if type(actRes) in sequenceTypes:
                        res[0] = res[0] and actRes[0]
                        if self.result == 'file':
                            res[1] = res[1] + actRes[1]
                        else:
                            res[1] = res[1] + '\n' + actRes[1]
                    else:
                        res[0] = res[0] and actRes
            else:
                # There is only one Python method
                actRes = self.action(obj)
                if type(actRes) in sequenceTypes:
                    res = list(actRes)
                else:
                    res = [actRes, '']
            # If res is None (ie the user-defined action did not return
            # anything), we consider the action as successfull.
            if res[0] == None: res[0] = True
        except Exception, e:
            res = (False, str(e))
        return res

class Info(Type):
    '''An info is a field whose purpose is to present information
       (text, html...) to the user.'''
    def __init__(self, validator=None, multiplicity=(1,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 master=None, masterValue=None, focus=False):
        Type.__init__(self, None, (0,1), index, default, optional,
                      False, show, page, group, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, master, masterValue, focus)

# Workflow-specific types ------------------------------------------------------
class State:
    def __init__(self, permissions, initial=False, phase='main', show=True):
        self.permissions = permissions #~{s_permissionName:[s_roleName]}~ This
        # dict gives, for every permission managed by a workflow, the list of
        # roles for which the permission is granted in this state.
        # Standard permissions are 'read', 'write' and 'delete'.
        self.initial = initial
        self.phase = phase
        self.show = show
    def getUsedRoles(self):
        res = set()
        for roleValue in self.permissions.itervalues():
            if isinstance(roleValue, basestring):
                res.add(roleValue)
            elif roleValue:
                for role in roleValue:
                    res.add(role)
        return list(res)
    def getTransitions(self, transitions, selfIsFromState=True):
        '''Among p_transitions, returns those whose fromState is p_self (if
           p_selfIsFromState is True) or those whose toState is p_self (if
           p_selfIsFromState is False).'''
        res = []
        for t in transitions:
            if self in t.getStates(selfIsFromState):
                res.append(t)
        return res
    def getPermissions(self):
        '''If you get the permissions mapping through self.permissions, dict
           values may be of different types (a list of roles, a single role or
           None). Iy you call this method, you will always get a list which
           may be empty.'''
        res = {}
        for permission, roleValue in self.permissions.iteritems():
            if roleValue == None:
                res[permission] = []
            elif isinstance(roleValue, basestring):
                res[permission] = [roleValue]
            else:
                res[permission] = roleValue
        return res

class Transition:
    def __init__(self, states, condition=True, action=None, notify=None,
                 show=True):
        self.states = states # In its simpler form, it is a tuple with 2
        # states: (fromState, toState). But it can also be a tuple of several
        # (fromState, toState) sub-tuples. This way, you may define only 1
        # transition at several places in the state-transition diagram. It may
        # be useful for "undo" transitions, for example.
        self.condition = condition
        self.action = action
        self.notify = notify # If not None, it is a method telling who must be
        # notified by email after the transition has been executed.
        self.show = show # If False, the end user will not be able to trigger
        # the transition. It will only be possible by code.

    def getUsedRoles(self):
        '''If self.condition is specifies a role.'''
        res = []
        if isinstance(self.condition, basestring):
            res = [self.condition]
        return res

    def isSingle(self):
        '''If this transitions is only define between 2 states, returns True.
           Else, returns False.'''
        return isinstance(self.states[0], State)

    def getStates(self, fromStates=True):
        '''Returns the fromState(s) if p_fromStates is True, the toState(s)
           else. If you want to get the states grouped in tuples
           (fromState, toState), simply use self.states.'''
        res = []
        stateIndex = 1
        if fromStates:
            stateIndex = 0
        if self.isSingle():
            res.append(self.states[stateIndex])
        else:
            for states in self.states:
                theState = states[stateIndex]
                if theState not in res:
                    res.append(theState)
        return res

    def hasState(self, state, isFrom):
        '''If p_isFrom is True, this method returns True if p_state is a
           starting state for p_self. If p_isFrom is False, this method returns
           True if p_state is an ending state for p_self.'''
        stateIndex = 1
        if isFrom:
            stateIndex = 0
        if self.isSingle():
            res = state == self.states[stateIndex]
        else:
            res = False
            for states in self.states:
                if states[stateIndex] == state:
                    res = True
                    break
        return res

class Permission:
    '''If you need to define a specific read or write permission of a given
       attribute of an Appy type, you use the specific boolean parameters
       "specificReadPermission" or "specificWritePermission" for this attribute.
       When you want to refer to those specific read or write permissions when
       defining a workflow, for example, you need to use instances of
       "ReadPermission" and "WritePermission", the 2 children classes of this
       class. For example, if you need to refer to write permission of
       attribute "t1" of class A, write: "WritePermission("A.t1") or
       WritePermission("x.y.A.t1") if class A is not in the same module as
       where you instantiate the class.'''
    def __init__(self, fieldDescriptor):
        self.fieldDescriptor = fieldDescriptor

class ReadPermission(Permission): pass
class WritePermission(Permission): pass

# ------------------------------------------------------------------------------
class Selection:
    '''Instances of this class may be given as validator of a String, in order
       to tell Appy that the validator is a selection that will be computed
       dynamically.'''
    pass

# ------------------------------------------------------------------------------
class Tool:
    '''If you want so define a custom tool class, she must inherit from this
       class.'''
class Flavour:
    '''A flavour represents a given group of configuration options. If you want
       to define a custom flavour class, she must inherit from this class.'''
    def __init__(self, name): self.name = name

# ------------------------------------------------------------------------------
class Config:
    '''If you want to specify some configuration parameters for appy.gen and
       your application, please create an instance of this class and modify its
       attributes. You may put your instance anywhere in your application
       (main package, sub-package, etc).'''

    # The default Config instance, used if the application does not give one.
    defaultConfig = None
    def getDefault():
        if not Config.defaultConfig:
            Config.defaultConfig = Config()
        return Config.defaultConfig
    getDefault = staticmethod(getDefault)

    def __init__(self):
        # For every language code that you specify in this list, appy.gen will
        # produce and maintain translation files.
        self.languages = ['en']
        # People having one of these roles will be able to create instances
        # of classes defined in your application.
        self.defaultCreators = ['Manager', 'Owner']
        # If True, the following flag will produce a minimalist Plone, where
        # some actions, portlets or other stuff less relevant for building
        # web applications, are removed or hidden. Using this produces
        # effects on your whole Plone site!
        self.minimalistPlone = False
        # If you want to replace the Plone front page with a page coming from
        # your application, use the following parameter. Setting
        # frontPage = True will replace the Plone front page with a page
        # whose content will come fron i18n label "front_page_text".
        self.frontPage = False
        # If you don't need the portlet that appy.gen has generated for your
        # application, set the following parameter to False.
        self.showPortlet = True
# ------------------------------------------------------------------------------
