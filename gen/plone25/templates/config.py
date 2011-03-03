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
from zExceptions import BadRequest
from ZPublisher.HTTPRequest import BaseRequest
try:
    import CustomizationPolicy
except ImportError:
    CustomizationPolicy = None
from OFS.Image import File
from ZPublisher.HTTPRequest import FileUpload
from AccessControl import getSecurityManager
from DateTime import DateTime
from Products.CMFCore import utils as cmfutils
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.PloneBatch import Batch
from Products.CMFPlone.utils import ToolInit
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFCore import DirectoryView
from Products.CMFCore.DirectoryView import manage_addDirectoryView
from Products.DCWorkflow.Transitions import TRIGGER_USER_ACTION
from Products.ExternalMethod.ExternalMethod import ExternalMethod
from Products.Archetypes.Extensions.utils import installTypes
from Products.Archetypes.Extensions.utils import install_subskin
from Products.Archetypes.config import TOOL_NAME as ARCHETYPETOOLNAME
from Products.Archetypes import listTypes, process_types
from Products.GenericSetup import EXTENSION, profile_registry
import appy.gen
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

# Applications classes, in various formats
rootClasses = [<!rootClasses!>]
appClasses = [<!appClasses!>]
appClassNames = [<!appClassNames!>]
allClassNames = [<!allClassNames!>]
# List of classes that must be hidden from the catalog
catalogMap = {}
<!catalogMap!>

# Dict whose keys are class names and whose values are workflow names (=the
# workflow used by the content type)
workflows = {<!workflows!>}
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
# In the following dict, we store, for every Appy class, a dict of appy types
# keyed by their names.
attributesDict = {<!attributesDict!>}

# Application roles
applicationRoles = [<!roles!>]
applicationGlobalRoles = [<!gRoles!>]
grantableRoles = [<!grRoles!>]

# Configuration options
showPortlet = <!showPortlet!>
languages = [<!languages!>]
languageSelector = <!languageSelector!>
minimalistPlone = <!minimalistPlone!>
appFrontPage = <!appFrontPage!>
sourceLanguage = '<!sourceLanguage!>'
# ------------------------------------------------------------------------------
