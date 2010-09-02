# ------------------------------------------------------------------------------
from appy.gen import *
from appy.gen.plone25.wrappers import AbstractWrapper
from appy.gen.plone25.wrappers.ToolWrapper import ToolWrapper
from appy.gen.plone25.wrappers.FlavourWrapper import FlavourWrapper
from appy.gen.plone25.wrappers.PodTemplateWrapper import PodTemplateWrapper
from appy.gen.plone25.wrappers.UserWrapper import UserWrapper
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
<!imports!>

class PodTemplate(PodTemplateWrapper):
    '''This class represents a POD template for this application.'''
<!podTemplateBody!>
class User(UserWrapper):
    '''This class represents a user.'''
<!userBody!>
class Flavour(FlavourWrapper):
    '''This class represents the Appy class used for defining a flavour.'''
    folder=True
<!flavourBody!>
class Tool(ToolWrapper):
    '''This class represents the tool for this application.'''
    folder=True
<!toolBody!>
<!wrappers!>
# ------------------------------------------------------------------------------
