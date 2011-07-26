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
        '''Lazy-gets the phases defined on fields of this class.'''
        if not hasattr(self, 'phases') or (self.phases == None):
            self.phases = []
            for fieldName, appyType, klass in self.getOrderedAppyAttributes():
                if appyType.page.phase in self.phases: continue
                self.phases.append(appyType.page.phase)
        return self.phases

    def getPages(self):
        '''Lazy-gets the page names defined on fields of this class.'''
        if not hasattr(self, 'pages') or (self.pages == None):
            self.pages = []
            for fieldName, appyType, klass in self.getOrderedAppyAttributes():
                if appyType.page.name in self.pages: continue
                self.pages.append(appyType.page.name)
        return self.pages

class WorkflowDescriptor(Descriptor):
    '''This class gives information about an Appy workflow.'''
    @staticmethod
    def getWorkflowName(klass):
        '''Returns the name of this workflow.'''
        res = klass.__module__.replace('.', '_') + '_' + klass.__name__
        return res.lower()
# ------------------------------------------------------------------------------
