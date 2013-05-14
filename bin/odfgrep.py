'''This script allows to perform a "grep" command that will be applied on files
   content.xml and styles.xml within all ODF files (odt and ods) found within a
   given folder.'''

# ------------------------------------------------------------------------------
import sys, os.path, zipfile, time, subprocess
from appy.shared.utils import getOsTempFolder, FolderDeleter

# ------------------------------------------------------------------------------
usage = '''Usage: python odfGrep.py [file|folder] [keyword].

 If *file* is given, it is the path to an ODF file (odt or ods). grep will be
 run on this file only.
 If *folder* is given, the grep will be run on all ODF files found in this
 folder and sub-folders.

 *keyword* is the string to search within the file(s).
'''

# ------------------------------------------------------------------------------
class OdfGrep:
    toGrep = ('content.xml', 'styles.xml')
    toUnzip = ('.ods', '.odt')
    def __init__(self, fileOrFolder, keyword):
        self.fileOrFolder = fileOrFolder
        self.keyword = keyword
        self.tempFolder = getOsTempFolder()

    def callGrep(self, folder):
        '''Performs a "grep" with self.keyword in p_folder.'''
        cmd = 'grep -irn "%s" %s' % (self.keyword, folder)
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        return bool(out)

    def grepFile(self, fileName):
        '''Unzips the .xml files from file named p_fileName and performs a
           grep on it.'''
        # Unzip the file in the temp folder
        name = 'f%f' % time.time()
        tempFolder = os.path.join(self.tempFolder, name)
        os.mkdir(tempFolder)
        zip = zipfile.ZipFile(fileName)
        for zippedFile in zip.namelist():
            if zippedFile not in self.toGrep: continue
            destFile = os.path.join(tempFolder, zippedFile)
            f = open(destFile, 'wb')
            fileContent = zip.read(zippedFile)
            f.write(fileContent)
            f.close()
        # Run "grep" in this folder
        match = self.callGrep(tempFolder)
        if match:
            print 'Found in', fileName
        FolderDeleter.delete(tempFolder)

    def run(self):
        if os.path.isfile(self.fileOrFolder):
            self.grepFile(self.fileOrFolder)
        elif os.path.isdir(self.fileOrFolder):
            # Grep on all files found in this folder.
            for dir, dirnames, filenames in os.walk(self.fileOrFolder):
                for name in filenames:
                    if os.path.splitext(name)[1] in self.toUnzip:
                        self.grepFile(os.path.join(dir, name))
        else:
            print '%s does not exist.' % self.fileOrFolder

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print usage
        sys.exit()
    OdfGrep(sys.argv[1], sys.argv[2]).run()
# ------------------------------------------------------------------------------
