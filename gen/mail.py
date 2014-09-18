'''This package contains functions for sending email notifications.'''
import smtplib, socket
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
from email.Header import Header
from appy.shared.utils import sequenceTypes

# ------------------------------------------------------------------------------
class MailConfig:
    '''Parameters for conneting to a SMTP server.'''
    def __init__(self, fromName=None, fromEmail='info@appyframework.org',
                 server='localhost', port=25, login=None, password=None,
                 enabled=True):
        # The name that will appear in the "from" part of the messages
        self.fromName = fromName
        # The email that will appear in the "from" part of the messages
        self.fromEmail = fromEmail
        # The SMTP server address
        self.server = server
        # The SMTP server port
        self.port = port
        # Optional credentials to the SMTP server.
        self.login = login
        self.password = password
        # Is this server connection enabled ?
        self.enabled = enabled

    def getFrom(self):
        '''Gets the "from" part of the messages to send.'''
        if self.fromName: return '%s <%s>' % (self.fromName, self.fromEmail)
        return self.fromEmail

# ------------------------------------------------------------------------------
def sendMail(config, to, subject, body, attachments=None, log=None):
    '''Sends a mail, via the smtp server defined in the p_config (an instance of
       appy.gen.mail.MailConfig above), to p_to (a single email recipient or a
       list of recipients). Every (string) recipient can be an email address or
       a string of the form "[name] <[email]>".

       p_attachment must be a list or tuple whose elements can have 2 forms:
         1. a tuple (fileName, fileContent): "fileName" is the name of the file
            as a string; "fileContent" is the file content, also as a string;
         2. a appy.fields.file.FileInfo instance.

      p_log can be a function/method accepting a single string arg. 
    '''
    if not config:
        if log: log('Must send mail but no smtp server configured.')
        return
    # Just log things if mail is disabled
    fromAddress = config.getFrom()
    if not config.enabled or not config.server:
        if not config.server:
            msg = ' (no mailhost defined)'
        else:
            msg = ''
        if log:
            log('mail disabled%s: should send mail from %s to %s.' % \
                (msg, fromAddress, str(to)))
            log('subject: %s' % subject)
            log('body: %s' % body)
        if attachments and log: log('%d attachment(s).' % len(attachments))
        return
    if log: log('sending mail from %s to %s (subject: %s).' % \
                (fromAddress, str(to), subject))
    # Create the base MIME message
    body = MIMEText(body, 'plain', 'utf-8')
    if attachments:
        msg = MIMEMultipart()
        msg.attach(body)
    else:
        msg = body
    # Add the header values
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = fromAddress
    if isinstance(to, basestring):
        msg['To'] = to
    else:
        if len(to) == 1:
            msg['To'] = to[0]
        else:
            msg['To'] = fromAddress
            msg['Bcc'] = ', '.join(to)
            to = fromAddress
    # Add attachments
    if attachments:
        for attachment in attachments:
            # 2 possible forms for an attachment
            if isinstance(attachment, tuple) or isinstance(attachment, list):
                fileName, fileContent = attachment
            else:
                # a FileInfo instance
                fileName = attachment.uploadName
                f = file(attachment.fsPath, 'rb')
                fileContent = f.read()
                f.close()
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(fileContent)
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename="%s"' % fileName)
            msg.attach(part)
    # Send the email
    try:
        smtpServer = smtplib.SMTP(config.server, port=config.port)
        if config.login:
            smtpServer.login(config.login, config.password)
        res = smtpServer.sendmail(fromAddress, [to], msg.as_string())
        smtpServer.quit()
        if res and log:
            log('could not send mail to some recipients. %s' % str(res),
                type='warning')
    except smtplib.SMTPException, e:
        if log: log('mail sending failed: %s' % str(e), type='error')
    except socket.error, se:
        if log: log('mail sending failed: %s' % str(se), type='error')

# ------------------------------------------------------------------------------
def sendNotification(obj, transition, transitionName, workflow):
    '''Sends mail about p_transition named p_transitionName, that has been
       triggered on p_obj that is controlled by p_workflow.'''
    from appy.gen.descriptors import WorkflowDescriptor
    wfName = WorkflowDescriptor.getWorkflowName(workflow.__class__)
    zopeObj = obj.o
    tool = zopeObj.getTool()
    mailInfo = transition.notify(workflow, obj)
    if not mailInfo[0]: return # Send a mail to nobody.
    # mailInfo may be one of the following:
    #   (to,)
    #   (to, cc)
    #   (to, mailSubject, mailBody)
    #   (to, cc, mailSubject, mailBody)
    # "to" and "cc" maybe simple strings (one simple string = one email
    # address or one role) or sequences of strings.
    # Determine mail subject and body.
    if len(mailInfo) <= 2:
        # The user didn't mention mail body and subject. We will use those
        # defined from i18n labels.
        wfHistory = zopeObj.getHistory()
        labelPrefix = '%s_%s' % (wfName, transitionName)
        tName = obj.translate(labelPrefix)
        keys = {'siteUrl': tool.getPath('/').absolute_url(),
                'siteTitle': tool.getAppName(),
                'objectUrl': zopeObj.absolute_url(),
                'objectTitle': zopeObj.Title(),
                'transitionName': tName,
                'transitionComment': wfHistory[0]['comments']}
        mailSubject = obj.translate(labelPrefix + '_mail_subject', keys)
        mailBody = obj.translate(labelPrefix + '_mail_body', keys)
    else:
        mailSubject = mailInfo[-1]
        mailBody = mailInfo[-2]
    # Determine "to" and "cc".
    to = mailInfo[0]
    cc = []
    if (len(mailInfo) in (2,4)) and mailInfo[1]: cc = mailInfo[1]
    if type(to) not in sequenceTypes: to = [to]
    if type(cc) not in sequenceTypes: cc = [cc]
    # Send the mail
    sendMail(tool.appy(), to, mailSubject, mailBody)
# ------------------------------------------------------------------------------
