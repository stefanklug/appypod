'''This package contains base classes for wrappers that hide to the Appy
   developer the real classes used by the underlying web framework.'''

# ------------------------------------------------------------------------------
import time, os.path, mimetypes, unicodedata
from appy.gen import Search
from appy.gen.utils import sequenceTypes
from appy.shared.utils import getOsTempFolder
from appy.shared.xml_parser import XmlMarshaller

# Some error messages ----------------------------------------------------------
WRONG_FILE_TUPLE = 'This is not the way to set a file. You can specify a ' \
    '2-tuple (fileName, fileContent) or a 3-tuple (fileName, fileContent, ' \
    'mimeType).'

# ------------------------------------------------------------------------------
class AbstractWrapper:
    '''Any real web framework object has a companion object that is an instance
       of this class.'''
    def __init__(self, o):
        self.__dict__['o'] = o
    def _set_file_attribute(self, name, v):
        '''Updates the value of a file attribute named p_name with value p_v.
           p_v may be:
           - a string value containing the path to a file on disk;
           - a 2-tuple (fileName, fileContent) where
             * fileName = the name of the file (ie "myFile.odt")
             * fileContent = the binary or textual content of the file or an
               open file handler.
           - a 3-tuple (fileName, fileContent, mimeType) where mimeType is the
              v MIME type of the file.'''
        ploneFileClass = self.o.getProductConfig().File
        if isinstance(v, ploneFileClass):
            exec "self.o.set%s%s(v)" % (name[0].upper(), name[1:])
        elif isinstance(v, FileWrapper):
            setattr(self, name, v._atFile)
        elif isinstance(v, basestring):
            f = file(v)
            fileName = os.path.basename(v)
            fileId = 'file.%f' % time.time()
            ploneFile = ploneFileClass(fileId, fileName, f)
            ploneFile.filename = fileName
            ploneFile.content_type = mimetypes.guess_type(fileName)[0]
            setattr(self, name, ploneFile)
            f.close()
        elif type(v) in sequenceTypes:
            # It should be a 2-tuple or 3-tuple
            fileName = None
            mimeType = None
            if len(v) == 2:
                fileName, fileContent = v
            elif len(v) == 3:
                fileName, fileContent, mimeType = v
            else:
                raise WRONG_FILE_TUPLE
            if fileName:
                fileId = 'file.%f' % time.time()
                ploneFile = ploneFileClass(fileId, fileName, fileContent)
                ploneFile.filename = fileName
                if not mimeType:
                    mimeType = mimetypes.guess_type(fileName)[0]
                ploneFile.content_type = mimeType
                setattr(self, name, ploneFile)
    def __setattr__(self, name, v):
        appyType = self.o.getAppyType(name)
        if not appyType and (name != 'title'):
            raise 'Attribute "%s" does not exist.' % name
        if appyType and (appyType['type'] == 'File'):
            self._set_file_attribute(name, v)
        else:
            exec "self.o.set%s%s(v)" % (name[0].upper(), name[1:])
    def __repr__(self):
        return '<%s wrapper at %s>' % (self.klass.__name__, id(self))
    def __cmp__(self, other):
        if other: return cmp(self.o, other.o)
        else:     return 1
    def get_tool(self): return self.o.getTool().appy()
    tool = property(get_tool)
    def get_flavour(self): return self.o.getTool().getFlavour(self.o, appy=True)
    flavour = property(get_flavour)
    def get_request(self): return self.o.REQUEST
    request = property(get_request)
    def get_session(self): return self.o.REQUEST.SESSION
    session = property(get_session)
    def get_typeName(self): return self.__class__.__bases__[-1].__name__
    typeName = property(get_typeName)
    def get_id(self): return self.o.id
    id = property(get_id)
    def get_state(self):
        return self.o.portal_workflow.getInfoFor(self.o, 'review_state')
    state = property(get_state)
    def get_stateLabel(self):
        appName = self.o.getProductConfig().PROJECTNAME
        return self.o.utranslate(self.o.getWorkflowLabel(), domain=appName)
    stateLabel = property(get_stateLabel)
    def get_klass(self): return self.__class__.__bases__[1]
    klass = property(get_klass)
    def get_url(self): return self.o.absolute_url()+'/skyn/view'
    url = property(get_url)

    def link(self, fieldName, obj):
        '''This method links p_obj to this one through reference field
           p_fieldName.'''
        if isinstance(obj, AbstractWrapper):
            obj = obj.o
        postfix = 'et%s%s' % (fieldName[0].upper(), fieldName[1:])
        # Update the Archetypes reference field
        exec 'objs = self.o.g%s()' % postfix
        if not objs:
            objs = []
        elif type(objs) not in (list, tuple):
            objs = [objs]
        objs.append(obj)
        exec 'self.o.s%s(objs)' % postfix
        # Update the ordered list of references
        sortedRefField = '_appy_%s' % fieldName
        if not hasattr(self.o.aq_base, sortedRefField):
            exec 'self.o.%s = self.o.getProductConfig().PersistentList()' % \
                 sortedRefField
        getattr(self.o, sortedRefField).append(obj.UID())

    def sort(self, fieldName):
        '''Sorts referred elements linked to p_self via p_fieldName. At
           present, it can only sort elements based on their title.'''
        sortedUids = getattr(self.o, '_appy_%s' % fieldName)
        c = self.o.uid_catalog
        sortedUids.sort(lambda x,y: \
           cmp(c(UID=x)[0].getObject().Title(),c(UID=y)[0].getObject().Title()))

    def create(self, fieldNameOrClass, **kwargs):
        '''If p_fieldNameOfClass is the name of a field, this method allows to
           create an object and link it to the current one (self) through
           reference field named p_fieldName.
           If p_fieldNameOrClass is a class from the gen-application, it must
           correspond to a root class and this method allows to create a
           root object in the application folder.'''
        isField = isinstance(fieldNameOrClass, basestring)
        # Determine the portal type of the object to create
        if isField:
            fieldName = fieldNameOrClass
            idPrefix = fieldName
            portalType = self.o.getAppyRefPortalType(fieldName)
        else:
            theClass = fieldNameOrClass
            idPrefix = theClass.__name__
            portalType = self.o._appy_getAtType(theClass, self.flavour.o)
        # Determine object id
        if kwargs.has_key('id'):
            objId = kwargs['id']
            del kwargs['id']
        else:
            objId = '%s.%f' % (idPrefix, time.time())
        # Determine if object must be created from external data
        externalData = None
        if kwargs.has_key('_data'):
            externalData = kwargs['_data']
            del kwargs['_data']
        # Where must I create the object?
        if not isField:
            folder = self.o.getTool().getAppFolder()
        else:
            if hasattr(self, 'folder') and self.folder:
                folder = self.o
            else:
                folder = self.o.getParentNode()
        # Create the object
        folder.invokeFactory(portalType, objId)
        ploneObj = getattr(folder, objId)
        appyObj = ploneObj._appy_getWrapper(force=True)
        # Set object attributes
        ploneObj._appy_manageSortedRefs()
        for attrName, attrValue in kwargs.iteritems():
            setterName = 'set%s%s' % (attrName[0].upper(), attrName[1:])
            if isinstance(attrValue, AbstractWrapper):
                try:
                    refAppyType = getattr(appyObj.__class__.__bases__[-1],
                                          attrName)
                    appyObj.link(attrName, attrValue.o)
                except AttributeError, ae:
                    pass
            else:
                getattr(ploneObj, setterName)(attrValue)
        if isField:
            # Link the object to this one
            self.link(fieldName, ploneObj)
            self.o.reindexObject()
        # Call custom initialization
        try:
            if externalData: param = externalData
            else: param = True
            appyObj.onEdit(param)
        except AttributeError:
            pass
        ploneObj.reindexObject()
        return appyObj

    def translate(self, label, mapping={}, domain=None):
        '''Check documentation of self.o.translate.'''
        return self.o.translate(label, mapping, domain)

    def do(self, transition, comment='', doAction=False, doNotify=False):
        '''This method allows to trigger on p_self a workflow p_transition
           programmatically. If p_doAction is False, the action that must
           normally be executed after the transition has been triggered will
           not be executed. If p_doNotify is False, the notifications
           (email,...) that must normally be launched after the transition has
           been triggered will not be launched.'''
        wfTool = self.o.portal_workflow
        availableTransitions = [t['id'] for t in \
                                wfTool.getTransitionsFor(self.o)]
        transitionName = transition
        if not transitionName in availableTransitions:
            # Maybe is is a compound Appy transition. Try to find the
            # corresponding DC transition.
            state = self.state
            transitionPrefix = transition + state[0].upper() + state[1:] + 'To'
            for at in availableTransitions:
                if at.startswith(transitionPrefix):
                    transitionName = at
                    break
        # Set in a versatile attribute details about what to execute or not
        # (actions, notifications) after the transition has been executed by DC
        # workflow.
        self.o._v_appy_do = {'doAction': doAction, 'doNotify': doNotify}
        wfTool.doActionFor(self.o, transitionName, comment=comment)
        del self.o._v_appy_do

    def log(self, message, logLevel='info'):
        '''Logs a message in the log file. p_logLevel may be "info", "warning"
           or "error".'''
        logger = self.o.getProductConfig().logger
        if logLevel == 'warning': logMethod = logger.warn
        elif logLevel == 'error': logMethod = logger.error
        else: logMethod = logger.info
        logMethod(message)

    def normalize(self, s):
        '''Returns a version of string p_s whose special chars have been
           replaced with normal chars.'''
        return unicodedata.normalize('NFKD', s).encode("ascii","ignore")

    def search(self, klass, sortBy='', **fields):
        '''Searches objects of p_klass. p_sortBy must be the name of an indexed
           field (declared with indexed=True); every param in p_fields must
           take the name of an indexed field and take a possible value of this
           field.'''
        # Find the content type corresponding to p_klass
        flavour = self.flavour
        contentType = flavour.o.getPortalType(klass)
        # Create the Search object
        search = Search('customSearch', sortBy=sortBy, **fields)
        res = self.tool.o.executeQuery(contentType,flavour.number,search=search)
        return [o.appy() for o in res['objects']]

    def reindex(self):
        '''Asks a direct object reindexing. In most cases you don't have to
           reindex objects "manually" with this method. When an object is
           modified after some user action has been performed, Appy reindexes
           this object automatically. But if your code modifies other objects,
           Appy may not know that they must be reindexed, too. So use this
           method in those cases.'''
        self.o.reindexObject()

    def export(self, at='string'):
        '''Creates an "exportable", XML version of this object. If p_at is
           "string", this method returns the XML version. Else, (a) if not p_at,
           the XML will be exported on disk, in the OS temp folder, with an
           ugly name; (b) else, it will be exported at path p_at.'''
        # Determine where to put the result
        toDisk = (at != 'string')
        if toDisk and not at:
            at = getOsTempFolder() + '/' + self.o.UID() + '.xml'
        # Create the XML version of the object
        xml = XmlMarshaller().marshall(self.o, objectType='archetype')
        # Produce the desired result
        if toDisk:
            f = file(at, 'w')
            f.write(xml)
            f.close()
            return at
        else:
            return xml

# ------------------------------------------------------------------------------
class FileWrapper:
    '''When you get, from an appy object, the value of a File attribute, you
       get an instance of this class.'''
    def __init__(self, atFile):
        '''This constructor is only used by Appy to create a nice File instance
           from a Plone/Zope corresponding instance (p_atFile). If you need to
           create a new file and assign it to a File attribute, use the
           attribute setter, do not create yourself an instance of this
           class.'''
        d = self.__dict__
        d['_atFile'] = atFile # Not for you!
        d['name'] = atFile.filename
        d['content'] = atFile.data
        d['mimeType'] = atFile.content_type
        d['size'] = atFile.size # In bytes

    def __setattr__(self, name, v):
        d = self.__dict__
        if name == 'name':
            self._atFile.filename = v
            d['name'] = v
        elif name == 'content':
            self._atFile.update_data(v, self.mimeType, len(v))
            d['content'] = v
            d['size'] = len(v)
        elif name == 'mimeType':
            self._atFile.content_type = self.mimeType = v
        else:
            raise 'Impossible to set attribute %s. "Settable" attributes ' \
                  'are "name", "content" and "mimeType".' % name

    def dump(self, filePath=None):
        '''Writes the file on disk. If p_filePath is specified, it is the
           path name where the file will be dumped; folders mentioned in it
           must exist. If not, the file will be dumped in the OS temp folder.
           The absolute path name of the dumped file is returned.'''
        if not filePath:
            filePath = '%s/file%f.%s' % (getOsTempFolder(), time.time(),
                self.name)
        f = file(filePath, 'w')
        if self.content.__class__.__name__ == 'Pdata':
            # The file content is splitted in several chunks.
            f.write(self.content.data)
            nextPart = self.content.next
            while nextPart:
                f.write(nextPart.data)
                nextPart = nextPart.next
        else:
            # Only one chunk
            f.write(self.content)
        f.close()
        return filePath
# ------------------------------------------------------------------------------
