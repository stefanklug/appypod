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

# Standard Appy labels with their default value in english ---------------------
appyLabels = [
 ('app_name', 'Appy'),
 ('workflow_state', 'state'),
 ('workflow_comment', 'Optional comment'),
 ('appy_title', 'Title'),
 ('data_change', 'Data change'),
 ('modified_field', 'Modified field'),
 ('previous_value', 'Previous value'),
 ('phase', 'phase'),
 ('choose_a_value', ' - '),
 ('choose_a_doc', '[ Documents ]'),
 ('min_ref_violated', 'You must choose more elements here.'),
 ('max_ref_violated', 'Too much elements are selected here.'),
 ('no_ref', 'No object.'),
 ('add_ref', 'Add a new one'),
 ('action_ok', 'The action has been successfully executed.'),
 ('action_ko', 'A problem occurred while executing the action.'),
 ('move_up', 'Move up'),
 ('move_down', 'Move down'),
 ('query_create', 'create'),
 ('query_import', 'import'),
 ('query_no_result', 'Nothing to see for the moment.'),
 ('query_consult_all', 'consult all'),
 ('import_title', 'Importing data into your application'),
 ('import_show_hide', 'Show / hide alreadly imported elements.'),
 ('import_already', 'Already imported.'),
 ('import_many', 'Import selected elements'),
 ('import_done', 'Import terminated successfully.'),
 ('search_title', 'Advanced search'),
 ('search_button', 'Search'),
 ('search_objects', 'Search objects of this type.'),
 ('search_results', 'Search results'),
 ('search_results_descr', ' '),
 ('search_new', 'New search'),
 ('search_from', 'From'),
 ('search_to', 'to'),
 ('search_or', 'or'),
 ('search_and', 'and'),
 ('ref_invalid_index', 'No move occurred: please specify a valid number.'),
 ('bad_long', 'An integer value is expected; do not enter any space.'),
 ('bad_float', 'A floating-point number is expected; use the dot as decimal ' \
               'separator, not a comma; do not enter any space.'),
 ('bad_date', 'Please specify a valid date.'),
 ('bad_email', 'Please enter a valid email.'),
 ('bad_url', 'Please enter a valid URL.'),
 ('bad_alphanumeric', 'Please enter a valid alphanumeric value.'),
 ('bad_select_value', 'The value is not among possible values for this field.'),
 ('select_delesect', '(Un)select all'),
 ('no_elem_selected', 'You must select at least one element.'),
 ('object_edit', 'Edit'),
 ('object_delete', 'Delete'),
 ('object_unlink', 'Unlink'),
 ('delete_confirm', 'Are you sure you want to delete this element?'),
 ('unlink_confirm', 'Are you sure you want to unlink this element?'),
 ('delete_done', 'The element has been deleted.'),
 ('unlink_done', 'The element has been unlinked.'),
 ('goto_first', 'Go to top'),
 ('goto_previous', 'Go to previous'),
 ('goto_next', 'Go to next'),
 ('goto_last', 'Go to end'),
 ('goto_source', 'Go back'),
 ('whatever', 'Whatever'),
 ('yes', 'Yes'),
 ('no', 'No'),
 ('field_required', 'Please fill this field.'),
 ('field_invalid', 'Please fill or correct this.'),
 ('file_required', 'Please select a file.'),
 ('image_required', 'The uploaded file must be an image.'),
 ('odt', 'ODT'),
 ('pdf', 'PDF'),
 ('doc', 'DOC'),
 ('rtf', 'RTF'),
 ('front_page_text', 'Welcome to this Appy-powered site.'),
 ('captcha_text', 'Please type "${text}" (without the double quotes) in the ' \
                  'field besides, but without the character at position ' \
                  '${number}.'),
 ('bad_captcha', 'The code was not correct. Please try again.'),
 ('app_login', 'Login'),
 ('app_connect', 'Log in'),
 ('app_logout', 'Logout'),
 ('app_password', 'Password'),
 ('app_home', 'Home'),
 ('login_reserved', 'This login is reserved.'),
 ('login_in_use', 'This login is already in use.'),
 ('login_ko', 'Welcome! You are now logged in.'),
 ('login_ok', 'Login failed.'),
 ('password_too_short', 'Passwords must contain at least ${nb} characters.'),
 ('passwords_mismatch', 'Passwords do not match.'),
 ('object_save', 'Save'),
 ('object_saved', 'Changes saved.'),
 ('validation_error', 'Please correct the indicated errors.'),
 ('object_cancel', 'Cancel'),
 ('object_canceled', 'Changes canceled.'),
 ('enable_cookies', 'You must enable cookies before you can log in.'),
 ('page_previous', 'Previous page'),
 ('page_next', 'Next page'),
 ('forgot_password', 'Forgot password?'),
 ('ask_password_reinit', 'Ask new password'),
 ('wrong_password_reinit', 'Something went wrong. First possibility: you ' \
    'have already clicked on the link (maybe have you double-clicked?) ' \
    'and your password has already been re-initialized. Please check ' \
    'that you haven\'t received your new password in another email. ' \
    'Second possibility: the link that you received in your mailer was ' \
    'splitted on several lines. In this case, please re-type the link in ' \
    'one single line and retry. Third possibility: you have waited too ' \
    'long and your request has expired, or a technical error occurred. ' \
    'In this case, please try again to ask a new password from the start.'),
 ('reinit_mail_sent', 'A mail has been sent to you. Please follow the ' \
                      'instructions from this email.'),
 ('reinit_password', 'Password re-initialisation'),
 ('reinit_password_body', 'Hello,<br/><br/>A password re-initialisation ' \
    'has been requested, tied to this email address, for the website ' \
    '${siteUrl}. If you are not at the origin of this request, please ' \
    'ignore this email. Else, click on the link below to receive a new ' \
    'password.<br/><br/>${url}'),
 ('new_password', 'Your new password'),
 ('new_password_body', 'Hello,<br/><br/>The new password you have ' \
                       'requested for website ${siteUrl} is ${password}<br/>' \
                       '<br/>Best regards.'),
 ('new_password_sent', 'Your new password has been sent to you by email.'),
 ('last_user_access', 'Last access'),
 ('object_history', 'History'),
 ('object_created_by', 'By'),
 ('object_created_on', 'On'),
 ('object_modified_on', 'Last updated on'),
 ('object_action', 'Action'),
 ('object_author', 'Author'),
 ('action_date', 'Date'),
 ('action_comment', 'Comment'),
 ('day_Mon_short', 'Mon'),
 ('day_Tue_short', 'Tue'),
 ('day_Wed_short', 'Wed'),
 ('day_Thu_short', 'Thu'),
 ('day_Fri_short', 'Fri'),
 ('day_Sat_short', 'Sat'),
 ('day_Sun_short', 'Sun'),
 ('day_Mon', 'Monday'),
 ('day_Tue', 'Tuesday'),
 ('day_Wed', 'Wednesday'),
 ('day_Thu', 'Thursday'),
 ('day_Fri', 'Friday'),
 ('day_Sat', 'Saturday'),
 ('day_Sun', 'Sunday'),
 ('ampm_am', 'AM'),
 ('ampm_pm', 'PM'),
 ('month_Jan_short', 'Jan'),
 ('month_Feb_short', 'Feb'),
 ('month_Mar_short', 'Mar'),
 ('month_Apr_short', 'Apr'),
 ('month_May_short', 'May'),
 ('month_Jun_short', 'Jun'),
 ('month_Jul_short', 'Jul'),
 ('month_Aug_short', 'Aug'),
 ('month_Sep_short', 'Sep'),
 ('month_Oct_short', 'Oct'),
 ('month_Nov_short', 'Nov'),
 ('month_Dec_short', 'Dec'),
 ('month_Jan', 'January'),
 ('month_Feb', 'February'),
 ('month_Mar', 'March'),
 ('month_Apr', 'April'),
 ('month_May', 'May'),
 ('month_Jun', 'June'),
 ('month_Jul', 'July'),
 ('month_Aug', 'Augustus'),
 ('month_Sep', 'September'),
 ('month_Oct', 'October'),
 ('month_Nov', 'November'),
 ('month_Dec', 'December'),
 ('today', 'Today'),
 ('which_event', 'Which event type would you like to create?'),
 ('event_span', 'Extend the event on the following number of days (leave ' \
                'blank to create an event on the current day only):'),
 ('del_next_events', 'Also delete successive events of the same type.'),
]

# Some default values for labels whose ids are not fixed (so they can't be
# included in the previous variable).
CONFIG = "Configuration panel for product '%s'"
# The following messages (starting with MSG_) correspond to tool
# attributes added for every gen-class (warning: the message IDs correspond
# to MSG_<attributePrefix>).
MSG_podTemplate = "POD template for field '%s'"
MSG_formats = "Output format(s) for field '%s'"
MSG_resultColumns = "Columns to display while showing query results"
MSG_enableAdvancedSearch = "Enable advanced search"
MSG_numberOfSearchColumns = "Number of search columns"
MSG_searchFields = "Search fields"
POD_ASKACTION = 'Trigger related action'
EMAIL_SUBJECT = '${siteTitle} - Action \\"${transitionName}\\" has been ' \
                'performed on element entitled \\"${objectTitle}\\".'
EMAIL_BODY = 'You can consult this element at ${objectUrl}.'
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
            # newMsg comes from a pot file, we must update the corresponding
            # message in the current po file.
            oldDefault = self.default
            if self.default != newMsg.default:
                # The default value has changed in the pot file
                oldDefault = self.default
                self.default = newMsg.default
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
                if not oldId.startswith('custom_') and \
                   not oldId.startswith('%sTranslation_page_'%self.domain) and \
                   (oldId not in newIds):
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
