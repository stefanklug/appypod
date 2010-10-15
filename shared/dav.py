# ------------------------------------------------------------------------------
import os, re, httplib, sys, stat
from StringIO import StringIO
from mimetypes import guess_type
from base64 import encodestring
from appy.shared.utils import copyData

# ------------------------------------------------------------------------------
urlRex = re.compile(r'http://([^:/]+)(:[0-9]+)?(/.+)?', re.I)
binaryRex = re.compile(r'[\000-\006\177-\277]')

# ------------------------------------------------------------------------------
class Resource:
    '''Every instance of this class represents some web resource accessible
       through WebDAV.'''

    def __init__(self, url, username=None, password=None):
        self.username = username
        self.password = password
        self.url = url

        # Split the URL into its components
        res = urlRex.match(url)
        if res:
            host, port, uri = res.group(1,2,3)
            self.host = host
            self.port = port and int(port[1:]) or 80
            self.uri = uri or '/'
        else: raise 'Wrong URL: %s' % str(url)

    def __repr__(self):
        port = ':' + str(self.port)
        if self.port == 80: port = ''
        return '<Dav resource at %s%s/%s>' % (self.url, port, self.uri)

    def updateHeaders(self, headers):
        # Add credentials if present
        if not (self.username and self.password): return
        if headers.has_key('Authorization'): return
        credentials = '%s:%s' % (self.username,self.password)
        credentials = credentials.replace('\012','')
        headers['Authorization'] = "Basic %s" % encodestring(credentials)
        headers['User-Agent'] = 'WebDAV.client'
        headers['Host'] = self.host
        headers['Connection'] = 'close'
        headers['Accept'] = '*/*'
        return headers

    def sendRequest(self, method, uri, body=None, headers={}, bodyType=None):
        '''Sends a HTTP request with p_method, for p_uri.'''
        conn = httplib.HTTP()
        conn.connect(self.host, self.port)
        conn.putrequest(method, uri)
        # Add HTTP headers
        self.updateHeaders(headers)
        for n, v in headers.items(): conn.putheader(n, v)
        conn.endheaders()
        if body: copyData(body, conn, 'send', type=bodyType)
        ver, code, msg = conn.getreply()
        data = conn.getfile().read()
        conn.close()
        return data

    def mkdir(self, name):
        '''Creates a folder named p_name in this resource.'''
        folderUri = self.uri + '/' + name
        #body = '<d:propertyupdate xmlns:d="DAV:"><d:set><d:prop>' \
        #       '<d:displayname>%s</d:displayname></d:prop></d:set>' \
        #       '</d:propertyupdate>' % name
        return self.sendRequest('MKCOL', folderUri)

    def delete(self, name):
        '''Deletes a file or a folder (and all contained files if any) named
           p_name within this resource.'''
        toDeleteUri = self.uri + '/' + name
        return self.sendRequest('DELETE', toDeleteUri)

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
        res = self.sendRequest('PUT', fileUri, body, headers, bodyType=bodyType)
        # Close the file when relevant
        if type =='fileName': body.close()
# ------------------------------------------------------------------------------
