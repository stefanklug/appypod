#!/usr/bin/python2.4.4
'''This script allows to create a brand new read-to-use Plone/Zone instance.
   As prerequisite, you must have installed Plone through the Unifier installer
   available at http://plone.org.'''

# ------------------------------------------------------------------------------
import os, os.path, sys, shutil
from optparse import OptionParser
from appy.shared.utils import cleanFolder

# ------------------------------------------------------------------------------
class NewError(Exception): pass
ERROR_CODE = 1
WRONG_NB_OF_ARGS = 'Wrong number of args.'
WRONG_PLONE_VERSION = 'Plone version must be among %s.'
WRONG_PLONE_PATH = 'Path "%s" is not an existing folder.'
PYTHON_NOT_FOUND = 'Python interpreter was not found in "%s". Are you sure ' \
    'we are in the folder hierarchy created by the Plone installer?'
PYTHON_EXE_NOT_FOUND = '"%s" does not exist.'
MKZOPE_NOT_FOUND = 'Script mkzopeinstance.py not found in "%s and ' \
    'subfolders. Are you sure we are in the folder hierarchy created by ' \
    'the Plone installer?'
WRONG_INSTANCE_PATH = '"%s" must be an existing folder for creating the ' \
    'instance in it.'

# ------------------------------------------------------------------------------
class NewScript:
    '''usage: %prog ploneVersion plonePath instancePath

       "ploneVersion"  can be plone25 or plone3
       
       "plonePath"     is the (absolute) path to you plone installation.
                       Plone 2.5 is typically installed in /opt/Plone-2.5.5,
                       while Plone 3 is typically installed in /usr/local/Plone.
       "instancePath"  is the (absolute) path where you want to create your
                       instance (should not already exist).'''
    ploneVersions = ('plone25', 'plone3')

    def createInstance(self):
        '''Calls the Zope script that allows to create a Zope instance and copy
           into it all the Plone packages and products.'''
        # Find the Python interpreter running Zope
        for elem in os.listdir(self.plonePath):
            pythonPath = None
            elemPath = os.path.join(self.plonePath, elem)
            if elem.startswith('Python-') and os.path.isdir(elemPath):
                pythonPath = elemPath + '/bin/python'
                if not os.path.exists(pythonPath):
                    raise NewError(PYTHON_EXE_NOT_FOUND % pythonPath)
                break
        if not pythonPath:
            raise NewError(PYTHON_NOT_FOUND % self.plonePath)
        # Find the Zope script mkzopeinstance.py
        makeInstancePath = None
        for dirname, dirs, files in os.walk(self.plonePath):
            # Do not browse the buildout-cache
            for fileName in files:
                if (fileName == 'mkzopeinstance.py') and \
                   ('/buildout-cache/' not in dirname):
                    makeInstancePath = os.path.join(dirname, fileName)
        if not makeInstancePath:
            raise NewError(MKZOPE_NOT_FOUND % self.plonePath)
        # Execute mkzopeinstance.py with the right Python interpreter
        cmd = '%s %s -d %s' % (pythonPath, makeInstancePath, self.instancePath)
        print cmd
        os.system(cmd)
        # Now, make the instance Plone-ready
        productsFolder = os.path.join(self.instancePath, 'Products')
        libFolder = os.path.join(self.instancePath, 'lib/python')
        print 'Copying Plone stuff in the Zope instance...'
        if self.ploneVersion == 'plone25':
            self.installPlone25Stuff(productsFolder, libFolder)
        elif self.ploneVersion == 'plone3':
            self.installPlone3Stuff(productsFolder, libFolder)
        # Clean the copied folders
        cleanFolder(productsFolder)
        cleanFolder(libFolder)

    def installPlone25Stuff(self, productsFolder, libFolder):
        '''Here, we will copy all Plone3-related stuff in the Zope instance
           we've created, to get a full Plone-ready Zope instance.'''
        pass

    uglyChunks = ('pkg_resources', '.declare_namespace(')
    wrongPackages = [os.sep.join(['plone', 'app', 'content']),
                     os.sep.join(['.egg', 'wicked'])
                    ]
    def findPythonPackageInEgg(self, currentFolder):
        '''Finds the Python package that is deeply hidden into the egg.'''
        # Find the file __init__.py
        isFinalPackage = False
        for elem in os.listdir(currentFolder):
            elemPath = os.path.join(currentFolder, elem)
            if elem == '__init__.py':
                f = file(elemPath)
                content = f.read()
                f.close()
                # Is it a awful egg init ?
                for chunk in self.uglyChunks:
                    if content.find(chunk) == -1:
                        isFinalPackage = True
                        break
                # Goddamned, there are exceptions.
                for wrongPackage in self.wrongPackages:
                    if currentFolder.endswith(wrongPackage) and \
                        not isFinalPackage:
                        isFinalPackage = True
                break
        if not isFinalPackage:
            # Find the subfolder and find the Python package into it.
            for elem in os.listdir(currentFolder):
                elemPath = os.path.join(currentFolder, elem)
                if os.path.isdir(elemPath):
                    return self.findPythonPackageInEgg(elemPath)
        else:
            return currentFolder

    def getSubFolder(self, folder):
        '''In p_folder, we now that there is only one subfolder. This method
           returns the subfolder's absolute path.'''
        for elem in os.listdir(folder):
            elemPath = os.path.join(folder, elem)
            if (elem != 'EGG-INFO') and os.path.isdir(elemPath):
                return elemPath
        return None

    def installPlone3Stuff(self, productsFolder, libFolder):
        '''Here, we will copy all Plone3-related stuff in the Zope instance
           we've created, to get a full Plone-ready Zope instance.'''
        # All Plone 3 eggs are in buildout-cache/eggs. We will extract from
        # those silly overstructured folder hierarchies the standard Python
        # packages that lie in it, and copy them in the instance. Within these
        # eggs, we need to distinguish:
        # - standard Python packages that will be copied in
        #   <zopeInstance>/lib/python (ie, like Appy applications)
        # - Zope products that will be copied in
        #   <zopeInstance>/Products (ie, like Appy generated Zope products)
        eggsFolder = os.path.join(self.plonePath, 'buildout-cache/eggs')
        for name in os.listdir(eggsFolder):
            eggMainFolder = os.path.join(eggsFolder, name)
            if name.startswith('Products.'):
                # A Zope product. Copy its content in Products.
                innerFolder= self.getSubFolder(self.getSubFolder(eggMainFolder))
                destFolder = os.path.join(productsFolder,
                                          os.path.basename(innerFolder))
                shutil.copytree(innerFolder, destFolder)
            else:
                # A standard Python package. Copy its content in lib/python.
                # Go into the subFolder that is not EGG-INFO.
                eggFolder = self.getSubFolder(eggMainFolder)
                if not eggFolder:
                    # This egg is malformed and contains basic Python files.
                    # Copy those files directly in libFolder.
                    for fileName in os.listdir(eggMainFolder):
                        if fileName.endswith('.py'):
                            fullFileName= os.path.join(eggMainFolder, fileName)
                            shutil.copy(fullFileName, libFolder)
                    continue
                eggFolderName = os.path.basename(eggFolder)
                if eggFolderName == 'Products':
                    # Goddamned. This should go in productsFolder and not in
                    # libFolder.
                    innerFolder = self.getSubFolder(eggFolder)
                    destFolder = os.path.join(productsFolder,
                                              os.path.basename(innerFolder))
                    shutil.copytree(innerFolder, destFolder)
                else:
                    packageFolder = self.findPythonPackageInEgg(eggFolder)
                    # Create the destination folder(s) in the instance,
                    # within libFolder
                    destFolders = []
                    if packageFolder != eggFolder:
                        destFolders = [eggFolderName]
                        remFolders = packageFolder[len(eggFolder):]
                        remFolders = remFolders.strip(os.sep)
                        if remFolders.find(os.sep) != -1:
                            # There are more subfolders
                            destFolders += remFolders.split(os.sep)[:-1]
                    if destFolders:
                        # We must create the subfolders (if not yet created)
                        # before copying the Python package.
                        baseFolder = libFolder
                        for subFolder in destFolders:
                            subFolderPath=os.path.join(baseFolder,subFolder)
                            if not os.path.exists(subFolderPath):
                                os.mkdir(subFolderPath)
                                # Create an empty __init__.py in it.
                                init = os.path.join(subFolderPath,
                                                    '__init__.py')
                                f = file(init, 'w')
                                f.write('#Makes me a Python package.')
                                f.close()
                            baseFolder = subFolderPath
                        destFolder = os.sep.join(destFolders)
                        destFolder = os.path.join(libFolder, destFolder)
                        if not os.path.exists(destFolder):
                            os.makedirs(destFolder)
                    else:
                        destFolder = libFolder
                    destFolder = os.path.join(
                        destFolder, os.path.basename(packageFolder))
                    shutil.copytree(packageFolder, destFolder)

    def manageArgs(self, args):
        '''Ensures that the script was call with the right parameters.'''
        if len(args) != 3: raise NewError(WRONG_NB_OF_ARGS)
        self.ploneVersion, self.plonePath, self.instancePath = args
        # Check Plone version
        if self.ploneVersion not in self.ploneVersions:
            raise NewError(WRONG_PLONE_VERSION % str(self.ploneVersions))
        # Check Plone path
        if not os.path.exists(self.plonePath) \
           or not os.path.isdir(self.plonePath):
            raise NewError(WRONG_PLONE_PATH % self.plonePath)
        # Check instance path
        parentFolder = os.path.dirname(self.instancePath)
        if not os.path.exists(parentFolder) or not os.path.isdir(parentFolder):
            raise NewError(WRONG_INSTANCE_PATH % parentFolder)

    def run(self):
        optParser = OptionParser(usage=NewScript.__doc__)
        (options, args) = optParser.parse_args()
        try:
            self.manageArgs(args)
            print 'Creating new %s instance...' % self.ploneVersion
            self.createInstance()
        except NewError, ne:
            optParser.print_help()
            print
            sys.stderr.write(str(ne))
            sys.stderr.write('\n')
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    NewScript().run()
# ------------------------------------------------------------------------------
