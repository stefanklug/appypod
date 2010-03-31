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
import os, os.path, sys, traceback, unicodedata

# ------------------------------------------------------------------------------
class FolderDeleter:
    def delete(dirName):
        '''Recursively deletes p_dirName.'''
        dirName = os.path.abspath(dirName)
        for root, dirs, files in os.walk(dirName, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(dirName)
    delete = staticmethod(delete)

# ------------------------------------------------------------------------------
class Traceback:
    '''Dumps the last traceback into a string.'''
    def get():
        res = ''
        excType, excValue, tb = sys.exc_info()
        tbLines = traceback.format_tb(tb)
        for tbLine in tbLines:
            res += ' %s' % tbLine
        res += ' %s: %s' % (str(excType), str(excValue))
        return res
    get = staticmethod(get)

# ------------------------------------------------------------------------------
def getOsTempFolder():
    tmp = '/tmp'
    if os.path.exists(tmp) and os.path.isdir(tmp):
        res = tmp
    elif os.environ.has_key('TMP'):
        res = os.environ['TMP']
    elif os.environ.has_key('TEMP'):
        res = os.environ['TEMP']
    else:
        raise "Sorry, I can't find a temp folder on your machine."
    return res

# ------------------------------------------------------------------------------
def executeCommand(cmd, ignoreLines=None):
    '''Executes command p_cmd and returns the content of its stderr.
       If p_ignoreLines is not None, we will remove from the result every line
       starting with p_ignoreLines.'''
    childStdIn, childStdOut, childStdErr = os.popen3(cmd)
    res = childStdErr.read()
    if res and ignoreLines:
        # Remove every line starting with ignoreLines
        keptLines = []
        for line in res.split('\n'):
            line = line.strip()
            if not line or line.startswith(ignoreLines): continue
            else:
                keptLines.append(line)
        res = '\n'.join(keptLines)
    childStdIn.close(); childStdOut.close(); childStdErr.close()
    return res

# ------------------------------------------------------------------------------
unwantedChars = ('\\', '/', ':', '*', '?', '"', '<', '>', '|', ' ')
def normalizeString(s, usage='fileName'):
    '''Returns a version of string p_s whose special chars have been
       replaced with normal chars.'''
    # We work in unicode. Convert p_s to unicode if not unicode.
    if isinstance(s, str):           s = s.decode('utf-8')
    elif not isinstance(s, unicode): s = unicode(s)
    if usage == 'fileName':
        # Remove any char that can't be found within a file name under
        # Windows.
        res = ''
        for char in s:
            if char not in unwantedChars:
                res += char
        s = res
    return unicodedata.normalize('NFKD', s).encode("ascii","ignore")

# ------------------------------------------------------------------------------
typeLetters = {'b': bool, 'i': int, 'j': long, 'f':float, 's':str, 'u':unicode,
               'l': list, 'd': dict}
# ------------------------------------------------------------------------------
