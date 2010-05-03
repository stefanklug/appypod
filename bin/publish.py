#!/usr/bin/python2.4.4
# Imports ----------------------------------------------------------------------
import os, os.path, shutil, re, zipfile, sys, ftplib, time
from appy.shared import appyPath
from appy.shared.utils import FolderDeleter
from appy.bin.clean import Cleaner
from appy.gen.utils import produceNiceMessage

# ------------------------------------------------------------------------------
versionRex = re.compile('(\d+\.\d+\.\d+)')
eggInfo = '''import os, setuptools
setuptools.setup(
    name = "appy", version = "%s", description = "The Appy framework",
    long_description = "See http://appyframework.org",
    author = "Gaetan Delannay", author_email = "gaetan.delannay AT gmail.com",
    license = "GPL", keywords = "plone, pod, pdf, odt, document",
    url = 'http://appyframework.org',
    classifiers = ['Development Status :: 4 - Beta', "License :: OSI Approved"],
    packages = setuptools.find_packages('src'), include_package_data = True,
    package_dir = {'':'src'}, data_files = [('.', [])],
    namespace_packages = ['appy'], zip_safe = False)'''

def askLogin():
    print 'Login: ',
    login = sys.stdin.readline().strip()
    print 'Password: ',
    passwd = sys.stdin.readline().strip()
    return (login, passwd)

def askQuestion(question, default='yes'):
    '''Asks a question to the user (yes/no) and returns True if the user
        answered "yes".'''
    defaultIsYes = (default.lower() in ('y', 'yes'))
    if defaultIsYes:
        yesNo = '[Y/n]'
    else:
        yesNo = '[y/N]'
    print question + ' ' + yesNo + ' ',
    response = sys.stdin.readline().strip().lower()
    res = False
    if response in ('y', 'yes'):
        res = True
    elif response in ('n', 'no'):
        res = False
    elif not response:
        # It depends on default value
        if defaultIsYes:
            res = True
        else:
            res = False
    return res

class FtpFolder:
    '''Represents a folder on a FTP site.'''
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.subFolders = []
        self.files = []
        self.isComplete = False # Is True if all contained files and direct
        # subFolders were analysed.
    def getFullName(self):
        if not self.parent:
            res = '.'
        else:
            res = '%s/%s' % (self.parent.getFullName(), self.name)
        return res
    def addSubFolder(self, subFolder):
        self.subFolders.append(subFolder)
        subFolder.parent = self
    def isFullyComplete(self):
        res = self.isComplete
        for subFolder in self.subFolders:
            res = res and subFolder.isFullyComplete()
        return res
    def getIncompleteSubFolders(self):
        res = []
        for subFolder in self.subFolders:
            if not subFolder.isComplete:
                res.append(subFolder)
            elif not subFolder.isFullyComplete():
                res += subFolder.getIncompleteSubFolders()
        return res
    def __str__(self):
        res = 'Folder %s' % self.getFullName()
        if self.files:
            res += '\nFiles:\n'
            for f in self.files:
                res += '%s\n' % f
        if self.subFolders:
            res += '\nSubFolders:\n'
            for subFolder in self.subFolders:
                res += str(subFolder)
        return res
    def clean(self, site):
        '''Cleans this folder'''
        # First, clean subFolders if they exist
        for subFolder in self.subFolders:
            subFolder.clean(site)
            # Remove the subFolder
            site.rmd(subFolder.getFullName())
        # Then, remove the files contained in the folder.
        for f in self.files:
            fileName = '%s/%s' % (self.getFullName(), f)
            site.delete(fileName)

# ------------------------------------------------------------------------------
class AppySite:
    '''Represents the Appy web sie where the project is published.'''
    name = 'appyframework.org'
    textExtensions = ('.htm', '.html', '.css', '.txt')
    def __init__(self):
        # Delete the "egg" folder on not-yet-copied local site.
        eggFolder = '%s/temp/egg' % appyPath
        if os.path.isdir(eggFolder):
            FolderDeleter.delete(eggFolder)
        # Ask user id and password for FTP transfer
        userId, userPassword = askLogin()
        self.site = ftplib.FTP(self.name)
        self.site.login(userId, userPassword)
        self.rootFolder = None # Root folder of appy site ~FtpFolder~
        self.currentFolder = None # Currently visited folder ~FtpFolder~
    def analyseFolderEntry(self, folderEntry):
        '''p_line corresponds to a 'ls' entry.'''
        elems = folderEntry.split(' ')
        elemName = elems[len(elems)-1]
        if (not elemName.startswith('.')) and \
           (not elemName.startswith('_')):
            if elems[0].startswith('d'):
                self.currentFolder.addSubFolder(FtpFolder(elemName))
            else:
                self.currentFolder.files.append(elemName)
    def createFolderProxies(self):
        '''Creates a representation of the FTP folders of the appy site in the
        form of FtpFolder instances.'''
        self.rootFolder = FtpFolder('.')
        self.currentFolder = self.rootFolder
        self.site.dir(self.currentFolder.getFullName(), self.analyseFolderEntry)
        self.rootFolder.isComplete = True
        while not self.rootFolder.isFullyComplete():
            incompleteFolders = self.rootFolder.getIncompleteSubFolders()
            for folder in incompleteFolders:
                self.currentFolder = folder
                self.site.dir(self.currentFolder.getFullName(),
                              self.analyseFolderEntry)
                self.currentFolder.isComplete = True
    def copyFile(self, fileName):
        '''Copies a file on the FTP server.'''
        localFile = file(fileName)
        cmd = 'STOR %s' % fileName
        fileExt = os.path.splitext(fileName)[1]
        if fileExt in self.textExtensions:
            # Make a transfer in text mode
            print 'Transfer file %s (text mode)' % fileName
            self.site.storlines(cmd, localFile)
        else:
            # Make a transfer in binary mode
            print 'Transfer file %s (binary mode)' % fileName
            self.site.storbinary(cmd, localFile)
    def publish(self):
        # Delete the existing content of the distant site
        self.createFolderProxies()
        print 'Removing existing data on site...'
        self.rootFolder.clean(self.site)
        curDir = os.getcwd()
        os.chdir('%s/temp' % appyPath)
        for root, dirs, files in os.walk('.'):
            for folder in dirs:
                folderName = '%s/%s' % (root, folder)
                self.site.mkd(folderName)
            for f in files:
                fileName = '%s/%s' % (root, f)
                self.copyFile(fileName)
        os.chdir(curDir)
        self.site.close()

# ------------------------------------------------------------------------------
class Text2Html:
    '''Converts a text file into a HTML file.'''
    def __init__(self, txtFile, htmlFile):
        self.txtFile = file(txtFile)
        self.htmlFile = file(htmlFile, 'w')
    def retainLine(self, line):
        '''Must we dump this line in the result ?'''
        pass
    def getFirstChar(self, line):
        '''Gets the first relevant character of the line. For a TodoConverter
        this is not really the first one because lines taken into account start
        with a 'v' character.'''
        return line[self.firstChar]
    def getCleanLine(self, line, isTitle=False):
        '''Gets the line as it will be inserted in the HTML result: remove some 
        leading and trailing characters.'''
        start = self.firstChar
        if not isTitle:
            start += 1
        return line[start:-1]
    def getProlog(self):
        '''If you want to write a small prolog in the HTML file, you may
           generate it here.'''
        return ''
    def run(self):
        self.htmlFile.write('<html>\n\n<head><title>%s</title></head>\n\n' \
                            '<body>\n' % self.title)
        self.htmlFile.write(self.getProlog())
        inList = False
        for line in self.txtFile:
            if self.retainLine(line):
                firstChar = self.getFirstChar(line)
                if firstChar == '-':
                    if not inList:
                        # Begin a new bulleted list
                        self.htmlFile.write('<ul>\n')
                        inList = True
                    self.htmlFile.write(
                        '<li>%s</li>\n' % self.getCleanLine(line))
                elif firstChar == ' ':
                    pass
                else:
                    # It is a title
                    if inList:
                        self.htmlFile.write('</ul>\n')
                        inList = False
                    self.htmlFile.write(
                        '<h1>%s</h1>\n' % self.getCleanLine(line, True))
        self.htmlFile.write('\n</ul>\n</body>\n</html>')
        self.txtFile.close()
        self.htmlFile.close()

# ------------------------------------------------------------------------------
class Publisher:
    '''Publishes Appy on the web.'''
    pageBody = re.compile('<body.*?>(.*)</body>', re.S)
    eggVersion = re.compile('version\s*=\s*".*?"')
    pythonTargets = ('2.4', '2.5')
    svnServer = 'http://svn.communesplone.org/svn/communesplone/appy'

    def __init__(self):
        self.genFolder = '%s/temp' % appyPath
        self.ftp = None # FTP connection to appyframework.org
        # Retrieve version-related information
        versionFileName = '%s/doc/version.txt' % appyPath
        f = file(versionFileName)
        self.versionShort = f.read().strip()
        # Long version includes release date
        self.versionLong = '%s (%s)' % (self.versionShort,
                                        time.strftime('%Y/%m/%d %H:%M'))
        f.close()

    def executeCommand(self, cmd):
        '''Executes the system command p_cmd.'''
        print 'Executing %s...' % cmd
        os.system(cmd)

    def createCodeAndEggReleases(self):
        '''Publishes the egg on pypi.python.org.'''
        curdir = os.getcwd()
        if askQuestion('Upload eggs on PyPI?', default='no'):
            # Create egg structure
            eggFolder = '%s/egg' % self.genFolder
            os.mkdir(eggFolder)
            f = file('%s/setup.py' % eggFolder, 'w')
            f.write(eggInfo % self.versionShort)
            f.close()
            os.mkdir('%s/docs' % eggFolder)
            os.mkdir('%s/src' % eggFolder)
            os.mkdir('%s/src/appy' % eggFolder)
            shutil.copy('%s/doc/version.txt' % appyPath,
                        '%s/docs/HISTORY.txt' % eggFolder)
            shutil.copy('%s/doc/license.txt' % appyPath,
                        '%s/docs/LICENSE.txt' % eggFolder)
            # Move appy sources within the egg
            os.rename('%s/appy' % self.genFolder, '%s/src/appy' % eggFolder)
            # Create eggs and publish them on pypi
            os.chdir(eggFolder)
            print 'Uploading appy%s source egg on PyPI...' % self.versionShort
            #self.executeCommand('python setup.py sdist upload')
            self.executeCommand('python setup.py sdist')
            for pythonTarget in self.pythonTargets:
                print 'Uploading appy%s binary egg for python%s...' % \
                      (self.versionShort, pythonTarget)
                #self.executeCommand('python%s setup.py bdist_egg upload' % \
                #    pythonTarget)
                self.executeCommand('python%s setup.py bdist_egg' % \
                    pythonTarget)
        os.chdir(curdir)

    def createZipRelease(self):
        '''Creates a zip file with the appy sources.'''
        newZipRelease = '%s/versions/appy%s.zip' % (appyPath, self.versionShort)
        if os.path.exists(newZipRelease):
            if not askQuestion('"%s" already exists. Replace it?' % \
                               newZipRelease, default='yes'):
                print 'Publication cancelled.'
                sys.exit(1)
            print 'Removing obsolete %s...' % newZipRelease
            os.remove(newZipRelease)
        zipFile = zipfile.ZipFile(newZipRelease, 'w', zipfile.ZIP_DEFLATED)
        curdir = os.getcwd()
        os.chdir(self.genFolder)
        for dir, dirnames, filenames in os.walk('appy'):
            for f in filenames:
                fileName = os.path.join(dir, f)
                zipFile.write(fileName)
                # [2:] is there to avoid havin './' in the path in the zip file.
        zipFile.close()
        os.chdir(curdir)
        # Remove the "appy" folder within the gen folder.
        FolderDeleter.delete(os.path.join(self.genFolder, 'appy'))

    def applyTemplate(self):
        '''Decorates each page with the template.'''
        # First, load the template into memory
        templateFileName = '%s/doc/template.html' % appyPath
        templateFile = open(templateFileName)
        templateContent = templateFile.read()
        templateFile.close()
        # Then, decorate each other html file
        for pageName in os.listdir(self.genFolder):
            if pageName.endswith('.html'):
                pageFileName = '%s/%s' % (self.genFolder, pageName)
                pageFile = file(pageFileName)
                pageContent = pageFile.read()
                pageFile.close()
                # Extract the page title
                i, j = pageContent.find('<title>'), pageContent.find('</title>')
                pageTitle = pageContent[i+7:j]
                # Extract the body tag content from the page
                pageContent = self.pageBody.search(pageContent).group(1)
                pageFile = open(pageFileName, 'w')
                templateWithTitle = templateContent.replace('{{ title }}',
                                                            pageTitle)
                pageFile.write(templateWithTitle.replace('{{ content }}',
                                                         pageContent))
                pageFile.close()

    def _getPageTitle(self, url):
        '''Returns the documentation page title from its URL.'''
        res = url.split('.')[0]
        if res not in ('pod', 'gen'):
            res = produceNiceMessage(res[3:])
        return res

    mainToc = re.compile('<span class="doc"(.*?)</span>', re.S)
    tocLink = re.compile('<a href="(.*?)">(.*?)</a>')
    subSection = re.compile('<h1>(.*?)</h1>')
    subSectionContent = re.compile('<a name="(.*?)">.*?</a>(.*)')
    def createDocToc(self):
        res = '<table width="100%"><tr>'
        docToc = '%s/docToc.html' % self.genFolder
        # First, parse template.html to get the main TOC structure
        template = file('%s/doc/template.html' % appyPath)
        mainData = self.mainToc.search(template.read()).group(0)
        links = self.tocLink.findall(mainData)[1:]
        sectionNb = 0
        for url, title in links:
            if title in ('gen', 'pod'):
                tag = 'h1'
                indent = 0
                styleBegin = ''
                styleEnd = ''
                if title == 'pod':
                    res += '</td>'
                res += '<td>'
            else:
                tag = 'p'
                indent = 2
                styleBegin = '<i>'
                styleEnd = '</i>'
            tabs = '&nbsp;' * indent * 2
            res += '<%s>%s%s<a href="%s">%s</a>%s</%s>\n' % \
                   (tag, tabs, styleBegin, url, self._getPageTitle(url),
                    styleEnd, tag)
            # Parse each HTML file and retrieve sections title that have an
            # anchor defined
            docFile = file('%s/doc/%s' % (appyPath, url))
            docContent = docFile.read()
            docFile.close()
            sections = self.subSection.findall(docContent)
            for section in sections:
                r = self.subSectionContent.search(section)
                if r:
                    sectionNb += 1
                    tabs = '&nbsp;' * 8
                    res += '<div>%s%d. <a href="%s#%s">%s</a></div>\n' % \
                           (tabs, sectionNb, url, r.group(1), r.group(2))
        res += '</td></tr></table>'
        f = file(docToc)
        toc = f.read()
        f.close()
        toc = toc.replace('{{ doc }}', res)
        f = file(docToc, 'w')
        f.write(toc)
        f.close()

    privateScripts = ('publish.py', 'zip.py', 'runOpenOffice.sh')
    def prepareGenFolder(self):
        '''Creates the basic structure of the temp folder where the appy
           website will be generated.'''
        # Reinitialise temp folder where the generated website will be dumped
        if os.path.exists(self.genFolder):
            FolderDeleter.delete(self.genFolder)
        shutil.copytree('%s/doc' % appyPath, self.genFolder)
        # Create a temp clean copy of appy sources (without .svn folders, etc)
        genSrcFolder = '%s/appy' % self.genFolder
        os.mkdir(genSrcFolder)
        for aFile in ('__init__.py', 'install.txt'):
            shutil.copy('%s/%s' % (appyPath, aFile), genSrcFolder)
        for aFolder in ('gen', 'pod', 'shared', 'bin'):
            shutil.copytree('%s/%s' % (appyPath, aFolder),
                            '%s/%s' % (genSrcFolder, aFolder))
        # Remove some scripts from bin
        for script in self.privateScripts:
            os.remove('%s/bin/%s' % (genSrcFolder, script))
        # Write the appy version into the code itself (in appy/version.py)'''
        print 'Publishing version %s...' % self.versionShort
        # Dump version info in appy/version.py
        f = file('%s/version.py' % genSrcFolder, 'w')
        f.write('short = "%s"\n' % self.versionShort)
        f.write('verbose = "%s"' % self.versionLong)
        f.close()
        # Remove unwanted files
        os.remove('%s/version.txt' % self.genFolder)
        os.remove('%s/license.txt' % self.genFolder)
        os.remove('%s/template.html' % self.genFolder)
        os.remove('%s/artwork.odg' % self.genFolder)
        # Remove subversion folders
        for root, dirs, files in os.walk(self.genFolder):
            for dirName in dirs:
                if dirName == '.svn':
                    FolderDeleter.delete(os.path.join(root, dirName))

    def run(self):
        Cleaner().run(verbose=False)
        print 'Generating site in %s...' % self.genFolder
        self.prepareGenFolder()
        self.createDocToc()
        self.applyTemplate()
        self.createZipRelease()
        #self.createCodeAndEggReleases()
        if askQuestion('Do you want to publish the site on ' \
                       'appyframework.org?', default='no'):
            AppySite().publish()
        if askQuestion('Delete locally generated site ?', default='no'):
            FolderDeleter.delete(self.genFolder)

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    Publisher().run()
# ------------------------------------------------------------------------------
