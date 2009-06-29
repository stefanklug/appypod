# ------------------------------------------------------------------------------
import os, os.path, zipfile, sys
from appy.shared import appyPath
from appy.bin.clean import Cleaner

# ------------------------------------------------------------------------------
class Zipper:
    def __init__(self):
        self.zipFileName = '%s/Desktop/appy.zip' % os.environ['HOME']
    def createZipFile(self):
        print 'Creating %s...' % self.zipFileName
        zipFile = zipfile.ZipFile(self.zipFileName, 'w', zipfile.ZIP_DEFLATED)
        for dir, dirnames, filenames in os.walk(appyPath):
            for f in filenames:
                fileName = os.path.join(dir, f)
                arcName = fileName[fileName.find('appy/'):]
                print 'Adding %s' % fileName
                zipFile.write(fileName, arcName)
        zipFile.close()

    def run(self):
        # Where to put the zip file ?
        print "Where do you want to put appy.zip ? [Default is %s] " % \
            os.path.dirname(self.zipFileName),
        response = sys.stdin.readline().strip()
        if response:
            if os.path.exists(response) and os.path.isdir(response):
                self.zipFileName = '%s/appy.zip' % response
            else:
                print '%s is not a folder.' % response
                sys.exit(1)
        if os.path.exists(self.zipFileName):
            print 'Removing existing %s...' % self.zipFileName
            os.remove(self.zipFileName)
        Cleaner().run(verbose=False)
        self.createZipFile()

# Main program -----------------------------------------------------------------
if __name__ == '__main__':
    Zipper().run()
# ------------------------------------------------------------------------------
