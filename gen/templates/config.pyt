<!codeHeader!>
import os, os.path, sys, copy
import appy
import appy.gen
import wrappers
<!imports!>
    
# The following imports are here for allowing mixin classes to access those
# elements without being statically dependent on Zope packages.
from persistent.list import PersistentList
from OFS.Image import File
from ZPublisher.HTTPRequest import FileUpload
from DateTime import DateTime
import appy.gen
import logging
logger = logging.getLogger('<!applicationName!>')

# Some global variables --------------------------------------------------------
PROJECTNAME = '<!applicationName!>'
diskFolder = os.path.dirname(<!applicationName!>.__file__)

# Applications classes, in various formats
appClasses = [<!appClasses!>]
appClassNames = [<!appClassNames!>]
allClassNames = [<!allClassNames!>]
allShortClassNames = {<!allShortClassNames!>}

# In the following dict, we store, for every Appy class, the ordered list of
# fields.
attributes = {<!attributes!>}

# Application roles
applicationRoles = [<!roles!>]
applicationGlobalRoles = [<!gRoles!>]
grantableRoles = [<!grRoles!>]

try:
    appConfig = <!applicationName!>.Config
except AttributeError:
    appConfig = appy.gen.Config

# When Zope is starting or runs in test mode, there is no request object. We
# create here a fake one for storing Appy wrappers.
fakeRequest = appy.Object()
# ------------------------------------------------------------------------------
