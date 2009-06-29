<!codeHeader!>
import sys
try: # New CMF
    from Products.CMFCore.permissions import setDefaultRoles
except ImportError: # Old CMF
    from Products.CMFCore.CMFCorePermissions import setDefaultRoles

import Extensions.appyWrappers
<!imports!>

# The following imports are here for allowing mixin classes to access those
# elements without being statically dependent on Plone/Zope packages. Indeed,
# every Archetype instance has a method "getProductConfig" that returns this
# module.
from persistent.list import PersistentList
from Products.Archetypes.utils import DisplayList
from OFS.Image import File
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.PloneBatch import Batch
import logging
logger = logging.getLogger('<!applicationName!>')

# Some global variables --------------------------------------------------------
defaultAddRoles = [<!defaultAddRoles!>]
DEFAULT_ADD_CONTENT_PERMISSION = "Add portal content"
ADD_CONTENT_PERMISSIONS = {
<!addPermissions!>}
setDefaultRoles(DEFAULT_ADD_CONTENT_PERMISSION, tuple(defaultAddRoles))
product_globals = globals()
PROJECTNAME = '<!applicationName!>'
applicationRoles = [<!roles!>]
referers = {
<!referers!>
}
# In the following dict, we keep one instance for every Appy workflow defined
# in the application. Those prototypical instances will be used for executing
# user-defined actions and transitions. For each instance, we add a special
# attribute "_transitionsMapping" that allows to get Appy transitions from the
# names of DC transitions.
workflowInstances = {}
<!workflowInstancesInit!>
# ------------------------------------------------------------------------------
