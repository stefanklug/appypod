# ------------------------------------------------------------------------------
import os, re, http.client, sys, stat, urllib.parse, time, socket, xml.sax
from urllib.parse import quote
from io import StringIO
from mimetypes import guess_type
from base64 import b64encode
from appy import Object
from appy.shared.utils import copyData, sequenceTypes
from appy.shared.xml_parser import XmlUnmarshaller, XmlMarshaller

# ------------------------------------------------------------------------------
class ResourceError(Exception): pass

# ------------------------------------------------------------------------------
class FormDataEncoder:
    '''Allows to encode form data for sending it through a HTTP request.'''
    def __init__(self, data):
        self.data = data # The data to encode, as a dict

    def marshalValue(self, name, value):
        if isinstance(value, basestring):
            return '%s=%s' % (name, quote(str(value)))
        elif isinstance(value, float):
            return '%s:float=%s' % (name, value)
        elif isinstance(value, int):
            return '%s:int=%s' % (name, value)
        elif isinstance(value, int):
            res = '%s:long=%s' % (name, value)
            if res[-1] == 'L':
                res = res[:-1]
            return res
        else:
            raise 'Cannot encode value %s' % str(value)

    def encode(self):
        res = []
        for name, value in self.data.items():
            res.append(self.marshalValue(name, value))
        return '&'.join(res)

# ------------------------------------------------------------------------------
class SoapDataEncoder:
    '''Allows to encode SOAP data for sending it through a HTTP request.'''
    namespaces = {'SOAP-ENV': 'http://schemas.xmlsoap.org/soap/envelope/',
                  'xsd'     : 'http://www.w3.org/2001/XMLSchema',
                  'xsi'     : 'http://www.w3.org/2001/XMLSchema-instance'}
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
        if isinstance(self.data, basestring): return self.data
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
        self.code = response.status # The return code, ie 404, 200, 500...
        self.text = response.reason # Textual description of the code
        self.headers = response.msg # A dict-like object containing the headers
        self.body = body # The body of the HTTP response
        # p_duration, if given, is the time, in seconds, we have waited, before
        # getting this response after having sent the request.
        self.duration = duration
        self.utf8 = utf8
        # The following attribute may contain specific data extracted from
        # the previous fields. For example, when response if 302 (Redirect),
        # self.data contains the URI where we must redirect the user to.
        self.data = self.extractData()

    def __repr__(self):
        duration = ''
        if self.duration: duration = ', got in %.4f seconds' % self.duration
        return '<HttpResponse %s (%s)%s>' % (self.code, self.text, duration)

    def extractContentType(self, contentType):
        '''Extract the content type from the HTTP header, potentially removing
           encoding-related data.'''
        i = contentType.find(';')
        if i != -1: return contentType[:i]
        return contentType

    xmlHeaders = ('text/xml', 'application/xml', 'application/soap+xml')
    def extractData(self):
        '''This method extracts, from the various parts of the HTTP response,
           some useful information. For example, it will find the URI where to
           redirect the user to if self.code is 302, or will unmarshall XML
           data into Python objects.'''
        if self.code == 302:
            return urllib.parse.urlparse(self.headers['location'])[2]
        elif 'content-type' in self.headers:
            contentType = self.extractContentType(self.headers['content-type'])
            for xmlHeader in self.xmlHeaders:
                if contentType.startswith(xmlHeader):
                    # Return an unmarshalled version of the XML content, for
                    # easy use in Python.
                    try:
                        parser = XmlUnmarshaller(utf8=self.utf8)
                        res = parser.parse(self.body)
                        if parser.rootTag == 'exception':
                            # This is an exception: "res" contains the traceback
                            raise ResourceError('Distant server exception: ' \
                                                '%s' % res)
                        return res
                    except xml.sax.SAXParseException as se:
                        raise ResourceError('Invalid XML response (%s)'%str(se))

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
        # If p_measure is True, we will measure, for every request sent, the
        # time we wait until we receive the response.
        self.measure = measure
        # If measure is True, we will store hereafter, the total time (in
        # seconds) spent waiting for the server for all requests sent through
        # this resource object.
        self.serverTime = 0
        # Split the URL into its components
        res = urlRex.match(url)
        if res:
            host, port, uri = res.group(1,2,3)
            self.host = host
            self.port = port and int(port[1:]) or 80
            self.uri = uri or '/'
        else: raise Exception('Wrong URL: %s' % str(url))
        # If some headers must be sent with any request sent through this
        # resource (like a cookie), you can store them in the following dict.
        self.headers = {'Host': self.host}
        self.utf8 = utf8

    def __repr__(self):
        return '<Dav resource at %s>' % self.url

    def updateHeaders(self, headers):
        # Add credentials if present
        if not (self.username and self.password): return
        if 'Authorization' in headers: return
        credentials = '%s:%s' % (self.username, self.password)
        credentials = credentials.replace('\012', '')
        headers['Authorization'] = "Basic %s" % b64encode(credentials.encode()).decode()
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
            raise ResourceError('Check your Internet connection (%s)'% str(sge))
        except socket.error as se:
            raise ResourceError('Connection error (%s)' % str(se))
        # Tell what kind of HTTP request it will be.
        conn.putrequest(method, uri, skip_host=True)
        # Add HTTP headers
        self.updateHeaders(headers)
        if self.headers: headers.update(self.headers)
        for n, v in list(headers.items()): conn.putheader(n, v)
        conn.endheaders()
        # Add HTTP body
        if body:
            if not bodyType: bodyType = 'string'
            copyData(body, conn, 'send', type=bodyType)
        # Send the request, get the reply
        if self.measure: startTime = time.time()
        response = conn.getresponse()
        if self.measure: endTime = time.time()
        body = response.read()
        conn.close()
        # Return a smart object containing the various parts of the response
        duration = None
        if self.measure:
            duration = endTime - startTime
            self.serverTime += duration
        return HttpResponse(response, body, duration=duration, utf8=self.utf8)

    def mkdir(self, name):
        '''Creates a folder named p_name in this resource.'''
        folderUri = self.uri + '/' + name
        #body = '<d:propertyupdate xmlns:d="DAV:"><d:set><d:prop>' \
        #       '<d:displayname>%s</d:displayname></d:prop></d:set>' \
        #       '</d:propertyupdate>' % name
        return self.send('MKCOL', folderUri)

    def delete(self, name):
        '''Deletes a file or a folder (and all contained files if any) named
           p_name within this resource.'''
        toDeleteUri = self.uri + '/' + name
        return self.send('DELETE', toDeleteUri)

    def add(self, content, type='fileName', name=''):
        '''Adds a file in this resource. p_type can be:
           - "fileName"  In this case, p_content is the path to a file on disk
                         and p_name is ignored;
           - "zope"      In this case, p_content is an instance of
                         OFS.Image.File and the name of the file is given in
                         p_name.
        '''
        if type == 'fileName':
            # p_content is the name of a file on disk
            size = os.stat(content)[stat.ST_SIZE]
            body = file(content, 'rb')
            name = os.path.basename(content)
            fileType, encoding = guess_type(content)
            bodyType = 'file'
        elif type == 'zope':
            # p_content is a "Zope" file, ie a OFS.Image.File instance
            # p_name is given
            fileType = content.content_type
            encoding = None
            size = content.size
            body = content
            bodyType = 'zope'
        fileUri = self.uri + '/' + name
        headers = {'Content-Length': str(size)}
        if fileType: headers['Content-Type'] = fileType
        if encoding: headers['Content-Encoding'] = encoding
        res = self.send('PUT', fileUri, body, headers, bodyType=bodyType)
        # Close the file when relevant
        if type =='fileName': body.close()
        return res

    def get(self, uri=None, headers={}, params=None):
        '''Perform a HTTP GET on the server. Parameters can be given as a dict
           in p_params.'''
        if not uri: uri = self.uri
        # Encode and append params if given
        if params:
            sep = ('?' in uri) and '&' or '?'
            uri = '%s%s%s' % (uri, sep, urllib.urlencode(params))
        return self.send('GET', uri, headers=headers)
    rss = get

    def post(self, data=None, uri=None, headers={}, encode='form'):
        '''Perform a HTTP POST on the server. If p_encode is "form", p_data is
           considered to be a dict representing form data that will be
           form-encoded. Else, p_data will be considered as the ready-to-send
           body of the HTTP request.'''
        if not uri: uri = self.uri
        # Prepare the data to send
        if encode == 'form':
            # Format the form data and prepare headers
            body = FormDataEncoder(data).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        else:
            body = data
        headers['Content-Length'] = str(len(body))
        return self.send('POST', uri, headers=headers, body=body)

    def soap(self, data, uri=None, headers={}, namespace=None, soapAction=None):
        '''Sends a SOAP message to this resource. p_namespace is the URL of the
           server-specific namespace. If header value "SOAPAction" is different
           from self.url, specify it in p_soapAction.'''
        if not uri: uri = self.uri
        # Prepare the data to send
        data = SoapDataEncoder(data, namespace).encode()
        headers['SOAPAction'] = soapAction or self.url
        headers['Content-Type'] = 'text/xml'
        res = self.post(data, uri, headers=headers, encode=None)
        # Unwrap content from the SOAP envelope
        if hasattr(res.data, 'Body'):
            res.data = res.data.Body
        return res
# ------------------------------------------------------------------------------
