# ------------------------------------------------------------------------------
import os, os.path, time, types
from StringIO import StringIO
from appy.shared import mimeTypes
from appy.shared.utils import getOsTempFolder
import appy.pod
from appy.pod.renderer import Renderer
import appy.gen
from appy.gen import Type
from appy.gen.plone25.mixins import AbstractMixin
from appy.gen.plone25.descriptors import ClassDescriptor

# Errors -----------------------------------------------------------------------
DELETE_TEMP_DOC_ERROR = 'A temporary document could not be removed. %s.'
POD_ERROR = 'An error occurred while generating the document. Please ' \
            'contact the system administrator.'

# ------------------------------------------------------------------------------
class FlavourMixin(AbstractMixin):
    _appy_meta_type = 'Flavour'
    def getPortalType(self, metaTypeOrAppyType):
        '''Returns the name of the portal_type that is based on
           p_metaTypeOrAppyType in this flavour.'''
        res = metaTypeOrAppyType
        isPredefined = False
        isAppy = False
        appName = self.getProductConfig().PROJECTNAME
        if not isinstance(res, basestring):
            res = ClassDescriptor.getClassName(res)
            isAppy = True
        if res.find('Extensions_appyWrappers') != -1:
            isPredefined = True
            elems = res.split('_')
            res = '%s%s' % (elems[1], elems[4])
        elif isAppy and issubclass(metaTypeOrAppyType, appy.gen.Tool):
            # This is the custom tool
            isPredefined = True
            res = '%sTool' % appName
        elif isAppy and issubclass(metaTypeOrAppyType, appy.gen.Flavour):
            # This is the custom Flavour
            isPredefined = True
            res = '%sFlavour' % appName
        if not isPredefined:
            number = self.appy().number
            if number != 1:
                res = '%s_%d' % (res, number)
        return res

    def registerPortalTypes(self):
        '''Registers, into portal_types, the portal types which are specific
           to this flavour.'''
        i = -1
        registeredFactoryTypes = self.portal_factory.getFactoryTypes().keys()
        factoryTypesToRegister = []
        appName = self.getProductConfig().PROJECTNAME
        for metaTypeName in self.allMetaTypes:
            i += 1
            portalTypeName = '%s_%d' % (metaTypeName, self.number)
            # If the portal type corresponding to the meta type is
            # registered in portal_factory (in the model:
            # use_portal_factory=True), we must also register the new
            # portal_type we are currently creating.
            if metaTypeName in registeredFactoryTypes:
                factoryTypesToRegister.append(portalTypeName)
            if not hasattr(self.portal_types, portalTypeName) and \
               hasattr(self.portal_types, metaTypeName):
                # Indeed abstract meta_types have no associated portal_type
                typeInfoName = "%s: %s (%s)" % (appName, metaTypeName,
                                                metaTypeName)
                self.portal_types.manage_addTypeInformation(
                    getattr(self.portal_types, metaTypeName).meta_type,
                    id=portalTypeName, typeinfo_name=typeInfoName)
                # Set the human readable title explicitly
                portalType = getattr(self.portal_types, portalTypeName)
                portalType.title = portalTypeName
                # Associate a workflow for this new portal type.
                pf = self.portal_workflow
                workflowChain = pf.getChainForPortalType(metaTypeName)
                pf.setChainForPortalTypes([portalTypeName],workflowChain)
                # Copy actions from the base portal type
                basePortalType = getattr(self.portal_types, metaTypeName)
                portalType._actions = tuple(basePortalType._cloneActions())
                # Copy aliases from the base portal type
                portalType.setMethodAliases(basePortalType.getMethodAliases())
        # Update the factory tool with the list of types to register
        self.portal_factory.manage_setPortalFactoryTypes(
            listOfTypeIds=factoryTypesToRegister+registeredFactoryTypes)

    def getClassFolder(self, className):
        '''Return the folder related to p_className.'''
        return getattr(self, className)

    def getAvailablePodTemplates(self, obj, phase='main'):
        '''Returns the POD templates which are available for generating a
           document from p_obj.'''
        appySelf = self.appy()
        fieldName = 'podTemplatesFor%s' % obj.meta_type
        res = []
        podTemplates = getattr(appySelf, fieldName, [])
        if not isinstance(podTemplates, list):
            podTemplates = [podTemplates]
        res = [r.o for r in podTemplates if r.podPhase == phase]
        hasParents = True
        klass = obj.__class__
        while hasParents:
            parent = klass.__bases__[-1]
            if hasattr(parent, 'wrapperClass'):
                fieldName = 'podTemplatesFor%s' % parent.meta_type
                podTemplates = getattr(appySelf, fieldName, [])
                if not isinstance(podTemplates, list):
                    podTemplates = [podTemplates]
                res += [r.o for r in podTemplates if r.podPhase == phase]
                klass = parent
            else:
                hasParents = False
        return res

    def getMaxShownTemplates(self, obj):
        attrName = 'getPodMaxShownTemplatesFor%s' % obj.meta_type
        return getattr(self, attrName)()

    def getPodInfo(self, ploneObj, fieldName):
        '''Returns POD-related information about Pod field p_fieldName defined
           on class whose p_ploneObj is an instance of.'''
        res = {}
        appyClass = self.getParentNode().getAppyClass(ploneObj.meta_type)
        appyFlavour = self.appy()
        n = appyFlavour.getAttributeName('formats', appyClass, fieldName)
        res['formats'] = getattr(appyFlavour, n)
        n = appyFlavour.getAttributeName('podTemplate', appyClass, fieldName)
        res['template'] = getattr(appyFlavour, n)
        appyType = ploneObj.getAppyType(fieldName)
        res['title'] = self.translate(appyType.labelId)
        res['context'] = appyType.context
        res['action'] = appyType.action
        return res

    def generateDocument(self):
        '''Generates the document:
           - from a PodTemplate instance if it is a class-wide pod template;
           - from field-related info on the flavour if it is a Pod field.
           UID of object that is the template target is given in the request.'''
        rq = self.REQUEST
        appyTool = self.getParentNode().appy()
        # Get the object
        objectUid = rq.get('objectUid')
        obj = self.uid_catalog(UID=objectUid)[0].getObject()
        appyObj = obj.appy()
        # Get information about the document to render. Information comes from
        # a PodTemplate instance or from the flavour itself, depending on
        # whether we generate a doc from a class-wide template or from a pod
        # field.
        templateUid = rq.get('templateUid', None)
        specificPodContext = None
        if templateUid:
            podTemplate = self.uid_catalog(UID=templateUid)[0].getObject()
            appyPt = podTemplate.appy()
            format = podTemplate.getPodFormat()
            template = appyPt.podTemplate.content
            podTitle = podTemplate.Title()
            doAction = False
        else:
            fieldName = rq.get('fieldName')
            format = rq.get('podFormat')
            podInfo = self.getPodInfo(obj, fieldName)
            template = podInfo['template'].content
            podTitle = podInfo['title']
            if podInfo['context']:
                if type(podInfo['context']) == types.FunctionType:
                    specificPodContext = podInfo['context'](appyObj)
                else:
                    specificPodContext = podInfo['context']
            doAction = rq.get('askAction') == 'True'
        # Temporary file where to generate the result
        tempFileName = '%s/%s_%f.%s' % (
            getOsTempFolder(), obj.UID(), time.time(), format)
        # Define parameters to pass to the appy.pod renderer
        currentUser = self.portal_membership.getAuthenticatedMember()
        podContext = {'tool': appyTool,    'flavour': self.appy(),
                      'user': currentUser, 'self': appyObj,
                      'now': self.getProductConfig().DateTime(),
                      'projectFolder': appyTool.getDiskFolder(),
                      }
        if specificPodContext:
            podContext.update(specificPodContext)
        if templateUid:
            podContext['podTemplate'] = appyPt
        rendererParams = {'template': StringIO(template),
                          'context': podContext,
                          'result': tempFileName}
        if appyTool.unoEnabledPython:
            rendererParams['pythonWithUnoPath'] = appyTool.unoEnabledPython
        if appyTool.openOfficePort:
            rendererParams['ooPort'] = appyTool.openOfficePort
        # Launch the renderer
        try:
            renderer = Renderer(**rendererParams)
            renderer.run()
        except appy.pod.PodError, pe:
            if not os.path.exists(tempFileName):
                # In some (most?) cases, when OO returns an error, the result is
                # nevertheless generated.
                appyTool.log(str(pe), type='error')
                appyTool.say(POD_ERROR)
                return self.goto(rq.get('HTTP_REFERER'))
        # Open the temp file on the filesystem
        f = file(tempFileName, 'rb')
        res = f.read()
        # Identify the filename to return
        fileName = u'%s-%s' % (obj.Title().decode('utf-8'), podTitle)
        fileName = appyTool.normalize(fileName)
        response = obj.REQUEST.RESPONSE
        response.setHeader('Content-Type', mimeTypes[format])
        response.setHeader('Content-Disposition', 'inline;filename="%s.%s"'\
            % (fileName, format))
        f.close()
        # Execute the related action if relevant
        if doAction and podInfo['action']:
            podInfo['action'](appyObj, podContext)
        # Returns the doc and removes the temp file
        try:
            os.remove(tempFileName)
        except OSError, oe:
            appyTool.log(DELETE_TEMP_DOC_ERROR % str(oe), type='warning')
        except IOError, ie:
            appyTool.log(DELETE_TEMP_DOC_ERROR % str(ie), type='warning')
        return res

    def getAttr(self, name):
        '''Gets on this flavour attribute named p_attrName. Useful because we
           can't use getattr directly in Zope Page Templates.'''
        return getattr(self.appy(), name, None)

    def _appy_getAllFields(self, contentType):
        '''Returns the (translated) names of fields of p_contentType.'''
        res = []
        for appyType in self.getProductConfig().attributes[contentType]:
            if appyType.name != 'title': # Will be included by default.
                label = '%s_%s' % (contentType, appyType.name)
                res.append((appyType.name, self.translate(label)))
        # Add object state
        res.append(('workflowState', self.translate('workflow_state')))
        return res

    def _appy_getSearchableFields(self, contentType):
        '''Returns the (translated) names of fields that may be searched on
           objects of type p_contentType (=indexed fields).'''
        res = []
        for appyType in self.getProductConfig().attributes[contentType]:
            if appyType.indexed:
                res.append((appyType.name, self.translate(appyType.labelId)))
        return res

    def getSearchableFields(self, contentType):
        '''Returns, among the list of all searchable fields (see method above),
           the list of fields that the user has configured in the flavour as
           being effectively used in the search screen.'''
        res = []
        fieldNames = getattr(self.appy(), 'searchFieldsFor%s' % contentType, ())
        for name in fieldNames:
            appyType = self.getAppyType(name, asDict=True,className=contentType)
            res.append(appyType)
        return res

    def getImportElements(self, contentType):
        '''Returns the list of elements that can be imported from p_path for
           p_contentType.'''
        tool = self.getParentNode()
        appyClass = tool.getAppyClass(contentType)
        importParams = tool.getCreateMeans(appyClass)['import']
        onElement = importParams['onElement'].__get__('')
        sortMethod = importParams['sort']
        if sortMethod: sortMethod = sortMethod.__get__('')
        elems = []
        importPath = getattr(self, 'importPathFor%s' % contentType)
        for elem in os.listdir(importPath):
            elemFullPath = os.path.join(importPath, elem)
            elemInfo = onElement(elemFullPath)
            if elemInfo:
                elemInfo.insert(0, elemFullPath) # To the result, I add the full
                # path of the elem, which will not be shown.
                elems.append(elemInfo)
        if sortMethod:
            elems = sortMethod(elems)
        return [importParams['headers'], elems]
# ------------------------------------------------------------------------------
