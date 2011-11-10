'''This package contains stuff used at run-time for installing a generated
   Plone product.'''

# ------------------------------------------------------------------------------
import os, os.path, time
from StringIO import StringIO
from sets import Set
import appy
import appy.version
from appy.gen import Type, Ref, String
from appy.gen.po import PoParser
from appy.gen.utils import produceNiceMessage, updateRolesForPermission
from appy.shared.data import languages
from migrator import Migrator

# ------------------------------------------------------------------------------
class ZCTextIndexInfo:
    '''Silly class used for storing information about a ZCTextIndex.'''
    lexicon_id = "plone_lexicon"
    index_type = 'Okapi BM25 Rank'

class PloneInstaller:
    '''This Plone installer runs every time the generated Plone product is
       installed or uninstalled (in the Plone configuration interface).'''
    def __init__(self, reinstall, ploneSite, config):
        # p_cfg is the configuration module of the Plone product.
        self.reinstall = reinstall # Is it a fresh install or a re-install?
        self.ploneSite = ploneSite
        self.config = cfg = config
        # Unwrap some useful variables from config
        self.productName = cfg.PROJECTNAME
        self.appClasses = cfg.appClasses
        self.appClassNames = cfg.appClassNames
        self.allClassNames = cfg.allClassNames
        self.applicationRoles = cfg.applicationRoles # Roles defined in the app
        self.defaultAddRoles = cfg.defaultAddRoles
        self.appFrontPage = cfg.appFrontPage
        self.languages = cfg.languages
        self.languageSelector = cfg.languageSelector
        self.attributes = cfg.attributes
        # A buffer for logging purposes
        self.toLog = StringIO()
        self.typeAliases = {'sharing': '', 'gethtml': '',
            '(Default)': 'skynView', 'edit': 'skyn/edit',
            'index.html': '', 'properties': '', 'view': ''}
        self.tool = None # The Plone version of the application tool
        self.appyTool = None # The Appy version of the application tool
        self.toolName = '%sTool' % self.productName
        self.toolInstanceName = 'portal_%s' % self.productName.lower()

    @staticmethod
    def updateIndexes(ploneSite, indexInfo, logger):
        '''This method creates or updates, in a p_ploneSite, definitions of
           indexes in its portal_catalog, based on index-related information
           given in p_indexInfo. p_indexInfo is a dictionary of the form
           {s_indexName:s_indexType}. Here are some examples of index types:
           "FieldIndex", "ZCTextIndex", "DateIndex".'''
        catalog = ploneSite.portal_catalog
        zopeCatalog = catalog._catalog
        for indexName, indexType in indexInfo.iteritems():
            # If this index already exists but with a different type, remove it.
            if (indexName in zopeCatalog.indexes):
                oldType = zopeCatalog.indexes[indexName].__class__.__name__
                if oldType != indexType:
                    catalog.delIndex(indexName)
                    logger.info('Existing index "%s" of type "%s" was removed:'\
                                ' we need to recreate it with type "%s".' % \
                                (indexName, oldType, indexType))
            if indexName not in zopeCatalog.indexes:
                # We need to create this index
                if indexType != 'ZCTextIndex':
                    catalog.addIndex(indexName, indexType)
                else:
                    catalog.addIndex(indexName,indexType,extra=ZCTextIndexInfo)
                # Indexing database content based on this index.
                catalog.reindexIndex(indexName, ploneSite.REQUEST)
                logger.info('Created index "%s" of type "%s"...' % \
                            (indexName, indexType))

    appyFolderType = 'AppyFolder'
    def registerAppyFolderType(self):
        '''We need a specific content type for the folder that will hold all
           objects created from this application, in order to remove it from
           Plone navigation settings. We will create a new content type based
           on Large Plone Folder.'''
        if not hasattr(self.ploneSite.portal_types, self.appyFolderType):
            portal_types = self.ploneSite.portal_types
            lpf = 'Large Plone Folder'
            largePloneFolder = getattr(portal_types, lpf)
            typeInfoName = 'ATContentTypes: ATBTreeFolder (ATBTreeFolder)'
            portal_types.manage_addTypeInformation(
                largePloneFolder.meta_type, id=self.appyFolderType,
                typeinfo_name=typeInfoName)
            appyFolder = getattr(portal_types, self.appyFolderType)
            appyFolder.title = 'Appy folder'
            #appyFolder.factory = largePloneFolder.factory
            #appyFolder.product = largePloneFolder.product
            # Copy actions and aliases
            appyFolder._actions = tuple(largePloneFolder._cloneActions())
            # Copy aliases from the base portal type
            appyFolder.setMethodAliases(largePloneFolder.getMethodAliases())
            # Prevent Appy folders to be visible in standard Plone navigation
            nv = self.ploneSite.portal_properties.navtree_properties
            metaTypesNotToList = list(nv.getProperty('metaTypesNotToList'))
            if self.appyFolderType not in metaTypesNotToList:
                metaTypesNotToList.append(self.appyFolderType)
            nv.manage_changeProperties(
                metaTypesNotToList=tuple(metaTypesNotToList))

    def getAddPermission(self, className):
        '''What is the name of the permission allowing to create instances of
           class whose name is p_className?'''
        return self.productName + ': Add ' + className

    def installRootFolder(self):
        '''Creates and/or configures, at the root of the Plone site and if
           needed, the folder where the application will store instances of
           root classes. Creates also the 'appy' folder (more precisely,
           a Filesystem Directory View) at the root of the site, for storing
           appy-wide ZPTs an images.'''
        # Register first our own Appy folder type if needed.
        site = self.ploneSite
        if not hasattr(site.portal_types, self.appyFolderType):
            self.registerAppyFolderType()
        # Create the folder
        if not hasattr(site.aq_base, self.productName):
            # Temporarily allow me to create Appy large plone folders
            getattr(site.portal_types, self.appyFolderType).global_allow = 1
            # Allow to create Appy large folders in the plone site
            getattr(site.portal_types,
                'Plone Site').allowed_content_types += (self.appyFolderType,)
            site.invokeFactory(self.appyFolderType, self.productName,
                               title=self.productName)
            getattr(site.portal_types, self.appyFolderType).global_allow = 0
            # Manager has been granted Add permissions for all root classes.
            # This may not be desired, so remove this.
            appFolder = getattr(site, self.productName)
            for className in self.config.rootClasses:
                permission = self.getAddPermission(className)
                appFolder.manage_permission(permission, (), acquire=0)
        else:
            appFolder = getattr(site, self.productName)
        # All roles defined as creators should be able to create the
        # corresponding root content types in this folder.
        i = -1
        allCreators = set()
        for klass in self.appClasses:
            i += 1
            if not klass.__dict__.has_key('root') or not klass.__dict__['root']:
                continue # It is not a root class
            creators = getattr(klass, 'creators', None)
            if not creators: creators = self.defaultAddRoles
            allCreators = allCreators.union(creators)
            className = self.appClassNames[i]
            permission = self.getAddPermission(className)
            updateRolesForPermission(permission, tuple(creators), appFolder)
        # Beyond content-type-specific "add" permissions, creators must also
        # have the main permission "Add portal content".
        permission = 'Add portal content'
        updateRolesForPermission(permission, tuple(allCreators), appFolder)
        # Creates the "appy" Directory view
        if hasattr(site.aq_base, 'skyn'):
            site.manage_delObjects(['skyn'])
        # This way, if Appy has moved from one place to the other, the
        # directory view will always refer to the correct place.
        addDirView = self.config.manage_addDirectoryView
        addDirView(site, appy.getPath() + '/gen/plone25/skin', id='skyn')

    def installTypes(self):
        '''Registers and configures the Plone content types that correspond to
           gen-classes.'''
        site = self.ploneSite
        # Do Plone-based type registration
        classes = self.config.listTypes(self.productName)
        self.config.installTypes(site, self.toLog, classes, self.productName)
        self.config.install_subskin(site, self.toLog, self.config.__dict__)
        # Set appy view/edit pages for every created type
        for className in self.allClassNames + ['%sTool' % self.productName]:
            # I did not put the app tool in self.allClassNames because it
            # must not be registered in portal_factory
            if hasattr(site.portal_types, className):
                # className may correspond to an abstract class that has no
                # corresponding Plone content type
                typeInfo = getattr(site.portal_types, className)
                typeInfo.setMethodAliases(self.typeAliases)
                # Update edit and view actions
                typeActions = typeInfo.listActions()
                for action in typeActions:
                    if action.id == 'view':
                        page = 'skynView'
                        action.edit(action='string:${object_url}/%s' % page)
                    elif action.id == 'edit':
                        page = 'skyn/edit'
                        action.edit(action='string:${object_url}/%s' % page)

        # Configure types for instance creation through portal_factory
        factoryTool = site.portal_factory
        factoryTypes = self.allClassNames + factoryTool.getFactoryTypes().keys()
        factoryTool.manage_setPortalFactoryTypes(listOfTypeIds=factoryTypes)

        # Whitelist tool in Archetypes, because now UID is in portal_catalog
        atTool = getattr(site, self.config.ARCHETYPETOOLNAME)
        atTool.setCatalogsByType(self.toolName, ['portal_catalog'])

    def updatePodTemplates(self):
        '''Creates or updates the POD templates in the tool according to pod
           declarations in the application classes.'''
        # Creates the templates for Pod fields if they do not exist.
        for contentType in self.attributes.iterkeys():
            appyClass = self.tool.getAppyClass(contentType)
            if not appyClass: continue # May be an abstract class
            wrapperClass = self.tool.getAppyClass(contentType, wrapper=True)
            for appyType in wrapperClass.__fields__:
                if appyType.type != 'Pod': continue
                # Find the attribute that stores the template, and store on
                # it the default one specified in the appyType if no
                # template is stored yet.
                attrName = self.appyTool.getAttributeName(
                                        'podTemplate', appyClass, appyType.name)
                fileObject = getattr(self.appyTool, attrName)
                if not fileObject or (fileObject.size == 0):
                    # There is no file. Put the one specified in the appyType.
                    fileName = os.path.join(self.appyTool.getDiskFolder(),
                                            appyType.template)
                    if os.path.exists(fileName):
                        setattr(self.appyTool, attrName, fileName)
                        self.appyTool.log('Imported "%s" in the tool in ' \
                                          'attribute "%s"'% (fileName,attrName))
                    else:
                        self.appyTool.log('Template "%s" was not found!' % \
                                          fileName, type='error')

    def installTool(self):
        '''Configures the application tool.'''
        # Register the tool in Plone
        try:
            self.ploneSite.manage_addProduct[
                self.productName].manage_addTool(self.toolName)
        except self.config.BadRequest:
            # If an instance with the same name already exists, this error will
            # be unelegantly raised by Zope.
            pass

        self.tool = getattr(self.ploneSite, self.toolInstanceName)
        self.tool.refreshSecurity()
        self.appyTool = self.tool.appy()
        if self.reinstall:
            self.tool.createOrUpdate(False, None)
        else:
            self.tool.createOrUpdate(True, None)

    def installTranslations(self):
        '''Creates or updates the translation objects within the tool.'''
        translations = [t.o.id for t in self.appyTool.translations]
        # We browse the languages supported by this application and check
        # whether we need to create the corresponding Translation objects.
        for language in self.languages:
            if language in translations: continue
            # We will create, in the tool, the translation object for this
            # language. Determine first its title.
            langId, langEn, langNat = languages.get(language)
            if langEn != langNat:
                title = '%s (%s)' % (langEn, langNat)
            else:
                title = langEn
            self.appyTool.create('translations', id=language, title=title)
            self.appyTool.log('Translation object created for "%s".' % language)
        # Now, we synchronise every Translation object with the corresponding
        # "po" file on disk.
        appFolder = self.config.diskFolder
        appName = self.config.PROJECTNAME
        dn = os.path.dirname
        jn = os.path.join
        i18nFolder = jn(jn(jn(dn(dn(dn(appFolder))),'Products'),appName),'i18n')
        for translation in self.appyTool.translations:
            # Get the "po" file
            poName = '%s-%s.po' % (appName, translation.id)
            poFile = PoParser(jn(i18nFolder, poName)).parse()
            for message in poFile.messages:
                setattr(translation, message.id, message.getMessage())
            self.appyTool.log('Translation "%s" updated from "%s".' % \
                              (translation.id, poName))

    def installRolesAndGroups(self):
        '''Registers roles used by workflows and classes defined in this
           application if they are not registered yet. Creates the corresponding
           groups if needed.'''
        site = self.ploneSite
        data = list(site.__ac_roles__)
        for role in self.config.applicationRoles:
            if not role in data:
                data.append(role)
                # Add to portal_role_manager
                prm = site.acl_users.portal_role_manager
                try:
                    prm.addRole(role, role, 'Added by "%s"' % self.productName)
                except KeyError: # Role already exists
                    pass
            # If it is a global role, create a specific group and grant him
            # this role
            if role not in self.config.applicationGlobalRoles: continue
            group = '%s_group' % role
            if site.portal_groups.getGroupById(group): continue # Already there
            site.portal_groups.addGroup(group, title=group)
            site.portal_groups.setRolesForGroup(group, [role])
        site.__ac_roles__ = tuple(data)

    def manageIndexes(self):
        '''For every indexed field, this method installs and updates the
           corresponding index if it does not exist yet.'''
        # Create a special index for object state, that does not correspond to
        # a field.
        indexInfo = {'getState': 'FieldIndex', 'UID': 'FieldIndex'}
        for className in self.attributes.iterkeys():
            wrapperClass = self.tool.getAppyClass(className, wrapper=True)
            for appyType in wrapperClass.__fields__:
                if not appyType.indexed or (appyType.name == 'title'): continue
                n = appyType.name
                indexName = 'get%s%s' % (n[0].upper(), n[1:])
                indexInfo[indexName] = appyType.getIndexType()
        if indexInfo:
            PloneInstaller.updateIndexes(self.ploneSite, indexInfo, self)

    def manageLanguages(self):
        '''Manages the languages supported by the application.'''
        languageTool = self.ploneSite.portal_languages
        defLanguage = self.languages[0]
        languageTool.manage_setLanguageSettings(defaultLanguage=defLanguage,
            supportedLanguages=self.languages, setContentN=None,
            setCookieN=True, setRequestN=True, setPathN=True,
            setForcelanguageUrls=True, setAllowContentLanguageFallback=None,
            setUseCombinedLanguageCodes=None, displayFlags=False,
            startNeutral=False)

    def finalizeInstallation(self):
        '''Performs some final installation steps.'''
        site = self.ploneSite
        # Do not allow an anonymous user to register himself as new user
        site.manage_permission('Add portal member', ('Manager',), acquire=0)
        # Replace Plone front-page with an application-specific page if needed
        if self.appFrontPage:
            frontPageName = self.productName + 'FrontPage'
            site.manage_changeProperties(default_page=frontPageName)
        # Store the used Appy version (used for detecting new versions)
        self.appyTool.appyVersion = appy.version.short
        self.info('Appy version is %s.' % self.appyTool.appyVersion)
        # Call custom installer if any
        if hasattr(self.appyTool, 'install'):
            self.tool.executeAppyAction('install', reindex=False)

    def info(self, msg): return self.appyTool.log(msg)

    def install(self):
        # Begin with a migration if required.
        self.installTool()
        if self.reinstall: Migrator(self).run()
        self.installRootFolder()
        self.installTypes()
        self.manageLanguages()
        self.manageIndexes()
        self.updatePodTemplates()
        self.installTranslations()
        self.installRolesAndGroups()
        self.finalizeInstallation()
        self.appyTool.log("Installation done.")

    def uninstall(self): return 'Done.'

# Stuff for tracking user activity ---------------------------------------------
loggedUsers = {}
originalTraverse = None
doNotTrack = ('.jpg','.gif','.png','.js','.class','.css')

def traverseWrapper(self, path, response=None, validated_hook=None):
    '''This function is called every time a users gets a URL, this is used for
       tracking user activity. self is a BaseRequest'''
    res = originalTraverse(self, path, response, validated_hook)
    t = time.time()
    if os.path.splitext(path)[-1].lower() not in doNotTrack:
        # Do nothing when the user gets non-pages
        userId = self['AUTHENTICATED_USER'].getId()
        if userId:
            loggedUsers[userId] = t
            # "Touch" the SESSION object. Else, expiration won't occur.
            session = self.SESSION
    return res

def onDelSession(sessionObject, container):
    '''This function is called when a session expires.'''
    rq = container.REQUEST
    if rq.cookies.has_key('__ac') and rq.cookies.has_key('_ZopeId') and \
       (rq['_ZopeId'] == sessionObject.token):
        # The request comes from a guy whose session has expired.
        resp = rq.RESPONSE
        resp.expireCookie('__ac', path='/')
        resp.write('<center>For security reasons, your session has ' \
                   'expired.</center>')

# ------------------------------------------------------------------------------
class ZopeInstaller:
    '''This Zope installer runs every time Zope starts and encounters this
       generated Zope product.'''
    def __init__(self, zopeContext, toolClass, config, classes):
        self.zopeContext = zopeContext
        self.toolClass = toolClass
        self.config = cfg = config
        self.classes = classes
        # Unwrap some useful config variables
        self.productName = cfg.PROJECTNAME
        self.logger = cfg.logger
        self.defaultAddContentPermission = cfg.DEFAULT_ADD_CONTENT_PERMISSION
        self.addContentPermissions = cfg.ADD_CONTENT_PERMISSIONS

    def completeAppyTypes(self):
        '''We complete here the initialisation process of every Appy type of
           every gen-class of the application.'''
        appName = self.productName
        for klass in self.classes:
            # Store on wrapper class the ordered list of Appy types
            wrapperClass = klass.wrapperClass
            if not hasattr(wrapperClass, 'title'):
                # Special field "type" is mandatory for every class.
                title = String(multiplicity=(1,1), show='edit', indexed=True)
                title.init('title', None, 'appy')
                setattr(wrapperClass, 'title', title)
            names = self.config.attributes[wrapperClass.__name__[:-8]]
            wrapperClass.__fields__ = [getattr(wrapperClass, n) for n in names]
            # Post-initialise every Appy type
            for baseClass in klass.wrapperClass.__bases__:
                if baseClass.__name__ == 'AbstractWrapper': continue
                for name, appyType in baseClass.__dict__.iteritems():
                    if not isinstance(appyType, Type) or \
                           (isinstance(appyType, Ref) and appyType.isBack):
                        continue # Back refs are initialised within fw refs
                    appyType.init(name, baseClass, appName)

    def installApplication(self):
        '''Performs some application-wide installation steps.'''
        register = self.config.DirectoryView.registerDirectory
        register('skins', self.config.__dict__)
        # Register the appy skin folder among DirectoryView'able folders
        register('skin', appy.getPath() + '/gen/plone25')

    def installTool(self):
        '''Installs the tool.'''
        self.config.ToolInit(self.productName + ' Tools',
            tools = [self.toolClass], icon='tool.gif').initialize(
                self.zopeContext)

    def installTypes(self):
        '''Installs and configures the types defined in the application.'''
        self.config.listTypes(self.productName)
        contentTypes, constructors, ftis = self.config.process_types(
            self.config.listTypes(self.productName), self.productName)
        self.config.cmfutils.ContentInit(self.productName + ' Content',
            content_types = contentTypes,
            permission = self.defaultAddContentPermission,
            extra_constructors = constructors, fti = ftis).initialize(
                self.zopeContext)
        # Define content-specific "add" permissions
        for i in range(0, len(contentTypes)):
            className = contentTypes[i].__name__
            if not className in self.addContentPermissions: continue
            self.zopeContext.registerClass(meta_type = ftis[i]['meta_type'],
                constructors = (constructors[i],),
                permission = self.addContentPermissions[className])
        # Create workflow prototypical instances in __instance__ attributes
        for contentType in contentTypes:
            wf = getattr(contentType.wrapperClass, 'workflow', None)
            if wf and not hasattr(wf, '__instance__'):
                wf.__instance__ = wf()

    def enableUserTracking(self):
        '''Enables the machinery allowing to know who is currently logged in.
           Information about logged users will be stored in RAM, in the variable
           named loggedUsers defined above.'''
        global originalTraverse
        if not originalTraverse:
            # User tracking is not enabled yet. Do it now.
            BaseRequest = self.config.BaseRequest
            originalTraverse = BaseRequest.traverse
            BaseRequest.traverse = traverseWrapper

    def finalizeInstallation(self):
        '''Performs some final installation steps.'''
        cfg = self.config
        # Apply customization policy if any
        cp = cfg.CustomizationPolicy
        if cp and hasattr(cp, 'register'): cp.register(context)
        # Install the default profile
        cfg.profile_registry.registerProfile(self.productName, self.productName,
            'Installation of %s' % self.productName, 'profiles/default',
            self.productName, cfg.EXTENSION, for_=cfg.IPloneSiteRoot)
        # Register a function warning us when a session object is deleted.
        app = self.zopeContext._ProductContext__app
        if hasattr(app, 'temp_folder'): # This is not the case in test mode
            app.temp_folder.session_data.setDelNotificationTarget(onDelSession)

    def install(self):
        self.logger.info('is being installed...')
        self.completeAppyTypes()
        self.installApplication()
        self.installTool()
        self.installTypes()
        self.enableUserTracking()
        self.finalizeInstallation()
# ------------------------------------------------------------------------------
