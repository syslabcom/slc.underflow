import logging
from smtplib import SMTPException

from Acquisition import aq_parent
from zope.component import queryUtility
from zope.i18n import translate
from zope.i18nmessageid import Message
from zope.interface import implements
from zope.lifecycleevent import ObjectModifiedEvent

from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from plone.app.discussion.interfaces import IDiscussionSettings

from slc.underflow import MessageFactory as _


MAIL_NOTIFICATION_MESSAGE = _(
    u"mail_notification_message",
    default=u"A comment on '${title}' "
             "has been posted here: ${link}\n\n"
             "---\n"
             "${text}\n"
             "---\n")

MAIL_NOTIFICATION_NOSY = _(
    u"mail_notification_nosy",
    default=u"A question titled '${title}' "
             "has been posted here: ${link}\n\n"
             "---\n"
             "${text}\n"
             "---\n")

logger = logging.getLogger("slc.underflow.eventhandlers")

def notify_followers(obj, event):
    """Tell our followers when a comment has been added.

       This method composes and sends emails to all users that have added a
       comment to this conversation and requested to be notified of follow-ups.
    """

    # Get info necessary to send email
    mail_host = getToolByName(obj, 'MailHost')
    portal_url = getToolByName(obj, 'portal_url')
    portal = portal_url.getPortalObject()
    sender = portal.getProperty('email_from_address')

    # Check if a sender address is available
    if not sender:
        return

    # Compose and send emails to all users that have add a comment to this
    # conversation and enabled user_notification.
    conversation = aq_parent(obj)
    content_object = aq_parent(conversation)

    # Avoid sending multiple notification emails to the same person
    # when he has commented multiple times.
    emails = set()
    for comment in conversation.getComments():
        if (obj != comment and
            comment.user_notification and comment.author_email):
            emails.add(comment.author_email)

    if not emails:
        return

    subject = translate(_(u"A comment has been posted."),
                        context=obj.REQUEST)
    message = translate(Message(
            MAIL_NOTIFICATION_MESSAGE,
            mapping={'title': safe_unicode(content_object.title),
                     'link': content_object.absolute_url() +
                             '/view#' + obj.id,
                     'text': obj.text}),
            context=obj.REQUEST)
    for email in emails:
        # Send email
        try:
            mail_host.send(message,
                           email,
                           sender,
                           subject,
                           charset='utf-8')
        except SMTPException:
            logger.error('SMTP exception while trying to send an ' +
                         'email from %s to %s',
                         sender,
                         email)


# Event handler for IObjectAddedEvent and IObjectModifiedEvent to let all
# nosy know of changes to the question object.
def notify_nosy(obj, event):
    """ Tell the nosy list (groups) about the new question. """

    # Get info necessary to send email
    mail_host = getToolByName(obj, 'MailHost')
    portal_url = getToolByName(obj, 'portal_url')
    portal = portal_url.getPortalObject()
    sender = portal.getProperty('email_from_address')

    # Check if a sender address is available
    if not sender:
        return

    emails = set()
    groups_tool = getToolByName(obj, 'portal_groups')
    for gid in obj.nosy:
        group = groups_tool.getGroupById(gid)
        for member in group.getGroupMembers():
            email = member.getProperty('email')
            if email != '':
                emails.add(email)

    if not emails:
        return

    # Transform the text of the question
    transforms = getToolByName(obj, 'portal_transforms')
    text = obj.question.output
    if isinstance(text, unicode):
        text = text.encode('utf8')
    transform = transforms.convertTo('text/plain', text, context=obj,
        mimetype='text/html')
    if transform:
        text = transform.getData().strip()
    else:
        text = ''

    if isinstance(event, ObjectModifiedEvent):
        subject = translate(_(u"A question has been modified."),
                        context=obj.REQUEST)
    else:
        subject = translate(_(u"A question has been posted."),
                        context=obj.REQUEST)

    message = translate(Message(
            MAIL_NOTIFICATION_NOSY,
            mapping={'title': safe_unicode(obj.title),
                     'link': obj.absolute_url(),
                     'text': text}),
            context=obj.REQUEST)

    for email in emails:
        # Send email
        try:
            mail_host.send(message, email, sender, subject, charset='utf-8')
        except SMTPException:
            logger.error('SMTP exception while trying to send an ' +
                         'email from %s to %s',
                         sender,
                         email)
