<!codeHeader!>
from AccessControl import ClassSecurityInfo
from Products.Archetypes.atapi import *
from Products.CMFCore.utils import UniqueObject
import Products.<!applicationName!>.config
from appy.gen.plone25.mixins.ToolMixin import ToolMixin
from Extensions.appyWrappers import AbstractWrapper, <!wrapperClass!>

predefinedSchema = Schema((<!predefinedFields!>
),)
schema = Schema((<!fields!>
),)
fullSchema = OrderedBaseFolderSchema.copy() + predefinedSchema.copy() + schema.copy()

class <!toolName!>(UniqueObject, OrderedBaseFolder, ToolMixin):
    '''Tool for <!applicationName!>.'''
    security = ClassSecurityInfo()
    __implements__ = (getattr(UniqueObject,'__implements__',()),) + (getattr(OrderedBaseFolder,'__implements__',()),)

    archetype_name = '<!toolName!>'
    meta_type = '<!toolName!>'
    portal_type = '<!toolName!>'
    allowed_content_types = ()
    filter_content_types = 0
    global_allow = 0
    #content_icon = '<!toolName!>.gif'
    immediate_view = '<!applicationName!>_appy_view'
    default_view = '<!applicationName!>_appy_view'
    suppl_views = ()
    typeDescription = "<!toolName!>"
    typeDescMsgId = '<!toolName!>_edit_descr'
    i18nDomain = '<!applicationName!>'
    wrapperClass = <!wrapperClass!>
    _at_rename_after_creation = True
    schema = fullSchema
    schema["id"].widget.visible = False
    schema["title"].widget.visible = False
    # When browsing into the tool, the 'configure' portlet should be dislayed.
    left_slots = ['here/portlet_prefs/macros/portlet']
    right_slots = []
    for elem in dir(ToolMixin):
        if not elem.startswith('__'): security.declarePublic(elem)

    # Tool constructor has no id argument, the id is fixed.
    def __init__(self, id=None):
        OrderedBaseFolder.__init__(self, '<!toolInstanceName!>')
        self.setTitle('<!applicationName!>')
<!commonMethods!>
<!predefinedMethods!>
<!methods!>
registerType(<!toolName!>, '<!applicationName!>')
