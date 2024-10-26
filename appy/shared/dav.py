# ------------------------------------------------------------------------------
import base64
import http.client
import os
import re
import socket
import stat
import time
import urllib.parse
import xml.sax
from mimetypes import guess_type
from urllib.parse import quote, urlencode

from appy import Object
from appy.shared.utils import copyData
from appy.shared.xml_parser import XmlMarshaller, XmlUnmarshaller


# ------------------------------------------------------------------------------
class ResourceError(Exception):
    pass

# ------------------------------------------------------------------------------


class FormDataEncoder:
    '''Allows to encode form data for sending it through a HTTP request.'''

    def __init__(self, data):
        self.data = data  # The data to encode, as a dict

    def marshalValue(self, name, value):
        if isinstance(value, str):
            return '%s=%s' % (name, quote(str(value)))
        elif isinstance(value, float):
            return '%s:float=%s' % (name, value)
        elif isinstance(value, int):
            return '%s:int=%s' % (name, value)
        else:
            raise Exception('Cannot encode value %s' % str(value))

    def encode(self):
        res = []
        for name, value in self.data.items():
            res.append(self.marshalValue(name, value))
        return '&'.join(res)

# ------------------------------------------------------------------------------


class SoapDataEncoder:
    '''Allows to encode SOAP data for sending it through a HTTP request.'''
    namespaces = {'SOAP-ENV': 'http://schemas.xmlsoap.org/soap/envelope/',
                  'xsd': 'http://www.w3.org/2001/XMLSchema',
                  'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}
    namespacedTags = {'Envelope': 'SOAP-ENV', 'Body': 'SOAP-ENV', '*': 'py'}

    def __init__(self, data, namespace='http://appyframework.org'):
        self.data = data
        # p_data can be:
        # - a string already containing a complete SOAP message
        # - a Python object, that we will convert to a SOAP message
        # Define the namespaces for this request
        self.ns = self.namespaces.copy()
        self.ns['py'] = namespace

    def encode(self):
        # Do nothing if we have a SOAP message already
        if isinstance(self.data, str):
            return self.data
        # self.data is here a Python object. Wrap it in a SOAP Body.
        soap = Object(Body=self.data)
        # Marshall it.
        marshaller = XmlMarshaller(rootTag='Envelope', namespaces=self.ns,
                                   namespacedTags=self.namespacedTags)
        return marshaller.marshall(soap)

# ------------------------------------------------------------------------------


class HttpResponse:
    '''Stores information about a HTTP response.'''

    def __init__(self, response, body, duration=None, utf8=True):
        self.code = response.status  # The return code, ie 404, 200, 500...
        self.text = response.reason  # Textual description of the code
        self.headers = response.headers  # A dict-like object containing the headers
        self.body = body  # The body of the HTTP response
        self.duration = duration
        self.utf8 = utf8
        self.data = self.extractData()

    def __repr__(self):
        duration = ''
        if self.duration:
            duration = ', got in %.4f seconds' % self.duration
        return '<HttpResponse %s (%s)%s>' % (self.code, self.text, duration)

    def extractContentType(self, contentType):
        '''Extract the content type from the HTTP header, potentially removing
           encoding-related data.'''
        i = contentType.find(';')
        if i != -1:
            return contentType[:i]
        return contentType

    xmlHeaders = ('text/xml', 'application/xml', 'application/soap+xml')

    def extractData(self):
        '''This method extracts, from the various parts of the HTTP response,
           some useful information.'''
        if self.code == 302:
            return urllib.parse.urlparse(self.headers['Location'])[2]
        elif 'Content-Type' in self.headers:
            contentType = self.extractContentType(self.headers['Content-Type'])
            for xmlHeader in self.xmlHeaders:
                if contentType.startswith(xmlHeader):
                    try:
                        parser = XmlUnmarshaller(utf8=self.utf8)
                        res = parser.parse(self.body)
                        if parser.rootTag == 'exception':
                            raise ResourceError(
                                'Distant server exception: %s' % res)
                        return res
                    except xml.sax.SAXParseException as se:
                        raise ResourceError(
                            'Invalid XML response (%s)' % str(se))


# ------------------------------------------------------------------------------
urlRex = re.compile(r'http[s]?://([^:/]+)(:[0-9]+)?(/.+)?', re.I)
binaryRex = re.compile(r'[\000-\006\177-\277]')


class Resource:
    '''Every instance of this class represents some web resource accessible
       through HTTP.'''

    def __init__(self, url, username=None, password=None, measure=False,
                 utf8=True):
        self.username = username
        self.password = password
        self.url = url
        self.measure = measure
        self.serverTime = 0
        res = urlRex.match(url)
        if res:
            host, port, uri = res.group(1, 2, 3)
            self.host = host
            self.port = int(port[1:]) if port else 80
            self.uri = uri or '/'
        else:
            raise Exception('Wrong URL: %s' % str(url))
        self.headers = {'Host': self.host}
        self.utf8 = utf8

    def __repr__(self):
        return '<Dav resource at %s>' % self.url

    def updateHeaders(self, headers):
        if not (self.username and self.password):
            return
        if 'Authorization' in headers:
            return
        credentials = '%s:%s' % (self.username, self.password)
        headers['Authorization'] = "Basic %s" % base64.b64encode(
            credentials.encode()).decode()
        headers['User-Agent'] = 'Appy'
        headers['Host'] = self.host
        headers['Connection'] = 'close'
        headers['Accept'] = '*/*'
        return headers

    def send(self, method, uri, body=None, headers={}, bodyType=None):
        '''Sends a HTTP request with p_method, for p_uri.'''
        conn = http.client.HTTPConnection(self.host, self.port)
        try:
            conn.connect()
        except socket.gaierror as sge:
            raise ResourceError(
                'Check your Internet connection (%s)' % str(sge))
        except socket.error as se:
            raise ResourceError('Connection error (%s)' % str(se))
        conn.putrequest(method, uri, skip_host=True)
        self.updateHeaders(headers)
        if self.headers:
            headers.update(self.headers)
        for n, v in headers.items():
            conn.putheader(n, v)
        conn.endheaders()
        if body:
            copyData(body, conn, 'send', type=bodyType or 'string')
        if self.measure:
            startTime = time.time()
        response = conn.getresponse()
        if self.measure:
            endTime = time.time()
        body = response.read()
        conn.close()
        duration = endTime - startTime if self.measure else None
        if self.measure:
            self.serverTime += duration
        return HttpResponse(response, body, duration=duration, utf8=self.utf8)

    def mkdir(self, name):
        '''Creates a folder named p_name in this resource.'''
        folderUri = self.uri + '/' + name
        return self.send('MKCOL', folderUri)

    def delete(self, name):
        '''Deletes a file or folder named p_name within this resource.'''
        toDeleteUri = self.uri + '/' + name
        return self.send('DELETE', toDeleteUri)

    def add(self, content, type='fileName', name=''):
        '''Adds a file to this resource.'''
        if type == 'fileName':
            size = os.stat(content)[stat.ST_SIZE]
            body = open(content, 'rb')
            name = os.path.basename(content)
            fileType, encoding = guess_type(content)
            bodyType = 'file'
        elif type == 'zope':
            fileType = content.content_type
            size = content.size
            body = content
            bodyType = 'zope'
        fileUri = self.uri + '/' + name
        headers = {'Content-Length': str(size)}
        if fileType:
            headers['Content-Type'] = fileType
        if encoding:
            headers['Content-Encoding'] = encoding
        res = self.send('PUT', fileUri, body, headers, bodyType=bodyType)
        if type == 'fileName':
            body.close()
        return res

    def get(self, uri=None, headers={}, params=None):
        if not uri:
            uri = self.uri
        if params:
            sep = '?' if '?' not in uri else '&'
            uri = f'{uri}{sep}{urlencode(params)}'
        return self.send('GET', uri, headers=headers)
    rss = get

    def post(self, data=None, uri=None, headers={}, encode='form'):
        if not uri:
            uri = self.uri
        if encode == 'form':
            body = FormDataEncoder(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = data
        headers['Content-Length'] = str(len(body))
        return self.send('POST', uri, headers=headers, body=body)

    def soap(self, data, uri=None, headers={}, namespace=None, soapAction=None):
        '''This method performs a POST to a SOAP web service.'''
        if not uri:
            uri = self.uri
        body = SoapDataEncoder(data, namespace=namespace).encode()
        headers['Content-Type'] = 'text/xml'
        headers['Content-Length'] = str(len(body))
        if soapAction:
            headers['SOAPAction'] = '"%s"' % soapAction
        return self.send('POST', uri, headers=headers, body=body)
