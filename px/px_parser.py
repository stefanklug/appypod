# ------------------------------------------------------------------------------
from appy.shared.xml_parser import XmlEnvironment, XmlParser
from appy.pod.buffers import MemoryBuffer

# ------------------------------------------------------------------------------
class PxEnvironment(XmlEnvironment):
    '''Environment for the PX parser.'''

    def __init__(self):
        # We try to mimic POD. POD has a root buffer that is a FileBuffer, which
        # is the final result buffer, into which the result of evaluating all
        # memory buffers, defined as sub-buffers of this file buffer, is
        # generated. For PX, we will define a result buffer, but as a memory
        # buffer instead of a file buffer.
        self.result = MemoryBuffer(self, None)
        # In this buffer, we will create a single memory sub-buffer that will
        # hold the result of parsing the PX = a hierarchy of memory buffers =
        # PX's AST (Abstract Syntax Tree).
        self.ast = MemoryBuffer(self, self.result)
        # A major difference between POD and PX: POD creates the AST and
        # generates the result in the same step: one AST is generated, and then
        # directly produces a single evaluation, in the root file buffer. PX
        # works in 2  steps: the AST is initially created in self.ast. Then,
        # several evaluations can be generated, in self.result, without
        # re-generating the AST. After every evaluation, self.result will be
        # cleaned, to be reusable for the next evaluation.
        # Context will come afterwards
        self.context = None
        # Buffer where we must dump the content we are currently reading
        self.currentBuffer = self.ast
        # Tag content we are currently reading. We will put soomething in this
        # attribute only if we encounter content that is Python code.
        # Else, we will directly dump the parsed content into the current
        # buffer.
        self.currentContent = ''
        # The currently walked element. We redefine it here. This attribute is
        # normally managed by the parent XmlEnvironment, but we do not use the
        # standard machinery from this environmment and from the default
        # XmlParser for better performance. Indeed, the base parser and env
        # process namespaces, and we do not need this for the PX parser.
        self.currentElem = None

    def addSubBuffer(self):
        subBuffer = self.currentBuffer.addSubBuffer()
        self.currentBuffer = subBuffer

    def isActionElem(self, elem):
        '''Returns True if the currently walked p_elem is the same elem as the
           main buffer elem.'''
        action = self.currentBuffer.action
        return action and (action.elem == elem)

# ------------------------------------------------------------------------------
class PxParser(XmlParser):
    '''PX parser that is specific for parsing PX data.'''
    pxAttributes = ('var', 'for', 'if')

    def __init__(self, env, caller=None):
        XmlParser.__init__(self, env, caller)

    def startElement(self, elem, attrs):
        '''A start p_elem with p_attrs is encountered in the PX.'''
        e = self.env
        self.currentElem = elem
        # See if we have a PX attribute among p_attrs.
        for name in self.pxAttributes:
            if attrs.has_key(name):
                # Dump the element in a new sub-buffer
                e.addSubBuffer()
                # Create the action for this buffer
                e.currentBuffer.createPxAction(elem, name, attrs[name])
                break
        if e.isActionElem(elem):
            # Add a temp element in the buffer (that will be unreferenced
            # later). This way, when encountering the corresponding end element,
            # we will be able to check whether the end element corresponds to
            # the main element or to a sub-element.
            e.currentBuffer.addElement(elem, elemType='px')
        if elem != 'x':
            e.currentBuffer.dumpStartElement(elem, attrs,
                                             ignoreAttrs=self.pxAttributes)

    def endElement(self, elem):
        e = self.env
        # Manage the potentially collected Python expression in
        # e.currentContent.
        if e.currentContent:
            e.currentBuffer.addExpression(e.currentContent)
            e.currentContent = ''
        # Dump the end element into the current buffer
        if elem != 'x': e.currentBuffer.dumpEndElement(elem)
        # If this element is the main element of the current buffer, we must
        # pop it and continue to work in the parent buffer.
        if e.isActionElem(elem):
            # Is it the buffer main element?
            isMainElement = e.currentBuffer.isMainElement(elem)
            # Unreference the element among buffer.elements
            e.currentBuffer.unreferenceElement(elem)
            if isMainElement:
                # Continue to work in the parent buffer
                e.currentBuffer = e.currentBuffer.parent

    def characters(self, content):
        e = self.env
        if not e.currentContent and content.startswith(':'):
            # This content is not static content to dump as-is into the result:
            # it is a Python expression.
            e.currentContent += content[1:]
        elif e.currentContent:
            # We continue to dump the Python expression.
            e.currentContent += content
        else:
            e.currentBuffer.dumpContent(content)
# ------------------------------------------------------------------------------
