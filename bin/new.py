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

       "ploneVersion"  can be plone25, plone30, or plone3x
                       (plone3x can be Plone 3.2.x, Plone 3.3.5...)
       
       "plonePath"     is the (absolute) path to you plone installation.
                       Plone 2.5 and 3.0 are typically installed in
                       /opt/Plone-x.x.x, while Plone 3 > 3.0 is typically
                       installed in in /usr/local/Plone.
       "instancePath"  is the (absolute) path where you want to create your
                       instance (should not already exist).'''
    ploneVersions = ('plone25', 'plone30', 'plone3x')

    def createInstance(self, linksForProducts):
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
        action = 'Copying'
        if linksForProducts:
            action = 'Symlinking'
        print '%s Plone stuff in the Zope instance...' % action
        if self.ploneVersion in ('plone25', 'plone30'):
            self.installPlone25or30Stuff(linksForProducts)
        elif self.ploneVersion == 'plone3x':
            self.installPlone3Stuff()
        # Clean the copied folders
        cleanFolder(os.path.join(self.instancePath, 'Products'))
        cleanFolder(os.path.join(self.instancePath, 'lib/python'))

    def installPlone25or30Stuff(self, linksForProducts):
        '''Here, we will copy all Plone2-related stuff in the Zope instance
           we've created, to get a full Plone-ready Zope instance. If
           p_linksForProducts is True, we do not perform a real copy: we will
           create symlinks to products lying within Plone installer files.'''
        j = os.path.join
        if self.ploneVersion == 'plone25':
            sourceFolders = ('zeocluster/Products',)
        else:
            sourceFolders = ('zinstance/Products', 'zinstance/lib/python')
        for sourceFolder in sourceFolders:
            sourceBase = j(self.plonePath, sourceFolder)
            destBase = j(self.instancePath,
                         sourceFolder[sourceFolder.find('/')+1:])
            for name in os.listdir(sourceBase):
                folderName = j(sourceBase, name)
                if os.path.isdir(folderName):
                    destFolder = j(destBase, name)
                    # This is a Plone product. Copy it to the instance.
                    if linksForProducts:
                        # Create a symlink to this product in the instance
                        cmd = 'ln -s %s %s' % (folderName, destFolder)
                        os.system(cmd)
                    else:
                        # Copy thre product into the instance
                        shutil.copytree(folderName, destFolder)

    uglyChunks = ('pkg_resources', '.declare_namespace(')
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
                        isFinalPackage = True # It is not an ugly egg init.
                        break
        if not isFinalPackage:
            # Maybe we are wrong: our way to identify egg-viciated __init__
            # files is approximative. If we believe it is not the final package,
            # but we find other Python files in the folder, we must admit that
            # we've nevertheless found the final Python package.
            otherPythonFiles = False
            for elem in os.listdir(currentFolder):
                if elem.endswith('.py') and (elem != '__init__.py'):
                    otherPythonFiles = True
                    break
            if otherPythonFiles:
                # Ok, this is the final Python package
                return currentFolder
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

    viciatedFiles = {'meta.zcml':      'includePlugins',
                     'configure.zcml': 'includePlugins',
                     'overrides.zcml': 'includePluginsOverrides'}
    def patchPlone(self, productsFolder, libFolder):
        '''Auto-proclaimed ugly code in z3c forces us to patch some files
           in Products.CMFPlone because these guys make the assumption that
           "plone.xxx" packages are within eggs when they've implemented their
           ZCML directives "includePlugins" and "includePluginsOverrides".
           So in this method, I remove every call to those directives in
           CMFPlone files. It does not seem to affect Plone behaviour. Indeed,
           these directives seem to be useful only when adding sad (ie, non
           Appy) Plone plug-ins.'''
        ploneFolder = os.path.join(productsFolder, 'CMFPlone')
        # Patch viciated files
        for fileName, uglyDirective in self.viciatedFiles.iteritems():
            filePath = os.path.join(ploneFolder, fileName)
            f = file(filePath)
            fileContent = f.read()
            f.close()
            if fileContent.find(uglyDirective) != -1:
                toReplace = '<%s package="plone" file="%s" />' % \
                            (uglyDirective, fileName)
                fileContent = fileContent.replace(toReplace, '')
                f = file(filePath, 'w')
                f.write(fileContent)
                f.close()

    def installPlone3Stuff(self):
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
        j = os.path.join
        eggsFolder = j(self.plonePath, 'buildout-cache/eggs')
        productsFolder = j(self.instancePath, 'Products')
        libFolder = j(self.instancePath, 'lib/python')
        for name in os.listdir(eggsFolder):
            eggMainFolder = j(eggsFolder, name)
            if name.startswith('Products.'):
                # A Zope product. Copy its content in Products.
                innerFolder= self.getSubFolder(self.getSubFolder(eggMainFolder))
                destFolder = j(productsFolder, os.path.basename(innerFolder))
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
                            fullFileName= j(eggMainFolder, fileName)
                            shutil.copy(fullFileName, libFolder)
                    continue
                eggFolderName = os.path.basename(eggFolder)
                if eggFolderName == 'Products':
                    # Goddamned. This should go in productsFolder and not in
                    # libFolder.
                    innerFolder = self.getSubFolder(eggFolder)
                    destFolder = j(productsFolder,os.path.basename(innerFolder))
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
                            subFolderPath = j(baseFolder,subFolder)
                            if not os.path.exists(subFolderPath):
                                os.mkdir(subFolderPath)
                                # Create an empty __init__.py in it.
                                init = j(subFolderPath,'__init__.py')
                                f = file(init, 'w')
                                f.write('# Makes me a Python package.')
                                f.close()
                            baseFolder = subFolderPath
                        destFolder = os.sep.join(destFolders)
                        destFolder = j(libFolder, destFolder)
                        if not os.path.exists(destFolder):
                            os.makedirs(destFolder)
                    else:
                        destFolder = libFolder
                    destFolder = j(destFolder, os.path.basename(packageFolder))
                    shutil.copytree(packageFolder, destFolder)
        self.patchPlone(productsFolder, libFolder)

    def manageArgs(self, args):
        '''Ensures that the script was called with the right parameters.'''
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
        optParser.add_option("-l", "--links", action="store_true",
            help="[Linux, plone25 or plone30 only] Within the created " \
                 "instance, symlinks to Products lying within the Plone " \
                 "installer files are created instead of copying them into " \
                 "the instance. This avoids duplicating the Products source " \
                 "code and is interesting if you create a lot of Zope " \
                 "instances.")
        (options, args) = optParser.parse_args()
        linksForProducts = options.links
        try:
            self.manageArgs(args)
            print 'Creating new %s instance...' % self.ploneVersion
            self.createInstance(linksForProducts)
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
