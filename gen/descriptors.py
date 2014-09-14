'''Descriptor classes defined in this file are "intermediary" classes that
   gather, from the user application, information about found gen- or workflow-
   classes.'''

# ------------------------------------------------------------------------------
import types, copy
import appy.gen as gen
import po
from model import ModelClass
from utils import produceNiceMessage, getClassName
TABS = 4 # Number of blanks in a Python indentation.

# ------------------------------------------------------------------------------
class Descriptor: # Abstract
    def __init__(self, klass, orderedAttributes, generator):
        # The corresponding Python class
        self.klass = klass
        # The names of the static appy-compliant attributes declared in
        # self.klass
        self.orderedAttributes = orderedAttributes
        # A reference to the code generator.
        self.generator = generator

    def __repr__(self): return '<Class %s>' % self.klass.__name__

class ClassDescriptor(Descriptor):
    '''This class gives information about an Appy class.'''

    def __init__(self, klass, orderedAttributes, generator):
        Descriptor.__init__(self, klass, orderedAttributes, generator)
        self.methods = '' # Needed method definitions will be generated here
        self.name = getClassName(self.klass, generator.applicationName)
        self.predefined = False
        self.customized = False
        # Phase and page names will be calculated later, when first required.
        self.phases = None
        self.pages = None

    def getOrderedAppyAttributes(self, condition=None):
        '''Returns the appy types for all attributes of this class and parent
           class(es). If a p_condition is specified, ony Appy types matching
           the condition will be returned. p_condition must be a string
           containing an expression that will be evaluated with, in its context,
           "self" being this ClassDescriptor and "attrValue" being the current
           Type instance.
           
           Order of returned attributes already takes into account type's
           "move" attributes.'''
        attrs = []
        # First, get the attributes for the current class
        for attrName in self.orderedAttributes:
            try:
                attrValue = getattr(self.klass, attrName)
                hookClass = self.klass
            except AttributeError:
                attrValue = getattr(self.modelClass, attrName)
                hookClass = self.modelClass
            if isinstance(attrValue, gen.Field):
                if not condition or eval(condition):
                    attrs.append( (attrName, attrValue, hookClass) )
        # Then, add attributes from parent classes
        for baseClass in self.klass.__bases__:
            # Find the classDescr that corresponds to baseClass
            baseClassDescr = None
            for classDescr in self.generator.classes:
                if classDescr.klass == baseClass:
                    baseClassDescr = classDescr
                    break
            if baseClassDescr:
                attrs = baseClassDescr.getOrderedAppyAttributes() + attrs
        # Modify attributes order by using "move" attributes
        res = []
        for name, appyType, klass in attrs:
            if appyType.move:
                newPosition = len(res) - abs(appyType.move)
                if newPosition <= 0:
                    newPosition = 0
                res.insert(newPosition, (name, appyType, klass))
            else:
                res.append((name, appyType, klass))
        return res

    def getChildren(self):
        '''Returns, among p_allClasses, the classes that inherit from p_self.'''
        res = []
        for classDescr in self.generator.classes:
            if (classDescr.klass != self.klass) and \
               issubclass(classDescr.klass, self.klass):
                res.append(classDescr)
        return res

    def getPhases(self):
        '''Lazy-gets the phases defined on fields of this class.'''
        if not hasattr(self, 'phases') or (self.phases == None):
            self.phases = []
            for fieldName, appyType, klass in self.getOrderedAppyAttributes():
                if appyType.page.phase in self.phases: continue
                self.phases.append(appyType.page.phase)
        return self.phases

    def getPages(self):
        '''Lazy-gets the page names defined on fields of this class.'''
        if not hasattr(self, 'pages') or (self.pages == None):
            self.pages = []
            for fieldName, appyType, klass in self.getOrderedAppyAttributes():
                if appyType.page.name in self.pages: continue
                self.pages.append(appyType.page.name)
        return self.pages

    def getParents(self, allClasses):
        parentWrapper = 'AbstractWrapper'
        parentClass = '%s.%s' % (self.klass.__module__, self.klass.__name__)
        if self.klass.__bases__:
            baseClassName = self.klass.__bases__[0].__name__
            for k in allClasses:
                if self.klass.__name__ == baseClassName:
                    parentWrapper = '%s_Wrapper' % k.name
        return (parentWrapper, parentClass)

    def generateSchema(self):
        '''Generates i18n and other related stuff for this class.'''
        for attrName in self.orderedAttributes:
            try:
                attrValue = getattr(self.klass, attrName)
            except AttributeError:
                attrValue = getattr(self.modelClass, attrName)
            if not isinstance(attrValue, gen.Field): continue
            FieldDescriptor(attrName, attrValue, self).generate()

    def isAbstract(self):
        '''Is self.klass abstract?'''
        res = False
        if self.klass.__dict__.has_key('abstract'):
            res = self.klass.__dict__['abstract']
        return res

    def isRoot(self):
        '''Is self.klass root? A root class represents some kind of major
           concept into the application. For example, creating instances
           of such classes will be easy from the user interface.'''
        res = False
        if self.klass.__dict__.has_key('root'):
            res = self.klass.__dict__['root']
        return res

    def isFolder(self, klass=None):
        '''Must self.klass be a folder? If klass is not None, this method tests
           it on p_klass instead of self.klass.'''
        res = False
        theClass = self.klass
        if klass:
            theClass = klass
        if theClass.__dict__.has_key('folder'):
            res = theClass.__dict__['folder']
        else:
            if theClass.__bases__:
                res = self.isFolder(theClass.__bases__[0])
        return res

    def getCreators(self):
        '''Gets the specific creators defined for this class, excepted if
           attribute "creators" does not contain a list or roles.'''
        res = []
        if not hasattr(self.klass, 'creators'): return res
        if not isinstance(self.klass.creators, list): return res
        for creator in self.klass.creators:
            if isinstance(creator, gen.Role):
                if creator.local:
                    raise 'Local role "%s" cannot be used as a creator.' % \
                          creator.name
                res.append(creator)
            else:
                res.append(gen.Role(creator))
        return res

    def getCreateMean(self, type='Import'):
        '''Returns the mean for this class that corresponds to p_type, or
           None if the class does not support this create mean.'''
        if not self.klass.__dict__.has_key('create'): return
        else:
            means = self.klass.create
            if not means: return
            if not isinstance(means, tuple) and not isinstance(means, list):
                means = [means]
            for mean in means:
                exec 'found = isinstance(mean, %s)' % type
                if found: return mean

    @staticmethod
    def getSearches(klass, tool=None):
        '''Returns the list of searches that are defined on this class. If
           p_tool is given, we are at execution time (not a generation time),
           and we may potentially execute search.show methods that allow to
           conditionnaly include a search or not.'''
        if klass.__dict__.has_key('search'):
            searches = klass.__dict__['search']
            if not tool: return searches
            # Evaluate attributes "show" for every search.
            return [s for s in searches if s.isShowable(klass, tool)]
        return []

    @staticmethod
    def getSearch(klass, searchName):
        '''Gets the search named p_searchName.'''
        for search in ClassDescriptor.getSearches(klass):
            if search.name == searchName:
                return search

    def addIndexMethod(self, field):
        '''For indexed p_field, this method generates a method that allows to
           get the value of the field as must be copied into the corresponding
           index.'''
        m = self.methods
        spaces = TABS
        n = field.fieldName
        m += '\n' + ' '*spaces + 'def get%s%s(self):\n' % (n[0].upper(), n[1:])
        spaces += TABS
        m += ' '*spaces + "'''Gets indexable value of field \"%s\".'''\n" % n
        m += ' '*spaces + 'return self.getAppyType("%s").getIndexValue(' \
             'self)\n' % n
        self.methods = m

    def addField(self, fieldName, fieldType):
        '''Adds a new field to the Tool.'''
        exec "self.modelClass.%s = fieldType" % fieldName
        if fieldName in self.modelClass._appy_attributes:
            print('Warning, field "%s" is already existing on class "%s"' % \
                  (fieldName, self.modelClass.__name__))
            return
        self.modelClass._appy_attributes.append(fieldName)
        self.orderedAttributes.append(fieldName)

# ------------------------------------------------------------------------------
class WorkflowDescriptor(Descriptor):
    '''This class gives information about an Appy workflow.'''
    @staticmethod
    def getWorkflowName(klass):
        '''Returns the name of this workflow.'''
        res = klass.__module__.replace('.', '_') + '_' + klass.__name__
        return res.lower()

# ------------------------------------------------------------------------------
class FieldDescriptor:
    '''This class gathers information about a specific typed attribute defined
       in a gen-class.'''

    def __init__(self, fieldName, appyType, classDescriptor):
        self.appyType = appyType
        self.classDescr = classDescriptor
        self.generator = classDescriptor.generator
        self.applicationName = classDescriptor.generator.applicationName
        self.fieldName = fieldName
        self.fieldParams = {'name': fieldName}
        self.widgetParams = {}
        self.fieldType = None
        self.widgetType = None

    def i18n(self, id, default, nice=True):
        '''Shorthand for adding a new message into self.generator.labels.'''
        self.generator.labels.append(id, default, nice=nice)

    def __repr__(self):
        return '<Field %s, %s>' % (self.fieldName, self.classDescr)

    def produceMessage(self, msgId, isLabel=True):
        '''Gets the default label, description or help (depending on p_msgType)
           for i18n message p_msgId.'''
        default = ' '
        niceDefault = False
        if isLabel:
            niceDefault = True
            default = self.fieldName
        return msgId, default, niceDefault

    def walkString(self):
        '''Generates String-specific i18n labels.'''
        if self.appyType.isSelect and \
           (type(self.appyType.validator) in (list, tuple)):
            # Generate i18n messages for every possible value if the list
            # of values is fixed.
            for value in self.appyType.validator:
                label = '%s_%s_list_%s' % (self.classDescr.name,
                                           self.fieldName, value)
                self.i18n(label, value)

    def walkBoolean(self):
        '''Generates Boolean-specific i18n labels.'''
        if self.appyType.render == 'radios':
            for v in ('true', 'false'):
                label = '%s_%s_%s' % (self.classDescr.name, self.fieldName, v)
                self.i18n(label, self.appyType.yesNo[v])

    def walkAction(self):
        '''Generates Action-specific i18n labels.'''
        if self.appyType.confirm:
            label = '%s_%s_confirm' % (self.classDescr.name, self.fieldName)
            self.i18n(label, po.CONFIRM, nice=False)

    def walkRef(self):
        '''How to generate a Ref?'''
        # Add the label for the confirm message if relevant
        if self.appyType.addConfirm:
            label = '%s_%s_addConfirm' % (self.classDescr.name, self.fieldName)
            self.i18n(label, po.CONFIRM, nice=False)

    def walkList(self):
        # Add i18n-specific messages
        for name, field in self.appyType.fields:
            label = '%s_%s_%s' % (self.classDescr.name, self.fieldName, name)
            self.i18n(label, name)
            if field.hasDescr:
                self.i18n('%s_descr' % label, ' ')
            if field.hasHelp:
                self.i18n('%s_help' % label, ' ')

    def walkCalendar(self):
        # Add i18n-specific messages
        eTypes = self.appyType.eventTypes
        if not isinstance(eTypes, list) and not isinstance(eTypes, tuple):return
        for et in self.appyType.eventTypes:
            label = '%s_%s_event_%s' % (self.classDescr.name,self.fieldName,et)
            self.i18n(label, et)

    def walkAppyType(self):
        '''Walks into the Appy type definition and gathers data about the
           i18n labels.'''
        # Manage things common to all Appy types
        # Put an index on this field?
        if self.appyType.indexed and (self.fieldName != 'title'):
            self.classDescr.addIndexMethod(self)
        # i18n labels
        if not self.appyType.label:
            # Create labels for generating them in i18n files, only if required.
            i18nPrefix = '%s_%s' % (self.classDescr.name, self.fieldName)
            if self.appyType.hasLabel:
                self.i18n(*self.produceMessage(i18nPrefix))
            if self.appyType.hasDescr:
                descrId = i18nPrefix + '_descr'
                self.i18n(*self.produceMessage(descrId,isLabel=False))
            if self.appyType.hasHelp:
                helpId = i18nPrefix + '_help'
                self.i18n(*self.produceMessage(helpId, isLabel=False))
        # Create i18n messages linked to pages and phases, only if there is more
        # than one page/phase for the class.
        if len(self.classDescr.getPhases()) > 1:
            # Create the message for the name of the phase
            phaseName = self.appyType.page.phase
            msgId = '%s_phase_%s' % (self.classDescr.name, phaseName)
            self.i18n(msgId, phaseName)
        if len(self.classDescr.getPages()) > 1:
            # Create the message for the name of the page
            pageName = self.appyType.page.name
            msgId = '%s_page_%s' % (self.classDescr.name, pageName)
            self.i18n(msgId, pageName)
        # Create i18n messages linked to groups
        group = self.appyType.group
        if group and not group.label:
            group.generateLabels(self.generator.labels, self.classDescr, set())
        # Generate type-specific i18n labels
        if not self.appyType.label:
            method = 'walk%s' % self.appyType.type
            if hasattr(self, method): getattr(self, method)()

    def generate(self):
        '''Generates the i18n labels for this type.'''
        self.walkAppyType()

# ------------------------------------------------------------------------------
class ToolClassDescriptor(ClassDescriptor):
    '''Represents the POD-specific fields that must be added to the tool.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False

    def getParents(self, allClasses=()):
        res = ['Tool']
        if self.customized:
            res.append('%s.%s' % (self.klass.__module__, self.klass.__name__))
        return res

    def update(self, klass, attributes):
        '''This method is called by the generator when he finds a custom tool
           definition. We must then add the custom tool elements in this default
           Tool descriptor.'''
        self.orderedAttributes += attributes
        self.klass = klass
        self.customized = True

    def isFolder(self, klass=None): return True
    def isRoot(self): return False

    def addImportRelatedFields(self, classDescr):
        '''Adds, for class p_classDescr, attributes related to the import
           functionality for class p_classDescr.'''
        className = classDescr.name
        # Field that defines the path of the files to import.
        fieldName = 'importPathFor%s' % className
        defValue = classDescr.getCreateMean('Import').path
        fieldType = gen.String(page='data', multiplicity=(1,1),
                               default=defValue,group=classDescr.klass.__name__)
        self.addField(fieldName, fieldType)

class UserClassDescriptor(ClassDescriptor):
    '''Appy-specific class for representing a user.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False
    def getParents(self, allClasses=()):
        res = ['User']
        if self.customized:
            res.append('%s.%s' % (self.klass.__module__, self.klass.__name__))
        return res
    def update(self, klass, attributes):
        '''This method is called by the generator when he finds a custom user
           definition. We must then add the custom user elements in this
           default User descriptor.'''
        self.orderedAttributes += attributes
        self.klass = klass
        self.customized = True
    def isFolder(self, klass=None): return False

class GroupClassDescriptor(ClassDescriptor):
    '''Represents the class that corresponds to the Group for the generated
       application.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False
    def getParents(self, allClasses=()):
        res = ['Group']
        if self.customized:
            res.append('%s.%s' % (self.klass.__module__, self.klass.__name__))
        return res
    def update(self, klass, attributes):
        '''This method is called by the generator when he finds a custom group
           definition. We must then add the custom group elements in this
           default Group descriptor.

           NOTE: currently, it is not possible to define a custom Group
           class.'''
        self.orderedAttributes += attributes
        self.klass = klass
        self.customized = True
    def isFolder(self, klass=None): return False

class TranslationClassDescriptor(ClassDescriptor):
    '''Represents the set of translation ids for a gen-application.'''

    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False

    def getParents(self, allClasses=()): return ('Translation',)
    def isFolder(self, klass=None): return False

    def addLabelField(self, messageId, page):
        '''Adds a Computed field that will display, in the source language, the
           content of the text to translate.'''
        field = gen.Computed(method=self.modelClass.label, plainText=False,
                             page=page, show=self.modelClass.show, layouts='f')
        self.addField('%s_label' % messageId, field)

    def addMessageField(self, messageId, page, i18nFiles):
        '''Adds a message field corresponding to p_messageId to the Translation
           class, on a given p_page. We need i18n files p_i18nFiles for
           fine-tuning the String type to generate for this field (one-line?
           several lines?...)'''
        params = {'page':page, 'layouts':'f', 'show': self.modelClass.show}
        appName = self.generator.applicationName
        # Scan all messages corresponding to p_messageId from all translation
        # files. We will define field length from the longer found message
        # content.
        maxLine = 100 # We suppose a line is 100 characters long.
        width = 0
        height = 0
        for fileName, poFile in i18nFiles.iteritems():
            if not fileName.startswith('%s-' % appName) or \
               not i18nFiles[fileName].messagesDict.has_key(messageId):
                # In this case this is not one of our Appy-managed translation
                # files.
                continue
            msgContent = i18nFiles[fileName].messagesDict[messageId].msg
            # Compute width
            width = max(width, len(msgContent))
            # Compute height (a "\n" counts for one line)
            mHeight = int(len(msgContent)/maxLine) + msgContent.count('<br/>')
            height = max(height, mHeight)
        if height < 1:
            # This is a one-line field.
            params['width'] = width
        else:
            # This is a multi-line field, or a very-long-single-lined field
            params['format'] = gen.String.TEXT
            params['height'] = height
        self.addField(messageId, gen.String(**params))

class PageClassDescriptor(ClassDescriptor):
    '''Represents the class that corresponds to a Page.'''
    def __init__(self, klass, generator):
        ClassDescriptor.__init__(self,klass,klass._appy_attributes[:],generator)
        self.modelClass = self.klass
        self.predefined = True
        self.customized = False
    def getParents(self, allClasses=()):
        res = ['Page']
        if self.customized:
            res.append('%s.%s' % (self.klass.__module__, self.klass.__name__))
        return res
    def update(self, klass, attributes):
        '''This method is called by the generator when he finds a custom page
           definition. We must then add the custom page elements in this
           default Page descriptor.

           NOTE: currently, it is not possible to define a custom Page class.'''
        self.orderedAttributes += attributes
        self.klass = klass
        self.customized = True
    def isFolder(self, klass=None): return True
# ------------------------------------------------------------------------------
