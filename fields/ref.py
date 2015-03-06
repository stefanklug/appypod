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
import sys, re, os.path
from appy import Object
from appy.fields import Field
from appy.fields.search import Search
from appy.px import Px
from appy.gen.layout import Table
from appy.gen import utils as gutils
from appy.shared import utils as sutils

# ------------------------------------------------------------------------------
class Ref(Field):
    # Some default layouts. "w" stands for "wide": those layouts produce tables
    # of Ref objects whose width is 100%.
    wLayouts = Table('lrv-f', width='100%')
    # "d" stands for "description": a description label is added
    wdLayouts = {'view': Table('l-d-f', width='100%')}

    # This PX displays the title of a referenced object, with a link on it to
    # reach the consult view for this object. If we are on a back reference, the
    # link allows to reach the correct page where the forward reference is
    # defined. If we are on a forward reference, the "nav" parameter is added to
    # the URL for allowing to navigate from one object to the next/previous one.
    pxObjectTitle = Px('''
     <x var="navInfo=field.getNavInfo(zobj, startNumber + currentNumber, \
                                      totalNumber, inPickList);
             pageName=field.isBack and field.back.pageName or 'main'">
      <x>::tied.o.getSupTitle(navInfo)</x>
      <x>::tied.o.getListTitle(nav=navInfo, target=target, page=pageName, \
                               inPopup=inPopup)</x>
      <span style=":showSubTitles and 'display:inline' or 'display:none'"
            name="subTitle" var="sub=tied.o.getSubTitle()" if="sub">::sub</span>
     </x>''')

    # This PX displays buttons for triggering global actions on several linked
    # objects (delete many, unlink many,...)
    pxGlobalActions = Px('''
     <div class="globalActions">
      <!-- Insert several objects (if in pick list) -->
      <input if="inPickList"
             var2="action='link'; label=_('object_link_many');
                   css=ztool.getButtonCss(label)"
             type="button" class=":css" value=":label"
             onclick=":'onLinkMany(%s,%s)' % (q(action), q(ajaxHookId))"
             style=":url('linkMany', bg=True)"/>
      <!-- Unlink several objects -->
      <input if="mayUnlink"
             var2="imgName=linkList and 'unlinkManyUp' or 'unlinkMany';
                   action='unlink'; label=_('object_unlink_many');
                   css=ztool.getButtonCss(label)"
             type="button" class=":css" value=":label"
             onclick=":'onLinkMany(%s,%s)' % (q(action), q(ajaxHookId))"
             style=":url(imgName, bg=True)"/>
      <!-- Delete several objects -->
      <input if="mayEdit and field.delete"
             var2="action='delete'; label=_('object_delete_many');
                   css=ztool.getButtonCss(label)"
             type="button" class=":css" value=":label"
             onclick=":'onLinkMany(%s,%s)' % (q(action), q(ajaxHookId))"
             style=":url('deleteMany', bg=True)"/>
     </div>''')

    # This PX displays icons for triggering actions on a given referenced object
    # (edit, delete, etc).
    pxObjectActions = Px('''
     <div if="field.showActions" class="objectActions"
          style=":'display:%s' % field.showActions" var2="layoutType='buttons'">
      <!-- Arrows for moving objects up or down -->
      <x if="(totalNumber &gt;1) and changeOrder and not inPickList \
            and not inMenu">
       <!-- Move to top -->
       <img if="objectIndex &gt; 1" class="clickable"
            src=":url('arrowsUp')" title=":_('move_top')"
            onclick=":'askBunchMove(%s, %s, %s, %s)' % \
                       (q(ajaxHookId), q(startNumber), q(tiedUid), q('top'))"/>
       <!-- Move to bottom -->
       <img if="objectIndex &lt; (totalNumber-2)" class="clickable"
            src=":url('arrowsDown')" title=":_('move_bottom')"
            onclick=":'askBunchMove(%s, %s, %s, %s)' % \
                     (q(ajaxHookId), q(startNumber), q(tiedUid), q('bottom'))"/>
       <!-- Move up -->
       <img if="objectIndex &gt; 0" class="clickable" src=":url('arrowUp')"
            title=":_('move_up')"
            onclick=":'askBunchMove(%s, %s, %s, %s)' % \
                       (q(ajaxHookId), q(startNumber), q(tiedUid), q('up'))"/>
       <!-- Move down -->
       <img if="objectIndex &lt; (totalNumber-1)" class="clickable"
            src=":url('arrowDown')" title=":_('move_down')"
            onclick=":'askBunchMove(%s, %s, %s, %s)' % \
                       (q(ajaxHookId), q(startNumber), q(tiedUid), q('down'))"/>
      </x>
      <!-- Edit -->
      <a if="not field.noForm and tied.o.mayEdit()"
         var2="navInfo=field.getNavInfo(zobj, startNumber + currentNumber, \
                                        totalNumber);
               linkInPopup=inPopup or (target.target != '_self')"
         href=":tied.o.getUrl(mode='edit', page='main', nav=navInfo, \
                              inPopup=linkInPopup)"
         target=":target.target" onclick=":target.openPopup">
       <img src=":url('edit')" title=":_('object_edit')"/>
      </a>
      <!-- Delete -->
      <img var="mayDeleteViaField=inPickList and True or field.delete;
                back=(inMenu and (layoutType=='buttons')) and \
                     q(zobj.id) or 'null'"
           if="mayEdit and mayDeleteViaField and tied.o.mayDelete()"
           class="clickable" title=":_('object_delete')" src=":url('delete')"
           onclick=":'onDeleteObject(%s,%s)' % (q(tiedUid), back)"/>
      <!-- Unlink -->
      <img if="mayUnlink and field.mayUnlinkElement(obj, tied)"
           var2="imgName=linkList and 'unlinkUp' or 'unlink'; action='unlink'"
           class="clickable" title=":_('object_unlink')" src=":url(imgName)"
           onclick=":'onLink(%s,%s,%s,%s)' % (q(action), q(zobj.id), \
                      q(field.name), q(tiedUid))"/>
      <!-- Insert (if in pick list) -->
      <img if="inPickList" var2="action='link'" class="clickable"
           title=":_('object_link')" src=":url(action)"
           onclick=":'onLink(%s,%s,%s,%s)' % (q(action), q(zobj.id), \
                      q(field.name), q(tiedUid))"/>
      <!-- Workflow transitions -->
      <x if="tied.o.showTransitions('result')"
         var2="targetObj=tied.o">:tied.pxTransitions</x>
      <!-- Fields (actions) defined with layout "buttons" -->
      <x if="not inPopup"
         var2="fields=tied.o.getAppyTypes('buttons', 'main');
               layoutType='cell';
               zobj=tied.o">
       <!-- Call pxCell and not pxRender to avoid having a table -->
       <x for="field in fields"
          var2="name=field.name; smallButtons=True">:field.pxCell</x>
      </x>
     </div>''')

    # Displays the button allowing to add a new object through a Ref field, if
    # it has been declared as addable and if multiplicities allow it.
    pxAdd = Px('''
     <form if="mayAdd and not inPickList"
           class=":inMenu and 'addFormMenu' or 'addForm'"
           var2="formName='%s_%s_add' % (zobj.id, field.name)"
           name=":formName" id=":formName" target=":target.target"
           action=":'%s/do' % folder.absolute_url()">
      <input type="hidden" name="action" value="Create"/>
      <input type="hidden" name="className" value=":tiedClassName"/>
      <input type="hidden" name="nav"
             value=":field.getNavInfo(zobj, 0, totalNumber)"/>
      <input type="hidden" name="popup"
             value=":(inPopup or (target.target != '_self')) and '1' or '0'"/>
      <input
       type=":(field.addConfirm or field.noForm) and 'button' or 'submit'"
       var="addLabel=_('add_ref');
            label=inMenu and tiedClassLabel or addLabel;
            css=ztool.getButtonCss(label)" class=":css"
       value=":label" style=":url('add', bg=True)" title=":addLabel"
       onclick=":field.getOnAdd(q, formName, addConfirmMsg, target, \
                                ajaxHookId, startNumber)"/>
     </form>''')

    # Displays the button allowing to select from a popup objects to be linked
    # via the Ref field.
    pxLink = Px('''
     <a target="appyIFrame"
        var="tiedClassName=tiedClassName|ztool.getPortalType(field.klass);
             className=ztool.getPortalType(obj.klass)"
        href=":'%s/query?className=%s&amp;search=%s*%s*%s&amp;popup=1' % \
               (ztool.absolute_url(), tiedClassName, obj.uid, field.name, \
                popupMode)">
      <input type="button"
             var="labelId= (popupMode=='repl') and 'search_button' or 'add_ref';
                  icon= (popupMode=='repl') and 'search' or 'add';
                  label=_(labelId);
                  css=ztool.getButtonCss(label)"
             value=":label" class=":css"
             style=":url(icon, bg=True)" onclick="openPopup('iframePopup')"/>
     </a>''')

    # This PX displays, in a cell header from a ref table, icons for sorting the
    # ref field according to the field that corresponds to this column.
    pxSortIcons = Px('''
     <x if="changeOrder and (len(objects) &gt; 1) and \
            refField.isSortable(usage='ref')">
      <img class="clickable" src=":url('sortAsc')"
           var="js='askBunchSortRef(%s, %s, %s, %s)' % \
                  (q(ajaxHookId), q(startNumber), q(refField.name), q('False'))"
           onclick=":'askConfirm(%s,%s,%s)' % (q('script'), q(js,False), \
                                               q(sortConfirm))"/>
      <img class="clickable" src=":url('sortDesc')"
           var="js='askBunchSortRef(%s, %s, %s, %s)' % \
                  (q(ajaxHookId), q(startNumber), q(refField.name), q('True'))"
           onclick=":'askConfirm(%s,%s,%s)' % (q('script'), q(js,False), \
                                               q(sortConfirm))"/>
     </x>''')

    # Shows the object number in a numbered list of tied objects
    pxNumber = Px('''
     <x if="not changeNumber">:objectIndex+1</x>
     <div if="changeNumber" class="dropdownMenu"
          var2="id='%s_%d' % (ajaxHookId, objectIndex);
                dropdownId='%s_dd' % id;
                imgId='%s_img' % id;
                inputId='%s_v' % id"
          onmouseover=":'toggleDropdown(%s)' % q(dropdownId)"
          onmouseout=":'toggleDropdown(%s,%s)' % (q(dropdownId), q('none'))">
      <input type="text" size=":numberWidth" id=":inputId"
             value=":objectIndex+1" onclick="this.select()"
             onkeydown=":'if (event.keyCode==13) \
                              document.getElementById(%s).click()' % q(imgId)"/>
      <!-- The menu -->
      <div id=":dropdownId" class="dropdown">
       <img class="clickable" src=":url('move')" id=":imgId"
            title=":_('move_number')"
            onclick=":'askBunchMove(%s, %s, %s, this)' % \
                       (q(ajaxHookId), q(startNumber), q(tiedUid))"/>
      </div>
     </div>''')

    # PX that displays referred objects as a list
    pxViewList = Px('''
     <div id=":ajaxHookId">
      <div if="(layoutType == 'view') or mayAdd or mayLink"
           style="margin-bottom: 4px">
       <x if="field.collapsible and objects">:collapse.px</x>
       <span if="subLabel" class="discreet">:_(subLabel)</span>
       (<span class="discreet">:totalNumber</span>) 
       <x>:field.pxAdd</x>
       <!-- This button opens a popup for linking additional objects -->
       <x if="mayLink and not inPickList"
          var2="popupMode='add'">:field.pxLink</x>
       <!-- The search button if field is queryable -->
       <input if="objects and field.queryable" type="button"
              var2="label=_('search_button'); css=ztool.getButtonCss(label)"
              value=":label" class=":css" style=":url('search', bg=True)"
              onclick=":'goto(%s)' % \
               q('%s/search?className=%s&amp;ref=%s:%s' % \
               (ztool.absolute_url(), tiedClassName, zobj.id, field.name))"/>
      </div>
      <script>:field.getAjaxData(ajaxHookId, zobj, popup=inPopup, \
        checkboxes=checkboxes, startNumber=startNumber, sourceId=zobj.id, \
        totalNumber=totalNumber, refFieldName=field.name, \
        inPickList=inPickList, numbered=numbered)</script>

      <!-- (Top) navigation -->
      <x>:tool.pxNavigate</x>

      <!-- No object is present -->
      <p class="discreet" if="not objects and mayAdd">:_('no_ref')</p>

      <!-- Linked objects -->
      <table if="objects" id=":collapse.id" style=":collapse.style" class="list"
             width=":field.layouts['view'].width"
             var2="columns=ztool.getColumnsSpecifiers(tiedClassName, \
                    field.getAttribute(obj, 'shownInfo'), dir);
                   currentNumber=0">

       <tr if="field.showHeaders">
        <th if="not inPickList and numbered" width=":numbered"></th>
        <th if="checkboxes" class="cbCell">
         <img src=":url('checkall')" class="clickable"
              title=":_('check_uncheck')"
              onclick=":'toggleAllCbs(%s)' % q(ajaxHookId)"/>
        </th>
        <th for="column in columns" width=":column.width"
            align=":column.align" var2="refField=column.field">
         <span>:_(refField.labelId)</span>
         <x>:field.pxSortIcons</x>
         <x var="className=tiedClassName;
                 field=refField">:tool.pxShowDetails</x>
        </th>
       </tr>
       <!-- Loop on every (tied or selectable) object -->
       <x for="tied in objects"
          var2="@currentNumber=currentNumber + 1;
                rowCss=loop.tied.odd and 'even' or 'odd'">:tied.pxViewAsTied</x>
      </table>
      <!-- Global actions -->
      <x if="mayEdit and checkboxes">:field.pxGlobalActions</x>
      <!-- (Bottom) navigation -->
      <x>:tool.pxNavigate</x>
      <!-- Init checkboxes if present -->
      <script if="checkboxes">:'initCbs(%s)' % q(ajaxHookId)</script>
     </div>''')

    # PX that displays referred objects as dropdown menus.
    pxMenu = Px('''
     <img if="menu.icon" src=":menu.icon" title=":menu.text"/><x
          if="not menu.icon">:menu.text</x>
     <!-- Nb of objects in the menu -->
     <x>:len(menu.objects)</x>''')

    pxViewMenus = Px('''
     <x var2="inMenu=True">
      <!-- One menu for every object type -->
      <div for="menu in field.getLinkedObjectsByMenu(obj, objects)"
           class="inline"
           style=":not loop.menu.last and 'padding-right:4px' or ''">
       <div class="dropdownMenu inline"
            var2="dropdownId='%s_%s_%d' % (zobj.id, name, loop.menu.nb);
                  singleObject=len(menu.objects) == 1"
            onmouseover=":'toggleDropdown(%s)' % q(dropdownId)"
            onmouseout=":'toggleDropdown(%s,%s)' % (q(dropdownId), q('none'))">

        <!-- The menu name and/or icon, that is clickable if there is a single
             object in the menu. -->
        <x if="singleObject" var2="tied=menu.objects[0]">
         <a if="field.menuUrlMethod" class="dropdownMenu"
            var2="info=field.getMenuUrl(zobj, tied)"
            href=":info[0]" target=":info[1]"
            title=":tied.o.getShownValue('title')">:field.pxMenu</a>
         <a if="not field.menuUrlMethod" class="dropdownMenu"
            var2="linkInPopup=inPopup or (target.target != '_self')"
            target=":target.target" onclick=":target.openPopup"
            href=":tied.o.getUrl(nav='',inPopup=linkInPopup)"
            title=":tied.o.getShownValue('title')">:field.pxMenu</a>
        </x>
        <x if="not singleObject">:field.pxMenu</x>

        <!-- The dropdown menu containing tied objects -->
        <div id=":dropdownId" class="dropdown" style="width:150px">
         <div for="tied in menu.objects"
              var2="startNumber=0;
                    totalNumber=len(menu.objects);
                    tiedUid=tied.uid"
              class=":not loop.tied.first and 'refMenuItem' or ''">
          <!-- A specific link may have to be computed from
               field.menuUrlMethod -->
          <a if="field.menuUrlMethod"
             var2="info=field.getMenuUrl(zobj, tied)"
             href=":info[0]" target=":info[1]">:tied.title</a>
          <!-- Show standard pxObjectTitle else -->
          <x if="not field.menuUrlMethod">:field.pxObjectTitle</x>
          <x if="tied.o.mayAct()">:field.pxObjectActions</x>
         </div>
        </div>
       </div>
      </div><x>:field.pxAdd</x></x> ''')

    # Simplified widget showing minimal info about tied objects.
    pxViewMinimal = Px('''
     <x var2="infos=[field.getReferenceLabel(obj, o, True) \
                     for o in objects]">:', '.join(infos) or _('no_ref')</x>''')

    # PX that displays referred objects through this field.
    # In mode link="list", if request key "scope" is:
    # - not in the request, the whole field is shown (both available and already
    #   tied objects);
    # - "objs", only tied objects are rendered;
    # - "poss", only available objects are rendered (the pick list).
    # ! scope is forced to "objs" on non-view "inner" (cell, buttons) layouts.
    pxView = Px('''
     <x var="layoutType=layoutType|'view';
             render=field.getRenderMode(layoutType);
             linkList=field.link == 'list';
             scope=(layoutType != 'view') and 'objs' or \
                   scope|req.get('scope', 'all');
             inPickList=(scope == 'poss');
             ajaxSuffix=inPickList and 'poss' or 'objs';
             ajaxHookId='%s_%s_%s' % (zobj.id, field.name, ajaxSuffix);
             inMenu=False;
             startNumber=field.getStartNumber(render, req, ajaxHookId);
             info=field.getViewValues(zobj, startNumber, scope);
             objects=info.objects;
             totalNumber=info.totalNumber;
             numberWidth=len(str(totalNumber));
             batchSize=info.batchSize;
             batchNumber=len(objects);
             folder=zobj.getCreateFolder();
             tiedClassName=ztool.getPortalType(field.klass);
             tiedClassLabel=_(tiedClassName);
             backHook=(layoutType == 'cell') and zobj.id or None;
             target=ztool.getLinksTargetInfo(field.klass, backHook);
             mayEdit=not field.isBack and zobj.mayEdit(field.writePermission);
             mayEd=not inPickList and mayEdit;
             mayAdd=mayEd and field.mayAdd(zobj, checkMayEdit=False);
             mayLink=mayEd and field.mayAdd(zobj, mode='link', \
                                            checkMayEdit=False);
             mayUnlink=mayEd and field.getAttribute(zobj, 'unlink');
             addConfirmMsg=field.addConfirm and \
                           _('%s_addConfirm' % field.labelId) or '';
             changeOrder=mayEd and field.getAttribute(zobj, 'changeOrder');
             sortConfirm=changeOrder and _('sort_confirm');
             numbered=not inPickList and field.isNumbered(zobj);
             gotoNumber=numbered;
             changeNumber=not inPickList and numbered and changeOrder and \
                          (totalNumber &gt; 3);
             checkboxesEnabled=(layoutType != 'cell') and \
                               field.getAttribute(zobj, 'checkboxes');
             checkboxes=checkboxesEnabled and (totalNumber &gt; 1);
             collapse=field.getCollapseInfo(obj, inPickList);
             showSubTitles=req.get('showSubTitles', 'true') == 'true'">
      <!-- JS tables storing checkbox statuses if checkboxes are enabled -->
      <script if="checkboxesEnabled and (render == 'list') and \
                  (scope == 'all')">:field.getCbJsInit(zobj)</script>
      <!-- The list of possible values, when relevant -->
      <x if="linkList and (scope == 'all') and mayEdit"
         var2="scope='poss'; layoutType='view'">:field.pxView</x>
      <!-- The list of tied or possible values, depending on scope -->
      <x if="render == 'list'"
         var2="subLabel=field.getListLabel(inPickList)">:field.pxViewList</x>
      <x if="render in ('menus','minimal')">:getattr(field, 'pxView%s' % \
         render.capitalize())</x>
     </x>''')

    pxCell = pxView

    # Edit widget, for Refs with link='popup'.
    pxEditPopup = Px('''
     <x var="objects=field.getPopupObjects(obj, req, requestValue)">
      <!-- The select field allowing to store the selected objects -->
      <select if="objects" name=":name" id=":name" multiple=":isMultiple"
              size=":isMultiple and field.height or ''">
       <option for="tied in objects" value=":tied.uid" selected="selected"
               var2="title=field.getReferenceLabel(obj, tied, unlimited=True)"
               title=":title">:ztool.truncateValue(title, field.width)</option>
      </select>
      <div if="not objects">-</div>
      <!-- The button for opening the popup -->
      <x var="popupMode='repl'">:field.pxLink</x></x>''')

    pxEdit = Px('''
     <x if="(field.link) and (field.link != 'list')">
      <select if="field.link != 'popup'"
              var2="objects=field.getPossibleValues(zobj);
                    uids=[o.id for o in field.getValue(zobj, appy=False)]"
              name=":name" id=":name" size=":isMultiple and field.height or ''"
              onchange=":field.getOnChange(zobj, layoutType)"
              multiple=":isMultiple">
       <option value="" if="not isMultiple">:_('choose_a_value')</option>
       <option for="tied in objects"
               var2="uid=tied.uid;
                     title=field.getReferenceLabel(obj, tied, unlimited=True)"
               selected=":inRequest and (uid in requestValue) or \
                                        (uid in uids)" value=":uid"
               title=":title">:ztool.truncateValue(title, field.width)</option>
      </select>
      <x if="field.link == 'popup'">:field.pxEditPopup</x></x>''')

    pxSearch = Px('''
     <!-- The "and" / "or" radio buttons -->
     <x if="field.multiplicity[1] != 1"
        var2="operName='o_%s' % name;
              orName='%s_or' % operName;
              andName='%s_and' % operName">
      <input type="radio" name=":operName" id=":orName" checked="checked"
             value="or"/>
      <label lfor=":orName">:_('search_or')</label>
      <input type="radio" name=":operName" id=":andName" value="and"/>
      <label lfor=":andName">:_('search_and')</label><br/>
     </x>
     <!-- The list of values -->
     <select var="objects=field.getPossibleValues(ztool);
                  selectAll='masterValues' in req"
             name=":widgetName" size=":field.sheight" multiple="multiple"
             onchange=":field.getOnChange(ztool, 'search', className)">
      <option for="tied in objects" value=":tied.uid" selected=":selectAll"
              var2="title=field.getReferenceLabel(obj, tied, unlimited=True)"
              title=":title">:ztool.truncateValue(title, field.swidth)</option>
     </select>''')

    def __init__(self, klass=None, attribute=None, validator=None,
                 multiplicity=(0,1), default=None, add=False, addConfirm=False,
                 delete=None, noForm=False, link=True, unlink=None,
                 unlinkElement=None, insert=None, beforeLink=None,
                 afterLink=None, afterUnlink=None, back=None, show=True,
                 page='main', group=None, layouts=None, showHeaders=False,
                 shownInfo=None, select=None, maxPerPage=30, move=0,
                 indexed=False, mustIndex=True, searchable=False,
                 specificReadPermission=False, specificWritePermission=False,
                 width=None, height=5, maxChars=None, colspan=1, master=None,
                 masterValue=None, focus=False, historized=False, mapping=None,
                 label=None, queryable=False, queryFields=None, queryNbCols=1,
                 navigable=False, changeOrder=True, numbered=False,
                 checkboxes=True, checkboxesDefault=None, sdefault='',
                 scolspan=1, swidth=None, sheight=None, sselect=None,
                 persist=True, render='list', menuIdMethod=None,
                 menuInfoMethod=None, menuUrlMethod=None, view=None, xml=None,
                 showActions=True, collapsible=False):
        self.klass = klass
        self.attribute = attribute
        # May the user add new objects through this ref ? "add" may also contain
        # a method whose result must be a boolean value.
        self.add = add
        # When the user adds a new object, must a confirmation popup be shown?
        self.addConfirm = addConfirm
        # May the user delete objects via this Ref?
        self.delete = delete
        if delete == None:
            # By default, one may delete objects via a Ref for which one can
            # add objects.
            self.delete = bool(self.add)
        # If noForm is True, when clicking to create an object through this ref,
        # the object will be created automatically, and no creation form will
        # be presented to the user.
        self.noForm = noForm
        # May the user link existing objects through this ref? If "link" is;
        # True,    the user will, on the edit page, choose objects from a
        #          dropdown menu;
        # "list",  the user will, on the view page, choose objects from a list
        #          of objects which is similar to those rendered in pxViewList;
        # "popup", the user will, on the edit page, choose objects from a popup
        #          menu. In this case, parameter "select" must hold a Search
        #          instance.
        self.link = link
        # May the user unlink existing objects?
        self.unlink = unlink
        if unlink == None:
            # By default, one may unlink objects via a Ref for which one can
            # link objects.
            self.unlink = bool(self.link)
        # "unlink" above is a global flag. If it is True, you can go further and
        # determine, for every linked object, if it can be unlinked or not by
        # defining a method in parameter "unlinkElement" below. This method
        # accepts the linked object as unique arg.
        self.unlinkElement = unlinkElement
        # When an object is inserted through this Ref field, at what position is
        # it inserted? If "insert" is:
        # None,     it will be inserted at the end;
        # "start",  it will be inserted at the start of the tied objects;
        # a method, (called with the object to insert as single arg), its return
        #           value (a number or a tuple of numbers) will be
        #           used to insert the object at the corresponding position
        #           (this method will also be applied to other objects to know
        #           where to insert the new one);
        # a tuple,  ('sort', method), the given method (called with the object
        #           to insert as single arg) will be used to sort tied objects
        #           and will be given as param "key" of the standard Python
        #           method "sort" applied on the list of tied objects.
        # With value ('sort', method), a full sort is performed and may hardly
        # reshake the tied objects; with value "method" alone, the tied
        # object is inserted at some given place: tied objects are more
        # maintained in the order of their insertion.
        self.insert = insert
        # Immediately before an object is going to be linked via this Ref field,
        # method potentially specified in "beforeLink" will be executed and will
        # take the object to link as single parameter.
        self.beforeLink = beforeLink
        # Immediately after an object has been linked via this Ref field, method
        # potentially specified in "afterLink" will be executed and will take
        # the linked object as single parameter.
        self.afterLink = afterLink
        # Immediately after an object as been unlinked from this Ref field,
        # method potentially specified in "afterUnlink" will be executed and
        # will take the unlinked object as single parameter.
        self.afterUnlink = afterUnlink
        self.back = None
        if back:
            # It is a forward reference
            self.isBack = False
            # Initialise the backward reference
            self.back = back
            back.back = self
            # klass may be None in the case we are defining an auto-Ref to the
            # same class as the class where this field is defined. In this case,
            # when defining the field within the class, write
            # myField = Ref(None, ...)
            # and, at the end of the class definition (name it K), write:
            # K.myField.klass = K
            # setattr(K, K.myField.back.attribute, K.myField.back)
            if klass: setattr(klass, back.attribute, back)
        else:
            self.isBack = True
        # When displaying a tabular list of referenced objects, must we show
        # the table headers?
        self.showHeaders = showHeaders
        # "shownInfo" is a tuple or list (or a method producing) containing
        # the names of the fields that will be shown when displaying tables of
        # tied objects. Field "title" should be present: by default it is a
        # clickable link to the "view" page of every tied object.
        if shownInfo == None:
            self.shownInfo = ['title']
        elif isinstance(shownInfo, tuple):
            self.shownInfo = list(shownInfo)
        else:
            self.shownInfo = shownInfo
        # If a method is defined in this field "select", it will be used to
        # return the list of possible tied objects. Be careful: this method can
        # receive, in its first argument ("self"), the tool instead of an
        # instance of the class where this field is defined. This little cheat
        # is:
        #  - not really a problem: in this method you will mainly use methods
        #    that are available on a tool as well as on any object (like
        #    "search");
        #  - necessary because in some cases we do not have an instance at our
        #    disposal, ie, when we need to compute a list of objects on a
        #    search screen.
        # "select" can also hold a Search instance. In this case, put any name
        # in Search's mandatory parameter "name": it will be ignored and
        # replaced with an internal technical name.
        # NOTE that when a method is defined in field "masterValue" (see parent
        # class "Field"), it will be used instead of select (or sselect below).
        self.select = select
        if isinstance(select, Search):
            select.name = '_field_'
            select.checkboxes = True
            select.checkboxesDefault = False
        # If you want to specify, for the search screen, a list of objects that
        # is different from the one produced by self.select, define an
        # alternative method in field "sselect" below.
        self.sselect = sselect or self.select
        # Maximum number of referenced objects shown at once.
        self.maxPerPage = maxPerPage
        # If param p_queryable is True, the user will be able to perform queries
        # from the UI within referenced objects.
        self.queryable = queryable
        # Here is the list of fields that will appear on the search screen.
        # If None is specified, by default we take every indexed field
        # defined on referenced objects' class.
        self.queryFields = queryFields
        # The search screen will have this number of columns
        self.queryNbCols = queryNbCols
        # Within the portlet, will referred elements appear ?
        self.navigable = navigable
        # If "changeOrder" is or returns False, it even if the user has the
        # right to modify the field, it will not be possible to move objects or
        # sort them.
        self.changeOrder = changeOrder
        # If "numbered" is or returns True, a leading column will show the
        # number of every tied object. Moreover, if the user can change order of
        # tied objects, an input field will allow him to enter a new number for
        # the tied object. If "numbered" is or returns a string, it will be used
        # as width for the column containing the number. Else, a default width
        # will be used.
        self.numbered = numbered
        # If "checkboxes" is or returns True, every linked object will be
        # "selectable" via a checkbox. Global actions will be activated and will
        # act on the subset of selected objects: delete, unlink, etc.
        self.checkboxes = checkboxes
        # Default value for checkboxes, if enabled.
        if checkboxesDefault == None:
            self.checkboxesDefault = bool(self.link)
        else:
            self.checkboxesDefault = checkboxesDefault
        # There are different ways to render a bunch of linked objects:
        # - "list" (the default) renders them as a list (=a XHTML table);
        # - "menus" renders them as a series of popup menus, grouped by type.
        # Note that render mode "menus" will only be applied in "cell" and
        # "buttons" layouts. Indeed, we need to keep the "list" rendering in
        # the "view" layout because the "menus" rendering is minimalist and does
        # not allow to perform all operations on linked objects (add, move,
        # delete, edit...);
        # - "minimal" renders a list of comma-separated, not-even-clickable,
        # data about the tied objects (according to shownInfo).
        self.render = render
        # If render is 'menus', 2 methods must be provided.
        # "menuIdMethod" will be called, with every linked object as single arg,
        # and must return an ID that identifies the menu into which the object
        # will be inserted.
        self.menuIdMethod = menuIdMethod
        # "menuInfoMethod" will be called with every collected menu ID (from
        # calls to the previous method) to get info about this menu. This info
        # must be a tuple (text, icon):
        # - "text" is the menu name;
        # - "icon" (can be None) gives the URL of an icon, if you want to render
        #   the menu as an icon instead of a text.
        self.menuInfoMethod = menuInfoMethod
        # "menuUrlMethod" is an optional method that allows to compute an
        # alternative URL for the tied object that is shown within the menu
        # (when render is "menus"). It can also be used with render being "list"
        # as well. The method can return a URL as a string, or, alternately, a
        # tuple (url, target), "target" being a string that will be used for
        # the "target" attribute of the corresponding XHTML "a" tag.
        self.menuUrlMethod = menuUrlMethod
        # "showActions" determines if we must show or not actions on every tied
        # object. Values can be: True, False or "inline". If True, actions will
        # appear in a "div" tag, below the object title; if "inline", they will
        # appear besides it, producing a more compact list of results.
        self.showActions = showActions
        # If "collapsible" is True, a "+/-" icon will allow to expand/collapse
        # the tied or available objects.
        self.collapsible = collapsible
        if showActions == True: self.showActions = 'block'
        # Call the base constructor
        Field.__init__(self, validator, multiplicity, default, show, page,
                       group, layouts, move, indexed, mustIndex, searchable,
                       specificReadPermission, specificWritePermission, width,
                       height, None, colspan, master, masterValue, focus,
                       historized, mapping, label, sdefault, scolspan, swidth,
                       sheight, persist, view, xml)
        self.validable = bool(self.link)
        self.checkParameters()

    def checkParameters(self):
        '''Ensures this Ref is correctly defined.'''
        # For forward Refs, "add" and "link" can't both be used.
        if not self.isBack and (self.add and self.link):
            raise Exception('Parameters "add" and "link" can\'t both be used.')
        # If link is "popup", "select" must hold a Search instance.
        if (self.link == 'popup') and not isinstance(self.select, Search):
            raise Exception('When "link" is "popup", "select" must be a ' \
                            'appy.fields.search.Search instance.')

    def getDefaultLayouts(self):
        return {'view': Table('l-f', width='100%'), 'edit': 'lrv-f'}

    def isShowable(self, obj, layoutType):
        res = Field.isShowable(self, obj, layoutType)
        if not res: return res
        # We add here specific Ref rules for preventing to show the field under
        # some inappropriate circumstances.
        if layoutType == 'edit':
            if self.mayAdd(obj): return
            if self.link in (False, 'list'): return
        if self.isBack:
            if layoutType == 'edit': return
            else: return getattr(obj.aq_base, self.name, None)
        return res

    def isRenderable(self, layoutType):
        '''Only Ref fields with render = "menus" can be rendered on "button"
           layouts.'''
        if layoutType == 'buttons': return self.render == 'menus'
        return True

    def getValue(self, obj, appy=True, noListIfSingleObj=False,
                 startNumber=None, someObjects=False):
        '''Returns the objects linked to p_obj through this Ref field. It
           returns Appy wrappers if p_appy is True, the Zope objects else.

           * If p_startNumber is None, it returns all referred objects;
           * if p_startNumber is a number, it returns self.maxPerPage objects,
             starting at p_startNumber.

           If p_noListIfSingleObj is True, it returns the single reference as
           an object and not as a list.

           If p_someObjects is True, it returns an instance of SomeObjects
           instead of returning a list of references.'''
        uids = getattr(obj.aq_base, self.name, [])
        if not uids:
            # Maybe is there a default value?
            defValue = Field.getValue(self, obj)
            if defValue:
                if type(defValue) in sutils.sequenceTypes:
                    uids = [o.o.id for o in defValue]
                else:
                    uids = [defValue.o.id]
        # Prepare the result: an instance of SomeObjects, that will be unwrapped
        # if not required.
        res = gutils.SomeObjects()
        res.totalNumber = res.batchSize = len(uids)
        batchNeeded = startNumber != None
        if batchNeeded:
            res.batchSize = self.maxPerPage
        if startNumber != None:
            res.startNumber = startNumber
        # Get the objects given their uids
        i = res.startNumber
        while i < (res.startNumber + res.batchSize):
            if i >= res.totalNumber: break
            # Retrieve every reference in the correct format according to p_type
            tied = obj.getTool().getObject(uids[i])
            if appy: tied = tied.appy()
            res.objects.append(tied)
            i += 1
        # Manage parameter p_noListIfSingleObj
        if res.objects and noListIfSingleObj:
            if self.multiplicity[1] == 1:
                res.objects = res.objects[0]
        if someObjects: return res
        return res.objects

    def getCopyValue(self, obj):
        '''Here, as "value ready-to-copy", we return the list of tied object
           UIDs, because m_store on the destination object can store tied
           objects based on such a list.''' 
        res = getattr(obj.aq_base, self.name, ())
        # Return a copy: it can be dangerous to give the real database value
        if res: return list(res)

    def getXmlValue(self, obj, value):
        '''The default XML value for a Ref is the list of tied object URLs.'''
        # Bypass the default behaviour if a custom method is given
        if self.xml: return self.xml(obj, value)
        return ['%s/xml' % tied.o.absolute_url() for tied in value]

    def getPossibleValues(self, obj, startNumber=None, someObjects=False,
                          removeLinked=False):
        '''This method returns the list of all objects that can be selected
           to be linked as references to p_obj via p_self. It is applicable only
           for Ref fields with link!=False. If master values are present in the
           request, we use field.masterValues method instead of self.select.

           If p_startNumber is a number, it returns self.maxPerPage objects,
           starting at p_startNumber. If p_someObjects is True, it returns an
           instance of SomeObjects instead of returning a list of objects.

           If p_removeLinked is True, we remove, from the result, objects which
           are already linked. For example, for Ref fields rendered as a
           dropdown menu or a multi-selection box (with link=True), on the edit
           page, we need to display all possible values: those that are already
           linked appear to be selected in the widget. But for Ref fields
           rendered as pick lists (link="list"), once an object is linked, it
           must disappear from the "pick list".
        '''
        req = obj.REQUEST
        obj = obj.appy()
        paginated = startNumber != None
        isSearch = False
        if 'masterValues' in req:
            # Convert masterValue(s) from id(s) to real object(s)
            masterValues = req['masterValues'].strip()
            if not masterValues: masterValues = None
            else:
                masterValues = masterValues.split('*')
                tool = obj.tool
                if len(masterValues) == 1:
                    masterValues = tool.getObject(masterValues[0])
                else:
                    masterValues = [tool.getObject(v) for v in masterValues]
            objects = self.masterValue(obj, masterValues)
        else:
            # If this field is an ajax-updatable slave, no need to compute
            # possible values: it will be overridden by method self.masterValue
            # by a subsequent ajax request (=the "if" statement above).
            if self.masterValue and callable(self.masterValue):
                objects = []
            else:
                if not self.select:
                    # No select method or search has been defined: we must
                    # retrieve all objects of the referred type that the user
                    # is allowed to access.
                    objects = obj.search(self.klass)
                else:
                    if isinstance(self.select, Search):
                        isSearch = True
                        maxResults = paginated and self.maxPerPage or 'NO_LIMIT'
                        start = startNumber or 0
                        className = obj.tool.o.getPortalType(self.klass)
                        objects = obj.o.executeQuery(className,
                            startNumber=start, search=self.select,
                            maxResults=maxResults)
                        objects.objects = [o.appy() for o in objects.objects]
                    else:
                        objects = self.select(obj)
        # Remove already linked objects if required
        if removeLinked:
            uids = getattr(obj.o.aq_base, self.name, None)
            if uids:
                # Browse objects in reverse order and remove linked objects
                if isSearch: objs = objects.objects
                else: objs = objects
                i = len(objs) - 1
                while i >= 0:
                    if objs[i].id in uids: del objs[i]
                    i -= 1
        # If possible values are not retrieved from a Search, restrict (if
        # required) the result to self.maxPerPage starting at p_startNumber.
        # Indeed, in this case, unlike m_getValue, we already have all objects
        # in "objects": we can't limit objects "waking up" to at most
        # self.maxPerPage.
        total = len(objects)
        if paginated and not isSearch:
            objects = objects[startNumber:startNumber + self.maxPerPage]
        # Return the result, wrapped in a SomeObjects instance if required
        if not someObjects:
            if isSearch: return objects.objects
            return objects
        if isSearch: return objects
        res = gutils.SomeObjects()
        res.totalNumber = total
        res.batchSize = self.maxPerPage
        res.startNumber = startNumber
        res.objects = objects
        return res

    def getViewValues(self, obj, startNumber, scope):
        '''Gets the values as must be shown on pxView. If p_scope is "poss", it
           is the list of possible, not-yet-linked, values. Else, it is the list
           of linked values. In both cases, we take the subset starting at
           p_startNumber.'''
        if scope == 'poss':
            return self.getPossibleValues(obj, startNumber=startNumber,
                                          someObjects=True, removeLinked=True)
        # Return the list of already linked values
        return self.getValue(obj, startNumber=startNumber, someObjects=True)

    def getLinkedObjectsByMenu(self, obj, objects):
        '''This method groups p_objects into sub-lists of objects, grouped by
           menu (happens when self.render == 'menus').'''
        if not objects: return ()
        res = []
        # We store in "menuIds" the already encountered menus:
        # ~{s_menuId : i_indexInRes}~
        menuIds = {}
        # Browse every object from p_objects and put them in their menu
        # (within "res").
        for tied in objects:
            menuId = self.menuIdMethod(obj, tied)
            if menuId in menuIds:
                # We have already encountered this menu
                menuIndex = menuIds[menuId]
                res[menuIndex].objects.append(tied)
            else:
                # A new menu
                menu = Object(id=menuId, objects=[tied])
                res.append(menu)
                menuIds[menuId] = len(res) - 1
        # Complete information about every menu by calling self.menuInfoMethod
        for menu in res:
            text, icon = self.menuInfoMethod(obj, menu.id)
            menu.text = text
            menu.icon = icon
        return res

    def isNumbered(self, obj):
        '''Must we show the order number of every tied object?'''
        res = self.getAttribute(obj, 'numbered')
        if not res: return res
        # Returns the column width.
        if not isinstance(res, basestring): return '15px'
        return res

    def getMenuUrl(self, zobj, tied):
        '''We must provide the URL of the p_tied object, when shown in a Ref
           field in render mode 'menus'. If self.menuUrlMethod is specified,
           use it. Else, returns the "normal" URL of the view page for the tied
           object, but without any navigation information, because in this
           render mode, tied object's order is lost and navigation is
           impossible.'''
        if self.menuUrlMethod:
            res = self.menuUrlMethod(zobj.appy(), tied)
            if isinstance(res, str): return res, '_self'
            return res
        return tied.o.getUrl(nav=''), '_self'

    def getStartNumber(self, render, req, hookId):
        '''This method returns the index of the first linked object that must be
           shown, or None if all linked objects must be shown at once (it
           happens when p_render is "menus").'''
        # When using 'menus' render mode, all linked objects must be shown
        if render == 'menus': return
        # When using 'list' (=default) render mode, the index of the first
        # object to show is in the request.
        key = '%s_startNumber' % hookId
        nb = req.has_key(key) and req[key] or req.get('startNumber', 0)
        return int(nb)

    def getFormattedValue(self, obj, value, layoutType='view',
                          showChanges=False, language=None):
        return value

    def getIndexType(self): return 'ListIndex'

    def getValidCatalogValue(self, value):
        '''p_value is the new value we want to index in the catalog, for this
           field, for some object. p_value as is may not be an acceptable value
           for the catalog: if it it an empty list, instead of using it, the
           catalog will keep the previously catalogued value! For this case,
           this method produces an "empty" value that will really overwrite the
           previous one. Moreover, the catalog does not like persistent
           lists.'''
        # The index does not like persistent lists. Moreover, I don't want to
        # give to anyone access to the persistent list in the DB.
        if value: return list(value)
        # Ugly catalog: if I return an empty list, the previous value is kept
        return ['']

    def getIndexValue(self, obj, forSearch=False):
        '''Value for indexing is the list of UIDs of linked objects. If
           p_forSearch is True, it will return a list of the linked objects'
           titles instead.'''
        # Must we produce an index value?
        if not self.getAttribute(obj, 'mustIndex'): return
        if not forSearch:
            res = getattr(obj.aq_base, self.name, None)
            return self.getValidCatalogValue(res)
        else:
            # For the global search: return linked objects' titles
            return ' '.join([o.getShownValue('title') \
                             for o in self.getValue(obj, appy=False)])

    def hasSortIndex(self):
        '''An indexed Ref field is of type "ListIndex", which is not sortable.
           So an additional FieldIndex is required.'''
        return True

    def validateValue(self, obj, value):
        if not self.link: return
        # We only check "link" Refs because in edit views, "add" Refs are
        # not visible. So if we check "add" Refs, on an "edit" view we will
        # believe that that there is no referred object even if there is.
        # Also ensure that multiplicities are enforced.
        if not value:
            nbOfRefs = 0
        elif isinstance(value, basestring):
            nbOfRefs = 1
        else:
            nbOfRefs = len(value)
        minRef = self.multiplicity[0]
        maxRef = self.multiplicity[1]
        if maxRef == None:
            maxRef = sys.maxint
        if nbOfRefs < minRef:
            return obj.translate('min_ref_violated')
        elif nbOfRefs > maxRef:
            return obj.translate('max_ref_violated')

    def linkObject(self, obj, value, back=False, noSecurity=True,
                   executeMethods=True):
        '''This method links p_value (which can be a list of objects) to p_obj
           through this Ref field. When linking 2 objects via a Ref,
           p_linkObject must be called twice: once on the forward Ref and once
           on the backward Ref. p_back indicates if we are calling it on the
           forward or backward Ref. If p_noSecurity is True, we bypass security
           checks (has the logged user the right to modify this Ref field?).
           If p_executeMethods is False, we do not execute methods that
           customize the object insertion (parameters insert, beforeLink,
           afterLink...). This can be useful while migrating data or duplicating
           an object.'''
        zobj = obj.o
        # Security check
        if not noSecurity: zobj.mayEdit(self.writePermission, raiseError=True)
        # p_value can be a list of objects
        if type(value) in sutils.sequenceTypes:
            for v in value:
                self.linkObject(obj, v, back, noSecurity, executeMethods)
            return
        # Gets the list of referred objects (=list of uids), or create it.
        refs = getattr(zobj.aq_base, self.name, None)
        if refs == None:
            refs = zobj.getProductConfig().PersistentList()
            setattr(zobj, self.name, refs)
        # Insert p_value into it
        uid = value.o.id
        if uid in refs: return
        # Execute self.beforeLink if present
        if executeMethods and self.beforeLink: self.beforeLink(obj, value)
        # Where must we insert the object?
        if not self.insert or not executeMethods:
            refs.append(uid)
        elif self.insert == 'start':
            refs.insert(0, uid)
        elif callable(self.insert):
            # It is a method. Use it on every tied object until we find where to
            # insert the new object.
            tool = zobj.getTool()
            insertOrder = self.insert(obj, value)
            i = 0
            inserted = False
            while i < len(refs):
                tied = tool.getObject(refs[i], appy=True)
                if self.insert(obj, tied) > insertOrder:
                    refs.insert(i, uid)
                    inserted = True
                    break
                i += 1
            if not inserted: refs.append(uid)
        else:
            # It is a tuple ('sort', method). Perform a full sort.
            refs.append(uid)
            tool = zobj.getTool()
            # Warning: "refs" is a persistent list whose method "sort" has no
            # param "key".
            refs.data.sort(key=lambda uid:self.insert[1](obj, \
                                                tool.getObject(uid, appy=True)))
            refs._p_changed = 1
        # Execute self.afterLink if present
        if executeMethods and self.afterLink: self.afterLink(obj, value)
        # Update the back reference
        if not back:
            self.back.linkObject(value, obj, True, noSecurity, executeMethods)

    def unlinkObject(self, obj, value, back=False, noSecurity=True,
                     executeMethods=True):
        '''This method unlinks p_value (which can be a list of objects) from
           p_obj through this Ref field. For an explanation about parameters
           p_back, p_noSecurity and p_executeMethods, check m_linkObject's doc
           above.'''
        zobj = obj.o
        # Security check
        if not noSecurity:
            zobj.mayEdit(self.writePermission, raiseError=True)
            if executeMethods:
                self.mayUnlinkElement(obj, value, raiseError=True)
        # p_value can be a list of objects
        if type(value) in sutils.sequenceTypes:
            for v in value:
                self.unlinkObject(obj, v, back, noSecurity, executeMethods)
            return
        refs = getattr(zobj.aq_base, self.name, None)
        if not refs: return
        # Unlink p_value
        uid = value.o.id
        if uid in refs:
            refs.remove(uid)
            # Execute self.afterUnlink if present
            if executeMethods and self.afterUnlink: self.afterUnlink(obj, value)
            # Update the back reference
            if not back:
                self.back.unlinkObject(value,obj,True,noSecurity,executeMethods)

    def store(self, obj, value):
        '''Stores on p_obj, the p_value, which can be:
           * None;
           * an object UID (=string);
           * a list of object UIDs (=list of strings). Generally, UIDs or lists
             of UIDs come from Ref fields with link:True edited through the web;
           * a Zope object;
           * a Appy object;
           * a list of Appy or Zope objects.'''
        if not self.persist: return
        # Standardize p_value into a list of Appy objects
        objects = value
        if not objects: objects = []
        if type(objects) not in sutils.sequenceTypes: objects = [objects]
        tool = obj.getTool()
        for i in range(len(objects)):
            if isinstance(objects[i], basestring):
                # We have an UID here
                objects[i] = tool.getObject(objects[i], appy=True)
            else:
                # Be sure to have an Appy object
                objects[i] = objects[i].appy()
        uids = [o.o.id for o in objects]
        appyObj = obj.appy()
        # Unlink objects that are not referred anymore
        refs = getattr(obj.aq_base, self.name, None)
        if refs:
            i = len(refs)-1
            while i >= 0:
                if refs[i] not in uids:
                    # Object having this UID must unlink p_obj
                    tied = tool.getObject(refs[i], appy=True)
                    self.back.unlinkObject(tied, appyObj)
                i -= 1
        # Link new objects
        if objects: self.linkObject(appyObj, objects)

    def mayAdd(self, obj, mode='create', checkMayEdit=True):
        '''May the user create (if p_mode == "create") or link
           (if mode == "link") (a) new referred object(s) from p_obj via this
           Ref? If p_checkMayEdit is False, it means that the condition of being
           allowed to edit this Ref field has already been checked somewhere
           else (it is always required, we just want to avoid checking it
           twice).'''
        # We can't (yet) do that on back references.
        if self.isBack: return gutils.No('is_back')
        # Check if this Ref is addable/linkable.
        if mode == 'create':
            add = self.getAttribute(obj, 'add')
            if not add: return gutils.No('no_add')
        elif mode == 'link':
            if (self.link != 'popup') or not self.isMultiValued(): return
        # Have we reached the maximum number of referred elements?
        if self.multiplicity[1] != None:
            refCount = len(getattr(obj, self.name, ()))
            if refCount >= self.multiplicity[1]: return gutils.No('max_reached')
        # May the user edit this Ref field?
        if checkMayEdit:
            if not obj.mayEdit(self.writePermission):
                return gutils.No('no_write_perm')
        # May the user create instances of the referred class?
        if mode == 'create':
            if not obj.getTool().userMayCreate(self.klass):
                return gutils.No('no_create_perm')
        return True

    def checkAdd(self, obj):
        '''Compute m_mayAdd above, and raise an Unauthorized exception if
           m_mayAdd returns False.'''
        may = self.mayAdd(obj)
        if not may:
            obj.raiseUnauthorized("User can't write Ref field '%s' (%s)." % \
                                  (self.name, may.msg))

    def getOnAdd(self, q, formName, addConfirmMsg, target, hookId, startNumber):
        '''Computes the JS code to execute when button "add" is clicked.'''
        if self.noForm:
            # Ajax-refresh the Ref with a special param to link a newly created
            # object.
            res = "askAjax('%s', null, {'startNumber':'%d', " \
                  "'action':'doCreateWithoutForm'})" % (hookId, startNumber)
            if self.addConfirm:
                res = "askConfirm('script', %s, %s)" % \
                      (q(res, False), q(addConfirmMsg))
        else:
            # In the basic case, no JS code is executed: target.openPopup is
            # empty and the button-related form is submitted in the main page.
            res = target.openPopup
            if self.addConfirm and not target.openPopup:
                res = "askConfirm('form','%s',%s)" % (formName,q(addConfirmMsg))
            elif self.addConfirm and target.openPopup:
                res = "askConfirm('form+script',%s,%s)" % \
                      (q(formName + '+' + target.openPopup, False), \
                       q(addConfirmMsg))
        return res

    def getAddLabel(self, obj, addLabel, tiedClassLabel, inMenu):
        '''Gets the label of the button allowing to add a new tied object. If
           p_inMenu, the label must contain the name of the class whose instance
           will be created by clincking on the button.'''
        if not inMenu: return obj.translate('add_ref')
        return tiedClassLabel

    def getListLabel(self, inPickList):
        '''If self.link == "list", a label must be shown in front of the list.
           Moreover, the label is different if the list is a pick list or the
           list of tied objects.'''
        if self.link != 'list': return
        return inPickList and 'selectable_objects' or 'selected_objects'

    def mayUnlinkElement(self, obj, tied, raiseError=False):
        '''May we unlink from this Ref field this specific p_tied object?'''
        if not self.unlinkElement: return True
        res = self.unlinkElement(obj, tied)
        if res: return True
        else:
            if not raiseError: return
            # Raise an exception.
            obj.o.raiseUnauthorized('field.unlinkElement prevents you to ' \
                                    'unlink this object.')

    def getCbJsInit(self, obj):
        '''When checkboxes are enabled, this method defines a JS associative
           array (named "_appy_objs_cbs") that will store checkboxes' statuses.
           This array is needed because all linked objects are not visible at
           the same time (pagination).

           Moreover, if self.link is "list", an additional array (named
           "_appy_poss_cbs") is defined for possible values.

           Semantics of this (those) array(s) can be as follows: if a key is
           present in it for a given linked object, it means that the
           checkbox is unchecked. In this case, all linked objects are selected
           by default. But the semantics can be inverted: presence of a key may
           mean that the checkbox is checked. The current array semantics is
           stored in a variable named "_appy_objs_sem" (or "_appy_poss_sem")
           and may hold "unchecked" (initial semantics) or "checked" (inverted
           semantics). Inverting semantics allows to keep the array small even
           when checking/unchecking all checkboxes.

           The mentioned JS arrays and variables are stored as attributes of the
           DOM node representing this field.'''
        # The initial semantics depends on the checkboxes default value.
        default = self.getAttribute(obj, 'checkboxesDefault') and \
                  'unchecked' or 'checked'
        code = "\nnode['_appy_%%s_cbs']={};\nnode['_appy_%%s_sem']='%s';" % \
               default
        poss = (self.link == 'list') and (code % ('poss', 'poss')) or ''
        return "var node=findNode(this, '%s_%s');%s%s" % \
               (obj.id, self.name, code % ('objs', 'objs'), poss)

    def getAjaxData(self, hook, zobj, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to this
           Ref field.'''
        # Complete params with default parameters
        params['ajaxHookId'] = hook;
        params['scope'] = hook.rsplit('_', 1)[-1]
        params = sutils.getStringDict(params)
        return "new AjaxData('%s', '%s:pxView', %s, null, '%s')" % \
               (hook, self.name, params, zobj.absolute_url())

    def getAjaxDataRow(self, obj, parentHook, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to
           p_hook = a row within the list of referred objects.'''
        hook = obj.id
        return "new AjaxData('%s', 'pxViewAsTiedFromAjax', %s, '%s', '%s')" % \
               (hook, sutils.getStringDict(params), parentHook, obj.url)

    def doChangeOrder(self, obj):
        '''Moves a referred object up/down/top/bottom.'''
        rq = obj.REQUEST
        # How to move the item?
        move = rq['move']
        # Get the UID of the tied object to move
        uid = rq['refObjectUid']
        uids = getattr(obj.aq_base, self.name)
        oldIndex = uids.index(uid)
        if move == 'up':
            newIndex = oldIndex - 1
        elif move == 'down':
            newIndex = oldIndex + 1
        elif move == 'top':
            newIndex = 0
        elif move == 'bottom':
            newIndex = len(uids) - 1
        elif move.startswith('index'):
            # New index starts at 1 (oldIndex starts at 0)
            try:
                newIndex = int(move.split('_')[1]) - 1
            except ValueError:
                newIndex = -1
        # If newIndex is negative, it means that the move can't occur
        if newIndex > -1:
            uids.remove(uid)
            uids.insert(newIndex, uid)

    def doCreateWithoutForm(self, obj):
        '''This method is called when a user wants to create a object from a
           reference field, automatically (without displaying a form).'''
        obj.appy().create(self.name)

    xhtmlToText = re.compile('<.*?>', re.S)
    def getReferenceLabel(self, obj, refObject, unlimited=False):
        '''p_self must have link=True. I need to display, on an edit view, the
           p_refObject in the listbox that will allow the user to choose which
           object(s) to link through the Ref. The information to display may
           only be the object title or more if "shownInfo" is used.'''
        res = ''
        for name in self.getAttribute(obj, 'shownInfo'):
            refType = refObject.o.getAppyType(name)
            value = getattr(refObject, name)
            value = refType.getShownValue(refObject.o, value)
            if refType.type == 'String':
                if refType.format == 2:
                    value = self.xhtmlToText.sub(' ', value)
                elif type(value) in sutils.sequenceTypes:
                    value = ', '.join(value)
            prefix = res and ' | ' or ''
            res += prefix + value
        if unlimited: return res
        maxWidth = self.width or 30
        if len(res) > maxWidth:
            res = refObject.tool.o.truncateValue(res, maxWidth)
        return res

    def getIndexOf(self, obj, tiedUid, raiseError=True):
        '''Gets the position of tied object identified by p_tiedUid within this
           field on p_obj.'''
        uids = getattr(obj.aq_base, self.name, None)
        if not uids:
            if raiseError: raise IndexError()
            else: return
        if tiedUid in uids:
            return uids.index(tiedUid)
        else:
            if raiseError: raise IndexError()
            else: return

    def sort(self, obj):
        '''Called when the user wants to sort the content of this field.'''
        rq = obj.REQUEST
        sortKey = rq.get('sortKey')
        reverse = rq.get('reverse') == 'True'
        obj.appy().sort(self.name, sortKey=sortKey, reverse=reverse)

    def getRenderMode(self, layoutType):
        '''Gets the render mode, determined by self.render and some
           exceptions.'''
        if (layoutType == 'view') and (self.render == 'menus'): return 'list'
        return self.render

    def getPopupObjects(self, obj, rq, requestValue):
        '''Gets the list of objects that were selected in the popup (for Ref
           fields with link="popup").'''
        if requestValue:
            # We are validating the form. Return the request value instead of
            # the popup value.
            tool = obj.tool
            if isinstance(requestValue, basestring):
                return [tool.getObject(requestValue)]
            else:
                return [tool.getObject(rv) for rv in requestValue]
        res = []
        # No object can be selected if the popup has not been opened yet
        if 'semantics' not in rq:
            # In this case, display already linked objects if any
            if not obj.isEmpty(self.name): return self.getValue(obj.o)
            return res
        uids = rq['selected'].split(',')
        tool = obj.tool
        if rq['semantics'] == 'checked':
            # Simply get the selected objects from their uid
            return [tool.getObject(uid) for uid in uids]
        else:
            # Replay the search in self.select to get the list of uids that were
            # shown in the popup.
            className = tool.o.getPortalType(self.klass)
            brains = obj.o.executeQuery(className, search=self.select,
                maxResults='NO_LIMIT', brainsOnly=True,
                sortBy=rq.get('sortKey'), sortOrder=rq.get('sortOrder'),
                filterKey=rq.get('filterKey'),filterValue=rq.get('filterValue'))
            queryUids = [os.path.basename(b.getPath()) for b in brains]
            for uid in queryUids:
                if uid not in uids:
                    res.append(tool.getObject(uid))
        return res

    def onSelectFromPopup(self, obj):
        '''This method is called on Ref fields with link="popup", when a user
           has selected objects from the popup, to be added to existing tied
           objects, from the view widget.'''
        obj = obj.appy()
        for tied in self.getPopupObjects(obj, obj.request, None):
            self.linkObject(obj, tied, noSecurity=False)

    def onUiRequest(self, obj, rq):
        '''This method is called when an action tied to this Ref field is
           triggered from the user interface (link, unlink, link_many,
           unlink_many, delete_many).'''
        action = rq['linkAction']
        tool = obj.getTool()
        msg = None
        appyObj = obj.appy()
        if not action.endswith('_many'):
            # "link" or "unlink"
            tied = tool.getObject(rq['targetUid'], appy=True)
            exec 'self.%sObject(appyObj, tied, noSecurity=False)' % action
        else:
            # "link_many", "unlink_many", "delete_many". As a preamble, perform
            # a security check once, instead of doing it on every object-level
            # operation.
            obj.mayEdit(self.writePermission, raiseError=True)
            # Get the (un-)checked objects from the request.
            uids = rq['targetUid'].split(',')
            unchecked = rq['semantics'] == 'unchecked'
            if action == 'link_many':
                # Get possible values (objects)
                values = self.getPossibleValues(obj, removeLinked=True)
                isObj = True
            else:
                # Get current values (uids)
                values = getattr(obj.aq_base, self.name, ())
                isObj = False
            # Collect the objects onto which the action must be performed.
            targets = []
            for value in values:
                uid = not isObj and value or value.uid
                if unchecked:
                    # Keep only objects not among uids.
                    if uid in uids: continue
                else:
                    # Keep only objects being in uids.
                    if uid not in uids: continue
                # Collect this object
                target = not isObj and tool.getObject(value, appy=True) or \
                         value
                targets.append(target)
            if not targets:
                msg = obj.translate('action_null')
            else:
                # Perform the action on every target. Count the number of failed
                # operations.
                failed = 0
                singleAction = action.split('_')[0]
                mustDelete = singleAction == 'delete'
                for target in targets:
                    if mustDelete:
                        # Delete
                        if target.o.mayDelete(): target.o.delete()
                        else: failed += 1
                    else:
                        # Link or unlink. For unlinking, we need to perform an
                        # additional check.
                        if (singleAction == 'unlink') and \
                           not self.mayUnlinkElement(appyObj, target):
                            failed += 1
                        else:
                            exec 'self.%sObject(appyObj, target)' % singleAction
                if failed:
                    msg = obj.translate('action_partial', mapping={'nb':failed})
        urlBack = obj.getUrl(rq['HTTP_REFERER'])
        if not msg: msg = obj.translate('action_done')
        appyObj.say(msg)
        tool.goto(urlBack)

    def getNavInfo(self, obj, nb, total, inPickList=False):
        '''Gets the navigation info allowing to navigate from tied object number
           p_nb to its siblings.'''
        if self.isBack or inPickList: return ''
        # If p_nb is None, we want to produce a generic nav info into which we
        # will insert a specific number afterwards.
        if nb == None: return 'ref.%s.%s.%%d.%d' % (obj.id, self.name, total)
        return 'ref.%s.%s.%d.%d' % (obj.id, self.name, nb, total)

    def onGotoTied(self, obj):
        '''Called when the user wants to go to a tied object whose number is in
           the request.'''
        number = int(obj.REQUEST['number']) - 1
        uids = getattr(obj.aq_base, self.name)
        tiedUid = uids[number]
        tied = obj.getTool().getObject(tiedUid)
        tiedUrl = tied.getUrl(nav=self.getNavInfo(obj, number+1, len(uids)))
        return obj.goto(tiedUrl)

    def getCollapseInfo(self, obj, inPickList):
        '''Returns a Collapsible instance, that determines if the "tied objects"
           or "available objects" zone (depending on p_inPickList) is collapsed
           or expanded.'''
        # Create the ID of the collapsible zone.
        suffix = inPickList and 'poss' or 'objs'
        id = '%s_%s_%s' % (obj.klass.__name__, self.name, suffix)
        return gutils.Collapsible(id, obj.request, default='expanded',
                                  display='table')

def autoref(klass, field):
    '''klass.field is a Ref to p_klass. This kind of auto-reference can't be
       declared in the "normal" way, like this:

       class A:
           attr1 = Ref(A)

       because at the time Python encounters the static declaration
       "attr1 = Ref(A)", class A is not completely defined yet.

       This method allows to overcome this problem. You can write such
       auto-reference like this:

       class A:
           attr1 = Ref(None)
       autoref(A, A.attr1)

       This function can also be used to avoid circular imports between 2
       classes from 2 different packages. Imagine class P1 in package p1 has a
       Ref to class P2 in package p2; and class P2 has another Ref to p1.P1
       (which is not the back Ref of the previous one: it is another,
       independent Ref).

       In p1, you have

       from p2 import P2
       class P1:
           ref1 = Ref(P2)

       Then, if you write the following in p2, python will complain because of a
       circular import:

       from p1 import P1
       class P2:
           ref2 = Ref(P1)

       The solution is to write this. In p1:

       from p2 import P2
       class P1:
           ref1 = Ref(P2)
       autoref(P1, P2.ref2)

       And, in p2:
       class P2:
           ref2 = Ref(None)
    '''
    field.klass = klass
    setattr(klass, field.back.attribute, field.back)
# ------------------------------------------------------------------------------
