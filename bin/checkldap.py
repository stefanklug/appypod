'''This script allows to check a LDAP connection.'''
import sys, ldap

# ------------------------------------------------------------------------------
class LdapTester:
    '''Usage: python checkldap.py ldapUri login password base.'''
    def __init__(self):
        # Get params from shell args.
        if len(sys.argv) != 5:
            print LdapTester.__doc__
            sys.exit(0)
        self.uri, self.login, self.password, self.base = sys.argv[1:]
        self.tentatives = 5
        self.timeout = 5
        self.attrList = ['uid']
        self.ssl = False

    def test(self):
        # Connect the the LDAP
        print 'Creating server object for server %s...' % self.uri
        server = ldap.initialize(self.uri)
        print 'Done. Login with %s...' % self.login
        server.simple_bind(self.login, self.password)
        if self.ssl:
            server.start_tls_s()
        try:
            for i in range(self.tentatives):
                try:
                    print 'Done. Performing a simple query on %s...' % self.base
                    res = server.search_st(
                        self.base, ldap.SCOPE_ONELEVEL, attrlist=self.attrList,
                        timeout=5)
                    print 'Got res', res
                    break
                except ldap.TIMEOUT:
                    print 'Got timeout.'
        except ldap.LDAPError, le:
            print le.__class__.__name__, le

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    LdapTester().test()
# ------------------------------------------------------------------------------
