# ------------------------------------------------------------------------------
# This file is part of Appy, a framework for building applications in the Python
# language. Copyright (C) 2007 Gaetan Delannay

# Appy is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

# Appy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# Appy. If not, see <http://www.gnu.org/licenses/>.

# ------------------------------------------------------------------------------
# Import stuff from appy.fields (and from a few other places too).
# This way, when an app gets "from appy.gen import *", everything is available.
from appy import Object
from appy.px import Px
from appy.fields import Field
from appy.fields.action import Action
from appy.fields.boolean import Boolean
from appy.fields.computed import Computed
from appy.fields.date import Date
from appy.fields.file import File
from appy.fields.float import Float
from appy.fields.info import Info
from appy.fields.integer import Integer
from appy.fields.list import List
from appy.fields.pod import Pod
from appy.fields.ref import Ref, autoref
from appy.fields.string import String, Selection
from appy.fields.search import Search, UiSearch
from appy.fields.group import Group, Column
from appy.fields.page import Page
from appy.fields.phase import Phase
from appy.fields.workflow import *
from appy.gen.layout import Table
from appy.gen.utils import No

# Make the following classes available here: people may need to override some
# of their PXs (defined as static attributes).
from appy.gen.wrappers import AbstractWrapper as BaseObject
from appy.gen.wrappers.ToolWrapper import ToolWrapper as BaseTool

# ------------------------------------------------------------------------------
class Model: pass
class Tool(Model):
    '''Subclass me to extend or modify the Tool class.'''
class User(Model):
    '''Subclass me to extend or modify the User class.'''

# ------------------------------------------------------------------------------
class LdapConfig:
    '''Parameters for authenticating users to an LDAP server.'''
    ldapAttributes = { 'loginAttribute':None, 'emailAttribute':'email',
                       'fullNameAttribute':'title',
                       'firstNameAttribute':'firstName',
                       'lastNameAttribute':'name' }

    def __init__(self):
        self.server = '' # Name of the LDAP server
        self.port = None # Port for this server.
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

    def getServerUri(self):
        '''Returns the complete URI for accessing the LDAP, ie
           "ldap://some.ldap.server:389".'''
        port = self.port or 389
        return 'ldap://%s:%d' % (self.server, port)

    def getUserFilterValues(self, login):
        '''Gets the filter values required to perform a query for finding user
           corresponding to p_login in the LDAP.'''
        res = [(self.loginAttribute, login)]
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
        for name, appyName in self.ldapAttributes.iteritems():
            if not appyName: continue
            # Get the name of the attribute as known in the LDAP.
            ldapName = getattr(self, name)
            if not ldapName: continue
            if ldapData.has_key(ldapName) and ldapData[ldapName]:
                value = ldapData[ldapName]
                if isinstance(value, list): value = value[0]
                res[appyName] = value
        return res

# ------------------------------------------------------------------------------
class Config:
    '''If you want to specify some configuration parameters for appy.gen and
       your application, please create a class named "Config" in the __init__.py
       file of your application and override some of the attributes defined
       here, ie:

       import appy.gen
       class Config(appy.gen.Config):
           langages = ('en', 'fr')
    '''
    # What skin to use for the web interface? Appy has 2 skins: the default
    # one (with a fixed width) and the "wide" skin (takes the whole page width).
    skin = None # None means: the default one. Could be "wide".
    # For every language code that you specify in this list, appy.gen will
    # produce and maintain translation files.
    languages = ['en']
    # If languageSelector is True, on every page, a language selector will
    # allow to switch between languages defined in self.languages. Else,
    # the browser-defined language will be used for choosing the language
    # of returned pages.
    languageSelector = False
    # People having one of these roles will be able to create instances
    # of classes defined in your application.
    defaultCreators = ['Manager']
    # The "root" classes are those that will get their menu in the user
    # interface. Put their names in the list below.
    rootClasses = []
    # Number of translations for every page on a Translation object
    translationsPerPage = 30
    # Language that will be used as a basis for translating to other
    # languages.
    sourceLanguage = 'en'
    # Activate or not the button on home page for asking a new password
    activateForgotPassword = True
    # Enable session timeout?
    enableSessionTimeout = False
    # If the following field is True, the login/password widget will be
    # discreet. This is for sites where authentication is not foreseen for
    # the majority of visitors (just for some administrators).
    discreetLogin = False
    # When using Ogone, place an instance of appy.gen.ogone.OgoneConfig in
    # the field below.
    ogone = None
    # When using Google analytics, specify here the Analytics ID
    googleAnalyticsId = None
    # Create a group for every global role?
    groupsForGlobalRoles = False
    # When using a LDAP for authenticating users, place an instance of class
    # LdapConfig above in the field below.
    ldap = None
# ------------------------------------------------------------------------------
