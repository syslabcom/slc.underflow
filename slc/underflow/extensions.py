from persistent import Persistent
from z3c.form.field import Fields
from zope.schema import Bool
from zope.annotation import factory
from zope.component import adapts
from zope.interface import Interface, implements
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from plone.z3cform.fieldsets.extensible import FormExtender

from plone.app.discussion.browser.comments import CommentForm
from plone.app.discussion.comment import Comment

from slc.underflow import MessageFactory as _

# Interface to define the fields we want to add to the comment form.
class IExtraFields(Interface):
    notify = Bool(title=_(u"Notify me of follow-up comments"), required=False)

class ExtraFields(Persistent):
    implements(IExtraFields)
    adapts(Comment)
    notify = False

CommentExtenderFactory = factory(ExtraFields)

class CommentExtender(FormExtender):
    adapts(Interface, IDefaultBrowserLayer, CommentForm)

    fields = Fields(IExtraFields)

    def __init__(self, context, request, form):
        self.context = context
        self.request = request
        self.form = form

    def update(self):
        self.add(IExtraFields, prefix="")
