'''This sript allows to wrap a Python module into an egg.'''

# ------------------------------------------------------------------------------
import os, os.path, sys, zipfile, appy
from appy.bin.clean import Cleaner
from appy.shared.utils import FolderDeleter, copyFolder, cleanFolder
from optparse import OptionParser

# ------------------------------------------------------------------------------
class EggifierError(Exception): pass
ERROR_CODE = 1
eggInfo = '''from setuptools import setup, find_packages
import os
setup(name = "%s", version = "%s", description = "%s",
      long_description = "%s",
      author = "%s", author_email = "%s",
      license = "GPL", keywords = "plone, appy", url = '%s',
      classifiers = ["Framework :: Appy", "Programming Language :: Python",],
      packages=find_packages(exclude=['ez_setup']), include_package_data = True,
      namespace_packages=['%s'], zip_safe = False,
      install_requires=['setuptools'],)'''
initInfo = '''
# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
'''

# ------------------------------------------------------------------------------
class EggifyScript:
    '''usage: python eggify.py pythonModule [options]
       pythonModule is the path to a Python module or the name of a Python file.

       Available options are:
         -a --appy      If specified, the Appy module (light version, without
                        test code) will be included in the egg.
         -r --result    The path where to create the egg (defaults to the
                        current working directory)
         -p --products  If specified, the module will be packaged in the
                        "Products" namespace.
         -v --version   Egg version. Defaults to 1.0.0.
    '''
    def createSetupFile(self, eggTempFolder):
        '''Creates the setup.py file in the egg.'''
        content = eggInfo % (self.moduleName, self.version, 'Appy module',
                             'Appy module', 'Gaetan Delannay',
                             'gaetan.delannay AT gmail.com',
                             'http://appyframework.org',
                             self.moduleName.split('.')[0])
        f = file(os.path.join(eggTempFolder, 'setup.py'), 'w')
        f.write(content)
        f.close()

    def createInitFile(self, eggTempFolder):
        '''Creates the ez_setup-compliant __init__ files.'''
        initPath = os.path.join(eggTempFolder,self.moduleName.split('.')[0])
        f = file(os.path.join(initPath, '__init__.py'), 'w')
        f.write(initInfo)
        f.close()

    def getEggName(self):
        '''Creates the egg name.'''
        return '%s-%s.egg' % (self.moduleName, self.version)

    zipExclusions = ('.bzr', 'doc', 'test', 'versions')
    def dirInZip(self, dir):
        '''Returns True if the p_dir must be included in the zip.'''
        for exclusion in self.zipExclusions:
            if dir.endswith(exclusion) or ('/%s/' % exclusion in dir):
                return False
        return True
    
    def zipResult(self, eggFullName, eggTempFolder):
        '''Zips the result and removes the egg temp folder.'''
        zipFile = zipfile.ZipFile(eggFullName, 'w', zipfile.ZIP_DEFLATED)
        # Put the Python module inside the egg.
        prefix = os.path.dirname(eggTempFolder)
        for dir, dirnames, filenames in os.walk(eggTempFolder):
            for f in filenames:
                fileName = os.path.join(dir, f)
                zipFile.write(fileName, fileName[len(prefix):])
        # Put the Appy module inside it if required.
        if self.includeAppy:
            eggPrefix = '%s/%s' % (eggTempFolder[len(prefix):],
                                   self.moduleName.replace('.', '/'))
            # Where is Appy?
            appyPath = os.path.dirname(appy.__file__)
            appyPrefix = os.path.dirname(appyPath)
            # Clean the Appy folder
            Cleaner().run(verbose=False)
            # Insert appy files into the zip
            for dir, dirnames, filenames in os.walk(appyPath):
                if not self.dirInZip(dir): continue
                for f in filenames:
                    fileName = os.path.join(dir, f)
                    zipName = eggPrefix + fileName[len(appyPrefix):]
                    zipFile.write(fileName, zipName)
        zipFile.close()
        # Remove the temp egg folder.
        FolderDeleter.delete(eggTempFolder)

    def eggify(self):
        '''Let's wrap a nice Python module into an ugly egg.'''
        j = os.path.join
        # First, clean the Python module
        cleanFolder(self.pythonModule, verbose=False)
        # Create the egg folder
        eggFullName = j(self.eggFolder, self.eggName)
        if os.path.exists(eggFullName):
            os.remove(eggFullName)
            print('Existing "%s" was removed.' % eggFullName)
        # Create a temp folder where to store the egg
        eggTempFolder = os.path.splitext(eggFullName)[0]
        if os.path.exists(eggTempFolder):
            FolderDeleter.delete(eggTempFolder)
            print('Removed "%s" that was in my way.' % eggTempFolder)
        os.mkdir(eggTempFolder)
        # Create the "Products" sub-folder if we must wrap the package in this
        # namespace
        eggModulePath = j(j(eggTempFolder, self.moduleName.replace('.', '/')))
        # Copy the Python module into the egg.
        os.makedirs(eggModulePath)
        copyFolder(self.pythonModule, eggModulePath)
        # Create setup files in the root egg folder
        self.createSetupFile(eggTempFolder)
        self.createInitFile(eggTempFolder)
        self.zipResult(eggFullName, eggTempFolder)

    def checkArgs(self, options, args):
        # Check that we have the correct number of args.
        if len(args) != 1: raise EggifierError('Wrong number of arguments.')
        # Check that the arg corresponds to an existing Python module
        if not os.path.exists(args[0]):
            raise EggifierError('Path "%s" does not correspond to an ' \
                                'existing Python package.' % args[0])
        self.pythonModule = args[0]
        # At present I only manage Python modules, not 1-file Python packages.
        if not os.path.isdir(self.pythonModule):
            raise EggifierError('"%s" is not a folder. One-file Python ' \
                                'packages are not supported yet.' % args[0])
        self.eggFolder = options.result
        if not os.path.exists(self.eggFolder):
            raise EggifierError('"%s" does not exist. Please create this ' \
                                'folder first.' % self.eggFolder)
        self.includeAppy = options.appy
        self.inProducts = options.products
        self.version = options.version
        self.moduleName = os.path.basename(self.pythonModule)
        if self.inProducts:
            self.moduleName = 'Products.' + self.moduleName
        self.eggName = self.getEggName()

    def run(self):
        optParser = OptionParser(usage=EggifyScript.__doc__)
        optParser.add_option("-r", "--result", dest="result",
                             help="The folder where to create the egg",
                             default=os.getcwd(), metavar="RESULT",
                             type='string')
        optParser.add_option("-a", "--appy", action="store_true",
                             help="Includes the Appy module in the egg")
        optParser.add_option("-p", "--products", action="store_true",
                             help="Includes the module in the 'Products' " \
                                  "namespace")
        optParser.add_option("-v", "--version", dest="version",
                             help="The module version", default='1.0.0',
                             metavar="VERSION", type='string')
        options, args = optParser.parse_args()
        try:
            self.checkArgs(options, args)
            self.eggify()
        except EggifierError, ee:
            sys.stderr.write(str(ee) + '\nRun eggify.py -h for getting help.\n')
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    EggifyScript().run()
# ------------------------------------------------------------------------------
