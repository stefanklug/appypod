'''Appy allows you to create easily complete applications in Python.'''

# ------------------------------------------------------------------------------
import os.path


# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------


class Object:
    '''At every place we need an object, but without any requirement on its
       class (methods, attributes,...) we will use this minimalist class.'''

    def __init__(self, **fields):
        for k, v in fields.items():
            setattr(self, k, v)

    def __repr__(self):
        res = '<Object '
        for attrName, attrValue in self.__dict__.items():
            v = attrValue
            if hasattr(v, '__repr__'):
                v = v.__repr__()
            try:
                res += '%s=%s ' % (attrName, v)
            except UnicodeDecodeError:
                res += '%s=<encoding problem> ' % attrName
        res = res.strip() + '>'
        return res.encode('utf-8')

    def __bool__(self):
        return bool(self.__dict__)

    def get(self, name, default=None): return getattr(self, name, default)
    def __getitem__(self, k): return getattr(self, k)

    def update(self, other):
        '''Includes information from p_other into p_self.'''
        for k, v in other.__dict__.items():
            setattr(self, k, v)

    def clone(self):
        res = Object()
        res.update(self)
        return res

# ------------------------------------------------------------------------------


class Hack:
    '''This class proposes methods for patching some existing code with
       alternative methods.'''
    @staticmethod
    def patch(method, replacement, klass=None):
        '''This method replaces m_method with a p_replacement method, but
           keeps p_method on its class under name
           "_base_<initial_method_name>_". In the patched method, one may use
           Hack.base to call the base method. If p_method is static, you must
           specify its class in p_klass.'''
        # Get the class on which the surgery will take place.
        isStatic = klass
        klass = klass or method.__self__.__class__
        # On this class, store m_method under its "base" name.
        name = isStatic and method.__name__ or method.__func__.__name__
        baseName = '_base_%s_' % name
        if isStatic:
            # If "staticmethod" isn't called hereafter, the static functions
            # will be wrapped in methods.
            method = staticmethod(method)
            replacement = staticmethod(replacement)
        setattr(klass, baseName, method)
        setattr(klass, name, replacement)

    @staticmethod
    def base(method, klass=None):
        '''Allows to call the base (replaced) method. If p_method is static,
           you must specify its p_klass.'''
        isStatic = klass
        klass = klass or method.__self__.__class__
        name = isStatic and method.__name__ or method.__func__.__name__
        return getattr(klass, '_base_%s_' % name)

    @staticmethod
    def inject(patchClass, klass, verbose=False):
        '''Injects any method or attribute from p_patchClass into klass.'''
        patched = []
        added = []
        for name, attr in patchClass.__dict__.items():
            if name.startswith('__'):
                continue  # Ignore special methods
            # Unwrap functions from static methods
            if attr.__class__.__name__ == 'staticmethod':
                attr = attr.__get__(attr)
                static = True
            else:
                static = False
            # Is this name already defined on p_klass ?
            if hasattr(klass, name):
                hasAttr = True
                klassAttr = getattr(klass, name)
            else:
                hasAttr = False
                klassAttr = None
            if hasAttr and callable(attr) and callable(klassAttr):
                # Patch this method via Hack.patch
                if static:
                    Hack.patch(klassAttr, attr, klass)
                else:
                    Hack.patch(klassAttr, attr)
                patched.append(name)
            else:
                # Simply replace the static attr or add the new static
                # attribute or method.
                setattr(klass, name, attr)
                added.append(name)
        if verbose:
            pName = patchClass.__name__
            cName = klass.__name__
            print('%d method(s) patched from %s to %s (%s)' %
                  (len(patched), pName, cName, str(patched)))
            print('%d method(s) and/or attribute(s) added from %s to %s (%s)' %
                  (len(added), pName, cName, str(added)))
# ------------------------------------------------------------------------------
