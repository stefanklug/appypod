# ------------------------------------------------------------------------------
from appy.gen.wrappers import AbstractWrapper

# ------------------------------------------------------------------------------
class UserWrapper(AbstractWrapper):

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        return 'view'

    def validateLogin(self, login):
        '''Is this p_login valid?'''
        # The login can't be the id of the whole site or "admin"
        if login == 'admin':
            return self.translate('This username is reserved.')
        # Check that no user or group already uses this login.
        if self.count('User', login=login) or self.count('Group', login=login):
            return self.translate('This login is already in use.')
        return True

    def validatePassword(self, password):
        '''Is this p_password valid?'''
        # Password must be at least 5 chars length
        if len(password) < 5:
            return self.translate('Passwords must contain at least 5 letters.')
        return True

    def showPassword(self):
        '''When must we show the 2 fields for entering a password ?'''
        if self.o.isTemporary(): return 'edit'
        return False

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
                msg = self.translate('Passwords do not match.')
                errors.password1 = msg
                errors.password2 = msg
        return self._callCustom('validate', new, errors)

    def onEdit(self, created):
        self.title = self.firstName + ' ' + self.name
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
            # Updates roles at the Zope level.
            zopeUser = aclUsers.getUserById(login)
            zopeUser.roles = self.roles
        # "self" must be owned by its Zope user
        if 'Owner' not in self.o.get_local_roles_for_userid(login):
            self.o.manage_addLocalRoles(login, ('Owner',))
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
        # Add group global roles
        if not hasattr(aq_base(self), 'groups'): return res
        for roles in self.groups.itervalues():
            for role in roles:
                if role not in res: res.append(role)
        return res

    def getRolesInContext(self, object):
        '''Return the list of global and local (to p_object) roles granted to
           this user (or to any of its groups).'''
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
            for role in roles: res.add(role)
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

    from AccessControl.User import SimpleUser
    SimpleUser.getRoles = getRoles
    SimpleUser.getRolesInContext = getRolesInContext
    SimpleUser.allowed = allowed
# ------------------------------------------------------------------------------
