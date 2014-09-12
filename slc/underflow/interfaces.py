from zope.interface import Interface
from zope.schema import TextLine
from plone.app.discussion.interfaces import IDiscussionLayer
from slc.underflow import MessageFactory as _


class ISlcUnderflow(IDiscussionLayer):
    """ Browser Layer interface. """


class ISettings(Interface):
    sender = TextLine(
        title=_(u"Sender address"),
        description=_(u"Enter the email address to use as the sender address "
            u"for outgoing notifications."),
        required=True)
