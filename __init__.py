import os.path

def getPath(): return os.path.dirname(__file__)
def versionIsGreaterThanOrEquals(version):
    '''This method returns True if the current Appy version is greater than or
       equals p_version. p_version must have a format like "0.5.0".'''
    import appy.version
    if appy.version.short == 'dev':
        # We suppose that a developer knows what he is doing, so we return True.
        return True
    else:
        paramVersion = [int(i) for i in version.split('.')]
        currentVersion = [int(i) for i in appy.version.short.split('.')]
        return currentVersion >= paramVersion
