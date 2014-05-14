# ------------------------------------------------------------------------------
import os, os.path, sys
try:
    from AccessControl.SecurityManagement import \
         newSecurityManager, noSecurityManager
except ImportError:
    pass

# ------------------------------------------------------------------------------
class TestMixin:
    '''This class is mixed in with any ZopeTestCase.'''
    def getNonEmptySubModules(self, moduleName):
        '''Returns the list of sub-modules of p_app that are non-empty.'''
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

    @staticmethod
    def getCovFolder():
        '''Returns the folder where to put the coverage folder if needed.'''
        for arg in sys.argv:
            if arg.startswith('[coverage'):
                return arg[10:].strip(']')
        return
    def _setup(self): pass

# Functions executed before and after every test -------------------------------
def beforeTest(test):
    '''Is executed before every test.'''
    g = test.globs
    g['tool'] = test.app.config.appy()
    cfg = g['tool'].o.getProductConfig()
    g['appFolder'] = cfg.diskFolder
    moduleOrClassName = g['test'].name # Not used yet.
    # Initialize the test
    g['t'] = g['test']

def afterTest(test):
    '''Is executed after every test.'''
    g = test.globs
    appName = g['tool'].o.getAppName()
    exec 'from Products.%s import cov, covFolder, totalNumberOfTests, ' \
         'countTest' % appName
    countTest()
    exec 'from Products.%s import numberOfExecutedTests' % appName
    if cov and (numberOfExecutedTests == totalNumberOfTests):
        cov.stop()
        appModules = test.getNonEmptySubModules(appName)
        # Dumps the coverage report
        # HTML version
        cov.html_report(directory=covFolder, morfs=appModules)
        # Summary in a text file
        f = file('%s/summary.txt' % covFolder, 'w')
        cov.report(file=f, morfs=appModules)
        f.close()
        # Annotated modules
        cov.annotate(directory=covFolder, morfs=appModules)
# ------------------------------------------------------------------------------
