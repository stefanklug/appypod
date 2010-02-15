'''This package contains stuff used at run-time for installing a generated
   Plone product.'''

# ------------------------------------------------------------------------------
import os, os.path, time
from StringIO import StringIO
from sets import Set
import appy
from appy.gen.utils import produceNiceMessage
from appy.gen.plone25.utils import updateRolesForPermission

class PloneInstaller:
    '''This Plone installer runs every time the generated Plone product is
       installed or uninstalled (in the Plone configuration interface).'''
    def __init__(self, reinstall, productName, ploneSite, minimalistPlone,
        appClasses, appClassNames, allClassNames, catalogMap, applicationRoles,
        defaultAddRoles, workflows, appFrontPage, showPortlet, ploneStuff):
        self.reinstall = reinstall # Is it a fresh install or a re-install?
        self.productName = productName
        self.ploneSite = ploneSite
        self.minimalistPlone = minimalistPlone # If True, lots of basic Plone
                                               # stuff will be hidden.
        self.appClasses = appClasses # The list of classes declared in the
                                     # gen-application.
        self.appClassNames = appClassNames # Names of those classes
        self.allClassNames = allClassNames # Includes Flavour and PodTemplate
        self.catalogMap = catalogMap # Indicates classes to be indexed or not
        self.applicationRoles = applicationRoles # Roles defined in the app
        self.defaultAddRoles = defaultAddRoles # The default roles that can add
                                               # content
        self.workflows = workflows # Dict whose keys are class names and whose
                                   # values are workflow names (=the workflow
                                   # used by the content type)
        self.appFrontPage = appFrontPage # Does this app define a site-wide
                                         # front page?
        self.showPortlet = showPortlet # Must we show the application portlet?
        self.ploneStuff = ploneStuff # A dict of some Plone functions or vars
        self.attributes = ploneStuff['GLOBALS']['attributes']
        self.toLog = StringIO()
        self.typeAliases = {'sharing': '', 'gethtml': '',
            '(Default)': 'skynView', 'edit': 'skyn/edit',
            'index.html': '', 'properties': '', 'view': ''}
        self.tool = None # The Plone version of the application tool
        self.appyTool = None # The Appy version of the application tool
        self.toolName = '%sTool' % self.productName
        self.toolInstanceName = 'portal_%s' % self.productName.lower()


    actionsToHide = {
        'portal_actions': ('sitemap', 'accessibility', 'change_state','sendto'),
        'portal_membership': ('mystuff', 'preferences'),
        'portal_undo': ('undo',)
    }
    def customizePlone(self):
        '''Hides some UI elements that appear by default in Plone.'''
        for portalName, toHide in self.actionsToHide.iteritems():
            portal = getattr(self.ploneSite, portalName)
            portalActions = portal.listActions()
            for action in portalActions:
                if action.id in toHide: action.visible = False

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
        appFolder = getattr(site, self.productName)
        
        # All roles defined as creators should be able to create the
        # corresponding root content types in this folder.
        i = -1
        allCreators = set()
        for klass in self.appClasses:
            i += 1
            if klass.__dict__.has_key('root') and klass.__dict__['root']:
                # It is a root class.
                creators = getattr(klass, 'creators', None)
                if not creators: creators = self.defaultAddRoles
                allCreators = allCreators.union(creators)
                className = self.appClassNames[i]
                updateRolesForPermission(self.getAddPermission(className),
                                         tuple(creators), appFolder)
        # Beyond content-type-specific "add" permissions, creators must also
        # have the main permission "Add portal content".
        updateRolesForPermission('Add portal content', tuple(allCreators),
            appFolder)
        # Creates the "appy" Directory view
        if not hasattr(site.aq_base, 'skyn'):
            addDirView = self.ploneStuff['manage_addDirectoryView']
            addDirView(site, appy.getPath() + '/gen/plone25/skin',id='skyn')

    def installTypes(self):
        '''Registers and configures the Plone content types that correspond to
           gen-classes.'''
        site = self.ploneSite
        # Do Plone-based type registration
        classes = self.ploneStuff['listTypes'](self.productName)
        self.ploneStuff['installTypes'](site, self.toLog, classes,
            self.productName)
        self.ploneStuff['install_subskin'](site, self.toLog,
            self.ploneStuff['GLOBALS'])
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

        # Configure CatalogMultiplex: tell what types will be catalogued or not.
        atTool = getattr(site, self.ploneStuff['ARCHETYPETOOLNAME'])
        for meta_type in self.catalogMap:
            submap = self.catalogMap[meta_type]
            current_catalogs = Set(
                [c.id for c in atTool.getCatalogsByType(meta_type)])
            if 'white' in submap:
                for catalog in submap['white']:
                    current_catalogs.update([catalog])
            if 'black' in submap:
                for catalog in submap['black']:
                    if catalog in current_catalogs:
                        current_catalogs.remove(catalog)
            atTool.setCatalogsByType(meta_type, list(current_catalogs))

    def findPodFile(self, klass, podTemplateName):
        '''Finds the file that corresponds to p_podTemplateName for p_klass.'''
        res = None
        exec 'import %s' % klass.__module__
        exec 'moduleFile = %s.__file__' % klass.__module__
        folderName = os.path.dirname(moduleFile)
        fileName = os.path.join(folderName, '%s.odt' % podTemplateName)
        if os.path.isfile(fileName):
            res = fileName
        return res

    def updatePodTemplates(self):
        '''Creates or updates the POD templates in flavours according to pod
           declarations in the application classes.'''
        # Creates or updates the old-way class-related templates
        i = -1
        for klass in self.appClasses:
            i += 1
            if klass.__dict__.has_key('pod'):
                pod = getattr(klass, 'pod')
                if isinstance(pod, bool):
                    podTemplates = [klass.__name__]
                else:
                    podTemplates = pod
                for templateName in podTemplates:
                    fileName = self.findPodFile(klass, templateName)
                    if fileName:
                        # Create the corresponding PodTemplate in all flavours
                        for flavour in self.appyTool.flavours:
                            podId='%s_%s' % (self.appClassNames[i],templateName)
                            podAttr = 'podTemplatesFor%s'% self.appClassNames[i]
                            allPodTemplates = getattr(flavour, podAttr)
                            if allPodTemplates:
                                if isinstance(allPodTemplates, list):
                                    allIds = [p.id for p in allPodTemplates]
                                else:
                                    allIds = [allPodTemplates.id]
                            else:
                                allIds = []
                            if podId not in allIds:
                                # Create a PodTemplate instance
                                f = file(fileName)
                                flavour.create(podAttr, id=podId, podTemplate=f,
                                    title=produceNiceMessage(templateName))
                                f.close()
        # Creates the new-way templates for Pod fields if they do not exist.
        for contentType, attrNames in self.attributes.iteritems():
            appyClass = self.tool.getAppyClass(contentType)
            for attrName in attrNames:
                appyType = getattr(appyClass, attrName)
                if appyType.type == 'Pod':
                    # For every flavour, find the attribute that stores the
                    # template, and store on it the default one specified in
                    # the appyType if no template is stored yet.
                    for flavour in self.appyTool.flavours:
                        attrName = flavour.getAttributeName(
                            'podTemplate', appyClass, attrName)
                        fileObject = getattr(flavour, attrName)
                        if not fileObject or (fileObject.size == 0):
                            # There is no file. Put the one specified in the
                            # appyType.
                            fileName=os.path.join(self.appyTool.getDiskFolder(),
                                                  appyType.template)
                            if os.path.exists(fileName):
                                setattr(flavour, attrName, fileName)
                            else:
                                self.appyTool.log(
                                    'Template "%s" was not found!' % \
                                    fileName, type='error')

    def installTool(self):
        '''Configures the application tool and flavours.'''
        # Register the tool in Plone
        try:
            self.ploneSite.manage_addProduct[
                self.productName].manage_addTool(self.toolName)
        except self.ploneStuff['BadRequest']:
            # If an instance with the same name already exists, this error will
            # be unelegantly raised by Zope.
            pass
        except:
            e = sys.exc_info()
            if e[0] != 'Bad Request': raise
        
        # Hide the tool from the search form
        portalProperties = self.ploneSite.portal_properties
        if portalProperties is not None:
            siteProperties = getattr(portalProperties, 'site_properties', None)
            if siteProperties is not None and \
               siteProperties.hasProperty('types_not_searched'):
                current = list(siteProperties.getProperty('types_not_searched'))
                if self.toolName not in current:
                    current.append(self.toolName)
                    siteProperties.manage_changeProperties(
                        **{'types_not_searched' : current})

        # Hide the tool in the navigation
        if portalProperties is not None:
            nvProps = getattr(portalProperties, 'navtree_properties', None)
            if nvProps is not None and nvProps.hasProperty('idsNotToList'):
                current = list(nvProps.getProperty('idsNotToList'))
                if self.toolInstanceName not in current:
                    current.append(self.toolInstanceName)
                    nvProps.manage_changeProperties(**{'idsNotToList': current})

        self.tool = getattr(self.ploneSite, self.toolInstanceName)
        self.appyTool = self.tool.appy()
        if self.reinstall:
            self.tool.createOrUpdate(False)
        else:
            self.tool.createOrUpdate(True)

        if not self.appyTool.flavours:
            # Create the default flavour
            self.appyTool.create('flavours', title=self.productName, number=1)
        self.updatePodTemplates()

        # Uncatalog tool
        self.tool.unindexObject()

        # Register tool as configlet
        portalControlPanel = self.ploneSite.portal_controlpanel
        portalControlPanel.unregisterConfiglet(self.toolName)
        portalControlPanel.registerConfiglet(
            self.toolName, self.productName,
            'string:${portal_url}/%s' % self.toolInstanceName, 'python:True',
            'Manage portal', # Access permission
            'Products', # Section to which the configlet should be added:
                        # (Plone, Products (default) or Member)
            1, # Visibility
            '%sID' % self.toolName, 'site_icon.gif', # Icon in control_panel
            self.productName, None)

    def installRolesAndGroups(self):
        '''Registers roles used by workflows defined in this application if
           they are not registered yet. Creates the corresponding groups if
           needed.'''
        site = self.ploneSite
        data = list(site.__ac_roles__)
        for role in self.applicationRoles:
            if not role in data:
                data.append(role)
                # Add to portal_role_manager
                # First, try to fetch it. If it's not there, we probaly have no
                # PAS or another way to deal with roles was configured.
                try:
                    prm = site.acl_users.get('portal_role_manager', None)
                    if prm is not None:
                        try:
                            prm.addRole(role, role,
                                "Added by product '%s'" % self.productName)
                        except KeyError: # Role already exists
                            pass
                except AttributeError:
                    pass
            # Create a specific group and grant him this role
            group = '%s_group' % role
            if not site.portal_groups.getGroupById(group):
                site.portal_groups.addGroup(group, title=group)
                site.portal_groups.setRolesForGroup(group, [role])
        site.__ac_roles__ = tuple(data)

    def installWorkflows(self):
        '''Creates or updates the workflows defined in the application.'''
        wfTool = self.ploneSite.portal_workflow
        for contentType, workflowName in self.workflows.iteritems():
            # Register the workflow if needed
            if workflowName not in wfTool.listWorkflows():
                wfMethod = self.ploneStuff['ExternalMethod']('temp', 'temp',
                    self.productName + '.workflows', 'create_%s' % workflowName)
                workflow = wfMethod(self, workflowName)
                wfTool._setObject(workflowName, workflow)
            else:
                self.log('%s already in workflows.' % workflowName)
            # Link the workflow to the current content type
            wfTool.setChainForPortalTypes([contentType], workflowName)
        return wfTool

    def installStyleSheet(self):
        '''Registers In Plone the stylesheet linked to this application.'''
        cssName = self.productName + '.css'
        cssTitle = self.productName + ' CSS styles'
        cssInfo = {'id': cssName, 'title': cssTitle}
        try:
            portalCss = self.ploneSite.portal_css
            try:
                portalCss.unregisterResource(cssInfo['id'])
            except:
                pass
            defaults = {'id': '', 'media': 'all', 'enabled': True}
            defaults.update(cssInfo)
            portalCss.registerStylesheet(**defaults)
        except:
            # No portal_css registry
            pass

    def managePortlets(self):
        '''Shows or hides the application-specific portlet and configures other
           Plone portlets if relevant.'''
        portletName= 'here/%s_portlet/macros/portlet' % self.productName.lower()
        site = self.ploneSite
        leftPortlets = site.getProperty('left_slots')
        if not leftPortlets: leftPortlets = []
        else: leftPortlets = list(leftPortlets)
        
        if self.showPortlet and (portletName not in leftPortlets):
            leftPortlets.insert(0, portletName)
        if not self.showPortlet and (portletName in leftPortlets):
            leftPortlets.remove(portletName)
        # Remove some basic Plone portlets that make less sense when building
        # web applications.
        portletsToRemove = ["here/portlet_navigation/macros/portlet",
                            "here/portlet_recent/macros/portlet",
                            "here/portlet_related/macros/portlet"]
        if not self.minimalistPlone: portletsToRemove = []
        for p in portletsToRemove:
            if p in leftPortlets:
                leftPortlets.remove(p)
        site.manage_changeProperties(left_slots=tuple(leftPortlets))
        if self.minimalistPlone:
            site.manage_changeProperties(right_slots=())

    def finalizeInstallation(self):
        '''Performs some final installation steps.'''
        site = self.ploneSite
        # Do not generate an action (tab) for each root folder
        if self.minimalistPlone:
            site.portal_properties.site_properties.manage_changeProperties(
                disable_folder_sections=True)
        # Do not allow an anonymous user to register himself as new user
        site.manage_permission('Add portal member', ('Manager',), acquire=0)
        # Call custom installer if any
        if hasattr(self.appyTool, 'install'):
            self.tool.executeAppyAction('install', reindex=False)
        # Patch the "logout" action with a custom Appy one that updates the
        # list of currently logged users.
        for action in site.portal_membership._actions:
            if action.id == 'logout':
                action.setActionExpression(
                    'string:${portal_url}/%s/logout' % self.toolInstanceName)
        # Replace Plone front-page with an application-specific page if needed
        if self.appFrontPage:
            frontPageName = self.productName + 'FrontPage'
            site.manage_changeProperties(default_page=frontPageName)

    def log(self, msg): print >> self.toLog, msg

    def install(self):
        self.log("Installation of %s:" % self.productName)
        if self.minimalistPlone: self.customizePlone()
        self.installRootFolder()
        self.installTypes()
        self.installTool()
        self.installRolesAndGroups()
        self.installWorkflows()
        self.installStyleSheet()
        self.managePortlets()
        self.finalizeInstallation()
        self.log("Installation of %s done." % self.productName)
        return self.toLog.getvalue()

    def uninstallTool(self):
        site = self.ploneSite
        # Unmention tool in the search form
        portalProperties = getattr(site, 'portal_properties', None)
        if portalProperties is not None:
            siteProperties = getattr(portalProperties, 'site_properties', None)
            if siteProperties is not None and \
               siteProperties.hasProperty('types_not_searched'):
                current = list(siteProperties.getProperty('types_not_searched'))
                if self.toolName in current:
                    current.remove(self.toolName)
                    siteProperties.manage_changeProperties(
                        **{'types_not_searched' : current})

        # Unmention tool in the navigation
        if portalProperties is not None:
            nvProps = getattr(portalProperties, 'navtree_properties', None)
            if nvProps is not None and nvProps.hasProperty('idsNotToList'):
                current = list(nvProps.getProperty('idsNotToList'))
                if self.toolInstanceName in current:
                    current.remove(self.toolInstanceName)
                    nvProps.manage_changeProperties(**{'idsNotToList': current})

    def uninstall(self):
        self.log("Uninstallation of %s:" % self.productName)
        self.uninstallTool()
        self.log("Uninstallation of %s done." % self.productName)
        return self.toLog.getvalue()

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
        if userId: loggedUsers[userId] = t
    return res

# ------------------------------------------------------------------------------
class ZopeInstaller:
    '''This Zope installer runs every time Zope starts and encounters this
       generated Zope product.'''
    def __init__(self, zopeContext, productName, toolClass,
                 defaultAddContentPermission, addContentPermissions,
                 logger, ploneStuff):
        self.zopeContext = zopeContext
        self.productName = productName
        self.toolClass = toolClass
        self.defaultAddContentPermission = defaultAddContentPermission
        self.addContentPermissions = addContentPermissions
        self.logger = logger
        self.ploneStuff = ploneStuff # A dict of some Plone functions or vars

    def installApplication(self):
        '''Performs some application-wide installation steps.'''
        register = self.ploneStuff['DirectoryView'].registerDirectory
        register('skins', self.ploneStuff['product_globals'])
        # Register the appy skin folder among DirectoryView'able folders
        register('skin', appy.getPath() + '/gen/plone25')

    def installTool(self):
        '''Installs the tool.'''
        self.ploneStuff['ToolInit'](self.productName + ' Tools',
            tools = [self.toolClass], icon='tool.gif').initialize(
                self.zopeContext)

    def installTypes(self):
        '''Installs and configures the types defined in the application.'''
        contentTypes, constructors, ftis = self.ploneStuff['process_types'](
            self.ploneStuff['listTypes'](self.productName), self.productName)

        self.ploneStuff['cmfutils'].ContentInit(self.productName + ' Content',
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

    def enableUserTracking(self):
        '''Enables the machinery allowing to know who is currently logged in.
           Information about logged users will be stored in RAM, in the variable
           named loggedUsers defined above.'''
        global originalTraverse
        if not originalTraverse:
            # User tracking is not enabled yet. Do it now.
            BaseRequest = self.ploneStuff['BaseRequest']
            originalTraverse = BaseRequest.traverse
            BaseRequest.traverse = traverseWrapper

    def finalizeInstallation(self):
        '''Performs some final installation steps.'''
        # Apply customization policy if any
        cp = self.ploneStuff['CustomizationPolicy']
        if cp and hasattr(cp, 'register'): cp.register(context)

    def install(self):
        self.logger.info('is being installed...')
        self.installApplication()
        self.installTool()
        self.installTypes()
        self.enableUserTracking()
        self.finalizeInstallation()
# ------------------------------------------------------------------------------
