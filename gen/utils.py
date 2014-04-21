# ------------------------------------------------------------------------------
import re, os, os.path, base64, urllib
from appy.shared import utils as sutils

# Function for creating a Zope object ------------------------------------------
def createObject(folder, id, className, appName, wf=True, noSecurity=False):
    '''Creates, in p_folder, object with some p_id. Object will be an instance
       of p_className from application p_appName. In a very special case (the
       creation of the config object), computing workflow-related info is not
       possible at this time. This is why this function can be called with
       p_wf=False.'''
    exec 'from Products.%s.%s import %s as ZopeClass' % \
         (appName, className, className)
    # Get the tool. It may not be present yet, maybe are we creating it now.
    if folder.meta_type.endswith('Folder'):
        # p_folder is a standard Zope (temp) folder.
        tool = getattr(folder, 'config', None)
    else:
        # p_folder is an instance of a gen-class.
        tool = folder.getTool()
    # Get the currently logged user
    user = None
    if tool:
        user = tool.getUser()
    # Checks whether the user an create this object if security is enabled.
    if not noSecurity:
        klass = ZopeClass.wrapperClass.__bases__[-1]
        if not tool.userMayCreate(klass):
            from AccessControl import Unauthorized
            raise Unauthorized("User can't create instances of %s" % \
                               klass.__name__)
    # Create the object
    obj = ZopeClass(id)
    folder._objects = folder._objects + ({'id':id, 'meta_type':className},)
    folder._setOb(id, obj)
    obj = folder._getOb(id) # Important. Else, obj is not really in the folder.
    obj.portal_type = className
    obj.id = id
    obj._at_uid = id
    # If no user object is there, we are at startup, before default User
    # instances are created.
    userId = user and user.login or 'system'
    obj.creator = userId
    from DateTime import DateTime
    obj.created = DateTime()
    obj.modified = obj.created
    from persistent.mapping import PersistentMapping
    obj.__ac_local_roles__ = PersistentMapping({ userId: ['Owner'] })
    if wf: obj.initializeWorkflow()
    return obj

# ------------------------------------------------------------------------------
upperLetter = re.compile('[A-Z]')
def produceNiceMessage(msg):
    '''Transforms p_msg into a nice msg.'''
    res = ''
    if msg:
        res = msg[0].upper()
        for c in msg[1:]:
            if c == '_':
                res += ' '
            elif upperLetter.match(c):
                res += ' ' + c.lower()
            else:
                res += c
    return res

# ------------------------------------------------------------------------------
class SomeObjects:
    '''Represents a bunch of objects retrieved from a reference or a query in
       the catalog.'''
    def __init__(self, objects=None, batchSize=None, startNumber=0,
                 noSecurity=False):
        self.objects = objects or [] # The objects
        self.totalNumber = len(self.objects) # self.objects may only represent a
        # part of all available objects.
        self.batchSize = batchSize or self.totalNumber # The max length of
        # self.objects.
        self.startNumber = startNumber # The index of first object in
        # self.objects in the whole list.
        self.noSecurity = noSecurity
    def brainsToObjects(self):
        '''self.objects has been populated from brains from the catalog,
           not from True objects. This method turns them (or some of them
           depending on batchSize and startNumber) into real objects.
           If self.noSecurity is True, it gets the objects even if the logged
           user does not have the right to get them.'''
        start = self.startNumber
        brains = self.objects[start:start + self.batchSize]
        if self.noSecurity: getMethod = '_unrestrictedGetObject'
        else:               getMethod = 'getObject'
        self.objects = [getattr(b, getMethod)() for b in brains]

# ------------------------------------------------------------------------------
class Keywords:
    '''This class allows to handle keywords that a user enters and that will be
       used as basis for performing requests in a TextIndex/XhtmlIndex.'''

    toRemove = '?-+*()'
    def __init__(self, keywords, operator='AND'):
        # Clean the p_keywords that the user has entered.
        words = sutils.normalizeText(keywords)
        if words == '*': words = ''
        for c in self.toRemove: words = words.replace(c, ' ')
        self.keywords = words.split()
        # Store the operator to apply to the keywords (AND or OR)
        self.operator = operator

    def merge(self, other, append=False):
        '''Merges our keywords with those from p_other. If p_append is True,
           p_other keywords are appended at the end; else, keywords are appended
           at the begin.'''
        for word in other.keywords:
            if word not in self.keywords:
                if append:
                    self.keywords.append(word)
                else:
                    self.keywords.insert(0, word)

    def get(self):
        '''Returns the keywords as needed by the TextIndex.'''
        if self.keywords:
            op = ' %s ' % self.operator
            return op.join(self.keywords)+'*'
        return ''

# ------------------------------------------------------------------------------
def getClassName(klass, appName=None):
    '''Generates, from appy-class p_klass, the name of the corresponding
       Zope class. For some classes, name p_appName is required: it is
       part of the class name.'''
    moduleName = klass.__module__
    if (moduleName == 'appy.gen.model') or moduleName.endswith('.wrappers'):
        # This is a model (generation time or run time)
        res = appName + klass.__name__
    elif klass.__bases__ and (klass.__bases__[-1].__module__ == 'appy.gen'):
        # This is a customized class (inherits from appy.gen.Tool, User,...)
        res = appName + klass.__bases__[-1].__name__
    else: # This is a standard class
        res = klass.__module__.replace('.', '_') + '_' + klass.__name__
    return res

# ------------------------------------------------------------------------------
def callMethod(obj, method, klass=None, cache=True):
    '''This function is used to call a p_method on some Appy p_obj. m_method
       can be an instance method on p_obj; it can also be a static method. In
       this latter case, p_obj is the tool and the static method, defined in
       p_klass, will be called with the tool as unique arg.

       A method cache is implemented on the request object (available at
       p_obj.request). So while handling a single request from the ui, every
       method is called only once. Some method calls must not be cached (ie,
       values of Computed fields). In this case, p_cache will be False.'''
    rq = obj.request
    # Create the method cache if it does not exist on the request
    if not hasattr(rq, 'methodCache'): rq.methodCache = {}
    # If m_method is a static method or an instance method, unwrap the true
    # Python function object behind it.
    methodType = method.__class__.__name__
    if methodType == 'staticmethod':
        method = method.__get__(klass)
    elif methodType == 'instancemethod':
        method = method.im_func
    # Call the method if cache is not needed.
    if not cache: return method(obj)
    # If first arg of method is named "tool" instead of the traditional "self",
    # we cheat and will call the method with the tool as first arg. This will
    # allow to consider this method as if it was a static method on the tool.
    # Every method call, even on different instances, will be cached in a unique
    # key.
    cheat = False
    if not klass and (method.func_code.co_varnames[0] == 'tool'):
        prefix = obj.klass.__name__
        obj = obj.tool
        cheat = True
    # Build the key of this method call in the cache.
    # First part of the key: the p_obj's uid (if p_method is an instance method)
    # or p_className (if p_method is a static method).
    if not cheat:
        if klass:
            prefix = klass.__name__
        else:
            prefix = obj.uid
    # Second part of the key: p_method name
    key = '%s:%s' % (prefix, method.func_name)
    # Return the cached value if present in the method cache.
    if key in rq.methodCache:
        return rq.methodCache[key]
    # No cached value: call the method, cache the result and return it
    res = method(obj)
    rq.methodCache[key] = res
    return res


# Functions for manipulating the authentication cookie -------------------------
def readCookie(request):
    '''Returns the tuple (login, password) read from the authentication
       cookie received in p_request. If no user is logged, its returns
       (None, None).'''
    cookie = request.get('_appy_', None)
    if not cookie: return None, None
    cookieValue = base64.decodestring(urllib.unquote(cookie))
    if ':' in cookieValue: return cookieValue.split(':')
    return None, None

def writeCookie(login, password, request):
    '''Encode p_login and p_password into the cookie set in the p_request.'''
    cookieValue = base64.encodestring('%s:%s' % (login, password)).rstrip()
    cookieValue = urllib.quote(cookieValue)
    request.RESPONSE.setCookie('_appy_', cookieValue, path='/')

# ------------------------------------------------------------------------------
def initMasterValue(v):
    '''Standardizes p_v as a list of strings, excepted if p_v is a method.'''
    if callable(v): return v
    if not isinstance(v, bool) and not v: res = []
    elif type(v) not in sutils.sequenceTypes: res = [v]
    else: res = v
    return [str(v) for v in res]

# ------------------------------------------------------------------------------
class No:
    '''When you write a workflow condition method and you want to return False
       but you want to give to the user some explanations about why a transition
       can't be triggered, do not return False, return an instance of No
       instead. When creating such an instance, you can specify an error
       message.'''
    def __init__(self, msg):
        self.msg = msg
    def __nonzero__(self):
        return False
# ------------------------------------------------------------------------------
