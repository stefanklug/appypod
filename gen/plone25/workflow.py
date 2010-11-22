'''This package contains functions for managing workflow events.'''

# ------------------------------------------------------------------------------
class WorkflowCreator:
    '''This class allows to construct the Plone workflow that corresponds to a
       Appy workflow.'''

    def __init__(self, wfName, ploneWorkflowClass, stateNames, initialState,
        stateInfos, transitionNames, transitionInfos, managedPermissions,
        productName, externalMethodClass):
        self.wfName = wfName
        self.ploneWorkflowClass = ploneWorkflowClass
        self.stateNames = stateNames
        self.initialState = initialState # Name of the initial state
        self.stateInfos = stateInfos
        # stateInfos is a dict giving information about every state. Keys are
        # state names, values are lists? Every list contains (in this order):
        # - the list of transitions (names) going out from this state;
        # - a dict of permissions, whose keys are permission names and whose
        #   values are lists of roles that are granted this permission. In
        # short: ~{s_stateName: ([transitions], {s_permissionName:
        #                                        (roleNames)})}~.
        self.transitionNames = transitionNames
        self.transitionInfos = transitionInfos
        # transitionInfos is a dict giving information avout every transition.
        # Keys are transition names, values are end states of the transitions.
        self.variableInfos = {
            'review_history': ("Provides access to workflow history",
                'state_change/getHistory', 0, 0, {'guard_permissions':\
                'Request review; Review portal content'}),
            'comments': ("Comments about the last transition",
                 'python:state_change.kwargs.get("comment", "")', 1, 1, None),
            'time': ("Time of the last transition", "state_change/getDateTime",
                1, 1, None),
            'actor': ("The ID of the user who performed the last transition",
                 "user/getId", 1, 1, None),
            'action': ("The last transition", "transition/getId|nothing",
                1, 1, None)
        }
        self.managedPermissions = managedPermissions
        self.ploneWf = None # The Plone DC workflow definition
        self.productName = productName
        self.externalMethodClass = externalMethodClass

    def createWorkflowDefinition(self):
        '''Creates the Plone instance corresponding to this workflow.'''
        self.ploneWf = self.ploneWorkflowClass(self.wfName)
        self.ploneWf.setProperties(title=self.wfName)

    def createWorkflowElements(self):
        '''Creates states, transitions, variables and managed permissions and
           sets the initial state.'''
        wf = self.ploneWf
        # Create states
        for s in self.stateNames:
            try:
                wf.states[s]
            except KeyError, k:
                # It does not exist, so we create it!
                wf.states.addState(s)
        # Create transitions
        for t in self.transitionNames:
            try:
                wf.transitions[t]
            except KeyError, k:
                wf.transitions.addTransition(t)
        # Create variables
        for v in self.variableInfos.iterkeys():
            try:
                wf.variables[v]
            except KeyError, k:
                wf.variables.addVariable(v)
        # Create managed permissions
        for mp in self.managedPermissions:
            try:
                wf.addManagedPermission(mp)
            except ValueError, va:
                pass # Already a managed permission
        # Set initial state
        if not wf.initial_state: wf.states.setInitialState(self.initialState)

    def getTransitionScriptName(self, transitionName):
        '''Gets the name of the script corresponding to DC p_transitionName.'''
        return '%s_do%s%s' % (self.wfName, transitionName[0].upper(),
                              transitionName[1:])

    def configureStatesAndTransitions(self):
        '''Configures states and transitions of the Plone workflow.'''
        wf = self.ploneWf
        # Configure states
        for stateName, stateInfo in self.stateInfos.iteritems():
            state = wf.states[stateName]
            stateTitle = '%s_%s' % (self.wfName, stateName)
            state.setProperties(title=stateTitle, description="",
                                transitions=stateInfo[0])
            for permissionName, roles in stateInfo[1].iteritems():
                state.setPermission(permissionName, 0, roles)
        # Configure transitions
        for transitionName, endStateName in self.transitionInfos.iteritems():
            # Define the script to call when the transition has been triggered.
            scriptName = self.getTransitionScriptName(transitionName)
            if not scriptName in wf.scripts.objectIds():
                sn = scriptName
                wf.scripts._setObject(sn, self.externalMethodClass(
                    sn, sn, self.productName + '.workflows', sn))
            # Configure the transition in itself
            transition = wf.transitions[transitionName]
            transition.setProperties(
                title=transitionName, new_state_id=endStateName, trigger_type=1,
                script_name="", after_script_name=scriptName,
                actbox_name='%s_%s' % (self.wfName, transitionName),
                actbox_url="",
                props={'guard_expr': 'python:here.may("%s")' % transitionName})

    def configureVariables(self):
        '''Configures the variables defined in this workflow.'''
        wf = self.ploneWf
        # Set the name of the state variable
        wf.variables.setStateVar('review_state')
        # Configure the variables
        for variableName, info in self.variableInfos.iteritems():
            var = wf.variables[variableName]
            var.setProperties(description=info[0], default_value='',
                default_expr=info[1], for_catalog=0, for_status=info[2],
                update_always=info[3], props=info[4])

    def run(self):
        self.createWorkflowDefinition()
        self.createWorkflowElements()
        self.configureStatesAndTransitions()
        self.configureVariables()
        return self.ploneWf

# ------------------------------------------------------------------------------
import notifier
def do(transitionName, stateChange, logger):
    '''This function is called by a Plone workflow every time a transition named
       p_transitionName has been triggered. p_stateChange.objet is the Plone
       object on which the transition has been triggered; p_logger is the Zope
       logger allowing to dump information, warnings or errors in the log file
       or object.'''
    ploneObj = stateChange.object
    workflow = ploneObj.getWorkflow()
    transition = workflow._transitionsMapping[transitionName]
    msg = ''
    # Must I execute transition-related actions and notifications?
    doAction = False
    if transition.action:
        doAction = True
        if hasattr(ploneObj, '_v_appy_do') and \
           not ploneObj._v_appy_do['doAction']:
            doAction = False
    doNotify = False
    if transition.notify:
        doNotify = True
        if hasattr(ploneObj, '_v_appy_do') and \
           not ploneObj._v_appy_do['doNotify']:
            doNotify = False
        elif not getattr(ploneObj.getTool().appy(), 'enableNotifications'):
            # We do not notify if the "notify" flag in the tool is disabled.
            doNotify = False
    if doAction or doNotify:
        obj = ploneObj.appy()
        if doAction:
            msg = ''
            if type(transition.action) in (tuple, list):
                # We need to execute a list of actions
                for act in transition.action:
                    msgPart = act(workflow, obj)
                    if msgPart: msg += msgPart
            else: # We execute a single action only.
                msgPart = transition.action(workflow, obj)
                if msgPart: msg += msgPart
        if doNotify:
            notifier.sendMail(obj, transition, transitionName, workflow, logger)
    # Produce a message to the user
    if hasattr(ploneObj, '_v_appy_do') and not ploneObj._v_appy_do['doSay']:
        # We do not produce any message if the transition was triggered
        # programmatically.
        return
    # Produce a default message if no transition has given a custom one.
    if not msg:
        msg = ploneObj.translate(u'Your content\'s status has been modified.',
                                 domain='plone')
    ploneObj.plone_utils.addPortalMessage(msg)
# ------------------------------------------------------------------------------
