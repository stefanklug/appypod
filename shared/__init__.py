# ------------------------------------------------------------------------------
import appy
import os.path

# ------------------------------------------------------------------------------
appyPath = os.path.realpath(os.path.dirname(appy.__file__))
mimeTypes = {'odt': 'application/vnd.oasis.opendocument.text',
             'doc': 'application/msword',
             'rtf': 'text/rtf',
             'pdf': 'application/pdf'}

# ------------------------------------------------------------------------------
class UnmarshalledObject:
    '''Used for producing objects from a marshalled Python object (in some files
       like a CSV file or an XML file).'''
    def __init__(self, **fields):
        for k, v in fields.iteritems():
            setattr(self, k, v)
    def __repr__(self):
        res = u'<PythonObject '
        for attrName, attrValue in self.__dict__.iteritems():
            v = attrValue
            if hasattr(v, '__repr__'):
                v = v.__repr__()
            try:
                res += u'%s = %s ' % (attrName, v)
            except UnicodeDecodeError:
                res += u'%s = <encoding problem> ' % attrName
        res  = res.strip() + '>'
        return res.encode('utf-8')

class UnmarshalledFile:
    '''Used for producing file objects from a marshalled Python object.'''
    def __init__(self):
        self.name = '' # The name of the file on disk
        self.mimeType = None # The MIME type of the file
        self.content = '' # The binary content of the file of a file object
        self.size = 0 # The length of the file in bytes.

# ------------------------------------------------------------------------------
class Dummy: pass
# ------------------------------------------------------------------------------
