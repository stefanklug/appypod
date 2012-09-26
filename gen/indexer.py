'''This file defines code for extracting, from field values, the text to be
   indexed.'''

# ------------------------------------------------------------------------------
from appy.shared.xml_parser import XmlParser
from appy.shared.utils import normalizeText

# Default Appy indexes ---------------------------------------------------------
defaultIndexes = {
    'State': 'FieldIndex', 'UID': 'FieldIndex', 'Title': 'TextIndex',
    'SortableTitle': 'FieldIndex', 'SearchableText': 'XhtmlIndex',
    'Creator': 'FieldIndex', 'Created': 'DateIndex', 'ClassName': 'FieldIndex',
    'Allowed': 'KeywordIndex'}

# Stuff for creating or updating the indexes -----------------------------------
class TextIndexInfo:
    '''Parameters for a text ZCTextIndex.'''
    lexicon_id = "text_lexicon"
    index_type = 'Okapi BM25 Rank'

class XhtmlIndexInfo:
    '''Parameters for a html ZCTextIndex.'''
    lexicon_id = "xhtml_lexicon"
    index_type = 'Okapi BM25 Rank'

class ListIndexInfo:
    '''Parameters for a list ZCTextIndex.'''
    lexicon_id = "list_lexicon"
    index_type = 'Okapi BM25 Rank'

def updateIndexes(installer, indexInfo):
    '''This function updates the indexes defined in the catalog.'''
    catalog = installer.app.catalog
    logger = installer.logger
    for indexName, indexType in indexInfo.iteritems():
        indexRealType = indexType
        if indexType in ('XhtmlIndex', 'TextIndex', 'ListIndex'):
            indexRealType = 'ZCTextIndex'
        # If this index already exists but with a different type (or with a
        # deprecated lexicon), remove it.
        if indexName in catalog.indexes():
            indexObject = catalog.Indexes[indexName]
            oldType = indexObject.__class__.__name__
            toDelete = False
            if (oldType != indexRealType):
                toDelete = True
                info = indexRealType
            elif (oldType == 'ZCTextIndex') and \
                 (indexObject.lexicon_id == 'lexicon'):
                toDelete = True
                info = '%s (%s)' % (oldType, indexType)
            if toDelete:
                catalog.delIndex(indexName)
                logger.info('Index %s (%s) to replace as %s.' % \
                            (indexName, oldType, info))
        if indexName not in catalog.indexes():
            # We need to (re-)create this index.
            if indexType == 'TextIndex':
                catalog.addIndex(indexName, indexRealType, extra=TextIndexInfo)
            elif indexType == 'XhtmlIndex':
                catalog.addIndex(indexName, indexRealType, extra=XhtmlIndexInfo)
            elif indexType == 'ListIndex':
                catalog.addIndex(indexName, indexRealType, extra=ListIndexInfo)
            else:
                catalog.addIndex(indexName, indexType)
            # Indexing database content based on this index.
            logger.info('Reindexing %s (%s)...' % (indexName, indexType))
            catalog.reindexIndex(indexName, installer.app.REQUEST)
            logger.info('Done.')

# ------------------------------------------------------------------------------
def splitIntoWords(text):
    '''Split the cleaned index value p_text into words (returns a list of
       words). Words of a single char are ignored, excepted digits which are
       always kept. Duplicate words are removed (result is a set and not a
       list).'''
    res = text.split(' ')
    # Remove tokens of a single char (excepted if this char is a digit).
    i = len(res)-1
    while i > -1 :
        if (len(res[i]) < 2) and not res[i].isdigit():
            del res[i]
        i -= 1
    # Remove duplicates
    return set(res)

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
        c = normalizeText(content)
        if len(c) > 1: self.res.append(c)

# ------------------------------------------------------------------------------
class XhtmlIndexer:
    '''Extracts, from XHTML field values, the text to index.'''
    def process(self, texts):
        res = set()
        for text in texts:
            extractor = XhtmlTextExtractor(raiseOnError=False)
            cleanText = extractor.parse('<p>%s</p>' % text)
            res = res.union(splitIntoWords(cleanText))
        return list(res)

# ------------------------------------------------------------------------------
class TextIndexer:
    '''Extracts, from text field values, a normalized value to index.'''
    def process(self, texts):
        res = set()
        for text in texts:
            cleanText = normalizeText(text)
            res = res.union(splitIntoWords(cleanText))
        return list(res)

class ListIndexer:
    '''This lexicon does nothing: list of values must be indexed as is.'''
    def process(self, texts): return texts

# ------------------------------------------------------------------------------
try:
    from Products.ZCTextIndex.PipelineFactory import element_factory as ef
    ef.registerFactory('XHTML indexer', 'XHTML indexer', XhtmlIndexer)
    ef.registerFactory('Text indexer', 'Text indexer', TextIndexer)
    ef.registerFactory('List indexer', 'List indexer', ListIndexer)
except ImportError:
    # May occur at generation time.
    pass
# ------------------------------------------------------------------------------
