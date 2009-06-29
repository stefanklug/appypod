# Imports ----------------------------------------------------------------------
import os, os.path
from appy.shared import appyPath
from appy.shared.utils import FolderDeleter

# ------------------------------------------------------------------------------
class Cleaner:
    exts = ('.pyc', '.class')
    def run(self, verbose=True):
        print 'Cleaning folder', appyPath, '...'
        # Remove files with an extension listed in self.exts
        for root, dirs, files in os.walk(appyPath):
            for fileName in files:
                ext = os.path.splitext(fileName)[1]
                if (ext in Cleaner.exts) or ext.endswith('~'):
                    fileToRemove = os.path.join(root, fileName)
                    if verbose:
                        print 'Removing %s...' % fileToRemove
                    os.remove(fileToRemove)
        # Remove all files in temp folders
        for tempFolder in ('%s/temp' % appyPath,
                           '%s/pod/test/temp' % appyPath):
            if os.path.exists(tempFolder):
                FolderDeleter.delete(tempFolder)
        # Remove test reports if any
        for testReport in ('%s/pod/test/Tester.report.txt' % appyPath,):
            if os.path.exists(testReport):
                os.remove(testReport)

# Main program -----------------------------------------------------------------
if __name__ == '__main__':
    Cleaner().run()
# ------------------------------------------------------------------------------
