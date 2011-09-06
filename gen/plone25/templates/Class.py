<!codeHeader!>
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Products.Archetypes.atapi import *
import Products.<!applicationName!>.config
from Products.CMFCore.utils import UniqueObject
from appy.gen.plone25.mixins import BaseMixin
from appy.gen.plone25.mixins.ToolMixin import ToolMixin
from Extensions.appyWrappers import <!genClassName!>_Wrapper
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
    allowed_content_types = ()
    filter_content_types = 0
    global_allow = <!global_allow!>
    immediate_view = 'skyn/view'
    default_view = 'skyn/view'
    suppl_views = ()
    typeDescription = '<!genClassName!>'
    typeDescMsgId = '<!genClassName!>'
    i18nDomain = '<!applicationName!>'
    wrapperClass = <!genClassName!>_Wrapper
    schema = fullSchema
    for elem in dir(<!baseMixin!>):
        if not elem.startswith('__'): security.declarePublic(elem)
    <!static!>
<!commonMethods!>
<!methods!>
<!register!>
