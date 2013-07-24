'''This package contains stuff used at run-time for installing a generated
   Zope product.'''

# ------------------------------------------------------------------------------
import os, os.path, time
import appy
import appy.version
import appy.gen as gen
from appy.gen.po import PoParser
from appy.gen.utils import updateRolesForPermission, createObject
from appy.gen.indexer import defaultIndexes, updateIndexes
from appy.gen.migrator import Migrator
from appy.shared.data import languages

# ------------------------------------------------------------------------------
homePage = '''
<tal:hp define="tool python: context.config;
                dummy python: request.RESPONSE.redirect(tool.getHomePage())">
</tal:hp>
'''
errorPage = '''
<tal:main define="tool python: context.config"
          on-error="string: ServerError">
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
        resp.setHeader('Content-Type', 'text/html')
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
        self.languages = config.appConfig.languages
        self.logger = config.logger
        self.addContentPermissions = config.ADD_CONTENT_PERMISSIONS

    def installUi(self):
        '''Installs the user interface.'''
        # Some useful imports
        from OFS.Folder import manage_addFolder
        from OFS.Image import manage_addImage, manage_addFile
        from Products.PythonScripts.PythonScript import PythonScript
        from Products.PageTemplates.ZopePageTemplate import \
             manage_addPageTemplate
        # Delete the existing folder if it existed.
        zopeContent = self.app.objectIds()
        if 'ui' in zopeContent: self.app.manage_delObjects(['ui'])
        manage_addFolder(self.app, 'ui')
        # Browse the physical ui folders (the Appy one and an app-specific, if
        # the app defines one) and create the corresponding objects in the Zope
        # folder. In the case of files having the same name in both folders,
        # the one from the app-specific folder is chosen.
        j = os.path.join
        uiFolders = [j(j(appy.getPath(), 'gen'), 'ui')]
        appUi = j(self.config.diskFolder, 'ui')
        if os.path.exists(appUi): uiFolders.insert(0, appUi)
        for ui in uiFolders:
            for root, dirs, files in os.walk(ui):
                folderName = root[len(ui):]
                # Get the Zope folder that corresponds to this name
                zopeFolder = self.app.ui
                if folderName:
                    for name in folderName.strip(os.sep).split(os.sep):
                        zopeFolder = zopeFolder._getOb(name)
                # Create sub-folders at this level
                for name in dirs:
                    if not hasattr(zopeFolder.aq_base, name):
                        manage_addFolder(zopeFolder, name)
                # Create files at this level
                for name in files:
                    zopeName, ext = os.path.splitext(name)
                    if ext not in ('.pt', '.py'):
                        # In the ZODB, pages and scripts have their name without
                        # their extension.
                        zopeName = name
                    if hasattr(zopeFolder.aq_base, zopeName): continue
                    f = file(j(root, name))
                    if zopeName == 'favicon.ico':
                        if not hasattr(self.app, zopeName):
                            # Copy it at the root. Else, IE won't notice it.
                            manage_addImage(self.app, zopeName, f)
                    elif ext in gen.File.imageExts:
                        manage_addImage(zopeFolder, zopeName, f)
                    elif ext == '.pt':
                        manage_addPageTemplate(zopeFolder,zopeName,'',f.read())
                    elif ext == '.py':
                        obj = PythonScript(zopeName)
                        zopeFolder._setObject(zopeName, obj)
                        zopeFolder._getOb(zopeName).write(f.read())
                    else:
                        manage_addFile(zopeFolder, zopeName, f)
                    f.close()
        # Update the home page
        if 'index_html' in zopeContent:
            self.app.manage_delObjects(['index_html'])
        manage_addPageTemplate(self.app, 'index_html', '', homePage)
        # Update the error page
        if 'standard_error_message' in zopeContent:
            self.app.manage_delObjects(['standard_error_message'])
        manage_addPageTemplate(self.app, 'standard_error_message', '',errorPage)

    def installCatalog(self):
        '''Create the catalog at the root of Zope if id does not exist.'''
        if 'catalog' not in self.app.objectIds():
            # Create the catalog
            from Products.ZCatalog.ZCatalog import manage_addZCatalog
            manage_addZCatalog(self.app, 'catalog', '')
            self.logger.info('Appy catalog created.')

        # Create lexicons for ZCTextIndexes
        catalog = self.app.catalog
        lexicons = catalog.objectIds()
        from Products.ZCTextIndex.ZCTextIndex import manage_addLexicon
        if 'xhtml_lexicon' not in lexicons:
            lex = appy.Object(group='XHTML indexer', name='XHTML indexer')
            manage_addLexicon(catalog, 'xhtml_lexicon', elements=[lex])
        if 'text_lexicon' not in lexicons:
            lex = appy.Object(group='Text indexer', name='Text indexer')
            manage_addLexicon(catalog, 'text_lexicon', elements=[lex])
        if 'list_lexicon' not in lexicons:
            lex = appy.Object(group='List indexer', name='List indexer')
            manage_addLexicon(catalog, 'list_lexicon', elements=[lex])

        # Delete the deprecated one if it exists
        if 'lexicon' in lexicons: catalog.manage_delObjects(['lexicon'])

        # Create or update Appy-wide indexes and field-related indexes
        indexInfo = defaultIndexes.copy()
        tool = self.app.config
        for className in self.config.attributes.iterkeys():
            wrapperClass = tool.getAppyClass(className, wrapper=True)
            indexInfo.update(wrapperClass.getIndexes(includeDefaults=False))
        updateIndexes(self, indexInfo)
        # Re-index index "SearchableText", wrongly defined for Appy < 0.8.3.
        stIndex = catalog.Indexes['SearchableText']
        if stIndex.indexSize() == 0:
            self.logger.info('Reindexing SearchableText...')
            catalog.reindexIndex('SearchableText', self.app.REQUEST)
            self.logger.info('Done.')

    def getAddPermission(self, className):
        '''What is the name of the permission allowing to create instances of
           class whose name is p_className?'''
        return self.productName + ': Add ' + className

    def installBaseObjects(self):
        '''Creates the tool and the root data folder if they do not exist.'''
        # Create or update the base folder for storing data
        zopeContent = self.app.objectIds()
        from OFS.Folder import manage_addFolder

        if 'config' not in zopeContent:
            toolName = '%sTool' % self.productName
            createObject(self.app, 'config', toolName, self.productName,
                         wf=False, noSecurity=True)

        if 'data' not in zopeContent:
            manage_addFolder(self.app, 'data')
            data = self.app.data
            tool = self.app.config
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
                className = self.config.appClassNames[i]
                wrapperClass = tool.getAppyClass(className, wrapper=True)
                creators = wrapperClass.getCreators(self.config)
                permission = self.getAddPermission(className)
                updateRolesForPermission(permission, tuple(creators), data)

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
        appyTool.log('Appy version is "%s".' % appy.version.short)

        # Create the admin user if it does not exist.
        if not appyTool.count('User', noSecurity=True, login='admin'):
            appyTool.create('users', noSecurity=True, login='admin',
                            password1='admin', password2='admin',
                            email='admin@appyframework.org', roles=['Manager'])
            appyTool.log('Admin user "admin" created.')

        # Create group "admins" if it does not exist
        if not appyTool.count('Group', noSecurity=True, login='admins'):
            appyTool.create('groups', noSecurity=True, login='admins',
                            title='Administrators', roles=['Manager'])
            appyTool.log('Group "admins" created.')

        # Create a group for every global role defined in the application
        # (if required).
        if self.config.appConfig.groupsForGlobalRoles:
            for role in self.config.applicationGlobalRoles:
                groupId = role.lower()
                if appyTool.count('Group', noSecurity=True, login=groupId):
                    continue
                appyTool.create('groups', noSecurity=True, login=groupId,
                                title=role, roles=[role])
                appyTool.log('Group "%s", related to global role "%s", was ' \
                             'created.' % (groupId, role))

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
                        # If the template is ods, set the default format to ods
                        # (because default is odt)
                        if fileName.endswith('.ods'):
                            formats = appyTool.getAttributeName('formats',
                                                       appyClass, appyType.name)
                            setattr(appyTool, formats, ['ods'])
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
            appyTool.create('translations', noSecurity=True,
                            id=language, title=title)
            appyTool.log('Translation object created for "%s".' % language)

        # Synchronize, if required, synchronise every Translation object with
        # the corresponding "po" file on disk.
        if appyTool.loadTranslationsAtStartup:
            appFolder = self.config.diskFolder
            appName = self.config.PROJECTNAME
            i18nFolder = os.path.join(appFolder, 'tr')
            for translation in appyTool.translations:
                # Get the "po" file
                poName = '%s-%s.po' % (appName, translation.id)
                poFile = PoParser(os.path.join(i18nFolder, poName)).parse()
                for message in poFile.messages:
                    setattr(translation, message.id, message.getMessage())
                appyTool.log('Translation "%s" updated from "%s".' % \
                             (translation.id, poName))

        # Execute custom installation code if any.
        if hasattr(appyTool, 'onInstall'): appyTool.onInstall()

    def configureSessions(self):
        '''Configure the session machinery.'''
        # Register a function warning us when a session object is deleted. When
        # launching Zope in test mode, the temp folder does not exist.
        if not hasattr(self.app, 'temp_folder'): return
        sessionData = self.app.temp_folder.session_data
        if self.config.appConfig.enableSessionTimeout:
            sessionData.setDelNotificationTarget(onDelSession)
        else:
            sessionData.setDelNotificationTarget(None)

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
            wf = wrapper.getWorkflow()
            if not hasattr(wf, '__instance__'): wf.__instance__ = wf()

    def installAppyTypes(self):
        '''We complete here the initialisation process of every Appy type of
           every gen-class of the application.'''
        appName = self.productName
        for klass in self.classes:
            # Store on wrapper class the ordered list of Appy types
            wrapperClass = klass.wrapperClass
            if not hasattr(wrapperClass, 'title'):
                # Special field "type" is mandatory for every class.
                title = gen.String(multiplicity=(1,1), show='edit',
                                   indexed=True, searchable=True)
                title.init('title', None, 'appy')
                setattr(wrapperClass, 'title', title)
            # Special field "state" must be added for every class
            state = gen.String(validator=gen.Selection('_appy_listStates'),
                               show='result')
            state.init('state', None, 'workflow')
            setattr(wrapperClass, 'state', state)
            names = self.config.attributes[wrapperClass.__name__[:-8]]
            wrapperClass.__fields__ = [getattr(wrapperClass, n) for n in names]
            # Post-initialise every Appy type
            for baseClass in klass.wrapperClass.__bases__:
                if baseClass.__name__ == 'AbstractWrapper': continue
                for name, appyType in baseClass.__dict__.iteritems():
                    if not isinstance(appyType, gen.Field) or \
                           (isinstance(appyType, gen.Ref) and appyType.isBack):
                        continue # Back refs are initialised within fw refs
                    appyType.init(name, baseClass, appName)

    def installRoles(self):
        '''Installs the application-specific roles if not already done.'''
        roles = list(self.app.__ac_roles__)
        for role in self.config.applicationRoles:
            if role not in roles: roles.append(role)
        self.app.__ac_roles__ = tuple(roles)

    def installDependencies(self):
        '''Zope products are installed in alphabetical order. But here, we need
           ZCTextIndex to be installed before our Appy application. So, we cheat
           and force Zope to install it now.'''
        from OFS.Application import install_product
        import Products
        install_product(self.app, Products.__path__[1], 'ZCTextIndex', [], {})

    def install(self):
        self.logger.info('is being installed...')
        self.installDependencies()
        self.installRoles()
        self.installAppyTypes()
        self.installZopeClasses()
        self.enableUserTracking()
        self.configureSessions()
        self.installBaseObjects()
        # The following line cleans and rebuilds the catalog entirely.
        #self.app.config.appy().refreshCatalog()
        self.installCatalog()
        self.installTool()
        self.installUi()
        # Perform migrations if required
        Migrator(self).run()
        # Update Appy version in the database
        self.app.config.appy().appyVersion = appy.version.short
        # Empty the fake REQUEST object, only used at Zope startup.
        del self.app.config.getProductConfig().fakeRequest.wrappers
# ------------------------------------------------------------------------------
