# ------------------------------------------------------------------------------
import re, os, os.path, time, Cookie, StringIO, types
from appy.shared import mimeTypes
from appy.shared.utils import getOsTempFolder
import appy.pod
from appy.pod.renderer import Renderer
import appy.gen
from appy.gen import Type, Search, Selection
from appy.gen.utils import SomeObjects, sequenceTypes, getClassName
from appy.gen.plone25.mixins import BaseMixin
from appy.gen.plone25.wrappers import AbstractWrapper
from appy.gen.plone25.descriptors import ClassDescriptor

# Errors -----------------------------------------------------------------------
DELETE_TEMP_DOC_ERROR = 'A temporary document could not be removed. %s.'
POD_ERROR = 'An error occurred while generating the document. Please ' \
            'contact the system administrator.'
jsMessages = ('no_elem_selected', 'delete_confirm')

# ------------------------------------------------------------------------------
class ToolMixin(BaseMixin):
    _appy_meta_type = 'Tool'
    def getPortalType(self, metaTypeOrAppyClass):
        '''Returns the name of the portal_type that is based on
           p_metaTypeOrAppyType.'''
        appName = self.getProductConfig().PROJECTNAME
        res = metaTypeOrAppyClass
        if not isinstance(metaTypeOrAppyClass, basestring):
            res = getClassName(metaTypeOrAppyClass, appName)
        if res.find('Extensions_appyWrappers') != -1:
            elems = res.split('_')
            res = '%s%s' % (elems[1], elems[4])
        return res

    def getPodInfo(self, ploneObj, fieldName):
        '''Returns POD-related information about Pod field p_fieldName defined
           on class whose p_ploneObj is an instance of.'''
        res = {}
        appyClass = self.getAppyClass(ploneObj.meta_type)
        appyTool = self.appy()
        n = appyTool.getAttributeName('formats', appyClass, fieldName)
        res['formats'] = getattr(appyTool, n)
        n = appyTool.getAttributeName('podTemplate', appyClass, fieldName)
        res['template'] = getattr(appyTool, n)
        appyType = ploneObj.getAppyType(fieldName)
        res['title'] = self.translate(appyType.labelId)
        res['context'] = appyType.context
        res['action'] = appyType.action
        res['stylesMapping'] = appyType.stylesMapping
        return res

    def getSiteUrl(self):
        '''Returns the absolute URL of this site.'''
        return self.portal_url.getPortalObject().absolute_url()

    def generateDocument(self):
        '''Generates the document from field-related info. UID of object that
           is the template target is given in the request.'''
        rq = self.REQUEST
        appyTool = self.appy()
        # Get the object
        objectUid = rq.get('objectUid')
        obj = self.uid_catalog(UID=objectUid)[0].getObject()
        appyObj = obj.appy()
        # Get information about the document to render.
        specificPodContext = None
        fieldName = rq.get('fieldName')
        format = rq.get('podFormat')
        podInfo = self.getPodInfo(obj, fieldName)
        template = podInfo['template'].content
        podTitle = podInfo['title']
        if podInfo['context']:
            if callable(podInfo['context']):
                specificPodContext = podInfo['context'](appyObj)
            else:
                specificPodContext = podInfo['context']
        doAction = rq.get('askAction') == 'True'
        # Temporary file where to generate the result
        tempFileName = '%s/%s_%f.%s' % (
            getOsTempFolder(), obj.UID(), time.time(), format)
        # Define parameters to give to the appy.pod renderer
        currentUser = self.portal_membership.getAuthenticatedMember()
        podContext = {'tool': appyTool, 'user': currentUser, 'self': appyObj,
                      'now': self.getProductConfig().DateTime(),
                      'projectFolder': appyTool.getDiskFolder(),
                      }
        # If the POD document is related to a query, get it from the request,
        # execute it and put the result in the context.
        if rq['queryData']:
            # Retrieve query params from the request
            cmd = ', '.join(self.queryParamNames)
            cmd += " = rq['queryData'].split(';')"
            exec cmd
            # (re-)execute the query, but without any limit on the number of
            # results; return Appy objects.
            objs = self.executeQuery(type_name, searchName=search,
                     sortBy=sortKey, sortOrder=sortOrder, filterKey=filterKey,
                     filterValue=filterValue, maxResults='NO_LIMIT')
            podContext['objects'] = [o.appy() for o in objs['objects']]
        if specificPodContext:
            podContext.update(specificPodContext)
        # Define a potential global styles mapping
        stylesMapping = None
        if podInfo['stylesMapping']:
            if callable(podInfo['stylesMapping']):
                stylesMapping = podInfo['stylesMapping'](appyObj)
            else:
                stylesMapping = podInfo['stylesMapping']
        rendererParams = {'template': StringIO.StringIO(template),
                          'context': podContext, 'result': tempFileName}
        if stylesMapping:
            rendererParams['stylesMapping'] = stylesMapping
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
        if rq['queryData']:
            # This is a POD for a bunch of objects
            fileName = podTitle
        else:
            # This is a POD for a single object: personalize the file name with
            # the object title.
            fileName = '%s-%s' % (obj.Title(), podTitle)
        fileName = appyTool.normalize(fileName)
        response = obj.REQUEST.RESPONSE
        response.setHeader('Content-Type', mimeTypes[format])
        response.setHeader('Content-Disposition', 'inline;filename="%s.%s"' % \
                           (fileName, format))
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
        '''Gets attribute named p_attrName. Useful because we can't use getattr
           directly in Zope Page Templates.'''
        return getattr(self.appy(), name, None)

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

    def getSearchInfo(self, contentType, refInfo=None):
        '''Returns, as a dict:
           - the list of searchable fields (= some fields among all indexed
             fields);
           - the number of columns for layouting those fields.'''
        fields = []
        fieldDicts = []
        if refInfo:
            # The search is triggered from a Ref field.
            refField = self.getRefInfo(refInfo)[1]
            fieldNames = refField.queryFields or ()
            nbOfColumns = refField.queryNbCols
        else:
            # The search is triggered from an app-wide search.
            at = self.appy()
            fieldNames = getattr(at, 'searchFieldsFor%s' % contentType,())
            nbOfColumns = getattr(at, 'numberOfSearchColumnsFor%s' %contentType)
        for name in fieldNames:
            appyType = self.getAppyType(name,asDict=False,className=contentType)
            appyDict = self.getAppyType(name, asDict=True,className=contentType)
            fields.append(appyType)
            fieldDicts.append(appyDict)
        return {'fields': fields, 'nbOfColumns': nbOfColumns,
                'fieldDicts': fieldDicts}

    queryParamNames = ('type_name', 'search', 'sortKey', 'sortOrder',
                       'filterKey', 'filterValue')
    def getQueryInfo(self):
        '''If we are showing search results, this method encodes in a string all
           the params in the request that are required for re-triggering the
           search.'''
        rq = self.REQUEST
        res = ''
        if rq.has_key('search'):
            res = ';'.join([rq.get(key,'').replace(';','') \
                            for key in self.queryParamNames])
        return res

    def getImportElements(self, contentType):
        '''Returns the list of elements that can be imported from p_path for
           p_contentType.'''
        appyClass = self.getAppyClass(contentType)
        importParams = self.getCreateMeans(appyClass)['import']
        onElement = importParams['onElement'].__get__('')
        sortMethod = importParams['sort']
        if sortMethod: sortMethod = sortMethod.__get__('')
        elems = []
        importType = self.getAppyType('importPathFor%s' % contentType)
        importPath = importType.getValue(self)
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

    def showPortlet(self, context):
        if self.portal_membership.isAnonymousUser(): return False
        if context.id == 'skyn': context = context.getParentNode()
        res = True
        if not self.getRootClasses():
            res = False
            # If there is no root class, show the portlet only if we are within
            # the configuration.
            if (self.id in context.absolute_url()): res = True
        return res

    def getObject(self, uid, appy=False):
        '''Allows to retrieve an object from its p_uid.'''
        res = self.uid_catalog(UID=uid)
        if res:
            res = res[0].getObject()
            if appy:
                res = res.appy()
        return res

    def executeQuery(self, contentType, searchName=None, startNumber=0,
                     search=None, remember=False, brainsOnly=False,
                     maxResults=None, noSecurity=False, sortBy=None,
                     sortOrder='asc', filterKey=None, filterValue=None,
                     refField=None):
        '''Executes a query on a given p_contentType (or several, separated
           with commas) in Plone's portal_catalog. If p_searchName is specified,
           it corresponds to:
             1) a search defined on p_contentType: additional search criteria
                will be added to the query, or;
             2) "_advanced": in this case, additional search criteria will also
                be added to the query, but those criteria come from the session
                (in key "searchCriteria") and were created from search.pt.

           We will retrieve objects from p_startNumber. If p_search is defined,
           it corresponds to a custom Search instance (instead of a predefined
           named search like in p_searchName). If both p_searchName and p_search
           are given, p_search is ignored.

           This method returns a list of objects in the form of the
           __dict__ attribute of an instance of SomeObjects (see in
           appy.gen.utils). We return the __dict__ attribute instead of real
           instance: that way, it can be used in ZPTs without security problems.
           If p_brainsOnly is True, it returns a list of brains instead (can be
           useful for some usages like knowing the number of objects without
           needing to get information about them). If no p_maxResults is
           specified, the method returns maximum
           self.numberOfResultsPerPage. The method returns all objects if
           p_maxResults equals string "NO_LIMIT".

           If p_noSecurity is True, it gets all the objects, even those that the
           currently logged user can't see.

           The result is sorted according to the potential sort key defined in
           the Search instance (Search.sortBy). But if parameter p_sortBy is
           given, it defines or overrides the sort. In this case, p_sortOrder
           gives the order (*asc*ending or *desc*ending).

           If p_filterKey is given, it represents an additional search parameter
           to take into account: the corresponding search value is in
           p_filterValue.

           If p_refField is given, the query is limited to the objects that are
           referenced through it.'''
        # Is there one or several content types ?
        if contentType.find(',') != -1:
            portalTypes = contentType.split(',')
        else:
            portalTypes = contentType
        params = {'portal_type': portalTypes}
        if not brainsOnly: params['batch'] = True
        # Manage additional criteria from a search when relevant
        if searchName:
            # In this case, contentType must contain a single content type.
            appyClass = self.getAppyClass(contentType)
            if searchName != '_advanced':
                search = ClassDescriptor.getSearch(appyClass, searchName)
            else:
                fields = self.REQUEST.SESSION['searchCriteria']
                search = Search('customSearch', **fields)
        if search:
            # Add additional search criteria
            for fieldName, fieldValue in search.fields.iteritems():
                # Management of searches restricted to objects linked through a
                # Ref field: not implemented yet.
                if fieldName == '_ref': continue
                # Make the correspondance between the name of the field and the
                # name of the corresponding index.
                attrName = Search.getIndexName(fieldName)
                # Express the field value in the way needed by the index
                params[attrName] = Search.getSearchValue(fieldName, fieldValue)
            # Add a sort order if specified
            sortKey = search.sortBy
            if sortKey:
                params['sort_on'] = Search.getIndexName(sortKey, usage='sort')
        # Determine or override sort if specified.
        if sortBy:
            params['sort_on'] = Search.getIndexName(sortBy, usage='sort')
            if sortOrder == 'desc': params['sort_order'] = 'reverse'
            else:                   params['sort_order'] = None
        # If defined, add the filter among search parameters.
        if filterKey:
            filterKey = Search.getIndexName(filterKey)
            filterValue = Search.getSearchValue(filterKey, filterValue)
            params[filterKey] = filterValue
            # TODO This value needs to be merged with an existing one if already
            # in params, or, in a first step, we should avoid to display the
            # corresponding filter widget on the screen.
        # Determine what method to call on the portal catalog
        if noSecurity: catalogMethod = 'unrestrictedSearchResults'
        else:          catalogMethod = 'searchResults'
        exec 'brains = self.portal_catalog.%s(**params)' % catalogMethod
        if brainsOnly:
            # Return brains only.
            if not maxResults: return brains
            else: return brains[:maxResults]
        if not maxResults:
            if refField: maxResults = refField.maxPerPage
            else:        maxResults = self.appy().numberOfResultsPerPage
        elif maxResults == 'NO_LIMIT': maxResults = None
        res = SomeObjects(brains, maxResults, startNumber,noSecurity=noSecurity)
        res.brainsToObjects()
        # In some cases (p_remember=True), we need to keep some information
        # about the query results in the current user's session, allowing him
        # to navigate within elements without re-triggering the query every
        # time a page for an element is consulted.
        if remember:
            if not searchName:
                # It is the global search for all objects pf p_contentType
                searchName = contentType
            uids = {}
            i = -1
            for obj in res.objects:
                i += 1
                uids[startNumber+i] = obj.UID()
            self.REQUEST.SESSION['search_%s' % searchName] = uids
        return res.__dict__

    def getResultColumnsNames(self, contentType, refField):
        contentTypes = contentType.strip(',').split(',')
        resSet = None # Temporary set for computing intersections.
        res = [] # Final, sorted result.
        fieldNames = None
        appyTool = self.appy()
        for cType in contentTypes:
            if refField:
                fieldNames = refField.shownInfo
            else:
                fieldNames = getattr(appyTool, 'resultColumnsFor%s' % cType)
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

    def truncateValue(self, value, appyType):
        '''Truncates the p_value according to p_appyType width.'''
        maxWidth = appyType['width']
        if len(value) > maxWidth:
            return value[:maxWidth] + '...'
        return value

    def truncateText(self, text, width=15):
        '''Truncates p_text to max p_width chars. If the text is longer than
           p_width, the truncated part is put in a "acronym" html tag.'''
        if len(text) <= width: return text
        else:
            return '<acronym title="%s">%s</acronym>' % \
                   (text, text[:width] + '...')

    translationMapping = {'portal_path': ''}
    def translateWithMapping(self, label):
        '''Translates p_label in the application domain, with a default
           translation mapping.'''
        if not self.translationMapping['portal_path']:
            self.translationMapping['portal_path'] = \
                self.portal_url.getPortalPath()
        return self.translate(label, mapping=self.translationMapping)

    def getPublishedObject(self):
        '''Gets the currently published object, if its meta_class is among
           application classes.'''
        rq = self.REQUEST
        obj = rq['PUBLISHED']
        parent = obj.getParentNode()
        if parent.id == 'skyn':
            obj = parent.getParentNode()
        if obj.meta_type in self.getProductConfig().attributes:
            return obj
        return None

    def getAppyClass(self, contentType):
        '''Gets the Appy Python class that is related to p_contentType.'''
        # Retrieve first the Archetypes class corresponding to p_ContentType
        portalType = self.portal_types.get(contentType)
        if not portalType: return None
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

    def userMaySearch(self, rootClass):
        '''This method checks if the currently logged user can trigger searches
           on a given p_rootClass. This is done by calling method "maySearch"
           on the class. If no such method exists, we return True.'''
        pythonClass = self.getAppyClass(rootClass)
        if 'maySearch' in pythonClass.__dict__:
            return pythonClass.maySearch(self.appy())
        return True

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
        self.say(self.translate('import_done'))
        return self.goto(rq['HTTP_REFERER'])

    def isAlreadyImported(self, contentType, importPath):
        appFolder = self.getAppFolder()
        objectId = os.path.basename(importPath)
        if hasattr(appFolder.aq_base, objectId):
            return True
        else:
            return False

    def isSortable(self, name, className, usage):
        '''Is field p_name defined on p_className sortable for p_usage purposes
           (p_usage can be "ref" or "search")?'''
        if (',' in className) or (name == 'workflowState'): return False
        appyType = self.getAppyType(name, className=className)
        if appyType: return appyType.isSortable(usage=usage)

    def _searchValueIsEmpty(self, key):
        '''Returns True if request value in key p_key can be considered as
           empty.'''
        rq = self.REQUEST.form
        if key.endswith('*int') or key.endswith('*float'):
            # We return True if "from" AND "to" values are empty.
            toKey = '%s_to' % key[2:key.find('*')]
            return not rq[key].strip() and not rq[toKey].strip()
        elif key.endswith('*date'):
            # We return True if "from" AND "to" values are empty. A value is
            # considered as not empty if at least the year is specified.
            toKey = '%s_to_year' % key[2:-5]
            return not rq[key] and not rq[toKey]
        else:
            return not rq[key]

    def _getDateTime(self, year, month, day, setMin):
        '''Gets a valid DateTime instance from date information coming from the
           request as strings in p_year, p_month and p_day. Returns None if
           p_year is empty. If p_setMin is True, when some
           information is missing (month or day), we will replace it with the
           minimum value (=1). Else, we will replace it with the maximum value
           (=12, =31).'''
        if not year: return None
        if not month:
            if setMin: month = 1
            else:      month = 12
        if not day:
            if setMin: day = 1
            else:      day = 31
        DateTime = self.getProductConfig().DateTime
        # We loop until we find a valid date. For example, we could loop from
        # 2009/02/31 to 2009/02/28.
        dateIsWrong = True
        while dateIsWrong:
            try:
                res = DateTime('%s/%s/%s' % (year, month, day))
                dateIsWrong = False
            except:
                day = int(day)-1
        return res

    transformMethods = {'uppercase': 'upper', 'lowercase': 'lower',
                        'capitalize': 'capitalize'}
    def onSearchObjects(self):
        '''This method is called when the user triggers a search from
           search.pt.'''
        rq = self.REQUEST
        # Store the search criteria in the session
        criteria = {}
        for attrName in rq.form.keys():
            if attrName.startswith('w_') and \
               not self._searchValueIsEmpty(attrName):
                # We have a(n interval of) value(s) that is not empty for a
                # given field.
                attrValue = rq.form[attrName]
                if attrName.find('*') != -1:
                    attrValue = attrValue.strip()
                    # The type of the value is encoded after char "*".
                    attrName, attrType = attrName.split('*')
                    if attrType == 'bool':
                        exec 'attrValue = %s' % attrValue
                    elif attrType in ('int', 'float'):
                        # Get the "from" value
                        if not attrValue: attrValue = None
                        else:
                            exec 'attrValue = %s(attrValue)' % attrType
                        # Get the "to" value
                        toValue = rq.form['%s_to' % attrName[2:]].strip()
                        if not toValue: toValue = None
                        else:
                            exec 'toValue = %s(toValue)' % attrType
                        attrValue = (attrValue, toValue)
                    elif attrType == 'date':
                        prefix = attrName[2:]
                        # Get the "from" value
                        year  = attrValue
                        month = rq.form['%s_from_month' % prefix]
                        day   = rq.form['%s_from_day' % prefix]
                        fromDate = self._getDateTime(year, month, day, True)
                        # Get the "to" value"
                        year  = rq.form['%s_to_year' % prefix]
                        month = rq.form['%s_to_month' % prefix]
                        day   = rq.form['%s_to_day' % prefix]
                        toDate = self._getDateTime(year, month, day, False)
                        attrValue = (fromDate, toDate)
                    elif attrType.startswith('string'):
                        # In the case of a string, it could be necessary to
                        # apply some text transform.
                        if len(attrType) > 6:
                            transform = attrType.split('-')[1]
                            if (transform != 'none') and attrValue:
                                exec 'attrValue = attrValue.%s()' % \
                                     self.transformMethods[transform]
                if isinstance(attrValue, list):
                    # It is a list of values. Check if we have an operator for
                    # the field, to see if we make an "and" or "or" for all
                    # those values. "or" will be the default.
                    operKey = 'o_%s' % attrName[2:]
                    oper = ' %s ' % rq.form.get(operKey, 'or').upper()
                    attrValue = oper.join(attrValue)
                criteria[attrName[2:]] = attrValue
        # Complete criteria with Ref info if the search is restricted to
        # referenced objects of a Ref field.
        refInfo = rq.get('ref', None)
        if refInfo: criteria['_ref'] = refInfo
        rq.SESSION['searchCriteria'] = criteria
        # Go to the screen that displays search results
        backUrl = '%s/query?type_name=%s&&search=_advanced' % \
                  (os.path.dirname(rq['URL']),rq['type_name'])
        return self.goto(backUrl)

    def getJavascriptMessages(self):
        '''Returns the translated version of messages that must be shown in
           Javascript popups.'''
        res = ''
        for msg in jsMessages:
            res += 'var %s = "%s";\n' % (msg, self.translate(msg))
        return res

    def getRefInfo(self, refInfo=None):
        '''When a search is restricted to objects referenced through a Ref
           field, this method returns information about this reference: the
           source content type and the Ref field (Appy type). If p_refInfo is
           not given, we search it among search criteria in the session.'''
        if not refInfo and (self.REQUEST.get('search', None) == '_advanced'):
            criteria = self.REQUEST.SESSION.get('searchCriteria', None)
            if criteria and criteria.has_key('_ref'): refInfo = criteria['_ref']
        if not refInfo: return ('', None)
        sourceContentType, refField = refInfo.split(':')
        return refInfo, self.getAppyType(refField, className=sourceContentType)

    def getSearches(self, contentType):
        '''Returns the list of searches that are defined for p_contentType.
           Every list item is a dict that contains info about a search or about
           a group of searches.'''
        appyClass = self.getAppyClass(contentType)
        res = []
        visitedGroups = {} # Names of already visited search groups
        for search in ClassDescriptor.getSearches(appyClass):
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

    def getQueryUrl(self, contentType, searchName, startNumber=None):
        '''This method creates the URL that allows to perform a (non-Ajax)
           request for getting queried objects from a search named p_searchName
           on p_contentType.'''
        baseUrl = self.getAppFolder().absolute_url() + '/skyn'
        baseParams = 'type_name=%s' % contentType
        rq = self.REQUEST
        if rq.get('ref'): baseParams += '&ref=%s' % rq.get('ref')
        # Manage start number
        if startNumber != None:
            baseParams += '&startNumber=%s' % startNumber
        elif rq.has_key('startNumber'):
            baseParams += '&startNumber=%s' % rq['startNumber']
        # Manage search name
        if searchName: baseParams += '&search=%s' % searchName
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
        # Compute the label of the search, or ref field
        if t == 'search':
            searchName = d2
            if not searchName:
                # We search all objects of a given type.
                label = '%s_plural' % d1.split(':')[0]
            elif searchName == '_advanced':
                # This is an advanced, custom search.
                label = 'search_results'
            else:
                # This is a named, predefined search.
                label = '%s_search_%s' % (d1.split(':')[0], searchName)
            res['backText'] = self.translate(label)
        else:
            fieldName, pageName = d2.split(':')
            sourceObj = self.uid_catalog(UID=d1)[0].getObject()
            label = '%s_%s' % (sourceObj.meta_type, fieldName)
            res['backText'] = '%s : %s' % (sourceObj.Title(),
                                           self.translate(label))
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
            # In the case of a reference, we retrieve ALL surrounding objects.
            masterObj = self.getObject(d1)
            batchSize = masterObj.getAppyType(fieldName).maxPerPage
            uids = getattr(masterObj, '_appy_%s' % fieldName)
            # Display the reference widget at the page where the current object
            # lies.
            startNumberKey = '%s%s_startNumber' % (masterObj.UID(), fieldName)
            startNumber = self.computeStartNumberFrom(res['currentNumber']-1,
                res['totalNumber'], batchSize)
            res['sourceUrl'] = masterObj.getUrl(**{startNumberKey:startNumber,
                                                   'page':pageName, 'nav':''})
        else: # Manage navigation from a search
            contentType = d1
            searchName = keySuffix = d2
            batchSize = self.appy().numberOfResultsPerPage
            if not searchName: keySuffix = contentType
            s = self.REQUEST.SESSION
            searchKey = 'search_%s' % keySuffix
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
                self.executeQuery(contentType, searchName=searchName,
                                  startNumber=newStartNumber, remember=True)
                uids = s[searchKey]
            # For the moment, for first and last, we get them only if we have
            # them in session.
            if not uids.has_key(0): firstNeeded = False
            if not uids.has_key(lastIndex): lastNeeded = False
            # Compute URL of source object
            startNumber = self.computeStartNumberFrom(res['currentNumber']-1,
                                                  res['totalNumber'], batchSize)
            res['sourceUrl'] = self.getQueryUrl(contentType, searchName,
                                                startNumber=startNumber)
        # Compute URLs
        for urlType in ('previous', 'next', 'first', 'last'):
            exec 'needIt = %sNeeded' % urlType
            urlKey = '%sUrl' % urlType
            res[urlKey] = None
            if needIt:
                exec 'index = %sIndex' % urlType
                uid = None
                try:
                    uid = uids[index]
                    # uids can be a list (ref) or a dict (search)
                except KeyError: pass
                except IndexError: pass
                if uid:
                    brain = self.uid_catalog(UID=uid)
                    if brain:
                        sibling = brain[0].getObject()
                        res[urlKey] = sibling.getUrl(nav=newNav % (index + 1),
                                                     page='main')
        return res

    def tabularize(self, data, numberOfRows):
        '''This method transforms p_data, which must be a "flat" list or tuple,
           into a list of lists, where every sub-list has length p_numberOfRows.
           This method is typically used for rendering elements in a table of
           p_numberOfRows rows.'''
        res = []
        row = []
        for elem in data:
            row.append(elem)
            if len(row) == numberOfRows:
                res.append(row)
                row = []
        # Complete the last unfinished line if required.
        if row:
            while len(row) < numberOfRows: row.append(None)
            res.append(row)
        return res

    def truncate(self, value, numberOfChars):
        '''Truncates string p_value to p_numberOfChars.'''
        if len(value) > numberOfChars: return value[:numberOfChars] + '...'
        return value

    monthsIds = {
        1:  'month_jan', 2:  'month_feb', 3:  'month_mar', 4:  'month_apr',
        5:  'month_may', 6:  'month_jun', 7:  'month_jul', 8:  'month_aug',
        9:  'month_sep', 10: 'month_oct', 11: 'month_nov', 12: 'month_dec'}
    def getMonthName(self, monthNumber):
        '''Gets the translated month name of month numbered p_monthNumber.'''
        return self.translate(self.monthsIds[int(monthNumber)], domain='plone')

    def logout(self):
        '''Logs out the current user when he clicks on "disconnect".'''
        rq = self.REQUEST
        userId = self.portal_membership.getAuthenticatedMember().getId()
        # Perform the logout in acl_users
        try:
            self.acl_users.logout(rq)
        except:
            pass
        skinvar = self.portal_skins.getRequestVarname()
        path = '/' + self.absolute_url(1)
        if rq.has_key(skinvar) and not self.portal_skins.getCookiePersistence():
            rq.RESPONSE.expireCookie(skinvar, path=path)
        # Invalidate existing sessions, but only if they exist.
        sdm = self.session_data_manager
        session = sdm.getSessionData(create=0)
        if session is not None:
            session.invalidate()
        from Products.CMFPlone import transaction_note
        transaction_note('Logged out')
        self.getProductConfig().logger.info('User "%s" has been logged out.' % \
                                            userId)
        # Remove user from variable "loggedUsers"
        from appy.gen.plone25.installer import loggedUsers
        if loggedUsers.has_key(userId): del loggedUsers[userId]
        return self.goto(self.getParentNode().absolute_url())

    def tempFile(self):
        '''A temp file has been created in a temp folder. This method returns
           this file to the browser.'''
        rq = self.REQUEST
        baseFolder = os.path.join(getOsTempFolder(), self.getAppName())
        baseFolder = os.path.join(baseFolder, rq.SESSION.id)
        fileName   = os.path.join(baseFolder, rq.get('name', ''))
        if os.path.exists(fileName):
            f = file(fileName)
            content = f.read()
            f.close()
            # Remove the temp file
            os.remove(fileName)
            return content
        return 'File does not exist'

    def getResultPodFields(self, contentType):
        '''Finds, among fields defined on p_contentType, which ones are Pod
           fields that need to be shown on a page displaying query results.'''
        # Skip this if we are searching multiple content types.
        if ',' in contentType: return ()
        return [f.__dict__ for f in self.getAllAppyTypes(contentType) \
                if (f.type == 'Pod') and (f.show == 'result')]
# ------------------------------------------------------------------------------
