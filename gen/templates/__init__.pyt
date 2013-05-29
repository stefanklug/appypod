<!codeHeader!>
# Test coverage-related stuff --------------------------------------------------
import sys
from appy.gen.mixins.TestMixin import TestMixin
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
        print('COVERAGE KO! The "coverage" program is not installed. You can ' \
              'download it from http://nedbatchelder.com/code/coverage.' \
              '\nHit <enter> to execute the test suite without coverage.')
        sys.stdin.readline()

def countTest():
    global numberOfExecutedTests
    numberOfExecutedTests += 1

# ------------------------------------------------------------------------------
import config
from appy.gen.installer import ZopeInstaller

# Zope-level installation of the generated product. ----------------------------
def initialize(context):
<!imports!>
    # I need to do those imports here; else, types and add permissions will not
    # be registered.
    classes = [<!classes!>]
    ZopeInstaller(context, config, classes).install()
# ------------------------------------------------------------------------------
