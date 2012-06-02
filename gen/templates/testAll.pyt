<!codeHeader!>

from unittest import TestSuite
from Testing import ZopeTestCase
from Testing.ZopeTestCase import ZopeDocTestSuite
from appy.gen.mixins.TestMixin import TestMixin, beforeTest, afterTest
<!imports!>

# Initialize the Zope test system ----------------------------------------------
ZopeTestCase.installProduct('<!applicationName!>')

class Test(TestMixin, ZopeTestCase.ZopeTestCase):
    '''Base test class for <!applicationName!> test cases.'''

# Data needed for defining the tests -------------------------------------------
data = {'test_class': Test, 'setUp': beforeTest, 'tearDown': afterTest,
        'globs': {'appName': '<!applicationName!>'}}
modulesWithTests = [<!modulesWithTests!>]

# ------------------------------------------------------------------------------
def test_suite():
    return TestSuite([ZopeDocTestSuite(m, **data) for m in modulesWithTests])
# ------------------------------------------------------------------------------
