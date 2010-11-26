# Imports ----------------------------------------------------------------------
import os, os.path
from appy.shared import appyPath
from appy.shared.utils import FolderDeleter, cleanFolder

# ------------------------------------------------------------------------------
class Cleaner:
    def run(self, verbose=True):
        cleanFolder(appyPath, verbose=verbose)
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
