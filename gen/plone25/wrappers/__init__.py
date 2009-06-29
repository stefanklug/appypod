'''This package contains base classes for wrappers that hide to the Appy
   developer the real classes used by the undelrying web framework.'''

# ------------------------------------------------------------------------------
import time

# ------------------------------------------------------------------------------
class AbstractWrapper:
    '''Any real web framework object has a companion object that is an instance
       of this class.'''
    def __init__(self, o):
        self.__dict__['o'] = o
    def __setattr__(self, name, v):
        exec "self.o.set%s%s(v)" % (name[0].upper(), name[1:])
    def __cmp__(self, other):
        if other:
            return cmp(self.o, other.o)
        else:
            return 1
    def get_tool(self):
        return self.o.getTool()._appy_getWrapper(force=True)
    tool = property(get_tool)
    def get_session(self):
        return self.o.REQUEST.SESSION
    session = property(get_session)
    def get_typeName(self):
        return self.__class__.__bases__[-1].__name__
    typeName = property(get_typeName)
    def get_id(self):
        return self.o.id
    id = property(get_id)
    def get_state(self):
        return self.o.portal_workflow.getInfoFor(self.o, 'review_state')
    state = property(get_state)
    def get_stateLabel(self):
        appName = self.o.getProductConfig().PROJECTNAME
        return self.o.utranslate(self.o.getWorkflowLabel(), domain=appName)
    stateLabel = property(get_stateLabel)
    def get_klass(self):
        return self.__class__.__bases__[1]
    klass = property(get_klass)

    def link(self, fieldName, obj):
        '''This method links p_obj to this one through reference field
           p_fieldName.'''
        if isinstance(obj, AbstractWrapper):
            obj = obj.o
        postfix = 'et%s%s' % (fieldName[0].upper(), fieldName[1:])
        # Update the Archetypes reference field
        exec 'objs = self.o.g%s()' % postfix
        if not objs:
            objs = []
        elif type(objs) not in (list, tuple):
            objs = [objs]
        objs.append(obj)
        exec 'self.o.s%s(objs)' % postfix
        # Update the ordered list of references
        sortedRefField = '_appy_%s' % fieldName
        if not hasattr(self.o.aq_base, sortedRefField):
            exec 'self.o.%s = self.o.getProductConfig().PersistentList()' % \
                 sortedRefField
        getattr(self.o, sortedRefField).append(obj.UID())

    def create(self, fieldName, **kwargs):
        '''This method allows to create an object and link it to the current
           one through reference field named p_fieldName.'''
        # Determine object id and portal type
        portalType = self.o.getAppyRefPortalType(fieldName)
        if kwargs.has_key('id'):
            objId = kwargs['id']
            del kwargs['id']
        else:
            objId = '%s.%f' % (fieldName, time.time())
        # Where must I create te object?
        if hasattr(self, 'folder') and self.folder:
            folder = self.o
        else:
            folder = self.o.getParentNode()
        # Create the object
        folder.invokeFactory(portalType, objId)
        ploneObj = getattr(folder, objId)
        appyObj = ploneObj._appy_getWrapper(force=True)
        # Set object attributes
        ploneObj._appy_manageSortedRefs()
        for attrName, attrValue in kwargs.iteritems():
            setterName = 'set%s%s' % (attrName[0].upper(), attrName[1:])
            if isinstance(attrValue, AbstractWrapper):
                try:
                    refAppyType = getattr(appyObj.__class__.__bases__[-1],
                                          attrName)
                    appyObj.link(attrName, attrValue.o)
                except AttributeError, ae:
                    pass
            else:
                getattr(ploneObj, setterName)(attrValue)
        # Link the object to this one
        self.link(fieldName, ploneObj)
        try:
            appyObj.onEdit(True) # Call custom initialization
        except AttributeError:
            pass
        self.o.reindexObject()
        ploneObj.reindexObject()
        return appyObj

    def translate(self, label, mapping={}, domain=None):
        if not domain: domain = self.o.getProductConfig().PROJECTNAME
        return self.o.utranslate(label, mapping, domain=domain)

    def do(self, transition, comment='', doAction=False, doNotify=False):
        '''This method allows to trigger on p_self a workflow p_transition
           programmatically. If p_doAction is False, the action that must
           normally be executed after the transition has been triggered will
           not be executed. If p_doNotify is False, the notifications
           (email,...) that must normally be launched after the transition has
           been triggered will not be launched.'''
        wfTool = self.o.portal_workflow
        availableTransitions = [t['id'] for t in \
                                wfTool.getTransitionsFor(self.o)]
        transitionName = transition
        if not transitionName in availableTransitions:
            # Maybe is is a compound Appy transition. Try to find the
            # corresponding DC transition.
            state = self.state
            transitionPrefix = transition + state[0].upper() + state[1:] + 'To'
            for at in availableTransitions:
                if at.startswith(transitionPrefix):
                    transitionName = at
                    break
        # Set in a versatile attribute details about what to execute or not
        # (actions, notifications) after the transition has been executed by DC
        # workflow.
        self.o._v_appy_do = {'doAction': doAction, 'doNotify': doNotify}
        wfTool.doActionFor(self.o, transitionName, comment=comment)
        del self.o._v_appy_do
# ------------------------------------------------------------------------------
