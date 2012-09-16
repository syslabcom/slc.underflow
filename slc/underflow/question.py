from zope.schema import Datetime, Bool, Set, Choice
from plone.app.textfield import RichText
from plone.directives import form
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
        title=_(u"Send question to"),
        value_type=Choice(vocabulary="plone.principalsource.Groups"))
