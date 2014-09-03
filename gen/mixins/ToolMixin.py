# ------------------------------------------------------------------------------
import os, os.path, sys, re, time, random, types, base64
from appy import Object
import appy.gen
from appy.gen import Search, UiSearch, String, Page
from appy.gen.layout import ColumnLayout
from appy.gen import utils as gutils
from appy.gen.mixins import BaseMixin
from appy.gen.wrappers import AbstractWrapper
from appy.gen.descriptors import ClassDescriptor
from appy.gen.mail import sendMail
from appy.shared import mimeTypes
from appy.shared import utils as sutils
from appy.shared.data import languages
from appy.shared.ldap_connector import LdapConnector
try:
    from AccessControl.ZopeSecurityPolicy import _noroles
except ImportError:
    _noroles = []

# Global JS internationalized messages that will be computed in every page -----
jsMessages = ('no_elem_selected', 'action_confirm', 'save_confirm',
              'warn_leave_form')

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
        url = None
        try:
            url = tool.getHomePage()
        except AttributeError:
            pass
        if not url:
            # Bring Managers to the config, lead others to pxHome.
            user = self.getUser()
            if user.has_role('Manager'):
                url = self.goto(self.absolute_url())
            else:
                url = self.goto('%s/home' % self.absolute_url())
        return url

    def getHomeObject(self, inPopup=False):
        '''The concept of "home object" is the object where the user must "be",
           even if he is "nowhere". For example, if the user is on a search
           screen, there is no contextual object. In this case, if we have a
           home object for him, we will use it as contextual object, and its
           portlet menu will nevertheless appear: the user will not have the
           feeling of being lost.'''
        # If we are in the popup, we do not want any home object in the way.
        if inPopup: return
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

    def doPod(self):
        '''Performs an action linked to a pod field: generate, freeze,
           unfreeze... a document from a pod field.'''
        rq = self.REQUEST
        # Get the object that is the target of this action.
        obj = self.getObject(rq.get('objectUid'), appy=True)
        return obj.getField(rq.get('fieldName')).onUiRequest(obj, rq)

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

    def getLanguageName(self, code, lowerize=False):
        '''Gets the language name (in this language) from a 2-chars language
           p_code.'''
        res = languages.get(code)[2]
        if not lowerize: return res
        return res.lower()

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

    def getGlobalCssJs(self, dir):
        '''Returns the list of CSS and JS files to include in the main template.
           The method ensures that appy.css and appy.js come first. If p_dir
           (=language *dir*rection) is "rtl" (=right-to-left), the stylesheet
           for rtl languages is also included.'''
        names = self.getPhysicalRoot().ui.objectIds('File')
        # The single Appy Javascript file
        names.remove('appy.js'); names.insert(0, 'appy.js')
        # CSS changes for left-to-right languages
        names.remove('appyrtl.css')
        if dir == 'rtl': names.insert(0, 'appyrtl.css')
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
        cfg = self.getProductConfig().appConfig
        rootClasses = cfg.rootClasses
        if not rootClasses:
            # We consider every class as being a root class.
            rootClasses = self.getProductConfig().appClassNames
        return [self.getAppyClass(k) for k in rootClasses]

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
            klass = self.getAppyClass(className)
            fieldNames = getattr(klass, 'searchFields', None)
            if not fieldNames:
                # Gather all the indexed fields on this class.
                fieldNames = [f.name for f in self.getAllAppyTypes(className) \
                              if f.indexed]
            nbOfColumns = getattr(klass, 'numberOfSearchColumns', 3)
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
        return getattr(klass, 'resultMode', 'list')

    def showPortlet(self, obj, layoutType):
        '''When must the portlet be shown? p_obj and p_layoutType can be None
           if we are not browing any objet (ie, we are on the home page).'''
        # Not on 'edit' pages.
        if layoutType == 'edit': return
        res = True
        if obj and hasattr(obj, 'showPortlet'):
            res = obj.showPortlet()
        else:
            tool = self.appy()
            if hasattr(tool, 'showPortletAt'):
                res = tool.showPortletAt(self.REQUEST['ACTUAL_URL'])
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
        '''Gets, for the current user, the value of index "Allowed".'''
        user = self.getUser()
        # Get the user roles. If we do not make a copy of the list here, we will
        # really add user logins among user roles!
        res = user.getRoles()[:]
        # Get the user logins
        if user.login != 'anon':
            for login in user.getLogins():
                res.append('user:%s' % login)
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
        # Compute maxResults
        if not maxResults:
            if refField: maxResults = refField.maxPerPage
            else: maxResults = search.maxPerPage or \
                               self.appy().numberOfResultsPerPage
        elif maxResults == 'NO_LIMIT':
            maxResults = None
        # Return brains only if required.
        if brainsOnly:
            if not maxResults: return brains
            else: return brains[:maxResults]
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
            k = self.getAppyClass(className)
            return hasattr(k, 'listColumns') and k.listColumns or ('title',)

    def truncateValue(self, value, width=20):
        '''Truncates the p_value according to p_width. p_value has to be
           unicode-encoded for being truncated (else, one char may be spread on
           2 chars).'''
        # Param p_width can be None.
        if not width: width = 20
        if isinstance(value, str): value = value.decode('utf-8')
        if len(value) > width: return value[:width] + '...'
        return value

    def truncateText(self, text, width=20):
        '''Truncates p_text to max p_width chars. If the text is longer than
           p_width, the truncated part is put in a "acronym" html tag. p_text
           has to be unicode-encoded for being truncated (else, one char may be
           spread on 2 chars).'''
        # Param p_width can be None.
        if not width: width = 20
        if isinstance(text, str): text = text.decode('utf-8')
        if len(text) <= width: return text
        return '<acronym title="%s">%s...</acronym>' % (text, text[:width])

    def splitList(self, l, sub):
        '''Returns a list made of the same elements as p_l, but grouped into
           sub-lists of p_sub elements.'''
        return sutils.splitList(l, sub)

    def quote(self, s, escapeWithEntity=True):
        '''Returns the quoted version of p_s.'''
        if not isinstance(s, basestring): s = str(s)
        repl = escapeWithEntity and '&apos;' or "\\'"
        s = s.replace('\r\n', '').replace('\n', '').replace("'", repl)
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
        # p_zopeName may be the name of the Zope class *or* the name of the Appy
        # class (shorter, not prefixed with the underscored package path).
        classes = self.getProductConfig().allShortClassNames
        if zopeName in classes: zopeName = classes[zopeName]
        zopeClass = self.getZopeClass(zopeName)
        if wrapper: return zopeClass.wrapperClass
        else: return zopeClass.wrapperClass.__bases__[-1]

    def getAllClassNames(self):
        '''Returns the name of all classes within this app, including default
           Appy classes (Tool, Translation, Page, etc).'''
        return self.getProductConfig().allClassNames + [self.__class__.__name__]

    def getCreateMeans(self, klass):
        '''Gets the different ways objects of p_klass can be created (currently:
           via a web form or programmatically only). Result is a list.'''
        res = []
        if not klass.__dict__.has_key('create'):
            return ['form']
        else:
            means = klass.create
            if means:
                if isinstance(means, basestring): res = [means]
                else: res = means
        return res

    def userMaySearch(self, klass):
        '''May the user search among instances of root p_klass ?'''
        # When editing a form, one should avoid annoying the user with this.
        url = self.REQUEST['ACTUAL_URL']
        if url.endswith('/edit') or url.endswith('/do'): return
        if hasattr(klass, 'maySearch'): return klass.maySearch(self.appy())
        return True

    def userMayCreate(self, klass):
        '''May the logged user create instances of p_klass ? This information
           can be defined on p_klass, in static attribute "creators".
           1. If this attr holds a list, we consider it to be a list of roles,
              and we check that the user has at least one of those roles.
           2. If this attr holds a boolean, we consider that the user can create
              instances of this class if the boolean is True.
           3. If this attr stores a method, we execute the method, and via its
              result, we fall again in cases 1 or 2.

           If p_klass does not define this attr "creators", we will use a
           default list of roles as defined in the config.'''
        # Get the value of attr "creators", or a default value if not present.
        if hasattr(klass, 'creators'):
            creators = klass.creators
        else:
            creators = self.getProductConfig().appConfig.defaultCreators
        # Resolve case (3): if "creators" is a method, execute it.
        if callable(creators): creators = creators(self.appy())
        # Resolve case (2)
        if isinstance(creators, bool) or not creators: return creators
        # Resolve case (1): checks whether the user has at least one of the
        # roles listed in "creators".
        for role in self.getUser().getRoles():
            if role in creators:
                return True

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
        for name in rq.form.keys():
            if name.startswith('w_') and not self._searchValueIsEmpty(name):
                hasStar = name.find('*') != -1
                fieldName = not hasStar and name[2:] or name[2:name.find('*')]
                field = self.getAppyType(fieldName, rq.form['className'])
                if field and not field.persist and not field.indexed: continue
                # We have a(n interval of) value(s) that is not empty for a
                # given field or index.
                value = rq.form[name]
                if hasStar:
                    value = value.strip()
                    # The type of the value is encoded after char "*".
                    name, type = name.split('*')
                    if type == 'bool':
                        exec 'value = %s' % value
                    elif type in ('int', 'float'):
                        # Get the "from" value
                        if not value: value = None
                        else:
                            exec 'value = %s(value)' % type
                        # Get the "to" value
                        toValue = rq.form['%s_to' % name[2:]].strip()
                        if not toValue: toValue = None
                        else:
                            exec 'toValue = %s(toValue)' % type
                        value = (value, toValue)
                    elif type == 'date':
                        prefix = name[2:]
                        # Get the "from" value
                        year  = value
                        month = rq.form['%s_from_month' % prefix]
                        day   = rq.form['%s_from_day' % prefix]
                        fromDate = self._getDateTime(year, month, day, True)
                        # Get the "to" value"
                        year  = rq.form['%s_to_year' % prefix]
                        month = rq.form['%s_to_month' % prefix]
                        day   = rq.form['%s_to_day' % prefix]
                        toDate = self._getDateTime(year, month, day, False)
                        value = (fromDate, toDate)
                    elif type.startswith('string'):
                        # In the case of a string, it could be necessary to
                        # apply some text transform.
                        if len(type) > 6:
                            transform = type.split('-')[1]
                            if (transform != 'none') and value:
                                exec 'value = value.%s()' % \
                                     self.transformMethods[transform]
                if isinstance(value, list):
                    # It is a list of values. Check if we have an operator for
                    # the field, to see if we make an "and" or "or" for all
                    # those values. "or" will be the default.
                    operKey = 'o_%s' % name[2:]
                    oper = ' %s ' % rq.form.get(operKey, 'or').upper()
                    value = oper.join(value)
                criteria[name[2:]] = value
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
                self.log('field "%s", used in a column specifier, was not ' \
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
        page = Page('searches') # A dummy page required by class UiGroup
        # Get the searches statically defined on the class
        className = self.getPortalType(klass)
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
                                                  content='searches')
                uiGroup.addElement(uiSearch)
            # Is this search the default search?
            if search.default: default = uiSearch
        return Object(searches=res, default=default)

    def getSearch(self, className, name, ui=False):
        '''Gets the Search instance (or a UiSearch instance if p_ui is True)
           corresponding to the search named p_name, on class p_className.'''
        initiator = None
        if name == 'customSearch':
            # It is a custom search whose parameters are in the session.
            fields = self.REQUEST.SESSION['searchCriteria']
            res = Search('customSearch', **fields)
        elif ':' in name:
            # The search is defined in a Ref field with link=popup. Get the
            # search, the initiator object and the Ref field.
            uid, ref, mode = name.split(':')
            initiator = self.getObject(uid, appy=True)
            initiatorField = initiator.getField(ref)
            res = getattr(initiator.klass, ref).select
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
        if ui:
            res = UiSearch(res, className, self)
            if initiator: res.setInitiator(initiator, initiatorField, mode)
        return res

    def advancedSearchEnabledFor(self, klass):
        '''Is advanced search visible for p_klass ?'''
        # By default, advanced search is enabled.
        if not hasattr(klass, 'searchAdvanced'): return True
        # Evaluate attribute "show" on this Search instance representing the
        # advanced search.
        return klass.searchAdvanced.isShowable(klass, self.appy())

    def portletBottom(self, klass):
        '''Is there a custom zone to display at the bottom of the portlet zone
           for p_klass?'''
        if not hasattr(klass, 'getPortletBottom'): return ''
        res = klass.getPortletBottom(self.appy())
        if not res: return ''
        return res

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

    def getNavigationInfo(self, inPopup=False):
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
            startNumberKey = '%s%s_startNumber' % (masterObj.id, fieldName)
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
                            page=rq.get('page', 'main'), inPopup=inPopup))
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
    def identifyUser(self, alsoSpecial=False):
        '''To identify a user means: get its login and password. There are
           several places to look for this information: http authentication,
           cookie of credentials coming from the web form.

           If no user could be identified, and p_alsoSpecial is True, we will
           nevertheless identify a "special user": "system", representing the
           system itself (running at startup or in batch mode) or "anon",
           representing an anonymous user.'''
        tool = self.appy()
        req = tool.request
        login = password = None
        # a. Identify the user from http basic authentication.
        if getattr(req, '_auth', None):
            # HTTP basic authentication credentials are present (used when
            # connecting to the ZMI). Decode it.
            creds = req._auth
            if creds.lower().startswith('basic '):
                try:
                    creds = creds.split(' ')[-1]
                    login, password = base64.decodestring(creds).split(':', 1)
                except Exception, e:
                    pass
        # b. Identify the user from the authentication cookie.
        if not login:
            login, password = gutils.readCookie(req)
        # c. Identify the user from the authentication form.
        if not login:
            login = req.get('__ac_name', None)
            password = req.get('__ac_password', '')
        # Stop identification here if we don't need to return a special user
        if not alsoSpecial: return login, password
        # d. All the identification methods failed. So identify the user as
        # "anon" or "system".
        if not login:
            # If we have a fake request, we are at startup or in batch mode and
            # the user is "system". Else, it is "anon". At Zope startup, Appy
            # uses an Object instance as a fake request. In "zopectl run" mode
            # (the Zope batch mode), Appy adds a param "_fake_" on the request
            # object created by Zope.
            if (req.__class__.__name__ == 'Object') or \
               (hasattr(req, '_fake_') and req._fake_):
                login = 'system'
            else:
                login = 'anon'
        return login, password

    def getLdapUser(self, login, password):
        '''Returns a local User instance corresponding to a LDAP user if p_login
           and p_password correspong to a valid LDAP user.'''
        # Check if LDAP is configured.
        cfg = self.getProductConfig(True).ldap
        if not cfg: return
        # Get a connector to the LDAP server and connect to the LDAP server.
        serverUri = cfg.getServerUri()
        connector = LdapConnector(serverUri, tool=self)
        success, msg = connector.connect(cfg.adminLogin, cfg.adminPassword)
        if not success: return
        # Check if the user corresponding to p_login exists in the LDAP.
        filter = connector.getFilter(cfg.getUserFilterValues(login))
        params = cfg.getUserAttributes()
        ldapData = connector.search(cfg.baseDn, cfg.scope, filter, params)
        if not ldapData: return
        # The user exists. Try to connect to the LDAP with this user in order
        # to validate its password.
        userConnector = LdapConnector(serverUri, tool=self)
        success, msg = userConnector.connect(ldapData[0][0], password)
        if not success: return
        # The password is correct. We can create/update our local user
        # corresponding to this LDAP user.
        userParams = cfg.getUserParams(ldapData[0][1])
        tool = self.appy()
        user = tool.search1('User', noSecurity=True, login=login)
        if user:
            # Update the user with fresh info about him from the LDAP
            for name, value in userParams.iteritems():
                setattr(user, name, value)
            # Update user password
            user.setPassword(password, log=False)
            user.reindex()
        else:
            # Create the user
            user = tool.create('users', noSecurity=True, login=login,
                               password1=password, source='ldap', **userParams)
        return user

    def getUser(self, authentify=False, source='zodb'):
        '''Gets the current user. If p_authentify is True, in addition to
           finding the logged user and returning it (=identification), we check
           if found credentials are valid (=authentification).

           If p_authentify is True and p_source is "zodb", authentication is
           performed locally. Else (p_source is "ldap"), authentication is
           performed on a LDAP (if a LDAP configuration is found). If p_source
           is "any", authentication is performed on the local User object, be it
           really local or a copy of a LDAP user.'''
        tool = self.appy()
        req = tool.request
        # Try first to return the user that can be cached on the request. In
        # this case, we suppose authentication has previously been done, and we
        # just return the cached user.
        if hasattr(req, 'user'): return req.user
        # Identify the user (=find its login and password). If we don't need
        # to authentify the user, we ask to identify a user or, if impossible,
        # a special user.
        login, password = self.identifyUser(alsoSpecial=not authentify)
        # Stop here if no user was found and authentication was required.
        if authentify and not login: return
        # Now, get the User instance.
        if source == 'zodb':
            # Get the User object, but only if it is a true local user.
            user = tool.search1('User', noSecurity=True, login=login)
            if user and (user.source != 'zodb'): user = None # Not a local one.
        elif source == 'ldap':
            user = self.getLdapUser(login, password)
        elif source == 'any':
            # Get the user object, be it really local or a copy of a LDAP user.
            user = tool.search1('User', noSecurity=True, login=login)
        if not user: return
        # Authentify the user if required.
        if authentify:
            if not user.checkPassword(password):
                # Disable the authentication cookie.
                req.RESPONSE.expireCookie('_appy_', path='/')
                return
            # Create an authentication cookie for this user.
            gutils.writeCookie(login, password, req)
        # Cache the user and some precomputed values, for performance.
        req.user = user
        req.userRoles = user.getRoles()
        req.userLogins = user.getLogins()
        req.zopeUser = user.getZopeUser()
        return user

    def performLogin(self):
        '''Logs the user in.'''
        rq = self.REQUEST
        jsEnabled = rq.get('js_enabled', False) in ('1', 1)
        cookiesEnabled = rq.get('cookies_enabled', False) in ('1', 1)
        urlBack = rq['HTTP_REFERER']
        if jsEnabled and not cookiesEnabled:
            msg = self.translate('enable_cookies')
            return self.goto(urlBack, msg)
        # Authenticate the user.
        if self.getUser(authentify=True) or \
           self.getUser(authentify=True, source='ldap'):
            msg = self.translate('login_ok')
            logMsg = 'logged in.'
        else:
            msg = self.translate('login_ko')
            login = rq.get('__ac_name') or '<empty>'
            logMsg = 'authentication failed with login %s.' % login
        self.log(logMsg)
        return self.goto(self.getApp().absolute_url(), msg)

    def performLogout(self):
        '''Logs out the current user when he clicks on "disconnect".'''
        rq = self.REQUEST
        userId = self.getUser().login
        # Perform the logout in acl_users
        rq.RESPONSE.expireCookie('_appy_', path='/')
        # Invalidate the user session.
        try:
            sdm = self.session_data_manager
        except AttributeError, ae:
            # When ran in test mode, session_data_manager is not there.
            sdm = None
        if sdm:
            session = sdm.getSessionData(create=0)
            if session is not None:
                session.invalidate()
        self.log('logged out.')
        # Remove user from variable "loggedUsers"
        if self.loggedUsers.has_key(userId): del self.loggedUsers[userId]
        return self.goto(self.getApp().absolute_url())

    # This dict stores, for every logged user, the date/time of its last access
    loggedUsers = {}
    forgetAccessExtensions = ('.jpg', '.gif', '.png', '.js', '.css')
    def rememberAccess(self, id, user):
        '''Every time there is a hit on the server, this method is called in
           order to update global dict loggedUsers (see above).'''
        if not id: return
        if os.path.splitext(id)[-1].lower() in self.forgetAccessExtensions:
            return
        self.loggedUsers[user.login] = time.time()
        # "Touch" the SESSION object. Else, expiration won't occur.
        session = self.REQUEST.SESSION

    def validate(self, request, auth='', roles=_noroles):
        '''This method performs authentication and authorization. It is used as
           a replacement for Zope's AccessControl.User.BasicUserFolder.validate,
           that allows to manage cookie-based authentication.'''
        v = request['PUBLISHED'] # The published object
        tool = self.getParentNode().config
        # v is the object (value) we're validating access to
        # n is the name used to access the object
        # a is the object the object was accessed through
        # c is the physical container of the object
        a, c, n, v = self._getobcontext(v, request)
        # Identify and authentify the user
        user = tool.getUser(authentify=True, source='any')
        if not user:
            # Login and/or password incorrect. Try to authorize and return the
            # anonymous user.
            if self.authorize(self._nobody, a, c, n, v, roles):
                return self._nobody.__of__(self)
            else:
                return
        else:
            # We found a user and his password was correct. Try to authorize him
            # against the published object. By the way, remember its last access
            # to this system.
            tool.rememberAccess(a.getId(), user)
            user = user.getZopeUser()
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

    def getUserLine(self):
        '''Returns info about the currently logged user as a 2-tuple: first
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
        return [f for f in self.getAllAppyTypes(contentType) \
                if (f.type == 'Pod') and (f.show == 'result')]

    def formatDate(self, date, withHour=True):
        '''Returns p_date formatted as specified by tool.dateFormat.
           If p_withHour is True, hour is appended, with a format specified
           in tool.hourFormat.'''
        tool = self.appy()
        res = date.strftime(tool.dateFormat)
        if withHour: res += ' (%s)' % date.strftime(tool.hourFormat)
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
            htmlMessage = '<a href="/">Back</a> You are not allowed to ' \
                          'access this page.'
            userId = self.appy().user.login
            textMessage = 'unauthorized for %s @%s.' % \
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

    def getButtonWidth(self, label):
        '''Determine button width, in pixels, corresponding to the button
           p_label.'''
        # Set a minimum width for small labels.
        if len(label) < 15: return 'width:130px'
        return 'padding-left: 26px; padding-right: 8px'

    def getLinksTargetInfo(self, klass):
        '''Appy allows to open links to view or edit instances of p_klass
           either via the same browser window, or via a popup. This method
           returns info about that, as an object having 2 attributes:
           - target is "_self" if the link leads to the same browser window,
                    "appyIFrame" if the link must be opened in a popup;
           - openPopup  is unused if target is "_self" and contains the
                        Javascript code to open the popup.'''
        res = Object(target='_self', openPopup='')
        if hasattr(klass, 'popup'):
            res.target = 'appyIFrame'
            d = klass.popup
            if isinstance(d, basestring):
                # Width only
                params = int(d[:-2])
            else:
                # Width and height
                params = "%s, %s" % (d[0][:-2], d[1][:-2])
            res.openPopup = "openPopup('iframePopup',null,%s)" % params
        return res

    def backFromPopup(self):
        '''Returns the PX allowing to close the iframe popup and refresh the
           base page.'''
        return self.appy().pxBack({'ztool': self})

    ieRex = re.compile('MSIE\s+(\d\.\d)')
    ieMin = '9' # We do not support IE below this version.
    def getBrowserIncompatibility(self):
        '''Produces an error message if the browser in use is not compatible
           with Appy.'''
        res = self.ieRex.search(self.REQUEST.get('HTTP_USER_AGENT'))
        if not res: return
        version = res.group(1)
        if version < self.ieMin:
            mapping = {'version': version, 'min': self.ieMin}
            return self.translate('wrong_browser', mapping=mapping)

    def executeAjaxAction(self, action, obj, field):
        '''When PX "pxAjax" is called to get some chunk of XHTML via an Ajax
           request, a server action can be executed before rendering the XHTML
           chunk. This method executes this action.'''
        if action.startswith(':'):
            # The action corresponds to a method on Appy p_obj.
            getattr(obj, action[1:])()
        else:
            # The action must be executed on p_field if present, on obj.o else.
            if field: getattr(field, action)(obj.o)
            else: getattr(obj.o, action)()
# ------------------------------------------------------------------------------
