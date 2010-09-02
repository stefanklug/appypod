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
import os, os.path, sys, traceback, unicodedata, shutil

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
extsToClean = ('.pyc', '.pyo')
def cleanFolder(folder, exts=extsToClean, verbose=False):
    '''This function allows to remove, in p_folder and subfolders, any file
       whose extension is in p_exts.'''
    if verbose: print 'Cleaning folder', folder, '...'
    # Remove files with an extension listed in exts
    for root, dirs, files in os.walk(folder):
        for fileName in files:
            ext = os.path.splitext(fileName)[1]
            if (ext in exts) or ext.endswith('~'):
                fileToRemove = os.path.join(root, fileName)
                if verbose: print 'Removing %s...' % fileToRemove
                os.remove(fileToRemove)


def copyFolder(source, dest, cleanDest=False):
    '''Copies the content of folder p_source to folder p_dest. p_dest is
       created, with intermediary subfolders if required. If p_cleanDest is
       True, it removes completely p_dest if it existed.'''
    dest = os.path.abspath(dest)
    # Delete the dest folder if required
    if os.path.exists(dest) and cleanDest:
        FolderDeleter.delete(dest)
    # Create the dest folder if it does not exist
    if not os.path.exists(dest):
        os.makedirs(dest)
    # Copy the content of p_source to p_dest.
    for name in os.listdir(source):
        sourceName = os.path.join(source, name)
        destName = os.path.join(dest, name)
        if os.path.isfile(sourceName):
            # Copy a single file
            shutil.copy(sourceName, destName)
        elif os.path.isdir(sourceName):
            # Copy a subfolder (recursively)
            copyFolder(sourceName, destName)

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
def executeCommand(cmd):
    '''Executes command p_cmd and returns the content of its stderr.'''
    childStdIn, childStdOut, childStdErr = os.popen3(cmd)
    res = childStdErr.read()
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
        # Windows or that could lead to problems with OpenOffice.
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
