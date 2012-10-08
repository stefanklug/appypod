# ------------------------------------------------------------------------------
import os, os.path, sys, re, time, random, types, base64, urllib
from appy.shared import mimeTypes
from appy.shared.utils import getOsTempFolder, sequenceTypes
from appy.shared.data import languages
import appy.gen
from appy.gen import Type, Search, Selection, String
from appy.gen.utils import SomeObjects, getClassName
from appy.gen.mixins import BaseMixin
from appy.gen.wrappers import AbstractWrapper
from appy.gen.descriptors import ClassDescriptor
from appy.gen.mail import sendMail
try:
    from AccessControl.ZopeSecurityPolicy import _noroles
except ImportError:
    _noroles = []

# Errors -----------------------------------------------------------------------
jsMessages = ('no_elem_selected', 'delete_confirm', 'unlink_confirm')

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
        if res.find('_wrappers') != -1:
            elems = res.split('_')
            res = '%s%s' % (elems[1], elems[4])
        if res in ('User', 'Group', 'Translation'): res = appName + res
        return res

    def getHomePage(self):
        '''Return the home page when a user hits the app.'''
        # If the app defines a method "getHomePage", call it.
        appyTool = self.appy()
        try:
            url = appyTool.getHomePage()
        except AttributeError:
            # Bring Managers to the config, lead others to home.pt.
            user = self.getUser()
            if user.has_role('Manager'):
                url = self.goto(self.absolute_url())
            else:
                url = self.goto(self.getApp().ui.home.absolute_url())
        return url

    def getCatalog(self):
        '''Returns the catalog object.'''
        return self.getParentNode().catalog

    def getApp(self):
        '''Returns the root Zope object.'''
        return self.getPhysicalRoot()

    def getSiteUrl(self):
        '''Returns the absolute URL of this site.'''
        return self.getApp().absolute_url()

    def getPodInfo(self, obj, name):
        '''Gets the available POD formats for Pod field named p_name on
           p_obj.'''
        podField = self.getAppyType(name, className=obj.meta_type)
        return podField.getToolInfo(obj.appy())

    def generateDocument(self):
        '''Generates the document from field-related info. UID of object that
           is the template target is given in the request.'''
        rq = self.REQUEST
        # Get the object on which a document must be generated.
        obj = self.getObject(rq.get('objectUid'), appy=True)
        fieldName = rq.get('fieldName')
        res = getattr(obj, fieldName)
        if isinstance(res, basestring):
            # An error has occurred, and p_res contains the error message
            obj.say(res)
            return self.goto(rq.get('HTTP_REFERER'))
        # res contains a FileWrapper instance.
        response = rq.RESPONSE
        response.setHeader('Content-Type', res.mimeType)
        response.setHeader('Content-Disposition',
                           'inline;filename="%s"' % res.name)
        return res.content

    def getAttr(self, name):
        '''Gets attribute named p_name.'''
        return getattr(self.appy(), name, None)

    def getAppName(self):
        '''Returns the name of the application.'''
        return self.getProductConfig().PROJECTNAME

    def getPath(self, path):
        '''Returns the folder or object whose absolute path p_path.'''
        res = self.getPhysicalRoot()
        if path == '/': return res
        path = path[1:]
        if '/' not in path: return res._getOb(path) # For performance
        for elem in path.split('/'): res = res._getOb(elem)
        return res

    def showLanguageSelector(self):
        '''We must show the language selector if the app config requires it and
           it there is more than 2 supported languages. Moreover, on some pages,
           switching the language is not allowed.'''
        cfg = self.getProductConfig()
        if not cfg.languageSelector: return
        if len(cfg.languages) < 2: return
        page = self.REQUEST.get('ACTUAL_URL').split('/')[-1]
        return page not in ('edit', 'query', 'search', 'do')

    def showForgotPassword(self):
        '''We must show link "forgot password?" when the app requires it.'''
        return self.getProductConfig().activateForgotPassword

    def getLanguages(self):
        '''Returns the supported languages. First one is the default.'''
        return self.getProductConfig().languages

    def getLanguageName(self, code):
        '''Gets the language name (in this language) from a 2-chars language
           p_code.'''
        return languages.get(code)[2]

    def changeLanguage(self):
        '''Sets the language cookie with the new desired language code that is
           in request["language"].'''
        rq = self.REQUEST
        rq.RESPONSE.setCookie('_ZopeLg', rq['language'], path='/')
        return self.goto(rq['HTTP_REFERER'])

    def flipLanguageDirection(self, align, dir):
        '''According to language direction p_dir ('ltr' or 'rtl'), this method
           turns p_align from 'left' to 'right' (or the inverse) when
           required.'''
        if dir == 'ltr': return align
        if align == 'left': return 'right'
        if align == 'right': return 'left'
        return align

    def getGlobalCssJs(self):
        '''Returns the list of CSS and JS files to include in the main template.
           The method ensures that appy.css and appy.js come first.'''
        names = self.getPhysicalRoot().ui.objectIds('File')
        names.remove('appy.js'); names.insert(0, 'appy.js')
        names.remove('appyrtl.css'); names.insert(0, 'appyrtl.css')
        names.remove('appy.css'); names.insert(0, 'appy.css')
        return names

    def consumeMessages(self):
        '''Returns the list of messages to show to a web page and clean it in
           the session.'''
        rq = self.REQUEST
        res = rq.SESSION.get('messages', '')
        if res:
            del rq.SESSION['messages']
            res = ' '.join([m[1] for m in res])
        return res

    def getRootClasses(self):
        '''Returns the list of root classes for this application.'''
        return self.getProductConfig().rootClasses

    def _appy_getAllFields(self, contentType):
        '''Returns the (translated) names of fields of p_contentType.'''
        res = []
        for appyType in self.getAllAppyTypes(className=contentType):
            res.append((appyType.name, self.translate(appyType.labelId)))
        # Add object state
        res.append(('state', self.translate('workflow_state')))
        return res

    def _appy_getSearchableFields(self, contentType):
        '''Returns the (translated) names of fields that may be searched on
           objects of type p_contentType (=indexed fields).'''
        res = []
        for appyType in self.getAllAppyTypes(className=contentType):
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
            refObject, fieldName = self.getRefInfo(refInfo)
            refField = refObject.getAppyType(fieldName)
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

    queryParamNames = ('className', 'search', 'sortKey', 'sortOrder',
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
        if context.id == 'ui': context = context.getParentNode()
        res = True
        if hasattr(context.aq_base, 'appy'):
            appyObj = context.appy()
            try:
                res = appyObj.showPortlet()
            except AttributeError:
                res = True
        else:
            appyObj = self.appy()
            try:
                res = appyObj.showPortletAt(context)
            except AttributeError:
                res = True
        return res

    def getObject(self, uid, appy=False, brain=False):
        '''Allows to retrieve an object from its p_uid.'''
        res = self.getPhysicalRoot().catalog(UID=uid)
        if not res: return
        res = res[0]
        if brain: return res
        res = res._unrestrictedGetObject()
        if not appy: return res
        return res.appy()

    def getAllowedValue(self):
        '''Gets, for the currently logged user, the value for index
           "Allowed".'''
        user = self.getUser()
        res = ['user:%s' % user.getId(), 'Anonymous'] + user.getRoles()
        try:
            res += ['user:%s' % g for g in user.groups.keys()]
        except AttributeError, ae:
            pass # The Zope admin does not have this attribute.
        return res

    def executeQuery(self, className, searchName=None, startNumber=0,
                     search=None, remember=False, brainsOnly=False,
                     maxResults=None, noSecurity=False, sortBy=None,
                     sortOrder='asc', filterKey=None, filterValue=None,
                     refObject=None, refField=None):
        '''Executes a query on instances of a given p_className (or several,
           separated with commas) in the catalog. If p_searchName is specified,
           it corresponds to:
             1) a search defined on p_className: additional search criteria
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
           the Search instance (Search.sortBy, together with Search.sortOrder).
           But if parameter p_sortBy is given, it defines or overrides the sort.
           In this case, p_sortOrder gives the order (*asc*ending or
           *desc*ending).

           If p_filterKey is given, it represents an additional search parameter
           to take into account: the corresponding search value is in
           p_filterValue.

           If p_refObject and p_refField are given, the query is limited to the
           objects that are referenced from p_refObject through p_refField.'''
        # Is there one or several content types ?
        if className.find(',') != -1:
            classNames = className.split(',')
        else:
            classNames = className
        params = {'ClassName': classNames}
        if not brainsOnly: params['batch'] = True
        # Manage additional criteria from a search when relevant
        if searchName:
            # In this case, className must contain a single content type.
            appyClass = self.getAppyClass(className)
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
                if search.sortOrder == 'desc': params['sort_order'] = 'reverse'
                else:                          params['sort_order'] = None
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
        if refObject:
            refField = refObject.getAppyType(refField)
            params['UID'] = getattr(refObject, refField.name).data
        # Use index "Allowed" if noSecurity is False
        if not noSecurity: params['Allowed'] = self.getAllowedValue()
        brains = self.getPath("/catalog")(**params)
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
                # It is the global search for all objects pf p_className
                searchName = className
            uids = {}
            i = -1
            for obj in res.objects:
                i += 1
                uids[startNumber+i] = obj.UID()
            self.REQUEST.SESSION['search_%s' % searchName] = uids
        return res.__dict__

    def getResultColumnsNames(self, contentType, refInfo):
        contentTypes = contentType.strip(',').split(',')
        resSet = None # Temporary set for computing intersections.
        res = [] # Final, sorted result.
        fieldNames = None
        appyTool = self.appy()
        refField = None
        if refInfo[0]: refField = refInfo[0].getAppyType(refInfo[1])
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
        if isinstance(value, str): value = value.decode('utf-8')
        if len(value) > maxWidth:
            return value[:maxWidth].encode('utf-8') + '...'
        return value.encode('utf-8')

    def truncateText(self, text, width=15):
        '''Truncates p_text to max p_width chars. If the text is longer than
           p_width, the truncated part is put in a "acronym" html tag.'''
        # p_text has to be unicode-encoded for being truncated (else, one char
        # may be spread on 2 chars). But this method must return an encoded
        # string, else, ZPT crashes. The same remark holds for m_truncateValue
        # above.
        uText = text # uText will store the unicode version
        if isinstance(text, str): uText = text.decode('utf-8')
        if len(uText) <= width: return text
        return '<acronym title="%s">%s</acronym>' % \
               (text, uText[:width].encode('utf-8') + '...')

    def getPublishedObject(self):
        '''Gets the currently published object, if its meta_class is among
           application classes.'''
        req = self.REQUEST
        # If we are querying object, there is no published object (the truth is:
        # the tool is the currently published object but we don't want to
        # consider it this way).
        if not req['ACTUAL_URL'].endswith('/ui/view'): return
        obj = self.REQUEST['PUBLISHED']
        parent = obj.getParentNode()
        if parent.id == 'ui': obj = parent.getParentNode()
        if obj.meta_type in self.getProductConfig().attributes: return obj

    def getZopeClass(self, name):
        '''Returns the Zope class whose name is p_name.'''
        exec 'from Products.%s.%s import %s as C'% (self.getAppName(),name,name)
        return C

    def getAppyClass(self, zopeName, wrapper=False):
        '''Gets the Appy class corresponding to the Zope class named p_name.
           If p_wrapper is True, it returns the Appy wrapper. Else, it returns
           the user-defined class.'''
        zopeClass = self.getZopeClass(zopeName)
        if wrapper: return zopeClass.wrapperClass
        else: return zopeClass.wrapperClass.__bases__[-1]

    def getCreateMeans(self, contentTypeOrAppyClass):
        '''Gets the different ways objects of p_contentTypeOrAppyClass (which
           can be a Zope content type or a Appy class) can be created
           (via a web form, by importing external data, etc). Result is a
           dict whose keys are strings (ie "form", "import"...) and whose
           values are additional data about the particular mean.'''
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
        # When editign a form, one should avoid annoying the user with this.
        url = self.REQUEST['ACTUAL_URL']
        if url.endswith('/edit') or url.endswith('/do'): return
        pythonClass = self.getAppyClass(rootClass)
        if 'maySearch' in pythonClass.__dict__:
            return pythonClass.maySearch(self.appy())
        return True

    def onImportObjects(self):
        '''This method is called when the user wants to create objects from
           external data.'''
        rq = self.REQUEST
        appyClass = self.getAppyClass(rq.get('className'))
        importPaths = rq.get('importPath').split('|')
        appFolder = self.getPath('/data')
        for importPath in importPaths:
            if not importPath: continue
            objectId = os.path.basename(importPath)
            self.appy().create(appyClass, id=objectId, _data=importPath)
        self.say(self.translate('import_done'))
        return self.goto(rq['HTTP_REFERER'])

    def isAlreadyImported(self, contentType, importPath):
        data = self.getPath('/data')
        objectId = os.path.basename(importPath)
        if hasattr(data.aq_base, objectId):
            return True
        else:
            return False

    def isSortable(self, name, className, usage):
        '''Is field p_name defined on p_className sortable for p_usage purposes
           (p_usage can be "ref" or "search")?'''
        if (',' in className) or (name == 'state'): return False
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
        # Set the hour
        if setMin: hour = '00:00'
        else: hour = '23:59'
        # We loop until we find a valid date. For example, we could loop from
        # 2009/02/31 to 2009/02/28.
        dateIsWrong = True
        while dateIsWrong:
            try:
                res = DateTime('%s/%s/%s %s' % (year, month, day, hour))
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
        backUrl = '%s/ui/query?className=%s&&search=_advanced' % \
                  (self.absolute_url(), rq['className'])
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
        if not refInfo: return (None, None)
        objectUid, fieldName = refInfo.split(':')
        obj = self.getObject(objectUid)
        return obj, fieldName

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

    def getQueryUrl(self, contentType, searchName, startNumber=None):
        '''This method creates the URL that allows to perform a (non-Ajax)
           request for getting queried objects from a search named p_searchName
           on p_contentType.'''
        baseUrl = self.absolute_url() + '/ui'
        baseParams = 'className=%s' % contentType
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
            sourceObj = self.getObject(d1)
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
            uids = getattr(masterObj, fieldName)
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
                    brain = self.getObject(uid, brain=True)
                    if brain:
                        sibling = brain.getObject()
                        res[urlKey] = sibling.getUrl(nav=newNav % (index + 1),
                                          page=self.REQUEST.get('page', 'main'))
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

    # --------------------------------------------------------------------------
    # Authentication-related methods
    # --------------------------------------------------------------------------
    def _updateCookie(self, login, password):
        cookieValue = base64.encodestring('%s:%s' % (login, password)).rstrip()
        cookieValue = urllib.quote(cookieValue)
        self.REQUEST.RESPONSE.setCookie('__ac', cookieValue, path='/')

    def _encryptPassword(self, password):
        '''Returns the encrypted version of clear p_password.'''
        return self.acl_users._encryptPassword(password)

    def performLogin(self):
        '''Logs the user in.'''
        rq = self.REQUEST
        jsEnabled = rq.get('js_enabled', False) in ('1', 1)
        cookiesEnabled = rq.get('cookies_enabled', False) in ('1', 1)
        urlBack = rq['HTTP_REFERER']

        if jsEnabled and not cookiesEnabled:
            msg = self.translate('enable_cookies')
            return self.goto(urlBack, msg)
        # Perform the Zope-level authentication
        login = rq.get('__ac_name', '')
        self._updateCookie(login, rq.get('__ac_password', ''))
        user = self.acl_users.validate(rq)
        if self.userIsAnon():
            rq.RESPONSE.expireCookie('__ac', path='/')
            msg = self.translate('login_ko')
            logMsg = 'Authentication failed (tried with login "%s").' % login
        else:
            msg = self.translate('login_ok')
            logMsg = 'User "%s" logged in.' % login
        self.log(logMsg)
        return self.goto(self.getApp().absolute_url(), msg)

    def performLogout(self):
        '''Logs out the current user when he clicks on "disconnect".'''
        rq = self.REQUEST
        userId = self.getUser().getId()
        # Perform the logout in acl_users
        rq.RESPONSE.expireCookie('__ac', path='/')
        # Invalidate session.
        try:
            sdm = self.session_data_manager
        except AttributeError, ae:
            # When ran in test mode, session_data_manager is not there.
            sdm = None
        if sdm:
            session = sdm.getSessionData(create=0)
            if session is not None:
                session.invalidate()
        self.log('User "%s" has been logged out.' % userId)
        # Remove user from variable "loggedUsers"
        from appy.gen.installer import loggedUsers
        if loggedUsers.has_key(userId): del loggedUsers[userId]
        return self.goto(self.getApp().absolute_url())

    def validate(self, request, auth='', roles=_noroles):
        '''This method performs authentication and authorization. It is used as
           a replacement for Zope's AccessControl.User.BasicUserFolder.validate,
           that allows to manage cookie-based authentication.'''
        v = request['PUBLISHED'] # The published object
        # v is the object (value) we're validating access to
        # n is the name used to access the object
        # a is the object the object was accessed through
        # c is the physical container of the object
        a, c, n, v = self._getobcontext(v, request)
        # Try to get user name and password from basic authentication
        login, password = self.identify(auth)
        if not login:
            # Try to get them from a cookie
            cookie = request.get('__ac', None)
            login = request.get('__ac_name', None)
            if login and request.form.has_key('__ac_password'):
                # The user just entered his credentials. The cookie has not been
                # set yet (it will come in the upcoming HTTP response when the
                # current request will be served).
                login = request.get('__ac_name', '')
                password = request.get('__ac_password', '')
            elif cookie and (cookie != 'deleted'):
                cookieValue = base64.decodestring(urllib.unquote(cookie))
                if ':' in cookieValue:
                    login, password = cookieValue.split(':')
        # Try to authenticate this user
        user = self.authenticate(login, password, request)
        emergency = self._emergency_user
        if emergency and user is emergency:
            # It is the emergency user.
            return emergency.__of__(self)
        elif user is None:
            # Login and/or password incorrect. Try to authorize and return the
            # anonymous user.
            if self.authorize(self._nobody, a, c, n, v, roles):
                return self._nobody.__of__(self)
            else:
                return # Anonymous can't acces this object
        else:
            # We found a user and his password was correct. Try to authorize him
            # against the published object.
            if self.authorize(user, a, c, n, v, roles):
                return user.__of__(self)
            # That didn't work.  Try to authorize the anonymous user.
            elif self.authorize(self._nobody, a, c, n, v, roles):
                return self._nobody.__of__(self)
            else:
                return

    # Patch BasicUserFolder with our version of m_validate above.
    from AccessControl.User import BasicUserFolder
    BasicUserFolder.validate = validate

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

    def getUserLine(self):
        '''Returns a info about the currently logged user as a 2-tuple: first
           elem is the one-line user info as shown on every page; second line is
           the URL to edit user info.'''
        appyUser = self.appy().appyUser
        info = [appyUser.title]
        rolesToShow = [r for r in appyUser.roles \
                       if r not in ('Authenticated', 'Member')]
        if rolesToShow:
            info.append(', '.join([self.translate('role_%s'%r) \
                                   for r in rolesToShow]))
        # Edit URL for the appy user.
        url = None
        if appyUser.o.mayEdit():
            url = appyUser.o.getUrl(mode='edit', page='main', nav='')
        return (' | '.join(info), url)

    def getUserName(self, login=None):
        '''Gets the user name corresponding to p_login (or the currently logged
           login if None), or the p_login itself if the user does not exist
           anymore.'''
        tool = self.appy()
        if not login: login = tool.user.getId()
        user = tool.search1('User', noSecurity=True, login=login)
        if not user: return login
        firstName = user.firstName
        name = user.name
        res = ''
        if firstName: res += firstName
        if name:
            if res: res += ' ' + name
            else: res = name
        if not res: res = login
        return res

    def formatDate(self, aDate, withHour=True):
        '''Returns aDate formatted as specified by tool.dateFormat.
           If p_withHour is True, hour is appended, with a format specified
           in tool.hourFormat.'''
        tool = self.appy()
        res = aDate.strftime(tool.dateFormat)
        if withHour: res += ' (%s)' % aDate.strftime(tool.hourFormat)
        return res

    def generateUid(self, className):
        '''Generates a UID for an instance of p_className.'''
        name = className.split('_')[-1]
        randomNumber = str(random.random()).split('.')[1]
        timestamp = ('%f' % time.time()).replace('.', '')
        return '%s%s%s' % (name, timestamp, randomNumber)

    def manageError(self, error):
        '''Manages an error.'''
        tb = sys.exc_info()
        from zExceptions.ExceptionFormatter import format_exception
        htmlMessage = format_exception(tb[0], tb[1], tb[2], as_html=1)
        textMessage = format_exception(tb[0], tb[1], tb[2], as_html=0)
        self.log(''.join(textMessage).strip(), type='error')
        return '<table class="main" align="center" cellpadding="0"><tr>' \
               '<td style="padding: 1em 1em 1em 1em">An error occurred. %s' \
               '</td></tr></table>' % '\n'.join(htmlMessage)

    def getMainPages(self):
        '''Returns the main pages.'''
        if hasattr(self.o.aq_base, 'pages') and self.o.pages:
            return [self.getObject(uid) for uid in self.o.pages ]
        return ()

    def askPasswordReinit(self):
        '''A user (anonymmous) does not remember its password. Here we will
           send him a mail containing a link that will trigger password
           re-initialisation.'''
        login = self.REQUEST.get('login').strip()
        appyTool = self.appy()
        user = appyTool.search1('User', login=login, noSecurity=True)
        msg = self.translate('reinit_mail_sent')
        backUrl = self.REQUEST['HTTP_REFERER']
        if not user:
            # Return the message nevertheless. This way, malicious users can't
            # deduce information about existing users.
            return self.goto(backUrl, msg)
        # If login is an email, use it. Else, use user.email instead.
        email = user.login
        if not String.EMAIL.match(email):
            email = user.email
        if not email:
            # Impossible to re-initialise the password.
            return self.goto(backUrl, msg)
        # Create a temporary file whose name is the user login and whose
        # content is a generated token.
        f = file(os.path.join(getOsTempFolder(), login), 'w')
        token = String().generatePassword()
        f.write(token)
        f.close()
        # Send an email
        initUrl = '%s/doPasswordReinit?login=%s&token=%s' % \
                  (self.absolute_url(), login, token)
        subject = self.translate('reinit_password')
        map = {'url':initUrl, 'siteUrl':self.getSiteUrl()}
        body= self.translate('reinit_password_body', mapping=map, format='text')
        sendMail(appyTool, email, subject, body)
        return self.goto(backUrl, msg)

    def doPasswordReinit(self):
        '''Performs the password re-initialisation.'''
        rq = self.REQUEST
        login = rq['login']
        token = rq['token']
        # Check if such token exists in temp folder
        res = None
        siteUrl = self.getSiteUrl()
        tokenFile = os.path.join(getOsTempFolder(), login)
        if os.path.exists(tokenFile):
            f = file(tokenFile)
            storedToken = f.read()
            f.close()
            if storedToken == token:
                # Generate a new password for this user
                appyTool = self.appy()
                user = appyTool.search1('User', login=login, noSecurity=True)
                newPassword = user.setPassword()
                # Send the new password by email
                email = login
                if not String.EMAIL.match(email):
                    email = user.email
                subject = self.translate('new_password')
                map = {'password': newPassword, 'siteUrl': siteUrl}
                body = self.translate('new_password_body', mapping=map,
                                      format='text')
                sendMail(appyTool, email, subject, body)
                os.remove(tokenFile)
                res = self.goto(siteUrl, self.translate('new_password_sent'))
        if not res:
            res = self.goto(siteUrl, self.translate('wrong_password_reinit'))
        return res

    def getSearchValues(self, name, className):
        '''Gets the possible values for selecting a value for searching field
           p_name belonging to class p_className.'''
        klass = self.getAppyClass(className, wrapper=True)
        method = getattr(klass, name).searchSelect
        tool = self.appy()
        objects = method.__get__(tool)(tool)
        return [(o.uid, o) for o in objects]
# ------------------------------------------------------------------------------
