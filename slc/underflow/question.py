from zope.schema import Datetime, Bool, Set, Choice
from z3c.form.interfaces import INPUT_MODE
from plone.app.textfield import RichText
from plone.directives import form
from plone.app.discussion.browser.comments import CommentForm as \
    BaseCommentForm
from plone.app.discussion.browser.comments import CommentsViewlet as \
    BaseCommentsViewlet
from Products.CMFCore.utils import getToolByName
from slc.underflow import MessageFactory as _

class IQuestion(form.Schema):
    """ A question """

    question = RichText(
        title=_(u"Question"),
        required=True)
    inforequest = Bool(
        title=_(u"Information Request"),
        required=False)
    nosy = Set(
        title=_(u"Audience"),
        value_type=Choice(vocabulary="plone.principalsource.Groups"))

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
