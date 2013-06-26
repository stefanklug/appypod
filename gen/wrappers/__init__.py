'''This package contains base classes for wrappers that hide to the Appy
   developer the real classes used by the underlying web framework.'''

# ------------------------------------------------------------------------------
import os, os.path, mimetypes
import appy.pod
from appy.gen import Type, Search, Ref, String, WorkflowAnonymous
from appy.gen.indexer import defaultIndexes
from appy.gen.utils import createObject
from appy.px import Px
from appy.shared.utils import getOsTempFolder, executeCommand, \
                              normalizeString, sequenceTypes
from appy.shared.xml_parser import XmlMarshaller
from appy.shared.csv_parser import CsvMarshaller

# Some error messages ----------------------------------------------------------
WRONG_FILE_TUPLE = 'This is not the way to set a file. You can specify a ' \
    '2-tuple (fileName, fileContent) or a 3-tuple (fileName, fileContent, ' \
    'mimeType).'
FREEZE_ERROR = 'Error while trying to freeze a "%s" file in POD field ' \
    '"%s" (%s).'
FREEZE_FATAL_ERROR = 'A server error occurred. Please contact the system ' \
    'administrator.'

# ------------------------------------------------------------------------------
class AbstractWrapper(object):
    '''Any real Appy-managed Zope object has a companion object that is an
       instance of this class.'''

    pxTemplate = Px('''
     <html var="tool=self.tool; ztool=tool.o;   user=tool.user;
                isAnon=ztool.userIsAnon();      app=ztool.getApp();
                appUrl=app.absolute_url();      appFolder=app.data;
                appName=ztool.getAppName();     _=ztool.translate;
                req=ztool.REQUEST;              resp=req.RESPONSE;
                lang=ztool.getUserLanguage();
                layoutType=ztool.getLayoutType();
                contextObj=ztool.getPublishedObject(layoutType);
                dir=ztool.getLanguageDirection(lang);
                discreetLogin=ztool.getAttr('discreetLogin', source='config');
                dleft=(dir == 'ltr') and 'left' or 'right';
                dright=(dir == 'ltr') and 'right' or 'left';
                x=resp.setHeader('Content-type', ztool.xhtmlEncoding);
                x=resp.setHeader('Expires', 'Thu, 11 Dec 1975 12:05:00 GMT+2');
                x=resp.setHeader('Content-Language', lang)"
           dir=":ztool.getLanguageDirection(lang)">
     <head>
      <title>:_('app_name')</title>
      <link rel="icon" type="image/x-icon" href="/favicon.ico"/>
      <x for="name in ztool.getGlobalCssJs()">
       <link if="name.endswith('.css') and \
                 not ((dir == 'ltr') and (name == 'appyrtl.css'))"
             rel="stylesheet" type="text/css"
             href=":'%s/ui/%s' % (appUrl, name)"/>
       <script if="name.endswith('.js')" type="text/javascript"
               src=":'%s/ui/%s' % (appUrl, name)"></script>
      </x>
     </head>
     <body>
      <!-- Google Analytics stuff, if enabled -->
      <script var="gaCode=ztool.getGoogleAnalyticsCode()" if="gaCode"
              type="text/javascript">:gaCode</script>

      <!-- Grey background shown when popups are shown -->
      <div id="grey" class="grey"></div>

      <!-- Popup for confirming an action -->
      <div id="confirmActionPopup" class="popup">
      <form id="confirmActionForm" method="post">
       <div align="center">
        <p id="appyConfirmText"></p>
        <input type="hidden" name="actionType"/>
        <input type="hidden" name="action"/>
        <div id="commentArea" align=":dleft"><br/>
         <span class="discreet">:_('workflow_comment')</span>
         <textarea name="comment" cols="30" rows="3"></textarea>
         <br/>
        </div>
        <br/>
        <input type="button" onclick="doConfirm()" value=":_('yes')"/>
        <input type="button" onclick="closePopup('confirmActionPopup')"
               value=":_('no')"/>
       </div>
      </form>
      </div>

      <!-- Popup for reinitializing the password -->
      <div id="askPasswordReinitPopup" class="popup"
           if="isAnon and ztool.showForgotPassword()">
      <form id="askPasswordReinitForm" method="post"
             action=":ztool.absolute_url() + '/askPasswordReinit'">
       <div align="center">
        <p>:_('app_login')</p>
        <input type="text" size="35" name="login" id="login" value=""/>
        <br/><br/>
        <input type="button" onclick="doAskPasswordReinit()"
               value=":_('ask_password_reinit')"/>
        <input type="button" onclick="closePopup('askPasswordReinitPopup')"
               value="_('object_cancel')"/>
       </div>
      </form>
      </div>

      <table class="main" align="center" cellpadding="0">
       <tr class="top">
        <!-- Top banner -->
        <td var="bannerName=(dir == 'ltr') and 'banner' or 'bannerrtl'"
            style=":'background-image: url(%s/ui/%s.jpg)'% (appUrl,bannerName)">

         <!-- Top links -->
         <div style="margin-top: 4px" align=":dright">
          <!-- Icon "home" -->
          <a class="pageLink" href=":appUrl" title=": _('app_home')">
           <img src=":'%s/ui/home.gif' % appUrl" style="margin-right: 3px"/>
          </a>
          <!-- Additional links (or icons) from icons.pt -->
          <!--metal:call use-macro="app/ui/icons/macros/links"/-->

          <!-- Top-level pages -->
          <a for="page in tool.pages" class="pageLink"
             href=":page.url">:page.title</a>

          <!-- Connect link if discreet login -->
          <a if="isAnon and discreetLogin" id="loginLink" name="loginLink"
             onclick="showLoginForm()" class="pageLink"
             style="cursor:pointer">:_('app_connect')</a>

          <!-- Language selector -->
          <x if="ztool.showLanguageSelector()">
           <select class="pageLink"
                   var="languages=ztool.getLanguages();
                        defaultLanguage=languages[0]"
                   onchange=":'window.location=&quot;%s/config/changeLanguage?language=&quot; + this.options[this.selectedIndex].value' % appUrl">
            <option for="lg in languages" value=":lg"
                    selected=":lang == lg">:ztool.getLanguageName(lg)</option>
           </select>
          </x>
         </div>
        </td>
       </tr>
     <!--tal:comment replace="nothing">The message strip</tal:comment>
     <tr valign="top">
      <td>
       <div style="position: relative">
        <metal:msg use-macro="app/ui/page/macros/message"/>
       </div>
      </td>
     </tr>
     <tal:comment replace="nothing">The user strip</tal:comment>
     <tr>
      <td>
       <table class="userStrip" width="100%">
        <tr>
         <tal:comment replace="nothing">The user login form for anonymous users</tal:comment>
         <td align="center"
             tal:condition="python: isAnon and ('/temp_folder/' not in req['ACTUAL_URL'])">
          <form id="loginForm" name="loginForm" method="post" class="login"
                tal:attributes="action python: tool.absolute_url() + '/performLogin'">
           <input type="hidden" name="js_enabled" id="js_enabled" value="0"/>
           <input type="hidden" name="cookies_enabled" id="cookies_enabled" value=""/>
           <input type="hidden" name="login_name" id="login_name" value=""/>
           <input type="hidden" name="pwd_empty" id="pwd_empty" value="0"/>
           <tal:comment replace="nothing">The login fields, directly shown or not (depends on discreetLogin)</tal:comment>
           <span id="loginFields" name="loginFields"
                 tal:attributes="style python: discreetLogin and 'display:none' or 'display:block'">
            <span class="userStripText" tal:content="python: _('app_login')"/>
            <input type="text" name="__ac_name" id="__ac_name" value="" style="width: 142px"/>&nbsp;
            <span class="userStripText" tal:content="python: _('app_password')"/>
            <input type="password" name="__ac_password" id="__ac_password" style="width: 142px"/>
            <input type="submit" name="submit" onclick="setLoginVars()"
                   tal:define="label python: _('app_connect')" tal:attributes="value label; alt label"/>
            <tal:comment replace="nothing">Forgot password?</tal:comment>
            <a class="lostPassword" href="javascript: openPopup('askPasswordReinitPopup')"
               tal:condition="tool/showForgotPassword"
               tal:content="python: _('forgot_password')">
            </a>
           </span>
          </form>
         </td>
         <tal:comment replace="nothing">User info and controls for authenticated users</tal:comment>
         <td tal:condition="not: isAnon">
          <table class="buttons" width="99%">
           <tr>
            <td>
             <tal:comment replace="nothing">Config</tal:comment>
             <a tal:condition="python: user.has_role('Manager')"
                tal:attributes="href python: tool.getUrl(nav='');
                                title python: _('%sTool' % appName)">
              <img tal:attributes="src string:$appUrl/ui/appyConfig.gif"/>
             </a>
             <tal:comment replace="nothing">Additional icons from icons.pt</tal:comment>
             <metal:call use-macro="app/ui/icons/macros/icons"/>
             <tal:comment replace="nothing">Log out</tal:comment>
             <a tal:attributes="href python: tool.absolute_url() + '/performLogout';
                                title python: _('app_logout')">
              <img tal:attributes="src string: $appUrl/ui/logout.gif"/>
             </a>
            </td>
            <td class="userStripText" tal:define="userInfo tool/getUserLine" tal:attributes="align dright">
              <span tal:content="python: userInfo[0]"></span>
              <a tal:condition="python: userInfo[1]"
                 tal:attributes="href python: userInfo[1]">
                <img tal:attributes="src string: $appUrl/ui/edit.png"/>
              </a>
            </td>
           </tr>
          </table>
         </td>
        </tr>
       </table>
      </td>
     </tr>
     <tal:comment replace="nothing">The navigation strip</tal:comment>
     <tr tal:condition="python: contextObj and (layoutType == 'view')">
      <td><metal:navigate use-macro="app/ui/navigate/macros/navigationStrip"/></td>
     </tr>
     <tr>
      <td>
        <table width="100%" cellpadding="0" cellspacing="0">
         <tr valign="top">
          <tal:comment replace="nothing">Portlet</tal:comment>
          <td tal:condition="python: tool.showPortlet(context, layoutType)" class="portlet">
            <metal:portlet use-macro="app/ui/portlet/macros/portlet"/>
          </td>
          <tal:comment replace="nothing">Page content</tal:comment>
          <td class="content"><span metal:define-slot="content"></span></td>
         </tr> 
        </table>
       </td> 
     </tr>
     <tr><tal:comment replace="nothing">Footer</tal:comment>
      <td><metal:call use-macro="app/ui/footer/macros/footer"/></td>
     </tr-->
    </table>
      <x>:content</x>
     </body>
    </html>
    ''', prologue=Px.xhtmlPrologue)

    # --------------------------------------------------------------------------
    # Class methods
    # --------------------------------------------------------------------------
    @classmethod
    def _getParentAttr(klass, attr):
        '''Gets value of p_attr on p_klass base classes (if this attr exists).
           Scan base classes in the reverse order as Python does. Used by
           classmethods m_getWorkflow and m_getCreators below. Scanning base
           classes in reverse order allows user-defined elements to override
           default Appy elements.'''
        i = len(klass.__bases__) - 1
        res = None
        while i >= 0:
            res = getattr(klass.__bases__[i], attr, None)
            if res: return res
            i -= 1

    @classmethod
    def getWorkflow(klass):
        '''Returns the workflow tied to p_klass.'''
        res = klass._getParentAttr('workflow')
        # Return a default workflow if no workflow was found.
        if not res: res = WorkflowAnonymous
        return res

    @classmethod
    def getCreators(klass, cfg):
        '''Returns the roles that are allowed to create instances of p_klass.
           p_cfg is the product config that holds the default value.'''
        res = klass._getParentAttr('creators')
        # Return default creators if no creators was found.
        if not res: res = cfg.defaultAddRoles
        return res

    @classmethod
    def getIndexes(klass, includeDefaults=True):
        '''Returns a dict whose keys are the names of the indexes that are
           applicable to instances of this class, and whose values are the
           (Zope) types of those indexes.'''
        # Start with the standard indexes applicable for any Appy class.
        if includeDefaults:
            res = defaultIndexes.copy()
        else:
            res = {}
        # Add the indexed fields found on this class
        for field in klass.__fields__:
            if not field.indexed or (field.name == 'title'): continue
            n = field.name
            indexName = 'get%s%s' % (n[0].upper(), n[1:])
            res[indexName] = field.getIndexType()
        return res

    # --------------------------------------------------------------------------
    # Instance methods
    # --------------------------------------------------------------------------
    def __init__(self, o): self.__dict__['o'] = o
    def appy(self): return self

    def __setattr__(self, name, value):
        appyType = self.o.getAppyType(name)
        if not appyType:
            raise 'Attribute "%s" does not exist.' % name
        appyType.store(self.o, value)

    def __getattribute__(self, name):
        '''Gets the attribute named p_name. Lot of cheating here.'''
        if name == 'o': return object.__getattribute__(self, name)
        elif name == 'tool': return self.o.getTool().appy()
        elif name == 'request':
            # The request may not be present, ie if we are at Zope startup.
            res = getattr(self.o, 'REQUEST', None)
            if res != None: return res
            return self.o.getProductConfig().fakeRequest
        elif name == 'session': return self.o.REQUEST.SESSION
        elif name == 'typeName': return self.__class__.__bases__[-1].__name__
        elif name == 'id': return self.o.id
        elif name == 'uid': return self.o.UID()
        elif name == 'klass': return self.__class__.__bases__[-1]
        elif name == 'created': return self.o.created
        elif name == 'modified': return self.o.modified
        elif name == 'url': return self.o.absolute_url()
        elif name == 'state': return self.o.State()
        elif name == 'stateLabel':
            return self.o.translate(self.o.getWorkflowLabel())
        elif name == 'history':
            o = self.o
            key = o.workflow_history.keys()[0]
            return o.workflow_history[key]
        elif name == 'user':
            return self.o.getUser()
        elif name == 'appyUser':
            user = self.search1('User', noSecurity=True,
                                login=self.o.getUser().getId())
            if user: return user
            if self.o.getUser().getUserName() == 'System Processes':
                return self.search1('User', noSecurity=True, login='admin')
            return
        elif name == 'fields': return self.o.getAllAppyTypes()
        elif name == 'siteUrl': return self.o.getTool().getSiteUrl()
        # Now, let's try to return a real attribute.
        res = object.__getattribute__(self, name)
        # If we got an Appy type, return the value of this type for this object
        if isinstance(res, Type):
            o = self.o
            if isinstance(res, Ref):
                return res.getValue(o, noListIfSingleObj=True)
            else:
                return res.getValue(o)
        return res

    def __repr__(self):
        return '<%s appyobj at %s>' % (self.klass.__name__, id(self))

    def __cmp__(self, other):
        if other: return cmp(self.o, other.o)
        return 1

    def _getCustomMethod(self, methodName):
        '''See docstring of _callCustom below.'''
        if len(self.__class__.__bases__) > 1:
            # There is a custom user class
            custom = self.__class__.__bases__[-1]
            if custom.__dict__.has_key(methodName):
                return custom.__dict__[methodName]

    def _callCustom(self, methodName, *args, **kwargs):
        '''This wrapper implements some methods like "validate" and "onEdit".
           If the user has defined its own wrapper, its methods will not be
           called. So this method allows, from the methods here, to call the
           user versions.'''
        custom = self._getCustomMethod(methodName)
        if custom: return custom(self, *args, **kwargs)

    def getField(self, name): return self.o.getAppyType(name)
    def isEmpty(self, name):
        '''Returns True if value of field p_name is considered as being
           empty.'''
        obj = self.o
        if hasattr(obj.aq_base, name):
            field = obj.getAppyType(name)
            return field.isEmptyValue(getattr(obj, name))
        return True

    def link(self, fieldName, obj):
        '''This method links p_obj (which can be a list of objects) to this one
           through reference field p_fieldName.'''
        return self.getField(fieldName).linkObject(self.o, obj)

    def unlink(self, fieldName, obj):
        '''This method unlinks p_obj (which can be a list of objects) from this
           one through reference field p_fieldName.'''
        return self.getField(fieldName).unlinkObject(self.o, obj)

    def sort(self, fieldName, sortKey='title', reverse=False):
        '''Sorts referred elements linked to p_self via p_fieldName according
           to a given p_sortKey which must be an attribute set on referred
           objects ("title", by default).'''
        refs = getattr(self.o, fieldName, None)
        if not refs: return
        tool = self.tool
        # refs is a PersistentList: param "key" is not available. So perform the
        # sort on the real list and then indicate that the persistent list has
        # changed (the ZODB way).
        refs.data.sort(key=lambda x: getattr(tool.getObject(x), sortKey),
                       reverse=reverse)
        refs._p_changed = 1

    def create(self, fieldNameOrClass, noSecurity=False, **kwargs):
        '''If p_fieldNameOrClass is the name of a field, this method allows to
           create an object and link it to the current one (self) through
           reference field named p_fieldName.
           If p_fieldNameOrClass is a class from the gen-application, it must
           correspond to a root class and this method allows to create a
           root object in the application folder.'''
        isField = isinstance(fieldNameOrClass, basestring)
        tool = self.tool.o
        # Determine the class of the object to create
        if isField:
            fieldName = fieldNameOrClass
            appyType = self.o.getAppyType(fieldName)
            portalType = tool.getPortalType(appyType.klass)
        else:
            klass = fieldNameOrClass
            portalType = tool.getPortalType(klass)
        # Determine object id
        if kwargs.has_key('id'):
            objId = kwargs['id']
            del kwargs['id']
        else:
            objId = tool.generateUid(portalType)
        # Determine if object must be created from external data
        externalData = None
        if kwargs.has_key('_data'):
            externalData = kwargs['_data']
            del kwargs['_data']
        # Where must I create the object?
        if not isField:
            folder = tool.getPath('/data')
        else:
            folder = self.o.getCreateFolder()
            if not noSecurity:
                # Check that the user can edit this field.
                appyType.checkAdd(self.o)
        # Create the object
        zopeObj = createObject(folder, objId, portalType, tool.getAppName(),
                               noSecurity=noSecurity)
        appyObj = zopeObj.appy()
        # Set object attributes
        for attrName, attrValue in kwargs.iteritems():
            setattr(appyObj, attrName, attrValue)
        if isField:
            # Link the object to this one
            appyType.linkObject(self.o, zopeObj)
        zopeObj._appy_managePermissions()
        # Call custom initialization
        if externalData: param = externalData
        else: param = True
        if hasattr(appyObj, 'onEdit'): appyObj.onEdit(param)
        zopeObj.reindex()
        return appyObj

    def freeze(self, fieldName, doAction=False):
        '''This method freezes a POD document. TODO: allow to freeze Computed
           fields.'''
        rq = self.request
        field = self.o.getAppyType(fieldName)
        if field.type != 'Pod': raise 'Cannot freeze non-Pod field.'
        # Perform the related action if required.
        if doAction: self.request.set('askAction', True)
        # Set the freeze format
        rq.set('podFormat', field.freezeFormat)
        # Generate the document.
        doc = field.getValue(self.o)
        if isinstance(doc, basestring):
            self.log(FREEZE_ERROR % (field.freezeFormat, field.name, doc),
                     type='error')
            if field.freezeFormat == 'odt': raise FREEZE_FATAL_ERROR
            self.log('Trying to freeze the ODT version...')
            # Try to freeze the ODT version of the document, which does not
            # require to call OpenOffice/LibreOffice, so the risk of error is
            # smaller.
            self.request.set('podFormat', 'odt')
            doc = field.getValue(self.o)
            if isinstance(doc, basestring):
                self.log(FREEZE_ERROR % ('odt', field.name, doc), type='error')
                raise FREEZE_FATAL_ERROR
        field.store(self.o, doc)

    def unFreeze(self, fieldName):
        '''This method un freezes a POD document. TODO: allow to unfreeze
           Computed fields.'''
        rq = self.request
        field = self.o.getAppyType(fieldName)
        if field.type != 'Pod': raise 'Cannot unFreeze non-Pod field.'
        field.store(self.o, None)

    def delete(self):
        '''Deletes myself.'''
        self.o.delete()

    def translate(self, label, mapping={}, domain=None, language=None,
                  format='html'):
        '''Check documentation of self.o.translate.'''
        return self.o.translate(label, mapping, domain, language=language,
                                format=format)

    def do(self, transition, comment='', doAction=True, doNotify=True,
           doHistory=True, noSecurity=False):
        '''This method allows to trigger on p_self a workflow p_transition
           programmatically. See doc in self.o.do.'''
        return self.o.trigger(transition, comment, doAction=doAction,
                              doNotify=doNotify, doHistory=doHistory,
                              doSay=False, noSecurity=noSecurity)

    def log(self, message, type='info'): return self.o.log(message, type)
    def say(self, message, type='info'): return self.o.say(message, type)

    def normalize(self, s, usage='fileName'):
        '''Returns a version of string p_s whose special chars have been
           replaced with normal chars.'''
        return normalizeString(s, usage)

    def search(self, klass, sortBy='', maxResults=None, noSecurity=False,
               **fields):
        '''Searches objects of p_klass. p_sortBy must be the name of an indexed
           field (declared with indexed=True); every param in p_fields must
           take the name of an indexed field and take a possible value of this
           field. You can optionally specify a maximum number of results in
           p_maxResults. If p_noSecurity is specified, you get all objects,
           even if the logged user does not have the permission to view it.'''
        # Find the content type corresponding to p_klass
        tool = self.tool.o
        contentType = tool.getPortalType(klass)
        # Create the Search object
        search = Search('customSearch', sortBy=sortBy, **fields)
        if not maxResults:
            maxResults = 'NO_LIMIT'
            # If I let maxResults=None, only a subset of the results will be
            # returned by method executeResult.
        res = tool.executeQuery(contentType, search=search,
                                maxResults=maxResults, noSecurity=noSecurity)
        return [o.appy() for o in res['objects']]

    def search1(self, *args, **kwargs):
        '''Identical to m_search above, but returns a single result (if any).'''
        res = self.search(*args, **kwargs)
        if res: return res[0]

    def count(self, klass, noSecurity=False, **fields):
        '''Identical to m_search above, but returns the number of objects that
           match the search instead of returning the objects themselves. Use
           this method instead of writing len(self.search(...)).'''
        tool = self.tool.o
        contentType = tool.getPortalType(klass)
        search = Search('customSearch', **fields)
        res = tool.executeQuery(contentType, search=search, brainsOnly=True,
                                noSecurity=noSecurity)
        if res: return res._len # It is a LazyMap instance
        else: return 0

    def countRefs(self, fieldName):
        '''Counts the number of objects linked to this one via Ref field
           p_fieldName.'''
        uids = getattr(self.o.aq_base, fieldName, None)
        if not uids: return 0
        return len(uids)

    def compute(self, klass, sortBy='', maxResults=None, context=None,
                expression=None, noSecurity=False, **fields):
        '''This method, like m_search and m_count above, performs a query on
           objects of p_klass. But in this case, instead of returning a list of
           matching objects (like m_search) or counting elements (like p_count),
           it evaluates, on every matching object, a Python p_expression (which
           may be an expression or a statement), and returns, if needed, a
           result. The result may be initialized through parameter p_context.
           p_expression is evaluated with 2 variables in its context: "obj"
           which is the currently walked object, instance of p_klass, and "ctx",
           which is the context as initialized (or not) by p_context. p_context
           may be used as
              (1) a variable or instance that is updated on every call to
                  produce a result;
              (2) an input variable or instance;
              (3) both.

           The method returns p_context, modified or not by evaluation of
           p_expression on every matching object.

           When you need to perform an action or computation on a lot of
           objects, use this method instead of doing things like
           
                    "for obj in self.search(MyClass,...)"
           '''
        tool = self.tool.o
        contentType = tool.getPortalType(klass)
        search = Search('customSearch', sortBy=sortBy, **fields)
        # Initialize the context variable "ctx"
        ctx = context
        for brain in tool.executeQuery(contentType, search=search, \
                 brainsOnly=True, maxResults=maxResults, noSecurity=noSecurity):
            # Get the Appy object from the brain
            if noSecurity: method = '_unrestrictedGetObject'
            else: method = 'getObject'
            exec 'obj = brain.%s().appy()' % method
            exec expression
        return ctx

    def reindex(self, fields=None, unindex=False):
        '''Asks a direct object reindexing. In most cases you don't have to
           reindex objects "manually" with this method. When an object is
           modified after some user action has been performed, Appy reindexes
           this object automatically. But if your code modifies other objects,
           Appy may not know that they must be reindexed, too. So use this
           method in those cases.
        '''
        if fields:
            # Get names of indexes from field names.
            indexes = [Search.getIndexName(name) for name in fields]
        else:
            indexes = None
        self.o.reindex(indexes=indexes, unindex=unindex)

    def export(self, at='string', format='xml', include=None, exclude=None):
        '''Creates an "exportable" version of this object. p_format is "xml" by
           default, but can also be "csv". If p_format is:
           * "xml", if p_at is "string", this method returns the XML version,
                    without the XML prologue. Else, (a) if not p_at, the XML
                    will be exported on disk, in the OS temp folder, with an
                    ugly name; (b) else, it will be exported at path p_at.
           * "csv", if p_at is "string", this method returns the CSV data as a
                    string. If p_at is an opened file handler, the CSV line will
                    be appended in it.
           If p_include is given, only fields whose names are in it will be
           included. p_exclude, if given, contains names of fields that will
           not be included in the result.
        '''
        if format == 'xml':
            # Todo: take p_include and p_exclude into account.
            # Determine where to put the result
            toDisk = (at != 'string')
            if toDisk and not at:
                at = getOsTempFolder() + '/' + self.o.UID() + '.xml'
            # Create the XML version of the object
            marshaller = XmlMarshaller(cdata=True, dumpUnicode=True,
                                       dumpXmlPrologue=toDisk,
                                       rootTag=self.klass.__name__)
            xml = marshaller.marshall(self.o, objectType='appy')
            # Produce the desired result
            if toDisk:
                f = file(at, 'w')
                f.write(xml.encode('utf-8'))
                f.close()
                return at
            else:
                return xml
        elif format == 'csv':
            if isinstance(at, basestring):
                marshaller = CsvMarshaller(include=include, exclude=exclude)
                return marshaller.marshall(self)
            else:
                marshaller = CsvMarshaller(at, include=include, exclude=exclude)
                marshaller.marshall(self)

    def historize(self, data):
        '''This method allows to add "manually" a "data-change" event into the
           object's history. Indeed, data changes are "automatically" recorded
           only when an object is edited through the edit form, not when a
           setter is called from the code.

           p_data must be a dictionary whose keys are field names (strings) and
           whose values are the previous field values.'''
        self.o.addDataChange(data)

    def formatText(self, text, format='html'):
        '''Produces a representation of p_text into the desired p_format, which
           is 'html' by default.'''
        return self.o.formatText(text, format)
# ------------------------------------------------------------------------------
