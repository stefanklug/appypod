# ------------------------------------------------------------------------------
from appy.gen import WorkflowOwner
from appy.gen.wrappers import AbstractWrapper

# ------------------------------------------------------------------------------
class GroupWrapper(AbstractWrapper):
    workflow = WorkflowOwner

    def showLogin(self):
        '''When must we show the login field?'''
        if self.o.isTemporary(): return 'edit'
        return ('view', 'result')

    def showGroups(self):
        '''Only the admin can view or edit roles.'''
        return self.user.has_role('Manager')

    def validateLogin(self, login):
        '''Is this p_login valid?'''
        return True

    def getGrantableRoles(self):
        '''Returns the list of roles that the admin can grant to a user.'''
        res = []
        for role in self.o.getProductConfig().grantableRoles:
            res.append( (role, self.translate('role_%s' % role)) )
        return res

    def getSelectableUsers(self):
        '''Returns all the users, excepted anon and system.'''
        return [u for u in self.tool.users if u.login not in ('anon', 'system')]

    def validate(self, new, errors):
        '''Inter-field validation.'''
        return self._callCustom('validate', new, errors)

    def onEdit(self, created):
        # If the group was created by anon|system, anon|system can't stay Owner.
        for login in ('anon', 'system'):
            if login in self.o.__ac_local_roles__:
                del self.o.__ac_local_roles__[login]
        return self._callCustom('onEdit', created)
# ------------------------------------------------------------------------------
