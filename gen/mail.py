'''This package contains functions for sending email notifications.'''
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email import Encoders
from email.Header import Header
from appy.shared.utils import sequenceTypes

# ------------------------------------------------------------------------------
def sendMail(tool, to, subject, body, attachments=None):
    '''Sends a mail, via p_tool.mailHost, to p_to (a single email address or a
       list of email addresses).'''
    # Just log things if mail is disabled
    fromAddress = tool.mailFrom
    if not tool.mailEnabled:
        tool.log('Mail disabled: should send mail from %s to %s.' % \
                 (fromAddress, str(to)))
        tool.log('Subject: %s' % subject)
        tool.log('Body: %s' % body)
        if attachments:
            tool.log('%d attachment(s).' % len(attachments))
        return
    tool.log('Sending mail from %s to %s (subject: %s).' % \
             (fromAddress, str(to), subject))
    # Create the base MIME message
    body = MIMEText(body, 'plain', 'utf-8')
    if attachments:
        msg = MIMEMultipart()
        msg.attach( body )
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
        for fileName, fileContent in attachments:
            part = MIMEBase('application', 'octet-stream')
            if hasattr(fileContent, 'data'):
                # It is a File instance coming from the database
                data = fileContent.data
                if isinstance(data, basestring):
                   payLoad = data
                else:
                   payLoad = ''
                   while data is not None:
                       payLoad += data.data
                       data = data.next
            else:
                payLoad = fileContent
            part.set_payload(payLoad)
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                            'attachment; filename="%s"' % fileName)
            msg.attach(part)
    # Send the email
    try:
        mh = smtplib.SMTP(tool.mailHost)
        mh.sendmail(fromAddress, [to], msg.as_string())
        mh.quit()
    except smtplib.SMTPException, e:
        tool.log('Mail sending failed: %s' % str(e))

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
