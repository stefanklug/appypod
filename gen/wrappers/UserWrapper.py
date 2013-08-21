# ------------------------------------------------------------------------------
from appy.gen import WorkflowOwner
from appy.gen.wrappers import AbstractWrapper
from appy.gen import utils as gutils

# ------------------------------------------------------------------------------
class UserWrapper(AbstractWrapper):
    workflow = WorkflowOwner

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        # The manager has the possibility to change the login itself.
        if self.user.has_role('Manager'): return True
        return ('view', 'result')

    def showName(tool):
        '''Name and first name, by default, are always shown.'''
        return True

    def showEmail(self):
        '''In most cases, email is the login. Show the field only if it is not
           the case.'''
        email = self.email
        return email and (email != self.login)

    def showRoles(tool):
        '''Only the admin can view or edit roles.'''
        return tool.user.has_role('Manager')

    def validateLogin(self, login):
        '''Is this p_login valid?'''
        # 2 cases: (1) The user is being created and has no login yet, or
        #          (2) The user is being edited and has already a login, that
        #              can potentially be changed.
        if not self.login or (login != self.login):
            # A new p_login is requested. Check if it is valid and free.
            # Firstly, the login can't be the id of the whole site or "admin".
            if login == 'admin': return self.translate('login_reserved')
            # Check that no user or group already uses this login.
            if self.count('User', noSecurity=True, login=login) or \
               self.count('Group', noSecurity=True, login=login):
                return self.translate('login_in_use')
        return True

    def validatePassword(self, password):
        '''Is this p_password valid?'''
        # Password must be at least 5 chars length
        if len(password) < 5:
            return self.translate('password_too_short', mapping={'nb':5})
        return True

    def showPassword(self):
        '''When must we show the 2 fields for entering a password ?'''
        # When someone creates the user
        if self.o.isTemporary(): return 'edit'
        # When the user itself (we don't check role Owner because a Manager can
        # also own a User instance) wants to edit information about himself.
        if self.user.login == self.login: return 'edit'

    def setPassword(self, newPassword=None):
        '''Sets a p_newPassword for self. If p_newPassword is not given, we
           generate one. This method returns the generated password (or simply
           p_newPassword if no generation occurred).'''
        if newPassword:
            msgPart = 'changed'
        else:
            newPassword = self.getField('password1').generatePassword()
            msgPart = 'generated'
        login = self.login
        zopeUser = self.getZopeUser()
        tool = self.tool.o
        zopeUser.__ = tool._encryptPassword(newPassword)
        if self.user.login == login:
            # The user for which we change the password is the currently logged
            # user. So update the authentication cookie, too.
            gutils.writeCookie(login, newPassword, self.request)
        self.log('Password %s by "%s" for "%s".' % \
                 (msgPart, self.user.login, login))
        return newPassword

    def checkPassword(self, clearPassword):
        '''Returns True if p_clearPassword is the correct password for this
           user.'''
        encryptedPassword = self.getZopeUser()._getPassword()
        from AccessControl.AuthEncoding import pw_validate
        return pw_validate(encryptedPassword, clearPassword)

    def setLogin(self, oldLogin, newLogin):
        '''Changes the login of this user from p_oldLogin to p_newLogin.'''
        self.login = newLogin
        # Update the corresponding Zope-level user
        aclUsers = self.o.acl_users
        zopeUser = aclUsers.getUser(oldLogin)
        zopeUser.name = newLogin
        del aclUsers.data[oldLogin]
        aclUsers.data[newLogin] = zopeUser
        # Update the email if the email corresponds to the login.
        email = self.email
        if email == oldLogin:
            self.email = newLogin
        # Update the title
        self.updateTitle()
        # Browse all objects of the database and update potential local roles
        # that referred to the old login.
        context = {'nb': 0, 'old': oldLogin, 'new': newLogin}
        for className in self.o.getProductConfig().allClassNames:
            self.compute(className, context=context, noSecurity=True,
                         expression="ctx['nb'] += obj.o.applyUserIdChange(" \
                                    "ctx['old'], ctx['new'])")
        self.log("Login '%s' renamed to '%s' by '%s'." % \
                 (oldLogin, newLogin, self.user.login))
        self.log('Login change: local roles updated in %d object(s).' % \
                 context['nb'])

    def getGrantableRoles(self):
        '''Returns the list of roles that the admin can grant to a user.'''
        res = []
        for role in self.o.getProductConfig().grantableRoles:
            res.append( (role, self.translate('role_%s' % role)) )
        return res

    def validate(self, new, errors):
        '''Inter-field validation.'''
        page = self.request.get('page', 'main')
        self.o._oldLogin = None
        if page == 'main':
            if hasattr(new, 'password1') and (new.password1 != new.password2):
                msg = self.translate('passwords_mismatch')
                errors.password1 = msg
                errors.password2 = msg
            # Remember the previous login
            if self.login: self.o._oldLogin = self.login
        return self._callCustom('validate', new, errors)

    def updateTitle(self):
        '''Sets a title for this user.'''
        if self.firstName and self.name:
            self.title = '%s %s' % (self.name, self.firstName)
        else:
            self.title = self.login

    def onEdit(self, created):
        self.updateTitle()
        aclUsers = self.o.acl_users
        login = self.login
        if created:
            # Create the corresponding Zope user
            aclUsers._doAddUser(login, self.password1, self.roles, ())
            zopeUser = aclUsers.getUser(login)
            # Remove our own password copies
            self.password1 = self.password2 = ''
            from persistent.mapping import PersistentMapping
            # The following dict will store, for every group, global roles
            # granted to it.
            zopeUser.groups = PersistentMapping()
        else:
            # Update the login itself if the user has changed it.
            oldLogin = self.o._oldLogin
            if oldLogin and (oldLogin != login):
                self.setLogin(oldLogin, login)
            del self.o._oldLogin
            # Update roles at the Zope level.
            zopeUser = self.getZopeUser()
            zopeUser.roles = self.roles
            # Update the password if the user has entered new ones.
            rq = self.request
            if rq.has_key('password1'):
                self.setPassword(rq['password1'])
                self.password1 = self.password2 = ''
        # "self" must be owned by its Zope user.
        if 'Owner' not in self.o.get_local_roles_for_userid(login):
            self.o.manage_addLocalRoles(login, ('Owner',))
        # If the user was created by an Anonymous, Anonymous can't stay Owner
        # of the object.
        if None in self.o.__ac_local_roles__:
            del self.o.__ac_local_roles__[None]
        return self._callCustom('onEdit', created)

    def mayEdit(self):
        custom = self._getCustomMethod('mayEdit')
        if custom: return self._callCustom('mayEdit')
        else:      return True

    def mayDelete(self):
        custom = self._getCustomMethod('mayDelete')
        if custom: return self._callCustom('mayDelete')
        else:      return True

    def getZopeUser(self):
        '''Gets the Zope user corresponding to this user.'''
        return self.o.acl_users.getUser(self.login)

    def onDelete(self):
        '''Before deleting myself, I must delete the corresponding Zope user.'''
        self.o.acl_users._doDelUsers([self.login])
        self.log('User "%s" deleted.' % self.login)
        # Call a custom "onDelete" if any.
        return self._callCustom('onDelete')

    # Standard Zope user methods -----------------------------------------------
    def has_role(self, role, obj=None):
        zopeUser = self.request.zopeUser
        if obj: return zopeUser.has_role(role, obj)
        return zopeUser.has_role(role)

    def has_permission(self, permission, obj):
        return self.request.zopeUser.has_permission(permission, obj)

    def getRoles(self):
        '''This method collects all the roles for this user, not simply
           user.roles, but also roles inherited from group membership.'''
        return self.getZopeUser().getRoles()

# ------------------------------------------------------------------------------
try:
    from AccessControl.PermissionRole import _what_not_even_god_should_do, \
                                             rolesForPermissionOn
    from Acquisition import aq_base
except ImportError:
    pass # For those using Appy without Zope

class ZopeUserPatches:
    '''This class is a fake one that defines Appy variants of some of Zope's
       AccessControl.User methods. The idea is to implement the notion of group
       of users.'''

    def getRoles(self):
        '''Returns the global roles that this user (or any of its groups)
           possesses.'''
        res = list(self.roles)
        if 'Anonymous' not in res: res.append('Authenticated')
        # Add group global roles
        if not hasattr(aq_base(self), 'groups'): return res
        for roles in self.groups.itervalues():
            for role in roles:
                if role not in res: res.append(role)
        return res

    def getRolesInContext(self, object):
        '''Return the list of global and local (to p_object) roles granted to
           this user (or to any of its groups).'''
        if isinstance(object, AbstractWrapper): object = object.o
        object = getattr(object, 'aq_inner', object)
        # Start with user global roles
        res = self.getRoles()
        # Add local roles
        localRoles = getattr(object, '__ac_local_roles__', None)
        if not localRoles: return res
        userId = self.getId()
        groups = getattr(self, 'groups', ())
        for id, roles in localRoles.iteritems():
            if (id != userId) and (id not in groups): continue
            for role in roles:
                if role not in res: res.append(role)
        return res

    def allowed(self, object, object_roles=None):
        '''Checks whether the user has access to p_object. The user (or one of
           its groups) must have one of the roles in p_object_roles.'''
        if object_roles is _what_not_even_god_should_do: return 0
        # If "Anonymous" is among p_object_roles, grant access.
        if (object_roles is None) or ('Anonymous' in object_roles): return 1
        # If "Authenticated" is among p_object_roles, grant access if the user
        # is not anonymous.
        if 'Authenticated' in object_roles and \
           (self.getUserName() != 'Anonymous User'):
            if self._check_context(object): return 1
        # Try first to grant access based on global user roles
        for role in self.getRoles():
            if role not in object_roles: continue
            if self._check_context(object): return 1
            return
        # Try then to grant access based on local roles
        innerObject = getattr(object, 'aq_inner', object)
        localRoles = getattr(innerObject, '__ac_local_roles__', None)
        if not localRoles: return
        userId = self.getId()
        groups = getattr(self, 'groups', ())
        for id, roles in localRoles.iteritems():
            if (id != userId) and (id not in groups): continue
            for role in roles:
                if role not in object_roles: continue
                if self._check_context(object): return 1
                return

    try:
        from AccessControl.User import SimpleUser
        SimpleUser.getRoles = getRoles
        SimpleUser.getRolesInContext = getRolesInContext
        SimpleUser.allowed = allowed
    except ImportError:
        pass
# ------------------------------------------------------------------------------
