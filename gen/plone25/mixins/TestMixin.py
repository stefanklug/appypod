# ------------------------------------------------------------------------------
class TestMixin:
    '''This class is mixed in with any PloneTestCase.'''
    def createUser(self, userId, roles):
        '''Creates a user p_name p_with some p_roles.'''
        pms = self.portal.portal_membership
        pms.addMember(userId, 'password', [], [])
        self.setRoles(roles, name=userId)

    def changeUser(self, userId):
        '''Logs out currently logged user and logs in p_loginName.'''
        self.logout()
        self.login(userId)

# Functions executed before and after every test -------------------------------
def beforeTest(test):
    g = test.globs
    g['tool'] = test.app.plone.get('portal_%s' % g['appName'].lower()).appy()
    g['appFolder'] = g['tool'].o.getProductConfig().diskFolder
    moduleOrClassName = g['test'].name # Not used yet.
    # Initialize the test
    test.createUser('admin', ('Member','Manager'))
    test.login('admin')
    g['t'] = g['test']

def afterTest(test): pass
# ------------------------------------------------------------------------------
