# ------------------------------------------------------------------------------
import appy
import os.path

appyPath = os.path.realpath(os.path.dirname(appy.__file__))
mimeTypes = {'odt': 'application/vnd.oasis.opendocument.text',
             'doc': 'application/msword',
             'rtf': 'text/rtf',
             'pdf': 'application/pdf'}
# ------------------------------------------------------------------------------
