# ------------------------------------------------------------------------------
# This file is part of Appy, a framework for building applications in the Python
# language. Copyright (C) 2007 Gaetan Delannay

# Appy is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.

# Appy is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# Appy. If not, see <http://www.gnu.org/licenses/>.

# ------------------------------------------------------------------------------
import time, os, os.path
from file import FileInfo
from appy import Object
from appy.fields import Field
from appy.px import Px
from appy.gen.layout import Table
from appy.gen import utils as gutils
from appy.pod import PodError
from appy.pod.renderer import Renderer
from appy.shared import utils as sutils

# ------------------------------------------------------------------------------
class Pod(Field):
    '''A pod is a field allowing to produce a (PDF, ODT, Word, RTF...) document
       from data contained in Appy class and linked objects or anything you
       want to put in it. It is the way gen uses pod.'''
    # Layout for rendering a POD field for exporting query results.
    rLayouts = {'view': Table('fl', width=None)}
    allFormats = ('pdf', 'doc', 'odt')
    POD_ERROR = 'An error occurred while generating the document. Please ' \
                'contact the system administrator.'
    NO_TEMPLATE = 'Please specify a pod template in field "template".'
    UNAVAILABLE_TEMPLATE = 'You are not allow to perform this action.'
    TEMPLATE_NOT_FOUND = 'Template not found at %s.'
    FREEZE_ERROR = 'Error while trying to freeze a "%s" file in pod field ' \
                    '"%s" (%s).'
    FREEZE_FATAL_ERROR = 'Server error. Please contact the administrator.'

    pxView = pxCell = Px('''
     <table cellpadding="0" cellspacing="0">
      <tr>
       <td for="template in field.getVisibleTemplates(obj)">
        <table cellpadding="0" cellspacing="0" class="podTable">
         <tr>
          <td for="fmt in field.getOutputFormats(obj)">
           <img src=":url(fmt)" title=":fmt.upper()" class="clickable"
                onclick=":'generatePodDocument(%s,%s,%s,%s,%s)' % \
                          (q(obj.uid), q(name), q(template), q(fmt), \
                           q(ztool.getQueryInfo()))"/>
          </td>
          <td class="podName">:field.getTemplateName(obj, template)</td>
         </tr>
        </table>
       </td>
      </tr>
     </table>''')

    pxEdit = pxSearch = ''

    def __init__(self, validator=None, default=None, show=('view', 'result'),
                 page='main', group=None, layouts=None, move=0, indexed=False,
                 searchable=False, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=None,
                 maxChars=None, colspan=1, master=None, masterValue=None,
                 focus=False, historized=False, mapping=None, label=None,
                 template=None, templateName=None, showTemplate=None,
                 context=None, stylesMapping={}, formats=None):
        # Param "template" stores the path to the pod template(s).
        if not template: raise Exception(Pod.NO_TEMPLATE)
        if isinstance(template, basestring):
            self.template = [template]
        else:
            self.template = template
        # Param "templateName", if specified, is a method that will be called
        # with the current template (from self.template) as single arg and must
        # return the name of this template. If self.template stores a single
        # template, you have no need to use param "templateName". Simply use the
        # field label to name the template. But if you have a multi-pod field
        # (with several templates specified as a list or tuple in param
        # "template"), you will probably choose to hide the field label and use
        # param "templateName" to give a specific name to every template. If
        # "template" contains several templates and "templateName" is None, Appy
        # will produce names from template filenames.
        self.templateName = templateName
        # "showTemplate", if specified, must be a method that will be called
        # with the current template as single arg and that must return True if
        # the template can be seen by the current user. "showTemplate" comes in
        # addition to self.show. self.show dictates the visibility of the whole
        # field (ie, all templates from self.template) while "showTemplate"
        # dictates the visiblity of a specific template within self.template.
        self.showTemplate = showTemplate
        # The context is a dict containing a specific pod context, or a method
        # that returns such a dict.
        self.context = context
        # A global styles mapping that would apply to the whole template
        self.stylesMapping = stylesMapping
        # What are the output formats when generating documents from this pod ?
        self.formats = formats
        if not formats:
            # Compute default ones
            if self.template[0].endswith('.ods'):
                self.formats = ('xls', 'ods')
            else:
                self.formats = ('pdf', 'doc', 'odt')
        Field.__init__(self, None, (0,1), default, show, page, group, layouts,
                       move, indexed, searchable, specificReadPermission,
                       specificWritePermission, width, height, None, colspan,
                       master, masterValue, focus, historized, mapping, label,
                       None, None, None, None, True)
        # Param "persist" is set to True but actually, persistence for a pod
        # field is determined by freezing.
        self.validable = False

    def getOutputFormats(self, obj):
        '''Returns self.formats, excepted if there is a frozen document: in
           this case, only the format of the frozen doc is returned.'''
        if not obj.user.has_role('Manager'): return self.formats
        # A manager can have all formats
        return self.allFormats

    def getTemplateName(self, obj, fileName):
        '''Gets the name of a template given its p_fileName.'''
        res = None
        if self.templateName:
            # Use the method specified in self.templateName.
            res = self.templateName(obj, fileName)
        # Else, deduce a nice name from p_fileName.
        if not res:
            name = os.path.splitext(os.path.basename(fileName))[0]
            res = gutils.produceNiceMessage(name)
        return res

    def getDownloadName(self, obj, template, format, queryRelated):
        '''Gets the name of the pod result as will be seen by the user that will
           download it.'''
        fileName = self.getTemplateName(obj, template)
        if not queryRelated:
            # This is a POD for a single object: personalize the file name with
            # the object title.
            fileName = '%s-%s' % (obj.title, fileName)
        return obj.tool.normalize(fileName) + '.' + format

    def getVisibleTemplates(self, obj):
        '''Returns, among self.template, the template(s) that can be shown.'''
        if not self.showTemplate: return self.template # Show them all.
        res = []
        for template in self.template:
            if self.showTemplate(obj, template):
                res.append(template)
        return res

    def getValue(self, obj, template=None, format=None, result=None):
        '''For a pod field, getting its value means computing a pod document or
           returning a frozen one. A pod field differs from other field types
           because there can be several ways to produce the field value (ie:
           self.template can hold various templates; output file format can be
           odt, pdf,.... We get those precisions about the way to produce the
           file, either:
           - from params p_template and p_format;
           - from the request object;
           - from default values (the request object may not be present, ie,
             when Zope runs in test mode).'''
        obj = obj.appy()
        rq = obj.request
        template = template or rq.get('template') or self.template[0]
        format = format or rq.get('podFormat') or 'odt'
        # Security check.
        if not self.showTemplate(obj, template):
            raise Exception(self.UNAVAILABLE_TEMPLATE)
        # Return the frozen document if frozen.
        frozen = self.isFrozen(obj, template, format)
        if frozen:
            print 'RETURN FROZEN'
            fileName = self.getDownloadName(obj, template, format, False)
            return FileInfo(frozen, inDb=False, uploadName=fileName)
        # We must call pod to compute a pod document from "template".
        tool = obj.tool
        diskFolder = tool.getDiskFolder()
        # Get the path to the pod template.
        templatePath = os.path.join(diskFolder, template)
        if not os.path.isfile(templatePath):
            raise Exception(self.TEMPLATE_NOT_FOUND % templatePath)
        # Get or compute the specific POD context
        specificContext = None
        if callable(self.context):
            specificContext = self.callMethod(obj, self.context)
        else:
            specificContext = self.context
        # Compute the name of the result file.
        if not result:
            result = '%s/%s_%f.%s' % (sutils.getOsTempFolder(),
                                      obj.uid, time.time(), format)
        # Define parameters to give to the appy.pod renderer
        podContext = {'tool': tool, 'user': obj.user, 'self': obj, 'field':self,
                      'now': obj.o.getProductConfig().DateTime(),
                      '_': obj.translate, 'projectFolder': diskFolder}
        # If the POD document is related to a query, get it from the request,
        # execute it and put the result in the context.
        isQueryRelated = rq.get('queryData', None)
        if isQueryRelated:
            # Retrieve query params from the request
            cmd = ', '.join(tool.o.queryParamNames)
            cmd += " = rq['queryData'].split(';')"
            exec cmd
            # (re-)execute the query, but without any limit on the number of
            # results; return Appy objects.
            objs = tool.o.executeQuery(obj.o.portal_type, searchName=search,
                     sortBy=sortKey, sortOrder=sortOrder, filterKey=filterKey,
                     filterValue=filterValue, maxResults='NO_LIMIT')
            podContext['objects'] = [o.appy() for o in objs.objects]
        # Add the field-specific context if present.
        if specificContext:
            podContext.update(specificContext)
        # If a custom param comes from the request, add it to the context. A
        # custom param must have form "name:value". Custom params override any
        # other value in the request, including values from the field-specific
        # context.
        customParams = rq.get('customParams', None)
        if customParams:
            paramsDict = eval(customParams)
            podContext.update(paramsDict)
        # Define a potential global styles mapping
        if callable(self.stylesMapping):
            stylesMapping = self.callMethod(obj, self.stylesMapping)
        else:
            stylesMapping = self.stylesMapping
        rendererParams = {'template': templatePath, 'context': podContext,
                          'result': result, 'stylesMapping': stylesMapping,
                          'imageResolver': tool.o.getApp(),
                          'overwriteExisting': True}
        if tool.unoEnabledPython:
            rendererParams['pythonWithUnoPath'] = tool.unoEnabledPython
        if tool.openOfficePort:
            rendererParams['ooPort'] = tool.openOfficePort
        # Launch the renderer
        try:
            renderer = Renderer(**rendererParams)
            renderer.run()
        except PodError, pe:
            if not os.path.exists(result):
                # In some (most?) cases, when OO returns an error, the result is
                # nevertheless generated.
                obj.log(str(pe).strip(), type='error')
                return Pod.POD_ERROR
        # Give a friendly name for this file
        fileName = self.getDownloadName(obj, template, format, isQueryRelated)
        # Get a FileInfo instance to manipulate the file on the filesystem.
        return FileInfo(result, inDb=False, uploadName=fileName)

    def getFreezeName(self, template=None, format='pdf'):
        '''Gets the name on disk on the frozen document corresponding to this
           pod field, p_template and p_format.'''
        template = template or self.template[0]
        templateName = os.path.splitext(template)[0].replace(os.sep, '_')
        return '%s_%s.%s' % (self.name, templateName, format)

    def isFrozen(self, obj, template=None, format='pdf'):
        '''Is there a frozen document for thid pod field, on p_obj, for
           p_template in p_format? If yes, it returns the absolute path to the
           frozen doc.'''
        template = template or self.template[0]
        dbFolder, folder = obj.o.getFsFolder()
        fileName = self.getFreezeName(template, format)
        res = os.path.join(dbFolder, folder, fileName)
        if os.path.exists(res): return res

    def freeze(self, obj, template=None, format='pdf'):
        '''Freezes, on p_obj, a document for this pod field, for p_template in
           p_format.'''
        # Compute the absolute path where to store the frozen document in the
        # database.
        dbFolder, folder = obj.o.getFsFolder(create=True)
        fileName = self.getFreezeName(template, format)
        result = os.path.join(dbFolder, folder, fileName)
        if os.path.exists(result):
            obj.log('Freeze: overwriting %s...' % result)
        # Generate the document.
        doc = self.getValue(obj, template=template, format=format,
                            result=result)
        if isinstance(doc, basestring):
            # An error occurred, the document was not generated.
            obj.log(self.FREEZE_ERROR % (format, self.name, doc), type='error')
            if format == 'odt': raise Exception(self.FREEZE_FATAL_ERROR)
            obj.log('Trying to freeze the ODT version...')
            # Try to freeze the ODT version of the document, which does not
            # require to call LibreOffice: the risk of error is smaller.
            fileName = self.getFreezeName(template, 'odt')
            result = os.path.join(dbFolder, folder, fileName)
            if os.path.exists(result):
                obj.log('Freeze: overwriting %s...' % result)
            doc = self.getValue(obj, template=template, format='odt',
                                result=result)
            if isinstance(doc, basestring):
                self.log(self.FREEZE_ERROR % ('odt', self.name, doc),
                         type='error')
                raise Exception(self.FREEZE_FATAL_ERROR)
        return doc

    def unfreeze(self, obj, template=None, format='pdf'):
        '''Unfreezes, on p_obj, the document for this pod field, for p_template
           in p_format.'''
        # Compute the absolute path to the frozen doc.
        dbFolder, folder = obj.o.getFsFolder()
        fileName = self.getFreezeName(template, format)
        frozenName = os.path.join(dbFolder, folder, fileName)
        if os.path.exists(frozenName): os.remove(frozenName)
# ------------------------------------------------------------------------------
