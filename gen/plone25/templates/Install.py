<!codeHeader!>
from zExceptions import BadRequest
from Products.ExternalMethod.ExternalMethod import ExternalMethod
from Products.Archetypes.Extensions.utils import installTypes
from Products.Archetypes.Extensions.utils import install_subskin
from Products.Archetypes.config import TOOL_NAME as ARCHETYPETOOLNAME
from Products.Archetypes.atapi import listTypes
from Products.<!applicationName!>.config import applicationRoles,defaultAddRoles
from Products.<!applicationName!>.config import product_globals as GLOBALS
import appy.gen
from appy.gen.plone25.installer import PloneInstaller
<!imports!>
catalogMap = {}
<!catalogMap!>
appClasses = <!appClasses!>
appClassNames = [<!appClassNames!>]
allClassNames = [<!allClassNames!>]
workflows = {<!workflows!>}
showPortlet = <!showPortlet!>
# ------------------------------------------------------------------------------
def install(self, reinstall=False):
    '''Installation of product "<!applicationName!>"'''
    ploneInstaller = PloneInstaller(reinstall, "<!applicationName!>", self,
        <!minimalistPlone!>, appClasses, appClassNames, allClassNames,
        catalogMap, applicationRoles, defaultAddRoles, workflows,
        <!appFrontPage!>, showPortlet, globals())
    return ploneInstaller.install()

# ------------------------------------------------------------------------------
def uninstall(self, reinstall=False):
    '''Uninstallation of product "<!applicationName!>"'''
    ploneInstaller = PloneInstaller(reinstall, "<!applicationName!>", self,
        <!minimalistPlone!>, appClasses, appClassNames, allClassNames,
        catalogMap, applicationRoles, defaultAddRoles, workflows,
        <!appFrontPage!>, showPortlet, globals())
    return ploneInstaller.uninstall()
# ------------------------------------------------------------------------------
