# ------------------------------------------------------------------------------
try:
    import ldap
except ImportError:
    # For people that do not care about ldap.
    ldap = None

# ------------------------------------------------------------------------------
def connect(serverUri, login, password):
    '''Tries to connect to some LDAP server whose UIR is p_serverUri, using
       p_login and p_password as credentials.'''
    try:
        server = ldap.initialize(serverUri)
        server.simple_bind(login, password)
        return True, server, None
    except ldap.LDAPError, le:
        return False, None, str(le)

# ------------------------------------------------------------------------------
def authenticate(login, password, ldapConfig, tool):
    '''Tries to authenticate user p_login in the LDAP.'''
    # Connect to the ldap server.
    serverUri = cfg.getServerUri()
    success, server, msg = connect(serverUri, cfg.adminLogin, cfg.adminPassword)
    # Manage a connection error.
    if not success:
        tool.log('%s: connect error (%s).' % (serverUri, msg))
        return
    # Do p_login and p_password correspond to a user in the LDAP?
    try:
        pass
    except:
        pass
# ------------------------------------------------------------------------------
