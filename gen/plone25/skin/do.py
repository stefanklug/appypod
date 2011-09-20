## Python Script "do.py"
##bind context=context
##parameters=action
rq = context.REQUEST

# Get the object impacted by the action.
if rq.get('objectUid', None):
    obj = context.portal_catalog(UID=rq['objectUid'])[0].getObject()
else:
    obj = context.getParentNode() # An appy obj or in some cases the app folder.
    if obj.portal_type == 'AppyFolder':
        from Products.CMFCore.utils import getToolByName
        portal = getToolByName(obj, 'portal_url').getPortalObject()
        obj = portal.get('portal_%s' % obj.id.lower()) # The tool
return obj.getMethod('on'+action)()
