<!codeHeader!>

from unittest import TestSuite
from Testing import ZopeTestCase
from Testing.ZopeTestCase import ZopeDocTestSuite
from Products.PloneTestCase import PloneTestCase
from appy.gen.plone25.mixins.TestMixin import TestMixin, beforeTest, afterTest
<!imports!>

# Initialize Zope & Plone test systems -----------------------------------------
ZopeTestCase.installProduct('<!applicationName!>')
PloneTestCase.setupPloneSite(products=['<!applicationName!>'])

class Test(PloneTestCase.PloneTestCase, TestMixin):
    '''Base test class for <!applicationName!> test cases.'''

# Data needed for defining the tests -------------------------------------------
data = {'test_class': Test, 'setUp': beforeTest, 'tearDown': afterTest,
        'globs': {'appName': '<!applicationName!>'}}
modulesWithTests = [<!modulesWithTests!>]

# ------------------------------------------------------------------------------
def test_suite():
    return TestSuite([ZopeDocTestSuite(m, **data) for m in modulesWithTests])
# ------------------------------------------------------------------------------
