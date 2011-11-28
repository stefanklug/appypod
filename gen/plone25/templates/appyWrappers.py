# ------------------------------------------------------------------------------
from appy.gen import *
Grp = Group # Avoid name clashes with the Group class below and appy.gen.Group
from appy.gen.plone25.wrappers import AbstractWrapper
from appy.gen.plone25.wrappers.ToolWrapper import ToolWrapper as WTool
from appy.gen.plone25.wrappers.UserWrapper import UserWrapper as WUser
from appy.gen.plone25.wrappers.GroupWrapper import GroupWrapper as WGroup
from appy.gen.plone25.wrappers.TranslationWrapper import TranslationWrapper as WT
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
tfw = {"edit":"f","cell":"f","view":"f"} # Layout for Translation fields
<!imports!>

<!User!>
<!Group!>
<!Translation!>
<!Tool!>
<!wrappers!>
# ------------------------------------------------------------------------------
