# ------------------------------------------------------------------------------
import os.path
import appy
from appy.shared.utils import executeCommand
from appy.gen.wrappers import AbstractWrapper

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
        '''Some pages on the tool can only be accessed by God.'''
        if self.user.has_role('Manager'): return 'view'

    def isManagerEdit(self):
        '''Some pages on the tool can only be accessed by God, also in edit.'''
        if self.user.has_role('Manager'): return True

    podOutputFormats = ('odt', 'pdf', 'doc', 'rtf')
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
           "tool.resultColumnsForx_y_A". Other example: the attribute that
           stores the editable default value of field "f1" of class x.y.A is
           "tool.defaultValueForx_y_A_f1". This method generates the attribute
           name based on p_attributeType, a p_klass from the application, and a
           p_attrName (given only if needed, for example if p_attributeType is
           "defaultValue"). p_attributeType may be:

           "defaultValue"
               Stores the editable default value for a given p_attrName of a
               given p_klass.

           "podTemplate"
               Stores the pod template for p_attrName.

           "formats"
               Stores the output format(s) of a given pod template for
               p_attrName.

           "resultColumns"
               Stores the list of columns that must be shown when displaying
               instances of the a given root p_klass.

           "enableAdvancedSearch"
               Determines if the advanced search screen must be enabled for
               p_klass.

           "numberOfSearchColumns"
               Determines in how many columns the search screen for p_klass
               is rendered.

           "searchFields"
               Determines, among all indexed fields for p_klass, which one will
               really be used in the search screen.

           "optionalFields"
               Stores the list of optional attributes that are in use in the
               tool for the given p_klass.

           "showWorkflow"
               Stores the boolean field indicating if we must show workflow-
               related information for p_klass or not.

           "showAllStatesInPhase"
               Stores the boolean field indicating if we must show all states
               linked to the current phase or not. If this field is False, we
               simply show the current state, be it linked to the current phase
               or not.
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
            # This is a global refresh. Clear the catallog completely, and then
            # reindex all Appy-managed objects, ie those in folders "config"
            # and "data".
            # First, clear the catalog.
            app = self.o.getParentNode()
            app.catalog._catalog.clear()
            app.config.reindex()
            nb = 1
            for obj in app.config.objectValues():
                nb += self.refreshCatalog(startObject=obj)
            # Then, refresh objects in the "data" folder.
            for obj in app.data.objectValues():
                nb += self.refreshCatalog(startObject=obj)
            print '%d object(s) were reindexed.' % nb
        else:
            startObject.reindex()
            nb = 1
            for obj in startObject.objectValues():
                nb += self.refreshCatalog(startObject=obj)
            return nb
# ------------------------------------------------------------------------------
