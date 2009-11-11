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
import sys, os, os.path, time, signal, unicodedata
from optparse import OptionParser

ODT_FILE_TYPES = {'doc': 'MS Word 97', # Could be 'MS Word 2003 XML'
                  'pdf': 'writer_pdf_Export',
                  'rtf': 'Rich Text Format',
                  'txt': 'Text',
                  'html': 'HTML (StarWriter)',
                  'htm': 'HTML (StarWriter)',
                  'odt': 'ODT'}
# Conversion to ODT does not make any conversion; it simply updates indexes and
# linked documents.

# ------------------------------------------------------------------------------
class ConverterError(Exception): pass

# ConverterError-related messages ----------------------------------------------
DOC_NOT_FOUND = 'Document "%s" was not found.'
URL_NOT_FOUND = 'Doc URL "%s" is wrong. %s'
BAD_RESULT_TYPE = 'Bad result type "%s". Available types are %s.'
CANNOT_WRITE_RESULT = 'I cannot write result "%s". %s'
CONNECT_ERROR = 'Could not connect to OpenOffice on port %d. UNO ' \
                '(OpenOffice API) says: %s.'

# Some constants ---------------------------------------------------------------
DEFAULT_PORT = 2002

# ------------------------------------------------------------------------------
class Converter:
    '''Converts an ODT document into pdf, doc, txt or rtf.'''
    exeVariants = ('soffice.exe', 'soffice')
    pathReplacements = {'program files': 'progra~1',
                        'openoffice.org 1': 'openof~1',
                        'openoffice.org 2': 'openof~1',
                        }
    def __init__(self, docPath, resultType, port=DEFAULT_PORT):
        self.port = port
        self.docUrl = self.getDocUrl(docPath)
        self.docUrlStr = unicodedata.normalize('NFKD', self.docUrl).encode(
            "ascii", "ignore")
        self.resultFilter = self.getResultFilter(resultType)
        self.resultUrl = self.getResultUrl(resultType)
        self.ooContext = None
        self.oo = None # OpenOffice application object
        self.doc = None # OpenOffice loaded document
    def getDocUrl(self, docPath):
        import uno
        if not os.path.exists(docPath) and not os.path.isfile(docPath):
            raise ConverterError(DOC_NOT_FOUND % docPath)
        docAbsPath = os.path.abspath(docPath)
        return uno.systemPathToFileUrl(docAbsPath)
    def getResultFilter(self, resultType):
        if ODT_FILE_TYPES.has_key(resultType):
            res = ODT_FILE_TYPES[resultType]
        else:
            raise ConverterError(BAD_RESULT_TYPE % (resultType,
                                                    ODT_FILE_TYPES.keys()))
        return res
    def getResultUrl(self, resultType):
        baseName = os.path.splitext(self.docUrlStr)[0]
        if resultType != 'odt':
            res = '%s.%s' % (baseName, resultType)
        else:
            res = '%s.res.%s' % (baseName, resultType)
        fileName = res[7:]
        try:
            f = open(fileName, 'w')
            f.write('Hello')
            f.close()
            os.remove(fileName)
            return res
        except OSError, oe:
            raise ConverterError(CANNOT_WRITE_RESULT % (res, oe))
    def connect(self):
        '''Connects to OpenOffice'''
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
            self.ooContext = resolver.resolve(
                'uno:socket,host=localhost,port=%d;urp;StarOffice.' \
                'ComponentContext' % self.port)
            # Is seems that we can't define a timeout for this method.
            # I need it because, for example, when a web server already listens
            # to the given port (thus, not a OpenOffice instance), this method
            # blocks.
            smgr = self.ooContext.ServiceManager
            # Get the central desktop object
            self.oo = smgr.createInstanceWithContext(
                'com.sun.star.frame.Desktop', self.ooContext)
        except NoConnectException, nce:
            raise ConverterError(CONNECT_ERROR % (self.port, nce))
    def disconnect(self):
        self.doc.close(True)
        # Do a nasty thing before exiting the python process. In case the
        # last call is a oneway call (e.g. see idl-spec of insertString),
        # it must be forced out of the remote-bridge caches before python
        # exits the process. Otherwise, the oneway call may or may not reach
        # the target object.
        # I do this here by calling a cheap synchronous call (getPropertyValue).
        self.ooContext.ServiceManager
    def loadDocument(self):
        from com.sun.star.lang import IllegalArgumentException, \
                                      IndexOutOfBoundsException
        # I need to use IndexOutOfBoundsException because sometimes, when
        # using sections.getCount, UNO returns a number that is bigger than
        # the real number of sections (this is because it also counts the
        # sections that are present within the sub-documents to integrate)
        from com.sun.star.beans import PropertyValue
        try:
            # Load the document to convert in a new hidden frame
            prop = PropertyValue()
            prop.Name = 'Hidden'
            prop.Value = True
            self.doc = self.oo.loadComponentFromURL(self.docUrl, "_blank", 0,
                                                    (prop,))
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
        except IllegalArgumentException, iae:
            raise ConverterError(URL_NOT_FOUND % (self.docUrlStr, iae))
    def convertDocument(self):
        if self.resultFilter != 'ODT':
            # I must really perform a conversion
            from com.sun.star.beans import PropertyValue
            prop = PropertyValue()
            prop.Name = 'FilterName'
            prop.Value = self.resultFilter
            self.doc.storeToURL(self.resultUrl, (prop,))
        else:
            self.doc.storeToURL(self.resultUrl, ())
    def run(self):
        self.connect()
        self.loadDocument()
        self.convertDocument()
        self.disconnect()

# ConverterScript-related messages ---------------------------------------------
WRONG_NB_OF_ARGS = 'Wrong number of arguments.'
ERROR_CODE = 1

# Class representing the command-line program ----------------------------------
class ConverterScript:
    usage = 'usage: python converter.py fileToConvert outputType [options]\n' \
            '   where fileToConvert is the absolute or relative pathname of\n' \
            '         the ODT file you want to convert;\n'\
            '   and   outputType is the output format, that must be one of\n' \
            '         %s.\n' \
            ' "python" should be a UNO-enabled Python interpreter (ie the one\n' \
            ' which is included in the OpenOffice.org distribution).' % \
            str(ODT_FILE_TYPES.keys())
    def run(self):
        optParser = OptionParser(usage=ConverterScript.usage)
        optParser.add_option("-p", "--port", dest="port",
                             help="The port on which OpenOffice runs " \
                             "Default is %d." % DEFAULT_PORT,
                             default=DEFAULT_PORT, metavar="PORT", type='int')
        (options, args) = optParser.parse_args()
        if len(args) != 2:
            sys.stderr.write(WRONG_NB_OF_ARGS)
            sys.stderr.write('\n')
            optParser.print_help()
            sys.exit(ERROR_CODE)
        converter = Converter(args[0], args[1], options.port)
        try:
            converter.run()
        except ConverterError, ce:
            sys.stderr.write(str(ce))
            sys.stderr.write('\n')
            optParser.print_help()
            sys.exit(ERROR_CODE)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    ConverterScript().run()
# ------------------------------------------------------------------------------
