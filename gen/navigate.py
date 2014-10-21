# ------------------------------------------------------------------------------
from appy.px import Px

# ------------------------------------------------------------------------------
class Siblings:
    '''Abstract class containing information for navigating from one object to
       its siblings.'''
    siblingTypes = ('previous', 'next', 'first', 'last')

    # Buttons for going to siblings of the current object.
    pxNavigate = Px('''
      <!-- Go to the source URL (search or referred object) -->
      <a if="not inPopup" href=":self.sourceUrl"><img
         var="goBack='%s - %s' % (self.getBackText(), _('goto_source'))"
         src=":url('gotoSource')" title=":goBack"/></a>

      <!-- Go to the first or previous page -->
      <a if="self.firstUrl" href=":self.firstUrl"><img title=":_('goto_first')"
         src=":url('arrowsLeft')"/></a><a
         if="self.previousUrl" href=":self.previousUrl"><img
         title=":_('goto_previous')" src=":url('arrowLeft')"/></a>

      <!-- Explain which element is currently shown -->
      <span class="discreet"> 
       <x>:self.number</x> <b>//</b> 
       <x>:self.total</x> </span>

      <!-- Go to the next or last page -->
      <a if="self.nextUrl" href=":self.nextUrl"><img title=":_('goto_next')"
         src=":url('arrowRight')"/></a><a
         if="self.lastUrl" href=":self.lastUrl"><img title=":_('goto_last')"
         src=":url('arrowsRight')"/></a>

      <!-- Go to the element number... -->
      <x if="self.showGotoNumber()"
         var2="field=self.field; sourceUrl=self.sourceObject.absolute_url();
               totalNumber=self.total"><br/><x>:obj.pxGotoNumber</x></x>''')

    @staticmethod
    def get(nav, tool, inPopup):
        '''This method analyses the navigation info p_nav and returns the
           corresponding concrete Siblings instance.'''
        elems = nav.split('.')
        params = elems[1:]
        if elems[0] == 'ref': return RefSiblings(tool, inPopup, *params)
        elif elems[0] == 'search': return SearchSiblings(tool, inPopup, *params)

    def computeStartNumber(self):
        '''Returns the start number of the batch where the current element
           lies.'''
        # First index starts at O, so we calibrate self.number
        number = self.number - 1
        batchSize = self.getBatchSize()
        res = 0
        while (res < self.total):
            if (number < res + batchSize): return res
            res += batchSize
        return res

    def __init__(self, tool, inPopup, number, total):
        self.tool = tool
        self.request = tool.REQUEST
        # Are we in a popup window or not?
        self.inPopup = inPopup
        # The number of the current element
        self.number = int(number)
        # The total number of siblings
        self.total = int(total)
        # Do I need to navigate to first, previous, next and/or last sibling ?
        self.previousNeeded = False # Previous ?
        self.previousIndex = self.number - 2
        if (self.previousIndex > -1) and (self.total > self.previousIndex):
            self.previousNeeded = True
        self.nextNeeded = False     # Next ?
        self.nextIndex = self.number
        if self.nextIndex < self.total: self.nextNeeded = True
        self.firstNeeded = False    # First ?
        self.firstIndex = 0
        if self.previousIndex > 0: self.firstNeeded = True
        self.lastNeeded = False     # Last ?
        self.lastIndex = self.total - 1
        if (self.nextIndex < self.lastIndex): self.lastNeeded = True
        # Compute the UIDs of the siblings of the current object
        self.siblings = self.getSiblings()
        # Compute back URL and URLs to siblings
        self.sourceUrl = self.getSourceUrl()
        siblingNav = self.getNavKey()
        siblingPage = self.request.get('page', 'main')
        for urlType in self.siblingTypes:
            exec 'needIt = self.%sNeeded' % urlType
            urlKey = '%sUrl' % urlType
            setattr(self, urlKey, None)
            if not needIt: continue
            exec 'index = self.%sIndex' % urlType
            uid = None
            try:
                # self.siblings can be a list (ref) or a dict (search)
                uid = self.siblings[index]
            except KeyError: continue
            except IndexError: continue
            if not uid: continue
            sibling = self.tool.getObject(uid)
            if not sibling: continue
            setattr(self, urlKey, sibling.getUrl(nav=siblingNav % (index + 1),
                                             page=siblingPage, inPopup=inPopup))

# ------------------------------------------------------------------------------
class RefSiblings(Siblings):
    '''Class containing information for navigating from one object to another
       within tied objects from a Ref field.'''
    prefix = 'ref'

    def __init__(self, tool, inPopup, sourceUid, fieldName, number, total):
        # The source object of the Ref field
        self.sourceObject = tool.getObject(sourceUid)
        # The Ref field in itself
        self.field = self.sourceObject.getAppyType(fieldName)
        # Call the base constructor
        Siblings.__init__(self, tool, inPopup, number, total)

    def getNavKey(self):
        '''Returns the general navigation key for navigating to another
           sibling.'''
        return self.field.getNavInfo(self.sourceObject, None, self.total)

    def getBackText(self):
        '''Computes the text to display when the user want to navigate back to
           the list of tied objects.'''
        _ = self.tool.translate
        return '%s - %s' % (self.sourceObject.Title(), _(self.field.labelId))

    def getBatchSize(self):
        '''Returns the maximum number of shown objects at a time for this
           ref.'''
        return self.field.maxPerPage

    def getSiblings(self):
        '''Returns the siblings of the current object.'''
        return getattr(self.sourceObject, self.field.name, ())

    def getSourceUrl(self):
        '''Computes the URL allowing to go back to self.sourceObject's page
           where self.field lies and shows the list of tied objects, at the
           batch where the current object lies.'''
        # Allow to go back to the batch where the current object lies
        field = self.field
        startNumberKey = '%s_%s_objs_startNumber' % \
                         (self.sourceObject.id,field.name)
        startNumber = str(self.computeStartNumber())
        return self.sourceObject.getUrl(**{startNumberKey:startNumber,
                                           'page':field.pageName, 'nav':''})

    def showGotoNumber(self):
        '''Show "goto number" if the Ref field is numbered.'''
        return self.field.isNumbered(self.sourceObject)

# ------------------------------------------------------------------------------
class SearchSiblings(Siblings):
    '''Class containing information for navigating from one object to another
       within results of a search.'''
    prefix = 'search'

    def __init__(self, tool, inPopup, className, searchName, number, total):
        # The class determining the type of searched objects
        self.className = className
        # Get the search object
        self.searchName = searchName
        self.uiSearch = tool.getSearch(className, searchName, ui=True)
        self.search = self.uiSearch.search
        Siblings.__init__(self, tool, inPopup, number, total)

    def getNavKey(self):
        '''Returns the general navigation key for navigating to another
           sibling.'''
        return 'search.%s.%s.%%d.%d' % (self.className, self.searchName,
                                        self.total)

    def getBackText(self):
        '''Computes the text to display when the user want to navigate back to
           the list of searched objects.'''
        return self.uiSearch.translated

    def getBatchSize(self):
        '''Returns the maximum number of shown objects at a time for this
           search.'''
        return self.search.maxPerPage

    def getSiblings(self):
        '''Returns the siblings of the current object. For performance reasons,
           only a part of the is stored, in the session object.'''
        session = self.request.SESSION
        searchKey = self.search.getSessionKey(self.className)
        if session.has_key(searchKey): res = session[searchKey]
        else: res = {}
        if (self.previousNeeded and not res.has_key(self.previousIndex)) or \
           (self.nextNeeded and not res.has_key(self.nextIndex)):
            # The needed sibling UID is not in session. We will need to
            # retrigger the query by querying all objects surrounding this one.
            newStartNumber = (self.number-1) - (self.search.maxPerPage / 2)
            if newStartNumber < 0: newStartNumber = 0
            self.tool.executeQuery(self.className, search=self.search,
                                   startNumber=newStartNumber, remember=True)
            res = session[searchKey]
        # For the moment, for first and last, we get them only if we have them
        # in session.
        if not res.has_key(0): self.firstNeeded = False
        if not res.has_key(self.lastIndex): self.lastNeeded = False
        return res

    def getSourceUrl(self):
        '''Computes the (non-Ajax) URL allowing to go back to the search
           results, at the batch where the current object lies.'''
        params = 'className=%s&search=%s&startNumber=%d' % \
                 (self.className, self.searchName, self.computeStartNumber())
        ref = self.request.get('ref', None)
        if ref: params += '&ref=%s' % ref
        return '%s/query?%s' % (self.tool.absolute_url(), params)

    def showGotoNumber(self): return
# ------------------------------------------------------------------------------
