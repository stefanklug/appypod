# ------------------------------------------------------------------------------
from appy.gen import *
Grp = Group # Avoid name clashes with the Group class below and appy.gen.Group
Pge = Page # Avoid name clashes with the Page class below and appy.gen.Page
from appy.gen.wrappers import AbstractWrapper
from appy.gen.wrappers.ToolWrapper import ToolWrapper as WTool
from appy.gen.wrappers.UserWrapper import UserWrapper as WUser
from appy.gen.wrappers.GroupWrapper import GroupWrapper as WGroup
from appy.gen.wrappers.TranslationWrapper import TranslationWrapper as WT
from appy.gen.wrappers.PageWrapper import PageWrapper as WPage
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
tfw = {"edit":"f","cell":"f","view":"f"} # Layout for Translation fields
<!imports!>

<!User!>
<!Group!>
<!Translation!>
<!Page!>
Page.pages.klass = Page
setattr(Page, Page.pages.back.attribute, Page.pages.back)

<!Tool!>
<!wrappers!>
# ------------------------------------------------------------------------------
