<!codeHeader!>
from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
import Products.<!applicationName!>.config
from appy.gen.plone25.mixins.UserMixin import UserMixin
from Extensions.appyWrappers import <!wrapperClass!>

schema = Schema((<!fields!>
),)
fullSchema = BaseSchema.copy() + schema.copy()

class <!applicationName!>User(BaseContent, UserMixin):
    '''Configuration flavour class for <!applicationName!>.'''
    security = ClassSecurityInfo()
    __implements__ = (getattr(BaseContent,'__implements__',()),)
    archetype_name = '<!applicationName!>User'
    meta_type = '<!applicationName!>User'
    portal_type = '<!applicationName!>User'
    allowed_content_types = []
    filter_content_types = 0
    global_allow = 1
    immediate_view = 'skyn/view'
    default_view = 'skyn/view'
    suppl_views = ()
    typeDescription = "<!applicationName!>User"
    typeDescMsgId = '<!applicationName!>User_edit_descr'
    i18nDomain = '<!applicationName!>'
    schema = fullSchema
    wrapperClass = <!wrapperClass!>
    for elem in dir(UserMixin):
        if not elem.startswith('__'): security.declarePublic(elem)
<!commonMethods!>
<!methods!>
registerType(<!applicationName!>User, '<!applicationName!>')
