'''This package contains stuff used at run-time for installing a generated
   Plone product.'''

# ------------------------------------------------------------------------------
from appy.gen.plone25.installer import PloneInstaller as Plone25Installer

class ZCTextIndexInfo:
    '''Silly class used for storing information about a ZCTextIndex.'''
    lexicon_id = "plone_lexicon"
    index_type = 'Okapi BM25 Rank'

class PloneInstaller(Plone25Installer):
    '''This Plone installer runs every time the generated Plone product is
       installed or uninstalled (in the Plone configuration interface).'''
    @staticmethod
    def updateIndexes(ploneSite, indexInfo, logger):
        '''This method creates or updates, in a p_ploneSite, definitions of
           indexes in its portal_catalog, based on index-related information
           given in p_indexInfo. p_indexInfo is a dictionary of the form
           {s_indexName:s_indexType}. Here are some examples of index types:
           "FieldIndex", "ZCTextIndex", "DateIndex".'''
        catalog = ploneSite.portal_catalog
        indexNames = catalog.indexes()
        for indexName, indexType in indexInfo.iteritems():
            if indexName not in indexNames:
                # We need to create this index
                if indexType != 'ZCTextIndex':
                    catalog.addIndex(indexName, indexType)
                else:
                    catalog.addIndex(indexName,indexType,extra=ZCTextIndexInfo)
                logger.info('Creating index "%s" of type "%s"...' % \
                            (indexName, indexType))
                # Indexing database content based on this index.
                catalog.reindexIndex(indexName, ploneSite.REQUEST)
                logger.info('Done.')
        # TODO: if the index already exists but has not the same type, we
        # re-create it with the same type and we reindex it.
# ------------------------------------------------------------------------------
