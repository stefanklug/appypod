'''This package contains base classes for wrappers that hide to the Appy
   developer the real classes used by the underlying web framework.'''

# ------------------------------------------------------------------------------
import os, os.path, mimetypes
import appy.pod
from appy.gen import Field, Search, Ref, String, WorkflowAnonymous
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

    # --------------------------------------------------------------------------
    # Navigation-related PXs
    # --------------------------------------------------------------------------
    # Icon for hiding/showing details below the title.
    pxShowDetails = Px('''
     <img if="ztool.subTitleIsUsed(className) and (field.name == 'title')"
          class="clickable" src=":img('toggleDetails')"
          onclick="toggleSubTitles()"/>''')

    # Displays up/down arrows in a table header column for sorting a given
    # column. Requires variables "sortable", 'filterable' and 'field'.
    pxSortAndFilter = Px('''<x>
     <x if="sortable">
      <img if="(sortKey != field.name) or (sortOrder == 'desc')"
           onclick=":navBaseCall.replace('**v**', '0,%s,%s,%s' % \
                     (q(field.name), q('asc'), q(filterKey)))"
           src=":img('sortDown.gif')" class="clickable"/>
      <img if="(sortKey != field.name) or (sortOrder == 'asc')"
           onclick=":navBaseCall.replace('**v**', '0,%s,%s,%s' % \
                     (q(field.name), q('desc'), q(filterKey)))"
           src=":img('sortUp.gif')" class="clickable"/>
     </x>
     <x if="filterable">
      <input type="text" size="7" id=":'%s_%s' % (ajaxHookId, field.name)"
             value=":filterKey == field.name and filterValue or ''"/>
      <img onclick=":navBaseCall.replace('**v**', '0, %s,%s,%s' % \
                     (q(sortKey), q(sortOrder), q(field.name)))"
           src=":img('funnel')" class="clickable"/>
     </x></x>''')

    # Buttons for navigating among a list of elements: next,back,first,last...
    pxAppyNavigate = Px('''
     <div if="totalNumber &gt; batchSize" align=":dright">
      <table class="listNavigate"
             var="mustSortAndFilter=ajaxHookId == 'queryResult';
                  sortAndFilter=mustSortAndFilter and \
                    ',%s,%s,%s' % (q(sortKey),q(sortOrder),q(filterKey)) or ''">
       <tr valign="middle">
        <!-- Go to the first page -->
        <td if="(startNumber != 0) and (startNumber != batchSize)"><img
            class="clickable" src=":img('arrowLeftDouble')"
            title=":_('goto_first')"
            onClick=":navBaseCall.replace('**v**', '0'+sortAndFilter)"/></td>

        <!-- Go to the previous page -->
        <td var="sNumber=startNumber - batchSize" if="startNumber != 0"><img
            class="clickable" src=":img('arrowLeftSimple')"
            title=":_('goto_previous')"
            onClick="navBaseCall.replace('**v**', \
                                         str(sNumber)+sortAndFilter)"/></td>

        <!-- Explain which elements are currently shown -->
        <td class="discreet">&nbsp;
         <x>:startNumber + 1</x><img src=":img('to')"/>
         <x>:startNumber + len(objs)</x>&nbsp;<b>//</b>
         <x>:totalNumber</x>&nbsp;&nbsp;</td>

        <!-- Go to the next page -->
        <td var="sNumber=startNumber + batchSize"
            if="sNumber &lt; totalNumber"><img class="clickable"
            src=":img('arrowRightSimple')" title=":_('goto_next')"
            onClick=":navBaseCall.replace('**v**', \
                                          str(sNumber)+sortAndFilter)"/></td>

        <!-- Go to the last page -->
        <td var="lastPageIsIncomplete=totalNumber % batchSize;
                 nbOfCompletePages=totalNumber/batchSize;
                 nbOfCountedPages=lastPageIsIncomplete and \
                                  nbOfCompletePages or nbOfCompletePages-1;
                 sNumber= nbOfCountedPages * batchSize"
            if="(startNumber != sNumber) and \
                (startNumber != sNumber-batchSize)"><img class="clickable"
            src=":img('arrowRightDouble')" title=":_('goto_last')"
            onClick="navBaseCall.replace('**v**', \
                                         str(sNumber)+sortAndFilter)"/></td>
       </tr>
      </table>
     </div>''')

    # Buttons for going to next/previous elements if this one is among bunch of
    # referenced or searched objects. currentNumber starts with 1.
    pxObjectNavigate = Px('''
     <div if="req.get('nav', None)"
          var2="navInfo=ztool.getNavigationInfo();
                currentNumber=navInfo['currentNumber'];
                totalNumber=navInfo['totalNumber'];
                firstUrl=navInfo['firstUrl'];
                previousUrl=navInfo['previousUrl'];
                nextUrl=navInfo['nextUrl'];
                lastUrl=navInfo['lastUrl'];
                sourceUrl=navInfo['sourceUrl'];
                backText=navInfo['backText']">

      <!-- Go to the source URL (search or referred object) -->
      <a if="sourceUrl" href=":sourceUrl"><img
         var="gotoSource=_('goto_source');
              goBack=backText and ('%s - %s' % (backText, gotoSource)) \
                     or gotoSource"
         src=":img('gotoSource')" title=":goBack"/></a>

      <!-- Go to the first page -->
      <a if="firstUrl" href=":firstUrl"><img title=":_('goto_first')"
         src=":img('arrowLeftDouble')"/></a>

      <!-- Go to the previous page -->
      <a if="previousUrl" href=":previousUrl"><img title=":_('goto_previous')"
         src=":img('arrowLeftSimple')"/></a>

      <!-- Explain which element is currently shown -->
      <span class="discreet">&nbsp;
       <x>:currentNumber</x>&nbsp;<b>//</b>
       <x>:totalNumber</x>&nbsp;&nbsp;
      </span>

      <!-- Go to the next page -->
      <a if="nextUrl" href=":nextUrl"><img title=":_('goto_next')"
         src=":img('arrowRightSimple')"/></a>

      <!-- Go to the last page -->
      <a if="lastUrl" href=":lastUrl"><img title=":_('goto_last')"
         src=":img('arrowRightDouble')"/></a>
     </div>''')

    pxNavigationStrip = Px('''
     <table width="100%" class="navigate">
      <tr>
       <!-- Breadcrumb -->
       <td var="breadcrumb=contextObj.getBreadCrumb()" class="breadcrumb">
        <x for="bc in breadcrumb" var2="nb=loop.bc.nb">
         <img if="nb != 0" src=":img('to')"/>
         <!-- Display only the title of the current object -->
         <span if="nb == len(breadcrumb)-1">:bc['title']</span>
         <!-- Display a link for parent objects -->
         <a if="nb != len(breadcrumb)-1" href=":bc['url']">:bc['title']</a>
        </x>
       </td>
       <!-- Object navigation -->
       <td align=":dright">:self.pxObjectNavigate</td>
      </tr>
     </table>''')

    # --------------------------------------------------------------------------
    # PXs for graphical elements shown on every page
    # --------------------------------------------------------------------------
    # Global elements included in every page.
    pxPagePrologue = Px('''<x>
     <!-- Include type-specific CSS and JS. -->
     <x if="cssJs">
      <link for="cssFile in cssJs['css']" rel="stylesheet" type="text/css"
            href=":'%s/ui/%s' % (appUrl, cssFile)"/>
      <script for="jsFile in cssJs['js']" type="text/javascript"
              src=":'%s/ui/%s' % (appUrl, jsFile)"></script></x>

     <!-- Javascript messages -->
     <script type="text/javascript">:ztool.getJavascriptMessages()</script>

     <!-- Global form for deleting an object -->
     <form id="deleteForm" method="post" action="do">
      <input type="hidden" name="action" value="Delete"/>
      <input type="hidden" name="objectUid"/>
     </form>
     <!-- Global form for deleting an event from an object's history -->
     <form id="deleteEventForm" method="post" action="do">
      <input type="hidden" name="action" value="DeleteEvent"/>
      <input type="hidden" name="objectUid"/>
      <input type="hidden" name="eventTime"/>
     </form>
     <!-- Global form for unlinking an object -->
     <form id="unlinkForm" method="post" action="do">
      <input type="hidden" name="action" value="Unlink"/>
      <input type="hidden" name="sourceUid"/>
      <input type="hidden" name="fieldName"/>
      <input type="hidden" name="targetUid"/>
     </form>
     <!-- Global form for unlocking a page -->
     <form id="unlockForm" method="post" action="do">
      <input type="hidden" name="action" value="Unlock"/>
      <input type="hidden" name="objectUid"/>
      <input type="hidden" name="pageName"/>
     </form>
     <!-- Global form for generating a document from a pod template -->
     <form id="podTemplateForm" name="podTemplateForm" method="post"
           action=":ztool.absolute_url() + '/generateDocument'">
      <input type="hidden" name="objectUid"/>
      <input type="hidden" name="fieldName"/>
      <input type="hidden" name="podFormat"/>
      <input type="hidden" name="askAction"/>
      <input type="hidden" name="queryData"/>
      <input type="hidden" name="customParams"/>
     </form>
    </x>''')

    pxPageBottom = Px('''
     <script type="text/javascript">initSlaves();</script>''')

    pxPortlet = Px('''
     <x var="toolUrl=tool.url;
             queryUrl='%s/ui/query' % toolUrl;
             currentSearch=req.get('search', None);
             currentClass=req.get('className', None);
             currentPage=req['PATH_INFO'].rsplit('/',1)[-1];
             rootClasses=ztool.getRootClasses();
             phases=contextObj and contextObj.getAppyPhases() or None">

      <table class="portletContent"
             if="contextObj and phases and contextObj.mayNavigate()"
             var2="singlePhase=phases and (len(phases) == 1);
                   page=req.get('page', '');
                   mayEdit=contextObj.mayEdit()">
       <x for="phase in phases">:phase['px']</x>
      </table>

      <!-- One section for every searchable root class -->
      <x for="rootClass in [rc for rc in rootClasses \
                            if ztool.userMaySearch(rc)]">

       <!-- A separator if required -->
       <div class="portletSep" var="nb=loop.rootClass.nb"
            if="(nb != 0) or ((nb == 0) and phases)"></div>

       <!-- Section title (link triggers the default search) -->
       <div class="portletContent"
            var="searchInfo=ztool.getGroupedSearches(rootClass)">
        <div class="portletTitle">
         <a var="queryParam=searchInfo['default'] and \
                            searchInfo['default']['name'] or ''"
            href=":'%s?className=%s&amp;search=%s' % \
                   (queryUrl,rootClass,queryParam)"
            class=":(not currentSearch and (currentClass==rootClass) and \
                    (currentPage=='query')) and \
                    'portletCurrent' or ''">::_(rootClass + '_plural')</a>
        </div>

        <!-- Actions -->
        <x var="addPermission='%s: Add %s' % (appName, rootClass);
                userMayAdd=user.has_permission(addPermission, appFolder);
                createMeans=ztool.getCreateMeans(rootClass)">

         <!-- Create a new object from a web form -->
         <input type="button" class="button"
                if="userMayAdd and ('form' in createMeans)"
                style=":img('buttonAdd', bg=True)" value=":_('query_create')"
                onclick=":'window.location=%s' % \
                  q('%s/do?action=Create&amp;className=%s' % \
                    (toolUrl, rootClass))"/>

         <!-- Create object(s) by importing data -->
         <input type="button" class="button"
                if="userMayAdd and ('import' in createMeans)"
                style=":img('buttonImport', bg=True)" value=":_('query_import')"
                onclick=":'window.location=%s' % \
                  q('%s/ui/import?className=%s' % (toolUrl, rootClass))"/>
        </x>

        <!-- Searches -->
        <x if="ztool.advancedSearchEnabledFor(rootClass)">

         <!-- Live search -->
         <form action=":'%s/config/do' % appUrl">
          <input type="hidden" name="action" value="SearchObjects"/>
          <input type="hidden" name="className" value=":rootClass"/>
          <table cellpadding="0" cellspacing="0">
           <tr valign="bottom">
            <td><input type="text" size="14" name="w_SearchableText"
                       class="inputSearch"/></td>
            <td>
             <input type="image" class="clickable" src=":img('search.gif')"
                    title=":_('search_button')"/></td>
           </tr>
          </table>
         </form>

         <!-- Advanced search -->
         <div var="highlighted=(currentClass == rootClass) and \
                               (currentPage == 'search')"
              class=":highlighted and 'portletSearch portletCurrent' or \
                     'portletSearch'"
              align=":dright">
          <a var="text=_('search_title')" style="font-size: 88%"
             href=":'%s/ui/search?className=%s' % (toolUrl, rootClass)"
             title=":text"><x>:text</x>...</a>
         </div>
        </x>

        <!-- Predefined searches -->
        <x for="widget in searchInfo['searches']">
         <x if="widget['type']=='group'">:widget['px']</x>
         <x if="widget['type']!='group'" var2="search=widget">:search['px']</x>
        </x>
       </div>
      </x>
     </x>''')

    # The message that is shown when a user triggers an action.
    pxMessage = Px('''
     <div var="messages=ztool.consumeMessages()" if="messages" class="message">
      <!-- The icon for closing the message -->
      <img src=":img('close')" align=":dright" class="clickable"
           onclick="this.parentNode.style.display='none'"/>
      <!-- The message content -->
      <x>::messages</x>
     </div>''')

    # The page footer.
    pxFooter = Px('''
     <table cellpadding="0" cellspacing="0" width="100%" class="footer">
      <tr>
       <td align=":dright">Made with
        <a href="http://appyframework.org" target="_blank">Appy</a></td></tr>
     </table>''')

    # Hook for defining a PX that proposes additional links, after the links
    # corresponding to top-level pages.
    pxLinks = ''

    # Hook for defining a PX that proposes additional icons after standard
    # icons in the user strip.
    pxIcons = ''

    # The template PX for all pages.
    pxTemplate = Px('''
     <html var="tool=self.tool; ztool=tool.o;   user=tool.user;
                isAnon=ztool.userIsAnon();      app=ztool.getApp();
                appUrl=app.absolute_url();      appFolder=app.data;
                appName=ztool.getAppName();     _=ztool.translate;
                req=ztool.REQUEST;              resp=req.RESPONSE;
                lang=ztool.getUserLanguage();   q=ztool.quote;
                img = ztool.getImageUrl;
                layoutType=ztool.getLayoutType();
                contextObj=ztool.getPublishedObject(layoutType) or \
                           ztool.getHomeObject();
                showPortlet=ztool.showPortlet(contextObj, layoutType);
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
         </div><br/>
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
                value=":_('object_cancel')"/>
        </div>
       </form>
      </div>

      <table class="main" align="center" cellpadding="0">
       <tr class="top">
        <!-- Top banner -->
        <td var="bannerName=(dir == 'ltr') and 'banner' or 'bannerrtl'"
            style=":img('%s.jpg' % bannerName, bg=True)">

         <!-- Top links -->
         <div style="margin-top: 4px" align=":dright">
          <!-- Icon "home" -->
          <a class="pageLink" href=":appUrl" title=": _('app_home')">
           <img src=":img('home.gif')" style="margin-right: 3px"/>
          </a>

          <!-- Additional links -->
          <x>:self.pxLinks</x>

          <!-- Top-level pages -->
          <a for="page in tool.pages" class="pageLink"
             href=":page.url">:page.title</a>

          <!-- Connect link if discreet login -->
          <a if="isAnon and discreetLogin" id="loginLink" name="loginLink"
             onclick="showLoginForm()" class="pageLink"
             class="clickable">:_('app_connect')</a>

          <!-- Language selector -->
          <select if="ztool.showLanguageSelector()"
                  var2="languages=ztool.getLanguages();
                       defaultLanguage=languages[0]"
                  class="pageLink" onchange="switchLanguage(this)"> 
           <option for="lg in languages" value=":lg"
                   selected=":lang == lg">:ztool.getLanguageName(lg)</option>
          </select>
         </div>
        </td>
       </tr>

       <!-- The message strip -->
       <tr valign="top">
        <td><div style="position: relative">:self.pxMessage</div></td>
       </tr>

       <!-- The user strip -->
       <tr>
        <td>
         <table class="userStrip" width="100%">
          <tr>
           <!-- The user login form for anonymous users -->
           <td align="center"
               if="isAnon and ('/temp_folder/' not in req['ACTUAL_URL'])">
            <form id="loginForm" name="loginForm" method="post" class="login"
                  action=":tool.url + '/performLogin'">
             <input type="hidden" name="js_enabled" id="js_enabled" value="0"/>
             <input type="hidden" name="cookies_enabled" id="cookies_enabled"
                    value=""/>
             <input type="hidden" name="login_name" id="login_name" value=""/>
             <input type="hidden" name="pwd_empty" id="pwd_empty" value="0"/>
             <!-- Login fields, directly shown or not (depends on
                  discreetLogin) -->
             <span id="loginFields" name="loginFields"
                   style=":discreetLogin and 'display:none' or 'display:block'">
              <span class="userStripText">:_('app_login')</span>
              <input type="text" name="__ac_name" id="__ac_name" value=""
                     style="width: 142px"/>&nbsp;
              <span class="userStripText">:_('app_password')</span>
              <input type="password" name="__ac_password" id="__ac_password"
                     style="width: 142px"/>
              <input type="submit" name="submit" onclick="setLoginVars()"
                     var="label=_('app_connect')" value=":label" alt=":label"/>
              <!-- Forgot password? -->
              <a if="ztool.showForgotPassword()"
                 href="javascript: openPopup('askPasswordReinitPopup')"
                 class="lostPassword">:_('forgot_password')</a>
             </span>
            </form>
           </td>

           <!-- User info and controls for authenticated users -->
           <td if="not isAnon">
            <table class="buttons" width="99%">
             <tr>
              <td>
               <!-- Config -->
               <a if="user.has_role('Manager')" href=":tool.url"
                  title=":_('%sTool' % appName)">
                <img src=":img('appyConfig.gif')"/></a>
               <!-- Additional icons -->
               <x>:self.pxIcons</x>
               <!-- Log out -->
               <a href=":tool.url + '/performLogout'" title=":_('app_logout')">
                <img src=":img('logout.gif')"/></a>
              </td>
              <td class="userStripText" var="userInfo=ztool.getUserLine()"
                  align=":dright">
               <span>:userInfo[0]</span>
               <a if="userInfo[1]"
                  href=":userInfo[1]"><img src=":img('edit')"/></a>
              </td>
             </tr>
            </table>
           </td>
          </tr>
         </table>
        </td>
       </tr>

       <!-- The navigation strip -->
       <tr if="contextObj and showPortlet and (layoutType != 'edit')">
        <td>:self.pxNavigationStrip</td>
       </tr>
       <tr>
        <td>
         <table width="100%" cellpadding="0" cellspacing="0">
          <tr valign="top">
           <!-- The portlet -->
           <td if="showPortlet" class="portlet">:self.pxPortlet</td>
           <!-- Page content -->
           <td class="content">:content</td>
          </tr>
         </table>
        </td>
       </tr>
       <!-- Footer -->
       <tr><td>:self.pxFooter</td></tr>
      </table>
     </body>
    </html>''', prologue=Px.xhtmlPrologue)

    # --------------------------------------------------------------------------
    # PXs for rendering graphical elements tied to a given object
    # --------------------------------------------------------------------------

    # This PX displays an object's history.
    pxObjectHistory = Px('''
     <x var="startNumber=req.get'startNumber', 0);
             startNumber=int(startNumber);
             batchSize=int(req.get('maxPerPage', 5));
             historyInfo=contextObj.getHistory(startNumber,batchSize=batchSize)"
        if="historyInfo['events']"
        var2="objs=historyInfo['events'];
              totalNumber=historyInfo['totalNumber'];
              ajaxHookId='appyHistory';
              navBaseCall='askObjectHistory(%s,%s,%d,**v**)' % \
                (q(ajaxHookId), q(contextObj.absolute_url()), batchSize)">

      <!-- Navigate between history pages -->
      <x>:self.pxAppyNavigate</x>
      <!-- History -->
      <table width="100%" class="history">
       <tr>
        <th align=":dleft">:_('object_action')</th>
        <th align=":dleft">:_('object_author')</th>
        <th align=":dleft">:_('action_date')</th>
        <th align=":dleft">:_('action_comment')</th>
       </tr>
       <tr for="event in objs"
           var2="odd=loop.event.odd;
                 rhComments=event.get('comments', None);
                 state=event.get('review_state', None);
                 action=event['action'];
                 isDataChange=action == '_datachange_'"
           class="odd and 'even' or 'odd'" valign="top">
        <td if="isDataChange">
         <x>:_('data_change')</x>
         <img if="user.has_role('Manager')" class="clickable"
              src=":img('delete')"
              onclick=":'onDeleteEvent(%s,%s)' % \
                        (q(contextObj.UID()), q(event['time']))"/>
        </td>
        <td if="not isDataChange">:_(contextObj.getWorkflowLabel(action))</td>
        <td var="actorId=event.get('actor')">
         <x if="not actorId">?</x>
         <x if="actorId">:ztool.getUserName(actorId)</x>
        </td>
        <td>:ztool.formatDate(event['time'], withHour=True)"></td>
        <td if="not isDataChange">
         <x if="rhComments">::contextObj.formatText(rhComments)</x>
         <x if="not rhComments">-</x>
        </td>
        <td if="isDataChange">
         <!-- Display the previous values of the fields whose value were
              modified in this change. -->
         <table class="appyChanges" width="100%">
          <tr>
           <th align=":dleft" width="30%">:_('modified_field')</th>
           <th align=":dleft" width="70%">:_('previous_value')</th>
          </tr>
          <tr for="change in event['changes'].items()" valign="top"
              var2="appyType=contextObj.getAppyType(change[0], asDict=True)">
           <td>::_(appyType['labelId'])</td>
           <td>::change[1][0]</td>
          </tr>
         </table>
        </td>
       </tr>
      </table>
     </x>''')

    # Displays an object's transitions(s).
    pxTransitions = Px('''
     <form var="transitions=targetObj.getAppyTransitions()" if="transitions"
           var2="formId='trigger_%s' % targetObj.UID()" method="post"
           id=":formId" action=":targetObj.absolute_url() + '/do'">
      <input type="hidden" name="action" value="Trigger"/>
      <input type="hidden" name="workflow_action"/>
      <table>
       <tr valign="middle">
        <!-- Input field for storing comment -->
        <textarea id="comment" name="comment" cols="30" rows="3"
                  style="display:none"></textarea>
        <!-- Buttons for triggering transitions -->
        <td align=":dright" for="transition in transitions">
         <!-- Real button -->
         <input type="button" class="button" if="transition['may_trigger']"
                style=":img('buttonTransition', bg=True)"
                title=":transition['title']"
                value=":ztool.truncateValue(transition['title'])"
                onclick=":'triggerTransition(%s,%s,%s)' % (q(formId), \
                  q(transition['name']), q(transition['confirm']))"/>

         <!-- Fake button, explaining why the transition can't be triggered -->
         <input type="button" class="button" if="not transition['may_trigger']"
                style=":img('buttonFake', bg=True) + ';cursor: help'"
                value=":ztool.truncateValue(transition['title'])"
                title=":'%s: %s' % (transition['title'], \
                                    transition['reason'])"/>
        </td>
       </tr>
      </table>
     </form>''')

    # Displays header information about an object: title, workflow-related info,
    # history...
    pxObjectHeader = Px('''
     <div if="not contextObj.isTemporary()"
          var2="hasHistory=contextObj.hasHistory();
                historyMaxPerPage=req.get('maxPerPage', 5);
                historyExpanded=req.get('appyHistory','collapsed') == 'expanded';
                creator=contextObj.Creator()">
      <table width="100%" class="summary">
       <tr>
        <td colspan="2" class="by">
         <!-- Plus/minus icon for accessing history -->
         <x if="hasHistory">
          <img class="clickable" onclick="toggleCookie('appyHistory')"
              src="historyExpanded and img('collapse.gif') or img('expand.gif')"
              align=":dleft" id="appyHistory_img"/>
          <x>:_('object_history')</x> || 
         </x>

         <!-- Creator and last modification date -->
         <x>:_('object_created_by')</x><x>:ztool.getUserName(creator)</x>
         
         <!-- Creation and last modification dates -->
         <x>:_('object_created_on')</x>
         <x var="creationDate=contextObj.Created();
                 modificationDate=contextObj.Modified()">
          <x>:ztool.formatDate(creationDate, withHour=True)></x>
          <x if="modificationDate != creationDate">&mdash;
           <x>:_('object_modified_on')</x>
           <x>:ztool.formatDate(modificationDate, withHour=True)</x>
          </x>
         </x>

         <!-- State -->
         <x if="contextObj.showState()">&mdash;
          <x>:_('workflow_state')</x> : <b>:_(contextObj.getWorkflowLabel())</b>
         </x>
        </td>
       </tr>

       <!-- Object history -->
       <tr if="hasHistory">
        <td colspan="2">
         <span id="appyHistory"
               style=":historyExpanded and 'display:block' or 'display:none')">
          <div var="ajaxHookId=contextObj.UID() + '_history'" id=":ajaxHookId">
           <script type="text/javascript">:'askObjectHistory(%s,%s,%d,0)' % \
             (q(ajaxHookId), q(contextObj.absolute_url()), \
              historyMaxPerPage)</script>
          </div>
         </span>
        </td>
       </tr>
      </table>
     </div>''')

    # Shows the range of buttons (next, previous, save,...) and the workflow
    # transitions.
    pxObjectButtons = Px('''
     <table cellpadding="2" cellspacing="0" style="margin-top: 7px"
            var="previousPage=contextObj.getPreviousPage(phaseInfo, page)[0];
                 nextPage=contextObj.getNextPage(phaseInfo, page)[0];
                 isEdit=layoutType == 'edit';
                 pageInfo=phaseInfo['pagesInfo'][page]">
      <tr>
       <!-- Previous -->
       <td if="previousPage and pageInfo['showPrevious']">
        <!-- Button on the edit page -->
        <x if="isEdit">
         <input type="button" class="button" value=":_('page_previous')"
                onClick="submitAppyForm('previous')"
                style=":img('buttonPrevious', bg=True)"/>
         <input type="hidden" name="previousPage" value=":previousPage"/>
        </x>
        <!-- Button on the view page -->
        <input if="not isEdit" type="button" class="button"
               value=":_('page_previous')"
               style=":img('buttonPrevious', bg=True)"
               onclick=":'window.location=%s' % \
                         q(contextObj.getUrl(page=previousPage))"/>
       </td>

       <!-- Save -->
       <td if="isEdit and pageInfo['showSave']">
        <input type="button" class="button" onClick="submitAppyForm('save')"
               style=":img(buttonSave', bg=True)" value=":_('object_save')"/>
       </td>

       <!-- Cancel -->
       <td if="isEdit and pageInfo['showCancel']">
        <input type="button" class="button" onClick="submitAppyForm('cancel')"
             style=":img('buttonCancel', bg=True)" value=":_('object_cancel')"/>
       </td>

       <td if="not isEdit"
           var2="locked=contextObj.isLocked(user, page);
                 editable=pageInfo['showOnEdit'] and contextObj.mayEdit()">

        <!-- Edit -->
        <input type="button" class="button" if="editable and not locked"
               style=":img('buttonEdit', bg=True)" value=":_('object_edit')"
               onclick=":'window.location=%s' % \
                         q(contextObj.getUrl(mode='edit', page=page))"/>

        <!-- Locked -->
        <a if="editable and locked">
         <img style="cursor: help"
              var="lockDate=tool.formatDate(locked[1]);
                   lockMap={'user':tool.getUserName(locked[0]),'date':lockDate};
                   lockMsg=_('page_locked', mapping=lockMap)"
              src=":img('lockedBig')" title=":lockMsg"/></a>
       </td>

       <!-- Next -->
       <td if="nextPage and pageInfo['showNext']">
        <!-- Button on the edit page -->
        <x if="isEdit">
         <input type="button" class="button" onClick="submitAppyForm('next')"
                style=":img('buttonNext', bg=True)" value=":_('page_next')"/>
         <input type="hidden" name="nextPage" value=":nextPage"/>
        </x>
        <!-- Button on the view page -->
        <input if="not isEdit" type="button" class="button"
               style=":img('buttonNext', bg=True)" value=":_('page_next')"
               onclick=":'window.location=%s' % \
                         q(contextObj.getUrl(page=nextPage))"/>
       </td>

       <!-- Workflow transitions -->
       <td var="targetObj=contextObj"
           if="targetObj.showTransitions(layoutType)">:self.pxTransitions</td>

       <!-- Refresh -->
       <td if="contextObj.isDebug()">
        <a href="contextObj.getUrl(mode=layoutType, page=page, refresh='yes')">
         <img title="Refresh" style="vertical-align:top" src=":img('refresh')"/>
        </a>
       </td>
      </tr>
     </table>''')

    pxLayoutedObject = Px('''<p>Layouted object</p>''')
    pxView = Px('''
     <x var="x=contextObj.allows('View', raiseError=True);
             errors=req.get('errors', {});
             layout=contextObj.getPageLayout(layoutType);
             phaseInfo=contextObj.getAppyPhases(currentOnly=True, \
                                                layoutType='view');
             phase=phaseInfo['name'];
             cssJs={};
             page=req.get('page',None) or contextObj.getDefaultViewPage();
             x=contextObj.removeMyLock(user, page);
             groupedWidgets=contextObj.getGroupedAppyTypes(layoutType, page, \
                                                           cssJs=cssJs)">
      <x>:self.pxPagePrologue</x>
      <x var="tagId='pageLayout'">:self.pxLayoutedObject</x>
      <x>:self.pxPageBottom</x>
     </x>''', template=pxTemplate, hook='content')

    pxEdit = Px('''
     <x var="x=contextObj.allows('Modify portal content', raiseError=True);
             errors=req.get('errors', None) or {};
             layout=contextObj.getPageLayout(layoutType);
             cssJs={};
             phaseInfo=contextObj.getAppyPhases(currentOnly=True, \
                                                layoutType=layoutType);
             phase=phaseInfo['name'];
             page=req.get('page', None) or contextObj.getDefaultEditPage();
             x=contextObj.setLock(user, page);
             confirmMsg=req.get('confirmMsg', None);
             groupedWidgets=contextObj.getGroupedAppyTypes(layoutType, page, \
                                                           cssJs=cssJs)">
      <x>:self.pxPagePrologue</x>
      <!-- Warn the user that the form should be left via buttons -->
      <script type="text/javascript"><![CDATA[
       window.onbeforeunload = function(e){
         theForm = document.getElementById('appyForm');
         if (theForm.button.value == "") {
           var e = e || window.event;
           if (e) {e.returnValue = warn_leave_form;}
           return warn_leave_form;
         }
       }]]>
      </script>
      <form id="appyForm" name="appyForm" method="post"
            enctype="multipart/form-data"
            action=":contextObj.absolute_url()+'/do'">
       <input type="hidden" name="action" value="Update"/>
       <input type="hidden" name="button" value=""/>
       <input type="hidden" name="page" value=":page"/>
       <input type="hidden" name="nav" value=":req.get('nav', None)"/>
       <input type="hidden" name="confirmed" value="False"/>
       <x var="tagId='pageLayout'">:self.pxLayoutedObject</x>
      </form>
      <script type="text/javascript"
              if="confirmMsg">:'askConfirm(%s,%s,%s)' % \
             (q('script'), q('postConfirmedEditForm()'), q(confirmMsg))</script>
      <x>:self.pxPageBottom</x>
     </x>''', template=pxTemplate, hook='content')

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
        if isinstance(res, Field):
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
