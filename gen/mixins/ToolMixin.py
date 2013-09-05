# ------------------------------------------------------------------------------
import os, os.path, sys, re, time, random, types
from appy import Object
import appy.gen
from appy.gen import Search, UiSearch, String, Page, ldap
from appy.gen.layout import ColumnLayout
from appy.gen import utils as gutils
from appy.gen.mixins import BaseMixin
from appy.gen.wrappers import AbstractWrapper
from appy.gen.descriptors import ClassDescriptor
from appy.gen.mail import sendMail
from appy.shared import mimeTypes
from appy.shared import utils as sutils
from appy.shared.data import languages
try:
    from AccessControl.ZopeSecurityPolicy import _noroles
except ImportError:
    _noroles = []

# Errors -----------------------------------------------------------------------
jsMessages = ('no_elem_selected', 'delete_confirm', 'unlink_confirm',
              'unlock_confirm', 'warn_leave_form')

# ------------------------------------------------------------------------------
class ToolMixin(BaseMixin):
    _appy_meta_type = 'Tool'
    xhtmlEncoding = 'text/html;charset=UTF-8'

    def getPortalType(self, metaTypeOrAppyClass):
        '''Returns the name of the portal_type that is based on
           p_metaTypeOrAppyType.'''
        appName = self.getProductConfig().PROJECTNAME
        res = metaTypeOrAppyClass
        if not isinstance(metaTypeOrAppyClass, basestring):
            res = gutils.getClassName(metaTypeOrAppyClass, appName)
        if res.find('_wrappers') != -1:
            elems = res.split('_')
            res = '%s%s' % (elems[1], elems[4])
        if res in ('User', 'Group', 'Translation'): res = appName + res
        return res

    def home(self):
        '''Returns the content of px ToolWrapper.pxHome.'''
        tool = self.appy()
        return tool.pxHome({'obj': None, 'tool': tool})

    def query(self):
        '''Returns the content of px ToolWrapper.pxQuery.'''
        tool = self.appy()
        return tool.pxQuery({'obj': None, 'tool': tool})

    def search(self):
        '''Returns the content of px ToolWrapper.pxSearch.'''
        tool = self.appy()
        return tool.pxSearch({'obj': None, 'tool': tool})

    def getHomePage(self):
        '''Return the home page when a user hits the app.'''
        # If the app defines a method "getHomePage", call it.
        tool = self.appy()
        try:
            url = tool.getHomePage()
        except AttributeError:
            # Bring Managers to the config, lead others to pxHome.
            user = self.getUser()
            if user.has_role('Manager'):
                url = self.goto(self.absolute_url())
            else:
                url = self.goto('%s/home' % self.absolute_url())
        return url

    def getHomeObject(self):
        '''The concept of "home object" is the object where the user must "be",
           even if he is "nowhere". For example, if the user is on a search
           screen, there is no contextual object. In this case, if we have a
           home object for him, we will use it as contextual object, and its
           portlet menu will nevertheless appear: the user will not have the
           feeling of being lost.'''
        # If the app defines a method "getHomeObject", call it.
        try:
            return self.appy().getHomeObject()
        except AttributeError:
            # For managers, the home object is the config. For others, there is
            # no default home object.
            if self.getUser().has_role('Manager'): return self.appy()

    def getCatalog(self):
        '''Returns the catalog object.'''
        return self.getParentNode().catalog

    def getApp(self):
        '''Returns the root Zope object.'''
        return self.getPhysicalRoot()

    def getSiteUrl(self):
        '''Returns the absolute URL of this site.'''
        return self.getApp().absolute_url()

    def getIncludeUrl(self, name, bg=False):
        '''Gets the full URL of an external resource, like an image, a
           Javascript or a CSS file, named p_name. If p_bg is True, p_name is
           an image that is meant to be used in a "style" attribute for defining
           the background image of some XHTML tag.'''
        # If no extension is found in p_name, we suppose it is a png image.
        if '.' not in name: name += '.png'
        url = '%s/ui/%s' % (self.getPhysicalRoot().absolute_url(), name)
        if not bg: return url
        return 'background-image: url(%s)' % url

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
        cfg = self.getProductConfig(True)
        if not cfg.languageSelector: return
        if len(cfg.languages) < 2: return
        page = self.REQUEST.get('ACTUAL_URL').split('/')[-1]
        return page not in ('edit', 'query', 'search', 'do')

    def showForgotPassword(self):
        '''We must show link "forgot password?" when the app requires it.'''
        return self.getProductConfig(True).activateForgotPassword

    def getLanguages(self):
        '''Returns the supported languages. First one is the default.'''
        return self.getProductConfig(True).languages

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
        cfg = self.getProductConfig()
        return [self.getAppyClass(k) for k in cfg.rootClasses]

    def _appy_getAllFields(self, className):
        '''Returns the (translated) names of fields of p_className.'''
        res = []
        for field in self.getAllAppyTypes(className=className):
            res.append((className.name, self.translate(className.labelId)))
        # Add object state
        res.append(('state', self.translate('workflow_state')))
        return res

    def _appy_getSearchableFields(self, className):
        '''Returns the (translated) names of fields that may be searched on
           objects of type p_className (=indexed fields).'''
        res = []
        for field in self.getAllAppyTypes(className=className):
            if field.indexed:
                res.append((field.name, self.translate(field.labelId)))
        return res

    def getSearchInfo(self, className, refInfo=None):
        '''Returns, as an object:
           - the list of searchable fields (some among all indexed fields);
           - the number of columns for layouting those fields.'''
        fields = []
        if refInfo:
            # The search is triggered from a Ref field.
            refObject, fieldName = self.getRefInfo(refInfo)
            refField = refObject.getAppyType(fieldName)
            fieldNames = refField.queryFields or ()
            nbOfColumns = refField.queryNbCols
        else:
            # The search is triggered from an app-wide search.
            tool = self.appy()
            fieldNames = getattr(tool, 'searchFieldsFor%s' % className,())
            nbOfColumns = getattr(tool, 'numberOfSearchColumnsFor%s' %className)
        for name in fieldNames:
            field = self.getAppyType(name, className=className)
            fields.append(field)
        return Object(fields=fields, nbOfColumns=nbOfColumns)

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

    def getResultMode(self, className):
        '''Must we show, on pxQueryResult, instances of p_className as a list or
           as a grid?'''
        klass = self.getAppyClass(className)
        if hasattr(klass, 'resultMode'): return klass.resultMode
        return 'list' # The default mode

    def getImportElements(self, className):
        '''Returns the list of elements that can be imported from p_path for
           p_className.'''
        appyClass = self.getAppyClass(className)
        importParams = self.getCreateMeans(appyClass)['import']
        onElement = importParams.onElement.__get__('')
        sortMethod = importParams.sort
        if sortMethod: sortMethod = sortMethod.__get__('')
        elems = []
        importType = self.getAppyType('importPathFor%s' % className)
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
        return [importParams.headers, elems]

    def showPortlet(self, context, layoutType):
        '''When must the portlet be shown?'''
        # Not on 'edit' pages.
        if layoutType == 'edit': return
        if context and (context.id == 'ui'): context = context.getParentNode()
        res = True
        if context and hasattr(context.aq_base, 'appy'):
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
        tool = self.appy()
        user = self.getUser()
        rq = tool.request
        # Get the user roles
        res = rq.userRoles
        # Add role "Anonymous"
        if 'Anonymous' not in res: res.append('Anonymous')
        # Add the user id if not anonymous
        userId = user.login
        if userId != 'anon': res.append('user:%s' % userId)
        # Add group ids
        try:
            res += ['user:%s' % g for g in rq.zopeUser.groups.keys()]
        except AttributeError, ae:
            pass # The Zope admin does not have this attribute.
        return res

    def executeQuery(self, className, searchName=None, startNumber=0,
                     search=None, remember=False, brainsOnly=False,
                     maxResults=None, noSecurity=False, sortBy=None,
                     sortOrder='asc', filterKey=None, filterValue=None,
                     refObject=None, refField=None):
        '''Executes a query on instances of a given p_className in the catalog.
           If p_searchName is specified, it corresponds to:
             1) a search defined on p_className: additional search criteria
                will be added to the query, or;
             2) "customSearch": in this case, additional search criteria will
                also be added to the query, but those criteria come from the
                session (in key "searchCriteria") and came from pxSearch.

           We will retrieve objects from p_startNumber. If p_search is defined,
           it corresponds to a custom Search instance (instead of a predefined
           named search like in p_searchName). If both p_searchName and p_search
           are given, p_search is ignored.

           This method returns a list of objects in the form of an instance of
           SomeObjects (see in appy.gen.utils). If p_brainsOnly is True, it
           returns a list of brains instead (can be useful for some usages like
           knowing the number of objects without needing to get information
           about them). If no p_maxResults is specified, the method returns
           maximum self.numberOfResultsPerPage. The method returns all objects
           if p_maxResults equals string "NO_LIMIT".

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

        params = {'ClassName': className}
        appyClass = self.getAppyClass(className, wrapper=True)
        if not brainsOnly: params['batch'] = True
        # Manage additional criteria from a search when relevant
        if searchName: search = self.getSearch(className, searchName)
        if search:
            # Add in params search and sort criteria.
            search.updateSearchCriteria(params, appyClass)
        # Determine or override sort if specified.
        if sortBy:
            params['sort_on'] = Search.getIndexName(sortBy, usage='sort')
            if sortOrder == 'desc': params['sort_order'] = 'reverse'
            else:                   params['sort_order'] = None
        # If defined, add the filter among search parameters.
        if filterKey:
            filterKey = Search.getIndexName(filterKey)
            filterValue = Search.getSearchValue(filterKey,filterValue,appyClass)
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
        res = gutils.SomeObjects(brains, maxResults, startNumber,
                                 noSecurity=noSecurity)
        res.brainsToObjects()
        # In some cases (p_remember=True), we need to keep some information
        # about the query results in the current user's session, allowing him
        # to navigate within elements without re-triggering the query every
        # time a page for an element is consulted.
        if remember:
            if not searchName:
                if not search or (search.name == 'allSearch'):
                    searchName = className
                else:
                    searchName = search.name
            uids = {}
            i = -1
            for obj in res.objects:
                i += 1
                uids[startNumber+i] = obj.UID()
            self.REQUEST.SESSION['search_%s' % searchName] = uids
        return res

    def getResultColumnsLayouts(self, className, refInfo):
        '''Returns the column layouts for displaying objects of
           p_className.'''
        if refInfo[0]:
            return refInfo[0].getAppyType(refInfo[1]).shownInfo
        else:
            toolFieldName = 'resultColumnsFor%s' % className
            return getattr(self.appy(), toolFieldName)

    def truncateValue(self, value, width=15):
        '''Truncates the p_value according to p_width.'''
        if isinstance(value, str): value = value.decode('utf-8')
        if len(value) > width:
            return value[:width].encode('utf-8') + '...'
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

    def splitList(self, l, sub):
        '''Returns a list made of the same elements as p_l, but grouped into
           sub-lists of p_sub elements.'''
        return sutils.splitList(l, sub)

    def quote(self, s):
        '''Returns the quoted version of p_s.'''
        if not isinstance(s, basestring): s = str(s)
        if "'" in s: return '&quot;%s&quot;' % s
        return "'%s'" % s

    def getLayoutType(self):
        '''Guess the current layout type, according to actual URL.'''
        url = self.REQUEST['ACTUAL_URL']
        if url.endswith('/view'): return 'view'
        if url.endswith('/edit') or url.endswith('/do'): return 'edit'

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

    def getCreateMeans(self, klass):
        '''Gets the different ways objects of p_klass can be created (via a web
           form, by importing external data, etc). Result is a dict whose keys
           are strings (ie "form", "import"...) and whose values are additional
           data about the particular mean.'''
        res = {}
        if not klass.__dict__.has_key('create'):
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
                            res[mean.id] = mean
                else:
                    res[means.id] = means
        return res

    def userMaySearch(self, rootClass):
        '''May the logged user search among instances of p_rootClass ?'''
        # When editing a form, one should avoid annoying the user with this.
        url = self.REQUEST['ACTUAL_URL']
        if url.endswith('/edit') or url.endswith('/do'): return
        if 'maySearch' in rootClass.__dict__:
            return pythonClass.rootClass(self.appy())
        return True

    def userMayCreate(self, klass):
        '''May the logged user create instances of p_klass ?'''
        allowedRoles = getattr(klass, 'creators', None) or \
                       self.getProductConfig().appConfig.defaultCreators
        for role in self.getUser().getRoles():
            if role in allowedRoles:
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

    def subTitleIsUsed(self, className):
        '''Does class named p_className define a method "getSubTitle"?'''
        klass = self.getAppyClass(className)
        return hasattr(klass, 'getSubTitle')

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

    def _getDefaultSearchCriteria(self):
        '''We are about to perform an advanced search on instances of a given
           class. Check, on this class, if in field Class.searchAdvanced, some
           default criteria (field values, sort filters, etc) exist, and, if
           yes, return it.'''
        res = {}
        rq = self.REQUEST
        if 'className' not in rq.form: return res
        klass = self.getAppyClass(rq.form['className'])
        if not hasattr(klass, 'searchAdvanced'): return res
        # In klass.searchAdvanced, we have the Search instance representing
        # default advanced search criteria.
        wrapperClass = self.getAppyClass(rq.form['className'], wrapper=True)
        klass.searchAdvanced.updateSearchCriteria(res, wrapperClass,
                                                  advanced=True)
        return res

    transformMethods = {'uppercase': 'upper', 'lowercase': 'lower',
                        'capitalize': 'capitalize'}
    def storeSearchCriteria(self):
        '''Stores the search criteria coming from the request into the
           session.'''
        rq = self.REQUEST
        # Store the search criteria in the session
        criteria = self._getDefaultSearchCriteria()
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

    def onSearchObjects(self):
        '''This method is called when the user triggers a search from
           pxSearch.'''
        rq = self.REQUEST
        self.storeSearchCriteria()
        # Go to the screen that displays search results
        backUrl = '%s/query?className=%s&&search=customSearch' % \
                  (self.absolute_url(), rq['className'])
        return self.goto(backUrl)

    def getJavascriptMessages(self):
        '''Returns the translated version of messages that must be shown in
           Javascript popups.'''
        res = ''
        for msg in jsMessages:
            res += 'var %s = "%s";\n' % (msg, self.translate(msg))
        return res

    def getColumnsSpecifiers(self, className, columnLayouts, dir):
        '''Extracts and returns, from a list of p_columnLayouts, info required
           for displaying columns of field values for instances of p_className,
           either in a result screen or for a Ref field.'''
        res = []
        for info in columnLayouts:
            fieldName, width, align = ColumnLayout(info).get()
            align = self.flipLanguageDirection(align, dir)
            field = self.getAppyType(fieldName, className)
            if not field:
                self.log('Field "%s", used in a column specifier, was not ' \
                         'found.' % fieldName, type='warning')
            else:
                res.append(Object(field=field, width=width, align=align))
        return res

    def getRefInfo(self, refInfo=None):
        '''When a search is restricted to objects referenced through a Ref
           field, this method returns information about this reference: the
           source class and the Ref field. If p_refInfo is not given, we search
           it among search criteria in the session.'''
        if not refInfo and (self.REQUEST.get('search', None) == 'customSearch'):
            criteria = self.REQUEST.SESSION.get('searchCriteria', None)
            if criteria and criteria.has_key('_ref'): refInfo = criteria['_ref']
        if not refInfo: return None, None
        objectUid, fieldName = refInfo.split(':')
        obj = self.getObject(objectUid)
        return obj, fieldName

    def getGroupedSearches(self, klass):
        '''Returns an object with 2 attributes:
           * "searches" stores the searches that are defined for p_klass;
           * "default" stores the search defined as the default one.
           Every item representing a search is a dict containing info about a
           search or about a group of searches.
        '''
        res = []
        default = None # Also retrieve the default one here.
        groups = {} # The already encountered groups
        page = Page('main') # A dummy page required by class UiGroup
        # Get the searches statically defined on the class
        searches = ClassDescriptor.getSearches(klass, tool=self.appy())
        # Get the dynamically computed searches
        if hasattr(klass, 'getDynamicSearches'):
            searches += klass.getDynamicSearches(self.appy())
        for search in searches:
            # Create the search descriptor
            uiSearch = UiSearch(search, className, self)
            if not search.group:
                # Insert the search at the highest level, not in any group.
                res.append(uiSearch)
            else:
                uiGroup = search.group.insertInto(res, groups, page, className,
                                                  forSearch=True)
                uiGroup.addField(uiSearch)
            # Is this search the default search?
            if search.default: default = uiSearch
        return Object(searches=res, default=default)

    def getSearch(self, className, name, ui=False):
        '''Gets the Search instance (or a UiSearch instance if p_ui is True)
           corresponding to the search named p_name, on class p_className.'''
        if name == 'customSearch':
            # It is a custom search whose parameters are in the session.
            fields = self.REQUEST.SESSION['searchCriteria']
            res = Search('customSearch', **fields)
        elif name:
            appyClass = self.getAppyClass(className)
            # Search among static searches
            res = ClassDescriptor.getSearch(appyClass, name)
            if not res and hasattr(appyClass, 'getDynamicSearches'):
                # Search among dynamic searches
                for search in appyClass.getDynamicSearches(self.appy()):
                    if search.name == name:
                        res = search
                        break
        else:
            # It is the search for every instance of p_className
            res = Search('allSearch')
        # Return a UiSearch if required.
        if ui: res = UiSearch(res, className, self)
        return res

    def advancedSearchEnabledFor(self, klass):
        '''Is advanced search visible for p_klass ?'''
        # By default, advanced search is enabled.
        if not hasattr(klass, 'searchAdvanced'): return True
        # Evaluate attribute "show" on this Search instance representing the
        # advanced search.
        return klass.searchAdvanced.isShowable(klass, self.appy())

    def getQueryUrl(self, contentType, searchName, startNumber=None):
        '''This method creates the URL that allows to perform a (non-Ajax)
           request for getting queried objects from a search named p_searchName
           on p_contentType.'''
        baseUrl = self.absolute_url()
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
        '''Extracts navigation information from request/nav and returns an
           object with the info that a page can use for displaying object
           navigation.'''
        res = Object()
        rq = self.REQUEST
        t, d1, d2, currentNumber, totalNumber = rq.get('nav').split('.')
        res.currentNumber = int(currentNumber)
        res.totalNumber = int(totalNumber)
        # Compute the label of the search, or ref field
        if t == 'search':
            searchName = d2
            if not searchName:
                # We search all objects of a given type.
                label = '%s_plural' % d1.split(':')[0]
            elif searchName == 'customSearch':
                # This is an advanced, custom search.
                label = 'search_results'
            else:
                # This is a named, predefined search.
                label = '%s_search_%s' % (d1.split(':')[0], searchName)
            res.backText = self.translate(label)
            # If it is a dynamic search this label does not exist.
            if ('_' in res.backText): res.backText = ''
        else:
            fieldName, pageName = d2.split(':')
            sourceObj = self.getObject(d1)
            label = '%s_%s' % (sourceObj.meta_type, fieldName)
            res.backText = '%s - %s' % (sourceObj.Title(),self.translate(label))
        newNav = '%s.%s.%s.%%d.%s' % (t, d1, d2, totalNumber)
        # Among, first, previous, next and last, which one do I need?
        previousNeeded = False # Previous ?
        previousIndex = res.currentNumber - 2
        if (previousIndex > -1) and (res.totalNumber > previousIndex):
            previousNeeded = True
        nextNeeded = False     # Next ?
        nextIndex = res.currentNumber
        if nextIndex < res.totalNumber: nextNeeded = True
        firstNeeded = False    # First ?
        firstIndex = 0
        if previousIndex > 0: firstNeeded = True
        lastNeeded = False     # Last ?
        lastIndex = res.totalNumber - 1
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
            startNumber = self.computeStartNumberFrom(res.currentNumber-1,
                res.totalNumber, batchSize)
            res.sourceUrl = masterObj.getUrl(**{startNumberKey:startNumber,
                                             'page':pageName, 'nav':''})
        else: # Manage navigation from a search
            contentType = d1
            searchName = keySuffix = d2
            batchSize = self.appy().numberOfResultsPerPage
            if not searchName: keySuffix = contentType
            s = rq.SESSION
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
                newStartNumber = (res.currentNumber-1) - (batchSize / 2)
                if newStartNumber < 0: newStartNumber = 0
                self.executeQuery(contentType, searchName=searchName,
                                  startNumber=newStartNumber, remember=True)
                uids = s[searchKey]
            # For the moment, for first and last, we get them only if we have
            # them in session.
            if not uids.has_key(0): firstNeeded = False
            if not uids.has_key(lastIndex): lastNeeded = False
            # Compute URL of source object
            startNumber = self.computeStartNumberFrom(res.currentNumber-1,
                                                     res.totalNumber, batchSize)
            res.sourceUrl = self.getQueryUrl(contentType, searchName,
                                             startNumber=startNumber)
        # Compute URLs
        for urlType in ('previous', 'next', 'first', 'last'):
            exec 'needIt = %sNeeded' % urlType
            urlKey = '%sUrl' % urlType
            setattr(res, urlKey, None)
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
                        setattr(res, urlKey, sibling.getUrl(\
                            nav=newNav % (index + 1),
                            page=rq.get('page', 'main')))
        return res

    def getGroupedSearchFields(self, searchInfo):
        '''This method transforms p_searchInfo.fields, which is a "flat"
           list of fields, into a list of lists, where every sub-list having
           length p_searchInfo.nbOfColumns. For every field, scolspan
           (=colspan "for search") is taken into account.'''
        res = []
        row = []
        rowLength = 0
        for field in searchInfo.fields:
            # Can I insert this field in the current row?
            remaining = searchInfo.nbOfColumns - rowLength
            if field.scolspan <= remaining:
                # Yes.
                row.append(field)
                rowLength += field.scolspan
            else:
                # We must put the field on a new line. Complete the current one
                # if not complete.
                while rowLength < searchInfo.nbOfColumns:
                    row.append(None)
                    rowLength += 1
                res.append(row)
                row = [field]
                rowLength = field.scolspan
        # Complete the last unfinished line if required.
        if row:
            while rowLength < searchInfo.nbOfColumns:
                row.append(None)
                rowLength += 1
            res.append(row)
        return res

    # --------------------------------------------------------------------------
    # Authentication-related methods
    # --------------------------------------------------------------------------
    def _encryptPassword(self, password):
        '''Returns the encrypted version of clear p_password.'''
        return self.acl_users._encryptPassword(password)

    def _zopeAuthenticate(self, request):
        '''Performs the Zope-level authentication. Returns True if
           authentication succeeds.'''
        user = self.acl_users.validate(request)
        return user.getUserName() != 'Anonymous User'

    def _ldapAuthenticate(self, login, password):
        '''Performs a LDAP-based authentication. Returns True if authentication
           succeeds.'''
        # Check if LDAP is configured.
        ldapConfig = self.getProductConfig(True).ldap
        if not ldapConfig: return
        user = ldap.authenticate(login, password, ldapConfig, self)
        if not user: return
        return True

    def performLogin(self):
        '''Logs the user in.'''
        rq = self.REQUEST
        jsEnabled = rq.get('js_enabled', False) in ('1', 1)
        cookiesEnabled = rq.get('cookies_enabled', False) in ('1', 1)
        urlBack = rq['HTTP_REFERER']
        if jsEnabled and not cookiesEnabled:
            msg = self.translate('enable_cookies')
            return self.goto(urlBack, msg)
        # Extract the login and password, and create an authentication cookie
        login = rq.get('__ac_name', '')
        password = rq.get('__ac_password', '')
        gutils.writeCookie(login, password, rq)
        # Perform the Zope-level authentication
        if self._zopeAuthenticate(rq) or self._ldapAuthenticate(login,password):
            msg = self.translate('login_ok')
            logMsg = 'User "%s" logged in.' % login
        else:
            rq.RESPONSE.expireCookie('_appy_', path='/')
            msg = self.translate('login_ko')
            logMsg = 'Authentication failed with login "%s".' % login
        self.log(logMsg)
        return self.goto(self.getApp().absolute_url(), msg)

    def performLogout(self):
        '''Logs out the current user when he clicks on "disconnect".'''
        rq = self.REQUEST
        userId = self.getUser().login
        # Perform the logout in acl_users
        rq.RESPONSE.expireCookie('_appy_', path='/')
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
        print c
        # Try to get user name and password from basic authentication
        login, password = self.identify(auth)
        if not login:
            # Try to get them from a cookie
            login, password = gutils.readCookie(request)
            if not login:
                # Maybe the user just entered his credentials. The cookie could
                # have been set in the response, but is not in the request.
                login = request.get('__ac_name', None)
                password = request.get('__ac_password', None)
        # Try to authenticate this user
        user = self.authenticate(login, password, request)
        emergency = self._emergency_user
        if emergency and (user is emergency):
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
            # That didn't work. Try to authorize the anonymous user.
            elif self.authorize(self._nobody, a, c, n, v, roles):
                return self._nobody.__of__(self)
            else:
                return

    # Patch BasicUserFolder with our version of m_validate above.
    from AccessControl.User import BasicUserFolder
    BasicUserFolder.validate = validate

    def getUser(self):
        '''Gets the User instance (Appy wrapper) corresponding to the current
           user.'''
        tool = self.appy()
        rq = tool.request
        # Try first to return the user that can be cached on the request.
        if hasattr(rq, 'user'): return rq.user
        # Get the user login from the authentication cookie.
        login, password = gutils.readCookie(rq)
        if not login: # It is the anonymous user or the system.
            # If we have a real request object, it is the anonymous user.
            login = (rq.__class__.__name__ == 'Object') and 'system' or 'anon'
        # Get the User object from a query in the catalog.
        user = tool.search1('User', noSecurity=True, login=login)
        # It is possible that we find no user here: it happens before users
        # "anon" and "system" are created, at first Zope startup.
        if not user: return
        rq.user = user
        # Precompute some values or this user for performance reasons.
        rq.userRoles = user.getRoles()
        rq.userLogins = user.getLogins()
        rq.zopeUser = user.getZopeUser()
        return user

    def getUserLine(self):
        '''Returns a info about the currently logged user as a 2-tuple: first
           elem is the one-line user info as shown on every page; second line is
           the URL to edit user info.'''
        user = self.getUser()
        info = [user.title]
        showable = [r for r in user.getRoles() if r != 'Authenticated']
        if showable:
            info.append(', '.join([self.translate('role_%s' % r) \
                                   for r in showable]))
        # Edit URL for the user.
        url = None
        if user.o.mayEdit():
            url = user.o.getUrl(mode='edit', page='main', nav='')
        return (' | '.join(info), url)

    def getUserName(self, login=None, normalized=False):
        '''Gets the user name corresponding to p_login (or the currently logged
           user if None), or the p_login itself if the user does not exist
           anymore. If p_normalized is True, special chars in the first and last
           names are normalized.'''
        tool = self.appy()
        if not login: login = tool.user.login
        # Manage the special case of an anonymous user.
        if login == 'anon':
            name = self.translate('anonymous')
            if normalized: name = sutils.normalizeString(name)
            return name
        # Manage the case of any other user.
        user = tool.search1('User', noSecurity=True, login=login)
        if not user: return login
        firstName = user.firstName
        name = user.name
        res = ''
        if firstName:
            if normalized: firstName = sutils.normalizeString(firstName)
            res += firstName
        if name:
            if normalized: name = sutils.normalizeString(name)
            if res: res += ' ' + name
            else: res = name
        if not res: res = login
        return res

    def tempFile(self):
        '''A temp file has been created in a temp folder. This method returns
           this file to the browser.'''
        rq = self.REQUEST
        baseFolder = os.path.join(sutils.getOsTempFolder(), self.getAppName())
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
        if error.type.__name__ == 'Unauthorized':
            siteUrl = self.getSiteUrl()
            htmlMessage = '<a href="%s"><img src="%s/ui/home.gif"/></a>' \
                          'You are not allowed to access this page.' % \
                          (siteUrl, siteUrl)
            userId = self.appy().user.login
            textMessage = 'Unauthorized for %s @%s.' % \
                          (userId, self.REQUEST.get('PATH_INFO'))
        else:
            from zExceptions.ExceptionFormatter import format_exception
            htmlMessage = format_exception(tb[0], tb[1], tb[2], as_html=1)
            htmlMessage = '\n'.join(htmlMessage)
            textMessage = format_exception(tb[0], tb[1], tb[2], as_html=0)
            textMessage = ''.join(textMessage).strip()
        self.log(textMessage, type='error')
        return '<div class="error">%s</div>' % htmlMessage

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
        f = file(os.path.join(sutils.getOsTempFolder(), login), 'w')
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
        tokenFile = os.path.join(sutils.getOsTempFolder(), login)
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
        if method.__class__.__name__ == 'function':
            objects = method(tool)
        else:
            objects = method.__get__(tool)(tool)
        return [(o.uid, o) for o in objects]

    def getGoogleAnalyticsCode(self):
        '''If the config defined a Google Analytics ID, this method returns the
           Javascript code to be included in every page, allowing Google
           Analytics to work.'''
        # Disable Google Analytics when we are in debug mode.
        if self.isDebug(): return
        # Disable Google Analytics if no ID is found in the config.
        gaId = self.getProductConfig(True).googleAnalyticsId
        if not gaId: return
        # Google Analytics must be enabled: return the chunk of Javascript
        # code specified by Google.
        code = "var _gaq = _gaq || [];\n" \
               "_gaq.push(['_setAccount', '%s']);\n" \
               "_gaq.push(['_trackPageview']);\n" \
               "(function() {\n" \
               "  var ga = document.createElement('script'); " \
               "ga.type = 'text/javascript'; ga.async = true;\n" \
               "  ga.src = ('https:' == document.location.protocol ? " \
               "'https://ssl' : 'http://www') + " \
               "'.google-analytics.com/ga.js';\n" \
               "  var s = document.getElementsByTagName('script')[0]; " \
               "s.parentNode.insertBefore(ga, s);\n" \
               "})();\n" % gaId
        return code
# ------------------------------------------------------------------------------
