# ------------------------------------------------------------------------------
from appy.px import Px
from appy.fields.string import String
from appy.gen import WorkflowOwner
from appy.gen.layout import summaryPageLayouts
from appy.gen.wrappers import AbstractWrapper
from appy.gen import utils as gutils
from appy.shared import utils as sutils

# ------------------------------------------------------------------------------
class UserWrapper(AbstractWrapper):
    workflow = WorkflowOwner
    specialUsers = ('system', 'anon', 'admin')
    layouts = summaryPageLayouts

    # Display, in the user strip, links to the User instance of the logged user.
    pxUserLink = Px('''
     <td class="userStripText" align=":dright">
      <a if="cfg.userLink" href=":user.url"><img src=":url('user')"/>
       <span style="padding: 0 3px">:user.getTitle()</span></a>
      <x if="not cfg.userLink">:user.getTitle()</x>
     </td>''')

    def isSpecial(self): return self.login in self.specialUsers

    def getTitle(self, normalized=False):
        '''Returns a nice name for this user, based on available information:
           name/first name or title or login. If p_normalized is True, special
           chars (like accents) are converted to ascii chars.'''
        # Manage the special case of an anonymous user.
        login = self.login
        if login == 'anon':
            res = self.translate('anonymous')
        else:
            res = self.title or login
        if not normalized: return res
        return sutils.normalizeString(name)

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        # The manager has the possibility to change the login itself (local
        # users only).
        if self.user.has_role('Manager') and (self.source == 'zodb'):
            return True
        return ('view', 'result')

    def showName(self):
        '''Name and first name, by default, can not be edited for non-local
           users.'''
        if (self.source != 'zodb'): return ('view', 'result')
        return True

    def showEmail(self):
        '''In most cases, email is the login. Show the field only if it is not
           the case.'''
        email = self.email
        if email and (email != self.login):
            if (self.source != 'zodb'): return ('view', 'result')
            return True

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
            # Some logins are not allowed.
            if login in self.specialUsers:
                return self.translate('login_reserved')
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

    def showPassword12(self):
        '''Fields "passwords1" and "password2", used only for modifying a
           password on an existing user (on specific page "passwords"), must be
           shown only for the user that can modify his password.'''
        # On creation, fields "password3" and "password4" are used
        if self.o.isTemporary(): return
        # When the user itself (we don't check role Owner because a Manager can
        # also own a User instance) wants to edit information about himself.
        if (self.user.login == self.login) and (self.source == 'zodb'):
            return 'edit'

    def showPassword34(self):
        '''Fields "password3" and "password4", used only on the main page for
           entering a password when creating a new user, must be shown only when
           the object is temporary.'''
        if self.o.isTemporary(): return 'edit'

    def encryptPassword(self, clearPassword):
        '''Returns p_clearPassword, encrypted.'''
        return self.o.getTool().acl_users._encryptPassword(clearPassword)

    def setPassword(self, newPassword=None, log=True):
        '''Sets a p_newPassword for self. If p_newPassword is not given, we
           generate one. This method returns the generated password (or simply
           p_newPassword if no generation occurred).'''
        if newPassword != None:
            msgPart = 'changed'
        else:
            # Take any password field for generating a new password
            newPassword = self.getField('password2').generatePassword()
            msgPart = 'generated'
        login = self.login
        zopeUser = self.getZopeUser()
        tool = self.tool.o
        zopeUser.__ = self.encryptPassword(newPassword)
        if self.user and (self.user.login == login):
            # The user for which we change the password is the currently logged
            # user. So update the authentication cookie, too.
            gutils.writeCookie(login, newPassword, self.request)
        if log:
            self.log('password %s for %s.' % (msgPart, login))
        return newPassword

    def setEncryptedPassword(self, encryptedPassword):
        '''Sets p_encryptedPassword for this user. m_setPassword above starts
           for a clear (given or generated) password. This one simply sets an
           already encrypted password for this user.'''
        self.getZopeUser().__ = encryptedPassword

    def checkPassword(self, clearPassword):
        '''Returns True if p_clearPassword is the correct password for this
           user.'''
        encryptedPassword = self.getZopeUser()._getPassword()
        from AccessControl.AuthEncoding import pw_validate
        return pw_validate(encryptedPassword, clearPassword)

    def getMailRecipient(self):
        '''Returns, for this user, the "recipient string" (first name, name,
           email) as can be used for sending an email.'''
        res = self.email or self.login
        # Ensure this is really an email
        if not String.EMAIL.match(res): return
        return '%s <%s>' % (self.title, res)

    def setLogin(self, oldLogin, newLogin):
        '''Changes the login of this user from p_oldLogin to p_newLogin.'''
        self.login = newLogin
        # Update the corresponding Zope-level user
        aclUsers = self.o.acl_users
        zopeUser = aclUsers.data[oldLogin]
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
        for className in self.tool.o.getAllClassNames():
            self.compute(className, context=context, noSecurity=True,
                         expression="ctx['nb'] += obj.o.applyUserIdChange(" \
                                    "ctx['old'], ctx['new'])")
        self.log("login %s renamed to %s." % (oldLogin, newLogin))
        self.log('login change: local roles updated in %d object(s).' % \
                 context['nb'])

    def getGrantableRoles(self):
        '''Returns the list of roles that the admin can grant to a user.'''
        res = []
        for role in self.o.getProductConfig().grantableRoles:
            res.append( (role, self.translate('role_%s' % role)) )
        return res

    def validate(self, new, errors):
        '''Inter-field validation.'''
        self.o._oldLogin = None
        # Check that passwords match, either on page "passwords" (passwords 1
        # and 2) or on page "main" (passwords 3 and 4).
        for i in (1, 3):
            passwordA = 'password%d' % i
            passwordB = 'password%d' % (i + 1)
            if hasattr(new, passwordA) and \
               (getattr(new, passwordA) != getattr(new, passwordB)):
                msg = self.translate('passwords_mismatch')
                setattr(errors, passwordA, msg)
                setattr(errors, passwordB, msg)
            # Remember the previous login
            if self.login: self.o._oldLogin = self.login
        return self._callCustom('validate', new, errors)

    def updateTitle(self):
        '''Sets a title for this user.'''
        if self.firstName and self.name:
            self.title = '%s %s' % (self.name, self.firstName)
        else:
            self.title = self.title or self.login

    def ensureAdminIsManager(self):
        '''User 'admin' must always have role 'Manager'.'''
        if self.o.id == 'admin':
            roles = self.roles
            if 'Manager' not in roles:
                if not roles: roles = ['Manager']
                else: roles.append('Manager')
                self.roles = roles

    def getSupTitle(self, nav):
        '''Display a specific icon if the user is a local copy of an external
           (ie, ldap) user.'''
        if self.source == 'zodb': return
        return '<img src="%s/ui/external.png"/>' % self.o.getTool().getSiteUrl()

    def onEdit(self, created):
        '''Triggered when a User is created or updated.'''
        login = self.login
        # Is it a local User or a LDAP User?
        isLocal = self.source == 'zodb'
        # Ensure correctness of some infos about this user.
        if isLocal:
            self.updateTitle()
            self.ensureAdminIsManager()
        if created:
            # Create the corresponding Zope user
            from AccessControl.User import User as ZopeUser
            password = self.encryptPassword(self.password3)
            zopeUser = ZopeUser(login, password, self.roles, ())
            # Add it in acl_users if it is a local user.
            if isLocal: self.o.acl_users.data[login] = zopeUser
            # Add it in self.o._zopeUser if it is a LDAP user
            else: self.o._zopeUser = zopeUser
            # Remove our own password copies
            self.password3 = self.password4 = ''
        else:
            # Update the login itself if the user has changed it
            oldLogin = self.o._oldLogin
            if oldLogin and (oldLogin != login):
                self.setLogin(oldLogin, login)
            del self.o._oldLogin
            # Update roles at the Zope level
            zopeUser = self.getZopeUser()
            zopeUser.roles = self.roles
            # Update the password if the user has entered new ones
            rq = self.request
            if rq.get('page', 'main') == 'passwords':
                self.setPassword(rq['password1'])
                self.password1 = self.password2 = ''
        # "self" must be owned by its Zope user.
        if 'Owner' not in self.o.get_local_roles_for_userid(login):
            self.o.manage_addLocalRoles(login, ('Owner',))
        # If the user was created by anon|system, anon|system can't stay Owner.
        for login in ('anon', 'system'):
            if login in self.o.__ac_local_roles__:
                del self.o.__ac_local_roles__[login]
        return self._callCustom('onEdit', created)

    def mayEdit(self):
        '''No one can edit users "system" and "anon".'''
        if self.o.id in ('anon', 'system'): return
        # Call custom "mayEdit" when present.
        custom = self._getCustomMethod('mayEdit')
        if custom: return self._callCustom('mayEdit')
        return True

    def mayDelete(self):
        '''No one can delete users "system", "anon" and "admin".'''
        if self.o.id in self.specialUsers: return
        # Call custom "mayDelete" when present.
        custom = self._getCustomMethod('mayDelete')
        if custom: return self._callCustom('mayDelete')
        return True

    def getZopeUser(self):
        '''Gets the Zope user corresponding to this user.'''
        if self.source == 'zodb':
            return self.o.acl_users.data.get(self.login, None)
        return self.o._zopeUser

    def onDelete(self):
        '''Before deleting myself, I must delete the corresponding Zope user
           (for local users only).'''
        if self.source == 'zodb': del self.o.acl_users.data[self.login]
        self.log('user %s deleted.' % self.login)
        # Call a custom "onDelete" if any.
        return self._callCustom('onDelete')

    def getLogins(self, groupsOnly=False):
        '''Gets all the logins that can "match" this user: it own login
           (excepted if p_groupsOnly is True) and the logins of all the groups
           he belongs to.'''
        # Try first to get those logins from a cache on the request, if this
        # user corresponds to the logged user.
        rq = self.request
        if (self.user == self) and hasattr(rq, 'userLogins'):
            return rq.userLogins
        # Compute it
        res = [group.login for group in self.groups]
        if not groupsOnly: res.append(self.login)
        return res

    def getRoles(self):
        '''This method returns all the global roles for this user, not simply
           self.roles, but also "ungrantable roles" (like Anonymous or
           Authenticated) and roles inherited from group membership.'''
        # Try first to get those roles from a cache on the request, if this user
        # corresponds to the logged user.
        rq = self.request
        if (self.user == self) and hasattr(rq, 'userRoles'):
            return rq.userRoles
        # Compute it.
        res = list(self.roles)
        # Add ungrantable roles
        if self.o.id == 'anon':
            res.append('Anonymous')
        else:
            res.append('Authenticated')
        # Add group global roles
        for group in self.groups:
            for role in group.roles:
                if role not in res: res.append(role)
        return res

    def getRolesFor(self, obj):
        '''Gets the roles the user has in the context of p_obj: its global roles
           + its roles which are local to p_obj.'''
        obj = obj.o
        # Start with user global roles.
        res = self.getRoles()
        # Add local roles, granted to the user directly or to one of its groups.
        localRoles = getattr(obj.aq_base, '__ac_local_roles__', None)
        if not localRoles: return res
        # Gets the logins of this user and all its groups.
        logins = self.getLogins()
        for login, roles in localRoles.iteritems():
            # Ignore logins not corresponding to this user.
            if login not in logins: continue
            for role in roles:
                if role not in res: res.append(role)
        return res

    def addRole(self, role):
        '''Adds p_role to the user's global roles.'''
        roles = self.roles
        if role in roles: return
        roles = list(roles)
        roles.append(role)
        self.roles = roles
        self.getZopeUser().roles = roles

    def has_role(self, role, obj=None):
        '''Has the logged user some p_role? If p_obj is None, check if the user
           has p_role globally; else, check if he has this p_role in the context
           of p_obj.'''
        if obj:
            roles = self.getRolesFor(obj)
        else:
            roles = self.getRoles()
        return role in roles

    def has_permission(self, permission, obj):
        '''Has the logged user p_permission on p_obj?'''
        obj = obj.o
        # What are the roles which are granted p_permission on p_obj?
        allowedRoles = obj.getRolesFor(permission)
        # Grant access if "Anonymous" is among roles.
        if ('Anonymous' in allowedRoles): return True
        # Grant access if "Authenticated" is among p_roles and the user is not
        # anonymous.
        if ('Authenticated' in allowedRoles) and (self.o.id != 'anon'):
            return True
        # Grant access based on global user roles.
        for role in self.getRoles():
            if role in allowedRoles: return True
        # Grant access based on local roles
        localRoles = getattr(obj.aq_base, '__ac_local_roles__', None)
        if not localRoles: return
        # Gets the logins of this user and all its groups.
        userLogins = self.getLogins()
        for login, roles in localRoles.iteritems():
            # Ignore logins not corresponding to this user.
            if login not in userLogins: continue
            for role in roles:
                if role in allowedRoles: return True
# ------------------------------------------------------------------------------
