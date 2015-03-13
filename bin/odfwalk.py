'''This script allows to walk (and potentially patch) files (content.xml,
   styles.xml...) contained within a given ODF file or within all ODF files
   found in some folder.'''

# ------------------------------------------------------------------------------
import sys, os.path, time
from appy.shared.zip import unzip, zip
from appy.shared.utils import getOsTempFolder, FolderDeleter, executeCommand

# ------------------------------------------------------------------------------
usage = '''Usage: python odfWalk.py [file|folder] yourScript.

 If *file* is given, it is the path to an ODF file (odt or ods). This single
 file will be walked.
 If *folder* is given, we will walk all ODF files found in this folder and
 sub-folders.

 *yourScript* is the path to a Python script that will be run on every walked
 file. It will be called with a single arg containing the absolute path to the
 folder containing the unzipped file content (content.xml, styles.xml...).'''

# ------------------------------------------------------------------------------
class OdfWalk:
    toUnzip = ('.ods', '.odt')
    def __init__(self, fileOrFolder, script):
        self.fileOrFolder = fileOrFolder
        self.script = script
        self.tempFolder = getOsTempFolder()

    def walkFile(self, fileName):
        '''Unzip p_fileName in a temp folder, call self.script, and then re-zip
           the result.'''
        print 'Walking %s...' % fileName
        # Create a temp folder
        name = 'f%f' % time.time()
        tempFolder = os.path.join(self.tempFolder, name)
        os.mkdir(tempFolder)
        # Unzip the file in it
        unzip(fileName, tempFolder)
        # Call self.script
        py = sys.executable or 'python'
        cmd = '%s %s %s' % (py, self.script, tempFolder)
        print '  Running %s...' % cmd,
        os.system(cmd)
        # Re-zip the result
        zip(fileName, tempFolder, odf=True)
        FolderDeleter.delete(tempFolder)
        print 'done.'

    def run(self):
        if os.path.isfile(self.fileOrFolder):
            self.walkFile(self.fileOrFolder)
        elif os.path.isdir(self.fileOrFolder):
            # Walk all files found in this folder
            for dir, dirnames, filenames in os.walk(self.fileOrFolder):
                for name in filenames:
                    if os.path.splitext(name)[1] in self.toUnzip:
                        self.walkFile(os.path.join(dir, name))
        else:
            print('%s does not exist.' % self.fileOrFolder)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(usage)
        sys.exit()
    # Warn the user.
    print 'All the files in %s will be modified. ' \
          'Are you sure? [y/N] ' % sys.argv[1],
    response = sys.stdin.readline().strip().lower()
    if response == 'y':
        OdfWalk(sys.argv[1], sys.argv[2]).run()
    else:
        print 'Canceled.'
# ------------------------------------------------------------------------------
