'''This package contains stuff used at run-time for installing a generated
   Zope product.'''

# ------------------------------------------------------------------------------
import os, os.path
import appy
import appy.version
import appy.gen as gen
from appy.gen.po import PoParser
from appy.gen.indexer import defaultIndexes, updateIndexes
from appy.gen.migrator import Migrator
from appy.gen import utils as gutils
from appy.shared.data import languages

# ------------------------------------------------------------------------------
homePage = '<tal:h define="dummy python: request.RESPONSE.redirect(' \
           'context.config.getHomePage())"/>'

def onDelSession(sessionObject, container):
    '''This function is called when a session expires.'''
    rq = container.REQUEST
    if rq.cookies.has_key('_appy_') and rq.cookies.has_key('_ZopeId') and \
       (rq['_ZopeId'] == sessionObject.token):
        # The request comes from a guy whose session has expired.
        resp = rq.RESPONSE
        resp.expireCookie('_appy_', path='/')
        resp.setHeader('Content-Type', 'text/html')
        resp.write('<center>For security reasons, your session has ' \
                   'expired.</center>')

# ------------------------------------------------------------------------------
class ZopeInstaller:
    '''This Zope installer runs every time Zope starts and encounters this
       generated Zope product.'''
    # Info about the default users that are always present.
    defaultUsers = {'admin': ('Manager',), 'system': ('Manager',), 'anon': ()}

    def __init__(self, zopeContext, config, classes):
        self.zopeContext = zopeContext
        self.app = zopeContext._ProductContext__app # The root of the Zope tree
        self.config = config
        self.classes = classes
        # Unwrap some useful config variables
        self.productName = config.PROJECTNAME
        self.languages = config.appConfig.languages
        self.logger = config.logger

    def installUi(self):
        '''Installs the user interface.'''
        # Some useful imports.
        from OFS.Folder import manage_addFolder
        from OFS.Image import manage_addImage, manage_addFile
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
                    ext = os.path.splitext(name)[1]
                    if hasattr(zopeFolder.aq_base, name): continue
                    f = file(j(root, name))
                    if name == 'favicon.ico':
                        if not hasattr(self.app, name):
                            # Copy it at the root. Else, IE won't notice it.
                            manage_addImage(self.app, name, f)
                    elif ext in gen.File.imageExts:
                        manage_addImage(zopeFolder, name, f)
                    else:
                        manage_addFile(zopeFolder, name, f)
                    f.close()
        # Update the home page
        if 'index_html' in zopeContent:
            self.app.manage_delObjects(['index_html'])
        from Products.PageTemplates.ZopePageTemplate import \
             manage_addPageTemplate
        manage_addPageTemplate(self.app, 'index_html', '', homePage)
        # Remove the error page.
        if 'standard_error_message' in zopeContent:
            self.app.manage_delObjects(['standard_error_message'])

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

    def installBaseObjects(self):
        '''Creates the tool and the base data folder if they do not exist.'''
        # Create the tool.
        zopeContent = self.app.objectIds()
        from OFS.Folder import manage_addFolder

        if 'config' not in zopeContent:
            toolName = '%sTool' % self.productName
            gutils.createObject(self.app, 'config', toolName, self.productName,
                                wf=False, noSecurity=True)
        # Create the base data folder.
        if 'data' not in zopeContent: manage_addFolder(self.app, 'data')

        # Remove some default objects created by Zope but not useful to Appy
        for name in ('standard_html_footer', 'standard_html_header',\
                     'standard_template.pt'):
            if name in zopeContent: self.app.manage_delObjects([name])

    def installTool(self):
        '''Updates the tool (now that the catalog is created) and updates its
           inner objects (users, groups, translations, documents).'''
        tool = self.app.config
        tool.createOrUpdate(True, None)
        appyTool = tool.appy()
        appyTool.log('Appy version is "%s".' % appy.version.short)

        # Create the default users if they do not exist.
        for login, roles in self.defaultUsers.iteritems():
            if not appyTool.count('User', noSecurity=True, login=login):
                appyTool.create('users', noSecurity=True, id=login, login=login,
                                password1=login, password2=login,
                                email='%s@appyframework.org'%login, roles=roles)
                appyTool.log('User "%s" created.' % login)

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

    def installZopeClasses(self):
        '''Zope-level class registration.'''
        for klass in self.classes:
            name = klass.__name__
            module = klass.__module__
            wrapper = klass.wrapperClass
            exec 'from %s import manage_add%s as ctor' % (module, name)
            self.zopeContext.registerClass(meta_type=name,
                constructors = (ctor,), permission = None)
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
            state = gen.String(show='result')
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
