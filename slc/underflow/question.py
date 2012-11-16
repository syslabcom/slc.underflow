from five import grok
from zope import schema
from z3c.form.interfaces import INPUT_MODE

from plone.directives import dexterity, form
from plone.indexer import indexer

from plone.app.textfield import RichText
from plone.app.discussion.browser.comments import CommentForm as \
    BaseCommentForm
from plone.app.discussion.browser.comments import CommentsViewlet as \
    BaseCommentsViewlet

from Products.CMFCore.utils import getToolByName
from Products.ZCatalog.interfaces import IZCatalog
from Products.UserAndGroupSelectionWidget.z3cform.widget import \
                                        UsersAndGroupsSelectionFieldWidget

from slc.underflow import MessageFactory as _

class IQuestion(form.Schema):
    """ A question """
    question = RichText(
        title=_(u"Question"),
        required=True)

    inforequest = schema.Bool(
        title=_(u"Information Request"),
        required=False)

    nosy = schema.List(
        title=_(u"Audience"),
        default=[],
        value_type=schema.TextLine())
    form.widget(nosy=UsersAndGroupsSelectionFieldWidget)

class Question(dexterity.Item):
    grok.implements(IQuestion)

    def __call__(self):
        return self


class CommentForm(BaseCommentForm):
    def updateWidgets(self):
        super(CommentForm, self).updateWidgets()
        # Re-enable the user_notification checkbox
        mtool = getToolByName(self.context, 'portal_membership')
        member = mtool.getAuthenticatedMember()
        if not (mtool.isAnonymousUser() or member.getProperty('email')==''):
            self.widgets['user_notification'].mode = INPUT_MODE

class CommentsViewlet(BaseCommentsViewlet):
    form = CommentForm

@indexer(IQuestion, IZCatalog)
def inforequest(ob):
    return ob.inforequest
