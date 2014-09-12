from five import grok
from slc.underflow.question import IQuestion
from slc.underflow.interfaces import ISlcUnderflow
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

grok.templatedir("templates")


class ConversationView(grok.View):
    """ View for question objects that always enables commenting. """
    grok.name("conversation_view")
    grok.context(IQuestion)
    grok.layer(ISlcUnderflow)
    grok.require("zope2.View")

    def enabled(self):
        return True

    def render(self):
        return ''


class InfoRequestNotificationEmail(grok.View):
    grok.name("mail_notification_nosy_inforequest")
    grok.context(IQuestion)
    grok.require("zope2.View")
    grok.layer(ISlcUnderflow)

    def render(self, options):
        self.options = options
        return ViewPageTemplateFile('templates/mail_notification_nosy_inforequest.pt')(self)


class NotificationEmail(grok.View):
    grok.name("mail_notification_nosy")
    grok.context(IQuestion)
    grok.require("zope2.View")
    grok.layer(ISlcUnderflow)

    def render(self, options):
        self.options = options
        return ViewPageTemplateFile('templates/mail_notification_nosy.pt')(self)
