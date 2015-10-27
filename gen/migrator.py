# ------------------------------------------------------------------------------
import os.path, time
from appy.fields.file import FileInfo
from appy.shared import utils as sutils

# ------------------------------------------------------------------------------
class Migrator:
    '''This class is responsible for performing migrations, when, on
       installation, we've detected a new Appy version.'''
    def __init__(self, installer):
        self.installer = installer
        self.logger = installer.logger
        self.app = installer.app
        self.tool = self.app.config.appy()

    @staticmethod
    def migrateBinaryFields(obj):
        '''Ensures all file and frozen pod fields on p_obj are FileInfo
           instances.'''
        migrated = 0 # Count the number of migrated fields
        for field in obj.fields:
            if field.type == 'File':
                oldValue = getattr(obj, field.name)
                if oldValue and not isinstance(oldValue, FileInfo):
                    # A legacy File object. Convert it to a FileInfo instance
                    # and extract the binary to the filesystem.
                    setattr(obj, field.name, oldValue)
                    migrated += 1
            elif field.type == 'Pod':
                frozen = getattr(obj.o, field.name, None)
                if frozen:
                    # Dump this file on disk.
                    tempFolder = sutils.getOsTempFolder()
                    fmt = os.path.splitext(frozen.filename)[1][1:]
                    fileName = os.path.join(tempFolder,
                                            '%f.%s' % (time.time(), fmt))
                    f = file(fileName, 'wb')
                    if frozen.data.__class__.__name__ == 'Pdata':
                        # The file content is splitted in several chunks.
                        f.write(frozen.data.data)
                        nextPart = frozen.data.__next__
                        while nextPart:
                            f.write(nextPart.data)
                            nextPart = nextPart.__next__
                    else:
                        # Only one chunk
                        f.write(frozen.data)
                    f.close()
                    f = file(fileName)
                    field.freeze(obj, template=field.template[0], format=fmt,
                                 noSecurity=True, upload=f,
                                 freezeOdtOnError=False)
                    f.close()
                    # Remove the legacy in-zodb file object
                    setattr(obj.o, field.name, None)
                    migrated += 1
        return migrated

    def migrateTo_0_9_0(self):
        '''Migrates this DB to Appy 0.9.x.'''
        # Put all binaries to the filesystem
        tool = self.tool
        tool.log('Migrating binary fields...')
        context = {'migrate': self.migrateBinaryFields, 'nb': 0}
        for className in tool.o.getAllClassNames():
            tool.compute(className, context=context, noSecurity=True,
                         expression="ctx['nb'] += ctx['migrate'](obj)")
        tool.log('Migrated %d binary field(s).' % context['nb'])

    def run(self, force=False):
        '''Executes a migration when relevant, or do it for sure if p_force is
           True.'''
        appyVersion = self.tool.appyVersion
        # appyVersion being None simply means that we are creating a new DB.
        if force or (appyVersion and (appyVersion < '0.9.0')):
            # Migration is required.
            self.logger.info('Appy version (DB) is %s' % appyVersion)
            startTime = time.time()
            self.migrateTo_0_9_0()
            stopTime = time.time()
            elapsed = (stopTime-startTime) / 60.0
            self.logger.info('Migration done in %d minute(s).' % elapsed)
# ------------------------------------------------------------------------------
