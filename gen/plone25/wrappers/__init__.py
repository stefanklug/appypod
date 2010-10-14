'''This package contains base classes for wrappers that hide to the Appy
   developer the real classes used by the underlying web framework.'''

# ------------------------------------------------------------------------------
import os, os.path, time, mimetypes, random
import appy.pod
from appy.gen import Search
from appy.gen.utils import sequenceTypes, FileWrapper
from appy.shared.utils import getOsTempFolder, executeCommand, normalizeString
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
            setattr(self.o, name, v)
        elif isinstance(v, FileWrapper):
            setattr(self.o, name, v._atFile)
        elif isinstance(v, basestring):
            f = file(v)
            fileName = os.path.basename(v)
            fileId = 'file.%f' % time.time()
            ploneFile = ploneFileClass(fileId, fileName, f)
            ploneFile.filename = fileName
            ploneFile.content_type = mimetypes.guess_type(fileName)[0]
            setattr(self.o, name, ploneFile)
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
                setattr(self.o, name, ploneFile)
    def __setattr__(self, name, v):
        if name == 'title':
            self.o.setTitle(v)
            return
        appyType = self.o.getAppyType(name)
        if not appyType:
            raise 'Attribute "%s" does not exist.' % name
        if appyType.type == 'File':
            self._set_file_attribute(name, v)
        elif appyType.type == 'Ref':
            raise "Use methods 'link' or 'create' to modify references."
        else:
            setattr(self.o, name, v)
    def __repr__(self):
        return '<%s wrapper at %s>' % (self.klass.__name__, id(self))
    def __cmp__(self, other):
        if other: return cmp(self.o, other.o)
        else:     return 1
    def get_tool(self): return self.o.getTool().appy()
    tool = property(get_tool)
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
    def get_klass(self): return self.__class__.__bases__[-1]
    klass = property(get_klass)
    def get_url(self): return self.o.absolute_url()
    url = property(get_url)
    def get_history(self):
        key = self.o.workflow_history.keys()[0]
        return self.o.workflow_history[key]
    history = property(get_history)
    def get_user(self): return self.o.portal_membership.getAuthenticatedMember()
    user = property(get_user)
    def get_fields(self): return self.o.getAllAppyTypes()
    fields = property(get_fields)

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
        self.o._appy_getSortedField(fieldName).append(obj.UID())

    def sort(self, fieldName, sortKey='title', reverse=False):
        '''Sorts referred elements linked to p_self via p_fieldName according
           to a given p_sortKey which must be an attribute set on referred
           objects ("title", by default).'''
        sortedUids = getattr(self.o, '_appy_%s' % fieldName)
        c = self.o.uid_catalog
        sortedUids.sort(lambda x,y: \
           cmp(getattr(c(UID=x)[0].getObject().appy(), sortKey),
               getattr(c(UID=y)[0].getObject().appy(), sortKey)))
        if reverse:
            sortedUids.reverse()

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
            fieldName = idPrefix = fieldNameOrClass
            appyType = self.o.getAppyType(fieldName)
            portalType = self.tool.o.getPortalType(appyType.klass)
        else:
            klass = fieldNameOrClass
            idPrefix = klass.__name__
            portalType = self.tool.o.getPortalType(klass)
        # Determine object id
        if kwargs.has_key('id'):
            objId = kwargs['id']
            del kwargs['id']
        else:
            objId = '%s.%f.%s' % (idPrefix, time.time(),
                                  str(random.random()).split('.')[1])
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
        appyObj = ploneObj.appy()
        # Set object attributes
        for attrName, attrValue in kwargs.iteritems():
            if isinstance(attrValue, AbstractWrapper):
                try:
                    refAppyType = getattr(appyObj.__class__.__bases__[-1],
                                          attrName)
                    appyObj.link(attrName, attrValue.o)
                except AttributeError, ae:
                    pass
            else:
                setattr(appyObj, attrName, attrValue)
        if isField:
            # Link the object to this one
            self.link(fieldName, ploneObj)
            self.o.reindexObject()
        # Call custom initialization
        if externalData: param = externalData
        else: param = True
        if hasattr(appyObj, 'onEdit'): appyObj.onEdit(param)
        ploneObj.reindexObject()
        return appyObj

    def translate(self, label, mapping={}, domain=None, language=None):
        '''Check documentation of self.o.translate.'''
        return self.o.translate(label, mapping, domain, language=language)

    def do(self, transition, comment='', doAction=False, doNotify=False,
           doHistory=True):
        '''This method allows to trigger on p_self a workflow p_transition
           programmatically. If p_doAction is False, the action that must
           normally be executed after the transition has been triggered will
           not be executed. If p_doNotify is False, the notifications
           (email,...) that must normally be launched after the transition has
           been triggered will not be launched. If p_doHistory is False, there
           will be no trace from this transition triggering in the workflow
           history.'''
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
        if not doHistory:
            comment = '_invisible_' # Will not be displayed.
            # At first sight, I wanted to remove the entry from
            # self.o.workflow_history. But Plone determines the state of an
            # object by consulting the target state of the last transition in
            # this workflow_history.
        wfTool.doActionFor(self.o, transitionName, comment=comment)
        del self.o._v_appy_do

    def log(self, message, type='info'):
        '''Logs a message in the log file. p_logLevel may be "info", "warning"
           or "error".'''
        logger = self.o.getProductConfig().logger
        if type == 'warning': logMethod = logger.warn
        elif type == 'error': logMethod = logger.error
        else: logMethod = logger.info
        logMethod(message)

    def say(self, message, type='info'):
        '''Prints a message in the user interface. p_logLevel may be "info",
           "warning" or "error".'''
        mType = type
        if mType == 'warning': mType = 'warn'
        elif mType == 'error': mType = 'stop'
        self.o.plone_utils.addPortalMessage(message, type=mType)

    unwantedChars = ('\\', '/', ':', '*', '?', '"', '<', '>', '|', ' ')
    def normalize(self, s, usage='fileName'):
        '''Returns a version of string p_s whose special chars have been
           replaced with normal chars.'''
        return normalizeString(s, usage)

    def search(self, klass, sortBy='', maxResults=None, noSecurity=False,
               **fields):
        '''Searches objects of p_klass. p_sortBy must be the name of an indexed
           field (declared with indexed=True); every param in p_fields must
           take the name of an indexed field and take a possible value of this
           field. You can optionally specify a maximum number of results in
           p_maxResults. If p_noSecurity is specified, you get all objects,
           even if the logged user does not have the permission to view it.'''
        # Find the content type corresponding to p_klass
        contentType = self.tool.o.getPortalType(klass)
        # Create the Search object
        search = Search('customSearch', sortBy=sortBy, **fields)
        if not maxResults:
            maxResults = 'NO_LIMIT'
            # If I let maxResults=None, only a subset of the results will be
            # returned by method executeResult.
        res = self.tool.o.executeQuery(contentType, search=search,
                                   maxResults=maxResults, noSecurity=noSecurity)
        return [o.appy() for o in res['objects']]

    def count(self, klass, noSecurity=False, **fields):
        '''Identical to m_search above, but returns the number of objects that
           match the search instead of returning the objects themselves. Use
           this method instead of writing len(self.search(...)).'''
        contentType = self.tool.o.getPortalType(klass)
        search = Search('customSearch', **fields)
        res = self.tool.o.executeQuery(contentType, search=search,
                                       brainsOnly=True, noSecurity=noSecurity)
        if res: return res._len # It is a LazyMap instance
        else: return 0

    def compute(self, klass, sortBy='', maxResults=None, context=None,
                expression=None, noSecurity=False, **fields):
        '''This method, like m_search and m_count above, performs a query on
           objects of p_klass. But in this case, instead of returning a list of
           matching objects (like m_search) or counting elements (like p_count),
           it evaluates, on every matching object, a Python p_expression (which
           may be an expression or a statement), and returns, if needed, a
           result. The result may be initialized through parameter p_context.
           p_expression is evaluated with 2 variables in its context: "obj"
           which is the currently walked object, instance of p_klass, and "ctx",
           which is the context as initialized (or not) by p_context. p_context
           may be used as
              (1) a variable or instance that is updated on every call to
                  produce a result;
              (2) an input variable or instance;
              (3) both.

           The method returns p_context, modified or not by evaluation of
           p_expression on every matching object.

           When you need to perform an action or computation on a lot of
           objects, use this method instead of doing things like
           
                    "for obj in self.search(MyClass,...)"
           '''
        contentType = self.tool.o.getPortalType(klass)
        search = Search('customSearch', sortBy=sortBy, **fields)
        # Initialize the context variable "ctx"
        ctx = context
        for brain in self.tool.o.executeQuery(contentType, search=search, \
                 brainsOnly=True, maxResults=maxResults, noSecurity=noSecurity):
            # Get the Appy object from the brain
            obj = brain.getObject().appy()
            exec expression
        return ctx

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
           "string", this method returns the XML version, without the XML
           prologue. Else, (a) if not p_at, the XML will be exported on disk,
           in the OS temp folder, with an ugly name; (b) else, it will be
           exported at path p_at.'''
        # Determine where to put the result
        toDisk = (at != 'string')
        if toDisk and not at:
            at = getOsTempFolder() + '/' + self.o.UID() + '.xml'
        # Create the XML version of the object
        marshaller = XmlMarshaller(cdata=True, dumpUnicode=True,
                                   dumpXmlPrologue=toDisk,
                                   rootTag=self.klass.__name__)
        xml = marshaller.marshall(self.o, objectType='appy')
        # Produce the desired result
        if toDisk:
            f = file(at, 'w')
            f.write(xml.encode('utf-8'))
            f.close()
            return at
        else:
            return xml

    def historize(self, data):
        '''This method allows to add "manually" a "data-change" event into the
           object's history. Indeed, data changes are "automatically" recorded
           only when an object is edited through the edit form, not when a
           setter is called from the code.

           p_data must be a dictionary whose keys are field names (strings) and
           whose values are the previous field values.'''
        self.o.addDataChange(data)
# ------------------------------------------------------------------------------
