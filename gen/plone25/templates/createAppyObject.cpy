## Controller Python Script "createAppyObject"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=initiator, field, type_name
##title=createAppyObject
##
if not initiator or not field:
    raise Exception, 'You must specify the uid of the object that initiates ' \
                     'this creation in the "initiator" parameter and the ' \
                     'related field in the "field" param.'

if not type_name:
    raise Exception, 'You must specify the target type name in the "type_name" ' \
                     'parameter.'

initiatorRes = context.uid_catalog.searchResults(UID=initiator)
if not initiatorRes:
    raise Exception, 'Given initiator UID does not correspond to a valid object.'

context.REQUEST.SESSION['initiator'] = initiator
context.REQUEST.SESSION['initiatorField'] = field
context.REQUEST.SESSION['initiatorTarget'] = type_name
return state.set(status='success')
