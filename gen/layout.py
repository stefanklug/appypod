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
#  m - The global status message sometimes shown. If you specify this in a
#      layout, ensure that you have hidden the global_statusmessage zone as
#      proposed by Plone. Else, the message will appear twice.

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
cellDelimiters = {'|': 'center', ';': 'left', '!': 'right'}
macroDict = {
  # Page-related elements
  's': ('page', 'header'), 'w': ('page', 'widgets'),
  'n': ('navigate', 'objectNavigate'), 'b': ('page', 'buttons'),
  'm': ('page', 'message'),
  # Field-related elements
  'l': ('show', 'label'), 'd': ('show', 'description'),
  'h': ('show', 'help'),  'v': ('show', 'validation'),
  'r': ('show', 'required')
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
    def __init__(self, layoutString, style=None, css_class='', cellpadding=0,
                 cellspacing=0, width='100%', align='left'):
        self.style = style
        self.css_class = css_class
        self.cellpadding = cellpadding
        self.cellspacing = cellspacing
        self.width = width
        self.align = align
        # The following attribute will store a special Row instance used for
        # defining column properties.
        self.headerRow = None
        # The content rows are stored hereafter.
        self.rows = []
        self.layoutString = layoutString
        self.decodeRows(layoutString)

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
                    self.headerRow = Row(rowContent,valign,isHeader=True).get()
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

# ------------------------------------------------------------------------------
defaultPageLayouts  = {
    'view': Table('m;-s|-n!-w;-b|'), 'edit': Table('m;-s|-n!-w;-b|')}
defaultFieldLayouts = {'view': 'l;f!', 'edit': 'lrv;f!'}
# ------------------------------------------------------------------------------
