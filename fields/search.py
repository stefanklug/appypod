# ------------------------------------------------------------------------------
# This file is part of Appy, a framework for building applications in the Python
# language. Copyright (C) 2007 Gaetan Delannay

# Appy is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

# Appy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# Appy. If not, see <http://www.gnu.org/licenses/>.

# ------------------------------------------------------------------------------
from appy.px import Px
from appy.gen import utils as gutils
from appy.gen.indexer import defaultIndexes
from appy.shared import utils as sutils
from group import Group

# ------------------------------------------------------------------------------
class Search:
    '''Used for specifying a search for a given class.'''

    def __init__(self, name=None, group=None, sortBy='', sortOrder='asc',
                 maxPerPage=30, default=False, colspan=1, translated=None,
                 show=True, showActions=True, translatedDescr=None,
                 checkboxes=False, checkboxesDefault=True, **fields):
        # "name" is mandatory, excepted in some special cases (ie, when used as
        # "select" param for a Ref field).
        self.name = name
        # Searches may be visually grouped in the portlet.
        self.group = Group.get(group)
        self.sortBy = sortBy
        self.sortOrder = sortOrder
        self.maxPerPage = maxPerPage
        # If this search is the default one, it will be triggered by clicking
        # on main link.
        self.default = default
        self.colspan = colspan
        # If a translated name or description is already given here, we will
        # use it instead of trying to translate from labels.
        self.translated = translated
        self.translatedDescr = translatedDescr
        # Condition for showing or not this search
        self.show = show
        # Condition for showing or not actions on every result of this search.
        # Can be: True, False or "inline". If True, actions will appear in a
        # "div" tag, below the object title; if "inline", they will appear
        # besides it, producing a more compact list of results.
        self.showActions = showActions
        # In the dict below, keys are indexed field names or names of standard
        # indexes, and values are search values.
        self.fields = fields
        # Do we need to display checkboxes for every object of the query result?
        self.checkboxes = checkboxes
        # Default value for checkboxes
        self.checkboxesDefault = checkboxesDefault

    @staticmethod
    def getIndexName(name, klass, usage='search'):
        '''Gets the name of the Zope index that corresponds to p_name. Indexes
           can be used for searching (p_usage="search") or for sorting
           (usage="sort"). The method returns None if the field named
           p_name can't be used for p_usage.'''
        # Manage indexes that do not have a corresponding field
        if name == 'created': return 'Created'
        elif name == 'modified': return 'Modified'
        elif name in defaultIndexes: return name
        else:
            # Manage indexes corresponding to fields
            field = getattr(klass, name, None) 
            if field: return field.getIndexName(usage)

    @staticmethod
    def getSearchValue(fieldName, fieldValue, klass):
        '''Returns a transformed p_fieldValue for producing a valid search
           value as required for searching in the index corresponding to
           p_fieldName.'''
        field = getattr(klass, fieldName, None)
        if (field and (field.getIndexType() == 'TextIndex')) or \
           (fieldName == 'SearchableText'):
            # For TextIndex indexes. We must split p_fieldValue into keywords.
            res = gutils.Keywords(fieldValue).get()
        elif isinstance(fieldValue, basestring) and fieldValue.endswith('*'):
            v = fieldValue[:-1]
            # Warning: 'z' is higher than 'Z'!
            res = {'query':(v,v+'z'), 'range':'min:max'}
        elif type(fieldValue) in sutils.sequenceTypes:
            if fieldValue and isinstance(fieldValue[0], basestring):
                # We have a list of string values (ie: we need to
                # search v1 or v2 or...)
                res = fieldValue
            else:
                # We have a range of (int, float, DateTime...) values
                minv, maxv = fieldValue
                rangev = 'minmax'
                queryv = fieldValue
                if minv == None:
                    rangev = 'max'
                    queryv = maxv
                elif maxv == None:
                    rangev = 'min'
                    queryv = minv
                res = {'query':queryv, 'range':rangev}
        else:
            res = fieldValue
        return res

    def updateSearchCriteria(self, criteria, klass, advanced=False):
        '''This method updates dict p_criteria with all the search criteria
           corresponding to this Search instance. If p_advanced is True,
           p_criteria correspond to an advanced search, to be stored in the
           session: in this case we need to keep the Appy names for parameters
           sortBy and sortOrder (and not "resolve" them to Zope's sort_on and
           sort_order).'''
        # Put search criteria in p_criteria
        for name, value in self.fields.iteritems():
            # Management of searches restricted to objects linked through a
            # Ref field: not implemented yet.
            if name == '_ref': continue
            # Make the correspondence between the name of the field and the
            # name of the corresponding index, excepted if advanced is True: in
            # that case, the correspondence will be done later.
            if not advanced:
                indexName = Search.getIndexName(name, klass)
                # Express the field value in the way needed by the index
                criteria[indexName] = Search.getSearchValue(name, value, klass)
            else:
                criteria[name] = value
        # Add a sort order if specified
        if self.sortBy:
            c = criteria
            if not advanced:
                c['sort_on']=Search.getIndexName(self.sortBy,klass,usage='sort')
                c['sort_order']= (self.sortOrder=='desc') and 'reverse' or None
            else:
                c['sortBy'] = self.sortBy
                c['sortOrder'] = self.sortOrder

    def isShowable(self, klass, tool):
        '''Is this Search instance (defined in p_klass) showable?'''
        if self.show.__class__.__name__ == 'staticmethod':
            return gutils.callMethod(tool, self.show, klass=klass)
        return self.show

    def getSessionKey(self, className, full=True):
        '''Returns the name of the key, in the session, where results for this
           search are stored when relevant. If p_full is False, only the suffix
           of the session key is returned (ie, without the leading
           "search_").'''
        res = (self.name == 'allSearch') and className or self.name
        if not full: return res
        return 'search_%s' % res

class UiSearch:
    '''Instances of this class are generated on-the-fly for manipulating a
       Search from the User Interface.'''
    # Default values for request parameters defining query sort and filter
    sortFilterDefaults = {'sortKey': '', 'sortOrder': 'asc',
                          'filterKey': '', 'filterValue': ''}
    pxByMode = {'list': 'pxResultList', 'grid': 'pxResultGrid'}

    # Rendering a search
    pxView = Px('''
     <div class="portletSearch">
      <a href=":'%s?className=%s&amp;search=%s' % \
                 (queryUrl, className, search.name)"
         class=":(search.name == currentSearch) and 'current' or ''"
         onclick="clickOn(this)"
         title=":search.translatedDescr">:search.translated</a>
     </div>''')

    # Search results, as a list (used by pxResult below)
    pxResultList = Px('''
     <table class="list" width="100%">
      <!-- Headers, with filters and sort arrows -->
      <tr if="showHeaders">
       <th if="checkboxes" class="cbCell" style=":'display:%s' % cbDisplay">
        <img src=":url('checkall')" class="clickable"
             title=":_('check_uncheck')"
             onclick=":'toggleAllCbs(%s)' % q(checkboxesId)"/>
       </th>
       <th for="column in columns"
           var2="field=column.field;
                 sortable=field.isSortable(usage='search');
                 filterable=field.filterable"
           width=":column.width" align=":column.align">
        <x>::ztool.truncateText(_(field.labelId))</x>
        <x if="(totalNumber &gt; 1) or filterValue">:tool.pxSortAndFilter</x>
        <x>:tool.pxShowDetails</x>
       </th>
      </tr>

      <!-- Results -->
      <tr if="not zobjects">
       <td colspan=":len(columns)+1">:_('query_no_result')</td>
      </tr>
      <x for="zobj in zobjects"
         var2="rowCss=loop.zobj.odd and 'even' or 'odd';
              @currentNumber=currentNumber + 1">:zobj.appy().pxViewAsResult</x>
     </table>
     <!-- The button for selecting objects and closing the popup -->
     <div if="inPopup and cbShown" align=":dleft">
      <input type="button"
             var="label=_('object_link_many'); css=ztool.getButtonCss(label)"
             value=":label" class=":css" style=":url('linkMany', bg=True)"
             onclick=":'onSelectObjects(%s,%s,%s,%s,%s,%s,%s)' % \
              (q(rootHookId), q(uiSearch.initiator.url), \
               q(uiSearch.initiatorMode), q(sortKey), q(sortOrder), \
               q(filterKey), q(filterValue))"/>
     </div>
     <!-- Init checkboxes if present -->
     <script if="checkboxes">:'initCbs(%s)' % q(checkboxesId)</script>
     <script>:'initFocus(%s)' % q(ajaxHookId)</script>''')

    # Search results, as a grid (used by pxResult below)
    pxResultGrid = Px('''
     <table width="100%"
            var="modeElems=resultMode.split('_');
                 cols=(len(modeElems)==2) and int(modeElems[1]) or 4;
                 rows=ztool.splitList(zobjects, cols)">
      <tr for="row in rows" valign="middle">
       <td for="zobj in row" width=":'%d%%' % (100/cols)" align="center"
           style="padding-top: 25px"
           var2="obj=zobj.appy(); mayView=zobj.mayView()">
        <x var="@currentNumber=currentNumber + 1"
           for="column in columns"
           var2="field=column.field">:field.pxRenderAsResult</x>
       </td>
      </tr>
     </table>''')

    # Render search results
    pxResult = Px('''
     <div var="ajaxHookId='queryResult';
               className=className|req['className'];
               klass=ztool.getAppyClass(className);
               searchName=field.name|req.get('search', '');
               uiSearch=field|ztool.getSearch(className, searchName, ui=True);
               resultMode=uiSearch.getResultMode(klass, req);
               customPx=resultMode not in uiSearch.pxByMode;
               maxResults=customPx and 'NO_LIMIT' or None;
               rootHookId=uiSearch.getRootHookId();
               refInfo=ztool.getRefInfo();
               refObject=refInfo[0];
               refField=refInfo[1];
               refUrlPart=refObject and ('&amp;ref=%s:%s' % (refObject.id, \
                                                             refField)) or '';
               startNumber=req.get('startNumber', '0');
               startNumber=int(startNumber);
               sortKey=req.get('sortKey', '');
               sortOrder=req.get('sortOrder', 'asc');
               filterKey=req.get('filterKey', '');
               filterValue=req.get('filterValue', '');
               queryResult=ztool.executeQuery(className, \
                 search=uiSearch.search, startNumber=startNumber, \
                 maxResults=maxResults, remember=True, sortBy=sortKey, \
                 sortOrder=sortOrder, filterKey=filterKey, \
                 filterValue=filterValue, refObject=refObject, \
                 refField=refField);
               zobjects=queryResult.objects;
               objects=maxResults and [z.appy() for z in zobjects];
               totalNumber=queryResult.totalNumber;
               batchSize=queryResult.batchSize;
               batchNumber=len(zobjects);
               showNewSearch=showNewSearch|True;
               newSearchUrl='%s/search?className=%s%s' % \
                   (ztool.absolute_url(), className, refUrlPart);
               showSubTitles=req.get('showSubTitles', 'true') == 'true';
               target=ztool.getLinksTargetInfo(klass);
               showHeaders=showHeaders|True;
               checkboxes=uiSearch.search.checkboxes;
               checkboxesId=rootHookId + '_objs';
               cbShown=uiSearch.showCheckboxes();
               cbDisplay=cbShown and 'table-cell' or 'none'"
          id=":ajaxHookId">
      <script>:uiSearch.getAjaxData(ajaxHookId, ztool, popup=inPopup, \
               checkboxes=checkboxes, checkboxesId=checkboxesId, \
               cbDisplay=cbDisplay, startNumber=startNumber, \
               totalNumber=totalNumber)</script>

      <x if="zobjects or filterValue"> <!-- Pod templates -->
       <table var="fields=ztool.getResultPodFields(className);
                   layoutType='view'"
              if="not inPopup and zobjects and fields" align=":dright">
        <tr>
         <td var="zobj=zobjects[0]; obj=zobj.appy()"
             for="field in fields"
             class=":not loop.field.last and 'pod' or ''">:field.pxRender</td>
        </tr>
       </table>

       <!-- The title of the search -->
       <p if="not inPopup">
       <x>::uiSearch.translated</x> (<span class="discreet">:totalNumber</span>)
        <x if="showNewSearch and (searchName == 'customSearch')">&nbsp;&mdash;
         &nbsp;<i><a href=":newSearchUrl">:_('search_new')</a></i>
        </x>
       </p>
       <table width="100%">
        <tr valign="top">
         <!-- Search description -->
         <td if="uiSearch.translatedDescr">
          <span class="discreet">:uiSearch.translatedDescr</span><br/>
         </td>
         <!-- (Top) navigation -->
         <td if="not customPx"
             align=":dright" width="200px">:tool.pxNavigate</td>
        </tr>
       </table>

       <!-- Results -->
       <x var="columnLayouts=ztool.getResultColumnsLayouts(className, refInfo);
               columns=ztool.getColumnsSpecifiers(className,columnLayouts,dir);
               currentNumber=0"><x>:uiSearch.getPx(resultMode, klass)</x></x>

       <!-- (Bottom) navigation -->
       <x if="not customPx">:tool.pxNavigate</x>
      </x>

      <x if="not zobjects and not filterValue">
       <x>:_('query_no_result')</x>
       <x if="showNewSearch and (searchName == 'customSearch')"><br/>
        <i class="discreet"><a href=":newSearchUrl">:_('search_new')</a></i></x>
      </x>
    </div>''')

    def __init__(self, search, className, tool):
        self.search = search
        self.name = search.name
        self.type = 'search'
        self.colspan = search.colspan
        self.className = className
        # Property "display" of the div tag containing actions for every search
        # result.
        self.showActions = search.showActions
        if search.showActions == True: self.showActions = 'block'
        if search.translated:
            self.translated = search.translated
            self.translatedDescr = search.translatedDescr
        else:
            # The label may be specific in some special cases
            labelDescr = ''
            if search.name == 'allSearch':
                label = '%s_plural' % className
            elif search.name == 'customSearch':
                label = 'search_results'
            elif search.name == '_field_':
                label = None
            else:
                label = '%s_search_%s' % (className, search.name)
                labelDescr = label + '_descr'
            _ = tool.translate
            self.translated = label and _(label) or ''
            self.translatedDescr = labelDescr and _(labelDescr) or ''

    def setInitiator(self, initiator, field, mode):
        '''If the search is defined in an attribute Ref.select, we receive here
           the p_initiator object, its Ref p_field and the p_mode, that can be:
           - "repl" if the objects selected in the popup will replace already
                    tied objects;
           - "add"  if those objects will be added to the already tied ones.
           .'''
        self.initiator = initiator
        self.initiatorField = field
        self.initiatorMode = mode
        # "initiatorHook" is the ID of the initiator field's XHTML tag.
        self.initiatorHook = '%s_%s' % (initiator.uid, field.name)

    def getRootHookId(self):
        '''If an initiator field is there, return the initiator hook.
           Else, simply return the name of the search.'''
        return getattr(self, 'initiatorHook', self.name)

    def getAllResultModes(self, klass):
        '''How must we show the result? As a list, grid, or a custom px?'''
        return getattr(klass, 'resultModes', ('list',))

    def getResultMode(self, klass, req):
        '''Get the current result mode'''
        res = req.get('resultMode')
        if not res: res = self.getAllResultModes(klass)[0]
        return res

    def getPx(self, mode, klass):
        '''What is the PX to show, according to the current result p_mode?'''
        if mode in UiSearch.pxByMode:
            return getattr(UiSearch, UiSearch.pxByMode[mode])
        # It must be a custom PX on p_klass
        return getattr(klass, mode)

    def showCheckboxes(self):
        '''If checkboxes are enabled for this search (and if an initiator field
           is there), they must be visible only if the initiator field is
           multivalued. Indeed, if it is not the case, it has no sense to select
           multiple objects. But in this case, we still want checkboxes to be in
           the DOM because they store object UIDs.'''
        if not self.search.checkboxes: return
        return not self.initiator or self.initiatorField.isMultiValued()

    def getCbJsInit(self, hookId):
        '''Returns the code that creates JS data structures for storing the
           status of checkboxes for every result of this search.'''
        default = self.search.checkboxesDefault and 'unchecked' or 'checked'
        return '''var node=findNode(this, '%s');
                  node['_appy_objs_cbs'] = {};
                  node['_appy_objs_sem'] = '%s';''' % (hookId, default)

    def getAjaxData(self, hook, ztool, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to
           p_hook = the whole search result.'''
        # Complete params with default ones and optional filter/sort params. For
        # performing a complete Ajax request, "className" and "searcName" are
        # not needed because included in the PX name. But they are requested by
        # sub-Ajax queries at the row level.
        params['className'] = self.className
        params['searchName'] = params['search'] = self.name
        req = ztool.REQUEST
        for param, default in UiSearch.sortFilterDefaults.iteritems():
            params[param] = req.get(param, default)
        # Convert params into a JS dict
        params = sutils.getStringDict(params)
        px = '%s:%s:pxResult' % (self.className, self.name)
        return "new AjaxData('%s', '%s', %s, null, '%s')" % \
               (hook, px, params, ztool.absolute_url())

    def getAjaxDataRow(self, zobj, parentHook, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to
           p_hook = a row within the list of results.'''
        hook = zobj.id
        return "new AjaxData('%s', 'pxViewAsResultFromAjax', %s, '%s', '%s')"% \
               (hook, sutils.getStringDict(params), parentHook,
                zobj.absolute_url())

    def getModeText(self, mode, _):
        '''Gets the i18n text corresponding to p_mode'''
        if mode in UiSearch.pxByMode: return _('result_mode_%s' % mode)
        return _('custom_%s' % mode)
# ------------------------------------------------------------------------------
