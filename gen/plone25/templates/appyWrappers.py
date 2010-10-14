# ------------------------------------------------------------------------------
from appy.gen import *
from appy.gen.plone25.wrappers import AbstractWrapper
from appy.gen.plone25.wrappers.ToolWrapper import ToolWrapper
from appy.gen.plone25.wrappers.UserWrapper import UserWrapper
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
<!imports!>

class User(UserWrapper):
    '''This class represents a user.'''
<!userBody!>
class Tool(ToolWrapper):
    '''This class represents the tool for this application.'''
    folder=True
<!toolBody!>
<!wrappers!>
# ------------------------------------------------------------------------------
