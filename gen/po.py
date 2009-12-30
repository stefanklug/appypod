# ------------------------------------------------------------------------------
import os, re, time, copy
from utils import produceNiceMessage

# ------------------------------------------------------------------------------
poHeader = '''msgid ""
msgstr ""
"Project-Id-Version: %s\\n"
"POT-Creation-Date: %s\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=utf-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=1; plural=0\\n"
"Language-code: %s\\n"
"Language-name: %s\\n"
"Preferred-encodings: utf-8 latin1\\n"
"Domain: %s\\n"
%s

'''
fallbacks = {'en': 'en-us en-ca',
             'fr': 'fr-be fr-ca fr-lu fr-mc fr-ch fr-fr'
            }

# ------------------------------------------------------------------------------
class PoMessage:
    '''Represents a i18n message (po format).'''
    CONFIG = "Configuration panel for product '%s'"
    FLAVOUR = "Configuration flavour"
    # The following messages (starting with MSG_) correspond to flavour
    # attributes added for every gen-class (warning: the message IDs correspond
    # to MSG_<attributePrexix>).
    MSG_optionalFieldsFor = 'Optional fields'
    MSG_defaultValueFor = "Default value for field '%s'"
    MSG_podTemplatesFor = "POD templates"
    MSG_podMaxShownTemplatesFor = "Max shown POD templates"
    MSG_resultColumnsFor = "Columns to display while showing query results"
    MSG_showWorkflowFor = 'Show workflow-related information'
    MSG_showWorkflowCommentFieldFor = 'Show field allowing to enter a ' \
        'comment every time a transition is triggered'
    MSG_showAllStatesInPhaseFor = 'Show all states in phase'
    POD_TEMPLATE = 'POD template'
    DEFAULT_VALID_ERROR = 'Please fill or correct this.'
    REF_NO = 'No object.'
    REF_ADD = 'Add a new one'
    REF_NAME = 'Name'
    REF_ACTIONS = 'Actions'
    REF_MOVE_UP = 'Move up'
    REF_MOVE_DOWN = 'Move down'
    REF_INVALID_INDEX = 'No move occurred: please specify a valid number.'
    QUERY_CREATE = 'create'
    QUERY_IMPORT = 'import'
    QUERY_CONSULT_ALL = 'consult all'
    QUERY_NO_RESULT = 'Nothing to see for the moment.'
    IMPORT_TITLE = 'Importing data into your application'
    IMPORT_SHOW_HIDE = 'Show / hide alreadly imported elements.'
    IMPORT_ALREADY = 'Already imported.'
    IMPORT_MANY = 'Import selected elements'
    IMPORT_DONE = 'Import terminated successfully.'
    SEARCH_TITLE = 'Advanced search'
    SEARCH_BUTTON = 'Search'
    SEARCH_OBJECTS = 'Search objects of this type.'
    SEARCH_RESULTS = 'Search results'
    WORKFLOW_COMMENT = 'Optional comment'
    WORKFLOW_STATE = 'state'
    DATA_CHANGE = 'Data change'
    MODIFIED_FIELD = 'Modified field'
    PREVIOUS_VALUE = 'Previous value'
    PHASE = 'phase'
    ROOT_TYPE = 'type'
    CHOOSE_A_VALUE = ' - '
    CHOOSE_A_DOC = '[ Documents ]'
    MIN_REF_VIOLATED = 'You must choose more elements here.'
    MAX_REF_VIOLATED = 'Too much elements are selected here.'
    BAD_INT = 'An integer value is expected; do not enter any space.'
    BAD_FLOAT = 'A floating-point number is expected; use the dot as decimal ' \
                'separator, not a comma; do not enter any space.'
    BAD_EMAIL = 'Please enter a valid email.'
    BAD_URL = 'Please enter a valid URL.'
    BAD_ALPHANUMERIC = 'Please enter a valid alphanumeric value.'
    ACTION_OK = 'The action has been successfully executed.'
    ACTION_KO = 'A problem occurred while executing the action.'
    FRONT_PAGE_TEXT = 'Welcome to this Appy-powered Plone site.'
    EMAIL_SUBJECT = '${siteTitle} - Action \\"${transitionName}\\" has been ' \
                    'performed on element entitled \\"${objectTitle}\\".'
    EMAIL_BODY = 'You can consult this element at ${objectUrl}.'
    SELECT_DESELECT = '(Un)select all'
    NO_SELECTION = 'You must select at least one element.'
    DELETE_CONFIRM = 'Are you sure you want to delete this element?'
    DELETE_DONE = 'The element has been deleted.'
    GOTO_FIRST = 'Go to top'
    GOTO_PREVIOUS = 'Go to previous'
    GOTO_NEXT = 'Go to next'
    GOTO_LAST = 'Go to end'
    GOTO_SOURCE = 'Go back'

    def __init__(self, id, msg, default, fuzzy=False, comments=[]):
        self.id = id
        self.msg = msg
        self.default = default
        self.fuzzy = fuzzy # True if the default value has changed in the pot
        # file: the msg in the po file needs to be translated again.
        self.comments = comments

    def update(self, newMsg, isPot, language):
        '''Updates me with new values from p_newMsg. If p_isPot is True (which
           means that the current file is a pot file), I do not care about
           filling self.msg.'''
        if isPot:
            self.msg = ""
            if not self.default:
                self.default = newMsg.default
                # It means that if the default message has changed, we will not
                # update it in the pot file. We will always keep the one that
                # the user may have changed in the pot file. We will write a
                # default message only when no default message is defined.
        else:
            # newMsg comes from a pot file, we must update the corresponding
            # message in the current po file.
            oldDefault = self.default
            if self.default != newMsg.default:
                # The default value has changed in the pot file
                self.default = newMsg.default
                if self.msg.strip():
                    self.fuzzy = True
                    # We mark the message as "fuzzy" (=may need to be rewritten
                    # because the default value has changed) only if the user
                    # has already entered a message. Else, this has no sense to
                    # rewrite the empty message.
                else:
                    self.fuzzy = False
            if (language == 'en'):
                if not self.msg:
                    # Put the default message into msg for english
                    self.msg = self.default
                if self.fuzzy and (self.msg == oldDefault):
                    # The message was equal to the old default value. It means
                    # that the user did not change it, because for English we
                    # fill by default the message with the default value (see
                    # code just above). So in this case, the message was not
                    # really fuzzy.
                    self.fuzzy = False
                    self.msg = self.default

    def produceNiceDefault(self):
        '''Transforms self.default into a nice msg.'''
        self.default = produceNiceMessage(self.default)

    def generate(self):
        '''Produces myself as I must appear in a po(t) file.'''
        res = ''
        for comment in self.comments:
            res += comment + '\n'
        if self.default != None:
            res = '#. Default: "%s"\n' % self.default
        if self.fuzzy:
            res += '#, fuzzy\n'
        res += 'msgid "%s"\n' % self.id
        res += 'msgstr "%s"\n' % self.msg
        return res

    def __repr__(self):
        return '<i18n msg id="%s", msg="%s", default="%s">' % \
               (self.id, self.msg, self.default)

    def __cmp__(self, other):
        return cmp(self.id, other.id)

    def clone(self, oldPrefix, newPrefix):
        '''This returns a cloned version of myself. The clone has another id
           that includes p_newPrefix.'''
        if self.id.startswith(oldPrefix):
            newId = newPrefix + self.id[len(oldPrefix):]
        else:
            newId = '%s_%s' % (newPrefix, self.id.split('_', 1)[1])
        return PoMessage(newId, self.msg, self.default, comments=self.comments)

class PoHeader:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def generate(self):
        '''Generates the representation of myself into a po(t) file.'''
        return '"%s: %s\\n"\n' % (self.name, self.value)

class PoFile:
    '''Represents a i18n file.'''
    def __init__(self, fileName):
        self.fileName = fileName
        self.isPot = fileName.endswith('.pot')
        self.messages = [] # Ordered list of messages
        self.messagesDict = {} # Dict of the same messages, indexed by msgid
        self.headers = []
        self.headersDict = {}
        # Get application name, domain name and language from fileName
        self.applicationName = ''
        self.language = ''
        self.domain = ''
        baseName = os.path.splitext(os.path.basename(fileName))[0]
        elems = baseName.split('-')
        if self.isPot:
            if len(elems) == 1:
                self.applicationName = baseName
                self.domain = baseName
            else:
                self.applicationName = elems[0]
                self.domain = elems[1]
        else:
            self.applicationName = elems[0]
            if len(elems) == 2:
                self.domain = self.applicationName
                self.language = elems[1]
            else:
                self.domain = elems[1]
                self.language = elems[2]
        self.generated = False # Is set to True during the generation process
        # when this file has been generated.

    def addMessage(self, newMsg):
        res = copy.copy(newMsg)
        self.messages.append(res)
        self.messagesDict[res.id] = res
        return res

    def addHeader(self, newHeader):
        self.headers.append(newHeader)
        self.headersDict[newHeader.name] = newHeader

    def update(self, newMessages, removeNotNewMessages=False,
               keepExistingOrder=True):
        '''Updates the existing messages with p_newMessages.
           If p_removeNotNewMessages is True, all messages in self.messages
           that are not in newMessages will be removed. If p_keepExistingOrder
           is False, self.messages will be sorted according to p_newMessages.
           Else, newMessages that are not yet in self.messages will be appended
           to the end of self.messages.'''
        # First, remove not new messages if necessary
        newIds = [m.id for m in newMessages]
        removedIds = []
        if removeNotNewMessages:
            i = len(self.messages)-1
            while i >= 0:
                oldId = self.messages[i].id
                if oldId not in newIds:
                    del self.messages[i]
                    del self.messagesDict[oldId]
                    removedIds.append(oldId)
                i -= 1
        if keepExistingOrder:
            # Update existing messages and add inexistent messages to the end.
            for newMsg in newMessages:
                if self.messagesDict.has_key(newMsg.id):
                    msg = self.messagesDict[newMsg.id]
                else:
                    msg = self.addMessage(newMsg)
                msg.update(newMsg, self.isPot, self.language)
        else:
            # Keep the list of all old messages not being in new messages.
            # We will append them at the end of the new messages.
            notNewMessages = [m for m in self.messages if m.id not in newIds]
            del self.messages[:]
            for newMsg in newMessages:
                if self.messagesDict.has_key(newMsg.id):
                    msg = self.messagesDict[newMsg.id]
                    self.messages.append(msg)
                else:
                    msg = self.addMessage(newMsg)
                msg.update(newMsg, self.isPot, self.language)
            # Append the list of old messages to the end
            self.messages += notNewMessages
        return removedIds

    def generateHeaders(self, f):
        if not self.headers:
            creationTime = time.strftime("%Y-%m-%d %H:%M-%S", time.localtime())
            fb = ''
            if not self.isPot:
                # I must add fallbacks
                if fallbacks.has_key(self.language):
                    fb = '"X-is-fallback-for: %s\\n"' % fallbacks[self.language]
            f.write(poHeader % (self.applicationName, creationTime,
                                self.language, self.language, self.domain, fb))
        else:
            # Some headers were already found, we dump them as is
            f.write('msgid ""\nmsgstr ""\n')
            for header in self.headers:
                f.write(header.generate())
            f.write('\n')

    def generate(self):
        '''Generates the corresponding po or pot file.'''
        folderName = os.path.dirname(self.fileName)
        if not os.path.exists(folderName):
            os.makedirs(folderName)
        f = file(self.fileName, 'w')
        self.generateHeaders(f)
        for msg in self.messages:
            f.write(msg.generate())
            f.write('\n')
        f.close()
        self.generated = True

    def getPoFileName(self, language):
        '''Gets the name of the po file that corresponds to this pot file and
           the given p_language.'''
        if self.applicationName == self.domain:
            res = '%s-%s.po' % (self.applicationName, language)
        else:
            res = '%s-%s-%s.po' % (self.applicationName, self.domain, language)
        return res

class PoParser:
    '''Allows to parse a i18n file. The result is produced in self.res as a
       PoFile instance.'''
    def __init__(self, fileName):
        self.res = PoFile(fileName)

    # Regular expressions for msgIds, msgStrs and default values.
    re_default = re.compile('#\.\s+Default\s*:\s*"(.*)"')
    re_fuzzy = re.compile('#,\s+fuzzy')
    re_id = re.compile('msgid\s+"(.*)"')
    re_msg = re.compile('msgstr\s+"(.*)"')

    def parse(self):
        '''Parses all i18n messages in the file, stores it in
           self.res.messages and returns it also.'''
        f = file(self.res.fileName)
        # Currently parsed values
        msgDefault = msgFuzzy = msgId = msgStr = None
        comments = []
        # Walk every line of the po(t) file
        for line in f:
            lineContent = line.strip()
            if lineContent and (not lineContent.startswith('"')):
                r = self.re_default.match(lineContent)
                if r:
                    msgDefault = r.group(1)
                else:
                    r = self.re_fuzzy.match(lineContent)
                    if r:
                        msgFuzzy = True
                    else:
                        r = self.re_id.match(lineContent)
                        if r:
                            msgId = r.group(1)
                        else:
                            r = self.re_msg.match(lineContent)
                            if r:
                                msgStr = r.group(1)
                            else:
                                if lineContent.startswith('#'):
                                    comments.append(lineContent.strip())
                if msgStr != None:
                    if not ((msgId == '') and (msgStr == '')):
                        poMsg = PoMessage(msgId, msgStr, msgDefault, msgFuzzy,
                                          comments)
                        self.res.addMessage(poMsg)
                    msgDefault = msgFuzzy = msgId = msgStr = None
                    comments = []
            if lineContent.startswith('"'):
                # It is a header value
                name, value = lineContent.strip('"').split(':', 1)
                if value.endswith('\\n'):
                    value = value[:-2]
                self.res.addHeader(PoHeader(name.strip(), value.strip()))
        f.close()
        return self.res
# ------------------------------------------------------------------------------
