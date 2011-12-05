# ------------------------------------------------------------------------------
from appy.gen.plone25.wrappers import AbstractWrapper

# ------------------------------------------------------------------------------
class GroupWrapper(AbstractWrapper):

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        return 'view'

    def validateLogin(self, login):
        '''Is this p_login valid?'''
        return True

    def getGrantableRoles(self):
        '''Returns the list of roles that the admin can grant to a user.'''
        res = []
        for role in self.o.getProductConfig().grantableRoles:
            res.append( (role, self.translate('role_%s' % role)) )
        return res

    def validate(self, new, errors):
        '''Inter-field validation.'''
        return self._callCustom('validate', new, errors)

    def confirm(self, new):
        '''Use this method for remembering the previous list of users for this
           group.'''
        obj = self.o
        if hasattr(obj.aq_base, '_oldUsers'): del obj.aq_base._oldUsers
        obj._oldUsers = self.users

    def addUser(self, user):
        '''Adds a p_user to this group.'''
        # Update the Ref field.
        self.link('users', user)
        # Update the group-related info on the Zope user.
        zopeUser = user.getZopeUser()
        zopeUser.groups[self.login] = self.roles

    def removeUser(self, user):
        '''Removes a p_user from this group.'''
        self.unlink('users', user)
        # Update the group-related info on the Zope user.
        zopeUser = user.getZopeUser()
        del zopeUser.groups[self.login]

    def onEdit(self, created):
        # Create or update, on every Zope user of this group, group-related
        # information.
        # 1. Remove reference to this group for users that were removed from it
        newUsers = self.users
        # The list of previously existing users does not exist when editing a
        # group from Python. For updating self.users, it is recommended to use
        # methods m_addUser and m_removeUser above.
        oldUsers = getattr(self.o.aq_base, '_oldUsers', ())
        for user in oldUsers:
            if user not in newUsers:
                del user.getZopeUser().groups[self.login]
                self.log('User "%s" removed from group "%s".' % \
                         (user.login, self.login))
        # 2. Add reference to this group for users that were added to it
        for user in newUsers:
            zopeUser = user.getZopeUser()
            # We refresh group-related info on the Zope user even if the user
            # was already in the group.
            zopeUser.groups[self.login] = self.roles
            if user not in oldUsers:
                self.log('User "%s" added to group "%s".' % \
                         (user.login, self.login))
        if hasattr(self.o.aq_base, '_oldUsers'): del self.o._oldUsers
        return self._callCustom('onEdit', created)
# ------------------------------------------------------------------------------
