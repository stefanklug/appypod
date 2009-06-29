# ------------------------------------------------------------------------------
import re

sequenceTypes = (list, tuple)

# Classes used by edit/view templates for accessing information ----------------
class Descr:
    '''Abstract class for description classes.'''
    def get(self): return self.__dict__

class FieldDescr(Descr):
    def __init__(self, atField, appyType, fieldRel):
        self.atField = atField # The corresponding Archetypes field (may be None
        # in the case of backward references)
        self.appyType = appyType # The corresponding Appy type
        self.fieldRel = fieldRel # The field relatonship, needed when the field
        # description is a backward reference.
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
