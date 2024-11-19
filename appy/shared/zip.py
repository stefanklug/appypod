'''Functions for (un)zipping files'''

# ------------------------------------------------------------------------------
import os, os.path, zipfile, time
from appy.shared import mimeTypes

# ------------------------------------------------------------------------------
def unzip(f, folder, odf=False):
    '''Unzips file p_f into p_folder. p_f can be any anything accepted by the
       zipfile.ZipFile constructor. p_folder must exist.
       
       If p_odf is True, p_f is considered to be an odt or ods file and this
       function will return a dict containing the content of content.xml and
       styles.xml from the zipped file.'''
    zipFile = zipfile.ZipFile(f)
    if odf: res = {}
    else: res = None
    for zippedFile in zipFile.namelist():
        # Before writing the zippedFile into p_folder, create the intermediary
        # subfolder(s) if needed.
        fileName = None
        if zippedFile.endswith('/') or zippedFile.endswith(os.sep):
            # This is an empty folder. Create it nevertheless. If zippedFile
            # starts with a '/', os.path.join will consider it an absolute
            # path and will throw away folder.
            os.makedirs(os.path.join(folder, zippedFile.lstrip('/')))
        else:
            fileName = os.path.basename(zippedFile)
            folderName = os.path.dirname(zippedFile)
            fullFolderName = folder
            if folderName:
                fullFolderName = os.path.join(fullFolderName, folderName)
                if not os.path.exists(fullFolderName):
                    os.makedirs(fullFolderName)
        # Unzip the file in folder
        if fileName:
            fullFileName = os.path.join(fullFolderName, fileName)
            f = open(fullFileName, 'wb')
            fileContent = zipFile.read(zippedFile)
            if odf and not folderName:
                # content.xml and others may reside in subfolders. Get only the
                # one in the root folder.
                if fileName == 'content.xml':
                    res['content.xml'] = fileContent
                elif fileName == 'styles.xml':
                    res['styles.xml'] = fileContent
                elif fileName == 'mimetype':
                    res['mimetype'] = fileContent
            f.write(fileContent)
            f.close()
    zipFile.close()
    return res

# ------------------------------------------------------------------------------
def zip(f, folder, odf=False):
    '''Zips the content of p_folder into the zip file whose (preferably)
       absolute filename is p_f. If p_odf is True, p_folder is considered to
       contain the standard content of an ODF file (content.xml,...). In this
       case, some rules must be respected while building the zip (see below).'''
    # Remove p_f if it exists
    if os.path.exists(f): os.remove(f)
    try:
        zipFile = zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED)
    except RuntimeError:
        zipFile = zipfile.ZipFile(f, 'w')
    # If p_odf is True, insert first the file "mimetype" (uncompressed), in
    # order to be compliant with the OpenDocument Format specification,
    # section 17.4, that expresses this restriction. Else, libraries like
    # "magic", under Linux/Unix, are unable to detect the correct mimetype for
    # a pod result (it simply recognizes it as a "application/zip" and not a
    # "application/vnd.oasis.opendocument.text)".
    if odf:
        mimetypeFile = os.path.join(folder, 'mimetype')
        # This file may not exist (presumably, ods files from Google Drive)
        if not os.path.exists(mimetypeFile):
            f = file(mimetypeFile, 'w')
            f.write(mimeTypes[os.path.splitext(f)[-1][1:]])
            f.close()
        zipFile.write(mimetypeFile, 'mimetype', zipfile.ZIP_STORED)
    for dir, dirnames, filenames in os.walk(folder):
        folderName = os.path.relpath(dir, folder)
        for name in filenames:
            # For p_odf files, ignore file "mimetype" that was already inserted
            if odf and (folderName == '.') and (name == 'mimetype'): continue
            zipFile.write(os.path.join(dir,name), os.path.join(folderName,name))
        if not dirnames and not filenames:
            # This is an empty leaf folder. We must create an entry in the
            # zip for him.
            zInfo = zipfile.ZipInfo("%s/" % folderName, time.localtime()[:6])
            zInfo.external_attr = 48
            zipFile.writestr(zInfo, '')
    zipFile.close()
# ------------------------------------------------------------------------------
