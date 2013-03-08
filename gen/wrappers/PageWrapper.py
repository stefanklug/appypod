# ------------------------------------------------------------------------------
from appy.gen.wrappers import AbstractWrapper

# ------------------------------------------------------------------------------
class PageWrapper(AbstractWrapper):

    def validate(self, new, errors):
        '''Inter-field validation.'''
        return self._callCustom('validate', new, errors)

    def showSubPages(self):
        '''Show the sub-pages.'''
        if self.user.has_role('Manager'): return 'view'

    def showPortlet(self):
        '''Do not show the portlet for a page, unless sub-pages arre defined.'''
        if self.isEmpty('pages'): return False
        return True

    def onEdit(self, created):
        return self._callCustom('onEdit', created)
# ------------------------------------------------------------------------------
