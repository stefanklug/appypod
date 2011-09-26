# ------------------------------------------------------------------------------
import time

# ------------------------------------------------------------------------------
class Migrator:
    '''This class is responsible for performing migrations, when, on
       installation, we've detected a new Appy version.'''
    def __init__(self, installer):
        self.installer = installer

    def migrateTo_0_7_1(self):
        '''Appy 0.7.1 has its own management of Ref fields and does not use
           Archetypes references and the reference catalog anymore. So we must
           update data structures that store Ref info on instances.'''
        ins = self.installer
        ins.info('Migrating to Appy 0.7.1...')
        allClassNames = [ins.tool.__class__.__name__] + ins.config.allClassNames
        for className in allClassNames:
            i = -1
            updated = 0
            ins.info('Analysing class "%s"...' % className)
            refFields = None
            for obj in ins.tool.executeQuery(className,\
                                             noSecurity=True)['objects']:
                i += 1
                if i == 0:
                    # Get the Ref fields for objects of this class
                    refFields = [f for f in obj.getAllAppyTypes() \
                                 if (f.type == 'Ref') and not f.isBack]
                    if refFields:
                        refNames = ', '.join([rf.name for rf in refFields])
                        ins.info('  Ref fields found: %s' % refNames)
                    else:
                        ins.info('  No Ref field found.')
                        break
                isUpdated = False
                for field in refFields:
                    # Attr for storing UIDs of referred objects has moved
                    # from _appy_[fieldName] to [fieldName].
                    refs = getattr(obj, '_appy_%s' % field.name)
                    if refs:
                        isUpdated = True
                        setattr(obj, field.name, refs)
                        exec 'del obj._appy_%s' % field.name
                        # Set the back references
                        for refObject in field.getValue(obj):
                            refObject.link(field.back.name, obj, back=True)
                if isUpdated: updated += 1
            if updated:
                ins.info('  %d/%d object(s) updated.' % (updated, i+1))

    def run(self):
        i = self.installer
        installedVersion = i.appyTool.appyVersion
        startTime = time.time()
        migrationRequired = False
        if not installedVersion or (installedVersion <= '0.7.0'):
            migrationRequired = True
            self.migrateTo_0_7_1()
        stopTime = time.time()
        if migrationRequired:
            i.info('Migration done in %d minute(s).'% ((stopTime-startTime)/60))
# ------------------------------------------------------------------------------
