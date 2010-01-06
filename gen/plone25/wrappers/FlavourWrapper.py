# ------------------------------------------------------------------------------
class FlavourWrapper:

    def onEdit(self, created):
        if created:
            nbOfFlavours = len(self.tool.flavours)
            if nbOfFlavours != 1:
                self.number = nbOfFlavours
                self.o.registerPortalTypes()
        # Call the custom flavour "onEdit" method if it exists
        customFlavour = self.__class__.__bases__[1]
        if customFlavour.__name__ != 'Flavour':
            # There is a custom flavour
            if customFlavour.__dict__.has_key('onEdit'):
                customFlavour.__dict__['onEdit'](self, created)

    def getAttributeName(self, attributeType, klass, attrName=None):
        '''Some names of Flavour attributes are not easy to guess. For example,
           the attribute that stores, for a given flavour, the POD templates
           for class A that is in package x.y is "flavour.podTemplatesForx_y_A".
           Other example: the attribute that stores the editable default value
           of field "f1" of class x.y.A is "flavour.defaultValueForx_y_A_f1".
           This method generates the attribute name based on p_attributeType,
           a p_klass from the application, and a p_attrName (given only if
           needed, for example if p_attributeType is "defaultValue").
           p_attributeType may be:

           "defaultValue"
               Stores the editable default value for a given p_attrName of a
               given p_klass.

           "podTemplates"
               Stores the POD templates that are defined for a given p_klass.

           "podMaxShownTemplates"
               Stores the maximum number of POD templates shown at once. If the
               number of available templates is higher, templates are shown in a
               drop-down list.

           "resultColumns"
               Stores the list of columns that must be show when displaying
               instances of the a given root p_klass.

           "enableAdvancedSearch"
               Determines if the advanced search screen must be enabled for
               p_klass.

           "numberOfSearchColumns"
               Determines in how many columns the search screen for p_klass
               is rendered.

           "searchFields"
               Determines, among all indexed fields for p_klass, which one will
               really be used in the search screen.

           "optionalFields"
               Stores the list of optional attributes that are in use in the
               current flavour for the given p_klass.

           "showWorkflow"
               Stores the boolean field indicating if we must show workflow-
               related information for p_klass or not.

           "showWorkflowCommentField"
               Stores the boolean field indicating if we must show the field
               allowing to enter a comment every time a transition is triggered.

           "showAllStatesInPhase"
               Stores the boolean field indicating if we must show all states
               linked to the current phase or not. If this field is False, we
               simply show the current state, be it linked to the current phase
               or not.
        '''
        fullClassName = '%s_%s' % (klass.__module__.replace('.', '_'),
                                   klass.__name__)
        res = '%sFor%s' % (attributeType, fullClassName)
        if attrName: res += '_%s' % attrName
        return res
# ------------------------------------------------------------------------------
