'''This package contains stuff used at run-time for installing a generated
   Plone product.'''

# ------------------------------------------------------------------------------
from appy.gen.plone25.installer import PloneInstaller as Plone25Installer

class PloneInstaller(Plone25Installer):
    '''This Plone installer runs every time the generated Plone product is
       installed or uninstalled (in the Plone configuration panel).'''
# ------------------------------------------------------------------------------
