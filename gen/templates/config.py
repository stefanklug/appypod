<!codeHeader!>
import os, os.path, sys, copy
import appy.gen
import wrappers
<!imports!>
    
# The following imports are here for allowing mixin classes to access those
# elements without being statically dependent on Zope packages.
from persistent.list import PersistentList
from zExceptions import BadRequest
from ZPublisher.HTTPRequest import BaseRequest
from OFS.Image import File
from ZPublisher.HTTPRequest import FileUpload
from AccessControl import getSecurityManager
from AccessControl.PermissionRole import rolesForPermissionOn
from DateTime import DateTime
from Products.ExternalMethod.ExternalMethod import ExternalMethod
from Products.Transience.Transience import TransientObjectContainer
import appy.gen
import logging
logger = logging.getLogger('<!applicationName!>')

# Some global variables --------------------------------------------------------
PROJECTNAME = '<!applicationName!>'
diskFolder = os.path.dirname(<!applicationName!>.__file__)
defaultAddRoles = [<!defaultAddRoles!>]
ADD_CONTENT_PERMISSIONS = {
<!addPermissions!>}

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
sourceLanguage = '<!sourceLanguage!>'
# ------------------------------------------------------------------------------
