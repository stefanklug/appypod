'''This file contains the main Generator class used for generating an
   ODT file from an Appy application.'''

# ------------------------------------------------------------------------------
import os, os.path
from appy.gen import Page
from appy.gen.utils import produceNiceMessage
from appy.gen.generator import Generator as AbstractGenerator

# ------------------------------------------------------------------------------
class Generator(AbstractGenerator):
    '''This generator generates ODT files from an Appy application.'''

    def __init__(self, *args, **kwargs):
        AbstractGenerator.__init__(self, *args, **kwargs)
        self.repls = {'generator': self}

    def finalize(self):
        pass

    def getOdtFieldLabel(self, fieldName):
        '''Given a p_fieldName, this method creates the label as it will appear
           in the ODT file.'''
        return '<text:p><text:bookmark text:name="%s"/>%s</text:p>' % \
               (fieldName, produceNiceMessage(fieldName))

    def generateClass(self, classDescr):
        '''Is called each time an Appy class is found in the application.'''
        repls = self.repls.copy()
        repls['classDescr'] = classDescr
        self.copyFile('basic.odt', repls,
            destName='%sEdit.odt' % classDescr.klass.__name__, isPod=True)

    def fieldIsStaticallyInvisible(self, field):
        '''This method determines if p_field is always invisible. It can be
           verified for example if field.type.show is the boolean value False or
           if the page where the field must be displayed has a boolean attribute
           "show" having the boolean value False.'''
        if (type(field.show) == bool) and not field.show: return True
        if (type(field.pageShow) == bool) and not field.pageShow: return True
        return False

    undumpable = ('Ref', 'Action', 'File', 'Computed')
    def getRelevantAttributes(self, classDescr):
        '''Some fields, like computed fields or actions, should not be dumped
           into the ODT file. This method returns the list of "dumpable"
           fields.'''
        res = []
        for fieldName, field in classDescr.getOrderedAppyAttributes():
            if (field.type not in self.undumpable) and \
               (not self.fieldIsStaticallyInvisible(field)):
                res.append((fieldName, field))
        return res
# ------------------------------------------------------------------------------
