class ConversationView(object):
    """ View for question objects that always enables commenting. """

    def enabled(self):
        return True
