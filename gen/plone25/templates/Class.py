<!codeHeader!>
from OFS.SimpleItem import SimpleItem
from OFS.Folder import Folder
from appy.gen.utils import createObject
from AccessControl import ClassSecurityInfo
import Products.<!applicationName!>.config as cfg
from appy.gen.plone25.mixins import BaseMixin
from appy.gen.plone25.mixins.ToolMixin import ToolMixin
from Extensions.appyWrappers import <!genClassName!>_Wrapper as Wrapper

def manage_add<!genClassName!>(self, id, title='', REQUEST=None):
    '''Creates instances of this class.'''
    createObject(self, id, '<!genClassName!>', '<!applicationName!>')
    if REQUEST is not None: return self.manage_main(self, REQUEST)

class <!genClassName!>(<!parents!>):
    '''<!classDoc!>'''
    security = ClassSecurityInfo()
    meta_type = '<!genClassName!>'
    portal_type = '<!genClassName!>'
    allowed_content_types = ()
    filter_content_types = 0
    global_allow = 1
    icon = "ui/<!icon!>"
    wrapperClass = Wrapper
    for elem in dir(<!baseMixin!>):
        if not elem.startswith('__'): security.declarePublic(elem)
    def getTool(self): return self.getPhysicalRoot().config
    def getProductConfig(self): return cfg
    def index_html(self):
       """Redirects to /ui. Transfers the status message if any."""
       rq = self.REQUEST
       msg = rq.get('portal_status_message', '')
       if msg:
           url = self.getUrl(portal_status_message=msg)
       else:
           url = self.getUrl()
       return rq.RESPONSE.redirect(url)
    def do(self):
        '''BaseMixin.do can't be traversed by Zope if this class is the tool.
           So here, we redefine this method.'''
        return BaseMixin.do(self)
<!methods!>
