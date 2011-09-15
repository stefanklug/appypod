# ------------------------------------------------------------------------------
from Products.CMFCore.utils import getToolByName

# ------------------------------------------------------------------------------
def installProduct(context):
    '''Installs the necessary products for Appy.'''
    portal = context.getSite()
    qi = getToolByName(portal, 'portal_quickinstaller')
    if not qi.isProductInstalled('PloneLanguageTool'):
        qi.installProduct('PloneLanguageTool')
    if not qi.isProductInstalled('<!applicationName!>'):
        qi.installProduct('<!applicationName!>')
    return "<!applicationName!> installed."

# ------------------------------------------------------------------------------
def install_default(context):
    # Installation function of default profile.
    installProduct(context)
# ------------------------------------------------------------------------------
