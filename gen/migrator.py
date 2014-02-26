# ------------------------------------------------------------------------------
import time

# ------------------------------------------------------------------------------
class Migrator:
    '''This class is responsible for performing migrations, when, on
       installation, we've detected a new Appy version.'''
    def __init__(self, installer):
        self.installer = installer
        self.logger = installer.logger
        self.app = installer.app
        self.tool = self.app.config.appy()

    def migrateTo_0_9_0(self):
        '''Migrates this DB to Appy 0.9.x.'''
        pass

    def run(self):
        appyVersion = self.tool.appyVersion
        if not appyVersion or (appyVersion < '0.9.0'):
            # Migration is required.
            startTime = time.time()
            self.migrateTo_0_9_0()
            stopTime = time.time()
            elapsed = (stopTime-startTime) / 60.0
            self.logger.info('Migration done in %d minute(s).' % elapsed)
# ------------------------------------------------------------------------------
