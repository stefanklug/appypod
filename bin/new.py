'''This script allows to create a brand new ready-to-use Plone/Zone instance.
   As prerequisite, you must have installed Plone through the Unifier installer
   available at http://plone.org.'''

# ------------------------------------------------------------------------------
import os, os.path, sys, shutil, re
from optparse import OptionParser
from appy.shared.utils import cleanFolder, copyFolder

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

zopeCtl = '''#!/bin/sh
PYTHON="%s"
INSTANCE_HOME="%s"
CONFIG_FILE="$INSTANCE_HOME/etc/zope.conf"
PYTHONPATH="$INSTANCE_HOME/lib/python"
ZDCTL="%s/Zope2/Startup/zopectl.py"
export INSTANCE_HOME
export PYTHON
export PYTHONPATH
exec "$PYTHON" "$ZDCTL" -C "$CONFIG_FILE" "$@"
'''
runZope = '''#! /bin/sh
PYTHON="%s"
INSTANCE_HOME="%s"
CONFIG_FILE="$INSTANCE_HOME/etc/zope.conf"
PYTHONPATH="$INSTANCE_HOME/lib/python"
ZOPE_RUN="%s/Zope2/Startup/run.py"
export INSTANCE_HOME
export PYTHON
export PYTHONPATH
exec "$PYTHON" "$ZOPE_RUN" -C "$CONFIG_FILE" "$@"
'''
# ------------------------------------------------------------------------------
class NewScript:
    '''usage: %prog ploneVersion plonePath instancePath

       "ploneVersion"  can be plone25, plone30, plone3x or plone4
                       (plone3x represents Plone 3.2.x, Plone 3.3.5...)
       
       "plonePath"     is the (absolute) path to you plone installation.
                       Plone 2.5 and 3.0 are typically installed in
                       /opt/Plone-x.x.x, while Plone 3 > 3.0 is typically
                       installed in in /usr/local/Plone.
       "instancePath"  is the (absolute) path where you want to create your
                       instance (should not already exist).'''
    ploneVersions = ('plone25', 'plone30', 'plone3x', 'plone4')

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
                        copyFolder(folderName, destFolder)

    filesToPatch = ('meta.zcml', 'configure.zcml', 'overrides.zcml')
    patchRex = re.compile('<includePlugins.*?/>', re.S)
    def patchPlone3x(self):
        '''Auto-proclaimed ugly code in z3c forces us to patch some files
           in Products.CMFPlone because these guys make the assumption that
           "plone.xxx" packages are within eggs when they've implemented their
           ZCML directives "includePlugins" and "includePluginsOverrides".
           So in this method, I remove every call to those directives in
           CMFPlone files. It does not seem to affect Plone behaviour. Indeed,
           these directives seem to be useful only when adding sad (ie, non
           Appy) Plone plug-ins.'''
        j = os.path.join
        ploneFolder = os.path.join(self.productsFolder, 'CMFPlone')
        # Patch files
        for fileName in self.filesToPatch:
            filePath = os.path.join(ploneFolder, fileName)
            f = file(filePath)
            fileContent = f.read()
            f.close()
            f = file(filePath, 'w')
            f.write(self.patchRex.sub('<!--Del. includePlugins-->',fileContent))
            f.close()

    filesToPatch2 = ('profiles/default/skins.xml')
    def patchPlone4(self):
        '''Patches Plone 4 that can't live without buildout as-is.'''
        self.patchPlone3x() # We still need this for Plone 4 as well.
        # bin/zopectl
        content = zopeCtl % (self.pythonPath, self.instancePath, self.zopePath)
        f = file('%s/bin/zopectl' % self.instancePath, 'w')
        f.write(content)
        f.close()
        # bin/runzope
        content = runZope % (self.pythonPath, self.instancePath, self.zopePath)
        f = file('%s/bin/runzope' % self.instancePath, 'w')
        f.write(content)
        f.close()
        j = os.path.join
        themeFolder = '%s/plonetheme' % self.libFolder
        for theme in os.listdir(themeFolder):
            # Create a simlink to every theme in self.productsFolder
            tFolder = j(themeFolder, theme)
            if not os.path.isdir(tFolder): continue
            os.system('ln -s %s %s/%s' % (tFolder, self.productsFolder, theme))
            # Patch skins.xml
            fileName = '%s/profiles/default/skins.xml' % tFolder
            f = file(fileName)
            content = f.read()
            f.close()
            f = file(fileName, 'w')
            f.write(content.replace('plonetheme.%s:' % theme, '%s/' % theme))
            f.close()
        # As eggs have been deleted, Plone can't tell which version of Zope and
        # Plone are there. So we patch the code that tries to get Plone and Zope
        # versions.
        codeFile = "%s/pkg_resources.py" % self.libFolder
        f = file(codeFile)
        content = f.read()
        f.close()
        content = content.replace("raise DistributionNotFound(req)",
            "dist = Distribution(project_name=req.project_name, " \
            "version='1.1.1', platform='linux2', location='%s')" % \
            self.instancePath)
        f = file(codeFile, 'w')
        f.write(content)
        f.close()

    def copyEggs(self):
        '''Copy content of eggs into the Zope instance.'''
        j = os.path.join
        eggsFolder = j(self.plonePath, 'buildout-cache/eggs')
        self.ploneThemes = []
        for name in os.listdir(eggsFolder):
            if name == 'EGG-INFO': continue
            absName = j(eggsFolder, name)
            # Copy every file or sub-folder into self.libFolder or
            # self.productsFolder.
            for fileName in os.listdir(absName):
                absFileName = j(absName, fileName)
                if fileName == 'Products' and not name.startswith('Zope2-'):
                    # Copy every sub-folder into self.productsFolder
                    for folderName in os.listdir(absFileName):
                        absFolder = j(absFileName, folderName)
                        if not os.path.isdir(absFolder): continue
                        copyFolder(absFolder, j(self.productsFolder,folderName))
                elif os.path.isdir(absFileName):
                    copyFolder(absFileName, j(self.libFolder, fileName))
                else:
                    shutil.copy(absFileName, self.libFolder)

    def createInstance(self, linksForProducts):
        '''Calls the Zope script that allows to create a Zope instance and copy
           into it all the Plone packages and products.'''
        j = os.path.join
        # Find the Python interpreter running Zope
        for elem in os.listdir(self.plonePath):
            pythonPath = None
            elemPath = j(self.plonePath, elem)
            if elem.startswith('Python-') and os.path.isdir(elemPath):
                pythonPath = elemPath + '/bin/python'
                if not os.path.exists(pythonPath):
                    raise NewError(PYTHON_EXE_NOT_FOUND % pythonPath)
                break
        if not pythonPath:
            raise NewError(PYTHON_NOT_FOUND % self.plonePath)
        self.pythonPath = pythonPath
        # Find the Zope script mkzopeinstance.py and Zope itself
        makeInstancePath = None
        self.zopePath = None
        for dirname, dirs, files in os.walk(self.plonePath):
            # Find Zope
            for folderName in dirs:
                if folderName.startswith('Zope2-'):
                    self.zopePath = j(dirname, folderName)
            # Find mkzopeinstance
            for fileName in files:
                if fileName == 'mkzopeinstance.py':
                    if self.ploneVersion == 'plone4':
                        makeInstancePath = j(dirname, fileName)
                    else:
                        if ('/buildout-cache/' not in dirname):
                            makeInstancePath = j(dirname, fileName)
        if not makeInstancePath:
            raise NewError(MKZOPE_NOT_FOUND % self.plonePath)
        # Execute mkzopeinstance.py with the right Python interpreter.
        # For Plone4, we will call it later.
        cmd = '%s %s -d %s' % (pythonPath, makeInstancePath, self.instancePath)
        if self.ploneVersion != 'plone4':
            print cmd
            os.system(cmd)
        # Now, make the instance Plone-ready
        action = 'Copying'
        if linksForProducts:
            action = 'Symlinking'
        print '%s Plone stuff in the Zope instance...' % action
        if self.ploneVersion in ('plone25', 'plone30'):
            self.installPlone25or30Stuff(linksForProducts)
        elif self.ploneVersion in ('plone3x', 'plone4'):
            self.copyEggs()
            if self.ploneVersion == 'plone3x':
                self.patchPlone3x()
            elif self.ploneVersion == 'plone4':
                # Create the Zope instance
                os.environ['PYTHONPATH'] = '%s:%s' % \
                    (j(self.instancePath,'Products'),
                     j(self.instancePath, 'lib/python'))
                print cmd
                os.system(cmd)
                self.patchPlone4()
        # Remove .bat files under Linux
        if os.name == 'posix':
            cleanFolder(j(self.instancePath, 'bin'), exts=('.bat',))

    def manageArgs(self, args):
        '''Ensures that the script was called with the right parameters.'''
        if len(args) != 3: raise NewError(WRONG_NB_OF_ARGS)
        self.ploneVersion, self.plonePath, self.instancePath = args
        # Add some more folder definitions
        j = os.path.join
        self.productsFolder = j(self.instancePath, 'Products')
        self.libFolder = j(self.instancePath, 'lib/python')
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
