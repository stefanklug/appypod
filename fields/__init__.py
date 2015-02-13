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
import copy, types, re
from appy import Object
from appy.gen.layout import Table, defaultFieldLayouts
from appy.gen import utils as gutils
from appy.px import Px
from appy.shared import utils as sutils
from group import Group
from search import Search
from page import Page

# ------------------------------------------------------------------------------
class Field:
    '''Basic abstract class for defining any field.'''

    # Some global static variables
    nullValues = (None, '', [])
    validatorTypes = (types.FunctionType, types.UnboundMethodType,
                      type(re.compile('')))
    labelTypes = ('label', 'descr', 'help')

    # Those attributes can be overridden by subclasses for defining,
    # respectively, names of CSS and Javascript files that are required by this
    # field, keyed by layoutType.
    cssFiles = {}
    jsFiles = {}
    bLayouts = Table('lrv-f', width=None)
    dLayouts = 'lrv-d-f'
    hLayouts = 'lhrv-f'
    wLayouts = Table('lrv-f')

    # Render a field. Optional vars:
    # * fieldName   can be given as different as field.name for fields included
    #               in List fields: in this case, fieldName includes the row
    #               index.
    # * showChanges If True, a variant of the field showing successive changes
    #               made to it is shown.
    pxRender = Px('''
     <x var="showChanges=showChanges|req.get('showChanges') == 'True';
             layoutType=layoutType|req.get('layoutType');
             isSearch = layoutType == 'search';
             layout=field.layouts[layoutType];
             name=fieldName|field.name;
             widgetName = isSearch and ('w_%s' % name) or name;
             outerValue=value|None;
             rawValue=not isSearch and zobj.getFieldValue(name, \
                        layoutType=layoutType, outerValue=outerValue);
             value=not isSearch and \
                   field.getFormattedValue(zobj, rawValue, showChanges);
             requestValue=not isSearch and zobj.getRequestFieldValue(name);
             inRequest=field.valueIsInRequest(zobj, req, name, layoutType);
             error=req.get('%s_error' % name);
             isMultiple=(field.multiplicity[1] == None) or \
                        (field.multiplicity[1] &gt; 1);
             masterCss=field.slaves and ('master_%s' % name) or '';
             slaveCss=field.getSlaveCss();
             tagCss=tagCss|'';
             tagCss=('%s %s' % (slaveCss, tagCss)).strip();
             zobj=zobj or ztool;
             tagId='%s_%s' % (zobj.id, name);
             tagName=field.master and 'slave' or '';
             layoutTarget=field">:tool.pxLayoutedObject</x>''')

    def doRender(self, layoutType, request, context=None, name=None):
        '''Allows to call pxRender from code, to display the content of this
           field in some specific context, for example in a Computed field.'''
        if context == None: context = {}
        context['layoutType'] = layoutType
        context['field'] = self
        context['name'] = name or self.name
        # We may be executing a PX on a given object or on a given object tied
        # through a Ref.
        ctx = request.pxContext
        if 'obj' not in context:
            context['obj'] = ('tied' in ctx) and ctx['tied'] or ctx['obj']
            context['zobj'] = context['obj'].o
        # Copy some keys from the context of the currently executed PX.
        for k in ('tool', 'ztool', 'req', '_', 'q', 'url', 'dir', 'dright',
                  'dleft', 'inPopup'):
            if k in context: continue
            context[k] = ctx[k]
        return self.pxRender(context).encode('utf-8')

    # Show the field content for some object on a list of referred objects
    pxRenderAsTied = Px('''
     <!-- The "title" field -->
     <x if="refField.name == 'title'">
      <x if="mayView">
       <x if="not field.menuUrlMethod">:field.pxObjectTitle</x>
       <a if="field.menuUrlMethod"
          var2="info=field.getMenuUrl(zobj, tied)"
          href=":info[0]" target=":info[1]">:tied.title</a>
       <x if="tied.o.mayAct()">:field.pxObjectActions</x>
      </x>
      <div if="not mayView">
       <img src=":url('fake')" style="margin-right: 5px"/>
       <x>:_('unauthorized')</x></div>
     </x>
     <!-- Any other field -->
     <x if="(refField.name != 'title') and mayView">
      <x var="zobj=tied.o; obj=tied; layoutType='cell'; field=refField"
         if="field.isShowable(zobj, 'result')">:field.pxRender</x>
     </x>''')

    # Show the field content for some object on a list of results
    pxRenderAsResult = Px('''
     <!-- Title -->
     <x if="field.name == 'title'"
        var2="navInfo='search.%s.%s.%d.%d' % (className, searchName, \
                                      startNumber+currentNumber, totalNumber)">
      <x if="mayView"
         var2="titleMode=inPopup and 'select' or 'link';
               pageName=zobj.getDefaultViewPage();
               selectJs=inPopup and 'onSelectObject(%s,%s,%s)' % (q(cbId), \
                          q(rootHookId), q(uiSearch.initiator.url))">
       <x var="sup=zobj.getSupTitle(navInfo)" if="sup">::sup</x>
       <x>::zobj.getListTitle(mode=titleMode, nav=navInfo, target=target, \
          page=pageName, inPopup=inPopup, selectJs=selectJs, highlight=True)</x>
       <span style=":showSubTitles and 'display:inline' or 'display:none'"
             name="subTitle" var="sub=zobj.getSubTitle()"
             if="sub">::zobj.highlight(sub)</span>

       <!-- Actions -->
       <div if="not inPopup and uiSearch.showActions and zobj.mayAct()"
            class="objectActions" style=":'display:%s' % uiSearch.showActions"
            var2="layoutType='buttons'">
        <!-- Edit -->
        <a if="zobj.mayEdit()"
           var2="linkInPopup=inPopup or (target.target != '_self')"
           target=":target.target" onclick=":target.openPopup"
           href=":zobj.getUrl(mode='edit', page=zobj.getDefaultEditPage(), \
                              nav=navInfo, inPopup=linkInPopup)">
         <img src=":url('edit')" title=":_('object_edit')"/>
        </a>
        <!-- Delete -->
        <img if="zobj.mayDelete()" class="clickable" src=":url('delete')"
             title=":_('object_delete')"
             onClick=":'onDeleteObject(%s)' % q(zobj.id)"/>
        <!-- Workflow transitions -->
        <x if="zobj.showTransitions('result')"
           var2="targetObj=zobj">:targetObj.appy().pxTransitions</x>
        <!-- Fields (actions) defined with layout "buttons" -->
        <x if="not inPopup"
           var2="fields=zobj.getAppyTypes('buttons', 'main');
                 layoutType='cell'">
         <!-- Call pxCell and not pxRender to avoid having a table -->
         <x for="field in fields"
            var2="name=field.name; smallButtons=True">:field.pxCell</x>
        </x>
       </div>
      </x>
      <x if="not mayView">
       <img src=":url('fake')" style="margin-right: 5px"/>
       <x>:_('unauthorized')</x>
      </x>
     </x>
     <!-- Any other field -->
     <x if="(field.name != 'title') and mayView">
      <x var="layoutType='cell'"
         if="field.isShowable(zobj, 'result')">:field.pxRender</x>
     </x>''')

    # Displays a field label
    pxLabel = Px('''<label if="field.hasLabel and field.renderLabel"
     lfor=":field.name">::_('label', field=field)</label>''')

    # Displays a field description
    pxDescription = Px('''<span if="field.hasDescr"
     class="discreet">::_('descr', field=field)</span>''')

    # Displays a field help
    pxHelp = Px('''<acronym title=":_('help', field=field)"><img
     src=":url('help')"/></acronym>''')

    # Displays validation-error-related info about a field
    pxValidation = Px('''<x><acronym if="error" title=":error"><img
     src=":url('warning')"/></acronym><img if="not error"
     src=":url('warning_no.gif')"/></x>''')

    # Displays the fact that a field is required
    pxRequired = Px('''<img src=":url('required.gif')"/>''')

    # Button for showing changes to the field
    pxChanges = Px('''
     <div if="zobj.hasHistory(name)" style="margin-bottom: 5px">
      <!-- Button for showing the field version containing changes -->
      <input if="not showChanges"
             var2="label=_('changes_show');
                   css=ztool.getButtonCss(label)" type="button" class=":css"
             value=":label" style=":url('changes', bg=True)"
             onclick=":'askField(%s,%s,%s,null,%s)' % \
                       (q(tagId), q(obj.url), q('view'), q('True'))"/>
      <!-- Button for showing the field version without changes -->
      <input if="showChanges"
             var2="label=_('changes_hide');
                  css=ztool.getButtonCss(label)" type="button" class=":css"
             value=":label" style=":url('changesNo', bg=True)"
             onclick=":'askField(%s,%s,%s,null,%s)' % \
                       (q(tagId), q(obj.url), q('view'), q('False'))"/>
     </div>''')

    def __init__(self, validator, multiplicity, default, show, page, group,
                 layouts, move, indexed, mustIndex, searchable,
                 specificReadPermission, specificWritePermission, width, height,
                 maxChars, colspan, master, masterValue, focus, historized,
                 mapping, label, sdefault, scolspan, swidth, sheight, persist,
                 view, xml):
        # The validator restricts which values may be defined. It can be an
        # interval (1,None), a list of string values ['choice1', 'choice2'],
        # a regular expression, a custom function, a Selection instance, etc.
        self.validator = validator
        # Multiplicity is a 2-tuple indicating the minimum and maximum
        # occurrences of values.
        self.multiplicity = multiplicity
        # Is the field required or not ? (derived from multiplicity)
        self.required = self.multiplicity[0] > 0
        # Default value
        self.default = default
        # Must the field be visible or not?
        self.show = show
        # When displaying/editing the whole object, on what page and phase must
        # this field value appear?
        self.page = Page.get(page)
        self.pageName = self.page.name
        # Within self.page, in what group of fields must this one appear?
        self.group = Group.get(group)
        # The following attribute allows to move a field back to a previous
        # position (useful for moving fields above predefined ones).
        self.move = move
        # If indexed is True, a database index will be set on the field for
        # fast access.
        self.indexed = indexed
        # If "mustIndex", True by default, is specified, it must be a method
        # returning a boolean value. Indexation will only occur when this value
        # is True.
        self.mustIndex = mustIndex
        if not mustIndex and not callable(mustIndex):
            raise Exception('Value for param "mustIndex" must be a method.')
        # If specified "searchable", the field will be added to some global
        # index allowing to perform application-wide, keyword searches.
        self.searchable = searchable
        # Normally, permissions to read or write every attribute in a type are
        # granted if the user has the global permission to read or
        # edit instances of the whole type. If you want a given attribute
        # to be protected by specific permissions, set one or the 2 next boolean
        # values to "True". In this case, you will create a new "field-only"
        # read and/or write permission. If you need to protect several fields
        # with the same read/write permission, you can avoid defining one
        # specific permission for every field by specifying a "named"
        # permission (string) instead of assigning "True" to the following
        # arg(s). A named permission will be global to your whole Zope site, so
        # take care to the naming convention. Typically, a named permission is
        # of the form: "<yourAppName>: Write|Read ---". If, for example, I want
        # to define, for my application "MedicalFolder" a specific permission
        # for a bunch of fields that can only be modified by a doctor, I can
        # define a permission "MedicalFolder: Write medical information" and
        # assign it to the "specificWritePermission" of every impacted field.
        self.specificReadPermission = specificReadPermission
        self.specificWritePermission = specificWritePermission
        # Widget width and height
        self.width = width
        self.height = height
        # While width and height refer to widget dimensions, maxChars hereafter
        # represents the maximum number of chars that a given input field may
        # accept (corresponds to HTML "maxlength" property). "None" means
        # "unlimited".
        self.maxChars = maxChars or ''
        # If the widget is in a group with multiple columns, the following
        # attribute specifies on how many columns to span the widget.
        self.colspan = colspan or 1
        # The list of slaves of this field, if it is a master
        self.slaves = []
        # The behaviour of this field may depend on another, "master" field
        self.master = master
        if master: self.master.slaves.append(self)
        # The semantics of attribute "masterValue" below is as follows:
        # - if "masterValue" is anything but a method, the field will be shown
        #   only when the master has this value, or one of it if multivalued;
        # - if "masterValue" is a method, the value(s) of the slave field will
        #   be returned by this method, depending on the master value(s) that
        #   are given to it, as its unique parameter.
        self.masterValue = gutils.initMasterValue(masterValue)
        # If a field must retain attention in a particular way, set focus=True.
        # It will be rendered in a special way.
        self.focus = focus
        # If we must keep track of changes performed on a field, "historized"
        # must be set to True.
        self.historized = historized
        # Mapping is a dict of contexts that, if specified, are given when
        # translating the label, descr or help related to this field.
        self.mapping = self.formatMapping(mapping)
        self.id = id(self)
        self.type = self.__class__.__name__
        self.pythonType = None # The True corresponding Python type
        # Get the layouts. Consult layout.py for more info about layouts.
        self.layouts = self.formatLayouts(layouts)
        # Can we filter this field?
        self.filterable = False
        # Can this field have values that can be edited and validated?
        self.validable = True
        # The base label for translations is normally generated automatically.
        # It is made of 2 parts: the prefix, based on class name, and the name,
        # which is the field name by default. You can change this by specifying
        # a value for param "label". If this value is a string, it will be
        # understood as a new prefix. If it is a tuple, it will represent the
        # prefix and another name. If you want to specify a new name only, and
        # not a prefix, write (None, newName).
        self.label = label
        # When you specify a default value "for search" (= "sdefault"), on a
        # search screen, in the search field corresponding to this field, this
        # default value will be present.
        self.sdefault = sdefault
        # Colspan for rendering the search widget corresponding to this field.
        self.scolspan = scolspan or 1
        # Width and height for the search widget
        self.swidth = swidth or width
        self.sheight = sheight or height
        # "persist" indicates if field content must be stored in the database.
        # For some fields it is not wanted (ie, fields used only as masters to
        # update slave's selectable values).
        self.persist = persist
        # If you want to use an alternate PX than Field.pxView, you can specify
        # it in "view".
        if view != None:
            # This instance attribute will override the class attribute
            self.pxView = view
        # Standard marshallers are provided for converting values of this field
        # into XML. If you want to customize the marshalling process, you can
        # define a method in "xml" that will accept a field value and will
        # return a possibly different value. Be careful: do not return a chunk
        # of XML here! Simply return an alternate value, that will be
        # XML-marshalled.
        self.xml = xml

    def init(self, name, klass, appName):
        '''When the application server starts, this secondary constructor is
           called for storing the name of the Appy field (p_name) and other
           attributes that are based on the name of the Appy p_klass, and the
           application name (p_appName).'''
        if hasattr(self, 'name'): return # Already initialized
        self.name = name
        # Determine prefix for this class
        if not klass: prefix = appName
        else:         prefix = gutils.getClassName(klass, appName)
        # Recompute the ID (and derived attributes) that may have changed if
        # we are in debug mode (because we recreate new Field instances).
        self.id = id(self)
        # Remember master name on every slave
        for slave in self.slaves: slave.masterName = name
        # Determine ids of i18n labels for this field
        labelName = name
        trPrefix = None
        if self.label:
            if isinstance(self.label, basestring): trPrefix = self.label
            else: # It is a tuple (trPrefix, name)
                if self.label[1]: labelName = self.label[1]
                if self.label[0]: trPrefix = self.label[0]
        if not trPrefix:
            trPrefix = prefix
        # Determine name to use for i18n
        self.labelId = '%s_%s' % (trPrefix, labelName)
        self.descrId = self.labelId + '_descr'
        self.helpId  = self.labelId + '_help'
        # Determine read and write permissions for this field
        rp = self.specificReadPermission
        if rp and not isinstance(rp, basestring):
            self.readPermission = '%s: Read %s %s' % (appName, prefix, name)
        elif rp and isinstance(rp, basestring):
            self.readPermission = rp
        else:
            self.readPermission = 'read'
        wp = self.specificWritePermission
        if wp and not isinstance(wp, basestring):
            self.writePermission = '%s: Write %s %s' % (appName, prefix, name)
        elif wp and isinstance(wp, basestring):
            self.writePermission = wp
        else:
            self.writePermission = 'write'
        if (self.type == 'Ref') and not self.isBack:
            # We must initialise the corresponding back reference
            self.back.klass = klass
            self.back.init(self.back.attribute, self.klass, appName)
        if self.type == "List":
            for subName, subField in self.fields:
                fullName = '%s_%s' % (name, subName)
                subField.init(fullName, klass, appName)
                subField.name = '%s*%s' % (name, subName)

    def reload(self, klass, obj):
        '''In debug mode, we want to reload layouts without restarting Zope.
           So this method will prepare a "new", reloaded version of p_self,
           that corresponds to p_self after a "reload" of its containing Python
           module has been performed.'''
        res = getattr(klass, self.name, None)
        if not res: return self
        if (self.type == 'Ref') and self.isBack: return self
        res.init(self.name, klass, obj.getProductConfig().PROJECTNAME)
        return res

    def isMultiValued(self):
        '''Does this type definition allow to define multiple values?'''
        maxOccurs = self.multiplicity[1]
        return (maxOccurs == None) or (maxOccurs > 1)

    def isSortable(self, usage):
        '''Can fields of this type be used for sorting purposes (when sorting
           search results (p_usage="search") or when sorting reference fields
           (p_usage="ref")?'''
        if self.name == 'state': return
        if usage == 'search':
            return self.indexed and not self.isMultiValued() and not \
                   ((self.type == 'String') and self.isSelection())
        elif usage == 'ref':
            if self.type in ('Integer', 'Float', 'Boolean', 'Date'): return True
            elif self.type == 'String':
                return (self.format == 0) and not self.isMultilingual(None,True)

    def isShowable(self, obj, layoutType):
        '''When displaying p_obj on a given p_layoutType, must we show this
           field?'''
        # Check if the user has the permission to view or edit the field
        perm = (layoutType == 'edit') and self.writePermission or \
                                          self.readPermission
        if not obj.allows(perm): return
        # Evaluate self.show
        if callable(self.show):
            res = self.callMethod(obj, self.show)
        else:
            res = self.show
        # Take into account possible values 'view', 'edit', 'result'...
        if type(res) in sutils.sequenceTypes:
            for r in res:
                if r == layoutType: return True
            return
        elif res in ('view', 'edit', 'result', 'buttons', 'xml'):
            return res == layoutType
        # For showing a field on layout "buttons", the "buttons" layout must
        # explicitly be returned by the show method.
        if layoutType != 'buttons': return bool(res)

    def isRenderable(self, layoutType):
        '''In some contexts, computing m_isShowable can be a performance
           problem. For example, when showing fields of some object on layout
           "buttons", there are plenty of fields that simply can't be shown on
           this kind of layout: it is no worth computing m_isShowable for those
           fields. m_isRenderable is meant to define light conditions to
           determine, before calling m_isShowable, if some field has a chance to
           be shown or not.

           In other words, m_isRenderable defines a "structural" condition,
           independent of any object, while m_isShowable defines a contextual
           condition, depending on some object.'''
        # Most fields are not renderable on layout "buttons"
        if layoutType == 'buttons': return
        return True

    def isClientVisible(self, obj):
        '''This method returns True if this field is visible according to
           master/slave relationships.'''
        masterData = self.getMasterData()
        if not masterData: return True
        else:
            master, masterValue = masterData
            if masterValue and callable(masterValue): return True
            reqValue = master.getRequestValue(obj)
            # reqValue can be a list or not
            if type(reqValue) not in sutils.sequenceTypes:
                return reqValue in masterValue
            else:
                for m in masterValue:
                    for r in reqValue:
                        if m == r: return True

    def formatMapping(self, mapping):
        '''Creates a dict of mappings, one entry by label type (label, descr,
           help).'''
        if isinstance(mapping, dict):
            # Is it a dict like {'label':..., 'descr':...}, or is it directly a
            # dict with a mapping?
            for k, v in mapping.iteritems():
                if (k not in self.labelTypes) or isinstance(v, basestring):
                    # It is already a mapping
                    return {'label':mapping, 'descr':mapping, 'help':mapping}
            # If we are here, we have {'label':..., 'descr':...}. Complete
            # it if necessary.
            for labelType in self.labelTypes:
                if labelType not in mapping:
                    mapping[labelType] = None # No mapping for this value.
            return mapping
        else:
            # Mapping is a method that must be applied to any i18n message.
            return {'label':mapping, 'descr':mapping, 'help':mapping}

    def formatLayouts(self, layouts):
        '''Standardizes the given p_layouts. .'''
        # First, get the layouts as a dictionary, if p_layouts is None or
        # expressed as a simple string.
        areDefault = False
        if not layouts:
            # Get the default layouts as defined by the subclass
            areDefault = True
            layouts = self.computeDefaultLayouts()
        else:
            if isinstance(layouts, basestring):
                # The user specified a single layoutString (the "edit" one)
                layouts = {'edit': layouts}
            elif isinstance(layouts, Table):
                # Idem, but with a Table instance
                layouts = {'edit': Table(other=layouts)}
            else:
                # Here, we make a copy of the layouts, because every layout can
                # be different, even if the user decides to reuse one from one
                # field to another. This is because we modify every layout for
                # adding master/slave-related info, focus-related info, etc,
                # which can be different from one field to the other.
                layouts = copy.deepcopy(layouts)
                if 'edit' not in layouts:
                    defEditLayout = self.computeDefaultLayouts()
                    if type(defEditLayout) == dict:
                        defEditLayout = defEditLayout['edit']
                    layouts['edit'] = defEditLayout
        # We have now a dict of layouts in p_layouts. Ensure now that a Table
        # instance is created for every layout (=value from the dict). Indeed,
        # a layout could have been expressed as a simple layout string.
        for layoutType in layouts.iterkeys():
            if isinstance(layouts[layoutType], basestring):
                layouts[layoutType] = Table(layouts[layoutType])
        # Derive "view", "search" and "cell" layouts from the "edit" layout
        # when relevant.
        if 'view' not in layouts:
            layouts['view'] = Table(other=layouts['edit'], derivedType='view')
        if 'search' not in layouts:
            layouts['search'] = Table(other=layouts['view'],
                                      derivedType='search')
        # Create the "cell" layout from the 'view' layout if not specified.
        if 'cell' not in layouts:
            layouts['cell'] = Table(other=layouts['view'], derivedType='cell')
        # Put the required CSS classes in the layouts
        layouts['cell'].addCssClasses('noStyle')
        if self.focus:
            # We need to make it flashy
            layouts['view'].addCssClasses('focus')
            layouts['edit'].addCssClasses('focus')
        # If layouts are the default ones, set width=None instead of width=100%
        # for the field if it is not in a group (excepted for rich texts and
        # refs).
        if areDefault and not self.group and \
           not ((self.type == 'String') and (self.format == self.XHTML)) and \
           not (self.type == 'Ref'):
            for layoutType in layouts.iterkeys():
                layouts[layoutType].width = ''
        # Remove letters "r" from the layouts if the field is not required.
        if not self.required:
            for layoutType in layouts.iterkeys():
                layouts[layoutType].removeElement('r')
        # Derive some boolean values from the layouts.
        self.hasLabel = self.hasLayoutElement('l', layouts)
        # "renderLabel" indicates if the existing label (if hasLabel is True)
        # must be rendered by pxLabel. For example, if field is an action, the
        # label will be rendered within the button, not by pxLabel.
        self.renderLabel = self.hasLabel
        # If field is within a group rendered like a tab, the label will already
        # be rendered in the corresponding tab.
        if self.group and (self.group.style == 'tabs'): self.renderLabel = False
        self.hasDescr = self.hasLayoutElement('d', layouts)
        self.hasHelp  = self.hasLayoutElement('h', layouts)
        return layouts

    @staticmethod
    def copyLayouts(layouts):
        '''Create a deep copy of p_layouts.'''
        res = {}
        for k, v in layouts.iteritems():
            if isinstance(v, Table): res[k] = Table(other=v)
            else: res[k] = v
        return res

    def hasLayoutElement(self, element, layouts):
        '''This method returns True if the given layout p_element can be found
           at least once among the various p_layouts defined for this field.'''
        for layout in layouts.itervalues():
            if element in layout.layoutString: return True
        return False

    def getDefaultLayouts(self):
        '''Any subclass can define this for getting a specific set of
           default layouts. If None is returned, a global set of default layouts
           will be used.'''

    def getInputLayouts(self):
        '''Gets, as a string, the layouts as could have been specified as input
           value for the Field constructor.'''
        res = '{'
        for k, v in self.layouts.iteritems():
            res += '"%s":"%s",' % (k, v.layoutString)
        res += '}'
        return res

    def computeDefaultLayouts(self):
        '''This method gets the default layouts from an Appy type, or a copy
           from the global default field layouts when they are not available.'''
        res = self.getDefaultLayouts()
        if not res:
            # Get the global default layouts
            res = copy.deepcopy(defaultFieldLayouts)
        return res

    def getCss(self, layoutType, res):
        '''This method completes the list p_res with the names of CSS files
           that are required for displaying widgets of self's type on a given
           p_layoutType. p_res is not a set because order of inclusion of CSS
           files may be important and may be loosed by using sets.'''
        if layoutType in self.cssFiles:
            for fileName in self.cssFiles[layoutType]:
                if fileName not in res:
                    res.append(fileName)

    def getJs(self, layoutType, res):
        '''This method completes the list p_res with the names of Javascript
           files that are required for displaying widgets of self's type on a
           given p_layoutType. p_res is not a set because order of inclusion of
           CSS files may be important and may be loosed by using sets.'''
        if layoutType in self.jsFiles:
            for fileName in self.jsFiles[layoutType]:
                if fileName not in res:
                    res.append(fileName)

    def getValue(self, obj):
        '''Gets, on_obj, the value conforming to self's type definition.'''
        value = getattr(obj.aq_base, self.name, None)
        if self.isEmptyValue(obj, value):
            # If there is no value, get the default value if any: return
            # self.default, of self.default() if it is a method.
            if callable(self.default):
                try:
                    # Caching a default value can lead to problems. For example,
                    # the process of creating an object from another one, or
                    # from some data, sometimes consists in (a) creating an
                    # "empty" object, (b) initializing its values and
                    # (c) reindexing it. Default values are computed in (a),
                    # but it they depend on values set at (b), and are cached
                    # and indexed, (c) will get the wrong, cached value.
                    return self.callMethod(obj, self.default, cache=False)
                except Exception, e:
                    # Already logged. Here I do not raise the exception,
                    # because it can be raised as the result of reindexing
                    # the object in situations that are not foreseen by
                    # method in self.default.
                    return
            else:
                return self.default
        return value

    def getCopyValue(self, obj):
        '''Gets the value of this field on p_obj as with m_getValue above. But
           if this value is mutable, get a copy of it.'''
        return self.getValue(obj)

    def getFormattedValue(self, obj, value, showChanges=False, language=None):
        '''p_value is a real p_obj(ect) value from a field from this type. This
           method returns a pretty, string-formatted version, for displaying
           purposes. Needs to be overridden by some child classes. If
           p_showChanges is True, the result must also include the changes that
           occurred on p_value across the ages. If the formatting implies
           translating some elements, p_language will be used if given, the
           user language else.'''
        if self.isEmptyValue(obj, value): return ''
        return value

    def getShownValue(self, obj, value, showChanges=False, language=None):
        '''Similar to m_getFormattedValue, but in some contexts, only a part of
           p_value must be shown. For example, sometimes we need to display only
           a language-specific part of a multilingual field (see overridden
           method in string.py).'''
        return self.getFormattedValue(obj, value, showChanges, language)

    def getXmlValue(self, obj, value):
        '''This method allows a developer to customize the value that will be
           marshalled into XML. It makes use of attribute "xml".'''
        if not self.xml: return value
        return self.xml(obj, value)

    def getIndexType(self):
        '''Returns the name of the technical, Zope-level index type for this
           field.'''
        # Normally, self.indexed contains a Boolean. If a string value is given,
        # we consider it to be an index type. It allows to bypass the standard
        # way to decide what index type must be used.
        if isinstance(self.indexed, str): return self.indexed
        if self.name == 'title': return 'TextIndex'
        return 'FieldIndex'

    def getIndexValue(self, obj, forSearch=False):
        '''This method returns a version for this field value on p_obj that is
           ready for indexing purposes. Needs to be overridden by some child
           classes.

           If p_forSearch is True, it will return a "string" version of the
           index value suitable for a global search.'''
        # Must we produce an index value?
        if not self.getAttribute(obj, 'mustIndex'): return
        # Start by getting the field value on p_obj
        res = self.getValue(obj)
        # Zope catalog does not like unicode strings
        if isinstance(res, unicode): res = res.encode('utf-8')
        if forSearch and (res != None):
            if type(res) in sutils.sequenceTypes:
                vals = []
                for v in res:
                    if isinstance(v, unicode): vals.append(v.encode('utf-8'))
                    else: vals.append(str(v))
                res = ' '.join(vals)
            else:
                res = str(res)
        return res

    def getIndexName(self, usage='search'):
        '''Gets the name of the Zope index that corresponds to this field.
           Indexes can be used for searching (p_usage="search") or for sorting
           (usage="sort"). The method returns None if the field
           named p_fieldName can't be used for p_usage.'''
        # Manage special cases
        if self.name == 'title':
            # For field 'title', Appy has a specific index 'SortableTitle',
            # because index 'Title' is a TextIndex (for searchability) and can't
            # be used for sorting.
            return (usage == 'sort') and 'SortableTitle' or 'Title'
        elif self.name == 'state': return 'State'
        elif self.name == 'SearchableText': return 'SearchableText'
        else:
            res = 'get%s%s'% (self.name[0].upper(), self.name[1:])
            if (usage == 'sort') and self.hasSortIndex(): res += '_sort'
        return res

    def hasSortIndex(self):
        '''Some fields have indexes that prevents sorting (ie, list indexes).
           Those fields may define a secondary index, specifically for sorting.
           This is the case of Ref fields for example.'''
        return

    def getCatalogValue(self, obj, usage='search'):
        '''This method returns the index value that is currently stored in the
           catalog for this field on p_obj.'''
        if not self.indexed:
            raise Exception('Field %s: cannot retrieve catalog version of ' \
                            'unindexed field.' % self.name)
        return obj.getTool().getCatalogValue(obj, self.getIndexName(usage))

    def valueIsInRequest(self, obj, request, name, layoutType):
        '''Is there a value corresponding to this field in the request? p_name
           can be different from self.name (ie, if it is a field within another
           (List) field). In most cases, checking that this p_name is in the
           request is sufficient. But in some cases it may be more complex, ie
           for string multilingual fields.'''
        return request.has_key(name)

    def getRequestValue(self, obj, requestName=None):
        '''Gets a value for this field as carried in the request object. In the
           simplest cases, the request value is a single value whose name in the
           request is the name of the field.

           Sometimes (ie: a Date: see the overriden method in the Date class),
           several request values must be combined.

           Sometimes (ie, a field which is a sub-field in a List), the name of
           the request value(s) representing the field value do not correspond
           to the field name (ie: the request name includes information about
           the container field). In this case, p_requestName must be used for
           searching into the request, instead of the field name (self.name).'''
        name = requestName or self.name
        return obj.REQUEST.get(name, None)

    def getStorableValue(self, obj, value):
        '''p_value is a valid value initially computed through calling
           m_getRequestValue. So, it is a valid string (or list of strings)
           representation of the field value coming from the request.
           This method computes the real (potentially converted or manipulated
           in some other way) value as can be stored in the database.'''
        if self.isEmptyValue(obj, value): return
        return value

    def setSlave(self, slaveField, masterValue):
        '''Sets p_slaveField as slave of this field. Normally, master/slave
           relationships are defined when a slave field is defined. At this time
           you specify parameters "master" and "masterValue" for this field and
           that's all. This method is used to add a master/slave relationship
           that was not initially foreseen.'''
        slaveField.master = self
        slaveField.masterValue = gutils.initMasterValue(masterValue)
        if slaveField not in self.slaves:
            self.slaves.append(slaveField)
        # Master's init method may not have been called yet.
        slaveField.masterName = getattr(self, 'name', None)

    def getMasterData(self):
        '''Gets the master of this field (and masterValue) or, recursively, of
           containing groups when relevant.'''
        if self.master: return (self.master, self.masterValue)
        if self.group: return self.group.getMasterData()

    def getSlaveCss(self):
        '''Gets the CSS class that must apply to this field in the web UI when
           this field is the slave of another field.'''
        if not self.master: return ''
        res = 'slave*%s*' % self.masterName
        if not callable(self.masterValue):
            res += '*'.join(self.masterValue)
        else:
            res += '+'
        return res

    def getOnChange(self, zobj, layoutType, className=None):
        '''When this field is a master, this method computes the call to the
           Javascript function that will be called when its value changes (in
           order to update slaves).'''
        if not self.slaves: return ''
        q = zobj.getTool().quote
        # When the field is on a search screen, we need p_className.
        cName = className and (',%s' % q(className)) or ''
        return 'updateSlaves(this,null,%s,%s,null,null%s)' % \
               (q(zobj.absolute_url()), q(layoutType), cName)

    def isEmptyValue(self, obj, value):
        '''Returns True if the p_value must be considered as an empty value.'''
        return value in self.nullValues

    def isCompleteValue(self, obj, value):
        '''Returns True if the p_value must be considered as "complete". While,
           in most cases, a "complete" value simply means a "non empty" value
           (see m_isEmptyValue above), in some special cases it is more subtle.
           For example, a multilingual string value is not empty as soon as a
           value is given for some language but will not be considered as
           complete while a value is missing for some language. Another example:
           a Date with the "hour" part required will not be considered as empty
           if the "day, month, year" part is present but will not be considered
           as complete without the "hour, minute" part.'''
        return not self.isEmptyValue(obj, value)

    def validateValue(self, obj, value):
        '''This method may be overridden by child classes and will be called at
           the right moment by m_validate defined below for triggering
           type-specific validation. p_value is never empty.'''
        return

    def securityCheck(self, obj, value):
        '''This method performs some security checks on the p_value that
           represents user input.'''
        if not isinstance(value, basestring): return
        # Search Javascript code in the value (prevent XSS attacks).
        if '<script' in value:
            obj.log('Detected Javascript in user input.', type='error')
            raise Exception('Your behaviour is considered a security ' \
                            'attack. System administrator has been warned.')

    def validate(self, obj, value):
        '''This method checks that p_value, coming from the request (p_obj is
           being created or edited) and formatted through a call to
           m_getRequestValue defined above, is valid according to this type
           definition. If it is the case, None is returned. Else, a translated
           error message is returned.'''
        # If the value is required, check that a (complete) value is present.
        if not self.isCompleteValue(obj, value):
            if self.required and self.isClientVisible(obj):
                # If the field is required, but not visible according to
                # master/slave relationships, we consider it not to be required.
                return obj.translate('field_required')
            else:
                return
        # Perform security checks on p_value
        self.securityCheck(obj, value)
        # Triggers the sub-class-specific validation for this value
        message = self.validateValue(obj, value)
        if message: return message
        # Evaluate the custom validator if one has been specified
        value = self.getStorableValue(obj, value)
        if self.validator and (type(self.validator) in self.validatorTypes):
            obj = obj.appy()
            if type(self.validator) != self.validatorTypes[-1]:
                # It is a custom function. Execute it.
                try:
                    validValue = self.validator(obj, value)
                    if isinstance(validValue, basestring) and validValue:
                        # Validation failed; and p_validValue contains an error
                        # message.
                        return validValue
                    else:
                        if not validValue:
                            return obj.translate('field_invalid')
                except Exception, e:
                    return str(e)
                except:
                    return obj.translate('field_invalid')
            else:
                # It is a regular expression
                if not self.validator.match(value):
                    return obj.translate('field_invalid')

    def store(self, obj, value):
        '''Stores the p_value (produced by m_getStorableValue) that complies to
           p_self type definition on p_obj.'''
        if self.persist: setattr(obj, self.name, value)

    def callMethod(self, obj, method, cache=True):
        '''This method is used to call a p_method on p_obj. p_method is part of
           this type definition (ie a default method, the method of a Computed
           field, a method used for showing or not a field...). Normally, those
           methods are called without any arg. But one may need, within the
           method, to access the related field. This method tries to call
           p_method with no arg *or* with the field arg.'''
        obj = obj.appy()
        try:
            return gutils.callMethod(obj, method, cache=cache)
        except TypeError, te:
            # Try a version of the method that would accept self as an
            # additional parameter. In this case, we do not try to cache the
            # value (we do not call gutils.callMethod), because the value may
            # be different depending on the parameter.
            tb = sutils.Traceback.get()
            try:
                return method(obj, self)
            except Exception, e:
                obj.log(tb, type='error')
                # Raise the initial error.
                raise te
        except Exception, e:
            obj.log(sutils.Traceback.get(), type='error')
            raise e

    def getAttribute(self, obj, name):
        '''Gets the value of attribue p_name on p_self, which can be a simple
           value or the result of a method call on p_obj.'''
        res = getattr(self, name)
        if not callable(res): return res
        return self.callMethod(obj, res)

    def process(self, obj):
        '''This method is a general hook allowing a field to perform some
           processing after an URL on an object has been called, of the form
           <objUrl>/onProcess.'''
        return obj.goto(obj.absolute_url())
# ------------------------------------------------------------------------------
