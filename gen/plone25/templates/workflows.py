<!codeHeader!>
from Products.CMFCore.WorkflowTool import addWorkflowFactory
from Products.DCWorkflow.DCWorkflow import DCWorkflowDefinition
from appy.gen.plone25.workflow import WorkflowCreator
from Products.<!applicationName!>.config import PROJECTNAME
from Products.ExternalMethod.ExternalMethod import ExternalMethod
import logging
logger = logging.getLogger('<!applicationName!>')
from appy.gen.plone25.workflow import do

<!workflows!>
