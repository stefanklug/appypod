## Python Script "do.py"
##bind context=context
##parameters=action
rq = context.REQUEST
urlBack = rq['HTTP_REFERER']

if action == 'create':
    # A user wants to create an object.
    if rq.get('initiator', None):
        # The object to create will be linked to an initiator object through a
        # ref field.
        initiatorRes= context.uid_catalog.searchResults(UID=rq.get('initiator'))
        rq.SESSION['initiator'] = rq.get('initiator')
        rq.SESSION['initiatorField'] = rq.get('field')
        rq.SESSION['initiatorTarget'] = rq.get('type_name')
    objId = context.generateUniqueId(rq.get('type_name'))
    urlBack = '%s/portal_factory/%s/%s/skyn/edit' % \
        (context.getParentNode().absolute_url(), rq.get('type_name'), objId)

elif action == 'edit': return context.getParentNode().onUpdate()

elif action == 'appyAction':
    obj = context.uid_catalog(UID=rq['objectUid'])[0].getObject()
    res, msg = obj.executeAppyAction(rq['fieldName'])
    if not msg:
        # Use the default i18n messages
        suffix = 'ko'
        if res:
            suffix = 'ok'
        label = '%s_action_%s' % (obj.getLabelPrefix(rq['fieldName']), suffix)
        msg = obj.translate(label)
    context.plone_utils.addPortalMessage(msg)

elif action == 'changeRefOrder':
    # Move the item up (-1), down (+1) or at a given position ?
    obj = context.getParentNode()
    move = -1 # Move up
    isDelta = True
    if rq.get('moveDown.x', None) != None:
        move = 1 # Move down
    elif rq.get('moveSeveral.x', None) != None:
        try:
            move = int(rq.get('moveValue'))
            # In this case, it is not a delta value; it is the new position where
            # the item must be moved.
            isDelta = False
        except ValueError:
            context.plone_utils.addPortalMessage(
                obj.translate('ref_invalid_index'))
    obj.changeAppyRefOrder(rq['fieldName'], rq['objectUid'], move, isDelta)

elif action == 'triggerTransition':
    obj = context.getParentNode()
    from Products.CMFPlone import PloneMessageFactory as _
    context.portal_workflow.doActionFor(obj, rq['workflow_action'],
                                        comment=rq.get('comment', ''))
    if urlBack.find('?') != -1:
        # Remove params; this way, the user may be redirected to correct phase
        # when relevant.
        urlBack = urlBack[:urlBack.find('?')]
    context.plone_utils.addPortalMessage(
        _(u'Your content\'s status has been modified.'))

return rq.RESPONSE.redirect(urlBack)
