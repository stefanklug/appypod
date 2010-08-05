<!codeHeader!>
import os, os.path, sys, copy
import appy.gen
from Products.CMFCore.permissions import setDefaultRoles
import Extensions.appyWrappers as wraps
<!imports!>
    
# The following imports are here for allowing mixin classes to access those
# elements without being statically dependent on Plone/Zope packages. Indeed,
# every Archetype instance has a method "getProductConfig" that returns this
# module.
from persistent.list import PersistentList
from OFS.Image import File
from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.PloneBatch import Batch
import logging
logger = logging.getLogger('<!applicationName!>')

# Some global variables --------------------------------------------------------
PROJECTNAME = '<!applicationName!>'
diskFolder = os.path.dirname(<!applicationName!>.__file__)
defaultAddRoles = [<!defaultAddRoles!>]
DEFAULT_ADD_CONTENT_PERMISSION = "Add portal content"
ADD_CONTENT_PERMISSIONS = {
<!addPermissions!>}
setDefaultRoles(DEFAULT_ADD_CONTENT_PERMISSION, tuple(defaultAddRoles))
product_globals = globals()
applicationRoles = [<!roles!>]
rootClasses = [<!rootClasses!>]

# In the following dict, we keep one instance for every Appy workflow defined
# in the application. Those prototypical instances will be used for executing
# user-defined actions and transitions. For each instance, we add a special
# attribute "_transitionsMapping" that allows to get Appy transitions from the
# names of DC transitions.
workflowInstances = {}
<!workflowInstancesInit!>

# In the following dict, we store, for every Appy class, the ordered list of
# appy types (included inherited ones).
attributes = {<!attributes!>}
# In the followinf dict, we store, for every Appy class, a dict of appy types
# keyed by their names.
attributesDict = {<!attributesDict!>}
# ------------------------------------------------------------------------------
