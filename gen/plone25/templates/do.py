## Python Script "<!applicationName!>_do.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=actionType
##title=Executes an action
rq = context.REQUEST
urlBack = rq['HTTP_REFERER']

if actionType == 'appyAction':
    obj = context.uid_catalog(UID=rq['objectUid'])[0].getObject()
    res, msg = obj.executeAppyAction(rq['fieldName'])
    if not msg:
        # Use the default i18n messages
        suffix = 'ko'
        if res:
            suffix = 'ok'
        label = '%s_action_%s' % (obj.getLabelPrefix(rq['fieldName']), suffix)
        msg = context.utranslate(label, domain='<!applicationName!>')
    context.plone_utils.addPortalMessage(msg)

elif actionType == 'changeRefOrder':
    # Move the item up (-1), down (+1) or at a given position ?
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
                context.utranslate('ref_invalid_index', domain='<!applicationName!>'))
    context.changeAppyRefOrder(rq['fieldName'], rq['objectUid'], move, isDelta)

elif actionType == 'triggerTransition':
    from Products.CMFPlone import PloneMessageFactory as _
    context.portal_workflow.doActionFor(context, rq['workflow_action'],
                                        comment=rq.get('comment', ''))
    if urlBack.find('?') != -1:
        # Remove params; this way, the user may be redirected to correct phase
        # when relevant.
        urlBack = urlBack[:urlBack.find('?')]
    context.plone_utils.addPortalMessage(_(u'Your content\'s status has been modified.'))

return rq.RESPONSE.redirect(urlBack)
