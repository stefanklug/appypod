<!codeHeader!>
from AccessControl import ClassSecurityInfo
from DateTime import DateTime
from Products.Archetypes.atapi import *
import Products.<!applicationName!>.config
from appy.gen.plone25.mixins.PodTemplateMixin import PodTemplateMixin
from Extensions.appyWrappers import <!wrapperClass!>

schema = Schema((<!fields!>
),)
fullSchema = BaseSchema.copy() + schema.copy()

class <!applicationName!>PodTemplate(BaseContent, PodTemplateMixin):
    '''POD template.'''
    security = ClassSecurityInfo()
    __implements__ = (getattr(BaseContent,'__implements__',()),)

    archetype_name = '<!applicationName!>PodTemplate'
    meta_type = '<!applicationName!>PodTemplate'
    portal_type = '<!applicationName!>PodTemplate'
    allowed_content_types = []
    filter_content_types = 0
    global_allow = 1
    #content_icon = '<!applicationName!>PodTemplate.gif'
    immediate_view = 'skyn/view'
    default_view = 'skyn/view'
    suppl_views = ()
    typeDescription = "<!applicationName!>PodTemplate"
    typeDescMsgId = '<!applicationName!>_edit_descr'
    wrapperClass = <!wrapperClass!>
    schema = fullSchema
    for elem in dir(PodTemplateMixin):
        if not elem.startswith('__'): security.declarePublic(elem)
<!commonMethods!>
<!methods!>
registerType(<!applicationName!>PodTemplate, '<!applicationName!>')
