<!codeHeader!>
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
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
    immediate_view = 'skyn/view'
    default_view = 'skyn/view'
    suppl_views = ()
    typeDescription = '<!genClassName!>'
    typeDescMsgId = '<!genClassName!>_edit_descr'
    i18nDomain = '<!applicationName!>'
    schema = fullSchema
    wrapperClass = <!genClassName!>_Wrapper
    for elem in dir(ClassMixin):
        if not elem.startswith('__'): security.declarePublic(elem)
<!commonMethods!>
<!methods!>
<!register!>
