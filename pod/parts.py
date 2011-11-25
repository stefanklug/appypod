# ------------------------------------------------------------------------------
import cgi

# ------------------------------------------------------------------------------
class OdtTable:
    '''This class allows to construct an ODT table programmatically.'''
    # Some namespace definitions
    tns = 'table:'
    txns = 'text:'

    def __init__(self, name, paraStyle, cellStyle, nbOfCols,
                 paraHeaderStyle=None, cellHeaderStyle=None):
        # An ODT table must have a name.
        self.name = name
        # The default style of every paragraph within cells
        self.paraStyle = paraStyle
        # The default style of every cell
        self.cellStyle = cellStyle
        # The total number of columns
        self.nbOfCols = nbOfCols
        # The default style of every paragraph within a header cell
        self.paraHeaderStyle = paraHeaderStyle or paraStyle
        # The default style of every header cell
        self.cellHeaderStyle = cellHeaderStyle or cellStyle
        # The buffer where the resulting table will be rendered
        self.res = ''

    def dumpCell(self, content, span=1, header=False,
                 paraStyle=None, cellStyle=None):
        '''Dumps a cell in the table. If no specific p_paraStyle (p_cellStyle)
           is given, self.paraStyle (self.cellStyle) is used, excepted if
           p_header is True: in that case, self.paraHeaderStyle
           (self.cellHeaderStyle) is used.'''
        if not paraStyle:
            if header: paraStyle = self.paraHeaderStyle
            else: paraStyle = self.paraStyle
        if not cellStyle:
            if header: cellStyle = self.cellHeaderStyle
            else: cellStyle = self.cellStyle
        self.res += '<%stable-cell %sstyle-name="%s" ' \
                    '%snumber-columns-spanned="%d">' % \
                    (self.tns, self.tns, cellStyle, self.tns, span)
        self.res += '<%sp %sstyle-name="%s">%s</%sp>' % \
                    (self.txns, self.txns, paraStyle, cgi.escape(str(content)),
                     self.txns)
        self.res += '</%stable-cell>' % self.tns

    def startRow(self):
        self.res += '<%stable-row>' % self.tns

    def endRow(self):
        self.res += '</%stable-row>' % self.tns

    def startTable(self):
        self.res += '<%stable %sname="%s">' % (self.tns, self.tns, self.name)
        self.res += '<%stable-column %snumber-columns-repeated="%d"/>' % \
                    (self.tns, self.tns, self.nbOfCols)

    def endTable(self):
        self.res += '</%stable>' % self.tns

    def dumpFloat(self, number):
        return str(round(number, 2))

    def get(self):
        '''Returns the whole table.'''
        return self.res.decode('utf-8')
# ------------------------------------------------------------------------------
