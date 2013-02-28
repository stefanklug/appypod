# ------------------------------------------------------------------------------
import os.path, time
import appy
from appy.gen.mail import sendMail
from appy.shared.utils import executeCommand
from appy.gen.wrappers import AbstractWrapper
from appy.gen.installer import loggedUsers

# ------------------------------------------------------------------------------
_PY = 'Please specify a file corresponding to a Python interpreter ' \
      '(ie "/usr/bin/python").'
FILE_NOT_FOUND = 'Path "%s" was not found.'
VALUE_NOT_FILE = 'Path "%s" is not a file. ' + _PY
NO_PYTHON = "Name '%s' does not starts with 'python'. " + _PY
NOT_UNO_ENABLED_PYTHON = '"%s" is not a UNO-enabled Python interpreter. ' \
                         'To check if a Python interpreter is UNO-enabled, ' \
                         'launch it and type "import uno". If you have no ' \
                         'ImportError exception it is ok.'

# ------------------------------------------------------------------------------
class ToolWrapper(AbstractWrapper):
    def validPythonWithUno(self, value):
        '''This method represents the validator for field unoEnabledPython.'''
        if value:
            if not os.path.exists(value):
                return FILE_NOT_FOUND % value
            if not os.path.isfile(value):
                return VALUE_NOT_FILE % value
            if not os.path.basename(value).startswith('python'):
                return NO_PYTHON % value
            if os.system('%s -c "import uno"' % value):
                return NOT_UNO_ENABLED_PYTHON % value
        return True

    def isManager(self):
        '''Some pages on the tool can only be accessed by managers.'''
        if self.user.has_role('Manager'): return 'view'

    def isManagerEdit(self):
        '''Some pages on the tool can only be accessed by managers, also in
           edit mode.'''
        if self.user.has_role('Manager'): return True

    def computeConnectedUsers(self):
        '''Computes a table showing users that are currently connected.'''
        res = '<table cellpadding="0" cellspacing="0" class="list"><tr>' \
              '<th></th><th>%s</th></tr>' % self.translate('last_user_access')
        rows = []
        for userId, lastAccess in loggedUsers.items():
            user = self.search1('User', noSecurity=True, login=userId)
            if not user: continue # Could have been deleted in the meanwhile
            fmt = '%s (%s)' % (self.dateFormat, self.hourFormat)
            access = time.strftime(fmt, time.localtime(lastAccess))
            rows.append('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>' % \
                        (user.o.absolute_url(), user.title,access))
        return res + '\n'.join(rows) + '</table>'

    podOutputFormats = ('odt', 'pdf', 'doc', 'rtf', 'ods', 'xls')
    def getPodOutputFormats(self):
        '''Gets the available output formats for POD documents.'''
        return [(of, self.translate(of)) for of in self.podOutputFormats]

    def getInitiator(self, field=False):
        '''Retrieves the object that triggered the creation of the object
           being currently created (if any), or the name of the field in this
           object if p_field is given.'''
        nav = self.o.REQUEST.get('nav', '')
        if not nav or not nav.startswith('ref.'): return
        if not field: return self.getObject(nav.split('.')[1])
        return nav.split('.')[2].split(':')[0]

    def getObject(self, uid):
        '''Allow to retrieve an object from its unique identifier p_uid.'''
        return self.o.getObject(uid, appy=True)

    def getDiskFolder(self):
        '''Returns the disk folder where the Appy application is stored.'''
        return self.o.config.diskFolder

    def getClass(self, zopeName):
        '''Gets the Appy class corresponding to technical p_zopeName.'''
        return self.o.getAppyClass(zopeName)

    def getAttributeName(self, attributeType, klass, attrName=None):
        '''Some names of Tool attributes are not easy to guess. For example,
           the attribute that stores the names of the columns to display in
           query results for class A that is in package x.y is
           "tool.resultColumnsForx_y_A". This method generates the attribute
           name based on p_attributeType, a p_klass from the application, and a
           p_attrName (given only if needed). p_attributeType may be:

           "podTemplate"
               Stores the pod template for p_attrName.

           "formats"
               Stores the output format(s) of a given pod template for
               p_attrName.

           "resultColumns"
               Stores the list of columns that must be shown when displaying
               instances of a given root p_klass.

           "enableAdvancedSearch"
               Determines if the advanced search screen must be enabled for
               p_klass.

           "numberOfSearchColumns"
               Determines in how many columns the search screen for p_klass
               is rendered.

           "searchFields"
               Determines, among all indexed fields for p_klass, which one will
               really be used in the search screen.
        '''
        fullClassName = self.o.getPortalType(klass)
        res = '%sFor%s' % (attributeType, fullClassName)
        if attrName: res += '_%s' % attrName
        return res

    def getAvailableLanguages(self):
        '''Returns the list of available languages for this application.'''
        return [(t.id, t.title) for t in self.translations]

    def convert(self, fileName, format):
        '''Launches a UNO-enabled Python interpreter as defined in the self for
           converting, using OpenOffice in server mode, a file named p_fileName
           into an output p_format.'''
        convScript = '%s/pod/converter.py' % os.path.dirname(appy.__file__)
        cmd = '%s %s "%s" %s -p%d' % (self.unoEnabledPython, convScript,
                                      fileName, format, self.openOfficePort)
        self.log('Executing %s...' % cmd)
        return executeCommand(cmd) # The result can contain an error message

    def sendMail(self, to, subject, body, attachments=None):
        '''Sends a mail. See doc for appy.gen.mail.sendMail.'''
        sendMail(self, to, subject, body, attachments=attachments)

    def refreshSecurity(self):
        '''Refreshes, on every object in the database, security-related,
           workflow-managed information.'''
        context = {'nb': 0}
        for className in self.o.getProductConfig().allClassNames:
            self.compute(className, context=context, noSecurity=True,
                         expression="ctx['nb'] += int(obj.o.refreshSecurity())")
        msg = 'Security refresh: %d object(s) updated.' % context['nb']
        self.log(msg)

    def refreshCatalog(self, startObject=None):
        '''Reindex all Appy objects. For some unknown reason, method
           catalog.refreshCatalog is not able to recatalog Appy objects.'''
        if not startObject:
            # This is a global refresh. Clear the catalog completely, and then
            # reindex all Appy-managed objects, ie those in folders "config"
            # and "data".
            # First, clear the catalog.
            self.log('Recomputing the whole catalog...')
            app = self.o.getParentNode()
            app.catalog._catalog.clear()
            nb = 1
            failed = []
            for obj in app.config.objectValues():
                subNb, subFailed = self.refreshCatalog(startObject=obj)
                nb += subNb
                failed += subFailed
            try:
                app.config.reindex()
            except:
                failed.append(app.config)
            # Then, refresh objects in the "data" folder.
            for obj in app.data.objectValues():
                subNb, subFailed = self.refreshCatalog(startObject=obj)
                nb += subNb
                failed += subFailed
            # Re-try to index all objects for which reindexation has failed.
            for obj in failed: obj.reindex()
            if failed:
                failMsg = ' (%d retried)' % len(failed)
            else:
                failMsg = ''
            self.log('%d object(s) were reindexed%s.' % (nb, failMsg))
        else:
            nb = 1
            failed = []
            for obj in startObject.objectValues():
                subNb, subFailed = self.refreshCatalog(startObject=obj)
                nb += subNb
                failed += subFailed
            try:
                startObject.reindex()
            except Exception, e:
                failed.append(startObject)
            return nb, failed

    def validate(self, new, errors):
        '''Validates that uploaded POD templates and output types are
           compatible.'''
        page = self.request.get('page', 'main')
        if page == 'documents':
            # Check that uploaded templates and output formats are compatible.
            for fieldName in dir(new):
                # Ignore fields which are not POD templates.
                if not fieldName.startswith('podTemplate'): continue
                # Get the file name, either from the newly uploaded file or
                # from the existing file stored in the database.
                if getattr(new, fieldName):
                    fileName = getattr(new, fieldName).filename
                else:
                    fileName = getattr(self, fieldName).name
                # Get the extension of the uploaded file.
                ext = os.path.splitext(fileName)[1][1:]
                # Get the chosen output formats for this template.
                formatsFieldName = 'formatsFor%s' % fieldName[14:]
                formats = getattr(new, formatsFieldName)
                error = False
                if ext == 'odt':
                    error = ('ods' in formats) or ('xls' in formats)
                elif ext == 'ods':
                    error = ('odt' in formats) or ('pdf' in formats) or \
                            ('doc' in formats) or ('rtf' in formats)
                if error:
                    msg = 'This (these) format(s) cannot be used with ' \
                          'this template.'
                    setattr(errors, formatsFieldName, msg)
        return self._callCustom('validate', new, errors)
# ------------------------------------------------------------------------------
