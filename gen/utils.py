# ------------------------------------------------------------------------------
import re

sequenceTypes = (list, tuple)

# Classes used by edit/view templates for accessing information ----------------
class Descr:
    '''Abstract class for description classes.'''
    def get(self): return self.__dict__

class FieldDescr(Descr):
    def __init__(self, atField, appyType, fieldRel):
        # The corresponding Archetypes field (may be None in the case of
        # backward references)
        self.atField = atField
        # The corresponding Appy type
        self.appyType = appyType
        # The field relationship, needed when the field description is a
        # backward reference.
        self.fieldRel = fieldRel
        # Can we sort this field ?
        at = self.appyType
        self.sortable = False
        if not fieldRel and ((self.atField.getName() == 'title') or \
                             (at['indexed'])):
            self.sortable = True
        # Can we filter this field?
        self.filterable = False
        if not fieldRel and at['indexed'] and (at['type'] == 'String') and \
           (at['format'] == 0) and not at['isSelect']:
            self.filterable = True
        if fieldRel:
            self.widgetType = 'backField'
            self.group = appyType['backd']['group']
            self.show = appyType['backd']['show']
            self.page = appyType['backd']['page']
        else:
            self.widgetType = 'field'
            self.group = appyType['group']
            self.show = appyType['show']
            self.page = appyType['page']
            fieldName = self.atField.getName()

class GroupDescr(Descr):
    def __init__(self, name, cols, page):
        self.name = name
        self.cols = cols # The nb of columns for placing fields into the group
        self.rows = None # The number of rows
        self.page = page
        self.fields = []
        self.widgetType = 'group'

    def computeRows(groupDict):
        '''Computes self.rows. But because at this time the object has already
           been converted to a dict (for being maniputated within ZPTs, this
           method is a static method that takes the dict as arg.'''
        groupDict['rows'] = len(groupDict['fields']) / groupDict['cols']
        if len(groupDict['fields']) % groupDict['cols']:
            groupDict['rows'] += 1
    computeRows = staticmethod(computeRows)

    def getGroupInfo(groupName):
        '''In the group name, the user may optionally specify at the end the
           number of columns for placing fields into the group. This method
           returns the real group name and the number of columns.'''
        res = groupName.rsplit('_', 1)
        if len(res) == 1:
            res.append(1) # Append the default numer of columns
        else:
            try:
                res[1] = int(res[1])
            except ValueError:
                res[1] = 1
        return res
    getGroupInfo = staticmethod(getGroupInfo)

class PageDescr(Descr):
    def getPageInfo(pageOrName, pageKlass):
        '''pageOrName can be:
           - a string containing the name of the page
           - a string containing <pageName>_<phaseName>
           - a appy.gen.Page instance for a more detailed page description.
           This method returns a normalized tuple containing page-related
           information.'''
        if isinstance(pageOrName, pageKlass):
            res = [pageOrName.name, pageOrName.phase, pageOrName.show]
        else:
            res = pageOrName.rsplit('_', 1)
            if len(res) == 1:
                res.append('main')
            res.append(True)
        return res
    getPageInfo = staticmethod(getPageInfo)

class PhaseDescr(Descr):
    def __init__(self, name, states, forPlone, ploneObj):
        self.name = name
        self.states = states
        self.forPlone = forPlone
        self.ploneObj = ploneObj
        self.phaseStatus = None
        self.pages = [] # The list of pages in this phase
        self.totalNbOfPhases = None
    def addPage(self, appyType, obj):
        toAdd = appyType['page']
        if (toAdd == 'main') and self.forPlone:
            toAdd = 'default'
        if (toAdd not in self.pages) and \
           obj._appy_showPage(appyType['page'], appyType['pageShow']):
            self.pages.append(toAdd)
    def computeStatus(self):
        '''Compute status of whole phase based on individual status of states
           in this phase. If this phase includes no state, the concept of phase
           is simply used as a tab, and its status depends on the page currently
           shown.'''
        res = 'Current'
        if self.states:
            # Compute status base on states
            res = self.states[0]['stateStatus']
            if len(self.states) > 1:
                for state in self.states[1:]:
                    if res != state['stateStatus']:
                        res = 'Current'
                        break
        else:
            # Compute status based on current page
            rq = self.ploneObj.REQUEST
            if rq.has_key('fieldset'):
                pageName = rq['fieldset']
                if not self.forPlone and (pageName == 'default'):
                    pageName = 'main'
            else:
                pageName = rq.get('pageName', 'main')
            if pageName in self.pages:
                res = 'Current'
            else:
                res = 'Deselected'
        self.phaseStatus = res

class StateDescr(Descr):
    def __init__(self, name, stateStatus):
        self.name = name
        self.stateStatus = stateStatus.capitalize()

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
class ValidationErrors: pass
class AppyRequest:
    def __init__(self, zopeRequest, appyObj=None):
        self.zopeRequest = zopeRequest
        self.appyObj = appyObj
    def __str__(self): return '<AppyRequest object>'
    def __repr__(self): return '<AppyRequest object>'
    def __getattr__(self, attr):
        res = None
        if self.appyObj:
            # I can retrieve type information from the ploneObj.
            appyType = self.appyObj.o.getAppyType(attr)
            if appyType['type'] == 'Ref':
                res = self.zopeRequest.get('appy_ref_%s' % attr, None)
            else:
                res = self.zopeRequest.get(attr, None)
                if appyType['pythonType']:
                    try:
                        exec 'res = %s' % res # bool('False') gives True, so we
                        # can't write: res = appyType['pythonType'](res)
                    except SyntaxError, se:
                        # Can happen when for example, an Integer value is empty
                        res = None
        else:
            res = self.zopeRequest.get(attr, None)
        return res

# ------------------------------------------------------------------------------
class SomeObjects:
    '''Represents a bunch of objects retrieved from a reference or a query in
       portal_catalog.'''
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
        '''self.objects has been populated from brains from the portal_catalog,
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
       used as basis for performing requests in a Zope ZCTextIndex.'''

    toRemove = '?-+*()'
    def __init__(self, keywords, operator='AND'):
        # Clean the p_keywords that the user has entered.
        words = keywords.strip()
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
        '''Returns the keywords as needed by the ZCTextIndex.'''
        if self.keywords:
            op = ' %s ' % self.operator
            return op.join(self.keywords)+'*'
        return ''

# ------------------------------------------------------------------------------
class FakeBrain:
    '''This class behaves like a brain retrieved from a query to a ZCatalog. It
       is used for representing a fake brain that was generated from a search in
       a distant portal_catalog.'''
    Creator = None
    created = None
    modified = None
    review_state = None
    def has_key(self, key): return hasattr(self, key)
    def getPath(self): return self.path
    def getURL(self, relative=0): return self.url
    def _unrestrictedGetObject(self): return self
    def pretty_title_or_id(self): return self.Title
    def getObject(self, REQUEST=None): return self
    def getRID(self): return self.url
# ------------------------------------------------------------------------------
