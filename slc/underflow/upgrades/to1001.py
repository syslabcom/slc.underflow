# coding=utf-8
from logging import getLogger
from plone import api


logger = getLogger(__name__)


def fix_behaviors(context):
    """ We want to remove the behavior
    plone.app.referenceablebehavior.referenceable.IReferenceable
    because we do not have any AT object to reference
    """
    pt = api.portal.get_tool("portal_types")
    banned = "plone.app.referenceablebehavior.referenceable.IReferenceable"
    ftiid = "slc.underflow.question"
    fti = pt[ftiid]
    if banned in fti.behaviors:
        logger.info("Removed %r from %r", banned, ftiid)
        fti.behaviors = tuple(b for b in fti.behaviors if b != banned)
