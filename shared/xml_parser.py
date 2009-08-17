# ------------------------------------------------------------------------------
# Appy is a framework for building applications in the Python language.
# Copyright (C) 2007 Gaetan Delannay

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,USA.

# ------------------------------------------------------------------------------
import xml.sax, base64
from xml.sax.handler import ContentHandler, ErrorHandler
from xml.sax.xmlreader import InputSource
from StringIO import StringIO

# ------------------------------------------------------------------------------
class XmlElement:
    '''Represents an XML tag.'''
    def __init__(self, elem, attrs=None, nsUri=None):
        '''An XmlElement instance may represent:
           - an already parsed tag (in this case, p_elem may be prefixed with a
             namespace);
           - the definition of an XML element (in this case, no namespace can be
             found in p_elem; but a namespace URI may be defined in p_nsUri).'''
        self.elem = elem
        self.attrs = attrs
        if elem.find(':') != -1:
            self.ns, self.name = elem.split(':')
        else:
            self.ns = ''
            self.name = elem
            self.nsUri = nsUri
    def equalsTo(self, other, namespaces=None):
        '''Does p_elem == p_other? If a p_namespaces dict is given, p_other must
           define a nsUri.'''
        res = None
        if namespaces:
            res = self.elem == ('%s:%s' % (namespaces[other.nsUri], other.name))
        else:
            res = self.elem == other.elem
        return res
    def __repr__(self):
        res = self.elem
        if self.attrs:
            res += '('
            for attrName, attrValue in self.attrs.items():
                res += '%s="%s"' % (attrName, attrValue)
            res += ')'
        return res
    def getFullName(self, namespaces=None):
        '''Gets the name of the element including the namespace prefix.'''
        if not namespaces:
            res = self.elem
        else:
            res = '%s:%s' % (namespaces[self.nsUri], self.name)
        return res

class XmlEnvironment:
    '''An XML environment remembers a series of elements during a SAX parsing.
       This class is an abstract class that gathers basic things like
       namespaces.'''
    def __init__(self):
        # This dict contains the xml namespace declarations encountered so far
        self.namespaces = {} # ~{s_namespaceUri:s_namespaceName}~
        self.currentElem = None # The currently parsed element
        self.parser = None
    def manageNamespaces(self, attrs):
        '''Manages namespaces definitions encountered in p_attrs.'''
        for attrName, attrValue in attrs.items():
            if attrName.startswith('xmlns:'):
                self.namespaces[attrValue] = attrName[6:]
    def ns(self, nsUri):
        '''Returns the namespace corresponding to o_nsUri.'''
        return self.namespaces[nsUri]

class XmlParser(ContentHandler, ErrorHandler):
    '''Basic XML content handler that does things like :
      - remembering the currently parsed element;
      - managing namespace declarations.'''
    def __init__(self, env=None, caller=None):
        '''p_env should be an instance of a class that inherits from
           XmlEnvironment: it specifies the environment to use for this SAX
           parser.'''
        ContentHandler.__init__(self)
        if not env: env = XmlEnvironment()
        self.env = env
        self.env.parser = self
        self.caller = caller # The class calling this parser
        self.parser = xml.sax.make_parser() # Fast, standard expat parser
        self.res = None # The result of parsing.
    def setDocumentLocator(self, locator):
        self.locator = locator
        return self.env
    def endDocument(self):
        return self.env
    def startElement(self, elem, attrs):
        self.env.manageNamespaces(attrs)
        if self.env.currentElem == None:
            self.env.currentElem = XmlElement(elem, attrs=attrs)
        else:
            # Reuse the exiting instance in order to avoid creating one instance
            # every time an elem is met in the XML file.
            self.env.currentElem.__init__(elem, attrs)
        return self.env
    def endElement(self, elem):
        self.env.currentElem.__init__(elem)
        return self.env
    def characters(self, content):
        return self.env
    def parse(self, xmlContent, source='string'):
        '''Parsers the XML file or string p_xmlContent.'''
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        self.parser.setContentHandler(self)
        self.parser.setErrorHandler(self)
        inputSource = InputSource()
        if source == 'string':
            inputSource.setByteStream(StringIO(xmlContent))
        else:
            inputSource.setByteStream(xmlContent)
        self.parser.parse(inputSource)
        return self.res

# ------------------------------------------------------------------------------
from appy.shared import UnmarshalledObject, Dummy
from appy.gen.plone25.wrappers import FileWrapper
try:
    from DateTime import DateTime
except ImportError:
    DateTime = 'unicode'

class XmlUnmarshaller(XmlParser):
    '''This class allows to parse a XML file and recreate the corresponding web
       of Python objects. This parser assumes that the XML file respects this
       convention: any tag may define in attribute "type" storing the type of
       its content, which may be:
       
       bool * int * float * long * DateTime * tuple * list * object

       If "object" is specified, it means that the tag contains sub-tags, each
       one corresponding to the value of an attribute for this object.
       if "tuple" is specified, it will be converted to a list.'''
    def __init__(self, klass=None):
        XmlParser.__init__(self)
        self.klass = klass # If a klass is given here, instead of creating
        # a root UnmarshalledObject instance, we will create an instance of this
        # class (only if the root object is an object; this does not apply if
        # it is a list or tuple; yes, technically the root tag can be a list or
        # tuple even if it is silly because only one root tag can exist). But be
        # careful: we will not call the constructor of this class. We will
        # simply create an instance of UnmarshalledObject and dynamically change
        # the class of the created instance to this class.

    def startDocument(self):
        self.res = None # The resulting web of Python objects
        # (UnmarshalledObject instances).
        self.env.containerStack = [] # The stack of current "containers" where
        # to store the next parsed element. A container can be a list, a tuple,
        # an object (the root object of the whole web or a sub-object).
        self.env.currentBasicType = None # Will hold the name of the currently
        # parsed basic type (unicode, float, ...)
        self.env.currentContent = '' # We store here the content of tags.
        self.env.currentFileName = '' # If current tag contains a file, we
        # store here the file name.
        self.env.currentMimeType = '' # If current tag contains a file, we
        # store here the file name.

    containerTags = ('tuple', 'list', 'object')
    numericTypes = ('bool', 'int', 'float', 'long')
    def startElement(self, elem, attrs):
        e = XmlParser.startElement(self, elem, attrs)
        # Determine the type of the element.
        elemType = 'unicode' # Default value
        if attrs.has_key('type'):
            elemType = attrs['type']
        if elemType in self.containerTags:
            # I must create a new container object.
            if elemType == 'object': newObject = UnmarshalledObject()
            elif elemType == 'tuple': newObject = [] # Tuples become lists
            elif elemType == 'list': newObject = []
            else: newObject = UnmarshalledObject()
            # Store the value on the last container, or on the root object.
            self.storeValue(elem, newObject)
            # Push the new object on the container stack
            e.containerStack.append(newObject)
        else:
            # We are parsing a basic type
            e.currentBasicType = elemType
            if elemType == 'file':
                if attrs.has_key('name'): e.currentFileName = attrs['name']
                if attrs.has_key('mimeType'):
                    e.currentMimeType = attrs['mimeType']

    def storeValue(self, name, value):
        '''Stores the newly parsed p_value (contained in tag p_name) on the
           current container in environment p_e.'''
        e = self.env
        # Where must I store this value?
        if not e.containerStack:
            # I store the object at the root of the web.
            self.res = value
            if self.klass and isinstance(value, UnmarshalledObject):
                self.res.__class__ = self.klass
        else:
            currentContainer = e.containerStack[-1]
            if type(currentContainer) == list:
                currentContainer.append(value)
            else:
                # Current container is an object
                setattr(currentContainer, name, value)

    def characters(self, content):
        e = XmlParser.characters(self, content)
        if e.currentBasicType:
            e.currentContent += content

    def endElement(self, elem):
        e = XmlParser.endElement(self, elem)
        if e.currentBasicType:
            # Get and convert the value of this field
            if e.currentBasicType in self.numericTypes:
                try:
                    exec 'value = %s' % e.currentContent.strip()
                except SyntaxError:
                    value = None
            elif e.currentBasicType == 'DateTime':
                value = DateTime(e.currentContent.strip())
            elif e.currentBasicType == 'file':
                value = Dummy()
                value.name = e.currentFileName
                value.content = base64.b64decode(e.currentContent.strip())
                value.mimeType = e.currentMimeType
                value.size = len(value.content)
                value.__class__ = FileWrapper
            else:
                value = e.currentContent.strip()
            # Store the value on the last container
            self.storeValue(elem, value)
            # Clean the environment
            e.currentBasicType = None
            e.currentContent = ''
        else:
            e.containerStack.pop()

    # Alias 'unmarshall' -> 'parse'
    unmarshall = XmlParser.parse

# ------------------------------------------------------------------------------
class XmlMarshaller:
    '''This class allows to produce a XML version of a Python object, which
       respects some conventions as described in the doc of the corresponding
       Unmarshaller (see above).'''
    xmlPrologue = '<?xml version="1.0" encoding="utf-8"?>'
    xmlEntities = {'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;',
                   "'": '&apos;'}
    trueFalse = {True: 'True', False: 'False'}
    sequenceTypes = (tuple, list)
    rootElementName = 'xmlPythonData'
    fieldsToMarshall = 'all'
    fieldsToExclude = []
    atFiles = ('image', 'file') # Types of archetypes fields that contain files.

    def dumpValue(self, res, value, fieldType='basic'):
        '''Dumps the XML version of p_value to p_res.'''
        if fieldType == 'file':
            # p_value contains the (possibly binary) content of a file. We will
            # encode it in Base64.
            if hasattr(value, 'data'):
                v = value.data # Simple wrap for images
                if hasattr(v, 'data'): v = v.data # Double wrap for files
            else:
                v = value
            res.write(base64.b64encode(v))
        elif isinstance(value, basestring):
            # Replace special chars by XML entities
            for c in value:
                if self.xmlEntities.has_key(c):
                    res.write(self.xmlEntities[c])
                else:
                    res.write(c)
        elif isinstance(value, bool):
            res.write(self.trueFalse[value])
        else:
            res.write(value)

    def dumpField(self, res, fieldName, fieldValue, fieldType='basic'):
        '''Dumps in p_res, the value of the p_field for p_instance.'''
        res.write('<'); res.write(fieldName);
        # Dump the type of the field as an XML attribute
        fType = None # No type will mean "string".
        if fieldType == 'file': fType ='file'
        elif fieldType == 'ref': fType = 'list'
        elif isinstance(fieldValue, bool): fType = 'bool'
        elif isinstance(fieldValue, int): fType = 'int'
        elif isinstance(fieldValue, float): fType = 'float'
        elif isinstance(fieldValue, long): fType = 'long'
        elif isinstance(fieldValue, tuple): fType = 'tuple'
        elif isinstance(fieldValue, list): fType = 'list'
        elif fieldValue.__class__.__name__ == 'DateTime': fType = 'DateTime'
        if fType: res.write(' type="%s"' % fType)
        if type(fieldValue) in self.sequenceTypes:
            res.write(' count="%d"' % len(fieldValue))
        if fieldType == 'file':
            if hasattr(fieldValue, 'content_type'):
                res.write(' mimeType="%s"' % fieldValue.content_type)
            if hasattr(fieldValue, 'filename'):
                res.write(' name="%s"' % fieldValue.filename)
        res.write('>')
        # Dump the child elements if any
        if fieldType == 'ref':
            if fieldValue:
                for elem in fieldValue:
                    self.dumpField(res, 'url', elem.absolute_url_path())
            else:
                self.dumpField(res, 'url', '')
        elif type(fieldValue) in self.sequenceTypes:
            # The previous condition must be checked before this one because
            # Referred objects are stored in lists or tuples, too.
            for elem in fieldValue:
                self.dumpField(res, 'e', elem)
        else:
            res.write(self.dumpValue(res, fieldValue, fieldType))
        res.write('</'); res.write(fieldName); res.write('>')

    def marshall(self, instance, objectType='popo'):
        '''Returns in a StringIO the XML version of p_instance. If p_instance
           corresponds to a Plain Old Python Object, specify 'popo' for
           p_objectType. If p_instance corresponds to an Archetypes object
           (Zope/Plone), specify 'archetype' for p_objectType.'''
        res = StringIO()
        # Dump the XML prologue and root element
        res.write(self.xmlPrologue)
        res.write('<'); res.write(self.rootElementName)
        res.write(' type="object">')
        # Dump the value of the fields that must be dumped
        if objectType == 'popo':
            for fieldName, fieldValue in instance.__dict__.iteritems():
                mustDump = False
                if fieldName in self.fieldsToExclude:
                    mustDump = False
                elif self.fieldsToMarshall == 'all':
                    mustDump = True
                else:
                    if (type(self.fieldsToMarshall) in self.sequenceTypes) and \
                       (fieldName in self.fieldsToMarshall):
                        mustDump = True
                if mustDump:
                    self.dumpField(res, fieldName, fieldValue)
        elif objectType == 'archetype':
            fields = instance.schema.fields()
            for field in instance.schema.fields():
                # Dump only needed fields
                mustDump = False
                if field.getName() in self.fieldsToExclude:
                    mustDump = False
                elif (self.fieldsToMarshall == 'all') and \
                   (field.schemata != 'metadata'):
                    mustDump = True
                elif self.fieldsToMarshall == 'all_with_metadata':
                    mustDump = True
                else:
                    if (type(self.fieldsToMarshall) in self.sequenceTypes) and \
                       (field.getName() in self.fieldsToMarshall):
                        mustDump = True
                if mustDump:
                    fieldType = 'basic'
                    if field.type in self.atFiles:
                        fieldType = 'file'
                    elif field.type == 'reference':
                        fieldType = 'ref'
                    self.dumpField(res, field.getName(), field.get(instance),
                        fieldType=fieldType)
        self.marshallSpecificElements(instance, res)
        # Return the result
        res.write('</'); res.write(self.rootElementName); res.write('>')
        data = res.getvalue()
        res.close()
        return data

    def marshallSpecificElements(self, instance, res):
        '''You can use this marshaller as a base class for creating your own.
           In this case, this method will be called by the marshall method
           for allowing your concrete marshaller to insert more things in the
           result. p_res is the StringIO buffer where the result of the
           marshalling process is currently dumped; p_instance is the instance
           currently marshalled.'''
# ------------------------------------------------------------------------------
