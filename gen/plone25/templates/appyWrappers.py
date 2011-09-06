# ------------------------------------------------------------------------------
from appy.gen import *
from appy.gen.plone25.wrappers import AbstractWrapper
from appy.gen.plone25.wrappers.ToolWrapper import ToolWrapper as WTool
from appy.gen.plone25.wrappers.UserWrapper import UserWrapper as WUser
from appy.gen.plone25.wrappers.TranslationWrapper import TranslationWrapper as WT
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
tfw = {"edit":"f","cell":"f","view":"f"} # Layout for Translation fields
<!imports!>

<!User!>
<!Translation!>
<!Tool!>
<!wrappers!>
# ------------------------------------------------------------------------------
