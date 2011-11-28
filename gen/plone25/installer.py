'''This package contains stuff used at run-time for installing a generated
   Plone product.'''

# ------------------------------------------------------------------------------
import os, os.path, time
from StringIO import StringIO
from sets import Set
import appy
import appy.version
from appy.gen import Type, Ref, String, File
from appy.gen.po import PoParser
from appy.gen.utils import produceNiceMessage, updateRolesForPermission, \
                           createObject
from appy.shared.data import languages
from migrator import Migrator


# ------------------------------------------------------------------------------
homePage = '''
<tal:main define="tool python: context.config">
 <html metal:use-macro="context/ui/template/macros/main">
  <div metal:fill-slot="content">
   <span tal:replace="structure python: tool.translate('front_page_text')"/>
  </div>
 </html>
</tal:main>
'''
errorPage = '''
<tal:main define="tool python: context.config">
 <html metal:use-macro="context/ui/template/macros/main">
  <div metal:fill-slot="content" tal:define="o python:options">
   <p tal:condition="o/error_message"
      tal:content="structure o/error_message"></p>
   <p>Error type: <b><span tal:replace="o/error_type"/></b></p>
   <p>Error value: <b><span tal:replace="o/error_value"/></b></p>
   <p tal:content="structure o/error_tb"></p>
  </div>
 </html>
</tal:main>
'''
# ------------------------------------------------------------------------------
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
        self.tool = None # The Plone version of the application tool
        self.appyTool = None # The Appy version of the application tool
        self.toolName = '%sTool' % self.productName
        self.toolInstanceName = 'portal_%s' % self.productName.lower()

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
            
        else:
            appFolder = getattr(site, self.productName)

        # Beyond content-type-specific "add" permissions, creators must also
        # have the main permission "Add portal content".
        permission = 'Add portal content'
        updateRolesForPermission(permission, tuple(allCreators), appFolder)

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
    def __init__(self, zopeContext, config, classes):
        self.zopeContext = zopeContext
        self.app = zopeContext._ProductContext__app # The root of the Zope tree
        self.config = config
        self.classes = classes
        # Unwrap some useful config variables
        self.productName = config.PROJECTNAME
        self.languages = config.languages
        self.logger = config.logger
        self.addContentPermissions = config.ADD_CONTENT_PERMISSIONS

    def installUi(self):
        '''Installs the user interface.'''
        # Delete the existing folder if it existed.
        zopeContent = self.app.objectIds()
        if 'ui' in zopeContent: self.app.manage_delObjects(['ui'])
        self.app.manage_addFolder('ui')
        # Some useful imports
        from Products.PythonScripts.PythonScript import PythonScript
        from Products.PageTemplates.ZopePageTemplate import \
             manage_addPageTemplate
        # Browse the physical folder and re-create it in the Zope folder
        j = os.path.join
        ui = j(j(appy.getPath(), 'gen'), 'ui')
        for root, dirs, files in os.walk(ui):
            folderName = root[len(ui):]
            # Get the Zope folder that corresponds to this name
            zopeFolder = self.app.ui
            if folderName:
                for name in folderName.strip(os.sep).split(os.sep):
                    zopeFolder = zopeFolder._getOb(name)
            # Create sub-folders at this level
            for name in dirs: zopeFolder.manage_addFolder(name)
            # Create files at this level
            for name in files:
                baseName, ext = os.path.splitext(name)
                f = file(j(root, name))
                if ext in File.imageExts:
                    zopeFolder.manage_addImage(name, f)
                elif ext == '.pt':
                    manage_addPageTemplate(zopeFolder, baseName, '', f.read())
                elif ext == '.py':
                    obj = PythonScript(baseName)
                    zopeFolder._setObject(baseName, obj)
                    zopeFolder._getOb(baseName).write(f.read())
                else:
                    zopeFolder.manage_addFile(name, f)
                f.close()
        # Update the home page
        if 'index_html' in zopeContent:
            self.app.manage_delObjects(['index_html'])
        manage_addPageTemplate(self.app, 'index_html', '', homePage)
        # Update the error page
        if 'standard_error_message' in zopeContent:
            self.app.manage_delObjects(['standard_error_message'])
        manage_addPageTemplate(self.app, 'standard_error_message', '',errorPage)

    def installIndexes(self, indexInfo):
        '''Updates indexes in the catalog.'''
        catalog = self.app.catalog
        logger = self.logger
        for indexName, indexType in indexInfo.iteritems():
            # If this index already exists but with a different type, remove it.
            if indexName in catalog.indexes():
                oldType = catalog.Indexes[indexName].__class__.__name__
                if oldType != indexType:
                    catalog.delIndex(indexName)
                    logger.info('Existing index "%s" of type "%s" was removed:'\
                                ' we need to recreate it with type "%s".' % \
                                (indexName, oldType, indexType))
            if indexName not in catalog.indexes():
                # We need to create this index
                type = indexType
                if type == 'ZCTextIndex': type = 'TextIndex'
                catalog.addIndex(indexName, type)
                logger.info('Created index "%s" of type "%s"...' % \
                            (indexName, type))

    def installCatalog(self):
        '''Create the catalog at the root of Zope if id does not exist.'''
        if 'catalog' not in self.app.objectIds():
            # Create the catalog
            from Products.ZCatalog.ZCatalog import manage_addZCatalog
            manage_addZCatalog(self.app, 'catalog', '')
            self.logger.info('Appy catalog created.')
        # Create or update Appy-wide indexes and field-related indexes
        indexInfo = {'State': 'FieldIndex', 'UID': 'FieldIndex',
                     'Title': 'TextIndex', 'SortableTitle': 'FieldIndex',
                     'SearchableText': 'FieldIndex', 'Creator': 'FieldIndex',
                     'Created': 'DateIndex', 'ClassName': 'FieldIndex',
                     'Allowed': 'KeywordIndex'}
        tool = self.app.config
        for className in self.config.attributes.iterkeys():
            wrapperClass = tool.getAppyClass(className, wrapper=True)
            for appyType in wrapperClass.__fields__:
                if not appyType.indexed or (appyType.name == 'title'): continue
                n = appyType.name
                indexName = 'get%s%s' % (n[0].upper(), n[1:])
                indexInfo[indexName] = appyType.getIndexType()
        self.installIndexes(indexInfo)

    def getAddPermission(self, className):
        '''What is the name of the permission allowing to create instances of
           class whose name is p_className?'''
        return self.productName + ': Add ' + className

    def installBaseObjects(self):
        '''Creates the tool and the root data folder if they do not exist.'''
        # Create or update the base folder for storing data
        zopeContent = self.app.objectIds()

        if 'data' not in zopeContent:
            self.app.manage_addFolder('data')
            data = self.app.data
            # Manager has been granted Add permissions for all root classes.
            # This may not be desired, so remove this.
            for className in self.config.rootClasses:
                permission = self.getAddPermission(className)
                data.manage_permission(permission, (), acquire=0)
            # All roles defined as creators should be able to create the
            # corresponding root classes in this folder.
            i = -1
            for klass in self.config.appClasses:
                i += 1
                if not klass.__dict__.has_key('root') or \
                   not klass.__dict__['root']:
                    continue # It is not a root class
                creators = getattr(klass, 'creators', None)
                if not creators: creators = self.config.defaultAddRoles
                className = self.config.appClassNames[i]
                permission = self.getAddPermission(className)
                updateRolesForPermission(permission, tuple(creators), data)

        if 'config' not in zopeContent:
            toolName = '%sTool' % self.productName
            createObject(self.app, 'config', toolName,self.productName,wf=False)
        # Remove some default objects created by Zope but not useful to Appy
        for name in ('standard_html_footer', 'standard_html_header',\
                     'standard_template.pt'):
            if name in zopeContent: self.app.manage_delObjects([name])

    def installTool(self):
        '''Updates the tool (now that the catalog is created) and updates its
           inner objects (users, groups, translations, documents).'''
        tool = self.app.config
        tool.createOrUpdate(True, None)
        tool.refreshSecurity()
        appyTool = tool.appy()

        # Create the admin user if no user exists.
        if not self.app.acl_users.getUsers():
            self.app.acl_users._doAddUser('admin', 'admin', ['Manager'], ())
            appyTool.log('Admin user "admin" created.')

        # Create group "admins" if it does not exist
        if not appyTool.count('Group', login='admins'):
            appyTool.create('groups', login='admins', title='Administrators',
                            roles=['Manager'])
            appyTool.log('Group "admins" created.')

        # Create a group for every global role defined in the application
        for role in self.config.applicationGlobalRoles:
            relatedGroup = '%s_group' % role
            if appyTool.count('Group', login=relatedGroup): continue
            appyTool.create('groups', login=relatedGroup, title=relatedGroup,
                            roles=[role])
            appyTool.log('Group "%s", related to global role "%s", was ' \
                         'created.' % (relatedGroup, role))

        # Create POD templates within the tool if required
        for contentType in self.config.attributes.iterkeys():
            appyClass = tool.getAppyClass(contentType)
            if not appyClass: continue # May be an abstract class
            wrapperClass = tool.getAppyClass(contentType, wrapper=True)
            for appyType in wrapperClass.__fields__:
                if appyType.type != 'Pod': continue
                # Find the attribute that stores the template, and store on
                # it the default one specified in the appyType if no
                # template is stored yet.
                attrName = appyTool.getAttributeName('podTemplate', appyClass,
                                                     appyType.name)
                fileObject = getattr(appyTool, attrName)
                if not fileObject or (fileObject.size == 0):
                    # There is no file. Put the one specified in the appyType.
                    fileName = os.path.join(appyTool.getDiskFolder(),
                                            appyType.template)
                    if os.path.exists(fileName):
                        setattr(appyTool, attrName, fileName)
                        appyTool.log('Imported "%s" in the tool in ' \
                                     'attribute "%s"'% (fileName, attrName))
                    else:
                        appyTool.log('Template "%s" was not found!' % \
                                     fileName, type='error')

        # Create or update Translation objects
        translations = [t.o.id for t in appyTool.translations]
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
            appyTool.create('translations', id=language, title=title)
            appyTool.log('Translation object created for "%s".' % language)
        # Now, we synchronise every Translation object with the corresponding
        # "po" file on disk.
        appFolder = self.config.diskFolder
        appName = self.config.PROJECTNAME
        dn = os.path.dirname
        jn = os.path.join
        i18nFolder = jn(jn(jn(dn(dn(dn(appFolder))),'Products'),appName),'i18n')
        for translation in appyTool.translations:
            # Get the "po" file
            poName = '%s-%s.po' % (appName, translation.id)
            poFile = PoParser(jn(i18nFolder, poName)).parse()
            for message in poFile.messages:
                setattr(translation, message.id, message.getMessage())
            appyTool.log('Translation "%s" updated from "%s".' % \
                         (translation.id, poName))

        # Execute custom installation code if any
        if hasattr(appyTool, 'install'):
            tool.executeAppyAction('install', reindex=False)

    def configureSessions(self):
        '''Configure the session machinery.'''
        # Register a function warning us when a session object is deleted. When
        # launching Zope, the temp folder does not exist.
        if not hasattr(self.app, 'temp_folder'): return
        self.app.temp_folder.session_data.setDelNotificationTarget(onDelSession)

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

    def installZopeClasses(self):
        '''Zope-level class registration.'''
        for klass in self.classes:
            name = klass.__name__
            module = klass.__module__
            wrapper = klass.wrapperClass
            exec 'from %s import manage_add%s as ctor' % (module, name)
            self.zopeContext.registerClass(meta_type=name,
                constructors = (ctor,),
                permission = self.addContentPermissions[name])
            # Create workflow prototypical instances in __instance__ attributes
            wf = getattr(klass.wrapperClass, 'workflow', None)
            if wf and not hasattr(wf, '__instance__'): wf.__instance__ = wf()

    def installAppyTypes(self):
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

    def installRoles(self):
        '''Installs the application-specific roles if not already done.'''
        roles = list(self.app.__ac_roles__)
        for role in self.config.applicationRoles:
            if role not in roles: roles.append(role)
        self.app.__ac_roles__ = tuple(roles)

    def install(self):
        self.logger.info('is being installed...')
        self.installRoles()
        self.installAppyTypes()
        self.installZopeClasses()
        self.enableUserTracking()
        self.configureSessions()
        self.installBaseObjects()
        self.installCatalog()
        self.installTool()
        self.installUi()
# ------------------------------------------------------------------------------
