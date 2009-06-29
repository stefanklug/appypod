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
import xml.sax
from xml.sax.handler import ContentHandler, ErrorHandler
from xml.sax.xmlreader import InputSource

# ------------------------------------------------------------------------------
class XmlElement:
    '''Representgs an XML tag.'''
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
    def __init__(self, env, caller=None):
        '''p_env should be an instance of a class that inherits from
           XmlEnvironment: it specifies the environment to use for this SAX
           parser.'''
        ContentHandler.__init__(self)
        self.env = env
        self.env.parser = self
        self.caller = caller # The class calling this parser
        self.parser = xml.sax.make_parser() # Fast, standard expat parser
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
# ------------------------------------------------------------------------------
