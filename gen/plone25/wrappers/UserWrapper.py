# ------------------------------------------------------------------------------
from appy.gen.plone25.wrappers import AbstractWrapper

# ------------------------------------------------------------------------------
class UserWrapper(AbstractWrapper):

    def _callCustom(self, methodName, *args, **kwargs):
        '''This wrapper implements some methods like "validate" and "onEdit".
           If the user has defined its own wrapper, its methods will not be
           called. So this method allows, from the methods here, to call the
           user versions.'''
        if len(self.__class__.__bases__) > 1:
            # There is a custom user class
            customUser = self.__class__.__bases__[-1]
            if customUser.__dict__.has_key(methodName):
                customUser.__dict__[methodName](self, *args, **kwargs)

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        return 'view'

    def validateLogin(self, login):
        '''Is this p_login valid?'''
        # The login can't be the id of the whole site or "admin"
        if (login == self.o.portal_url.getPortalObject().getId()) or \
           (login == 'admin'):
            return self.translate(u'This username is reserved. Please choose ' \
                                   'a different name.', domain='plone')
        # Check that the login does not already exist and check some
        # Plone-specific rules.
        pr = self.o.portal_registration
        if not pr.isMemberIdAllowed(login):
            return self.translate(u'The login name you selected is already ' \
               'in use or is not valid. Please choose another.', domain='plone')
        return True

    def validatePassword(self, password):
        '''Is this p_password valid?'''
        # Password must be at least 5 chars length
        if len(password) < 5:
            return self.translate(u'Passwords must contain at least 5 letters.',
                                  domain='plone')
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
                msg = self.translate(u'Passwords do not match.', domain='plone')
                errors.password1 = msg
                errors.password2 = msg
        self._callCustom('validate', new, errors)

    def onEdit(self, created):
        self.title = self.firstName + ' ' + self.name
        pm = self.o.portal_membership
        if created:
            # Create the corresponding Plone user
            pm.addMember(self.login, self.password1, ('Member',), None)
            # Remove our own password copies
            self.password1 = self.password2 = ''
        # Perform updates on the corresponding Plone user
        ploneUser = self.o.portal_membership.getMemberById(self.login)
        ploneUser.setMemberProperties({'fullname': self.title})
        # This object must be owned by its Plone user
        if 'Owner' not in self.o.get_local_roles_for_userid(self.login):
            self.o.manage_addLocalRoles(self.login, ('Owner',))
        # Change group membership according to self.roles. Indeed, instead of
        # granting roles directly to the user, we will add the user to a
        # Appy-created group having this role.
        userRoles = self.roles
        userGroups = ploneUser.getGroups()
        for role in self.o.getProductConfig().grantableRoles:
            # Retrieve the group corresponding to this role
            groupName = '%s_group' % role
            if role == 'Manager':    groupName = 'Administrators'
            elif role == 'Reviewer': groupName = 'Reviewers'
            group = self.o.portal_groups.getGroupById(groupName)
            # Add or remove the user from this group according to its role(s).
            if role in userRoles:
                # Add the user if not already present in the group
                if groupName not in userGroups:
                    group.addMember(self.login)
            else:
                # Remove the user if it was in the corresponding group
                if groupName in userGroups:
                    group.removeMember(self.login)
        self._callCustom('onEdit', created)

    def onDelete(self):
        '''Before deleting myself, I must delete the corresponding Plone
           user.'''
        # Delete the corresponding Plone user
        self.o.acl_users._doDelUser(self.login)
        self.log('Plone user "%s" deleted.' % self.login)
        # Call a custom "onDelete" if any.
        self._callCustom('onDelete')
# ------------------------------------------------------------------------------
