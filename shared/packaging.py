# ------------------------------------------------------------------------------
import os, os.path, subprocess, md5, shutil
from appy.shared.utils import getOsTempFolder, FolderDeleter

# ------------------------------------------------------------------------------
debianInfo = '''Package: python-appy%s
Version: %s
Architecture: all
Maintainer: Gaetan Delannay <gaetan.delannay@geezteem.com>
Installed-Size: %d
Depends: python (>= %s), python (<= %s)%s
Section: python
Priority: optional
Homepage: http://appyframework.org
Description: Appy builds simple but complex web Python apps.
'''

class Debianizer:
    '''This class allows to produce a Debian package from a Python (Appy)
       package.'''

    def __init__(self, app, out, appVersion='0.1.0',
                 pythonVersions=('2.6', '2.7'),
                 depends=('zope2.12', 'openoffice.org')):
        # app is the path to the Python package to Debianize.
        self.app = app
        self.appName = os.path.basename(app)
        # out is the folder where the Debian package will be generated.
        self.out = out
        # What is the version number for this app ?
        self.appVersion = appVersion
        # On which Python versions will the Debian package depend?
        self.pythonVersions = pythonVersions
        # Debian package dependencies
        self.depends = depends

    def run(self):
        '''Generates the Debian package.'''
        curdir = os.getcwd()
        j = os.path.join
        tempFolder = getOsTempFolder()
        # Create, in the temp folder, the required sub-structure for the Debian
        # package.
        debFolder = j(tempFolder, 'debian')
        if os.path.exists(debFolder):
            FolderDeleter.delete(debFolder)
        # Copy the Python package into it
        srcFolder = j(debFolder, 'usr', 'lib')
        for version in self.pythonVersions:
            libFolder = j(srcFolder, 'python%s' % version)
            os.makedirs(libFolder)
            shutil.copytree(self.app, j(libFolder, self.appName))
        # Create data.tar.gz based on it.
        os.chdir(debFolder)
        os.system('tar czvf data.tar.gz ./usr')
        # Get the size of the app, in Kb.
        cmd = subprocess.Popen(['du', '-b', '-s', 'usr'],stdout=subprocess.PIPE)
        size = int(int(cmd.stdout.read().split()[0])/1024.0)
        # Create the control file
        f = file('control', 'w')
        nameSuffix = ''
        dependencies = []
        if self.appName != 'appy':
            nameSuffix = '-%s' % self.appName.lower()
            dependencies.append('python-appy')
        if self.depends:
            for d in self.depends: dependencies.append(d)
        depends = ''
        if dependencies:
            depends = ', ' + ', '.join(dependencies)
        f.write(debianInfo % (nameSuffix, self.appVersion, size,
                              self.pythonVersions[0], self.pythonVersions[1],
                              depends))
        f.close()
        # Create md5sum file
        f = file('md5sums', 'w')
        for dir, dirnames, filenames in os.walk('usr'):
            for name in filenames:
                m = md5.new()
                pathName = j(dir, name)
                currentFile = file(pathName, 'rb')
                while True:
                    data = currentFile.read(8096)
                    if not data:
                        break
                    m.update(data)
                currentFile.close()
                # Add the md5 sum to the file
                f.write('%s  %s\n' % (m.hexdigest(), pathName))
        f.close()
        # Create postinst, a script that will bytecompile Python files after the
        # Debian install.
        f = file('postinst', 'w')
        content = '#!/bin/sh\nset -e\n'
        for version in self.pythonVersions:
            content += 'if [ -e /usr/bin/python%s ]\nthen\n    ' \
                       '/usr/bin/python%s -m compileall -q ' \
                       '/usr/lib/python%s/%s 2> /dev/null\nfi\n' % \
                       (version, version, version, self.appName)
        f.write(content)
        f.close()
        # Create prerm, a script that will remove all pyc files before removing
        # the Debian package.
        f = file('prerm', 'w')
        content = '#!/bin/sh\nset -e\n'
        for version in self.pythonVersions:
            content += 'find /usr/lib/python%s/%s -name "*.pyc" -delete\n' % \
                       (version, self.appName)
        f.write(content)
        f.close()
        # Create control.tar.gz
        os.system('tar czvf control.tar.gz ./control ./md5sums ./postinst ' \
                  './prerm')
        # Create debian-binary
        f = file('debian-binary', 'w')
        f.write('2.0\n')
        f.close()
        # Create the .deb package
        debName = 'python-appy%s-%s.deb' % (nameSuffix, self.appVersion)
        os.system('ar -r %s debian-binary control.tar.gz data.tar.gz' % \
                  debName)
        # Move it to self.out
        os.rename(j(debFolder, debName), j(self.out, debName))
        # Clean temp files
        FolderDeleter.delete(debFolder)
        os.chdir(curdir)
# ------------------------------------------------------------------------------
