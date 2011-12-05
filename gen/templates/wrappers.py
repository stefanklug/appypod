# ------------------------------------------------------------------------------
from appy.gen import *
Grp = Group # Avoid name clashes with the Group class below and appy.gen.Group
from appy.gen.wrappers import AbstractWrapper
from appy.gen.wrappers.ToolWrapper import ToolWrapper as WTool
from appy.gen.wrappers.UserWrapper import UserWrapper as WUser
from appy.gen.wrappers.GroupWrapper import GroupWrapper as WGroup
from appy.gen.wrappers.TranslationWrapper import TranslationWrapper as WT
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
