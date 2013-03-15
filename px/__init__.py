'''PX stands for *P*ython *X*ML. It is a templating engine that reuses the pod
   engine to produce XML (including XHTML) from templates written as a mix of
   Python and XML.'''

# ------------------------------------------------------------------------------
from UserDict import UserDict
from px_parser import PxParser, PxEnvironment
from appy.pod.renderer import BAD_CONTEXT

# Exception class --------------------------------------------------------------
class PxError(Exception): pass

# ------------------------------------------------------------------------------
class Px:
    '''Represents a (chunk of) PX code.'''
    def __init__(self, content, isFileName=False, partial=True):
        '''p_content is the PX code, as a string, or a file name if p_isFileName
           is True. If this code represents a complete XML file, p_partial is
           False. Else, we must surround p_content with a root tag to be able
           to parse it with a SAX parser.'''
        # Get the PX content
        if isFileName:
            f = file(content)
            self.content = f.read()
            f.close()
        else:
            self.content = content
        # It this content a complete XML file, or just some part of it?
        if partial:
            # Surround the partial chunk with a root tag: it must be valid XML.
            self.content = '<x>%s</x>' % self.content
        self.partial = partial
        # Create a PX parser
        self.parser = PxParser(PxEnvironment(), self)
        # Parses self.content (a PX code in a string) with self.parser, to
        # produce a tree of memory buffers.
        self.parser.parse(self.content)

    def __call__(self, context):
        # Get the context in a standardized form.
        evalContext = {}
        if hasattr(context, '__dict__'):
            evalContext.update(context.__dict__)
        elif isinstance(context, dict) or isinstance(context, UserDict):
            evalContext.update(context)
        else:
            raise PxError(BAD_CONTEXT)
        # Store the context on the PX environment
        self.parser.env.context = evalContext
        # Render the PX result and return it
        env = self.parser.env
        env.ast.evaluate()
        res = env.result.content
        # Clean the res, for the next evaluation
        env.result.clean()
        return res
# ------------------------------------------------------------------------------
