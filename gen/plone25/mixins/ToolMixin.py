# ------------------------------------------------------------------------------
import re, os, os.path, Cookie
from appy.gen.utils import FieldDescr, SomeObjects
from appy.gen.plone25.mixins import AbstractMixin
from appy.gen.plone25.mixins.FlavourMixin import FlavourMixin
from appy.gen.plone25.wrappers import AbstractWrapper
from appy.gen.plone25.descriptors import ArchetypesClassDescriptor

_PY = 'Please specify a file corresponding to a Python interpreter ' \
      '(ie "/usr/bin/python").'
FILE_NOT_FOUND = 'Path "%s" was not found.'
VALUE_NOT_FILE = 'Path "%s" is not a file. ' + _PY
NO_PYTHON = "Name '%s' does not starts with 'python'. " + _PY
NOT_UNO_ENABLED_PYTHON = '"%s" is not a UNO-enabled Python interpreter. ' \
                         'To check if a Python interpreter is UNO-enabled, ' \
                         'launch it and type "import uno". If you have no ' \
                         'ImportError exception it is ok.'
jsMessages = ('no_elem_selected', 'delete_confirm')

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

    def getAppName(self):
        '''Returns the name of this application.'''
        return self.getProductConfig().PROJECTNAME

    def getAppFolder(self):
        '''Returns the folder at the root of the Plone site that is dedicated
           to this application.'''
        cfg = self.getProductConfig()
        portal = cfg.getToolByName(self, 'portal_url').getPortalObject()
        return getattr(portal, self.getAppName())

    def getRootClasses(self):
        '''Returns the list of root classes for this application.'''
        return self.getProductConfig().rootClasses

    def showPortlet(self):
        return not self.portal_membership.isAnonymousUser()

    def getObject(self, uid, appy=False):
        '''Allows to retrieve an object from its p_uid.'''
        res = self.uid_catalog(UID=uid)
        if res: return res[0].getObject()
        return None

    _sortFields = {'title': 'sortable_title'}
    def executeQuery(self, contentType, flavourNumber=1, searchName=None,
                     startNumber=0, search=None, remember=False,
                     brainsOnly=False, maxResults=None):
        '''Executes a query on a given p_contentType (or several, separated
           with commas) in Plone's portal_catalog. Portal types are from the
           flavour numbered p_flavourNumber. If p_searchName is specified, it
           corresponds to a search defined on p_contentType: additional search
           criteria will be added to the query. We will retrieve objects from
           p_startNumber. If p_search is defined, it corresponds to a custom
           Search instance (instead of a predefined named search like in
           p_searchName). If both p_searchName and p_search are given, p_search
           is ignored. This method returns a list of objects in the form of the
           __dict__ attribute of an instance of SomeObjects (see in
           appy.gen.utils). We return the __dict__ attribute instead of real
           instance: that way, it can be used in ZPTs without security problems.
           If p_brainsOnly is True, it returns a list of brains instead (can be
           useful for some usages like knowing the number of objects without
           needing to get information about them). If no p_maxResults is
           specified, the method returns maximum
           self.getNumberOfResultsPerPage(). The method returns all objects if
           p_maxResults equals string "NO_LIMIT". p_maxResults is ignored if
           p_brainsOnly is True.'''
        # Is there one or several content types ?
        if contentType.find(',') != -1:
            # Several content types are specified
            portalTypes = contentType.split(',')
            if flavourNumber != 1:
                portalTypes = ['%s_%d' % (pt, flavourNumber) \
                               for pt in portalTypes]
        else:
            portalTypes = contentType
        params = {'portal_type': portalTypes}
        if not brainsOnly: params['batch'] = True
        # Manage additional criteria from a search when relevant
        if searchName or search:
            # In this case, contentType must contain a single content type.
            appyClass = self.getAppyClass(contentType)
            if searchName:
                search = ArchetypesClassDescriptor.getSearch(
                    appyClass, searchName)
        if search:
            # Add additional search criteria
            for fieldName, fieldValue in search.fields.iteritems():
                attrName = fieldName
                if attrName == 'title': attrName = 'Title'
                elif attrName == 'description': attrName = 'Description'
                elif attrName == 'state': attrName = 'review_state'
                else: attrName = 'get%s%s'% (fieldName[0].upper(),fieldName[1:])
                params[attrName] = fieldValue
            # Add a sort order if specified
            sb = search.sortBy
            if sb:
                # For field 'title', Plone has created a specific index
                # 'sortable_title', because index 'Title' is a ZCTextIndex
                # (for searchability) and can't be used for sorting.
                if self._sortFields.has_key(sb): sb = self._sortFields[sb]
                params['sort_on'] = sb
        brains = self.portal_catalog.searchResults(**params)
        if brainsOnly: return brains
        if not maxResults: maxResults = self.getNumberOfResultsPerPage()
        elif maxResults == 'NO_LIMIT': maxResults = None
        res = SomeObjects(brains, maxResults, startNumber)
        res.brainsToObjects()
        # In some cases (p_remember=True), we need to keep some information
        # about the query results in the current user's session, allowing him
        # to navigate within elements without re-triggering the query every
        # time a page for an element is consulted.
        if remember:
            if not searchName:
                # It is the global search for all objects pf p_contentType
                searchName = contentType
            s = self.REQUEST.SESSION
            uids = {}
            i = -1
            for obj in res.objects:
                i += 1
                uids[startNumber+i] = obj.UID()
            s['search_%s_%s' % (flavourNumber, searchName)] = uids
        return res.__dict__

    def getResultColumnsNames(self, contentType):
        contentTypes = contentType.strip(',').split(',')
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

    def getResultColumns(self, anObject, contentType):
        '''What columns must I show when displaying a list of root class
           instances? Result is a list of tuples containing the name of the
           column (=name of the field) and a FieldDescr instance.'''
        res = []
        for fieldName in self.getResultColumnsNames(contentType):
            if fieldName == 'workflowState':
                # We do not return a FieldDescr instance if the attributes is
                # not a *real* attribute but the workfow state.
                res.append(fieldName)
            else:
                # Create a FieldDescr instance
                appyType = anObject.getAppyType(fieldName)
                if not appyType:
                    res.append({'atField': None, 'name': fieldName})
                    # The field name is wrong.
                    # We return it so we can show it in an error message.
                else:
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

    def getPublishedObject(self):
        '''Gets the currently published object.'''
        rq = self.REQUEST
        obj = rq['PUBLISHED']
        parent = obj.getParentNode()
        if parent.id == 'skyn': return parent.getParentNode()
        return rq['PUBLISHED']

    def getAppyClass(self, contentType):
        '''Gets the Appy Python class that is related to p_contentType.'''
        # Retrieve first the Archetypes class corresponding to p_ContentType
        portalType = self.portal_types.get(contentType)
        atClassName = portalType.getProperty('content_meta_type')
        appName = self.getProductConfig().PROJECTNAME
        exec 'from Products.%s.%s import %s as atClass' % \
            (appName, atClassName, atClassName)
        # Get then the Appy Python class
        return atClass.wrapperClass.__bases__[-1]
        
    def getCreateMeans(self, contentTypeOrAppyClass):
        '''Gets the different ways objects of p_contentTypeOrAppyClass (which
           can be a Plone content type or a Appy class) can be created
           (via a web form, by importing external data, etc). Result is a
           dict whose keys are strings (ie "form", "import"...) and whose
           values are additional data bout the particular mean.'''
        pythonClass = contentTypeOrAppyClass
        if isinstance(contentTypeOrAppyClass, basestring):
            pythonClass = self.getAppyClass(pythonClass)
        res = {}
        if not pythonClass.__dict__.has_key('create'):
            res['form'] = None
            # No additional data for this means, which is the default one.
        else:
            means = pythonClass.create
            if means:
                if isinstance(means, basestring): res[means] = None
                elif isinstance(means, list) or isinstance(means, tuple):
                    for mean in means:
                        if isinstance(mean, basestring):
                            res[mean] = None
                        else:
                            res[mean.id] = mean.__dict__
                else:
                    res[means.id] = means.__dict__
        return res

    def getImportElements(self, contentType):
        '''Returns the list of elements that can be imported from p_path for
           p_contentType.'''
        appyClass = self.getAppyClass(contentType)
        importParams = self.getCreateMeans(appyClass)['import']
        columnMethod = importParams['columnMethod'].__get__('')
        sortMethod = importParams['sortMethod']
        if sortMethod: sortMethod = sortMethod.__get__('')
        elems = []
        for elem in os.listdir(importParams['path']):
            elemFullPath = os.path.join(importParams['path'], elem)
            niceElem = columnMethod(elemFullPath)
            niceElem.insert(0, elemFullPath) # To the result, I add the full
            # path of the elem, which will not be shown.
            elems.append(niceElem)
        if sortMethod:
            elems = sortMethod(elems)
        return [importParams['columnHeaders'], elems]

    def onImportObjects(self):
        '''This method is called when the user wants to create objects from
           external data.'''
        rq = self.REQUEST
        appyClass = self.getAppyClass(rq.get('type_name'))
        importPaths = rq.get('importPath').split('|')
        appFolder = self.getAppFolder()
        for importPath in importPaths:
            if not importPath: continue
            objectId = os.path.basename(importPath)
            self.appy().create(appyClass, id=objectId, _data=importPath)
        self.plone_utils.addPortalMessage(self.translate('import_done'))
        return self.goto(rq['HTTP_REFERER'])

    def isAlreadyImported(self, contentType, importPath):
        appFolder = self.getAppFolder()
        objectId = os.path.basename(importPath)
        if hasattr(appFolder.aq_base, objectId):
            return True
        else:
            return False

    def getJavascriptMessages(self):
        '''Returns the translated version of messages that must be shown in
           Javascript popups.'''
        res = ''
        for msg in jsMessages:
            res += 'var %s = "%s";\n' % (msg, self.translate(msg))
        return res

    def getSearches(self, contentType):
        '''Returns the list of searches that are defined for p_contentType.
           Every list item is a dict that contains info about a search or about
           a group of searches.'''
        appyClass = self.getAppyClass(contentType)
        res = []
        visitedGroups = {} # Names of already visited search groups
        for search in ArchetypesClassDescriptor.getSearches(appyClass):
            # Determine first group label, we will need it.
            groupLabel = ''
            if search.group:
                groupLabel = '%s_searchgroup_%s' % (contentType, search.group)
            # Add an item representing the search group if relevant
            if search.group and (search.group not in visitedGroups):
                group = {'name': search.group, 'isGroup': True,
                         'labelId': groupLabel, 'searches': [],
                         'label': self.translate(groupLabel),
                         'descr': self.translate('%s_descr' % groupLabel),
                }
                res.append(group)
                visitedGroups[search.group] = group
            # Add the search itself
            searchLabel = '%s_search_%s' % (contentType, search.name)
            dSearch = {'name': search.name, 'isGroup': False,
                       'label': self.translate(searchLabel),
                       'descr': self.translate('%s_descr' % searchLabel)}
            if search.group:
                visitedGroups[search.group]['searches'].append(dSearch)
            else:
                res.append(dSearch)
        return res

    def getCookieValue(self, cookieId, default=''):
        '''Server-side code for getting the value of a cookie entry.'''
        cookie = Cookie.SimpleCookie(self.REQUEST['HTTP_COOKIE'])
        cookieValue = cookie.get(cookieId)
        if cookieValue: return cookieValue.value
        return default

    def getQueryUrl(self, contentType, flavourNumber, searchName, ajax=True,
                    startNumber=None):
        '''This method creates the URL that allows to perform an ajax GET
           request for getting queried objects from a search named p_searchName
           on p_contentType from flavour numbered p_flavourNumber. If p_ajax
           is False, it returns the non-ajax URL.'''
        baseUrl = self.getAppFolder().absolute_url() + '/skyn'
        baseParams = 'type_name=%s&flavourNumber=%s'%(contentType,flavourNumber)
        # Manage start number
        rq = self.REQUEST
        if startNumber != None:
            baseParams += '&startNumber=%s' % startNumber
        elif rq.has_key('startNumber'):
            baseParams += '&startNumber=%s' % rq['startNumber']
        # Manage search name
        if searchName or ajax: baseParams += '&search=%s' % searchName
        if ajax:
            return '%s/ajax?objectUid=%s&page=macros&macro=queryResult&%s' % \
                   (baseUrl, self.UID(), baseParams)
        else:
            return '%s/query?%s' % (baseUrl, baseParams)

    def computeStartNumberFrom(self, currentNumber, totalNumber, batchSize):
        '''Returns the number (start at 0) of the first element in a list
           containing p_currentNumber (starts at 0) whose total number is
           p_totalNumber and whose batch size is p_batchSize.'''
        startNumber = 0
        res = startNumber
        while (startNumber < totalNumber):
            if (currentNumber < startNumber + batchSize):
                return startNumber
            else:
                startNumber += batchSize
        return startNumber

    def getNavigationInfo(self):
        '''Extracts navigation information from request/nav and returns a dict
           with the info that a page can use for displaying object
           navigation.'''
        res = {}
        t,d1,d2,currentNumber,totalNumber = self.REQUEST.get('nav').split('.')
        res['currentNumber'] = int(currentNumber)
        res['totalNumber'] = int(totalNumber)
        newNav = '%s.%s.%s.%%d.%s' % (t, d1, d2, totalNumber)
        # Among, first, previous, next and last, which one do I need?
        previousNeeded = False # Previous ?
        previousIndex = res['currentNumber'] - 2
        if (previousIndex > -1) and (res['totalNumber'] > previousIndex):
            previousNeeded = True
        nextNeeded = False     # Next ?
        nextIndex = res['currentNumber']
        if nextIndex < res['totalNumber']: nextNeeded = True
        firstNeeded = False    # First ?
        firstIndex = 0
        if previousIndex > 0: firstNeeded = True
        lastNeeded = False     # Last ?
        lastIndex = res['totalNumber'] - 1
        if (nextIndex < lastIndex): lastNeeded = True
        # Get the list of available UIDs surrounding the current object
        if t == 'ref': # Manage navigation from a reference
            fieldName = d2
            masterObj = self.getObject(d1)
            batchSize = masterObj.getAppyType(fieldName)['maxPerPage']
            uids = getattr(masterObj, '_appy_%s' % fieldName)
            # In the case of a reference, we retrieve ALL surrounding objects.
            
            # Display the reference widget at the page where the current object
            # lies.
            startNumberKey = '%s%s_startNumber' % (masterObj.UID(), fieldName)
            startNumber = self.computeStartNumberFrom(res['currentNumber']-1,
                res['totalNumber'], batchSize)
            res['sourceUrl'] = '%s?%s=%s' % (masterObj.getUrl(),
                startNumberKey, startNumber)
        else:          # Manage navigation from a search
            contentType, flavourNumber = d1.split(':')
            flavourNumber = int(flavourNumber)
            searchName = keySuffix = d2
            batchSize = self.getNumberOfResultsPerPage()
            if not searchName: keySuffix = contentType
            s = self.REQUEST.SESSION
            searchKey = 'search_%s_%s' % (flavourNumber, keySuffix)
            if s.has_key(searchKey): uids = s[searchKey]
            else:                    uids = {}
            # In the case of a search, we retrieve only a part of all
            # surrounding objects, those that are stored in the session.
            if (previousNeeded and not uids.has_key(previousIndex)) or \
               (nextNeeded and not uids.has_key(nextIndex)):
                # I do not have this UID in session. I will need to
                # retrigger the query by querying all objects surrounding
                # this one.
                newStartNumber = (res['currentNumber']-1) - (batchSize / 2)
                if newStartNumber < 0: newStartNumber = 0
                self.executeQuery(contentType, flavourNumber,
                    searchName=searchName, startNumber=newStartNumber,
                    remember=True)
                uids = s[searchKey]
            # For the moment, for first and last, we get them only if we have
            # them in session.
            if not uids.has_key(0): firstNeeded = False
            if not uids.has_key(lastIndex): lastNeeded = False
            # Compute URL of source object
            startNumber = self.computeStartNumberFrom(res['currentNumber']-1,
                res['totalNumber'], batchSize)
            res['sourceUrl'] = self.getQueryUrl(contentType, flavourNumber,
                searchName, ajax=False, startNumber=startNumber)
        # Compute URLs
        for urlType in ('previous', 'next', 'first', 'last'):
            exec 'needIt = %sNeeded' % urlType
            urlKey = '%sUrl' % urlType
            res[urlKey] = None
            if needIt:
                exec 'index = %sIndex' % urlType
                brain = self.uid_catalog(UID=uids[index])
                if brain:
                    baseUrl = brain[0].getObject().getUrl()
                    navUrl = baseUrl + '/?nav=' + newNav % (index + 1)
                    res['%sUrl' % urlType] = navUrl
        return res
# ------------------------------------------------------------------------------
