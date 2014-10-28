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
             'fr': 'fr-be fr-ca fr-lu fr-mc fr-ch fr-fr'}

# Default values for i18n labels whose ids are not fixed.
CONFIG = "Configuration panel for product '%s'"
CONFIRM = 'Are you sure ?'

# ------------------------------------------------------------------------------
class PoMessage:
    '''Represents a i18n message (po format).'''
    def __init__(self, id, msg, default, fuzzy=False, comments=[],
                 niceDefault=False):
        self.id = id
        self.msg = msg
        self.default = default
        if niceDefault: self.produceNiceDefault()
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
            # newMsg comes from a pot file or from a base po file (like a
            # standard Appy po file). We must update the corresponding
            # message in the current po file.
            oldDefault = self.default
            if self.default != newMsg.default:
                # The default value has changed in the pot file
                oldDefault = self.default
                self.default = newMsg.default
                self.fuzzy = False
                if self.msg.strip():
                    self.fuzzy = True
                    # We mark the message as "fuzzy" (=may need to be rewritten
                    # because the default value has changed) only if the user
                    # has already entered a message. Else, this has no sense to
                    # rewrite the empty message.
                    if not oldDefault.strip():
                        # This is a strange case: the old default value did not
                        # exist. Maybe was this PO file generated from some
                        # tool, but simply without any default value. So in
                        # this case, we do not consider the label as fuzzy.
                        self.fuzzy = False
            # If p_newMsg contains a message, and no message is defined for
            # self, copy it.
            if newMsg.msg and not self.msg:
                self.msg = newMsg.msg
            # For english, the the default value from a pot file can be used as
            # value for the po file.
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

    def getMessage(self):
        '''Returns self.msg, but with some replacements.'''
        return self.msg.replace('<br/>', '\n').replace('\\"', '"')

class PoMessages:
    '''A list of po messages under construction.'''
    def __init__(self):
        # The list of messages
        self.messages = []
        # A dict of message ids, useful for efficiently checking if an id is
        # already in the list or not.
        self.ids = {}

    def append(self, id, default, nice=True):
        '''Creates a new PoMessage and adds it to self.messages. If p_nice is
           True, it produces a nice default value for the message.'''
        # Avoir creating duplicate ids
        if id in self.ids: return
        message = PoMessage(id, '', default, niceDefault=nice)
        self.messages.append(message)
        self.ids[id] = True

    def get(self): return self.messages

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
                self.applicationName = self.domain = elems[0]
            else:
                self.applicationName, self.domain = elems
        else:
            if len(elems) == 1:
                self.applicationName = self.domain = ''
                self.language = elems[0]
            elif len(elems) == 2:
                self.applicationName = self.domain = elems[0]
                self.language = elems[1]
            else:
                self.applicationName, self.domain, self.language = elems
        self.generated = False # Will be True during the generation process,
        # once this file will have been generated.

    def addMessage(self, newMsg, needsCopy=True):
        if needsCopy:
            res = copy.copy(newMsg)
        else:
            res = newMsg
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
           that are not in newMessages will be removed, excepted if they start
           with "custom_". If p_keepExistingOrder is False, self.messages will
           be sorted according to p_newMessages. Else, newMessages that are not
           yet in self.messages will be appended to the end of self.messages.'''
        # First, remove not new messages if necessary
        newIds = [m.id for m in newMessages]
        removedIds = []
        if removeNotNewMessages:
            i = len(self.messages)-1
            while i >= 0:
                oldId = self.messages[i].id
                if not oldId.startswith('custom_') and (oldId not in newIds):
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

    def getCustomMessages(self):
        '''Returns, the list of messages from self.messages whose ID starts with
           "custom_".'''
        return [m for m in self.messages if m.id.startswith('custom_')]

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
           self.res.messages and returns self.res.'''
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
