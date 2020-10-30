from Products.Five import BrowserView


class ConversationView(BrowserView):
    """ View for question objects that always enables commenting. """

    def enabled(self):
        return True

    def __call__(self):
        return ''


class NotificationMessage(BrowserView):

    def render(self, options):
        self.options = options
        return self.index()


class NosyInfoRequestNotificationEmail(BrowserView):

    def render(self, options):
        self.options = options
        return self.index()


class NosyNotificationEmail(BrowserView):

    def render(self, options):
        self.options = options
        return self.index()
