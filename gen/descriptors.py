# ------------------------------------------------------------------------------
from appy.gen import State, Transition, Type

# ------------------------------------------------------------------------------
class Descriptor: # Abstract
    def __init__(self, klass, orderedAttributes, generator):
        # The corresponding Python class
        self.klass = klass
        # The names of the static appy-compliant attributes declared in
        # self.klass
        self.orderedAttributes = orderedAttributes
        # A reference to the code generator.
        self.generator = generator

    def __repr__(self): return '<Class %s>' % self.klass.__name__

class ClassDescriptor(Descriptor):
    '''This class gives information about an Appy class.'''
    def getOrderedAppyAttributes(self, condition=None):
        '''Returns the appy types for all attributes of this class and parent
           class(es). If a p_condition is specified, ony Appy types matching
           the condition will be returned. p_condition must be a string
           containing an expression that will be evaluated with, in its context,
           "self" being this ClassDescriptor and "attrValue" being the current
           Type instance.
           
           Order of returned attributes already takes into account type's
           "move" attributes.'''
        attrs = []
        # First, get the attributes for the current class
        for attrName in self.orderedAttributes:
            try:
                attrValue = getattr(self.klass, attrName)
                hookClass = self.klass
            except AttributeError:
                attrValue = getattr(self.modelClass, attrName)
                hookClass = self.modelClass
            if isinstance(attrValue, Type):
                if not condition or eval(condition):
                    attrs.append( (attrName, attrValue, hookClass) )
        # Then, add attributes from parent classes
        for baseClass in self.klass.__bases__:
            # Find the classDescr that corresponds to baseClass
            baseClassDescr = None
            for classDescr in self.generator.classes:
                if classDescr.klass == baseClass:
                    baseClassDescr = classDescr
                    break
            if baseClassDescr:
                attrs = baseClassDescr.getOrderedAppyAttributes() + attrs
        # Modify attributes order by using "move" attributes
        res = []
        for name, appyType, klass in attrs:
            if appyType.move:
                newPosition = len(res) - abs(appyType.move)
                if newPosition <= 0:
                    newPosition = 0
                res.insert(newPosition, (name, appyType, klass))
            else:
                res.append((name, appyType, klass))
        return res

    def getChildren(self):
        '''Returns, among p_allClasses, the classes that inherit from p_self.'''
        res = []
        for classDescr in self.generator.classes:
            if (classDescr.klass != self.klass) and \
               issubclass(classDescr.klass, self.klass):
                res.append(classDescr)
        return res

    def getPhases(self):
        '''Gets the phases defined on fields of this class.'''
        res = []
        for fieldName, appyType, klass in self.getOrderedAppyAttributes():
            if appyType.phase not in res:
                res.append(appyType.phase)
        return res

class WorkflowDescriptor(Descriptor):
    '''This class gives information about an Appy workflow.'''

    def _getWorkflowElements(self, elemType):
        res = []
        for attrName in dir(self.klass):
            attrValue = getattr(self.klass, attrName)
            condition = False
            if elemType == 'states':
                condition = isinstance(attrValue, State)
            elif elemType == 'transitions':
                condition = isinstance(attrValue, Transition)
            elif elemType == 'all':
                condition = isinstance(attrValue, State) or \
                            isinstance(attrValue, Transition)
            if condition:
                res.append(attrValue)
        return res

    def getStates(self):
        return self._getWorkflowElements('states')

    def getTransitions(self):
        return self._getWorkflowElements('transitions')

    def getStateNames(self, ordered=False):
        res = []
        attrs = dir(self.klass)
        allAttrs = attrs
        if ordered:
            attrs = self.orderedAttributes
            allAttrs = dir(self.klass)
        for attrName in attrs:
            attrValue = getattr(self.klass, attrName)
            if isinstance(attrValue, State):
                res.append(attrName)
        # Complete the list with inherited states. For the moment, we are unable
        # to sort inherited states.
        for attrName in allAttrs:
            attrValue = getattr(self.klass, attrName)
            if isinstance(attrValue, State) and (attrName not in attrs):
                res.insert(0, attrName)
        return res

    def getInitialStateName(self):
        res = None
        for attrName in dir(self.klass):
            attrValue = getattr(self.klass, attrName)
            if isinstance(attrValue, State) and attrValue.initial:
                res = attrName
                break
        return res

    def getTransitionNamesOf(self, transitionName, transition,
                             limitToFromState=None):
        '''Appy p_transition may correspond to several transitions of the
           concrete workflow engine used. This method returns in a list the
           name(s) of the "concrete" transition(s) corresponding to
           p_transition.'''
        res = []
        if transition.isSingle():
            res.append(transitionName)
        else:
            for fromState, toState in transition.states:
                if not limitToFromState or \
                   (limitToFromState and (fromState == limitToFromState)):
                    fromStateName = self.getNameOf(fromState)
                    toStateName = self.getNameOf(toState)
                    res.append('%s%s%sTo%s%s' % (transitionName,
                        fromStateName[0].upper(), fromStateName[1:],
                        toStateName[0].upper(), toStateName[1:]))
        return res

    def getTransitionNames(self, limitToTransitions=None, limitToFromState=None,
                           withLabels=False):
        '''Returns the name of all "concrete" transitions corresponding to the
           Appy transitions of this worlflow. If p_limitToTransitions is not
           None, it represents a list of Appy transitions and the result is a
           list of the names of the "concrete" transitions that correspond to
           those transitions only. If p_limitToFromState is not None, it
           represents an Appy state; only transitions having this state as start
           state will be taken into account. If p_withLabels is True, the method
           returns a list of tuples (s_transitionName, s_transitionLabel); the
           label being the name of the Appy transition.'''
        res = []
        for attrName in dir(self.klass):
            attrValue = getattr(self.klass, attrName)
            if isinstance(attrValue, Transition):
                # We encountered a transition.
                t = attrValue
                tName = attrName
                if not limitToTransitions or \
                   (limitToTransitions and t in limitToTransitions):
                    # We must take this transition into account according to
                    # param "limitToTransitions".
                    if (not limitToFromState) or \
                       (limitToFromState and \
                        t.hasState(limitToFromState, isFrom=True)):
                        # We must take this transition into account according
                        # to param "limitToFromState"
                        tNames = self.getTransitionNamesOf(
                            tName, t, limitToFromState)
                        if not withLabels:
                            res += tNames
                        else:
                            for tn in tNames:
                                res.append((tn, tName))
        return res

    def getEndStateName(self, transitionName):
        '''Returns the name of the state where the "concrete" transition named
           p_transitionName ends.'''
        res = None
        for attrName in dir(self.klass):
            attrValue = getattr(self.klass, attrName)
            if isinstance(attrValue, Transition):
                # We got a transition.
                t = attrValue
                tName = attrName
                if t.isSingle():
                    if transitionName == tName:
                        endState = t.states[1]
                        res = self.getNameOf(endState)
                else:
                    transNames = self.getTransitionNamesOf(tName, t)
                    if transitionName in transNames:
                        endState = t.states[transNames.index(transitionName)][1]
                        res = self.getNameOf(endState)
        return res

    def getNameOf(self, stateOrTransition):
        '''Gets the Appy name of a p_stateOrTransition.'''
        res = None
        for attrName in dir(self.klass):
            attrValue = getattr(self.klass, attrName)
            if attrValue == stateOrTransition:
                res = attrName
                break
        return res
# ------------------------------------------------------------------------------
