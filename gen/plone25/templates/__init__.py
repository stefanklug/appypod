<!codeHeader!>
# Test coverage-related stuff --------------------------------------------------
import sys
from appy.gen.plone25.mixins.TestMixin import TestMixin
covFolder = TestMixin.getCovFolder()
# The previous method checks in sys.argv whether Zope was lauched for performing
# coverage tests or not.
cov = None # The main Coverage instance as created by the coverage program.
totalNumberOfTests = <!totalNumberOfTests!>
numberOfExecutedTests = 0
if covFolder:
    try:
        import coverage
        from coverage import coverage
        cov = coverage()
        cov.start()
    except ImportError:
        print 'COVERAGE KO! The "coverage" program is not installed. You can ' \
              'download it from http://nedbatchelder.com/code/coverage.' \
              '\nHit <enter> to execute the test suite without coverage.'
        sys.stdin.readline()

def countTest():
    global numberOfExecutedTests
    numberOfExecutedTests += 1

# ------------------------------------------------------------------------------
from config import *
from ZPublisher.HTTPRequest import BaseRequest
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

# Zope-level installation of the generated product. ----------------------------
def initialize(context):
<!imports!>
    # I need to do those imports here; else, types and add permissions will not
    # be registered.
    ZopeInstaller(context, PROJECTNAME,
        <!applicationName!>Tool.<!applicationName!>Tool,
        DEFAULT_ADD_CONTENT_PERMISSION, ADD_CONTENT_PERMISSIONS,
        logger, globals()).install()
# ------------------------------------------------------------------------------
