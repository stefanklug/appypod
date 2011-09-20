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
from Products.ExternalMethod.ExternalMethod import ExternalMethod
from Products.Archetypes.Extensions.utils import installTypes
from Products.Archetypes.Extensions.utils import install_subskin
from Products.Archetypes.config import TOOL_NAME as ARCHETYPETOOLNAME
from Products.Archetypes import listTypes, process_types
from Products.GenericSetup import EXTENSION, profile_registry
from Products.Transience.Transience import TransientObjectContainer
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

# In the following dict, we store, for every Appy class, the ordered list of
# appy types (included inherited ones).
attributes = {<!attributes!>}

# Application roles
applicationRoles = [<!roles!>]
applicationGlobalRoles = [<!gRoles!>]
grantableRoles = [<!grRoles!>]

# Configuration options
languages = [<!languages!>]
languageSelector = <!languageSelector!>
appFrontPage = <!appFrontPage!>
sourceLanguage = '<!sourceLanguage!>'
# ------------------------------------------------------------------------------
