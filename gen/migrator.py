# ------------------------------------------------------------------------------
import time
from appy.fields.file import FileInfo

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
    def migrateFileFields(obj):
        '''Ensures all file fields on p_obj are FileInfo instances.'''
        migrated = 0 # Count the number of migrated fields
        for field in obj.fields:
            if field.type != 'File': continue
            oldValue = getattr(obj, field.name)
            if oldValue and not isinstance(oldValue, FileInfo):
                # A legacy File object. Convert it to a FileInfo instance and
                # extract the binary to the filesystem.
                setattr(obj, field.name, oldValue)
                migrated += 1
        return migrated

    def migrateTo_0_9_0(self):
        '''Migrates this DB to Appy 0.9.x.'''
        # Put all binaries to the filesystem
        tool = self.tool
        tool.log('Migrating file fields...')
        context = {'migrate': self.migrateFileFields, 'nb': 0}
        for className in tool.o.getAllClassNames():
            tool.compute(className, context=context, noSecurity=True,
                         expression="ctx['nb'] += ctx['migrate'](obj)")
        tool.log('Migrated %d File field(s).' % context['nb'])

    def run(self, force=False):
        '''Executes a migration when relevant, or do it for sure if p_force is
           True.'''
        appyVersion = self.tool.appyVersion
        if force or not appyVersion or (appyVersion < '0.9.0'):
            # Migration is required.
            self.logger.info('Appy version (DB) is %s' % appyVersion)
            startTime = time.time()
            self.migrateTo_0_9_0()
            stopTime = time.time()
            elapsed = (stopTime-startTime) / 60.0
            self.logger.info('Migration done in %d minute(s).' % elapsed)
# ------------------------------------------------------------------------------
