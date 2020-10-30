from Acquisition import aq_parent
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.controlpanel import IMailSchema
from Products.CMFPlone.utils import safe_unicode
from plone.registry.interfaces import IRegistry
from plone.uuid.interfaces import IUUID
from plone import api
from slc.underflow.interfaces import ISlcUnderflow
from slc.underflow.settings import getSettings
from smtplib import SMTPException
from zope.i18n import translate
from zope.lifecycleevent import ObjectModifiedEvent
from zope import component
import logging


logger = logging.getLogger("slc.underflow.eventhandlers")


def notify_followers(obj, event):
    """Tell our followers when a comment has been added.

       This method composes and sends emails to all users that have added a
       comment to this conversation and requested to be notified of follow-ups.
    """
    request = getattr(obj, 'REQUEST', None)
    if not request:
        return
    if not ISlcUnderflow.providedBy(request):
        return

    # Get info necessary to send email
    mail_host = getToolByName(obj, 'MailHost')
    portal_url = getToolByName(obj, 'portal_url')
    portal = portal_url.getPortalObject()

    settings = getSettings()
    if settings is None or settings.sender is None:
        sender = portal.getProperty('email_from_address')
        if not sender:
            registry = component.getUtility(IRegistry)
            mail_settings = registry.forInterface(IMailSchema, prefix='plone')
            sender = mail_settings.email_from_address
    else:
        sender = settings.sender

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

    subject = translate(u"A comment has been posted [${uid}#${id}]",
        mapping={'uid': IUUID(content_object), 'id': obj.id},
        context=obj.REQUEST)
    template = component.getMultiAdapter((obj, obj.REQUEST),
        name="mail_notification")
    message = template.render({
            'title': safe_unicode(content_object.title),
            'link': content_object.absolute_url() +
                    '/view#' + obj.id,
            'text': obj.text
    })
    for email in emails:
        # Send email
        try:
            mail_host.send(message, email, sender, subject, charset='utf-8')
        except SMTPException:
            logger.error('SMTP exception while trying to send an ' +
                         'email from %s to %s',
                         sender,
                         email)


def get_nosy_members(context, ls):
    """ Identify the chosen groups and return their members as well as the
        individually chosen members (while removing duplicates).
    """
    pg = getToolByName(context, 'portal_groups')
    mt = getToolByName(context, 'portal_membership')
    groups = pg.getGroupIds()
    chosen_groups = list(set(ls).intersection(set(groups)))
    chosen_members = list(set(ls).difference(set(groups)))
    for g in chosen_groups:
        chosen_members += pg.getGroupById(g).getGroupMemberIds()
    return [mt.getMemberById(m) for m in list(set(chosen_members))]


# Event handler for IObjectAddedEvent and IObjectModifiedEvent to let all
# nosy know of changes to the question object.
def notify_nosy(obj, event):
    """ Give the nosy list access to the question. Then tell them about the new
        question. """
    request = getattr(obj, 'REQUEST', None)
    if not request:
        return
    if not ISlcUnderflow.providedBy(request):
        return

    # Get info necessary to send email
    mail_host = getToolByName(obj, 'MailHost')
    portal_url = getToolByName(obj, 'portal_url')
    membership = getToolByName(obj, 'portal_membership')

    portal = portal_url.getPortalObject()
    member = api.user.get_current()
    user_id = member.getId()
    username = member.getProperty('fullname')

    settings = getSettings()
    if settings is None or settings.sender is None:
        sender = portal.getProperty('email_from_address')
        if not sender:
            registry = component.getUtility(IRegistry)
            mail_settings = registry.forInterface(IMailSchema, prefix='plone')
            sender = mail_settings.email_from_address
    else:
        sender = settings.sender

    # Check if a sender address is available
    if not sender:
        return

    # Add Reader role on any nosy principals, remove from non-selected ones.
    disown = []

    for principal, roles in obj.get_local_roles():
        if principal not in obj.nosy:
            disown.append(principal)

    for principal in obj.nosy:
        obj.manage_addLocalRoles(principal, ['Reader'])

    if disown:
        obj.manage_delLocalRoles(disown)

    emails = set()
    groups_tool = getToolByName(obj, 'portal_groups')
    members = get_nosy_members(obj, obj.nosy)
    for member in members:
        if member is not None:
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
        subject = translate(u"A question has been modified in ${container} [${uid}]",
            mapping={'uid': IUUID(obj),
                     'container': safe_unicode(obj.aq_parent.Title())},
            context=obj.REQUEST)
    else:
        if obj.inforequest:
            subject = translate(u"Response required: StarDesk Message from ${username}",
                mapping={'username': safe_unicode(username or user_id)},
                context=obj.REQUEST)
        else:
            subject = translate(u"StarDesk Message from ${username} to ${container} members",
                mapping={'username': safe_unicode(username or user_id),
                         'container': safe_unicode(obj.aq_parent.Title())},
                context=obj.REQUEST)

    if obj.inforequest:
        template = component.getMultiAdapter((obj, obj.REQUEST),
                name="mail_notification_nosy_inforequest")
    else:
        template = component.getMultiAdapter((obj, obj.REQUEST),
                name="mail_notification_nosy")

    message = template.render({
        'username': safe_unicode(username or user_id),
        'title': safe_unicode(obj.title),
        'link': obj.absolute_url(),
        'text': safe_unicode(text),
        'container': obj.aq_parent.Title()
    })
    # remove the current user from the notification, he doesn't need to receive
    # it, he asked in the first place
    for email in emails:
        # Send email
        try:
            mail_host.send(message, email, sender, subject, charset='utf-8')
        except SMTPException:
            logger.error('SMTP exception while trying to send an ' +
                         'email from %s to %s',
                         sender,
                         email)


def pester_answerer(event):
    # Place an annotation on the member that will cause sticky-status messages
    # to display a notice

    # Not implemented
    return

