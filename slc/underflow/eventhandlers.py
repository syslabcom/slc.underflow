from Acquisition import aq_parent
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from datetime import datetime
from plone.uuid.interfaces import IUUID
from plone import api
from slc.stickystatusmessages.config import SSMKEY
from slc.underflow import MessageFactory as _
from slc.underflow.interfaces import ISlcUnderflow
from slc.underflow.settings import getSettings
from smtplib import SMTPException
from zope.annotation.interfaces import IAnnotations
from zope.i18n import interpolate
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
    """ The UserAndGroupSelectionWidget can return users and groups.

        Identify the chosen groups and return their members as well as the
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
            if email != '' and email != user_id:
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
                     'container': obj.aq_parent.Title()},
            context=obj.REQUEST)
    else:
        if obj.inforequest:
            subject = translate(u"Response required: StarDesk Message from ${username}",
                mapping={'username': username or user_id},
                context=obj.REQUEST)
        else:
            subject = translate(u"StarDesk Message from ${username} to ${container} members",
                mapping={'username': username or user_id,
                         'container': obj.aq_parent.Title()},
                context=obj.REQUEST)

    if obj.inforequest:
        template = component.getMultiAdapter((obj, obj.REQUEST),
                name="mail_notification_nosy_inforequest")
    else:
        template = component.getMultiAdapter((obj, obj.REQUEST),
                name="mail_notification_nosy")

    message = template.render({
        'username': username or user_id,
        'title': safe_unicode(obj.title),
        'link': obj.absolute_url(),
        'text': safe_unicode(text),
        'container': obj.aq_parent.Title()
    })
    # remove the current user from the notification, he doesn't need to receive it, he asked in the first place
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

    # Stubbing out this method for a demo
    return

    request = getattr(event.object, 'REQUEST', None)
    if not request:
        return
    if not ISlcUnderflow.providedBy(request):
        return

    try:
        pm = getToolByName(event.object, 'portal_membership')
    except AttributeError:
        # seldom case of zope user in event.object that cannot acquire portal tools
        return
    pc = getToolByName(event.object, 'portal_catalog')
    userid = event.object.getUserId()
    member = pm.getMemberById(userid)

    # Find questions we need to answer
    brains = pc(portal_type='slc.underflow.question', inforequest=True)

    for brain in brains:
        if userid not in brain.commentators:
            # XXX This code really belongs in some utililty inside
            # slc.stickystatusmessages
            timestamp = datetime.now().isoformat()
            annotations = IAnnotations(member)
            sticky_messages = annotations.get(SSMKEY, {})

            mapping = { 'u': brain.getURL() }
            msg = _(u'An information request is waiting for your response. '
                u'Click <a href="${u}">here</a> to respond to it now.')
            msg = interpolate(msg, mapping)

            mdict= {
                'type': 'info',
                'message': msg,
                'timestamp': timestamp,
                }
            sticky_messages[timestamp] = mdict
            annotations[SSMKEY] = sticky_messages
