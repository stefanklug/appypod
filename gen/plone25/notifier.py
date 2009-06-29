'''This package contains functions for sending email notifications.'''

# ------------------------------------------------------------------------------
def getEmailAddress(name, email, encoding='utf-8'):
    '''Creates a full email address from a p_name and p_email.'''
    res = email
    if name: res = name.decode(encoding) + ' <%s>' % email
    return res

def convertRolesToEmails(users, portal):
    '''p_users is a list of emails and/or roles. This function returns the same
       list, where all roles have been expanded to emails of users having this
       role (more precisely, users belonging to the group Appy created for the
       given role).'''
    res = []
    for mailOrRole in users:
        if mailOrRole.find('@') != -1:
            # It is an email. Append it directly to the result.
            res.append(mailOrRole)
        else:
            # It is a role. Find the corresponding group (Appy creates
            # one group for every role defined in the application).
            groupId = mailOrRole + '_group'
            group = portal.acl_users.getGroupById(groupId)
            if group:
                for user in group.getAllGroupMembers():
                    userMail = user.getProperty('email')
                    if userMail and (userMail not in res):
                        res.append(userMail)
    return res

# ------------------------------------------------------------------------------
SENDMAIL_ERROR = 'Error while sending mail: %s.'
ENCODING_ERROR = 'Encoding error while sending mail: %s.'

from appy.gen.utils import sequenceTypes
from appy.gen.plone25.descriptors import WorkflowDescriptor
import socket

def sendMail(obj, transition, transitionName, workflow, logger):
    '''Sends mail about p_transition that has been triggered on p_obj that is
       controlled by p_workflow.'''
    wfName = WorkflowDescriptor.getWorkflowName(workflow.__class__)
    ploneObj = obj.o
    portal = ploneObj.portal_url.getPortalObject()
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
        # The user didn't mention mail body and subject. We will use
        # those defined from i18n labels.
        wfHistory = ploneObj.getWorkflowHistory()
        labelPrefix = '%s_%s' % (wfName, transitionName)
        tName = obj.translate(labelPrefix)
        keys = {'siteUrl': portal.absolute_url(),
                'siteTitle': portal.Title(),
                'objectUrl': ploneObj.absolute_url(),
                'objectTitle': ploneObj.Title(),
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
    # Among "to" and "cc", convert all roles to concrete email addresses
    to = convertRolesToEmails(to, portal)
    cc = convertRolesToEmails(cc, portal)
    # Determine "from" address
    enc= portal.portal_properties.site_properties.getProperty('default_charset')
    fromAddress = getEmailAddress(
        portal.getProperty('email_from_name'),
        portal.getProperty('email_from_address'), enc)
    # Send the mail
    i = 0
    for recipient in to:
        i += 1
        try:
            if i != 1: cc = []
            portal.MailHost.secureSend(mailBody.encode(enc),
                recipient.encode(enc), fromAddress.encode(enc),
                mailSubject.encode(enc), mcc=cc, charset='utf-8')
        except socket.error, sg:
            logger.warn(SENDMAIL_ERROR % str(sg))
            break
        except UnicodeDecodeError, ue:
            logger.warn(ENCODING_ERROR % str(ue))
            break
        except Exception, e:
            logger.warn(SENDMAIL_ERROR % str(e))
            break
# ------------------------------------------------------------------------------
