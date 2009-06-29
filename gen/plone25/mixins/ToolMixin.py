# ------------------------------------------------------------------------------
import re, os, os.path
from appy.gen.utils import FieldDescr
from appy.gen.plone25.mixins import AbstractMixin
from appy.gen.plone25.mixins.FlavourMixin import FlavourMixin
from appy.gen.plone25.wrappers import AbstractWrapper

_PY = 'Please specify a file corresponding to a Python interpreter ' \
      '(ie "/usr/bin/python").'
FILE_NOT_FOUND = 'Path "%s" was not found.'
VALUE_NOT_FILE = 'Path "%s" is not a file. ' + _PY
NO_PYTHON = "Name '%s' does not starts with 'python'. " + _PY
NOT_UNO_ENABLED_PYTHON = '"%s" is not a UNO-enabled Python interpreter. ' \
                         'To check if a Python interpreter is UNO-enabled, ' \
                         'launch it and type "import uno". If you have no ' \
                         'ImportError exception it is ok.'

# ------------------------------------------------------------------------------
class ToolMixin(AbstractMixin):
    _appy_meta_type = 'tool'
    def _appy_validateUnoEnabledPython(self, value):
        '''This method represents the validator for field unoEnabledPython.
           This field is present on the Tool only if POD is needed.'''
        if value:
            if not os.path.exists(value):
                return FILE_NOT_FOUND % value
            if not os.path.isfile(value):
                return VALUE_NOT_FILE % value
            if not os.path.basename(value).startswith('python'):
                return NO_PYTHON % value
            if os.system('%s -c "import uno"' % value):
                return NOT_UNO_ENABLED_PYTHON % value
        return None

    def getFlavour(self, contextObjOrPortalType, appy=False):
        '''Gets the flavour that corresponds to p_contextObjOrPortalType.'''
        if isinstance(contextObjOrPortalType, basestring):
            portalTypeName = contextObjOrPortalType
        else:
            # It is the contextObj, not a portal type name
            portalTypeName = contextObjOrPortalType.portal_type
        res = None
        appyTool = self._appy_getWrapper(force=True)
        flavourNumber = None
        nameElems = portalTypeName.split('_')
        if len(nameElems) > 1:
            try:
                flavourNumber = int(nameElems[-1])
            except ValueError:
                pass
        appName = self.getProductConfig().PROJECTNAME
        if flavourNumber != None:
            for flavour in appyTool.flavours:
                if flavourNumber == flavour.number:
                    res = flavour
        elif portalTypeName == ('%sFlavour' % appName):
            # Current object is the Flavour itself. In this cas we simply
            # return the wrapped contextObj. Here we are sure that
            # contextObjOrPortalType is an object, not a portal type.
            res = contextObjOrPortalType._appy_getWrapper(force=True)
        if not res and appyTool.flavours:
            res = appyTool.flavours[0]
        # If appy=False, return the Plone object and not the Appy wrapper
        # (this way, we avoid Zope security/access-related problems while
        # using this object in Zope Page Templates)
        if res and not appy:
            res = res.o
        return res

    def getFlavoursInfo(self):
        '''Returns information about flavours.'''
        res = []
        appyTool = self._appy_getWrapper(force=True)
        for flavour in appyTool.flavours:
            if isinstance(flavour.o, FlavourMixin):
                # This is a bug: sometimes other objects are associated as
                # flavours.
                res.append({'title': flavour.title, 'number':flavour.number})
        return res

    def getAppFolder(self):
        '''Returns the folder at the root of the Plone site that is dedicated
           to this application.'''
        portal = self.getProductConfig().getToolByName(
            self, 'portal_url').getPortalObject()
        appName = self.getProductConfig().PROJECTNAME
        return getattr(portal, appName)

    def showPortlet(self):
        return not self.portal_membership.isAnonymousUser()

    def executeQuery(self, queryName, flavourNumber):
        if queryName.find(',') != -1:
            # Several content types are specified
            portalTypes = queryName.split(',')
            if flavourNumber != 1:
                portalTypes = ['%s_%d' % (pt, flavourNumber) \
                               for pt in portalTypes]
        else:
            portalTypes = queryName
        params = {'portal_type': portalTypes, 'batch': True}
        res = self.portal_catalog.searchResults(**params)
        batchStart = self.REQUEST.get('b_start', 0)
        res = self.getProductConfig().Batch(res,
            self.getNumberOfResultsPerPage(), int(batchStart), orphan=0)
        return res

    def getResultColumnsNames(self, queryName):
        contentTypes = queryName.strip(',').split(',')
        resSet = None # Temporary set for computing intersections.
        res = [] # Final, sorted result.
        flavour = None
        fieldNames = None
        for cType in contentTypes:
            # Get the flavour tied to those content types
            if not flavour:
                flavour = self.getFlavour(cType, appy=True)
            if flavour.number != 1:
                cType = cType.rsplit('_', 1)[0]
            fieldNames = getattr(flavour, 'resultColumnsFor%s' % cType)
            if not resSet:
                resSet = set(fieldNames)
            else:
                resSet = resSet.intersection(fieldNames)
        # By converting to set, we've lost order. Let's put things in the right
        # order.
        for fieldName in fieldNames:
            if fieldName in resSet:
                res.append(fieldName)
        return res

    def getResultColumns(self, anObject, queryName):
        '''What columns must I show when displaying a list of root class
           instances? Result is a list of tuples containing the name of the
           column (=name of the field) and a FieldDescr instance.'''
        res = []
        for fieldName in self.getResultColumnsNames(queryName):
            if fieldName == 'workflowState':
                # We do not return a FieldDescr instance if the attributes is
                # not a *real* attribute but the workfow state.
                res.append(fieldName)
            else:
                # Create a FieldDescr instance
                appyType = anObject.getAppyType(fieldName)
                atField = anObject.schema.get(fieldName)
                fieldDescr = FieldDescr(atField, appyType, None)
                res.append(fieldDescr.get())
        return res

    xhtmlToText = re.compile('<.*?>', re.S)
    def getReferenceLabel(self, brain, appyType):
        '''p_appyType is a Ref with link=True. I need to display, on an edit
           view, the referenced object p_brain in the listbox that will allow
           the user to choose which object(s) to link through the Ref.
           According to p_appyType, the label may only be the object title,
           or more if parameter appyType.shownInfo is used.'''
        res = brain.Title
        if 'title' in appyType['shownInfo']:
            # We may place it at another place
            res = ''
        appyObj = brain.getObject()._appy_getWrapper(force=True)
        for fieldName in appyType['shownInfo']:
            value = getattr(appyObj, fieldName)
            if isinstance(value, AbstractWrapper):
                value = value.title.decode('utf-8')
            elif isinstance(value, basestring):
                value = value.decode('utf-8')
                refAppyType = appyObj.o.getAppyType(fieldName)
                if refAppyType and (refAppyType['type'] == 'String') and \
                   (refAppyType['format'] == 2):
                    value = self.xhtmlToText.sub(' ', value)
            else:
                value = str(value)
            prefix = ''
            if res:
                prefix = ' | '
            res += prefix + value.encode('utf-8')
        maxWidth = self.getListBoxesMaximumWidth()
        if len(res) > maxWidth:
            res = res[:maxWidth-2] + '...'
        return res

    translationMapping = {'portal_path': ''}
    def translateWithMapping(self, label):
        '''Translates p_label in the application domain, with a default
           translation mapping.'''
        if not self.translationMapping['portal_path']:
            self.translationMapping['portal_path'] = \
                self.portal_url.getPortalPath()
        appName = self.getProductConfig().PROJECTNAME
        return self.utranslate(label, self.translationMapping, domain=appName)
# ------------------------------------------------------------------------------
