# ------------------------------------------------------------------------------
from appy.gen.plone25.mixins import AbstractMixin

# ------------------------------------------------------------------------------
class ClassMixin(AbstractMixin):
    _appy_meta_type = 'class'
    def _appy_fieldIsUsed(self, portalTypeName, fieldName):
        tool = self.getTool()
        flavour = tool.getFlavour(portalTypeName)
        optionalFieldsAccessor = 'getOptionalFieldsFor%s' % self.meta_type
        exec 'usedFields = flavour.%s()' % optionalFieldsAccessor
        res = False
        if fieldName in usedFields:
            res = True
        return res

    def _appy_getDefaultValueFor(self, portalTypeName, fieldName):
        tool = self.getTool()
        flavour = tool.getFlavour(portalTypeName)
        fieldFound = False
        klass = self.__class__
        while not fieldFound:
            metaType = klass.meta_type
            defValueAccessor = 'getDefaultValueFor%s_%s' % (metaType, fieldName)
            if not hasattr(flavour, defValueAccessor):
                # The field belongs to a super-class.
                klass = klass.__bases__[-1]
            else:
                fieldFound = True
        exec 'res = flavour.%s()' % defValueAccessor
        return res

    def fieldIsUsed(self, fieldName):
        '''Checks in the corresponding flavour if p_fieldName is used.'''
        portalTypeName = self._appy_getPortalType(self.REQUEST)
        return self._appy_fieldIsUsed(portalTypeName, fieldName)

    def getDefaultValueFor(self, fieldName):
        '''Gets in the flavour the default value for p_fieldName.'''
        portalTypeName = self._appy_getPortalType(self.REQUEST)
        return self._appy_getDefaultValueFor(portalTypeName,fieldName)
# ------------------------------------------------------------------------------
