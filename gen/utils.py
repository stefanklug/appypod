# ------------------------------------------------------------------------------
import re, os, os.path, time
import appy.pod
from appy.shared.utils import getOsTempFolder, normalizeString, executeCommand
sequenceTypes = (list, tuple)

# Classes used by edit/view templates for accessing information ----------------
class Descr:
    '''Abstract class for description classes.'''
    def get(self): return self.__dict__

class GroupDescr(Descr):
    def __init__(self, group, page, metaType):
        '''Creates the data structure manipulated in ZPTs from p_group, the
           Group instance used in the field definition.'''
        self.type = 'group'
        # All p_group attributes become self attributes.
        for name, value in group.__dict__.iteritems():
            if not name.startswith('_'):
                setattr(self, name, value)
        self.columnsWidths = [col.width for col in group.columns]
        self.columnsAligns = [col.align for col in group.columns]
        # Names of i18n labels
        self.labelId = '%s_group_%s' % (metaType, self.name)
        self.descrId = self.labelId + '_descr'
        self.helpId  = self.labelId + '_help'
        # The name of the page where the group lies
        self.page = page.name
        # The widgets belonging to the group that the current user may see.
        # They will be stored by m_addWidget below as a list of lists because
        # they will be rendered as a table.
        self.widgets = [[]]

    @staticmethod
    def addWidget(groupDict, newWidget):
        '''Adds p_newWidget into p_groupDict['widgets']. We try first to add
           p_newWidget into the last widget row. If it is not possible, we
           create a new row.

           This method is a static method taking p_groupDict as first param
           instead of being an instance method because at this time the object
           has already been converted to a dict (for being maniputated within
           ZPTs).'''
        # Get the last row
        widgetRow = groupDict['widgets'][-1]
        numberOfColumns = len(groupDict['columnsWidths'])
        # Computes the number of columns already filled by widgetRow
        rowColumns = 0
        for widget in widgetRow: rowColumns += widget['colspan']
        freeColumns = numberOfColumns - rowColumns
        if freeColumns >= newWidget['colspan']:
            # We can add the widget in the last row.
            widgetRow.append(newWidget)
        else:
            if freeColumns:
                # Terminate the current row by appending empty cells
                for i in range(freeColumns): widgetRow.append('')
            # Create a new row
            newRow = [newWidget]
            groupDict['widgets'].append(newRow)

class PhaseDescr(Descr):
    def __init__(self, name, states, obj):
        self.name = name
        self.states = states
        self.obj = obj
        self.phaseStatus = None
        # The list of names of pages in this phase
        self.pages = []
        # The list of hidden pages in this phase
        self.hiddenPages = []
        # The dict below stores infor about every page listed in self.pages.
        self.pagesInfo = {}
        self.totalNbOfPhases = None
        # The following attributes allows to browse, from a given page, to the
        # last page of the previous phase and to the first page of the following
        # phase if allowed by phase state.
        self.previousPhase = None
        self.nextPhase = None

    def addPage(self, appyType, obj, layoutType):
        '''Adds page-related information in the phase.'''
        # If the page is already there, we have nothing more to do.
        if (appyType.page.name in self.pages) or \
           (appyType.page.name in self.hiddenPages): return
        # Add the page only if it must be shown.
        isShowableOnView = appyType.page.isShowable(obj, 'view')
        isShowableOnEdit = appyType.page.isShowable(obj, 'edit')
        if isShowableOnView or isShowableOnEdit:
            # The page must be added.
            self.pages.append(appyType.page.name)
            # Create the dict about page information and add it in self.pageInfo
            pageInfo = {'page': appyType.page,
                        'showOnView': isShowableOnView,
                        'showOnEdit': isShowableOnEdit}
            pageInfo.update(appyType.page.getInfo(obj, layoutType))
            self.pagesInfo[appyType.page.name] = pageInfo
        else:
            self.hiddenPages.append(appyType.page.name)

    def computeStatus(self, allPhases):
        '''Compute status of whole phase based on individual status of states
           in this phase. If this phase includes no state, the concept of phase
           is simply used as a tab, and its status depends on the page currently
           shown. This method also fills fields "previousPhase" and "nextPhase"
           if relevant, based on list of p_allPhases.'''
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
            page = self.obj.REQUEST.get('page', 'main')
            if page in self.pages:
                res = 'Current'
            else:
                res = 'Deselected'
            # Identify previous and next phases
            for phaseInfo in allPhases:
                if phaseInfo['name'] == self.name:
                    i = allPhases.index(phaseInfo)
                    if i > 0:
                        self.previousPhase = allPhases[i-1]
                    if i < (len(allPhases)-1):
                        self.nextPhase = allPhases[i+1]
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
class AppyObject: pass

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
CONVERSION_ERROR = 'An error occurred while executing command "%s". %s'
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

    def dump(self, filePath=None, format=None, tool=None):
        '''Writes the file on disk. If p_filePath is specified, it is the
           path name where the file will be dumped; folders mentioned in it
           must exist. If not, the file will be dumped in the OS temp folder.
           The absolute path name of the dumped file is returned.
           If an error occurs, the method returns None. If p_format is
           specified, OpenOffice will be called for converting the dumped file
           to the desired format. In this case, p_tool, a Appy tool, must be
           provided. Indeed, any Appy tool contains parameters for contacting
           OpenOffice in server mode.'''
        if not filePath:
            filePath = '%s/file%f.%s' % (getOsTempFolder(), time.time(),
                normalizeString(self.name))
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
        if format:
            if not tool: return
            # Convert the dumped file using OpenOffice
            errorMessage = tool.convert(filePath, format)
            # Even if we have an "error" message, it could be a simple warning.
            # So we will continue here and, as a subsequent check for knowing if
            # an error occurred or not, we will test the existence of the
            # converted file (see below).
            os.remove(filePath)
            # Return the name of the converted file.
            baseName, ext = os.path.splitext(filePath)
            if (ext == '.%s' % format):
                filePath = '%s.res.%s' % (baseName, format)
            else:
                filePath = '%s.%s' % (baseName, format)
            if not os.path.exists(filePath):
                tool.log(CONVERSION_ERROR % (cmd, errorMessage), type='error')
                return
        return filePath

# ------------------------------------------------------------------------------
def getClassName(klass, appName=None):
    '''Generates, from appy-class p_klass, the name of the corresponding
       Archetypes class. For some classes, name p_appName is required: it is
       part of the class name.'''
    moduleName = klass.__module__
    if (moduleName == 'appy.gen.plone25.model') or \
       moduleName.endswith('.appyWrappers'):
        # This is a model (generation time or run time)
        res = appName + klass.__name__
    elif klass.__bases__ and (klass.__bases__[-1].__module__ == 'appy.gen'):
        # This is a customized class (inherits from appy.gen.Tool, User,...)
        res = appName + klass.__bases__[-1].__name__
    else: # This is a standard class
        res = klass.__module__.replace('.', '_') + '_' + klass.__name__
    return res
# ------------------------------------------------------------------------------
