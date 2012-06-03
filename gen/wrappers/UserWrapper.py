# ------------------------------------------------------------------------------
from appy.gen import WorkflowOwner
from appy.gen.wrappers import AbstractWrapper

# ------------------------------------------------------------------------------
class UserWrapper(AbstractWrapper):
    workflow = WorkflowOwner

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        return ('view', 'result')

    def showName(self):
        '''Name and first name, by default, are always shown.'''
        return True

    def showEmail(self):
        '''In most cases, email is the login. Show the field only if it is not
           the case.'''
        email = self.email
        return email and (email != self.login)

    def showRoles(self):
        '''Only the admin can view or edit roles.'''
        return self.user.has_role('Manager')

    def validateLogin(self, login):
        '''Is this p_login valid?'''
        # The login can't be the id of the whole site or "admin"
        if login == 'admin': return self.translate('login_reserved')
        # Check that no user or group already uses this login.
        if self.count('User', noSecurity=True, login=login) or \
           self.count('Group', noSecurity=True, login=login):
            self.translate('login_in_use')
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
        # When the user itself (which is Owner of the object representing him)
        # wants to edit information about himself.
        if self.user.has_role('Owner', self): return 'edit'

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
        zopeUser = self.o.acl_users.getUserById(login)
        tool = self.tool.o
        zopeUser.__ = tool._encryptPassword(newPassword)
        if self.user.getId() == login:
            # The user for which we change the password is the currently logged
            # user. So update the authentication cookie, too.
            tool._updateCookie(login, newPassword)
        self.log('Password %s by "%s" for "%s".' % \
                 (msgPart, self.user.getId(), login))
        return newPassword

    def getGrantableRoles(self):
        '''Returns the list of roles that the admin can grant to a user.'''
        res = []
        for role in self.o.getProductConfig().grantableRoles:
            res.append( (role, self.translate('role_%s' % role)) )
        return res

    def validate(self, new, errors):
        '''Inter-field validation.'''
        page = self.request.get('page', 'main')
        if page == 'main':
            if hasattr(new, 'password1') and (new.password1 != new.password2):
                msg = self.translate('passwords_mismatch')
                errors.password1 = msg
                errors.password2 = msg
        return self._callCustom('validate', new, errors)

    def onEdit(self, created):
        self.title = self.login
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
            # Update roles at the Zope level.
            zopeUser = aclUsers.getUserById(login)
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

    def getZopeUser(self):
        '''Gets the Zope user corresponding to this user.'''
        return self.o.acl_users.getUser(self.login)

    def onDelete(self):
        '''Before deleting myself, I must delete the corresponding Zope user.'''
        self.o.acl_users._doDelUsers([self.login])
        self.log('User "%s" deleted.' % self.login)
        # Call a custom "onDelete" if any.
        return self._callCustom('onDelete')

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
