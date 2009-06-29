# ------------------------------------------------------------------------------
from Products.CMFCore.utils import getToolByName

# ------------------------------------------------------------------------------
def installProduct(context):
    '''Installs the necessary products for running PloneMeeting.'''
    portal = context.getSite()
    qi = getToolByName(portal, 'portal_quickinstaller')
    if not qi.isProductInstalled('Archetypes'):
        qi.installProduct('Archetypes')
    if not qi.isProductInstalled('<!applicationName!>'):
        qi.installProduct('<!applicationName!>')
    return "Product <!applicationName!> installed."

# ------------------------------------------------------------------------------
def install_default(context):
    # Installation function of default profile.
    installProduct(context)
# ------------------------------------------------------------------------------
