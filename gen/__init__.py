# ------------------------------------------------------------------------------
import types, string
from appy.gen.mail import sendNotification
from appy.gen import utils as gutils

# ------------------------------------------------------------------------------
# Import stuff from appy.fields (and from a few other places too).
# This way, when an app gets "from appy.gen import *", everything is available.
# ------------------------------------------------------------------------------
from appy.fields import Field
from appy.fields.action import Action
from appy.fields.boolean import Boolean
from appy.fields.computed import Computed
from appy.fields.date import Date
from appy.fields.file import File
from appy.fields.float import Float
from appy.fields.info import Info
from appy.fields.integer import Integer
from appy.fields.list import List
from appy.fields.pod import Pod
from appy.fields.ref import Ref, autoref
from appy.fields.string import String, Selection
from appy.fields.search import Search, UiSearch
from appy.fields.group import Group, Column
from appy.fields.page import Page
from appy.fields.phase import Phase
from appy.gen.layout import Table
from appy.px import Px
from appy import Object
No = gutils.No

# Default Appy permissions -----------------------------------------------------
r, w, d = ('read', 'write', 'delete')

class Import:
    '''Used for describing the place where to find the data to use for creating
       an object.'''
    def __init__(self, path, onElement=None, headers=(), sort=None):
        self.id = 'import'
        self.path = path
        # p_onElement hereafter must be a function (or a static method) that
        # will be called every time an element to import is found. It takes a
        # single arg that is the absolute filen name of the file to import,
        # within p_path. It must return a list of info about the element, or
        # None if the element must be ignored. The list will be used to display
        # information about the element in a tabular form.
        self.onElement = onElement
        # The following attribute must contain the names of the column headers
        # of the table that will display elements to import (retrieved from
        # calls to self.onElement). Every not-None element retrieved from
        # self.onElement must have the same length as self.headers.
        self.headers = headers
        # The following attribute must store a function or static method that
        # will be used to sort elements to import. It will be called with a
        # single param containing the list of all not-None elements as retrieved
        # by calls to self.onElement (but with one additional first element in
        # every list, which is the absolute file name of the element to import)
        # and must return a similar, sorted, list.
        self.sort = sort

# Workflow-specific types and default workflows --------------------------------
class Role:
    '''Represents a role.'''
    zopeRoles = ('Manager', 'Owner', 'Anonymous', 'Authenticated')
    zopeLocalRoles = ('Owner',)
    zopeUngrantableRoles = ('Anonymous', 'Authenticated')
    def __init__(self, name, local=False, grantable=True):
        self.name = name
        self.local = local # True if it can be used as local role only.
        # It is a standard Zope role or an application-specific one?
        self.zope = name in self.zopeRoles
        if self.zope and (name in self.zopeLocalRoles):
            self.local = True
        self.grantable = grantable
        if self.zope and (name in self.zopeUngrantableRoles):
            self.grantable = False
        # An ungrantable role is one that is, like the Anonymous or
        # Authenticated roles, automatically attributed to a user.

class State:
    def __init__(self, permissions, initial=False, phase=None, show=True):
        self.usedRoles = {}
        # The following dict ~{s_permissionName:[s_roleName|Role_role]}~
        # gives, for every permission managed by a workflow, the list of roles
        # for which the permission is granted in this state. Standard
        # permissions are 'read', 'write' and 'delete'.
        self.permissions = permissions 
        self.initial = initial
        self.phase = phase
        self.show = show
        # Standardize the way roles are expressed within self.permissions
        self.standardizeRoles()

    def getName(self, wf):
        '''Returns the name for this state in workflow p_wf.'''
        for name in dir(wf):
            value = getattr(wf, name)
            if (value == self): return name

    def getRole(self, role):
        '''p_role can be the name of a role or a Role instance. If it is the
           name of a role, this method returns self.usedRoles[role] if it
           exists, or creates a Role instance, puts it in self.usedRoles and
           returns it else. If it is a Role instance, the method stores it in
           self.usedRoles if it is not in it yet and returns it.'''
        if isinstance(role, basestring):
            if role in self.usedRoles:
                return self.usedRoles[role]
            else:
                theRole = Role(role)
                self.usedRoles[role] = theRole
                return theRole
        else:
            if role.name not in self.usedRoles:
                self.usedRoles[role.name] = role
            return role

    def standardizeRoles(self):
        '''This method converts, within self.permissions, every role to a
           Role instance. Every used role is stored in self.usedRoles.'''
        for permission, roles in self.permissions.items():
            if isinstance(roles, basestring) or isinstance(roles, Role):
                self.permissions[permission] = [self.getRole(roles)]
            elif roles:
                rolesList = []
                for role in roles:
                    rolesList.append(self.getRole(role))
                self.permissions[permission] = rolesList

    def getUsedRoles(self): return self.usedRoles.values()

class Transition:
    def __init__(self, states, condition=True, action=None, notify=None,
                 show=True, confirm=False):
        self.states = states # In its simpler form, it is a tuple with 2
        # states: (fromState, toState). But it can also be a tuple of several
        # (fromState, toState) sub-tuples. This way, you may define only 1
        # transition at several places in the state-transition diagram. It may
        # be useful for "undo" transitions, for example.
        self.condition = condition
        if isinstance(condition, basestring):
            # The condition specifies the name of a role.
            self.condition = Role(condition)
        self.action = action
        self.notify = notify # If not None, it is a method telling who must be
        # notified by email after the transition has been executed.
        self.show = show # If False, the end user will not be able to trigger
        # the transition. It will only be possible by code.
        self.confirm = confirm # If True, a confirm popup will show up.

    def getName(self, wf):
        '''Returns the name for this state in workflow p_wf.'''
        for name in dir(wf):
            value = getattr(wf, name)
            if (value == self): return name

    def getUsedRoles(self):
        '''self.condition can specify a role.'''
        res = []
        if isinstance(self.condition, Role):
            res.append(self.condition)
        return res

    def isSingle(self):
        '''If this transition is only defined between 2 states, returns True.
           Else, returns False.'''
        return isinstance(self.states[0], State)

    def isShowable(self, workflow, obj):
        '''Is this transition showable?'''
        if callable(self.show):
            return self.show(workflow, obj.appy())
        else:
            return self.show

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

    def isTriggerable(self, obj, wf, noSecurity=False):
        '''Can this transition be triggered on p_obj?'''
        wf = wf.__instance__ # We need the prototypical instance here.
        # Checks that the current state of the object is a start state for this
        # transition.
        objState = obj.State(name=False)
        if self.isSingle():
            if objState != self.states[0]: return False
        else:
            startFound = False
            for startState, stopState in self.states:
                if startState == objState:
                    startFound = True
                    break
            if not startFound: return False
        # Check that the condition is met
        user = obj.getTool().getUser()
        if isinstance(self.condition, Role):
            # Condition is a role. Transition may be triggered if the user has
            # this role.
            if noSecurity: return True
            return user.has_role(self.condition.name, obj)
        elif type(self.condition) == types.FunctionType:
            return self.condition(wf, obj.appy())
        elif type(self.condition) in (tuple, list):
            # It is a list of roles and/or functions. Transition may be
            # triggered if user has at least one of those roles and if all
            # functions return True.
            hasRole = None
            for roleOrFunction in self.condition:
                if isinstance(roleOrFunction, basestring):
                    if hasRole == None:
                        hasRole = False
                    if user.has_role(roleOrFunction, obj) or noSecurity:
                        hasRole = True
                elif type(roleOrFunction) == types.FunctionType:
                    if not roleOrFunction(wf, obj.appy()):
                        return False
            if hasRole != False:
                return True

    def executeAction(self, obj, wf):
        '''Executes the action related to this transition.'''
        msg = ''
        obj = obj.appy()
        wf = wf.__instance__ # We need the prototypical instance here.
        if type(self.action) in (tuple, list):
            # We need to execute a list of actions
            for act in self.action:
                msgPart = act(wf, obj)
                if msgPart: msg += msgPart
        else: # We execute a single action only.
            msgPart = self.action(wf, obj)
            if msgPart: msg += msgPart
        return msg

    def trigger(self, transitionName, obj, wf, comment, doAction=True,
                doNotify=True, doHistory=True, doSay=True):
        '''This method triggers this transition on p_obj. The transition is
           supposed to be triggerable (call to self.isTriggerable must have been
           performed before calling this method). If p_doAction is False, the
           action that must normally be executed after the transition has been
           triggered will not be executed. If p_doNotify is False, the
           email notifications that must normally be launched after the
           transition has been triggered will not be launched. If p_doHistory is
           False, there will be no trace from this transition triggering in the
           workflow history. If p_doSay is False, we consider the transition is
           trigger programmatically, and no message is returned to the user.'''
        # Create the workflow_history dict if it does not exist.
        if not hasattr(obj.aq_base, 'workflow_history'):
            from persistent.mapping import PersistentMapping
            obj.workflow_history = PersistentMapping()
        # Create the event list if it does not exist in the dict
        if not obj.workflow_history: obj.workflow_history['appy'] = ()
        # Get the key where object history is stored (this overstructure is
        # only there for backward compatibility reasons)
        key = obj.workflow_history.keys()[0]
        # Identify the target state for this transition
        if self.isSingle():
            targetState = self.states[1]
            targetStateName = targetState.getName(wf)
        else:
            startState = obj.State(name=False)
            for sState, tState in self.states:
                if startState == sState:
                    targetState = tState
                    targetStateName = targetState.getName(wf)
                    break
        # Create the event and add it in the object history
        action = transitionName
        if transitionName == '_init_': action = None
        if not doHistory: comment = '_invisible_'
        obj.addHistoryEvent(action, review_state=targetStateName,
                            comments=comment)
        # Reindex the object if required. Not only security-related indexes
        # (Allowed, State) need to be updated here.
        if not obj.isTemporary(): obj.reindex()
        # Execute the related action if needed
        msg = ''
        if doAction and self.action: msg = self.executeAction(obj, wf)
        # Send notifications if needed
        if doNotify and self.notify and obj.getTool(True).mailEnabled:
            sendNotification(obj.appy(), self, transitionName, wf)
        # Return a message to the user if needed
        if not doSay or (transitionName == '_init_'): return
        if not msg: msg = obj.translate('object_saved')
        obj.say(msg)

class Permission:
    '''If you need to define a specific read or write permission of a given
       attribute of an Appy type, you use the specific boolean parameters
       "specificReadPermission" or "specificWritePermission" for this attribute.
       When you want to refer to those specific read or write permissions when
       defining a workflow, for example, you need to use instances of
       "ReadPermission" and "WritePermission", the 2 children classes of this
       class. For example, if you need to refer to write permission of
       attribute "t1" of class A, write: WritePermission("A.t1") or
       WritePermission("x.y.A.t1") if class A is not in the same module as
       where you instantiate the class.

       Note that this holds only if you use attributes "specificReadPermission"
       and "specificWritePermission" as booleans. When defining named
       (string) permissions, for referring to it you simply use those strings,
       you do not create instances of ReadPermission or WritePermission.'''

    allowedChars = string.digits + string.letters + '_'

    def __init__(self, fieldDescriptor):
        self.fieldDescriptor = fieldDescriptor

    def getName(self, wf, appName):
        '''Returns the name of this permission.'''
        className, fieldName = self.fieldDescriptor.rsplit('.', 1)
        if className.find('.') == -1:
            # The related class resides in the same module as the workflow
            fullClassName= '%s_%s' % (wf.__module__.replace('.', '_'),className)
        else:
            # className contains the full package name of the class
            fullClassName = className.replace('.', '_')
        # Read or Write ?
        if self.__class__.__name__ == 'ReadPermission': access = 'Read'
        else: access = 'Write'
        return '%s: %s %s %s' % (appName, access, fullClassName, fieldName)

class ReadPermission(Permission): pass
class WritePermission(Permission): pass

class WorkflowAnonymous:
    '''One-state workflow allowing anyone to consult and Manager to edit.'''
    mgr = 'Manager'
    o = 'Owner'
    active = State({r:(mgr, 'Anonymous', 'Authenticated'), w:(mgr,o),d:(mgr,o)},
                   initial=True)

class WorkflowAuthenticated:
    '''One-state workflow allowing authenticated users to consult and Manager
       to edit.'''
    mgr = 'Manager'
    o = 'Owner'
    active = State({r:(mgr, 'Authenticated'), w:(mgr,o), d:(mgr,o)},
                   initial=True)

class WorkflowOwner:
    '''One-state workflow allowing only manager and owner to consult and
       edit.'''
    mgr = 'Manager'
    o = 'Owner'
    active = State({r:(mgr, o), w:(mgr, o), d:mgr}, initial=True)

# ------------------------------------------------------------------------------
class Model: pass
class Tool(Model):
    '''If you want to extend or modify the Tool class, subclass me.'''
class User(Model):
    '''If you want to extend or modify the User class, subclass me.'''

# ------------------------------------------------------------------------------
class LdapConfig:
    '''Parameters for authenticating users to an LDAP server.'''
    ldapAttributes = { 'loginAttribute':None, 'emailAttribute':'email',
                       'fullNameAttribute':'title',
                       'firstNameAttribute':'firstName',
                       'lastNameAttribute':'name' }

    def __init__(self):
        self.server = '' # Name of the LDAP server
        self.port = None # Port for this server.
        # Login and password of the technical power user that the Appy
        # application will use to connect to the LDAP.
        self.adminLogin = ''
        self.adminPassword = ''
        # LDAP attribute to use as login for authenticating users.
        self.loginAttribute = 'dn' # Can also be "mail", "sAMAccountName", "cn"
        # LDAP attributes for storing email
        self.emailAttribute = None
        # LDAP attribute for storing full name (first + last name)
        self.fullNameAttribute = None
        # Alternately, LDAP attributes for storing 1st & last names separately.
        self.firstNameAttribute = None
        self.lastNameAttribute = None
        # LDAP classes defining the users stored in the LDAP.
        self.userClasses = ('top', 'person')
        self.baseDn = '' # Base DN where to find users in the LDAP.
        self.scope = 'SUBTREE' # Scope of the search within self.baseDn

    def getServerUri(self):
        '''Returns the complete URI for accessing the LDAP, ie
           "ldap://some.ldap.server:389".'''
        port = self.port or 389
        return 'ldap://%s:%d' % (self.server, port)

    def getUserFilterValues(self, login):
        '''Gets the filter values required to perform a query for finding user
           corresponding to p_login in the LDAP.'''
        res = [(self.loginAttribute, login)]
        for userClass in self.userClasses:
            res.append( ('objectClass', userClass) )
        return res

    def getUserAttributes(self):
        '''Gets the attributes we want to get from the LDAP for characterizing
           a user.'''
        res = [self.loginAttribute]
        for name in self.ldapAttributes.iterkeys():
            if getattr(self, name):
                res.append(getattr(self, name))
        return res

    def getUserParams(self, ldapData):
        '''Formats the user-related p_ldapData retrieved from the ldap, as a
           dict of params usable for creating or updating the corresponding
           Appy user.'''
        res = {}
        for name, appyName in self.ldapAttributes.iteritems():
            if not appyName: continue
            # Get the name of the attribute as known in the LDAP.
            ldapName = getattr(self, name)
            if not ldapName: continue
            if ldapData.has_key(ldapName) and ldapData[ldapName]:
                res[appyName] = ldapData[ldapName]
        return res

# ------------------------------------------------------------------------------
class Config:
    '''If you want to specify some configuration parameters for appy.gen and
       your application, please create a class named "Config" in the __init__.py
       file of your application and override some of the attributes defined
       here, ie:

       import appy.gen
       class Config(appy.gen.Config):
           langages = ('en', 'fr')
    '''
    # For every language code that you specify in this list, appy.gen will
    # produce and maintain translation files.
    languages = ['en']
    # If languageSelector is True, on every page, a language selector will
    # allow to switch between languages defined in self.languages. Else,
    # the browser-defined language will be used for choosing the language
    # of returned pages.
    languageSelector = False
    # People having one of these roles will be able to create instances
    # of classes defined in your application.
    defaultCreators = ['Manager']
    # Number of translations for every page on a Translation object
    translationsPerPage = 30
    # Language that will be used as a basis for translating to other
    # languages.
    sourceLanguage = 'en'
    # Activate or not the button on home page for asking a new password
    activateForgotPassword = True
    # Enable session timeout?
    enableSessionTimeout = False
    # If the following field is True, the login/password widget will be
    # discreet. This is for sites where authentication is not foreseen for
    # the majority of visitors (just for some administrators).
    discreetLogin = False
    # When using Ogone, place an instance of appy.gen.ogone.OgoneConfig in
    # the field below.
    ogone = None
    # When using Google analytics, specify here the Analytics ID
    googleAnalyticsId = None
    # Create a group for every global role?
    groupsForGlobalRoles = False
    # When using a LDAP for authenticating users, place an instance of class
    # LdapConfig above in the field below.
    ldap = None
# ------------------------------------------------------------------------------
