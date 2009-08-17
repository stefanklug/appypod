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

# ------------------------------------------------------------------------------
class Dummy: pass
# ------------------------------------------------------------------------------
