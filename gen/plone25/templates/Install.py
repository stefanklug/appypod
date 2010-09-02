<!codeHeader!>
import appy.gen
from appy.gen.plone25.installer import PloneInstaller
import Products.<!applicationName!>.config as config

# ------------------------------------------------------------------------------
def install(self, reinstall=False):
    '''Installation procedure.'''
    return PloneInstaller(reinstall, self, config).install()

# ------------------------------------------------------------------------------
def uninstall(self, reinstall=False):
    '''Uninstallation procedure.'''
    return PloneInstaller(reinstall, self, config).uninstall()
# ------------------------------------------------------------------------------
