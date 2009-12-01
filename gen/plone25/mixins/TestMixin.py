# ------------------------------------------------------------------------------
import os, os.path, sys

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

    def getNonEmptySubModules(self, moduleName):
        '''Returns the list fo sub-modules of p_app that are non-empty.'''
        res = []
        try:
            exec 'import %s' % moduleName
            exec 'moduleObj = %s' % moduleName
            moduleFile = moduleObj.__file__
            if moduleFile.endswith('.pyc'):
                moduleFile = moduleFile[:-1]
        except ImportError, ie:
            return res
        except SyntaxError, se:
            return res
        # Include the module if not empty. "Emptyness" is determined by the
        # absence of names beginning with other chars than "__".
        for elem in moduleObj.__dict__.iterkeys():
            if not elem.startswith('__'):
                print 'Element found in this module!!!', moduleObj, elem
                res.append(moduleObj)
                break
        # Include sub-modules if any
        if moduleFile.find("__init__.py") != -1:
            # Potentially, sub-modules exist.
            moduleFolder = os.path.dirname(moduleFile)
            for elem in os.listdir(moduleFolder):
                if elem.startswith('.'): continue
                subModuleName, ext = os.path.splitext(elem)
                if ((ext == '.py') and (subModuleName != '__init__')) or \
                   os.path.isdir(os.path.join(moduleFolder, subModuleName)):
                    # Submodules may be sub-folders or Python files
                    subModuleName = '%s.%s' % (moduleName, subModuleName)
                    res += self.getNonEmptySubModules(subModuleName)
        return res

    def getCovFolder(self):
        '''Returns the folder where to put the coverage folder if needed.'''
        for arg in sys.argv:
            if arg.startswith('[coverage'):
                return arg[10:].strip(']')
        return None

# Functions executed before and after every test -------------------------------
def beforeTest(test):
    '''Is executed before every test.'''
    g = test.globs
    g['tool'] = test.app.plone.get('portal_%s' % g['appName'].lower()).appy()
    cfg = g['tool'].o.getProductConfig()
    g['appFolder'] = cfg.diskFolder
    moduleOrClassName = g['test'].name # Not used yet.
    # Initialize the test
    test.createUser('admin', ('Member','Manager'))
    test.login('admin')
    g['t'] = g['test']
    # Must we perform test coverage ?
    covFolder = test.getCovFolder()
    if covFolder:
        try:
            print 'COV!!!!', covFolder
            import coverage
            app = getattr(cfg, g['tool'].o.getAppName())
            from coverage import coverage
            cov = coverage()
            g['cov'] = cov
            g['covFolder'] = covFolder
            cov.start()
        except ImportError:
            print 'You must install the "coverage" product.'

def afterTest(test):
    '''Is executed after every test.'''
    g = test.globs
    if g.has_key('covFolder'):
        cov = g['cov']
        cov.stop()
        # Dumps the coverage report
        appModules = test.getNonEmptySubModules(g['tool'].o.getAppName())
        cov.html_report(directory=g['covFolder'], morfs=appModules)
# ------------------------------------------------------------------------------
