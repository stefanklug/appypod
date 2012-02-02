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

    bypassRoles = ('Authenticated', 'Member')
    bypassGroups = ('Administrators', 'Reviewers')
    def migrateUsers(self, ploneSite):
        '''Migrate users from Plone's acl_users to Zope acl_users with
           corresponding Appy objects.'''
        # First of all, remove the Plone-patched root acl_users by a standard
        # (hum, Appy-patched) Zope UserFolder.
        tool = self.app.config.appy()
        from AccessControl.User import manage_addUserFolder
        self.app.manage_delObjects(ids=['acl_users'])
        manage_addUserFolder(self.app)
        # Put an admin user into it
        newUsersDb = self.app.acl_users
        newUsersDb._doAddUser('admin', 'admin', ['Manager'], ())
        # Copy users from Plone acl_users to Zope acl_users
        for user in ploneSite.acl_users.getUsers():
            id = user.getId()
            userRoles = user.getRoles()
            for br in self.bypassRoles:
                if br in userRoles: userRoles.remove(br)
            userInfo = ploneSite.portal_membership.getMemberById(id)
            userName = userInfo.getProperty('fullname') or id
            userEmail = userInfo.getProperty('email') or ''
            appyUser = tool.create('users', login=id,
                password1='fake', password2='fake', roles=userRoles,
                name=userName, firstName=' ', email=userEmail)
            appyUser.title = appyUser.title.strip()
            # Set the correct password
            password = ploneSite.acl_users.source_users._user_passwords[id]
            newUsersDb.data[id].__ = password
            # Manage groups. Exclude not-used default Plone groups.
            for groupId in user.getGroups():
                if groupId in self.bypassGroups: continue
                if tool.count('Group', login=groupId):
                    # The Appy group already exists, get it
                    appyGroup = tool.search('Group', login=groupId)[0]
                else:
                    # Create the group. Todo: get Plone group roles and title
                    appyGroup = tool.create('groups', login=groupId,
                                            title=groupId)
                appyGroup.addUser(appyUser)

    def reindexObject(self, obj):
        obj.reindex()
        i = 1
        for subObj in obj.objectValues():
            i += self.reindexObject(subObj)
        return i # The number of reindexed (sub-)object(s)

    def migrateTo_0_8_0(self):
        '''Migrates a Plone-based (<= 0.7.1) Appy app to a Ploneless (0.8.0)
           Appy app.'''
        self.logger.info('Migrating to Appy 0.8.0...')
        # Find the Plone site. It must be at the root of the Zope tree.
        ploneSite = None
        for obj in self.app.objectValues():
            if obj.__class__.__name__ == 'PloneSite':
                ploneSite = obj
                break
        # As a preamble: delete translation objects from self.app.config: they
        # will be copied from the old tool.
        self.app.config.manage_delObjects(ids=self.app.config.objectIds())
        # Migrate data objects:
        # - from oldDataFolder to self.app.data
        # - from oldTool       to self.app.config (excepted translation
        #                         objects that were re-created from i18n files).
        appName = self.app.config.getAppName()
        for oldFolderName in (appName, 'portal_%s' % appName.lower()):
            oldFolder = getattr(ploneSite, oldFolderName)
            objectIds = [id for id in oldFolder.objectIds()]
            cutted = oldFolder.manage_cutObjects(ids=objectIds)
            if oldFolderName == appName:
                destFolder = self.app.data
            else:
                destFolder = self.app.config
            destFolder.manage_pasteObjects(cutted)
            i = 0
            for obj in destFolder.objectValues():
                i += self.reindexObject(obj)
            self.logger.info('%d objects imported into %s.' % \
                             (i, destFolder.getId()))
            if oldFolderName != appName:
                # Re-link objects copied into the self.app.config with the Tool
                # through Ref fields.
                tool = self.app.config.appy()
                pList = tool.o.getProductConfig().PersistentList
                for field in tool.fields:
                    if field.type != 'Ref': continue
                    n = field.name
                    if n in ('users', 'groups'): continue
                    uids = getattr(oldFolder, n)
                    if uids:
                        # Update the forward reference
                        setattr(tool.o, n, pList(uids))
                        # Update the back reference
                        for obj in getattr(tool, n):
                            backList = getattr(obj.o, field.back.name)
                            backList.remove(oldFolder._at_uid)
                            backList.append(tool.uid)
                        self.logger.info('config.%s: linked %d object(s)' % \
                                         (n, len(uids)))
                    else:
                        self.logger.info('config.%s: no object to link.' % n)
        self.migrateUsers(ploneSite)
        self.logger.info('Migration done.')

    def run(self):
        if self.app.acl_users.__class__.__name__ == 'UserFolder':
            return # Already Ploneless
        tool = self.app.config.appy()
        appyVersion = tool.appyVersion
        if not appyVersion or (appyVersion < '0.8.0'):
            # Migration is required.
            startTime = time.time()
            self.migrateTo_0_8_0()
            stopTime = time.time()
            elapsed = (stopTime-startTime) / 60.0
            self.logger.info('Migration done in %d minute(s).' % elapsed)
# ------------------------------------------------------------------------------
