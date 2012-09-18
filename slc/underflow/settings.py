from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from slc.underflow.interfaces import ISettings
from slc.underflow import MessageFactory as _

class UnderflowSettings(RegistryEditForm):
    schema = ISettings
    label = _(u"Underflow Settings")
    description = _(u"Use the settings below to configure "
                    u"slc.underflow for this site")

class UnderflowControlPanel(ControlPanelFormWrapper):
    form = UnderflowSettings
