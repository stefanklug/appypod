# ------------------------------------------------------------------------------
# Appy is a framework for building applications in the Python language.
# Copyright (C) 2007 Gaetan Delannay

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,USA.

# ------------------------------------------------------------------------------
import sys, os, os.path, time, signal
from optparse import OptionParser

htmlFilters = {'odt': 'HTML (StarWriter)',
               'ods': 'HTML (StarCalc)',
               'odp': 'impress_html_Export'}

FILE_TYPES = {'odt': 'writer8',
              'ods': 'calc8',
              'odp': 'impress8',
              'htm': htmlFilters, 'html': htmlFilters,
              'rtf': 'Rich Text Format',
              'txt': 'Text',
              'csv': 'Text - txt - csv (StarCalc)',
              'pdf': {'odt': 'writer_pdf_Export',  'ods': 'calc_pdf_Export',
                      'odp': 'impress_pdf_Export', 'htm': 'writer_pdf_Export',
                      'html': 'writer_pdf_Export', 'rtf': 'writer_pdf_Export',
                      'txt': 'writer_pdf_Export', 'csv': 'calc_pdf_Export',
                      'swf': 'draw_pdf_Export', 'doc': 'writer_pdf_Export',
                      'xls': 'calc_pdf_Export', 'ppt': 'impress_pdf_Export',
                      'docx': 'writer_pdf_Export', 'xlsx': 'calc_pdf_Export'
                      },
              'swf': 'impress_flash_Export',
              'doc': 'MS Word 97',
              'xls': 'MS Excel 97',
              'ppt': 'MS PowerPoint 97',
              'docx': 'MS Word 2007 XML',
              'xlsx': 'Calc MS Excel 2007 XML',
}
# Conversion from odt to odt does not make any conversion, but updates indexes
# and linked documents.

# ------------------------------------------------------------------------------
class ConverterError(Exception): pass

# ConverterError-related messages ----------------------------------------------
DOC_NOT_FOUND = '"%s" not found.'
URL_NOT_FOUND = 'Doc URL "%s" is wrong. %s'
BAD_RESULT_TYPE = 'Bad result type "%s". Available types are %s.'
CANNOT_WRITE_RESULT = 'I cannot write result "%s". %s'
CONNECT_ERROR = 'Could not connect to LibreOffice on port %d. UNO ' \
                '(LibreOffice API) says: %s.'

# Some constants ---------------------------------------------------------------
DEFAULT_PORT = 2002

# ------------------------------------------------------------------------------
class Converter:
    '''Converts a document readable by LibreOffice into pdf, doc, txt, rtf...'''
    exeVariants = ('soffice.exe', 'soffice')
    pathReplacements = {'program files': 'progra~1',
                        'openoffice.org 1': 'openof~1',
                        'openoffice.org 2': 'openof~1',
                        }
    def __init__(self, docPath, resultType, port=DEFAULT_PORT,
                 templatePath=None):
        self.port = port
        # The path to the document to convert
        self.docUrl, self.docPath = self.getFilePath(docPath)
        self.inputType = os.path.splitext(docPath)[1][1:].lower()
        self.resultType = resultType
        self.resultFilter = self.getResultFilter()
        self.resultUrl = self.getResultUrl()
        self.loContext = None
        self.oo = None # The LibreOffice application object
        self.doc = None # The LibreOffice loaded document
        # The path to a LibreOffice template (ie, a ".ott" file) from which
        # styles can be imported
        self.templateUrl = self.templatePath = None
        if templatePath:
            self.templateUrl, self.templatePath = self.getFilePath(templatePath)

    def getFilePath(self, filePath):
        '''Returns the absolute path of p_filePath. In fact, it returns a
           tuple with some URL version of the path for LO as the first element
           and the absolute path as the second element.''' 
        import unohelper
        if not os.path.exists(filePath) and not os.path.isfile(filePath):
            raise ConverterError(DOC_NOT_FOUND % filePath)
        docAbsPath = os.path.abspath(filePath)
        # Return one path for OO, one path for me
        return unohelper.systemPathToFileUrl(docAbsPath), docAbsPath

    def getResultFilter(self):
        '''Based on the result type, identifies which OO filter to use for the
           document conversion.'''
        if self.resultType in FILE_TYPES:
            res = FILE_TYPES[self.resultType]
            if isinstance(res, dict):
                res = res[self.inputType]
        else:
            raise ConverterError(BAD_RESULT_TYPE % (self.resultType,
                                                    list(FILE_TYPES.keys())))
        return res

    def getResultUrl(self):
        '''Returns the path of the result file in the format needed by LO. If
           the result type and the input type are the same (ie the user wants to
           refresh indexes or some other action and not perform a real
           conversion), the result file is named
                           <inputFileName>.res.<resultType>.

           Else, the result file is named like the input file but with a
           different extension:
                           <inputFileName>.<resultType>
        '''
        import unohelper
        baseName = os.path.splitext(self.docPath)[0]
        if self.resultType != self.inputType:
            res = '%s.%s' % (baseName, self.resultType)
        else:
            res = '%s.res.%s' % (baseName, self.resultType)
        try:
            f = open(res, 'w')
            f.write('Hello')
            f.close()
            os.remove(res)
            return unohelper.systemPathToFileUrl(res)
        except (OSError, IOError):
            e = sys.exc_info()[1]
            raise ConverterError(CANNOT_WRITE_RESULT % (res, e))

    def props(self, properties):
        '''Create a UNO-compliant tuple of properties, from tuple p_properties
           containing sub-tuples (s_propertyName, value).'''
        from com.sun.star.beans import PropertyValue
        res = []
        for name, value in properties:
            prop = PropertyValue()
            prop.Name = name
            prop.Value = value
            res.append(prop)
        return tuple(res)

    def connect(self):
        '''Connects to LibreOffice'''
        if os.name == 'nt':
            import socket
        import uno
        from com.sun.star.connection import NoConnectException
        try:
            # Get the uno component context from the PyUNO runtime
            localContext = uno.getComponentContext()
            # Create the UnoUrlResolver
            resolver = localContext.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", localContext)
            # Connect to the running office
            self.loContext = resolver.resolve(
                'uno:socket,host=localhost,port=%d;urp;StarOffice.' \
                'ComponentContext' % self.port)
            # Is seems that we can't define a timeout for this method.
            # I need it because, for example, when a web server already listens
            # to the given port (thus, not a LibreOffice instance), this method
            # blocks.
            smgr = self.loContext.ServiceManager
            # Get the central desktop object
            self.oo = smgr.createInstanceWithContext(
                'com.sun.star.frame.Desktop', self.loContext)
        except NoConnectException:
            e = sys.exc_info()[1]
            raise ConverterError(CONNECT_ERROR % (self.port, e))

    def updateOdtDocument(self):
        '''If the input file is an ODT document, we will perform those tasks:
           1) update all annexes;
           2) update sections (if sections refer to external content, we try to
              include the content within the result file);
           3) load styles from an external template if given.
        '''
        from com.sun.star.lang import IndexOutOfBoundsException
        # I need to use IndexOutOfBoundsException because sometimes, when
        # using sections.getCount, UNO returns a number that is bigger than
        # the real number of sections (this is because it also counts the
        # sections that are present within the sub-documents to integrate)
        # Update all indexes
        indexes = self.doc.getDocumentIndexes()
        indexesCount = indexes.getCount()
        if indexesCount != 0:
            for i in range(indexesCount):
                try:
                    indexes.getByIndex(i).update()
                except IndexOutOfBoundsException:
                    pass
        # Update sections
        self.doc.updateLinks()
        sections = self.doc.getTextSections()
        sectionsCount = sections.getCount()
        if sectionsCount != 0:
            for i in range(sectionsCount-1, -1, -1):
                # I must walk into the section from last one to the first
                # one. Else, when "disposing" sections, I remove sections
                # and the remaining sections other indexes.
                try:
                    section = sections.getByIndex(i)
                    if section.FileLink and section.FileLink.FileURL:
                        section.dispose() # This method removes the
                        # <section></section> tags without removing the content
                        # of the section. Else, it won't appear.
                except IndexOutOfBoundsException:
                    pass
        # Import styles from an external file when required
        if self.templateUrl:
            params = self.props(('OverwriteStyles', True),
                                ('LoadPageStyles', False))
            self.doc.StyleFamilies.loadStylesFromURL(self.templateUrl, params)

    def loadDocument(self):
        from com.sun.star.lang import IllegalArgumentException, \
                                      IndexOutOfBoundsException
        try:
            # Loads the document to convert in a new hidden frame
            props = [('Hidden', True)]
            if self.inputType == 'csv':
                # Give some additional params if we need to open a CSV file
                props.append(('FilterFlags', '59,34,76,1'))
                #props.append(('FilterData', 'Any'))
            self.doc = self.oo.loadComponentFromURL(self.docUrl, "_blank", 0,
                                                    self.props(props))
            # Perform additional tasks for odt documents
            if self.inputType == 'odt': self.updateOdtDocument()
            try:
                self.doc.refresh()
            except AttributeError:
                pass
        except IllegalArgumentException:
            e = sys.exc_info()[1]
            raise ConverterError(URL_NOT_FOUND % (self.docPath, e))

    def convertDocument(self):
        '''Calls LO to perform a document conversion. Note that the conversion
           is not really done if the source and target documents have the same
           type.'''
        props = [('FilterName', self.resultFilter)]
        if self.resultType == 'csv': # Add options for CSV export (separator...)
            props.append(('FilterOptions', '59,34,76,1'))
        self.doc.storeToURL(self.resultUrl, self.props(props))

    def run(self):
        '''Connects to LO, does the job and disconnects'''
        self.connect()
        self.loadDocument()
        self.convertDocument()
        self.doc.close(True)

# ConverterScript-related messages ---------------------------------------------
WRONG_NB_OF_ARGS = 'Wrong number of arguments.'
ERROR_CODE = 1

# Class representing the command-line program ----------------------------------
class ConverterScript:
    usage = 'usage: python converter.py fileToConvert outputType [options]\n' \
            '   where fileToConvert is the absolute or relative pathname of\n' \
            '         the file you want to convert (or whose content like\n' \
            '         indexes need to be refreshed);\n'\
            '   and   outputType is the output format, that must be one of\n' \
            '         %s.\n' \
            ' "python" should be a UNO-enabled Python interpreter (ie the ' \
            '  one which is included in the LibreOffice distribution).' % \
            str(list(FILE_TYPES.keys()))
    def run(self):
        optParser = OptionParser(usage=ConverterScript.usage)
        optParser.add_option("-p", "--port", dest="port",
                             help="The port on which LibreOffice runs " \
                             "Default is %d." % DEFAULT_PORT,
                             default=DEFAULT_PORT, metavar="PORT", type='int')
        optParser.add_option("-t", "--template", dest="template",
                             default=None, metavar="TEMPLATE", type='string',
                             help="The path to a LibreOffice template from " \
                                  "which you may import styles.")
        (options, args) = optParser.parse_args()
        if len(args) != 2:
            sys.stderr.write(WRONG_NB_OF_ARGS)
            sys.stderr.write('\n')
            optParser.print_help()
            sys.exit(ERROR_CODE)
        converter = Converter(args[0], args[1], options.port, options.template)
        try:
            converter.run()
        except ConverterError:
            e = sys.exc_info()[1]
            sys.stderr.write(str(e))
            sys.stderr.write('\n')
            optParser.print_help()
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    ConverterScript().run()
# ------------------------------------------------------------------------------
