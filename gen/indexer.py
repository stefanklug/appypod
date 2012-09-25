'''This file defines code for extracting, from field values, the text to be
   indexed.'''

# ------------------------------------------------------------------------------
from Products.ZCTextIndex.PipelineFactory import element_factory
from appy.shared.xml_parser import XmlParser
from appy.shared.utils import normalizeString

# ------------------------------------------------------------------------------
class XhtmlTextExtractor(XmlParser):
    '''Extracts text from XHTML.'''
    def startDocument(self):
        XmlParser.startDocument(self)
        self.res = []

    def endDocument(self):
        self.res = ' '.join(self.res)
        return XmlParser.endDocument(self)

    def characters(self, content):
        c = normalizeString(content, usage='extractedText').strip().lower()
        if len(c) > 1: self.res.append(c)
        return self.env

    # Do not raise exceptions when errors occur.
    def error(self, error): pass
    def fatalError(self, error): pass
    def warning(self, error): pass

# ------------------------------------------------------------------------------
class XhtmlIndexer:
    '''Extracts, from XHTML field values, the text to index.'''
    def process(self, text):
        # Wrap the XHTML chunk into a root tag, to get valid XML.
        text = '<p>%s</p>' % text[0]
        parser = XhtmlTextExtractor()
        text = parser.parse(text)
        res = text.split(' ')
        # Remove tokens of a single char.
        i = len(res)-1
        while i > -1 :
            if (len(res[i]) < 2) and not res[i].isdigit():
                del res[i]
            i -= 1
        return res

# ------------------------------------------------------------------------------
element_factory.registerFactory('XHTML indexer', 'XHTML indexer', XhtmlIndexer)
# ------------------------------------------------------------------------------
