from zope.schema import Datetime
from plone.app.textfield import RichText
from plone.directives import form
from slc.underflow import MessageFactory as _

class IQuestion(form.Schema):
    """ A question """

    question = RichText(
        title=_(u"Question"),
        required=True
    )
