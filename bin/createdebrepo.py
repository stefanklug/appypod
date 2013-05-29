#!/usr/bin/python

'''This script can be created on a Linux machine for creating a local Debian
(binary) repository.'''

import os, os.path

# Packages apache2 and dpkg-dev must be installed on the machine for enabling
# the Debian repository.
repoFolder = '/var/www/debianrepo'

# Create the repo folder if it does not exist
binaryFolder = os.path.join(repoFolder, 'binary')
if not os.path.exists(binaryFolder):
    os.makedirs(binaryFolder)

# Create the script that will allow to recompute indexes when packages are
# added or updated into the repository.
refreshScript = '''#!/bin/bash
cd %s
echo "(Re-)building indexes for binary packages..."
dpkg-scanpackages binary /dev/null | gzip -9c > binary/Packages.gz
echo "Done."
''' % repoFolder

curdir = os.getcwd()
os.chdir(repoFolder)
scriptName = os.path.join(repoFolder, 'refresh.sh')
if not os.path.exists(scriptName):
    f = file(scriptName, 'w')
    f.write(refreshScript)
    f.close()
os.system('chmod -R 755 %s' % repoFolder)
os.chdir(curdir)
print('Repository created.')
