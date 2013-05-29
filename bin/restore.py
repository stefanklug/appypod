# ------------------------------------------------------------------------------
import sys, time, os, os.path
from optparse import OptionParser

# ------------------------------------------------------------------------------
class RestoreError(Exception): pass
ERROR_CODE = 1

# ------------------------------------------------------------------------------
class ZodbRestorer:
    def __init__(self, storageLocation, backupFolder, options):
        self.storageLocation = storageLocation
        self.backupFolder = backupFolder
        self.repozo = options.repozo or 'repozo.py'
        self.restoreDate = options.date
        self.python = options.python
    def run(self):
        startTime = time.time()
        datePart = ''
        if self.restoreDate:
            datePart = '-D %s' % self.restoreDate
        repozoCmd = '%s %s -Rv -r %s %s -o %s' % (self.python,
            self.repozo, self.backupFolder, datePart, self.storageLocation)
        print('Executing %s...' % repozoCmd)
        os.system(repozoCmd)
        stopTime = time.time()
        print('Done in %d minute(s).' % ((stopTime-startTime)/60))

# ------------------------------------------------------------------------------
class ZodbRestoreScript:
    '''usage: python restore.py storageLocation backupFolder [options]
       storageLocation is the storage that will be created at the end of the
                       restore process (ie /tmp/Data.hurrah.fs);
       backupFolder is the folder used for storing storage backups
                       (ie /data/zodbbackups).'''

    def checkArgs(self, options, args):
        '''Check that the scripts arguments are correct.'''
        # Do I have the correct number of args?
        if len(args) != 2:
            raise RestoreError('Wrong number of arguments.')
        # Check that storageLocation does not exist.
        if os.path.exists(args[0]):
            raise RestoreError('"%s" exists. Please specify the name of a ' \
                               'new file (in a temp folder for example); you ' \
                               'will move this at the right place in a second '\
                               'step.' % args[0])
        # Check backupFolder
        if not os.path.isdir(args[1]):
            raise RestoreError('"%s" does not exist or is not a folder.' % \
                  args[1])
        # Try to create storageLocation to check if we have write
        # access in it.
        try:
            f = file(args[0], 'w')
            f.write('Hello.')
            f.close()
            os.remove(args[0])
        except OSError, oe:
            raise RestoreError('I do not have the right to write file ' \
                               '"%s".' % args[0])

    def run(self):
        optParser = OptionParser(usage=ZodbRestoreScript.__doc__)
        optParser.add_option("-p", "--python", dest="python",
                             help="The path to the Python interpreter running "\
                                  "Zope",
                             default='python2.4',metavar="REPOZO",type='string')
        optParser.add_option("-r", "--repozo", dest="repozo",
                             help="The path to repozo.py",
                             default='', metavar="REPOZO", type='string')
        optParser.add_option("-d", "--date", dest="date",
                             help="Date of the image to restore (format=" \
                                  "YYYY-MM-DD-HH-MM-SS). It is UTC time, " \
                                  "not local time. If you don't specify this " \
                                  "option, it defaults to now. If specified, " \
                                  "hour, minute, and second parts are optional",
                             default='', metavar="DATE", type='string')
        (options, args) = optParser.parse_args()
        try:
            self.checkArgs(options, args)
            backuper = ZodbRestorer(args[0], args[1], options)
            backuper.run()
        except RestoreError, be:
            sys.stderr.write(str(be))
            sys.stderr.write('\n')
            optParser.print_help()
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    ZodbRestoreScript().run()
# ------------------------------------------------------------------------------
