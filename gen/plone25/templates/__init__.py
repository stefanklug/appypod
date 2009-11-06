<!codeHeader!>
from config import *
import logging
try:
    import CustomizationPolicy
except ImportError:
    CustomizationPolicy = None
from Products.CMFCore import utils as cmfutils
from Products.CMFCore import DirectoryView
from Products.CMFPlone.utils import ToolInit
from Products.Archetypes.atapi import *
from Products.Archetypes import listTypes
from appy.gen.plone25.installer import ZopeInstaller
logger = logging.getLogger(PROJECTNAME)

def initialize(context):
<!imports!>
    # I need to do those imports here; else, types and add permissions will not
    # be registered.
    ZopeInstaller(context, PROJECTNAME,
        <!applicationName!>Tool.<!applicationName!>Tool,
        DEFAULT_ADD_CONTENT_PERMISSION, ADD_CONTENT_PERMISSIONS,
        logger, globals()).install()
