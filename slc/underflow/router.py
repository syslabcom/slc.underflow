import re
from datetime import datetime 
import email
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl import getSecurityManager
from zope.interface import implements
from zope.component import createObject
from Products.CMFCore.utils import getToolByName
from plone.app.uuid.utils import uuidToObject
from plone.app.discussion.interfaces import IConversation, IReplies
from slc.mailrouter.exceptions import PermissionError, NotFoundError, \
    PermanentError
from slc.mailrouter.interfaces import IMailRouter
from slc.underflow.settings import getSettings
from slc.underflow import MessageFactory as _

def decodeheader(value):
    """Decode RFC-2047 TEXT (e.g. "=?utf-8?q?f=C3=BCr?=" -> u"f\xfcr")."""
    atoms = email.Header.decode_header(value)
    decodedvalue = ""
    for atom, charset in atoms:
        if charset is not None:
            atom = atom.decode(charset)
        decodedvalue += atom
    return decodedvalue

class CommentRouter(object):
    implements(IMailRouter)

    def __call__(self, site, msg):
        recipient = email.Utils.parseaddr(msg.get('To'))[1]

        settings = getSettings()
        if settings is None or settings.sender is None:
            # Cannot handle email unless we have a dedicated address for it
            return False 

        if recipient.lower() != settings.sender.strip().lower():
            # It is not addressed to us
            return False

        sender = msg.get('From')
        sender = email.Utils.parseaddr(sender)[1].lower()

        # Drop privileges to the right user
        acl_users = getToolByName(site, 'acl_users')
        pm = getToolByName(site, 'portal_membership')
        props = getToolByName(site, 'portal_properties').site_properties
        user = None
        if props.getProperty('use_email_as_login'):
            # If email logins are used, the user's email might be his id
            user = pm.getMemberById(sender)
            if user is not None:
                if user.getProperty('email') == sender:
                    user = user.getUser()
                else:
                    user = None

        if user is None:
            potential = pm.searchMembers('email', sender)
            # Email might match more than one user, check for exact match
            for u in potential:
                if sender == u['email']:
                    user = pm.getMemberById(u['username']).getUser()
                    break

        if user is None:
            raise NotFoundError(_("Sender is not a valid user"))

        newSecurityManager(None, user.__of__(acl_users))

        # Find relevant comment
        subject = msg.get('subject', '').strip()
        if not subject:
            raise NotFoundError(_("Subject is blank"))

        subject = decodeheader(subject)
        pat = re.compile('[^[]*\[([^#]+)(#([^\]]+))?\]')
        m = pat.match(subject)
        if m is None:
            raise NotFoundError(_("Unable to match a question"))
        
        questionid = m.groups()[0]
        commentid = m.groups()[2] # Might be None

        question = uuidToObject(questionid)
        if question is None:
            raise NotFoundError(_("Unable to match a question"))

        can_reply = getSecurityManager().checkPermission(
            'Reply to item', question)

        if not can_reply:
            raise PermissionError(_("Insufficient privileges"))

        comment = createObject('plone.Comment')

        member = pm.getAuthenticatedMember()
        address = member.getProperty('email')
        fullname = member.getProperty('fullname')
        if not fullname or fullname == '':
            fullname = member.getUserName()
        elif isinstance(fullname, str):
            fullname = unicode(fullname, 'utf-8')

        if address and isinstance(address, str):
            address = unicode(address, 'utf-8')

        comment.creator = member.getUserName()
        comment.author_username = comment.creator
        comment.author_name = fullname
        comment.author_email = address
        comment.creation_date = datetime.utcnow()
        comment.modification_date = comment.creation_date

        # Walk the message and get the inline component
        for part in msg.walk():
            if part.is_multipart():
                # Ignore multipart envelope if it exists
                continue
            if part.get_filename() is not None:
                # Ignore attachments
                continue

            content_type = part.get_content_type()

            if content_type not in ('text/plain', 'text/html'):
                # Skip non text/html parts
                continue

            payload = part.get_payload(decode=1)
            if content_type == 'text/html':
                transforms = getToolByName(site, 'portal_transforms')
                transform = transforms.convertTo('text/plain',
                    payload, context=site, mimetype='text/html')
                if transform:
                    payload = transform.getData().strip()
                else:
                    raise PermanentError(_(u"Could not convert html email"))

            comment.text = payload.strip()
            break # Get out of the for loop

        # Add comment to conversation
        conversation = IConversation(question)
        if commentid is not None:
            # Add a reply to an existing comment
            conversation_to_reply_to = conversation.get(commentid)
            replies = IReplies(conversation_to_reply_to)
            comment_id = replies.addComment(comment)
        else:
            # Add a comment to the conversation
            comment_id = conversation.addComment(comment)

        return True

    def priority(self):
        return 25
