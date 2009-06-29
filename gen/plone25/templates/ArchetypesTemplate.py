<!codeHeader!>
from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
import Products.<!applicationName!>.config
from Extensions.appyWrappers import <!genClassName!>_Wrapper
from appy.gen.plone25.mixins.ClassMixin import ClassMixin
<!imports!>

schema = Schema((<!fields!>
),)
fullSchema = <!baseSchema!>.copy() + schema.copy()

class <!genClassName!>(<!parents!>):
    '''<!classDoc!>'''
    security = ClassSecurityInfo()
    __implements__ = <!implements!>
    archetype_name = '<!genClassName!>'
    meta_type = '<!genClassName!>'
    portal_type = '<!genClassName!>'
    allowed_content_types = []
    filter_content_types = 0
    global_allow = 1
    immediate_view = '<!applicationName!>_appy_view'
    default_view = '<!applicationName!>_appy_view'
    suppl_views = ()
    typeDescription = '<!genClassName!>'
    typeDescMsgId = '<!genClassName!>_edit_descr'
    _at_rename_after_creation = True
    i18nDomain = '<!applicationName!>'
    schema = fullSchema
    wrapperClass = <!genClassName!>_Wrapper
<!commonMethods!>
<!methods!>
<!register!>
