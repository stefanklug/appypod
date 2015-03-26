# ------------------------------------------------------------------------------
import re

# ------------------------------------------------------------------------------
def parseStyleAttribute(value, asDict=False):
    '''Returns a list of CSS (name, value) pairs (or a dict if p_asDict is
       True), parsed from p_value, which holds the content of a HTML "style"
       tag.'''
    if asDict: res = {}
    else:      res = []
    for attr in value.split(';'):
        if not attr.strip(): continue
        name, value = attr.split(':')
        if asDict: res[name.strip()] = value.strip()
        else:      res.append( (name.strip(), value.strip()) )
    return res

# ------------------------------------------------------------------------------
class CssValue:
    '''Represents a CSS value having unit "px" or "%": value and unit are
       extracted in attributes of the same name. If no unit is specified, "px"
       is assumed.'''
    valueRex = re.compile('(\d+)(%|px)?')

    def __init__(self, value):
        value, unit = CssValue.valueRex.match(value)
        if not unit: unit = 'px'
        self.value = int(value)
        self.unit = unit
    def __str__(self): return '%d%s' % (self.value, self.unit)
    def __repr__(self): return self.__str__()

class CssStyles:
    '''This class represents a set of styles collected from:
       * an HTML "style" attribute;
       * other attributes like "width".
    '''
    # The list of CSS properties having a unit (px or %)
    withUnit = ('width', 'height')

    def __init__(self, elem, attrs):
        '''Analyses styles as found in p_attrs and sets, for every found style,
           an attribute on self.'''
        # First, parse the "style" attr if present
        if attrs.has_key('style'):
            styles = parseStyleAttribute(attrs['style'], asDict=True)
            for name, value in styles.iteritems():
                if name in CssStyles.withUnit:
                    value = CssValue(value)
                setattr(self, name.replace('-', ''), value)
        # Parse attributes "width" and "height" if present. But they will not
        # override corresponding attributes from the "styles" attributes if
        # found.
        for name in ('width', 'height'):
            if not hasattr(self, name) and attrs.has_key(name):
                setattr(self, name, CssValue(attrs[name]))

    def __repr__(self):
        res = '<CSS'
        for name, value in self.__dict__.iteritems():
            res += ' %s:%s' % (name, value)
        return res + '>'
# ------------------------------------------------------------------------------
