<!codeHeader!>
from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
import Products.<!applicationName!>.config
from appy.gen.plone25.mixins.FlavourMixin import FlavourMixin
from Extensions.appyWrappers import <!wrapperClass!>

predefinedSchema = Schema((<!predefinedFields!>
),)
schema = Schema((<!fields!>
),)
fullSchema = OrderedBaseFolderSchema.copy() + predefinedSchema.copy() + schema.copy()

class <!flavourName!>(OrderedBaseFolder, FlavourMixin):
    '''Configuration flavour class for <!applicationName!>.'''
    security = ClassSecurityInfo()
    __implements__ = (getattr(OrderedBaseFolderSchema,'__implements__',()),)
    archetype_name = '<!flavourName!>'
    meta_type = '<!flavourName!>'
    portal_type = '<!flavourName!>'
    allowed_content_types = []
    filter_content_types = 0
    global_allow = 1
    #content_icon = '<!flavourName!>.gif'
    immediate_view = '<!applicationName!>_appy_view'
    default_view = '<!applicationName!>_appy_view'
    suppl_views = ()
    typeDescription = "<!flavourName!>"
    typeDescMsgId = '<!flavourName!>_edit_descr'
    i18nDomain = '<!applicationName!>'
    schema = fullSchema
    allMetaTypes = <!metaTypes!>
    wrapperClass = <!wrapperClass!>
    _at_rename_after_creation = True
    for elem in dir(FlavourMixin):
        if not elem.startswith('__'): security.declarePublic(elem)
<!commonMethods!>
<!predefinedMethods!>
<!methods!>
registerType(<!flavourName!>, '<!applicationName!>')
