# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
import re, time, copy, sys, types, os, os.path, mimetypes, string, StringIO
from appy import Object
from appy.gen.layout import Table
from appy.gen.layout import defaultFieldLayouts
from appy.gen.po import PoMessage
from appy.gen.utils import sequenceTypes, GroupDescr, Keywords, FileWrapper, \
                           getClassName, SomeObjects
import appy.pod
from appy.pod.renderer import Renderer
from appy.shared.data import countries
from appy.shared.utils import Traceback, getOsTempFolder

# Default Appy permissions -----------------------------------------------------
r, w, d = ('read', 'write', 'delete')
digit  = re.compile('[0-9]')
alpha  = re.compile('[a-zA-Z0-9]')
letter = re.compile('[a-zA-Z]')
nullValues = (None, '', [])
validatorTypes = (types.FunctionType, types.UnboundMethodType,
                  type(re.compile('')))
emptyTuple = ()
labelTypes = ('label', 'descr', 'help')

def initMasterValue(v):
    '''Standardizes p_v as a list of strings.'''
    if not v: res = []
    elif type(v) not in sequenceTypes: res = [v]
    else: res = v
    return [str(v) for v in res]

# Descriptor classes used for refining descriptions of elements in types
# (pages, groups,...) ----------------------------------------------------------
class Page:
    '''Used for describing a page, its related phase, show condition, etc.'''
    subElements = ('save', 'cancel', 'previous', 'next')
    def __init__(self, name, phase='main', show=True, showSave=True,
                 showCancel=True, showPrevious=True, showNext=True):
        self.name = name
        self.phase = phase
        self.show = show
        # When editing the page, must I show the "save" button?
        self.showSave = showSave
        # When editing the page, must I show the "cancel" button?
        self.showCancel = showCancel
        # When editing the page, and when a previous page exists, must I show
        # the "previous" button?
        self.showPrevious = showPrevious
        # When editing the page, and when a next page exists, must I show the
        # "next" button?
        self.showNext = showNext

    @staticmethod
    def get(pageData):
        '''Produces a Page instance from p_pageData. User-defined p_pageData
           can be:
           (a) a string containing the name of the page;
           (b) a string containing <pageName>_<phaseName>;
           (c) a Page instance.
           This method returns always a Page instance.'''
        res = pageData
        if res and isinstance(res, basestring):
            # Page data is given as a string.
            pageElems = pageData.rsplit('_', 1)
            if len(pageElems) == 1: # We have case (a)
                res = Page(pageData)
            else: # We have case (b)
                res = Page(pageData[0], phase=pageData[1])
        return res

    def isShowable(self, obj, layoutType, elem='page'):
        '''Must this page be shown for p_obj? "Show value" can be True, False
           or 'view' (page is available only in "view" mode).

           If p_elem is not "page", this method returns the fact that a
           sub-element is viewable or not (button "save", "cancel", etc).'''
        # Define what attribute to test for "showability".
        showAttr = 'show'
        if elem != 'page':
            showAttr = 'show%s' % elem.capitalize()
        # Get the value of the show attribute as identified above.
        show = getattr(self, showAttr)
        if callable(show):
            show = show(obj.appy())
        # Show value can be 'view', for example. Thanks to p_layoutType,
        # convert show value to a real final boolean value.
        res = show
        if res == 'view': res = layoutType == 'view'
        return res

    def getInfo(self, obj, layoutType):
        '''Gets information about this page, for p_obj, as a dict.'''
        res = {}
        for elem in Page.subElements:
            res['show%s' % elem.capitalize()] = self.isShowable(obj, layoutType,
                                                                elem=elem)
        return res

class Group:
    '''Used for describing a group of widgets within a page.'''
    def __init__(self, name, columns=['100%'], wide=True, style='section2',
                 hasLabel=True, hasDescr=False, hasHelp=False,
                 hasHeaders=False, group=None, colspan=1, align='center',
                 valign='top', css_class='', master=None, masterValue=None,
                 cellpadding=1, cellspacing=1, cellgap='0.6em', label=None):
        self.name = name
        # In its simpler form, field "columns" below can hold a list or tuple
        # of column widths expressed as strings, that will be given as is in
        # the "width" attributes of the corresponding "td" tags. Instead of
        # strings, within this list or tuple, you may give Column instances
        # (see below).
        self.columns = columns
        self._setColumns()
        # If field "wide" below is True, the HTML table corresponding to this
        # group will have width 100%. You can also specify some string value,
        # which will be used for HTML param "width".
        if wide == True:
            self.wide = '100%'
        elif isinstance(wide, basestring):
            self.wide = wide
        else:
            self.wide = ''
        # If style = 'fieldset', all widgets within the group will be rendered
        # within an HTML fieldset. If style is 'section1' or 'section2', widgets
        # will be rendered after the group title.
        self.style = style
        # If hasLabel is True, the group will have a name and the corresponding
        # i18n label will be generated.
        self.hasLabel = hasLabel
        # If hasDescr is True, the group will have a description and the
        # corresponding i18n label will be generated.
        self.hasDescr = hasDescr
        # If hasHelp is True, the group will have a help text associated and the
        # corresponding i18n label will be generated.
        self.hasHelp = hasHelp
        # If hasheaders is True, group content will begin with a row of headers,
        # and a i18n label will be generated for every header.
        self.hasHeaders = hasHeaders
        self.nbOfHeaders = len(columns)
        # If this group is himself contained in another group, the following
        # attribute is filled.
        self.group = Group.get(group)
        # If the group is rendered into another group, we can specify the number
        # of columns that this group will span.
        self.colspan = colspan
        self.align = align
        self.valign = valign
        self.cellpadding = cellpadding
        self.cellspacing = cellspacing
        # Beyond standard cellpadding and cellspacing, cellgap can define an
        # additional horizontal gap between cells in a row. So this value does
        # not add space before the first cell or after the last one.
        self.cellgap = cellgap
        if style == 'tabs':
            # Group content will be rendered as tabs. In this case, some
            # param combinations have no sense.
            self.hasLabel = self.hasDescr = self.hasHelp = False
            # The rendering is forced to a single column
            self.columns = self.columns[:1]
            # Header labels will be used as labels for the tabs.
            self.hasHeaders = True
        self.css_class = css_class
        self.master = master
        self.masterValue = initMasterValue(masterValue)
        if master: master.slaves.append(self)
        self.label = label # See similar attr of Type class.

    def _setColumns(self):
        '''Standardizes field "columns" as a list of Column instances. Indeed,
           the initial value for field "columns" may be a list or tuple of
           Column instances or strings.'''
        for i in range(len(self.columns)):
            columnData = self.columns[i]
            if not isinstance(columnData, Column):
                self.columns[i] = Column(self.columns[i])

    @staticmethod
    def get(groupData):
        '''Produces a Group instance from p_groupData. User-defined p_groupData
           can be a string or a Group instance; this method returns always a
           Group instance.'''
        res = groupData
        if res and isinstance(res, basestring):
            # Group data is given as a string. 2 more possibilities:
            # (a) groupData is simply the name of the group;
            # (b) groupData is of the form <groupName>_<numberOfColumns>.
            groupElems = groupData.rsplit('_', 1)
            if len(groupElems) == 1:
                # We have case (a)
                res = Group(groupElems[0])
            else:
                try:
                    nbOfColumns = int(groupElems[1])
                except ValueError:
                    nbOfColumns = 1
                width = 100.0 / nbOfColumns
                res = Group(groupElems[0], ['%.2f%%' % width] * nbOfColumns)
        return res

    def getMasterData(self):
        '''Gets the master of this group (and masterValue) or, recursively, of
           containing groups when relevant.'''
        if self.master: return (self.master, self.masterValue)
        if self.group: return self.group.getMasterData()

    def generateLabels(self, messages, classDescr, walkedGroups):
        '''This method allows to generate all the needed i18n labels related to
           this group. p_messages is the list of i18n p_messages that we are
           currently building; p_classDescr is the descriptor of the class where
           this group is defined.'''
        if self.hasLabel:
            msgId = '%s_group_%s' % (classDescr.name, self.name)
            poMsg = PoMessage(msgId, '', self.name, niceDefault=True)
            if poMsg not in messages:
                messages.append(poMsg)
                classDescr.labelsToPropagate.append(poMsg)
        if self.hasDescr:
            msgId = '%s_group_%s_descr' % (classDescr.name, self.name)
            poMsg = PoMessage(msgId, '', ' ')
            if poMsg not in messages:
                messages.append(poMsg)
                classDescr.labelsToPropagate.append(poMsg)
        if self.hasHelp:
            msgId = '%s_group_%s_help' % (classDescr.name, self.name)
            poMsg = PoMessage(msgId, '', ' ')
            if poMsg not in messages:
                messages.append(poMsg)
                classDescr.labelsToPropagate.append(poMsg)
        if self.hasHeaders:
            for i in range(self.nbOfHeaders):
                msgId = '%s_group_%s_col%d' % (classDescr.name, self.name, i+1)
                poMsg = PoMessage(msgId, '', ' ')
                if poMsg not in messages:
                    messages.append(poMsg)
                    classDescr.labelsToPropagate.append(poMsg)
        walkedGroups.add(self)
        if self.group and (self.group not in walkedGroups) and \
           not self.group.label:
            # We remember walked groups for avoiding infinite recursion.
            self.group.generateLabels(messages, classDescr, walkedGroups)

    def insertInto(self, widgets, groupDescrs, page, metaType):
        '''Inserts the GroupDescr instance corresponding to this Group instance
           into p_widgets, the recursive structure used for displaying all
           widgets in a given p_page, and returns this GroupDescr instance.'''
        # First, create the corresponding GroupDescr if not already in
        # p_groupDescrs.
        if self.name not in groupDescrs:
            groupDescr = groupDescrs[self.name] = GroupDescr(self, page,
                                                             metaType).get()
            # Insert the group at the higher level (ie, directly in p_widgets)
            # if the group is not itself in a group.
            if not self.group:
                widgets.append(groupDescr)
            else:
                outerGroupDescr = self.group.insertInto(widgets, groupDescrs,
                                                        page, metaType)
                GroupDescr.addWidget(outerGroupDescr, groupDescr)
        else:
            groupDescr = groupDescrs[self.name]
        return groupDescr

class Column:
    '''Used for describing a column within a Group like defined above.'''
    def __init__(self, width, align="left"):
        self.width = width
        self.align = align

class Import:
    '''Used for describing the place where to find the data to use for creating
       an object.'''
    def __init__(self, path, onElement=None, headers=(), sort=None):
        self.id = 'import'
        self.path = path
        # p_onElement hereafter must be a function (or a static method) that
        # will be called every time an element to import is found. It takes a
        # single arg that is the absolute filen name of the file to import,
        # within p_path. It must return a list of info about the element, or
        # None if the element must be ignored. The list will be used to display
        # information about the element in a tabular form.
        self.onElement = onElement
        # The following attribute must contain the names of the column headers
        # of the table that will display elements to import (retrieved from
        # calls to self.onElement). Every not-None element retrieved from
        # self.onElement must have the same length as self.headers.
        self.headers = headers
        # The following attribute must store a function or static method that
        # will be used to sort elements to import. It will be called with a
        # single param containing the list of all not-None elements as retrieved
        # by calls to self.onElement (but with one additional first element in
        # every list, which is the absolute file name of the element to import)
        # and must return a similar, sorted, list.
        self.sort = sort

class Search:
    '''Used for specifying a search for a given type.'''
    def __init__(self, name, group=None, sortBy='', limit=None, **fields):
        self.name = name
        self.group = group # Searches may be visually grouped in the portlet
        self.sortBy = sortBy
        self.limit = limit
        # In the dict below, keys are indexed field names and values are
        # search values.
        self.fields = fields
    @staticmethod
    def getIndexName(fieldName, usage='search'):
        '''Gets the name of the technical index that corresponds to field named
           p_fieldName. Indexes can be used for searching (p_usage="search") or
           for sorting (usage="sort"). The method returns None if the field
           named p_fieldName can't be used for p_usage.'''
        if fieldName == 'title':
            if usage == 'search':  return 'Title'
            else:                  return 'sortable_title'
            # Indeed, for field 'title', Plone has created a specific index
            # 'sortable_title', because index 'Title' is a ZCTextIndex
            # (for searchability) and can't be used for sorting.
        elif fieldName == 'description':
            if usage == 'search':  return 'Description'
            else:                  return None
        else:
            return 'get%s%s'% (fieldName[0].upper(),fieldName[1:])
    @staticmethod
    def getSearchValue(fieldName, fieldValue):
        '''Returns a transformed p_fieldValue for producing a valid search
           value as required for searching in the index corresponding to
           p_fieldName.'''
        if fieldName == 'title':
            # Title is a ZCTextIndex. We must split p_fieldValue into keywords.
            res = Keywords(fieldValue.decode('utf-8')).get()
        elif isinstance(fieldValue, basestring) and fieldValue.endswith('*'):
            v = fieldValue[:-1]
            # Warning: 'z' is higher than 'Z'!
            res = {'query':(v,v+'z'), 'range':'min:max'}
        elif type(fieldValue) in sequenceTypes:
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

# ------------------------------------------------------------------------------
class Type:
    '''Basic abstract class for defining any appy type.'''
    def __init__(self, validator, multiplicity, index, default, optional,
                 editDefault, show, page, group, layouts, move, indexed,
                 searchable, specificReadPermission, specificWritePermission,
                 width, height, maxChars, colspan, master, masterValue, focus,
                 historized, sync, mapping, label):
        # The validator restricts which values may be defined. It can be an
        # interval (1,None), a list of string values ['choice1', 'choice2'],
        # a regular expression, a custom function, a Selection instance, etc.
        self.validator = validator
        # Multiplicity is a tuple indicating the minimum and maximum
        # occurrences of values.
        self.multiplicity = multiplicity
        # Type of the index on the values. If you want to represent a simple
        # (ordered) list of values, specify None. If you want to
        # index your values with unordered integers or with other types like
        # strings (thus creating a dictionary of values instead of a list),
        # specify a type specification for the index, like Integer() or
        # String(). Note that this concept of "index" has nothing to do with
        # the concept of "database index" (see fields "indexed" and
        # "searchable" below). self.index is not yet used.
        self.index = index
        # Default value
        self.default = default
        # Is the field optional or not ?
        self.optional = optional
        # Is the field required or not ? (derived from multiplicity)
        self.required = self.multiplicity[0] > 0
        # May the user configure a default value ?
        self.editDefault = editDefault
        # Must the field be visible or not?
        self.show = show
        # When displaying/editing the whole object, on what page and phase must
        # this field value appear?
        self.page = Page.get(page)
        self.pageName = self.page.name
        # Within self.page, in what group of fields must this field value
        # appear?
        self.group = Group.get(group)
        # The following attribute allows to move a field back to a previous
        # position (useful for content types that inherit from others).
        self.move = move
        # If indexed is True, a database index will be set on the field for
        # fast access.
        self.indexed = indexed
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
        self.maxChars = maxChars
        # If the widget is in a group with multiple columns, the following
        # attribute specifies on how many columns to span the widget.
        self.colspan = colspan
        # The list of slaves of this field, if it is a master
        self.slaves = []
        # The behaviour of this field may depend on another, "master" field
        self.master = master
        if master:
            self.master.slaves.append(self)
        # When master has some value(s), there is impact on this field.
        self.masterValue = initMasterValue(masterValue)
        # If a field must retain attention in a particular way, set focus=True.
        # It will be rendered in a special way.
        self.focus = focus
        # If we must keep track of changes performed on a field, "historized"
        # must be set to True.
        self.historized = historized
        # self.sync below determines if the field representations will be
        # retrieved in a synchronous way by the browser or not (Ajax).
        self.sync = self.formatSync(sync)
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

    def init(self, name, klass, appName):
        '''When the application server starts, this secondary constructor is
           called for storing the name of the Appy field (p_name) and other
           attributes that are based on the name of the Appy p_klass, and the
           application name (p_appName).'''
        if hasattr(self, 'name'): return # Already initialized
        self.name = name
        # Determine prefix for this class
        if not klass: prefix = appName
        else:         prefix = getClassName(klass, appName)
        # Recompute the ID (and derived attributes) that may have changed if
        # we are in debug mode (because we recreate new Type instances).
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
            self.readPermission = 'View'
        wp = self.specificWritePermission
        if wp and not isinstance(wp, basestring):
            self.writePermission = '%s: Write %s %s' % (appName, prefix, name)
        elif wp and isinstance(wp, basestring):
            self.writePermission = wp
        else:
            self.writePermission = 'Modify portal content'
        if isinstance(self, Ref) and not self.isBack:
            # We must initialise the corresponding back reference
            self.back.klass = klass
            self.back.init(self.back.attribute, self.klass, appName)
        if isinstance(self, List):
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
        if isinstance(self, Ref) and self.isBack: return self
        res.init(self.name, klass, obj.getProductConfig().PROJECTNAME)
        return res

    def isMultiValued(self):
        '''Does this type definition allow to define multiple values?'''
        res = False
        maxOccurs = self.multiplicity[1]
        if (maxOccurs == None) or (maxOccurs > 1):
            res = True
        return res

    def isSortable(self, usage):
        '''Can fields of this type be used for sorting purposes (when sorting
           search results (p_usage="search") or when sorting reference fields
           (p_usage="ref")?'''
        if usage == 'search':
            return self.indexed and not self.isMultiValued() and not \
                   ((self.type == 'String') and self.isSelection())
        elif usage == 'ref':
            return self.type in ('Integer', 'Float', 'Boolean', 'Date') or \
                   ((self.type == 'String') and (self.format == 0))

    def isShowable(self, obj, layoutType):
        '''When displaying p_obj on a given p_layoutType, must we show this
           field?'''
        # Do not show field if it is optional and not selected in tool
        if self.optional:
            tool = obj.getTool().appy()
            fieldName = 'optionalFieldsFor%s' % obj.meta_type
            fieldValue = getattr(tool, fieldName, ())
            if self.name not in fieldValue:
                return False
        # Check if the user has the permission to view or edit the field
        if layoutType == 'edit': perm = self.writePermission
        else:                    perm = self.readPermission
        if not obj.allows(perm): return False
        # Evaluate self.show
        if callable(self.show):
            res = self.callMethod(obj, self.show)
        else:
            res = self.show
        # Take into account possible values 'view', 'edit', 'search'...
        if res in ('view', 'edit', 'result'): return res == layoutType
        return bool(res)

    def isClientVisible(self, obj):
        '''This method returns True if this field is visible according to
           master/slave relationships.'''
        masterData = self.getMasterData()
        if not masterData: return True
        else:
            master, masterValue = masterData
            reqValue = master.getRequestValue(obj.REQUEST)
            reqValue = master.getStorableValue(reqValue)
            # reqValue can be a list or not
            if type(reqValue) not in sequenceTypes:
                return reqValue in masterValue
            else:
                for m in masterValue:
                    for r in reqValue:
                        if m == r: return True

    def formatSync(self, sync):
        '''Creates a dictionary indicating, for every layout type, if the field
           value must be retrieved synchronously or not.'''
        if isinstance(sync, bool):
            sync = {'edit': sync, 'view': sync, 'cell': sync}
        for layoutType in ('edit', 'view', 'cell'):
            if layoutType not in sync:
                sync[layoutType] = False
        return sync

    def formatMapping(self, mapping):
        '''Creates a dict of mappings, one entry by label type (label, descr,
           help).'''
        if isinstance(mapping, dict):
            # Is it a dict like {'label':..., 'descr':...}, or is it directly a
            # dict with a mapping?
            for k, v in mapping.iteritems():
                if (k not in labelTypes) or isinstance(v, basestring):
                    # It is already a mapping
                    return {'label':mapping, 'descr':mapping, 'help':mapping}
            # If we are here, we have {'label':..., 'descr':...}. Complete
            # it if necessary.
            for labelType in labelTypes:
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
        # Derive "view" and "cell" layouts from the "edit" layout when relevant
        if 'view' not in layouts:
            layouts['view'] = Table(other=layouts['edit'], derivedType='view')
        # Create the "cell" layout from the 'view' layout if not specified.
        if 'cell' not in layouts:
            layouts['cell'] = Table(other=layouts['view'], derivedType='cell')
        # Put the required CSS classes in the layouts
        layouts['cell'].addCssClasses('noStyle')
        if self.focus:
            # We need to make it flashy
            layouts['view'].addCssClasses('appyFocus')
            layouts['edit'].addCssClasses('appyFocus')
        # If layouts are the default ones, set width=None instead of width=100%
        # for the field if it is not in a group.
        if areDefault and not self.group:
            for layoutType in layouts.iterkeys():
                layouts[layoutType].width = ''
        # Remove letters "r" from the layouts if the field is not required.
        if not self.required:
            for layoutType in layouts.iterkeys():
                layouts[layoutType].removeElement('r')
        # Derive some boolean values from the layouts.
        self.hasLabel = self.hasLayoutElement('l', layouts)
        self.hasDescr = self.hasLayoutElement('d', layouts)
        self.hasHelp  = self.hasLayoutElement('h', layouts)
        # Store Table instance's dicts instead of instances: this way, they can
        # be manipulated in ZPTs.
        for layoutType in layouts.iterkeys():
            layouts[layoutType] = layouts[layoutType].get()
        return layouts

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
           value for the Type constructor.'''
        res = '{'
        for k, v in self.layouts.iteritems():
            res += '"%s":"%s",' % (k, v['layoutString'])
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

    def getCss(self, layoutType):
        '''This method returns a list of CSS files that are required for
           displaying widgets of self's type on a given p_layoutType.'''

    def getJs(self, layoutType):
        '''This method returns a list of Javascript files that are required for
           displaying widgets of self's type on a given p_layoutType.'''

    def getValue(self, obj):
        '''Gets, on_obj, the value conforming to self's type definition.'''
        value = getattr(obj.aq_base, self.name, None)
        if self.isEmptyValue(value):
            # If there is no value, get the default value if any
            if not self.editDefault:
                # Return self.default, of self.default() if it is a method
                if callable(self.default):
                    try:
                        return self.callMethod(obj, self.default)
                    except Exception, e:
                        # Already logged. Here I do not raise the exception,
                        # because it can be raised as the result of reindexing
                        # the object in situations that are not foreseen by
                        # method in self.default.
                        return None
                else:
                    return self.default
            # If value is editable, get the default value from the tool
            portalTypeName = obj._appy_getPortalType(obj.REQUEST)
            tool = obj.getTool().appy()
            return getattr(tool, 'defaultValueFor%s' % self.labelId)
        return value

    def getFormattedValue(self, obj, value):
        '''p_value is a real p_obj(ect) value from a field from this type. This
           method returns a pretty, string-formatted version, for displaying
           purposes. Needs to be overridden by some child classes.'''
        if self.isEmptyValue(value): return ''
        return value

    def getIndexType(self):
        '''Returns the name of the technical, Zope-level index type for this
           field.'''
        return 'FieldIndex'

    def getIndexValue(self, obj, forSearch=False):
        '''This method returns a version for this field value on p_obj that is
           ready for indexing purposes. Needs to be overridden by some child
           classes.

           If p_forSearch is True, it will return a "string" version of the
           index value suitable for a global search.'''
        value = self.getValue(obj)
        if forSearch and (value != None):
            if isinstance(value, unicode):
                res = value.encode('utf-8')
            elif type(value) in sequenceTypes:
                res = []
                for v in value:
                    if isinstance(v, unicode): res.append(v.encode('utf-8'))
                    else: res.append(str(v))
                res = ' '.join(res)
            else:
                res = str(value)
            return res
        return value

    def getRequestValue(self, request):
        '''Gets the string (or list of strings if multi-valued)
           representation of this field as found in the p_request.'''
        return request.get(self.name, None)

    def getStorableValue(self, value):
        '''p_value is a valid value initially computed through calling
           m_getRequestValue. So, it is a valid string (or list of strings)
           representation of the field value coming from the request.
           This method computes the real (potentially converted or manipulated
           in some other way) value as can be stored in the database.'''
        if self.isEmptyValue(value): return None
        return value

    def getMasterData(self):
        '''Gets the master of this field (and masterValue) or, recursively, of
           containing groups when relevant.'''
        if self.master: return (self.master, self.masterValue)
        if self.group: return self.group.getMasterData()

    def isEmptyValue(self, value, obj=None):
        '''Returns True if the p_value must be considered as an empty value.'''
        return value in nullValues

    def validateValue(self, obj, value):
        '''This method may be overridden by child classes and will be called at
           the right moment by m_validate defined below for triggering
           type-specific validation. p_value is never empty.'''
        return None

    def securityCheck(self, obj, value):
        '''This method performs some security checks on the p_value that
           represents user input.'''
        if not isinstance(value, basestring): return
        # Search Javascript code in the value (prevent XSS attacks).
        if '<script' in value:
            obj.log('Detected Javascript in user input.', type='error')
            raise 'Your behaviour is considered a security attack. System ' \
                  'administrator has been warned.'

    def validate(self, obj, value):
        '''This method checks that p_value, coming from the request (p_obj is
           being created or edited) and formatted through a call to
           m_getRequestValue defined above, is valid according to this type
           definition. If it is the case, None is returned. Else, a translated
           error message is returned.'''
        # Check that a value is given if required.
        if self.isEmptyValue(value, obj):
            if self.required and self.isClientVisible(obj):
                # If the field is required, but not visible according to
                # master/slave relationships, we consider it not to be required.
                return obj.translate('field_required')
            else:
                return None
        # Perform security checks on p_value
        self.securityCheck(obj, value)
        # Triggers the sub-class-specific validation for this value
        message = self.validateValue(obj, value)
        if message: return message
        # Evaluate the custom validator if one has been specified
        value = self.getStorableValue(value)
        if self.validator and (type(self.validator) in validatorTypes):
            obj = obj.appy()
            if type(self.validator) != validatorTypes[-1]:
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
                    # If the regular expression is among the default ones, we
                    # generate a specific error message.
                    if self.validator == String.EMAIL:
                        return obj.translate('bad_email')
                    elif self.validator == String.URL:
                        return obj.translate('bad_url')
                    elif self.validator == String.ALPHANUMERIC:
                        return obj.translate('bad_alphanumeric')
                    else:
                        return obj.translate('field_invalid')

    def store(self, obj, value):
        '''Stores the p_value (produced by m_getStorableValue) that complies to
           p_self type definition on p_obj.'''
        setattr(obj, self.name, value)

    def clone(self, forTool=True):
        '''Returns a clone of myself. If p_forTool is True, the clone will be
           adapted to its life into the tool.'''
        res = copy.copy(self)
        res.group = copy.copy(self.group)
        res.page = copy.copy(self.page)
        if not forTool: return res
        # A field added to the tool can't have parameters that would lead to the
        # creation of new fields in the tool.
        res.editDefault = False
        res.optional = False
        res.show = True
        # Set default layouts for all Tool fields
        res.layouts = res.formatLayouts(None)
        res.specificReadPermission = False
        res.specificWritePermission = False
        res.multiplicity = (0, self.multiplicity[1])
        if callable(res.validator):
            # We will not be able to call this function from the tool.
            res.validator = None
        return res

    def callMethod(self, obj, method, raiseOnError=True):
        '''This method is used to call a p_method on p_obj. p_method is part of
           this type definition (ie a default method, the method of a Computed
           field, a method used for showing or not a field...). Normally, those
           methods are called without any arg. But one may need, within the
           method, to access the related field. This method tries to call
           p_method with no arg *or* with the field arg.'''
        obj = obj.appy()
        try:
            return method(obj)
        except TypeError, te:
            # Try a version of the method that would accept self as an
            # additional parameter.
            try:
                return method(obj, self)
            except Exception, e:
                obj.log(Traceback.get(), type='error')
                if raiseOnError: raise e
                else: return str(e)
        except Exception, e:
            obj.log(Traceback.get(), type='error')
            if raiseOnError: raise e
            else: return str(e)

class Integer(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=6, height=None,
                 maxChars=13, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      searchable, specificReadPermission,
                      specificWritePermission, width, height, maxChars, colspan,
                      master, masterValue, focus, historized, True, mapping,
                      label)
        self.pythonType = long

    def validateValue(self, obj, value):
        try:
            value = self.pythonType(value)
        except ValueError:
            return obj.translate('bad_%s' % self.pythonType.__name__)

    def getStorableValue(self, value):
        if not self.isEmptyValue(value): return self.pythonType(value)

    def getFormattedValue(self, obj, value):
        if self.isEmptyValue(value): return ''
        return str(value)

class Float(Type):
    allowedDecimalSeps = (',', '.')
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=6, height=None,
                 maxChars=13, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None,
                 precision=None, sep=(',', '.')):
        # The precision is the number of decimal digits. This number is used
        # for rendering the float, but the internal float representation is not
        # rounded.
        self.precision = precision
        # The decimal separator can be a tuple if several are allowed, ie
        # ('.', ',')
        if type(sep) not in sequenceTypes:
            self.sep = (sep,)
        else:
            self.sep = sep
        # Check that the separator(s) are among allowed decimal separators
        for sep in self.sep:
            if sep not in Float.allowedDecimalSeps:
                raise 'Char "%s" is not allowed as decimal separator.' % sep
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      False, specificReadPermission, specificWritePermission,
                      width, height, maxChars, colspan, master, masterValue,
                      focus, historized, True, mapping, label)
        self.pythonType = float

    def getFormattedValue(self, obj, value):
        if self.isEmptyValue(value): return ''
        # Determine the field separator
        sep = self.sep[0]
        # Produce the rounded string representation
        if self.precision == None:
            res = str(value)
        else:
            format = '%%.%df' % self.precision
            res = format % value
        # Use the correct decimal separator
        res = res.replace('.', sep)
        # Remove the decimal part if = 0
        splitted = res.split(sep)
        if len(splitted) > 1:
            try:
                decPart = int(splitted[1])
                if decPart == 0:
                    res = splitted[0]
            except ValueError:
                # This exception may occur when the float value has an "exp"
                # part, like in this example: 4.345e-05.
                pass
        return res

    def validateValue(self, obj, value):
        # Replace used separator with the Python separator '.'
        for sep in self.sep: value = value.replace(sep, '.')
        try:
            value = self.pythonType(value)
        except ValueError:
            return obj.translate('bad_%s' % self.pythonType.__name__)

    def getStorableValue(self, value):
        if not self.isEmptyValue(value):
            for sep in self.sep: value = value.replace(sep, '.')
            return self.pythonType(value)

class String(Type):
    # Some predefined regular expressions that may be used as validators
    c = re.compile
    EMAIL = c('[a-zA-Z][\w\.-]*[a-zA-Z0-9]@[a-zA-Z0-9][\w\.-]*[a-zA-Z0-9]\.' \
              '[a-zA-Z][a-zA-Z\.]*[a-zA-Z]')
    ALPHANUMERIC = c('[\w-]+')
    URL = c('(http|https):\/\/[a-z0-9]+([\-\.]{1}[a-z0-9]+)*(\.[a-z]{2,5})?' \
            '(([0-9]{1,5})?\/.*)?')

    # Some predefined functions that may also be used as validators
    @staticmethod
    def _MODULO_97(obj, value, complement=False):
        '''p_value must be a string representing a number, like a bank account.
           this function checks that the 2 last digits are the result of
           computing the modulo 97 of the previous digits. Any non-digit
           character is ignored. If p_complement is True, it does compute the
           complement of modulo 97 instead of modulo 97. p_obj is not used;
           it will be given by the Appy validation machinery, so it must be
           specified as parameter. The function returns True if the check is
           successful.'''
        if not value: return True # Plone calls me erroneously for
        # non-mandatory fields.
        # First, remove any non-digit char
        v = ''
        for c in value:
            if digit.match(c): v += c
        # There must be at least 3 digits for performing the check
        if len(v) < 3: return False
        # Separate the real number from the check digits
        number = int(v[:-2])
        checkNumber = int(v[-2:])
        # Perform the check
        if complement:
            return (97 - (number % 97)) == checkNumber
        else:
            # The check number can't be 0. In this case, we force it to be 97.
            # This is the way Belgian bank account numbers work. I hope this
            # behaviour is general enough to be implemented here.
            mod97 = (number % 97)
            if mod97 == 0: return checkNumber == 97
            else:          return checkNumber == mod97
    @staticmethod
    def MODULO_97(obj, value): return String._MODULO_97(obj, value)
    @staticmethod
    def MODULO_97_COMPLEMENT(obj, value):
        return String._MODULO_97(obj, value, True)
    BELGIAN_ENTERPRISE_NUMBER = MODULO_97_COMPLEMENT
    @staticmethod
    def IBAN(obj, value):
        '''Checks that p_value corresponds to a valid IBAN number. IBAN stands
           for International Bank Account Number (ISO 13616). If the number is
           valid, the method returns True.'''
        if not value: return True # Plone calls me erroneously for
        # non-mandatory fields.
        # First, remove any non-digit or non-letter char
        v = ''
        for c in value:
            if alpha.match(c): v += c
        # Maximum size is 34 chars
        if (len(v) < 8) or (len(v) > 34): return False
        # 2 first chars must be a valid country code
        if not countries.exists(v[:2].upper()): return False
        # 2 next chars are a control code whose value must be between 0 and 96.
        try:
            code = int(v[2:4])
            if (code < 0) or (code > 96): return False
        except ValueError:
            return False
        # Perform the checksum
        vv = v[4:] + v[:4] # Put the 4 first chars at the end.
        nv = ''
        for c in vv:
            # Convert each letter into a number (A=10, B=11, etc)
            # Ascii code for a is 65, so A=10 if we perform "minus 55"
            if letter.match(c): nv += str(ord(c.upper()) - 55)
            else: nv += c
        return int(nv) % 97 == 1
    @staticmethod
    def BIC(obj, value):
        '''Checks that p_value corresponds to a valid BIC number. BIC stands
           for Bank Identifier Code (ISO 9362). If the number is valid, the
           method returns True.'''
        if not value: return True # Plone calls me erroneously for
        # non-mandatory fields.
        # BIC number must be 8 or 11 chars
        if len(value) not in (8, 11): return False
        # 4 first chars, representing bank name, must be letters
        for c in value[:4]:
            if not letter.match(c): return False
        # 2 next chars must be a valid country code
        if not countries.exists(value[4:6].upper()): return False
        # Last chars represent some location within a country (a city, a
        # province...). They can only be letters or figures.
        for c in value[6:]:
            if not alpha.match(c): return False
        return True

    # Possible values for "format"
    LINE = 0
    TEXT = 1
    XHTML = 2
    PASSWORD = 3
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, format=LINE,
                 show=True, page='main', group=None, layouts=None, move=0,
                 indexed=False, searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None,
                 transform='none'):
        self.format = format
        # The following field has a direct impact on the text entered by the
        # user. It applies a transformation on it, exactly as does the CSS
        # "text-transform" property. Allowed values are those allowed for the
        # CSS property: "none" (default), "uppercase", "capitalize" or
        # "lowercase".
        self.transform = transform
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      searchable, specificReadPermission,
                      specificWritePermission, width, height, maxChars, colspan,
                      master, masterValue, focus, historized, True, mapping,
                      label)
        self.isSelect = self.isSelection()
        # Default width, height and maxChars vary according to String format
        if width == None:
            if format == String.TEXT: self.width  = 60
            else:                     self.width  = 30
        if height == None:
            if format == String.TEXT: self.height = 5
            elif self.isSelect:       self.height = 4
            else:                     self.height = 1
        if maxChars == None:
            if self.isSelect: pass
            elif format == String.LINE: self.maxChars = 256
            elif format == String.TEXT: self.maxChars = 9999
            elif format == String.XHTML: self.maxChars = 9999
            elif format == String.PASSWORD: self.maxChars = 20
        self.filterable = self.indexed and (self.format == String.LINE) and \
                          not self.isSelect

    def isSelection(self):
        '''Does the validator of this type definition define a list of values
           into which the user must select one or more values?'''
        res = True
        if type(self.validator) in (list, tuple):
            for elem in self.validator:
                if not isinstance(elem, basestring):
                    res = False
                    break
        else:
            if not isinstance(self.validator, Selection):
                res = False
        return res

    def getDefaultLayouts(self):
        '''Returns the default layouts for this type. Default layouts can vary
           acccording to format or multiplicity.'''
        if self.format in (String.TEXT, String.XHTML):
            return {'view': 'l-f', 'edit': 'lrv-d-f'}
        elif self.isMultiValued():
            return {'view': 'l-f', 'edit': 'lrv-f'}

    def getValue(self, obj):
        value = Type.getValue(self, obj)
        if not value:
            if self.isMultiValued(): return emptyTuple
            else: return value
        if isinstance(value, basestring) and self.isMultiValued():
            value = [value]
        # Some backward compatibilities with Archetypes.
        elif value.__class__.__name__ == 'BaseUnit':
            try:
                value = unicode(value)
            except UnicodeDecodeError:
                value = str(value)
        elif isinstance(value, tuple):
            # When Appy storage was based on Archetype, multivalued string
            # fields stored values as tuples of unicode strings.
            value = list(value)
        return value

    def getFormattedValue(self, obj, value):
        if self.isEmptyValue(value): return ''
        res = value
        if self.isSelect:
            if isinstance(self.validator, Selection):
                # Value(s) come from a dynamic vocabulary
                val = self.validator
                if self.isMultiValued():
                    return [val.getText(obj, v, self) for v in value]
                else:
                    return val.getText(obj, value, self)
            else:
                # Value(s) come from a fixed vocabulary whose texts are in
                # i18n files.
                t = obj.translate
                if self.isMultiValued():
                    res = [t('%s_list_%s' % (self.labelId, v)) for v in value]
                else:
                    res = t('%s_list_%s' % (self.labelId, value))
        elif not isinstance(value, basestring):
            # Archetypes "Description" fields may hold a BaseUnit instance.
            try:
                res = unicode(value)
            except UnicodeDecodeError:
                res = str(value)
        # If value starts with a carriage return, add a space; else, it will
        # be ignored.
        if isinstance(res, basestring) and \
           (res.startswith('\n') or res.startswith('\r\n')): res = ' ' + res
        return res

    emptyStringTuple = ('',)
    emptyValuesCatalogIgnored = (None, '')
    def getIndexValue(self, obj, forSearch=False):
        '''For indexing purposes, we return only strings, not unicodes.'''
        res = Type.getIndexValue(self, obj, forSearch)
        if isinstance(res, unicode):
            res = res.encode('utf-8')
        # Ugly portal_catalog: if I give an empty tuple as index value,
        # portal_catalog keeps the previous value! If I give him a tuple
        # containing an empty string, it is ok.
        if isinstance(res, tuple) and not res: res = self.emptyStringTuple
        # Ugly portal_catalog: if value is an empty string or None, it keeps
        # the previous index value!
        if res in self.emptyValuesCatalogIgnored: res = ' '
        return res

    def getPossibleValues(self,obj,withTranslations=False,withBlankValue=False):
        '''Returns the list of possible values for this field if it is a
           selection field. If p_withTranslations is True,
           instead of returning a list of string values, the result is a list
           of tuples (s_value, s_translation). If p_withBlankValue is True, a
           blank value is prepended to the list, excepted if the type is
           multivalued.'''
        if not self.isSelect: raise 'This field is not a selection.'
        if isinstance(self.validator, Selection):
            # We need to call self.methodName for getting the (dynamic) values.
            # If methodName begins with _appy_, it is a special Appy method:
            # we will call it on the Mixin (=p_obj) directly. Else, it is a
            # user method: we will call it on the wrapper (p_obj.appy()). Some
            # args can be hidden into p_methodName, separated with stars,
            # like in this example: method1*arg1*arg2. Only string params are
            # supported.
            methodName = self.validator.methodName
            # Unwrap parameters if any.
            if methodName.find('*') != -1:
                elems = methodName.split('*')
                methodName = elems[0]
                args = elems[1:]
            else:
                args = ()
            # On what object must we call the method that will produce the
            # values?
            if methodName.startswith('tool:'):
                obj = obj.getTool()
                methodName = methodName[5:]
            # Do we need to call the method on the object or on the wrapper?
            if methodName.startswith('_appy_'):
                exec 'res = obj.%s(*args)' % methodName
            else:
                exec 'res = obj.appy().%s(*args)' % methodName
            if not withTranslations: res = [v[0] for v in res]
            elif isinstance(res, list): res = res[:]
        else:
            # The list of (static) values is directly given in self.validator.
            res = []
            for value in self.validator:
                label = '%s_list_%s' % (self.labelId, value)
                if withTranslations:
                    res.append( (value, obj.translate(label)) )
                else:
                    res.append(value)
        if withBlankValue and not self.isMultiValued():
            # Create the blank value to insert at the beginning of the list
            if withTranslations:
                blankValue = ('', obj.translate('choose_a_value'))
            else:
                blankValue = ''
            # Insert the blank value in the result
            if isinstance(res, tuple):
                res = (blankValue,) + res
            else:
                res.insert(0, blankValue)
        return res

    def validateValue(self, obj, value):
        if not self.isSelect: return
        # Check that the value is among possible values
        possibleValues = self.getPossibleValues(obj)
        if isinstance(value, basestring):
            error = value not in possibleValues
        else:
            error = False
            for v in value:
                if v not in possibleValues:
                    error = True
                    break
        if error: return obj.translate('bad_select_value')

    accents = {'é':'e','è':'e','ê':'e','ë':'e','à':'a','â':'a','ä':'a',
               'ù':'u','û':'u','ü':'u','î':'i','ï':'i','ô':'o','ö':'o',
               'ç':'c', 'Ç':'C',
               'Ù':'U','Û':'U','Ü':'U','Î':'I','Ï':'I','Ô':'O','Ö':'O',
               'É':'E','È':'E','Ê':'E','Ë':'E','À':'A','Â':'A','Ä':'A'}
    def applyTransform(self, value):
        '''Applies a transform as required by self.transform on single
           value p_value.'''
        if self.transform in ('uppercase', 'lowercase'):
            # For those transforms, I will remove any accent, because
            # (1) 'é'.upper() or 'Ê'.lower() has no effect;
            # (2) most of the time, if the user wants to apply such effect, it
            #     is for ease of data manipulation, so I guess without accent.
            for c, n in self.accents.iteritems():
                if c in value: value = value.replace(c, n)
        # Apply the transform
        if   self.transform == 'lowercase':  return value.lower()
        elif self.transform == 'uppercase':  return value.upper()
        elif self.transform == 'capitalize': return value.capitalize()
        return value

    def getStorableValue(self, value):
        if not self.isEmptyValue(value) and (self.transform != 'none'):
            if isinstance(value, basestring):
                return self.applyTransform(value)
            else:
                return [self.applyTransform(v) for v in value]
        return value

    def store(self, obj, value):
        if self.isMultiValued() and isinstance(value, basestring):
            value = [value]
        # Truncate the result if longer than self.maxChars
        if self.maxChars and isinstance(value, basestring) and \
           (len(value) > self.maxChars):
            value = value[:self.maxChars]
        exec 'obj.%s = value' % self.name

    def getIndexType(self):
        '''Index type varies depending on String parameters.'''
        # If String.isSelect, be it multivalued or not, we define a ZCTextIndex:
        # this way we can use AND/OR operator.
        if self.isSelect or (self.format in (String.TEXT, String.XHTML)):
            return 'ZCTextIndex'
        return Type.getIndexType(self)

    def getJs(self, layoutType):
        if (layoutType == 'edit') and (self.format == String.XHTML):
            return ('tiny_mce/tiny_mce.js',)

class Boolean(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, layouts = None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      searchable, specificReadPermission,
                      specificWritePermission, width, height, None, colspan,
                      master, masterValue, focus, historized, True, mapping,
                      label)
        self.pythonType = bool

    def getDefaultLayouts(self):
        return {'view': 'l;f!-', 'edit': Table('f;lrv;=', width=None)}

    def getValue(self, obj):
        '''Never returns "None". Returns always "True" or "False", even if
           "None" is stored in the DB.'''
        value = Type.getValue(self, obj)
        if value == None: return False
        return value

    def getFormattedValue(self, obj, value):
        if value: res = obj.translate('yes', domain='plone')
        else:     res = obj.translate('no', domain='plone')
        return res

    def getStorableValue(self, value):
        if not self.isEmptyValue(value):
            exec 'res = %s' % value
            return res

class Date(Type):
    # Possible values for "format"
    WITH_HOUR = 0
    WITHOUT_HOUR = 1
    dateParts = ('year', 'month', 'day')
    hourParts = ('hour', 'minute')
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False,
                 format=WITH_HOUR, calendar=True,
                 startYear=time.localtime()[0]-10,
                 endYear=time.localtime()[0]+10, reverseYears=False,
                 show=True, page='main', group=None, layouts=None, move=0,
                 indexed=False, searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None):
        self.format = format
        self.calendar = calendar
        self.startYear = startYear
        self.endYear = endYear
        # If reverseYears is True, in the selection box, available years, from
        # self.startYear to self.endYear will be listed in reverse order.
        self.reverseYears = reverseYears
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      searchable, specificReadPermission,
                      specificWritePermission, width, height, None, colspan,
                      master, masterValue, focus, historized, True, mapping,
                      label)

    def getCss(self, layoutType):
        if (layoutType == 'edit') and self.calendar: return ('calendar.css',)

    def getJs(self, layoutType):
        if (layoutType == 'edit') and self.calendar: return ('calendar.js',)

    def getSelectableYears(self):
        '''Gets the list of years one may select for this field.'''
        res = range(self.startYear, self.endYear + 1)
        if self.reverseYears: res.reverse()
        return res

    def validateValue(self, obj, value):
        DateTime = obj.getProductConfig().DateTime
        try:
            value = DateTime(value)
        except DateTime.DateError, ValueError:
            return obj.translate('bad_date')

    def getFormattedValue(self, obj, value):
        if self.isEmptyValue(value): return ''
        res = value.strftime('%d/%m/') + str(value.year())
        if self.format == Date.WITH_HOUR:
            res += ' %s' % value.strftime('%H:%M')
        return res

    def getRequestValue(self, request):
        # Manage the "date" part
        value = ''
        for part in self.dateParts:
            valuePart = request.get('%s_%s' % (self.name, part), None)
            if not valuePart: return None
            value += valuePart + '/'
        value = value[:-1]
        # Manage the "hour" part
        if self.format == self.WITH_HOUR:
            value += ' '
            for part in self.hourParts:
                valuePart = request.get('%s_%s' % (self.name, part), None)
                if not valuePart: return None
                value += valuePart + ':'
            value = value[:-1]
        return value

    def getStorableValue(self, value):
        if not self.isEmptyValue(value):
            import DateTime
            return DateTime.DateTime(value)

class File(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None,
                 isImage=False):
        self.isImage = isImage
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      False, specificReadPermission, specificWritePermission,
                      width, height, None, colspan, master, masterValue, focus,
                      historized, True, mapping, label)

    @staticmethod
    def getFileObject(filePath, fileName=None, zope=False):
        '''Returns a File instance as can be stored in the database or
           manipulated in code, filled with content from a file on disk,
           located at p_filePath. If you want to give it a name that is more
           sexy than the actual basename of filePath, specify it in
           p_fileName.

           If p_zope is True, it will be the raw Zope object = an instance of
           OFS.Image.File. Else, it will be a FileWrapper instance from Appy.'''
        f = file(filePath, 'rb')
        if not fileName:
            fileName = os.path.basename(filePath)
        fileId = 'file.%f' % time.time()
        import OFS.Image
        res = OFS.Image.File(fileId, fileName, f)
        res.filename = fileName
        res.content_type = mimetypes.guess_type(fileName)[0]
        f.close()
        if not zope: res = FileWrapper(res)
        return res

    def getValue(self, obj):
        value = Type.getValue(self, obj)
        if value: value = FileWrapper(value)
        return value

    def getFormattedValue(self, obj, value):
        if not value: return value
        return value._atFile

    def getRequestValue(self, request):
        return request.get('%s_file' % self.name)

    def getDefaultLayouts(self): return {'view':'lf','edit':'lrv-f'}

    def isEmptyValue(self, value, obj=None):
        '''Must p_value be considered as empty?'''
        if not obj: return Type.isEmptyValue(self, value)
        if value: return False
        # If "nochange", the value must not be considered as empty
        return obj.REQUEST.get('%s_delete' % self.name) != 'nochange'

    imageExts = ('.jpg', '.jpeg', '.png', '.gif')
    def validateValue(self, obj, value):
        form = obj.REQUEST.form
        action = '%s_delete' % self.name
        if (not value or not value.filename) and form.has_key(action) and \
            not form[action]:
            # If this key is present but empty, it means that the user selected
            # "replace the file with a new one". So in this case he must provide
            # a new file to upload.
            return obj.translate('file_required')
        # Check that, if self.isImage, the uploaded file is really an image
        if value and value.filename and self.isImage:
            ext = os.path.splitext(value.filename)[1].lower()
            if ext not in File.imageExts:
                return obj.translate('image_required')

    defaultMimeType = 'application/octet-stream'
    def store(self, obj, value):
        '''Stores the p_value that represents some file. p_value can be:
           * an instance of Zope class ZPublisher.HTTPRequest.FileUpload. In
             this case, it is file content coming from a HTTP POST;
           * an instance of Zope class OFS.Image.File;
           * an instance of appy.gen.utils.FileWrapper, which wraps an instance
             of OFS.Image.File and adds useful methods for manipulating it;
           * a string. In this case, the string represents the path of a file
             on disk;
           * a 2-tuple (fileName, fileContent) where:
             - fileName is the name of the file (ie "myFile.odt")
             - fileContent is the binary or textual content of the file or an
                           open file handler.
           * a 3-tuple (fileName, fileContent, mimeType) where
             - fileName and fileContent have the same meaning than above;
             - mimeType is the MIME type of the file.
        '''
        if value:
            ZFileUpload = obj.o.getProductConfig().FileUpload
            OFSImageFile = obj.o.getProductConfig().File
            if isinstance(value, ZFileUpload):
                # The file content comes from a HTTP POST.
                # Retrieve the existing value, or create one if None
                existingValue = getattr(obj.aq_base, self.name, None)
                if not existingValue:
                    existingValue = OFSImageFile(self.name, '', '')
                # Set mimetype
                if value.headers.has_key('content-type'):
                    mimeType = value.headers['content-type']
                else:
                    mimeType = File.defaultMimeType
                existingValue.content_type = mimeType
                # Set filename
                fileName = value.filename
                filename= fileName[max(fileName.rfind('/'),fileName.rfind('\\'),
                                       fileName.rfind(':'))+1:]
                existingValue.filename = fileName
                # Set content
                existingValue.manage_upload(value)
                setattr(obj, self.name, existingValue)
            elif isinstance(value, OFSImageFile):
                setattr(obj, self.name, value)
            elif isinstance(value, FileWrapper):
                setattr(obj, self.name, value._atFile)
            elif isinstance(value, basestring):
                setattr(obj, self.name, File.getFileObject(value, zope=True))
            elif type(value) in sequenceTypes:
                # It should be a 2-tuple or 3-tuple
                fileName = None
                mimeType = None
                if len(value) == 2:
                    fileName, fileContent = value
                elif len(value) == 3:
                    fileName, fileContent, mimeType = value
                else:
                    raise WRONG_FILE_TUPLE
                if fileName:
                    fileId = 'file.%f' % time.time()
                    zopeFile = OFSImageFile(fileId, fileName, fileContent)
                    zopeFile.filename = fileName
                    if not mimeType:
                        mimeType = mimetypes.guess_type(fileName)[0]
                    zopeFile.content_type = mimeType
                    setattr(obj, self.name, zopeFile)
        else:
            # I store value "None", excepted if I find in the request the desire
            # to keep the file unchanged.
            action = obj.REQUEST.get('%s_delete' % self.name, None)
            if action == 'nochange': pass
            else: setattr(obj, self.name, None)

class Ref(Type):
    def __init__(self, klass=None, attribute=None, validator=None,
                 multiplicity=(0,1), index=None, default=None, optional=False,
                 editDefault=False, add=False, addConfirm=False, noForm=False,
                 link=True, unlink=False, back=None, show=True, page='main',
                 group=None, layouts=None, showHeaders=False, shownInfo=(),
                 select=None, maxPerPage=30, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=5,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None,
                 queryable=False, queryFields=None, queryNbCols=1):
        self.klass = klass
        self.attribute = attribute
        # May the user add new objects through this ref ?
        self.add = add
        # When the user adds a new object, must a confirmation popup be shown?
        self.addConfirm = addConfirm
        # If noForm is True, when clicking to create an object through this ref,
        # the object will be created automatically, and no creation form will
        # be presented to the user.
        self.noForm = noForm
        # May the user link existing objects through this ref?
        self.link = link
        # May the user unlink existing objects?
        self.unlink = unlink
        self.back = None
        if back:
            # It is a forward reference
            self.isBack = False
            # Initialise the backward reference
            self.back = back
            self.backd = back.__dict__
            back.isBack = True
            back.back = self
            back.backd = self.__dict__
            setattr(klass, back.attribute, back)
        # When displaying a tabular list of referenced objects, must we show
        # the table headers?
        self.showHeaders = showHeaders
        # When displaying referenced object(s), we will display its title + all
        # other fields whose names are listed in the following attribute.
        self.shownInfo = list(shownInfo)
        if not self.shownInfo: self.shownInfo.append('title')
        self.shownInfoWidths = []
        for i in range(len(self.shownInfo)):
            if '*' in self.shownInfo[i]:
                # The width is also specified
                info, width = self.shownInfo[i].split('*',1)
                self.shownInfo[i] = info
                self.shownInfoWidths.append(width)
            else:
                # No width is specified
                self.shownInfoWidths.append('')
        # If a method is defined in this field "select", it will be used to
        # filter the list of available tied objects.
        self.select = select
        # Maximum number of referenced objects shown at once.
        self.maxPerPage = maxPerPage
        # Specifies sync
        sync = {'view': False, 'edit':True}
        # If param p_queryable is True, the user will be able to perform queries
        # from the UI within referenced objects.
        self.queryable = queryable
        # Here is the list of fields that will appear on the search screen.
        # If None is specified, by default we take every indexed field
        # defined on referenced objects' class.
        self.queryFields = queryFields
        # The search screen will have this number of columns
        self.queryNbCols = queryNbCols
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      False, specificReadPermission, specificWritePermission,
                      width, height, None, colspan, master, masterValue, focus,
                      historized, sync, mapping, label)
        self.validable = self.link

    def getDefaultLayouts(self):
        return {'view': Table('l-f', width='100%'), 'edit': 'lrv-f'}

    def isShowable(self, obj, layoutType):
        res = Type.isShowable(self, obj, layoutType)
        if not res: return res
        # We add here specific Ref rules for preventing to show the field under
        # some inappropriate circumstances.
        if (layoutType == 'edit') and self.add: return False
        if self.isBack:
            if layoutType == 'edit': return False
            else: return getattr(obj.aq_base, self.name, None)
        return res

    def getValue(self, obj, type='objects', noListIfSingleObj=False,
                 startNumber=None, someObjects=False):
        '''Returns the objects linked to p_obj through this Ref field.
           - If p_type is "objects",  it returns the Appy wrappers;
           - If p_type is "zobjects", it returns the Zope objects;
           - If p_type is "uids",     it returns UIDs of objects (= strings).

           * If p_startNumber is None, it returns all referred objects.
           * If p_startNumber is a number, it returns self.maxPerPage objects,
             starting at p_startNumber.

           If p_noListIfSingleObj is True, it returns the single reference as
           an object and not as a list.

           If p_someObjects is True, it returns an instance of SomeObjects
           instead of returning a list of references.'''
        uids = getattr(obj.aq_base, self.name, [])
        if not uids:
            # Maybe is there a default value?
            defValue = Type.getValue(self, obj)
            if defValue:
                # I must prefix call to function "type" with "__builtins__"
                # because this name was overridden by a method parameter.
                if __builtins__['type'](defValue) in sequenceTypes:
                    uids = [o.o.UID() for o in defValue]
                else:
                    uids = [defValue.o.UID()]
        # Prepare the result: an instance of SomeObjects, that will be unwrapped
        # if not required.
        res = SomeObjects()
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
            if type == 'uids':
                ref = uids[i]
            else:
                ref = obj.portal_catalog(UID=uids[i])[0].getObject()
                if type == 'objects':
                    ref = ref.appy()
            res.objects.append(ref)
            i += 1
        # Manage parameter p_noListIfSingleObj
        if res.objects and noListIfSingleObj:
            if self.multiplicity[1] == 1:
                res.objects = res.objects[0]
        if someObjects: return res
        return res.objects

    def getFormattedValue(self, obj, value):
        return value

    def validateValue(self, obj, value):
        if not self.link: return None
        # We only check "link" Refs because in edit views, "add" Refs are
        # not visible. So if we check "add" Refs, on an "edit" view we will
        # believe that that there is no referred object even if there is.
        # If the field is a reference, we must ensure itself that multiplicities
        # are enforced.
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

    def linkObject(self, obj, value, back=False):
        '''This method links p_value (which can be a list of objects) to p_obj
           through this Ref field.'''
        # p_value can be a list of objects
        if type(value) in sequenceTypes:
            for v in value: self.linkObject(obj, v, back=back)
            return
        # Gets the list of referred objects (=list of uids), or create it.
        obj = obj.o
        refs = getattr(obj.aq_base, self.name, None)
        if refs == None:
            refs = obj.getProductConfig().PersistentList()
            setattr(obj, self.name, refs)
        # Insert p_value into it.
        uid = value.o.UID()
        if uid not in refs:
            refs.append(uid)
            # Update the back reference
            if not back: self.back.linkObject(value, obj, back=True)

    def unlinkObject(self, obj, value, back=False):
        '''This method unlinks p_value (which can be a list of objects) from
           p_obj through this Ref field.'''
        # p_value can be a list of objects
        if type(value) in sequenceTypes:
            for v in value: self.unlinkObject(obj, v, back=back)
            return
        obj = obj.o
        refs = getattr(obj.aq_base, self.name, None)
        if not refs: return
        # Unlink p_value
        uid = value.o.UID()
        if uid in refs:
            refs.remove(uid)
            # Update the back reference
            if not back: self.back.unlinkObject(value, obj, back=True)

    def store(self, obj, value):
        '''Stores on p_obj, the p_value, which can be:
           * None;
           * an object UID (=string);
           * a list of object UIDs (=list of strings). Generally, UIDs or lists
             of UIDs come from Ref fields with link:True edited through the web;
           * a Zope object;
           * a Appy object;
           * a list of Appy or Zope objects.'''
        # Standardize p_value into a list of Zope objects
        objects = value
        if not objects: objects = []
        if type(objects) not in sequenceTypes: objects = [objects]
        tool = obj.getTool()
        for i in range(len(objects)):
            if isinstance(objects[i], basestring):
                # We have a UID here
                objects[i] = tool.getObject(objects[i])
            else:
                # Be sure to have a Zope object
                objects[i] = objects[i].o
        uids = [o.UID() for o in objects]
        # Unlink objects that are not referred anymore
        refs = getattr(obj.aq_base, self.name, None)
        if refs:
            i = len(refs)-1
            while i >= 0:
                if refs[i] not in uids:
                    # Object having this UID must unlink p_obj
                    self.back.unlinkObject(tool.getObject(refs[i]), obj)
                i -= 1
        # Link new objects
        self.linkObject(obj, objects)

    def clone(self, forTool=True):
        '''Produces a clone of myself.'''
        res = Type.clone(self, forTool)
        res.back = copy.copy(self.back)
        if not forTool: return res
        res.link = True
        res.add = False
        res.back.attribute += 'DefaultValue'
        res.back.show = False
        res.select = None # Not callable from tool.
        return res

class Computed(Type):
    def __init__(self, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show='view',
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, method=None, plainText=True,
                 master=None, masterValue=None, focus=False, historized=False,
                 sync=True, mapping=None, label=None, context={}):
        # The Python method used for computing the field value
        self.method = method
        # Does field computation produce plain text or XHTML?
        self.plainText = plainText
        if isinstance(method, basestring):
            # When field computation is done with a macro, we know the result
            # will be HTML.
            self.plainText = False
        # The context is a dict (or method returning a dict) that will be given
        # to the macro specified in self.method. If the dict contains key
        # "someKey", it will be available to the macro as "options/someKey".
        self.context = context
        Type.__init__(self, None, multiplicity, index, default, optional,
                      False, show, page, group, layouts, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, None, colspan, master, masterValue, focus,
                      historized, sync, mapping, label)
        self.validable = False

    def callMacro(self, obj, macroPath):
        '''Returns the macro corresponding to p_macroPath. The base folder
           where we search is "skyn".'''
        # Get the special page in Appy that allows to call a macro
        macroPage = obj.skyn.callMacro
        # Get, from p_macroPath, the page where the macro lies, and the macro
        # name.
        names = self.method.split('/')
        # Get the page where the macro lies
        page = obj.skyn
        for name in names[:-1]:
            page = getattr(page, name)
        macroName = names[-1]
        # Compute the macro context.
        ctx = {'contextObj':obj, 'page':page, 'macroName':macroName}
        if callable(self.context):
            ctx.update(self.context(obj.appy()))
        else:
            ctx.update(self.context)
        return macroPage(obj, **ctx)

    def getValue(self, obj):
        '''Computes the value instead of getting it in the database.'''
        if not self.method: return
        if isinstance(self.method, basestring):
            # self.method is a path to a macro that will produce the field value
            return self.callMacro(obj, self.method)
        else:
            # self.method is a method that will return the field value
            return self.callMethod(obj, self.method, raiseOnError=False)

    def getFormattedValue(self, obj, value):
        if not isinstance(value, basestring): return str(value)
        return value

class Action(Type):
    '''An action is a workflow-independent Python method that can be triggered
       by the user on a given gen-class. For example, the custom installation
       procedure of a gen-application is implemented by an action on the custom
       tool class. An action is rendered as a button.'''
    def __init__(self, validator=None, multiplicity=(1,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, action=None, result='computation',
                 confirm=False, master=None, masterValue=None, focus=False,
                 historized=False, mapping=None, label=None):
        # Can be a single method or a list/tuple of methods
        self.action = action
        # For the 'result' param:
        #  * value 'computation' means that the action will simply compute
        #    things and redirect the user to the same page, with some status
        #    message about execution of the action;
        #  * 'file' means that the result is the binary content of a file that
        #    the user will download.
        #  * 'filetmp' is similar to file, but the file is a temp file and Appy
        #    will delete it as soon as it will be served to the browser.
        #  * 'redirect' means that the action will lead to the user being
        #    redirected to some other page.
        self.result = result
        # If following field "confirm" is True, a popup will ask the user if
        # she is really sure about triggering this action.
        self.confirm = confirm
        Type.__init__(self, None, (0,1), index, default, optional,
                      False, show, page, group, layouts, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, None, colspan, master, masterValue, focus,
                      historized, False, mapping, label)
        self.validable = False

    def getDefaultLayouts(self): return {'view': 'l-f', 'edit': 'lrv-f'}
    def __call__(self, obj):
        '''Calls the action on p_obj.'''
        try:
            if type(self.action) in sequenceTypes:
                # There are multiple Python methods
                res = [True, '']
                for act in self.action:
                    actRes = act(obj)
                    if type(actRes) in sequenceTypes:
                        res[0] = res[0] and actRes[0]
                        if self.result.startswith('file'):
                            res[1] = res[1] + actRes[1]
                        else:
                            res[1] = res[1] + '\n' + actRes[1]
                    else:
                        res[0] = res[0] and actRes
            else:
                # There is only one Python method
                actRes = self.action(obj)
                if type(actRes) in sequenceTypes:
                    res = list(actRes)
                else:
                    res = [actRes, '']
            # If res is None (ie the user-defined action did not return
            # anything), we consider the action as successfull.
            if res[0] == None: res[0] = True
        except Exception, e:
            res = (False, 'An error occurred. %s' % str(e))
            obj.log(Traceback.get(), type='error')
        return res

    def isShowable(self, obj, layoutType):
        if layoutType == 'edit': return False
        else: return Type.isShowable(self, obj, layoutType)

class Info(Type):
    '''An info is a field whose purpose is to present information
       (text, html...) to the user.'''
    def __init__(self, validator=None, multiplicity=(1,1), index=None,
                 default=None, optional=False, editDefault=False, show='view',
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None):
        Type.__init__(self, None, (0,1), index, default, optional,
                      False, show, page, group, layouts, move, indexed, False,
                      specificReadPermission, specificWritePermission, width,
                      height, None, colspan, master, masterValue, focus,
                      historized, False, mapping, label)
        self.validable = False

class Pod(Type):
    '''A pod is a field allowing to produce a (PDF, ODT, Word, RTF...) document
       from data contained in Appy class and linked objects or anything you
       want to put in it. It uses appy.pod.'''
    POD_ERROR = 'An error occurred while generating the document. Please ' \
                'contact the system administrator.'
    DELETE_TEMP_DOC_ERROR = 'A temporary document could not be removed. %s.'
    def __init__(self, validator=None, index=None, default=None,
                 optional=False, editDefault=False, show='view',
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None,
                 template=None, context=None, action=None, askAction=False,
                 stylesMapping={}, freezeFormat='pdf'):
        # The following param stores the path to a POD template
        self.template = template
        # The context is a dict containing a specific pod context, or a method
        # that returns such a dict.
        self.context = context
        # Next one is a method that will be triggered after the document has
        # been generated.
        self.action = action
        # If askAction is True, the action will be triggered only if the user
        # checks a checkbox, which, by default, will be unchecked.
        self.askAction = askAction
        # A global styles mapping that would apply to the whole template
        self.stylesMapping = stylesMapping
        # Freeze format is by PDF by default
        self.freezeFormat = freezeFormat
        Type.__init__(self, None, (0,1), index, default, optional,
                      False, show, page, group, layouts, move, indexed,
                      searchable, specificReadPermission,
                      specificWritePermission, width, height, None, colspan,
                      master, masterValue, focus, historized, False, mapping,
                      label)
        self.validable = False

    def isFrozen(self, obj):
        '''Is there a frozen document for p_self on p_obj?'''
        value = getattr(obj.o.aq_base, self.name, None)
        return isinstance(value, obj.o.getProductConfig().File)

    def getToolInfo(self, obj):
        '''Gets information related to this field (p_self) that is available in
           the tool: the POD template and the available output formats. If this
           field is frozen, available output formats are not available anymore:
           only the format of the frozen doc is returned.'''
        tool = obj.tool
        appyClass = tool.o.getAppyClass(obj.o.meta_type)
        # Get the output format(s)
        if self.isFrozen(obj):
            # The only available format is the one from the frozen document
            fileName = getattr(obj.o.aq_base, self.name).filename
            formats = (os.path.splitext(fileName)[1][1:],)
        else:
            # Available formats are those which are selected in the tool.
            name = tool.getAttributeName('formats', appyClass, self.name)
            formats = getattr(tool, name)
        # Get the POD template
        name = tool.getAttributeName('podTemplate', appyClass, self.name)
        template = getattr(tool, name)
        return (template, formats)

    def getValue(self, obj):
        '''Gets, on_obj, the value conforming to self's type definition. For a
           Pod field, if a file is stored in the field, it means that the
           field has been frozen. Else, it means that the value must be
           retrieved by calling pod to compute the result.'''
        rq = getattr(obj, 'REQUEST', None)
        res = getattr(obj.aq_base, self.name, None)
        if res and res.size: return FileWrapper(res) # Return the frozen file.
        # If we are here, it means that we must call pod to compute the file.
        # A Pod field differs from other field types because there can be
        # several ways to produce the field value (ie: output file format can be
        # odt, pdf,...; self.action can be executed or not...). We get those
        # precisions about the way to produce the file from the request object
        # and from the tool. If we don't find the request object (or if it does
        # not exist, ie, when Zope runs in test mode), we use default values.
        obj = obj.appy()
        tool = obj.tool
        # Get POD template and available formats from the tool.
        template, availFormats = self.getToolInfo(obj)
        # Get the output format
        defaultFormat = 'pdf'
        if defaultFormat not in availFormats: defaultFormat = availFormats[0]
        outputFormat = getattr(rq, 'podFormat', defaultFormat)
        # Get or compute the specific POD context
        specificContext = None
        if callable(self.context):
            specificContext = self.callMethod(obj, self.context)
        else:
            specificContext = self.context
        # Temporary file where to generate the result
        tempFileName = '%s/%s_%f.%s' % (
            getOsTempFolder(), obj.uid, time.time(), outputFormat)
        # Define parameters to give to the appy.pod renderer
        podContext = {'tool': tool, 'user': obj.user, 'self': obj,
                      'now': obj.o.getProductConfig().DateTime(),
                      '_': obj.translate, 'projectFolder': tool.getDiskFolder()}
        # If the POD document is related to a query, get it from the request,
        # execute it and put the result in the context.
        isQueryRelated = rq.get('queryData', None)
        if isQueryRelated:
            # Retrieve query params from the request
            cmd = ', '.join(tool.o.queryParamNames)
            cmd += " = rq['queryData'].split(';')"
            exec cmd
            # (re-)execute the query, but without any limit on the number of
            # results; return Appy objects.
            objs = tool.o.executeQuery(type_name, searchName=search,
                     sortBy=sortKey, sortOrder=sortOrder, filterKey=filterKey,
                     filterValue=filterValue, maxResults='NO_LIMIT')
            podContext['objects'] = [o.appy() for o in objs['objects']]
        if specificContext:
            podContext.update(specificContext)
        # Define a potential global styles mapping
        if callable(self.stylesMapping):
            stylesMapping = self.callMethod(obj, self.stylesMapping)
        else:
            stylesMapping = self.stylesMapping
        rendererParams = {'template': StringIO.StringIO(template.content),
                          'context': podContext, 'result': tempFileName,
                          'stylesMapping': stylesMapping}
        if tool.unoEnabledPython:
            rendererParams['pythonWithUnoPath'] = tool.unoEnabledPython
        if tool.openOfficePort:
            rendererParams['ooPort'] = tool.openOfficePort
        # Launch the renderer
        try:
            renderer = Renderer(**rendererParams)
            renderer.run()
        except appy.pod.PodError, pe:
            if not os.path.exists(tempFileName):
                # In some (most?) cases, when OO returns an error, the result is
                # nevertheless generated.
                obj.log(str(pe), type='error')
                return Pod.POD_ERROR
        # Give a friendly name for this file
        fileName = obj.translate(self.labelId)
        if not isQueryRelated:
            # This is a POD for a single object: personalize the file name with
            # the object title.
            fileName = '%s-%s' % (obj.title, fileName)
        fileName = tool.normalize(fileName) + '.' + outputFormat
        # Get a FileWrapper instance from the temp file on the filesystem
        res = File.getFileObject(tempFileName, fileName)
        # Execute the related action if relevant
        doAction = getattr(rq, 'askAction', False) in ('True', True)
        if doAction and self.action: self.action(obj, podContext)
        # Returns the doc and removes the temp file
        try:
            os.remove(tempFileName)
        except OSError, oe:
            obj.log(Pod.DELETE_TEMP_DOC_ERROR % str(oe), type='warning')
        except IOError, ie:
            obj.log(Pod.DELETE_TEMP_DOC_ERROR % str(ie), type='warning')
        return res

    def store(self, obj, value):
        '''Stores (=freezes) a document (in p_value) in the field.'''
        if isinstance(value, FileWrapper):
            value = value._atFile
        setattr(obj, self.name, value)

class List(Type):
    '''A list.'''
    def __init__(self, fields, validator=None, multiplicity=(0,1), index=None,
                 default=None, optional=False, editDefault=False, show=True,
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None,
                 subLayouts=Table('fv', width=None)):
        Type.__init__(self, validator, multiplicity, index, default, optional,
                      editDefault, show, page, group, layouts, move, indexed,
                      False, specificReadPermission, specificWritePermission,
                      width, height, None, colspan, master, masterValue, focus,
                      historized, True, mapping, label)
        self.validable = True
        # Tuples of (names, Type instances) determining the format of every
        # element in the list.
        self.fields = fields
        self.fieldsd = [(n, f.__dict__) for (n,f) in self.fields]
        # Force some layouting for sub-fields, if subLayouts are given. So the
        # one who wants freedom on tuning layouts at the field level must
        # specify subLayouts=None.
        if subLayouts:
            for name, field in self.fields:
                field.layouts = field.formatLayouts(subLayouts)

    def getField(self, name):
        '''Gets the field definition whose name is p_name.'''
        for n, field in self.fields:
            if n == name: return field

    def getRequestValue(self, request):
        '''Concatenates the list from distinct form elements in the request.'''
        prefix = self.name + '*' + self.fields[0][0] + '*'
        res = {}
        for key in request.keys():
            if not key.startswith(prefix): continue
            # I have found a row. Gets its index
            row = Object()
            rowIndex = int(key.split('*')[-1])
            if rowIndex == -1: continue # Ignore the template row.
            for name, field in self.fields:
                keyName = '%s*%s*%s' % (self.name, name, rowIndex)
                if request.has_key(keyName):
                    # Simulate the request as if it was for a single value
                    request.set(field.name, request[keyName])
                    v = field.getRequestValue(request)
                else:
                    v = None
                setattr(row, name, v)
            res[rowIndex] = row
        # Produce a sorted list.
        keys = res.keys()
        keys.sort()
        res = [res[key] for key in keys]
        # I store in the request this computed value. This way, when individual
        # subFields will need to get their value, they will take it from here,
        # instead of taking it from the specific request key. Indeed, specific
        # request keys contain row indexes that may be wrong after row deletions
        # by the user.
        request.set(self.name, res)
        return res

    def getStorableValue(self, value):
        '''Gets p_value in a form that can be stored in the database.'''
        res = []
        for v in value:
            sv = Object()
            for name, field in self.fields:
                setattr(sv, name, field.getStorableValue(getattr(v, name)))
            res.append(sv)
        return res

    def getInnerValue(self, outerValue, name, i):
        '''Returns the value of inner field named p_name in row number p_i
           within the whole list of values p_outerValue.'''
        if i == -1: return ''
        if not outerValue: return ''
        if i >= len(outerValue): return ''
        return getattr(outerValue[i], name, '')

# Workflow-specific types and default workflows --------------------------------
appyToZopePermissions = {
  'read': ('View', 'Access contents information'),
  'write': 'Modify portal content',
  'delete': 'Delete objects',
}

class Role:
    '''Represents a role.'''
    ploneRoles = ('Manager', 'Member', 'Owner', 'Reviewer', 'Anonymous',
                  'Authenticated')
    ploneLocalRoles = ('Owner',)
    ploneUngrantableRoles = ('Anonymous', 'Authenticated')
    def __init__(self, name, local=False, grantable=True):
        self.name = name
        self.local = local # True if it can be used as local role only.
        # It is a standard Plone role or an application-specific one?
        self.plone = name in self.ploneRoles
        if self.plone and (name in self.ploneLocalRoles):
            self.local = True
        self.grantable = grantable
        if self.plone and (name in self.ploneUngrantableRoles):
            self.grantable = False
        # An ungrantable role is one that is, like the Anonymous or
        # Authenticated roles, automatically attributed to a user.

class State:
    def __init__(self, permissions, initial=False, phase=None, show=True):
        self.usedRoles = {}
        # The following dict ~{s_permissionName:[s_roleName|Role_role]}~
        # gives, for every permission managed by a workflow, the list of roles
        # for which the permission is granted in this state. Standard
        # permissions are 'read', 'write' and 'delete'.
        self.permissions = permissions 
        self.initial = initial
        self.phase = phase
        self.show = show
        # Standardize the way roles are expressed within self.permissions
        self.standardizeRoles()

    def getName(self, wf):
        '''Returns the name for this state in workflow p_wf.'''
        for name in dir(wf):
            value = getattr(wf, name)
            if (value == self): return name

    def getRole(self, role):
        '''p_role can be the name of a role or a Role instance. If it is the
           name of a role, this method returns self.usedRoles[role] if it
           exists, or creates a Role instance, puts it in self.usedRoles and
           returns it else. If it is a Role instance, the method stores it in
           self.usedRoles if it not in it yet and returns it.'''
        if isinstance(role, basestring):
            if role in self.usedRoles:
                return self.usedRoles[role]
            else:
                theRole = Role(role)
                self.usedRoles[role] = theRole
                return theRole
        else:
            if role.name not in self.usedRoles:
                self.usedRoles[role.name] = role
            return role

    def standardizeRoles(self):
        '''This method converts, within self.permissions, every role to a
           Role instance. Every used role is stored in self.usedRoles.'''
        for permission, roles in self.permissions.items():
            if isinstance(roles, basestring) or isinstance(roles, Role):
                self.permissions[permission] = [self.getRole(roles)]
            elif roles:
                rolesList = []
                for role in roles:
                    rolesList.append(self.getRole(role))
                self.permissions[permission] = rolesList

    def getUsedRoles(self): return self.usedRoles.values()

    def getPermissions(self):
        '''If you get the permissions mapping through self.permissions, dict
           values may be of different types (a list of roles, a single role or
           None). Iy you call this method, you will always get a list which
           may be empty.'''
        res = {}
        for permission, roleValue in self.permissions.iteritems():
            if roleValue == None:
                res[permission] = []
            elif isinstance(roleValue, basestring):
                res[permission] = [roleValue]
            else:
                res[permission] = roleValue
        return res

    def updatePermission(self, obj, zopePermission, roleNames):
        '''Updates, on p_obj, list of p_roleNames which are granted a given
           p_zopePermission. This method returns True if the list has been
           effectively updated.'''
        attr = Permission.getZopeAttrName(zopePermission)
        if not hasattr(obj.aq_base, attr) or \
           (getattr(obj.aq_base, attr) != roleNames):
            setattr(obj, attr, roleNames)
            return True
        return False

    def updatePermissions(self, wf, obj):
        '''Zope requires permission-to-roles mappings to be stored as attributes
           on the object itself. This method does this job, duplicating the info
           from this state definition on p_obj. p_res is True if at least one
           change has been effectively performed.'''
        res = False
        for permission, roles in self.getPermissions().iteritems():
            roleNames = tuple([role.name for role in roles])
            # Compute Zope permission(s) related to this permission.
            if appyToZopePermissions.has_key(permission):
                # It is a standard permission (r, w, d)
                zopePerm = appyToZopePermissions[permission]
            elif isinstance(permission, basestring):
                # It is a user-defined permission
                zopePerm = permission
            else:
                # It is a Permission instance
                appName = obj.getProductConfig().PROJECTNAME
                zopePerm = permission.getName(wf, appName)
            # zopePerm contains a single permission or a tuple of permissions
            if isinstance(zopePerm, basestring):
                changed = self.updatePermission(obj, zopePerm, roleNames)
                res = res or changed
            else:
                for zPerm in zopePerm:
                    changed = self.updatePermission(obj, zPerm, roleNames)
                    res = res or changed
        return res

class Transition:
    def __init__(self, states, condition=True, action=None, notify=None,
                 show=True, confirm=False):
        self.states = states # In its simpler form, it is a tuple with 2
        # states: (fromState, toState). But it can also be a tuple of several
        # (fromState, toState) sub-tuples. This way, you may define only 1
        # transition at several places in the state-transition diagram. It may
        # be useful for "undo" transitions, for example.
        self.condition = condition
        if isinstance(condition, basestring):
            # The condition specifies the name of a role.
            self.condition = Role(condition)
        self.action = action
        self.notify = notify # If not None, it is a method telling who must be
        # notified by email after the transition has been executed.
        self.show = show # If False, the end user will not be able to trigger
        # the transition. It will only be possible by code.
        self.confirm = confirm # If True, a confirm popup will show up.

    def getName(self, wf):
        '''Returns the name for this state in workflow p_wf.'''
        for name in dir(wf):
            value = getattr(wf, name)
            if (value == self): return name

    def getUsedRoles(self):
        '''self.condition can specify a role.'''
        res = []
        if isinstance(self.condition, Role):
            res.append(self.condition)
        return res

    def isSingle(self):
        '''If this transition is only defined between 2 states, returns True.
           Else, returns False.'''
        return isinstance(self.states[0], State)

    def isShowable(self, workflow, obj):
        '''Is this transition showable?'''
        if callable(self.show):
            return self.show(workflow, obj.appy())
        else:
            return self.show

    def hasState(self, state, isFrom):
        '''If p_isFrom is True, this method returns True if p_state is a
           starting state for p_self. If p_isFrom is False, this method returns
           True if p_state is an ending state for p_self.'''
        stateIndex = 1
        if isFrom:
            stateIndex = 0
        if self.isSingle():
            res = state == self.states[stateIndex]
        else:
            res = False
            for states in self.states:
                if states[stateIndex] == state:
                    res = True
                    break
        return res

    def isTriggerable(self, obj, wf):
        '''Can this transition be triggered on p_obj?'''
        wf = wf.__instance__ # We need the prototypical instance here.
        # Checks that the current state of the object is a start state for this
        # transition.
        objState = obj.getState(name=False)
        if self.isSingle():
            if objState != self.states[0]: return False
        else:
            startFound = False
            for startState, stopState in self.states:
                if startState == objState:
                    startFound = True
                    break
            if not startFound: return False
        # Check that the condition is met
        user = obj.portal_membership.getAuthenticatedMember()
        if isinstance(self.condition, Role):
            # Condition is a role. Transition may be triggered if the user has
            # this role.
            return user.has_role(self.condition.name, obj)
        elif type(self.condition) == types.FunctionType:
            return self.condition(wf, obj.appy())
        elif type(self.condition) in (tuple, list):
            # It is a list of roles and/or functions. Transition may be
            # triggered if user has at least one of those roles and if all
            # functions return True.
            hasRole = None
            for roleOrFunction in self.condition:
                if isinstance(roleOrFunction, basestring):
                    if hasRole == None:
                        hasRole = False
                    if user.has_role(roleOrFunction, obj):
                        hasRole = True
                elif type(roleOrFunction) == types.FunctionType:
                    if not roleOrFunction(wf, obj.appy()):
                        return False
            if hasRole != False:
                return True

    def executeAction(self, obj, wf):
        '''Executes the action related to this transition.'''
        msg = ''
        obj = obj.appy()
        wf = wf.__instance__ # We need the prototypical instance here.
        if type(self.action) in (tuple, list):
            # We need to execute a list of actions
            for act in self.action:
                msgPart = act(wf, obj)
                if msgPart: msg += msgPart
        else: # We execute a single action only.
            msgPart = self.action(wf, obj)
            if msgPart: msg += msgPart
        return msg

    def trigger(self, transitionName, obj, wf, comment, doAction=True,
                doNotify=True, doHistory=True, doSay=True):
        '''This method triggers this transition on p_obj. The transition is
           supposed to be triggerable (call to self.isTriggerable must have been
           performed before calling this method). If p_doAction is False, the
           action that must normally be executed after the transition has been
           triggered will not be executed. If p_doNotify is False, the
           notifications (email,...) that must normally be launched after the
           transition has been triggered will not be launched. If p_doHistory is
           False, there will be no trace from this transition triggering in the
           workflow history. If p_doSay is False, we consider the transition is
           trigger programmatically, and no message is returned to the user.'''
        # Create the workflow_history dict if it does not exist.
        if not hasattr(obj.aq_base, 'workflow_history'):
            from persistent.mapping import PersistentMapping
            obj.workflow_history = PersistentMapping()
        # Create the event list if it does not exist in the dict
        if not obj.workflow_history: obj.workflow_history['appy'] = ()
        # Get the key where object history is stored (this overstructure is
        # only there for backward compatibility reasons)
        key = obj.workflow_history.keys()[0]
        # Identify the target state for this transition
        if self.isSingle():
            targetState = self.states[1]
            targetStateName = targetState.getName(wf)
        else:
            startState = obj.getState(name=False)
            for sState, tState in self.states:
                if startState == sState:
                    targetState = tState
                    targetStateName = targetState.getName(wf)
                    break
        # Create the event and add it in the object history
        action = transitionName
        if transitionName == '_init_': action = None
        if not doHistory: comment = '_invisible_'
        obj.addHistoryEvent(action, review_state=targetStateName,
                            comments=comment)
        # Update permissions-to-roles attributes
        targetState.updatePermissions(wf, obj)
        # Refresh catalog-related security if required
        if not obj.isTemporary():
            obj.reindexObject(idxs=('allowedRolesAndUsers', 'getState'))
        # Execute the related action if needed
        msg = ''
        if doAction and self.action: msg = self.executeAction(obj, wf)
        # Send notifications if needed
        if doNotify and self.notify and obj.getTool(True).enableNotifications:
            notifier.sendMail(obj.appy(), self, transitionName, wf)
        # Return a message to the user if needed
        if not doSay or (transitionName == '_init_'): return
        if not msg:
            msg = obj.translate(u'Your content\'s status has been modified.',
                                domain='plone')
        obj.say(msg)

class Permission:
    '''If you need to define a specific read or write permission of a given
       attribute of an Appy type, you use the specific boolean parameters
       "specificReadPermission" or "specificWritePermission" for this attribute.
       When you want to refer to those specific read or write permissions when
       defining a workflow, for example, you need to use instances of
       "ReadPermission" and "WritePermission", the 2 children classes of this
       class. For example, if you need to refer to write permission of
       attribute "t1" of class A, write: WritePermission("A.t1") or
       WritePermission("x.y.A.t1") if class A is not in the same module as
       where you instantiate the class.

       Note that this holds only if you use attributes "specificReadPermission"
       and "specificWritePermission" as booleans. When defining named
       (string) permissions, for referring to it you simply use those strings,
       you do not create instances of ReadPermission or WritePermission.'''

    allowedChars = string.digits + string.letters + '_'

    def __init__(self, fieldDescriptor):
        self.fieldDescriptor = fieldDescriptor

    def getName(self, wf, appName):
        '''Returns the name of the Zope permission that corresponds to this
           permission.'''
        className, fieldName = self.fieldDescriptor.rsplit('.', 1)
        if className.find('.') == -1:
            # The related class resides in the same module as the workflow
            fullClassName= '%s_%s' % (wf.__module__.replace('.', '_'),className)
        else:
            # className contains the full package name of the class
            fullClassName = className.replace('.', '_')
        # Read or Write ?
        if self.__class__.__name__ == 'ReadPermission': access = 'Read'
        else: access = 'Write'
        return '%s: %s %s %s' % (appName, access, fullClassName, fieldName)

    @staticmethod
    def getZopeAttrName(zopePermission):
        '''Gets the name of the attribute where Zope stores, on every object,
           the tuple of roles who are granted a given p_zopePermission.'''
        res = ''
        for c in zopePermission:
            if c in Permission.allowedChars: res += c
            else: res += '_'
        return '_%s_Permission' % res

class ReadPermission(Permission): pass
class WritePermission(Permission): pass

class No:
    '''When you write a workflow condition method and you want to return False
       but you want to give to the user some explanations about why a transition
       can't be triggered, do not return False, return an instance of No
       instead. When creating such an instance, you can specify an error
       message.'''
    def __init__(self, msg):
        self.msg = msg
    def __nonzero__(self):
        return False

class WorkflowAnonymous:
    '''One-state workflow allowing anyone to consult and Manager to edit.'''
    mgr = 'Manager'
    active = State({r:(mgr, 'Anonymous'), w:mgr, d:mgr}, initial=True)
WorkflowAnonymous.__instance__ = WorkflowAnonymous()

class WorkflowAuthenticated:
    '''One-state workflow allowing authenticated users to consult and Manager
       to edit.'''
    mgr = 'Manager'
    active = State({r:(mgr, 'Authenticated'), w:mgr, d:mgr}, initial=True)
WorkflowAuthenticated.__instance__ = WorkflowAuthenticated()

# ------------------------------------------------------------------------------
class Selection:
    '''Instances of this class may be given as validator of a String, in order
       to tell Appy that the validator is a selection that will be computed
       dynamically.'''
    def __init__(self, methodName):
        # The p_methodName parameter must be the name of a method that will be
        # called every time Appy will need to get the list of possible values
        # for the related field. It must correspond to an instance method of
        # the class defining the related field. This method accepts no argument
        # and must return a list (or tuple) of pairs (lists or tuples):
        # (id, text), where "id" is one of the possible values for the
        # field, and "text" is the value as will be shown on the screen.
        # You can use self.translate within this method to produce an
        # internationalized version of "text" if needed.
        self.methodName = methodName

    def getText(self, obj, value, appyType):
        '''Gets the text that corresponds to p_value.'''
        for v, text in appyType.getPossibleValues(obj, withTranslations=True):
            if v == value:
                return text
        return value

# ------------------------------------------------------------------------------
class Model: pass
class Tool(Model):
    '''If you want so define a custom tool class, she must inherit from this
       class.'''
class User(Model):
    '''If you want to extend or modify the User class, subclass me.'''

# ------------------------------------------------------------------------------
class Config:
    '''If you want to specify some configuration parameters for appy.gen and
       your application, please create an instance of this class and modify its
       attributes. You may put your instance anywhere in your application
       (main package, sub-package, etc).'''

    # The default Config instance, used if the application does not give one.
    defaultConfig = None
    def getDefault():
        if not Config.defaultConfig:
            Config.defaultConfig = Config()
        return Config.defaultConfig
    getDefault = staticmethod(getDefault)

    def __init__(self):
        # For every language code that you specify in this list, appy.gen will
        # produce and maintain translation files.
        self.languages = ['en']
        # If languageSelector is True, on every page, a language selector will
        # allow to switch between languages defined in self.languages. Else,
        # the browser-defined language will be used for choosing the language
        # of returned pages.
        self.languageSelector = False
        # People having one of these roles will be able to create instances
        # of classes defined in your application.
        self.defaultCreators = ['Manager', 'Owner']
        # If you want to replace the default front page with a page coming from
        # your application, use the following parameter. Setting
        # frontPage = True will replace the Plone front page with a page
        # whose content will come fron i18n label "front_page_text".
        self.frontPage = False
        # You can choose the Plone or Appy main template
        self.frontPageTemplate = 'plone' # or "appy"
        # Number of translations for every page on a Translation object
        self.translationsPerPage = 30
        # Language that will be used as a basis for translating to other
        # languages.
        self.sourceLanguage = 'en'
# ------------------------------------------------------------------------------
