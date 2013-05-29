'''This script allows to check a LDAP connection.'''
import sys, ldap

# ------------------------------------------------------------------------------
class LdapTester:
    '''Usage: python checkldap.py ldapUri login password base attrs filter

         ldapUri is, for example, "ldap://127.0.0.1:389"
         login is the login user DN, ie: "cn=gdy,o=geezteem"
         password is the password for this login
         base is the base DN where to perform the search, ie "ou=hr,o=GeezTeem"
         attrs is a comma-separated list of attrs we will retrieve in the LDAP,
               ie "uid,login"
         filter is the query filter, ie "(&(attr1=Geez*)(status=OK))"
    '''
    def __init__(self):
        # Get params from shell args.
        if len(sys.argv) != 7:
            print(LdapTester.__doc__)
            sys.exit(0)
        s = self
        s.uri, s.login, s.password, s.base, s.attrs, s.filter = sys.argv[1:]
        self.attrs = self.attrs.split(',')
        self.tentatives = 5
        self.timeout = 5
        self.attrList = ['cfwbV2cn', 'logindisabled']
        self.ssl = False

    def test(self):
        # Connect the the LDAP
        print('Creating server object for server %s...' % self.uri)
        server = ldap.initialize(self.uri)
        print('Done. Login with %s...' % self.login)
        server.simple_bind(self.login, self.password)
        if self.ssl:
            server.start_tls_s()
        try:
            for i in range(self.tentatives):
                try:
                    print('Done. Performing a simple query on %s...'% self.base)
                    res = server.search_st(
                        self.base, ldap.SCOPE_ONELEVEL, filterstr=self.filter,
                        attrlist=self.attrs, timeout=5)
                    print('Got %d entries' % len(res))
                    break
                except ldap.TIMEOUT:
                    print('Got timeout.')
        except ldap.LDAPError, le:
            print('%s %s' % (le.__class__.__name__, str(le)))

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    LdapTester().test()

# ------------------------------------------------------------------------------
