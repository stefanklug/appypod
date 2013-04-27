'''This module contains classes used for layouting graphical elements
   (fields, widgets, groups, ...).'''

# A layout defines how a given field is rendered in a given context. Several
# contexts exist:
#  "view"   represents a given page for a given Appy class, in read-only mode.
#  "edit"   represents a given page for a given Appy class, in edit mode.
#  "cell"   represents a cell in a table, like when we need to render a field
#           value in a query result or in a reference table.

# Layout elements for a class or page ------------------------------------------
#  s - The page summary, containing summarized information about the page or
#      class, workflow information and object history.
#  w - The widgets of the current page/class
#  n - The navigation panel (inter-objects navigation)
#  b - The range of buttons (intra-object navigation, save, edit, delete...)

# Layout elements for a field --------------------------------------------------
#  l -  "label"        The field label
#  d -  "description"  The field description (a description is always visible)
#  h -  "help"         Help for the field (typically rendered as an icon,
#                       clicking on it shows a popup with online help
#  v -  "validation"   The icon that is shown when a validation error occurs
#                       (typically only used on "edit" layouts)
#  r -  "required"     The icon that specified that the field is required (if
#                       relevant; typically only used on "edit" layouts)
#  f -  "field"        The field value, or input for entering a value.
#  c -  "changes"      The button for displaying changes to a field

# For every field of a Appy class, you can define, for every layout context,
# what field-related information will appear, and how it will be rendered.
# Variables defaultPageLayouts and defaultFieldLayouts defined below give the
# default layouts for pages and fields respectively.
# 
# How to express a layout? You simply define a string that is made of the
# letters corresponding to the field elements you want to render. The order of
# elements correspond to the order into which they will be rendered.

# ------------------------------------------------------------------------------
rowDelimiters =  {'-':'middle', '=':'top', '_':'bottom'}
rowDelms = ''.join(rowDelimiters.keys())
cellDelimiters = {'|': 'center', ';': 'left', '!': 'right'}
cellDelms = ''.join(cellDelimiters.keys())

macroDict = {
  # Page-related elements
  's': ('page', 'header'), 'w': ('page', 'widgets'),
  'n': ('navigate', 'objectNavigate'), 'b': ('page', 'buttons'),
  # Field-related elements
  'l': ('show', 'label'), 'd': ('show', 'description'),
  'h': ('show', 'help'),  'v': ('show', 'validation'),
  'r': ('show', 'required'), 'c': ('show', 'changes'),
}

# ------------------------------------------------------------------------------
class LayoutElement:
    '''Abstract base class for any layout element.'''
    def get(self): return self.__dict__

class Cell(LayoutElement):
    '''Represents a cell in a row in a table.'''
    def __init__(self, content, align, isHeader=False):
        self.align = align
        self.width = None
        self.content = None
        self.colspan = 1
        if isHeader:
            self.width = content
        else:
            self.content = [] # The list of widgets to render in the cell
            self.decodeContent(content)

    def decodeContent(self, content):
        digits = '' # We collect the digits that will give the colspan
        for char in content:
            if char.isdigit():
                digits += char
            else:
                # It is a letter corresponding to a macro
                if char in macroDict:
                    self.content.append(macroDict[char])
                elif char == 'f':
                    # The exact macro to call will be known at render-time
                    self.content.append('?')
        # Manage the colspan
        if digits:
            self.colspan = int(digits)

# ------------------------------------------------------------------------------
class Row(LayoutElement):
    '''Represents a row in a table.'''
    def __init__(self, content, valign, isHeader=False):
        self.valign = valign
        self.cells = []
        self.decodeCells(content, isHeader)
        # Compute the row length
        length = 0
        for cell in self.cells:
            length += cell['colspan']
        self.length = length

    def decodeCells(self, content, isHeader):
        '''Decodes the given chunk of layout string p_content containing
           column-related information (if p_isHeader is True) or cell content
           (if p_isHeader is False) and produces a list of Cell instances.'''
        cellContent = ''
        for char in content:
            if char in cellDelimiters:
                align = cellDelimiters[char]
                self.cells.append(Cell(cellContent, align, isHeader).get())
                cellContent = ''
            else:
                cellContent += char
        # Manage the last cell if any
        if cellContent:
            self.cells.append(Cell(cellContent, 'left', isHeader).get())

# ------------------------------------------------------------------------------
class Table(LayoutElement):
    '''Represents a table where to dispose graphical elements.'''
    simpleParams = ('style', 'css_class', 'cellpadding', 'cellspacing', 'width',
                    'align')
    derivedRepls = {'view': 'hrvd', 'cell': 'ldc'}
    def __init__(self, layoutString=None, style=None, css_class='',
                 cellpadding=0, cellspacing=0, width='100%', align='left',
                 other=None, derivedType=None):
        if other:
            # We need to create a Table instance from another Table instance,
            # given in p_other. In this case, we ignore previous params.
            if derivedType != None:
                # We will not simply mimic p_other. If p_derivedType is:
                # - "view", p_derivedFrom is an "edit" layout, and we must
                #           create the corresponding "view" layout;
                # - "cell", p_derivedFrom is a "view" layout, and we must
                #           create the corresponding "cell" layout;
                self.layoutString = Table.deriveLayout(other.layoutString,
                                                       derivedType)
            else:
                self.layoutString = other.layoutString
            source = 'other.'
        else:
            source = ''
            self.layoutString = layoutString
        # Initialise simple params, either from the true params, either from
        # the p_other Table instance.
        for param in Table.simpleParams:
            exec 'self.%s = %s%s' % (param, source, param)
        # The following attribute will store a special Row instance used for
        # defining column properties.
        self.headerRow = None
        # The content rows will be stored hereafter.
        self.rows = []
        self.decodeRows(self.layoutString)

    @staticmethod
    def deriveLayout(layout, derivedType):
        '''Returns a layout derived from p_layout.'''
        res = layout
        for letter in Table.derivedRepls[derivedType]:
            res = res.replace(letter, '')
        # Strip the derived layout
        res = res.lstrip(rowDelms); res = res.lstrip(cellDelms)
        if derivedType == 'cell':
            res = res.rstrip(rowDelms); res = res.rstrip(cellDelms)
        return res

    def addCssClasses(self, css_class):
        '''Adds a single or a group of p_css_class.'''
        classes = self.css_class
        if classes == None:
            classes = ''
        if not classes:
            self.css_class = css_class
        else:
            self.css_class += ' ' + css_classes
            # Ensures that every class appears once
            self.css_class = ' '.join(set(self.css_class.split()))

    def isHeaderRow(self, rowContent):
        '''Determines if p_rowContent specified the table header row or a
           content row.'''
        # Find the first char that is a number or a letter
        for char in rowContent:
            if char not in cellDelimiters:
                if char.isdigit(): return True
                else:              return False
        return True

    def decodeRows(self, layoutString):
        '''Decodes the given p_layoutString and produces a list of Row
           instances.'''
        # Split the p_layoutString with the row delimiters
        rowContent = ''
        for char in layoutString:
            if char in rowDelimiters:
                valign = rowDelimiters[char]
                if self.isHeaderRow(rowContent):
                    if not self.headerRow:
                        self.headerRow = Row(rowContent, valign,
                                             isHeader=True).get()
                else:
                    self.rows.append(Row(rowContent, valign).get())
                rowContent = ''
            else:
                rowContent += char
        # Manage the last row if any
        if rowContent:
            self.rows.append(Row(rowContent, 'middle').get())

    def removeElement(self, elem):
        '''Removes given p_elem from myself.'''
        macroToRemove = macroDict[elem]
        for row in self.rows:
            for cell in row['cells']:
                if macroToRemove in cell['content']:
                    cell['content'].remove(macroToRemove)

# Some base layouts to use, for fields and pages -------------------------------
# The default layouts for pages
defaultPageLayouts  = {
    'view': Table('w|-b|', align="center"),
    'edit': Table('w|-b|', width=None)}
# A layout for pages, containing the page summary.
summaryPageLayouts = {'view': Table('s-w|-b|', align="center"),
                      'edit': Table('w|-b|', width=None)}
widePageLayouts = {
    'view': Table('w|-b|', align="center"),
    'edit': Table('w|-b|')
}
centeredPageLayouts = {
    'view': Table('w|-b|', align="center"),
    'edit': Table('w|-b|', width=None, align='center')
}

# The default layout for fields. Alternative layouts may exist and are declared
# as static attributes of the concerned Type subclass.
defaultFieldLayouts = {'edit': 'lrv-f'}

# ------------------------------------------------------------------------------
class ColumnLayout:
    '''A "column layout" dictates the way a table column must be rendered. Such
       a layout is of the form: <name>[*width][,|!|`|`]
       * "name"   is the name of the field whose content must be shown in
                  column's cells;
       * "width"  is the width of the column. Any valid value for the "width"
                  attribute of the "td" HTML tag is accepted;
       * , | or ! indicates column alignment: respectively, left, centered or
                  right.
    '''
    def __init__(self, layoutString):
        self.layoutString = layoutString
    def get(self):
        '''Returns a list containing the separate elements that are within
           self.layoutString.'''
        consumed = self.layoutString
        # Determine column alignment
        align = 'left'
        lastChar = consumed[-1]
        if lastChar in cellDelimiters:
            align = cellDelimiters[lastChar]
            consumed = consumed[:-1]
        # Determine name and width
        if '*' in consumed:
            name, width = consumed.rsplit('*', 1)
        else:
            name = consumed
            width = ''
        return name, width, align
# ------------------------------------------------------------------------------
