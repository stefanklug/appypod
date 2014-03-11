# ------------------------------------------------------------------------------
import sys, time, os, os.path, smtplib, socket, popen2, shutil
from optparse import OptionParser
import ZODB.FileStorage
import ZODB.serialize
from DateTime import DateTime
from StringIO import StringIO
folderName = os.path.dirname(__file__)

# ------------------------------------------------------------------------------
class BackupError(Exception): pass
ERROR_CODE = 1

# ------------------------------------------------------------------------------
class ZodbBackuper:
    '''This backuper will run every night (after 00.00). Every night excepted
       Sunday, it will perform an incremental backup. Every Sunday, the script
       will pack the ZODB, perform a full backup, and, if successful, remove all
       previous (full and incremental) backups.'''
    fullBackupExts = ('.fs', '.fsz')
    toRemoveExts = ('.doc', '.pdf', '.rtf', '.odt')
    def __init__(self, storageLocation, backupFolder, options):
        self.storageLocation = storageLocation
        self.backupFolder = backupFolder
        self.options = options
        # Unwrap some options directly on self.
        self.repozo = options.repozo or './repozo.py'
        self.zopectl = options.zopectl or './zopectl'
        self.logFile = file(options.logFile, 'a')
        self.logMem = StringIO() # We keep a log of the last script execution,
        # so we can send this info by email.
        self.emails = options.emails
        self.tempFolder = options.tempFolder
        self.logsBackupFolder = options.logsBackupFolder
        self.zopeUser = options.zopeUser
        self.keepSeconds = int(options.keepSeconds)

    def log(self, msg):
        for logPlace in (self.logFile, self.logMem):
            logPlace.write(msg)
            logPlace.write('\n')

    def executeCommand(self, cmd):
        '''Executes command p_cmd.'''
        w = self.log
        w('Executing "%s"...' % cmd)
        outstream, instream = popen2.popen4(cmd)
        outTxt = outstream.readlines()
        instream.close()
        outstream.close()
        for line in outTxt:
            w(line[:-1])
        w('Done.')

    def packZodb(self):
        '''Packs the ZODB and keeps one week history.'''
        storage = ZODB.FileStorage.FileStorage(self.storageLocation)
        #storage.pack(time.time()-(7*24*60*60), ZODB.serialize.referencesf)
        storage.pack(time.time()-self.keepSeconds, ZODB.serialize.referencesf)
        for fileSuffix in ('', '.index'):
            fileName = self.storageLocation + fileSuffix
            os.system('chown %s %s' % (self.zopeUser, fileName))

    def removeDataFsOld(self):
        '''Removes the file Data.fs.old if it exists.

           In the process of packing the ZODB, an additional file Data.fs.pack
           is created, and renamed to Data.fs once finished. It means that, when
           we pack the ZODB, 3 copies of the DB can be present at the same time:
           Data.fs, Data.fs.old and Data.fs.pack. We prefer to remove the
           Data.fs.old copy to avoid missing disk space if the DB is big.
        '''
        old = self.storageLocation + '.old'
        if os.path.exists(old):
            self.log('Removing %s...' % old)
            os.remove(old)
            self.log('Done.')

    folderCreateError = 'Could not create backup folder. Backup of log ' \
                        'files will not take place. %s'
    def backupLogs(self):
        w = self.log
        if not os.path.exists(self.logsBackupFolder):
            # Try to create the folder when to store backups of the log files
            try:
                w('Try to create backup folder for logs "%s"...' % \
                  self.logsBackupFolder)
                os.mkdir(self.logsBackupFolder)
            except IOError, ioe:
                w(folderCreateError % str(ioe))
            except OSError, oe:
                w(folderCreateError % str(oe))
        if os.path.exists(self.logsBackupFolder):
            # Ok, we can make the backup of the log files.
            # Get the folder where logs lie
            logsFolder = self.options.logsFolder
            d = os.path.dirname
            j = os.path.join
            if not logsFolder:
                logsFolder = j(d(d(self.storageLocation)), 'log')
            if not os.path.isdir(logsFolder):
                w('Cannot backup log files because folder "%s" does not ' \
                  'exist. Try using option "-g".' % logsFolder)
                return
            for logFileName in os.listdir(logsFolder):
                if logFileName.endswith('.log'):
                    backupTime = DateTime().strftime('%Y_%m_%d_%H_%M')
                    parts = os.path.splitext(logFileName)
                    copyFileName = '%s.%s%s' % (parts[0], backupTime, parts[1])
                    absCopyFileName = j(self.logsBackupFolder, copyFileName)
                    absLogFileName = j(logsFolder, logFileName)
                    w('Moving "%s" to "%s"...' % (absLogFileName,
                                                  absCopyFileName))
                    shutil.copyfile(absLogFileName, absCopyFileName)
                    os.remove(absLogFileName)
                    # I do a "copy" + a "remove" instead of a "rename" because
                    # a "rename" fails if the source and dest files are on
                    # different physical devices.

    def getDate(self, dateString):
        '''Returns a DateTime instance from p_dateString, which has the form
           YYYY-MM-DD-HH-MM-SS.'''
        return DateTime('%s/%s/%s %s:%s:%s' % tuple(dateString.split('-')))

    def removeOldBackups(self):
        '''This method removes all files (full & incremental backups) that are
           older than the last full backup.'''
        w = self.log
        # Determine date of the oldest full backup
        oldestFullBackupDate = eighties = DateTime('1980/01/01')
        for backupFile in os.listdir(self.backupFolder):
            fileDate, ext = os.path.splitext(backupFile)
            if ext in self.fullBackupExts:
                # I have found a full backup
                fileDate = self.getDate(fileDate)
                if fileDate > oldestFullBackupDate:
                    oldestFullBackupDate = fileDate
        # Remove all backup files older that oldestFullBackupDate
        if oldestFullBackupDate != eighties:
            w('Last full backup date: %s' % str(oldestFullBackupDate))
        for backupFile in os.listdir(self.backupFolder):
            fileDate, ext = os.path.splitext(backupFile)
            if self.getDate(fileDate) < oldestFullBackupDate:
                fullFileName = '%s/%s' % (self.backupFolder, backupFile)
                w('Removing old backup file %s...' % fullFileName)
                os.remove(fullFileName)

    def sendEmails(self):
        '''Send content of self.logMem to self.emails.'''
        w = self.log
        subject = 'Backup notification.'
        msg = 'From: %s\nTo: %s\nSubject: %s\n\n%s' % (self.options.fromAddress,
              self.emails, subject, self.logMem.getvalue())
        try:
            w('> Sending mail notifications to %s...' % self.emails)
            smtpInfo = self.options.smtpServer.split(':', 3)
            login = password = None
            if len(smtpInfo) == 2:
                # We simply have server and port
                server, port = smtpInfo
            else:
                # We also have login and password
                server, port, login, password = smtpInfo
            smtpServer = smtplib.SMTP(server, port=int(port))
            if login:
                smtpServer.login(login, password)
            res = smtpServer.sendmail(self.options.fromAddress,
                                      self.emails.split(','), msg)
            smtpServer.quit()
            if res:
                w('Could not send mail to some recipients. %s' % str(res))
            w('Done.')
        except socket.error, se:
            w('Could not connect to SMTP server %s (%s).' % \
              (self.options.smtpServer, str(se)))

    def removeTempFiles(self):
        '''For EGW, OO produces temp files that EGW tries do delete at the time
           they are produced. But in some cases EGW can't do it (ie Zope runs
           with a given user and OO runs with root and produces files that can't
           be deleted by the user running Zope). This is why in this script we
           remove the temp files that could not be removed by Zope.'''
        w = self.log
        w('Removing temp files in "%s"...' % self.tempFolder)
        pdfCount = docCount = rtfCount = odtCount = 0
        for fileName in os.listdir(self.tempFolder):
            ext = os.path.splitext(fileName)[1]
            if ext in self.toRemoveExts:
                exec '%sCount += 1' % ext[1:]
                fullFileName = os.path.join(self.tempFolder, fileName)
                #w('Removing "%s"...' % fullFileName)
                try:
                    os.remove(fullFileName)
                except OSError, oe:
                    w('Could not remove "%s" (%s).' % (fullFileName, str(oe)))
        w('%d .pdf, %d .doc, %d .rtf and %d .odt file(s) removed.' % \
          (pdfCount, docCount, rtfCount, odtCount))

    def run(self):
        w = self.log
        startTime = time.time()
        mode = self.options.mode
        w('\n****** Backup launched at %s (mode: %s) ******' % \
          (str(time.asctime()), mode))
        # Shutdown the Zope instance
        w('> Shutting down Zope instance...')
        self.executeCommand('%s stop' % self.zopectl)
        # Check if we are on the "full backup day"
        dayFull = self.options.dayFullBackup
        if time.asctime().startswith(dayFull):
            # If mode 'zodb', let's pack the ZODB first. Afterwards it will
            # trigger a full backup.
            if mode == 'zodb':
                # As a preamble to packing the ZODB, remove Data.fs.old if
                # present.
                self.removeDataFsOld()
                w('> Day is "%s", packing the ZODB...' % dayFull)
                self.packZodb()
                w('Pack done.')
            elif mode == 'copy':
                dest = os.path.join(self.backupFolder, 'Data.fs.new')
                w('> Day is "%s", copying %s to %s...' % \
                  (dayFull, self.storageLocation, dest))
                # Perform a copy of Data.fs to the backup folder.
                shutil.copyfile(self.storageLocation, dest)
                # The copy has succeeded. Remove the previous copy and rename
                # this one.
                oldDest = os.path.join(self.backupFolder, 'Data.fs')
                w('> Copy successful. Renaming %s to %s...' % (dest, oldDest))
                if os.path.exists(oldDest):
                    os.remove(oldDest)
                    w('> (Old existing backup %s was removed).' % oldDest)
                os.rename(dest, oldDest)
                w('Done.')
            # Make a backup of the log files...
            w('> Make a backup of log files...')
            self.backupLogs()
            w('Log files copied.')
        else:
            if mode == 'copy':
                w('Copy mode: nothing to copy: day is not %s.' % dayFull)
        # Do the backup with repozo
        if mode == 'zodb':
            w('> Performing backup...')
            self.executeCommand('%s %s -BvzQ -r %s -f %s' % \
                (self.options.python, self.repozo, self.backupFolder,
                 self.storageLocation))
            # Remove previous full backups.
            self.removeOldBackups()
        # If a command is specified, run Zope to execute this command
        if self.options.command:
            w('> Executing command "%s"...' % self.options.command)
            jobScript = '%s/job.py' % folderName
            cmd = '%s run %s %s' % (self.zopectl, jobScript,
                                    self.options.command)
            self.executeCommand(cmd)
        # Start the instance again, in normal mode.
        w('> Restarting Zope instance...')
        self.executeCommand('%s start' % self.zopectl)
        self.removeTempFiles()
        stopTime = time.time()
        w('Done in %d minute(s).' % ((stopTime-startTime)/60))
        if self.emails:
            self.sendEmails()
        self.logFile.close()
        print(self.logMem.getvalue())
        self.logMem.close()

# ------------------------------------------------------------------------------
class ZodbBackupScript:
    '''usage: python backup.py storageLocation backupFolder [options]
       storageLocation is the path to a ZODB database (file storage) (ie
                       /opt/ZopeInstance/var/Data.fs);
       backupFolder is a folder exclusively dedicated for storing backups
                      of the mentioned storage (ie /data/zodbbackups).'''

    weekDays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    def checkArgs(self, options, args):
        '''Check that the scripts arguments are correct.'''
        # Do I have the correct number of args?
        if len(args) != 2:
            raise BackupError('Wrong number of arguments.')
        # Check storageLocation
        if not os.path.exists(args[0]) or not os.path.isfile(args[0]):
            raise BackupError('"%s" does not exist or is not a file.' % args[0])
        # Check backupFolder
        if not os.path.isdir(args[1]):
            raise BackupError('"%s" does not exist or is not a folder.'%args[1])
        # Check logs folder
        if options.logsFolder and not os.path.isdir(options.logsFolder):
            raise BackupError('"%s" is not a folder.' % options.logsFolder)
        # Try to create a file in this folder to check if we have write
        # access in it.
        fileName = '%s/%s.tmp' % (args[1], str(time.time()))
        try:
            f = file(fileName, 'w')
            f.write('Hello.')
            f.close()
            os.remove(fileName)
        except OSError, oe:
            raise BackupError('I do not have the right to write in ' \
                              'folder "%s".' % args[1])
        # Check temp folder
        if not os.path.isdir(options.tempFolder):
            raise BackupError('Temp folder "%s" does not exist or is not ' \
                              'a folder.' % options.tempFolder)
        # Check day of week
        if options.dayFullBackup not in self.weekDays:
            raise BackupError(
                'Day of week must be one of %s' % str(self.weekDays))
        # Check command format
        if options.command:
            parts = options.command.split(':')
            if len(parts) not in (4,5):
                raise BackupError('Command format must be ' \
                    '<ZopeAdmin><PloneInstancePath>:<ApplicationName>:' \
                    '<ToolMethodName>[:<args>]')

    def run(self):
        optParser = OptionParser(usage=ZodbBackupScript.__doc__)
        optParser.add_option("-p", "--python", dest="python",
            help="The path to the Python interpreter running Zope",
            default='python2.4',metavar="PYTHON",type='string')
        optParser.add_option("-r", "--repozo", dest="repozo",
            help="The path to repozo.py", default='', metavar="REPOZO",
            type='string')
        optParser.add_option("-z", "--zopectl", dest="zopectl",
            help="The path to Zope instance's zopectl script", default='',
            metavar="ZOPECTL", type='string')
        optParser.add_option("-l", "--logfile", dest="logFile",
            help="Log file where this script will append output (defaults to " \
                 "./backup.log)", default='./backup.log', metavar="LOGFILE",
            type='string')
        optParser.add_option("-d", "--day-full-backup", dest="dayFullBackup",
            help="Day of the week where the full backup must be performed " \
                 "(defaults to 'Sun'). Must be one of %s" % str(self.weekDays),
            default='Sun', metavar="DAYFULLBACKUP", type='string')
        optParser.add_option("-e", "--emails", dest="emails",
            help="Comma-separated list of emails that will receive the log " \
                 "of this script.", default='', metavar="EMAILS", type='string')
        optParser.add_option("-f", "--from-address", dest="fromAddress",
            help="From address for the sent mails", default='',
            metavar="FROMADDRESS", type='string')
        optParser.add_option("-s", "--smtp-server", dest="smtpServer",
            help="SMTP server and port (ie: localhost:25) for sending mails. " \
                 "You can also embed username and password if the SMTP " \
                 "server requires authentication, ie localhost:25:myLogin:" \
                 "myPassword", default='localhost:25', metavar="SMTPSERVER",
            type='string')
        optParser.add_option("-t", "--tempFolder", dest="tempFolder",
            help="Folder used by LibreOffice for producing temp files. " \
                 "Defaults to /tmp.", default='/tmp', metavar="TEMP",
            type='string')
        optParser.add_option("-g", "--logsFolder",dest="logsFolder",
            help="Folder where Zope log files are (typically: event.log and " \
                 "Z2.log). If no folder is provided, we will consider to " \
                 "work on a standard Zope instance and decide that the log " \
                 "folder is, from 'storageLocation', located at ../log",
            metavar="LOGSFOLDER", type='string')
        optParser.add_option("-b", "--logsBackupFolder",dest="logsBackupFolder",
            help="Folder where backups of log files (event.log and Z2.log) " \
            "will be stored.", default='./logsbackup',
            metavar="LOGSBACKUPFOLDER", type='string')

        optParser.add_option("-u", "--user", dest="zopeUser",
            help="User and group that must own Data.fs. Defaults to " \
                 "zope:www-data. If this script is launched by root, for " \
                 "example, when packing the ZODB this script may produce a " \
                 "new Data.fs that the user running Zope may not be able to " \
                 "read anymore. After packing, this script makes a 'chmod' " \
                 "on Data.fs.", default='zope:www-data', metavar="USER",
            type='string')
        optParser.add_option("-k", "--keep-seconds", dest="keepSeconds",
            help="Number of seconds to leave in the ZODB history when the " \
                 "ZODB is packed.", default='86400', metavar="KEEPSECONDS",
            type='string')
        optParser.add_option("-m", "--mode", dest="mode", help="Default mode, "\
            "'zodb', uses repozo for performing backups. Mode 'copy' simply " \
            "performs a copy of the database to the specified backup folder.",
            default='zodb', metavar="MODE", type='string')
        optParser.add_option("-c", "--command", dest="command",
            help="Command to execute while Zope is running. It must have the " \
            "following format: <ZopeAdmin>:<PloneInstancePath>:" \
            "<ApplicationName>:<ToolMethodName>[:<args>]. <ZopeAdmin> is the " \
            "user name of the Zope administrator; <PloneInstancePath> is the " \
            "path, within Zope, to the Plone Site object (if not at the " \
            "root of the Zope hierarchy, use '/' as folder separator); " \
            "<ApplicationName> is the name of the Appy application; " \
            "<ToolMethodName> is the name of the method to call on the tool " \
            "in this Appy application; (optional) <args> are the arguments " \
            "to give to this method (only strings are supported). Several " \
            "arguments must be separated by '*'.",  default='',
            metavar="COMMAND", type='string')
        (options, args) = optParser.parse_args()
        try:
            self.checkArgs(options, args)
            backuper = ZodbBackuper(args[0], args[1], options)
            backuper.run()
        except BackupError, be:
            sys.stderr.write(str(be) + '\nRun the script without any ' \
                                       'argument for getting help.\n')
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    ZodbBackupScript().run()
# ------------------------------------------------------------------------------
