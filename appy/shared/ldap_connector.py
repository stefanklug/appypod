# ------------------------------------------------------------------------------
import string
try:
    import ldap
except ImportError:
    # For people that do not care about ldap
    ldap = None

# ------------------------------------------------------------------------------
class LdapConfig:
    '''Parameters for authenticating users to an LDAP server. This class is
       used by gen-applications. For a pure, appy-independent LDAP connector,
       see the class LdapConnector below.'''
    ldapAttributes = { 'loginAttribute':None, 'emailAttribute':'email',
                       'fullNameAttribute':'title',
                       'firstNameAttribute':'firstName',
                       'lastNameAttribute':'name' }

    def __init__(self):
        self.server = '' # Name of the LDAP server
        self.port = None # Port for this server
        # Login and password of the technical power user that the Appy
        # application will use to connect to the LDAP.
        self.adminLogin = ''
        self.adminPassword = ''
        # LDAP attribute to use as login for authenticating users.
        self.loginAttribute = 'dn' # Can also be "mail", "sAMAccountName", "cn"
        # LDAP attributes for storing email
        self.emailAttribute = None
        # LDAP attribute for storing full name (first + last name)
        self.fullNameAttribute = None
        # Alternately, LDAP attributes for storing 1st & last names separately.
        self.firstNameAttribute = None
        self.lastNameAttribute = None
        # LDAP classes defining the users stored in the LDAP.
        self.userClasses = ('top', 'person')
        self.baseDn = '' # Base DN where to find users in the LDAP.
        self.scope = 'SUBTREE' # Scope of the search within self.baseDn
        # Is this server connection enabled ?
        self.enabled = True
        # The "user map" allows to put LDAP users into groups or assign them
        # roles. This dict will be used every time a local User will be created.
        # It can be while synchronizing all users (see m_synchronizeUsers
        # below) or when the user logs in for the first time (see m_getUser
        # below). This dict will NOT be used subsequently, when updating the
        # User instance. Every key must be a user login. Every value is an
        # appy.Object instance having the optional attributes:
        # "groups": a list of group IDs (logins);
        # "roles":  a list of global role names.
        self.userMap = {}

    def __repr__(self):
        '''Short string representation of this ldap config, for logging and
           debugging purposes.'''
        return self.getServerUri()

    def getServerUri(self):
        '''Returns the complete URI for accessing the LDAP, ie
           "ldap://some.ldap.server:389".'''
        port = self.port or 389
        return 'ldap://%s:%d' % (self.server, port)

    def getUserFilterValues(self, login=None):
        '''Gets the filter values required to perform a query for finding user
           corresponding to p_login in the LDAP, or all users if p_login is
           None.'''
        res = login and [(self.loginAttribute, login)] or []
        for userClass in self.userClasses:
            res.append( ('objectClass', userClass) )
        return res

    def getUserAttributes(self):
        '''Gets the attributes we want to get from the LDAP for characterizing
           a user.'''
        res = []
        for name in self.ldapAttributes.iterkeys():
            if getattr(self, name):
                res.append(getattr(self, name))
        return res

    def getUserParams(self, ldapData):
        '''Formats the user-related p_ldapData retrieved from the ldap, as a
           dict of params usable for creating or updating the corresponding
           Appy user.'''
        res = {}
        for name, appyName in self.ldapAttributes.items():
            if not appyName: continue
            # Get the name of the attribute as known in the LDAP
            ldapName = getattr(self, name)
            if not ldapName: continue
            if ldapData.has_key(ldapName) and ldapData[ldapName]:
                value = ldapData[ldapName]
                if isinstance(value, list): value = value[0]
                res[appyName] = value
        return res

    def setLocalUser(self, tool, attrs, login, password=None):
        '''Creates or updates the local User instance corresponding to a LDAP
           user from the LDAP, having p_login. Its other attributes are in
           p_attrs and, when relevant, its password is in p_password. This
           method returns a 2-tuple containing:
           * the local User instance;
           * the status of the operation:
             - "created" if the instance has been created,
             - "updated" if at least one data from p_attrs is different from the
               one stored on the existing User instance;
             - None else.
        '''
        # Do we already have a local User instance for this user ?
        status = None
        user = tool.search1('User', noSecurity=True, login=login)
        if user:
            # Yes. Update it with info about him from the LDAP
            for name, value in attrs.items():
                currentValue = getattr(user, name)
                if value != currentValue:
                    setattr(user, name, value)
                    status = 'updated'
            # Update user password, if given
            if password: user.setPassword(password, log=False)
            user.reindex()
        else:
            # Create the user
            user = tool.create('users', noSecurity=True, login=login,
                               source='ldap', **attrs)
            if password: user.setPassword(password, log=False)
            status = 'created'
            # Put him into groups and/or grant him some roles according to
            # self.userMap.
            if login in self.userMap:
                privileges = self.userMap[login]
                # Put the user in some groups
                groups = getattr(privileges, 'groups', None)
                if groups:
                    for groupLogin in groups:
                        group = tool.search1('Group', noSecurity=True,
                                             login=groupLogin)
                        group.link('users', user)
                # Grant him some roles
                roles = getattr(privileges, 'roles', None)
                if roles:
                    for role in roles: user.addRole(role)
                tool.log('%s: automatic privileges set.' % login)
        return user, status

    def getUser(self, tool, login, password):
        '''Returns a local User instance corresponding to a LDAP user if p_login
           and p_password correspond to a valid LDAP user.'''
        # Check if LDAP is enabled
        if not self.enabled: return
        # Get a connector to the LDAP server and connect to the LDAP server
        serverUri = self.getServerUri()
        connector = LdapConnector(serverUri, tool=tool)
        success, msg = connector.connect(self.adminLogin, self.adminPassword)
        if not success: return
        # Check if the user corresponding to p_login exists in the LDAP
        filter = connector.getFilter(self.getUserFilterValues(login))
        params = self.getUserAttributes()
        ldapData = connector.search(self.baseDn, self.scope, filter, params)
        if not ldapData: return
        # The user exists. Try to connect to the LDAP with this user in order
        # to validate its password.
        userConnector = LdapConnector(serverUri, tool=tool)
        success, msg = userConnector.connect(ldapData[0][0], password)
        if not success: return
        # The password is correct. We can create/update our local user
        # corresponding to this LDAP user.
        userParams = self.getUserParams(ldapData[0][1])
        user, status = self.setLocalUser(tool, userParams, login, password)
        return user

    def synchronizeUsers(self, tool):
        '''Synchronizes the local User copies with this LDAP user base. Returns
           a 2-tuple containing the number of created, updated and untouched
           local copies.'''
        if not self.enabled: raise Exception('LDAP config not enabled.')
        # Get a connector to the LDAP server and connect to the LDAP server
        serverUri = self.getServerUri()
        tool.log('reading users from %s...' % serverUri)
        connector = LdapConnector(serverUri, tool=tool)
        success, msg = connector.connect(self.adminLogin, self.adminPassword)
        if not success: raise Exception('Could not connect to %s' % serverUri)
        # Query the LDAP for users. Perform several queries to avoid having
        # error ldap.SIZELIMIT_EXCEEDED.
        params = self.getUserAttributes()
        # Count the number of created, updated and untouched users
        created = updated = untouched = 0
        for letter in string.ascii_lowercase:
            # Get all the users whose login starts with "letter"
            filter = connector.getFilter(self.getUserFilterValues('%s*'%letter))
            ldapData = connector.search(self.baseDn, self.scope, filter, params)
            if not ldapData: continue
            for userData in ldapData:
                # Get the user login
                login = userData[1][self.loginAttribute][0]
                # Get the other user parameters, as Appy wants it
                userParams = self.getUserParams(userData[1])
                # Create or update the user
                user, status = self.setLocalUser(tool, userParams, login)
                if status == 'created': created += 1
                elif status == 'updated': updated += 1
                else: untouched += 1
        tool.log('users synchronization: %d local user(s) created, ' \
                 '%d updated and %d untouched.'% (created, updated, untouched))
        return created, updated, untouched

# ------------------------------------------------------------------------------
class LdapConnector:
    '''This class manages the communication with a LDAP server.'''
    def __init__(self, serverUri, tentatives=5, ssl=False, timeout=5,
                 tool=None):
        # The URI of the LDAP server, ie ldap://some.ldap.server:389.
        self.serverUri = serverUri
        # The object that will represent the LDAP server
        self.server = None
        # The number of trials the connector will at most perform to the LDAP
        # server, when executing a query in it.
        self.tentatives = tentatives
        self.ssl = ssl
        # The timeout for every query to the LDAP.
        self.timeout = timeout
        # A tool from a Appy application can be given and will be used, ie for
        # logging purpose.
        self.tool = tool

    def log(self, message, type='info'):
        '''Logs via a Appy tool if available.'''
        if self.tool:
            self.tool.log(message, type=type)
        else:
            print(message)

    def connect(self, login, password):
        '''Connects to the LDAP server using p_login and p_password as
           credentials. If the connection succeeds, a server object is created
           in self.server and tuple (True, None) is returned. Else, tuple
           (False, errorMessage) is returned.'''
        try:
            self.server = ldap.initialize(self.serverUri)
            self.server.simple_bind_s(login, password)
            return True, None
        except AttributeError as ae:
            # When the ldap module is not there, trying to catch ldap.LDAPError
            # will raise an error.
            message = str(ae)
            self.log('Ldap connect error with login %s (%s).' % \
                     (login, message))
            return False, message
        except ldap.LDAPError as le:
            message = str(le)
            self.log('%s: connect error with login %s (%s).' % \
                     (self.serverUri, login, message))
            return False, message

    def getFilter(self, values):
        '''Builds and returns a LDAP filter based on p_values, a tuple or list
           of tuples (name,value).'''
        return '(&%s)' % ''.join(['(%s=%s)' % (n, v) for n, v in values])

    def search(self, baseDn, scope, filter, attributes=None):
        '''Performs a query in the LDAP at node p_baseDn, with the given
           p_scope. p_filter is a LDAP filter that constraints the search. It
           can be computed from a list of tuples (value, name) by method
           m_getFilter. p_attributes is the list of attributes that we will
           retrieve from the LDAP. If None, all attributes will be retrieved.'''
        if self.ssl: self.server.start_tls_s()
        try:
            # Get the LDAP constant corresponding to p_scope.
            scope = getattr(ldap, 'SCOPE_%s' % scope)
            # Perform the query.
            for i in range(self.tentatives):
                try:
                    return self.server.search_st(\
                        baseDn, scope, filterstr=filter, attrlist=attributes,
                        timeout=self.timeout)
                except ldap.TIMEOUT:
                    pass
        except ldap.LDAPError as le:
            self.log('LDAP query error %s: %s' % \
                     (le.__class__.__name__, str(le)))
# ------------------------------------------------------------------------------
