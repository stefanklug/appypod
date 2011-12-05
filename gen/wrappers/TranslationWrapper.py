# ------------------------------------------------------------------------------
import os.path
from appy.gen.wrappers import AbstractWrapper
from appy.gen.po import PoFile, PoMessage
from appy.shared.utils import getOsTempFolder

# ------------------------------------------------------------------------------
class TranslationWrapper(AbstractWrapper):
    def label(self, field):
        '''The label for a text to translate displays the text of the
           corresponding message in the source translation.'''
        tool = self.tool
        sourceLanguage = self.o.getProductConfig().sourceLanguage
        sourceTranslation = getattr(tool.o, sourceLanguage).appy()
        # p_field is the Computed field. We need to get the name of the
        # corresponding field holding the translation message.
        fieldName = field.name[:-6]
        # If we are showing the source translation, we do not repeat the message
        # in the label.
        if self.id == sourceLanguage:
            sourceMsg = ''
        else:
            sourceMsg = getattr(sourceTranslation,fieldName)
            # When editing the value, we don't want HTML code to be interpreted.
            # This way, the translator sees the HTML tags and can reproduce them
            # in the translation.
            url = self.request['URL']
            if url.endswith('/ui/edit') or url.endswith('/do'):
                sourceMsg = sourceMsg.replace('<','&lt;').replace('>','&gt;')
            sourceMsg = sourceMsg.replace('\n', '<br/>')
        return '<div class="translationLabel"><acronym title="%s">' \
               '<img src="ui/help.png"/></acronym>%s</div>' % \
               (fieldName, sourceMsg)

    def show(self, field):
        '''We show a field (or its label) only if the corresponding source
           message is not empty.'''
        tool = self.tool
        if field.type == 'Computed': name = field.name[:-6]
        else: name = field.name
        # Get the source message
        sourceLanguage = self.o.getProductConfig().sourceLanguage
        sourceTranslation = getattr(tool.o, sourceLanguage).appy()
        sourceMsg = getattr(sourceTranslation, name)
        if field.isEmptyValue(sourceMsg): return False
        return True

    poReplacements = ( ('\r\n', '<br/>'), ('\n', '<br/>'), ('"', '\\"') )
    def getPoFile(self):
        '''Computes and returns the PO file corresponding to this
           translation.'''
        tool = self.tool
        fileName = os.path.join(getOsTempFolder(),
                                '%s-%s.po' % (tool.o.getAppName(), self.id))
        poFile = PoFile(fileName)
        for field in self.fields:
            if (field.name == 'title') or (field.type != 'String'): continue
            # Adds the PO message corresponding to this field
            msg = field.getValue(self.o) or ''
            for old, new in self.poReplacements:
                msg = msg.replace(old, new)
            poFile.addMessage(PoMessage(field.name, msg, ''))
        poFile.generate()
        return True, file(fileName)

    def validate(self, new, errors):
        # Call a custom "validate" if any.
        return self._callCustom('validate', new, errors)

    def onEdit(self, created):
        # Call a custom "onEdit" if any.
        return self._callCustom('onEdit', created)

    def onDelete(self):
        # Call a custom "onDelete" if any.
        self.log('Translation "%s" deleted by "%s".' % (self.id, self.user.id))
        return self._callCustom('onDelete')
# ------------------------------------------------------------------------------
