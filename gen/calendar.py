# ------------------------------------------------------------------------------
import types
from appy import Object
from appy.gen import Type
from DateTime import DateTime
from BTrees.IOBTree import IOBTree
from persistent.list import PersistentList

# ------------------------------------------------------------------------------
class Calendar(Type):
    '''This field allows to produce an agenda (monthly view) and view/edit
       events on it.'''
    jsFiles = {'view': ('widgets/calendar.js',)}

    def __init__(self, eventTypes, eventNameMethod=None, validator=None,
                 default=None, show='view', page='main', group=None,
                 layouts=None, move=0, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=300,
                 colspan=1, master=None, masterValue=None, focus=False,
                 mapping=None, label=None, maxEventLength=50,
                 otherCalendars=None, additionalInfo=None, startDate=None,
                 endDate=None, defaultDate=None, preCompute=None,
                 applicableEvents=None):
        Type.__init__(self, validator, (0,1), default, show, page, group,
                      layouts, move, False, False, specificReadPermission,
                      specificWritePermission, width, height, None, colspan,
                      master, masterValue, focus, False, True, mapping, label,
                      None)
        # eventTypes can be a "static" list or tuple of strings that identify
        # the types of events that are supported by this calendar. It can also
        # be a method that computes such a "dynamic" list or tuple. When
        # specifying a static list, an i18n label will be generated for every
        # event type of the list. When specifying a dynamic list, you must also
        # give, in p_eventNameMethod, a method that will accept a single arg
        # (=one of the event types from your dynamic list) and return the "name"
        # of this event as it must be shown to the user.
        self.eventTypes = eventTypes
        self.eventNameMethod = eventNameMethod
        if (type(eventTypes) == types.FunctionType) and not eventNameMethod:
            raise Exception("When param 'eventTypes' is a method, you must " \
                            "give another method in param 'eventNameMethod'.")
        # It is not possible to create events that span more days than
        # maxEventLength.
        self.maxEventLength = maxEventLength
        # When displaying a given month for this agenda, one may want to
        # pre-compute, once for the whole month, some information that will then
        # be given as arg for other methods specified in subsequent parameters.
        # This mechanism exists for performance reasons, to avoid recomputing
        # this global information several times. If you specify a method in
        # p_preCompute, it will be called every time a given month is shown, and
        # will receive 2 args: the first day of the currently shown month (as a
        # DateTime instance) and the grid of all shown dates (as a list of lists
        # of DateTime instances, one sub-list by row in the month view). This
        # grid may hold a little more than dates of the current month.
        # Subsequently, the return of your method will be given as arg to other
        # methods that you may specify as args of other parameters of this
        # Calendar class (see comments below).
        self.preCompute = preCompute
        # If a method is specified in the following parameters, it must accept
        # a single arg (the result of self.preCompute) and must return a list of
        # calendars whose events must be shown within this agenda.
        # Every element in this list must be a sub-list [object, name, color]
        # (not a tuple):
        # - object must refer to the other object on which the other calendar
        #   field is defined;
        # - name is the name of the field on this object that stores the
        #   calendar;
        # - color must be a string containing the HTML color (including the
        #   leading "#" when relevant) into which events of the calendar must
        #   appear.
        self.otherCalendars = otherCalendars
        # One may want to add, day by day, custom information in the calendar.
        # When a method is given in p_additionalInfo, for every cell of the
        # month view, this method will be called with 2 args: the cell's date
        # and the result of self.preCompute. The method's result (a string that
        # can hold text or a chunk of XHTML) will be inserted in the cell.
        self.additionalInfo = additionalInfo
        # One may limit event encoding and viewing to a limited period of time,
        # via p_startDate and p_endDate. Those parameters, if given, must hold
        # methods accepting no arg and returning a Zope DateTime instance.
        self.startDate = startDate
        # Beware: specify an end date with an hour like
        # DateTime('2012/10/13 23:59:59') to avoid surprises.
        self.endDate = endDate
        # If a default date is specified, it must be a method accepting no arg
        # and returning a DateTime instance. As soon as the calendar is shown,
        # the month where this date is included will be shown. If not default
        # date is specified, it will be 'now' at the moment the calendar is
        # shown.
        self.defaultDate = defaultDate
        # For a specific day, all event types may not be applicable. If this is
        # the case, one may specify here a method that defines, for a given day,
        # a sub-set of all event types. This method must accept 3 args: the day
        # in question (as a DateTime instance), the list of all event types,
        # which is a copy of the (possibly computed) self.eventTypes) and
        # the result of calling self.preCompute. The method must modify
        # the 2nd arg and remove from it potentially not applicable events.
        # This method can also return a message, that will be shown to the user
        # for explaining him why he can, for this day, only create events of a
        # sub-set of the possible event types (or even no event at all).
        self.applicableEvents = applicableEvents

    def getPreComputedInfo(self, obj, monthDayOne, grid):
        '''Returns the result of calling self.preComputed, or None if no such
           method exists.'''
        if self.preCompute:
            return self.preCompute(obj.appy(), monthDayOne, grid)

    def getSiblingMonth(self, month, prevNext):
        '''Gets the next or previous month (depending of p_prevNext) relative
           to p_month.'''
        dayOne = DateTime('%s/01' % month)
        if prevNext == 'previous':
            refDate = dayOne - 1
        elif prevNext == 'next':
            refDate = dayOne + 33
        return refDate.strftime('%Y/%m')

    weekDays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    def getNamesOfDays(self, obj, short=True):
        res = []
        for day in self.weekDays:
            if short:
                suffix = '_short'
            else:
                suffix = ''
            res.append(obj.translate('day_%s%s' % (day, suffix)))
        return res

    def getMonthGrid(self, month):
        '''Creates a list of lists of DateTime objects representing the calendar
           grid to render for a given p_month.'''
        # Month is a string "YYYY/mm".
        currentDay = DateTime('%s/01 12:00' % month)
        currentMonth = currentDay.month()
        res = [[]]
        dayOneNb = currentDay.dow() or 7 # This way, Sunday is 7 and not 0.
        if dayOneNb != 1:
            previousDate = DateTime(currentDay)
            # If the 1st day of the month is not a Monday, start the row with
            # the last days of the previous month.
            for i in range(1, dayOneNb):
                previousDate = previousDate - 1
                res[0].insert(0, previousDate)
        finished = False
        while not finished:
            # Insert currentDay in the grid
            if len(res[-1]) == 7:
                # Create a new row
                res.append([currentDay])
            else:
                res[-1].append(currentDay)
            currentDay = currentDay + 1
            if currentDay.month() != currentMonth:
                finished = True
        # Complete, if needed, the last row with the first days of the next
        # month.
        if len(res[-1]) != 7:
            while len(res[-1]) != 7:
                res[-1].append(currentDay)
                currentDay = currentDay + 1
        return res

    def getOtherCalendars(self, obj, preComputed):
        '''Returns the list of other calendars whose events must also be shown
           on this calendar.'''
        if self.otherCalendars:
            res = self.callMethod(obj, self.otherCalendars, preComputed)
            # Replace field names with field objects
            for i in range(len(res)):
                res[i][1] = res[i][0].getField(res[i][1])
            return res

    def getAdditionalInfoAt(self, obj, date, preComputed):
        '''If the user has specified a method in self.additionalInfo, we call
           it for displaying this additional info in the calendar, at some
           p_date.'''
        if not self.additionalInfo: return
        return self.additionalInfo(obj.appy(), date, preComputed)

    def getEventTypes(self, obj):
        '''Returns the (dynamic or static) event types as defined in
           self.eventTypes.'''
        if type(self.eventTypes) == types.FunctionType:
            return self.eventTypes(obj.appy())
        else:
            return self.eventTypes

    def getApplicableEventsTypesAt(self, obj, date, allEventTypes, preComputed,
                                   forBrowser=False):
        '''Returns the event types that are applicable at a given p_date. More
           precisely, it returns an object with 2 attributes:
           * "events" is the list of applicable event types;
           * "message", not empty if some event types are not applicable,
                        contains a message explaining those event types are
                        not applicable.
        '''
        if not self.applicableEvents:
            eventTypes = allEventTypes
            message = None
        else:
            eventTypes = allEventTypes[:]
            message = self.applicableEvents(obj.appy(), date, eventTypes,
                                            preComputed)
        res = Object(eventTypes=eventTypes, message=message)
        if forBrowser:
            res.eventTypes = ','.join(res.eventTypes)
            if not res.message:
                res.message = ''
            else:
                res.message = obj.formatText(res.message, format='js')
            return res.__dict__
        return res

    def getEventsAt(self, obj, date, asDict=True):
        '''Returns the list of events that exist at some p_date (=day).'''
        obj = obj.o # Ensure p_obj is not a wrapper.
        if not hasattr(obj, self.name): return
        years = getattr(obj, self.name)
        year = date.year()
        if year not in years: return
        months = years[year]
        month = date.month()
        if month not in months: return
        days = months[month]
        day = date.day()
        if day not in days: return
        if asDict:
            res = [e.__dict__ for e in days[day]]
        else:
            res = days[day]
        return res

    def getEventTypeAt(self, obj, date):
        '''Returns the event type of the first event defined at p_day, or None
           if unspecified.'''
        events = self.getEventsAt(obj, date, asDict=False)
        if not events: return
        return events[0].eventType

    def hasEventsAt(self, obj, date, otherEvents):
        '''Returns True if, at p_date, an event is found of the same type as
           p_otherEvents.'''
        if not otherEvents: return False
        events = self.getEventsAt(obj, date, asDict=False)
        if not events: return False
        return events[0].eventType == otherEvents[0]['eventType']

    def getOtherEventsAt(self, obj, date, otherCalendars):
        '''Gets events that are defined in p_otherCalendars at some p_date.'''
        res = []
        for o, field, color in otherCalendars:
            events = field.getEventsAt(o.o, date, asDict=False)
            if events:
                eventType = events[0].eventType
                eventName = field.getEventName(o.o, eventType)
                info = Object(name=eventName, color=color)
                res.append(info.__dict__)
        return res

    def getEventName(self, obj, eventType):
        '''Gets the name of the event corresponding to p_eventType as it must
           appear to the user.'''
        if self.eventNameMethod:
            return self.eventNameMethod(obj.appy(), eventType)
        else:
            return obj.translate('%s_event_%s' % (self.labelId, eventType))

    def getStartDate(self, obj):
        '''Get the start date for this calendar if defined.'''
        if self.startDate: return self.startDate(obj.appy())

    def getEndDate(self, obj):
        '''Get the end date for this calendar if defined.'''
        if self.endDate: return self.endDate(obj.appy())

    def getDefaultDate(self, obj):
        '''Get the default date that must appear as soon as the calendar is
           shown.'''
        if self.defaultDate:
            return self.defaultDate(obj.appy())
        else:
            return DateTime() # Now

    def createEvent(self, obj, date, eventType=None, eventSpan=None,
                    handleEventSpan=True):
        '''Create a new event in the calendar, at some p_date (day).
           If p_eventType is given, it is used; else, rq['eventType'] is used.
           If p_handleEventSpan is True, we will use p_eventSpan (or
           rq["eventSpan"] if p_eventSpan is not given) and also
           create the same event for successive days.'''
        obj = obj.o # Ensure p_obj is not a wrapper.
        rq = obj.REQUEST
        # Get values from parameters
        if not eventType: eventType = rq['eventType']
        if handleEventSpan and not eventSpan:
            eventSpan = rq.get('eventSpan', None)
        # Split the p_date into separate parts
        year, month, day = date.year(), date.month(), date.day()
        # Check that the "preferences" dict exists or not.
        if not hasattr(obj.aq_base, self.name):
            # 1st level: create a IOBTree whose keys are years.
            setattr(obj, self.name, IOBTree())
        yearsDict = getattr(obj, self.name)
        # Get the sub-dict storing months for a given year
        if year in yearsDict:
            monthsDict = yearsDict[year]
        else:
            yearsDict[year] = monthsDict = IOBTree()
        # Get the sub-dict storing days of a given month
        if month in monthsDict:
            daysDict = monthsDict[month]
        else:
            monthsDict[month] = daysDict = IOBTree()
        # Get the list of events for a given day
        if day in daysDict:
            events = daysDict[day]
        else:
            daysDict[day] = events = PersistentList()
        # Create and store the event, excepted if an event already exists.
        if not events:
            event = Object(eventType=eventType)
            events.append(event)
        # Span the event on the successive days if required
        if handleEventSpan and eventSpan:
            nbOfDays = min(int(eventSpan), self.maxEventLength)
            for i in range(nbOfDays):
                date = date + 1
                self.createEvent(obj, date, handleEventSpan=False)

    def deleteEvent(self, obj, date, handleEventSpan=True):
        '''Deletes an event. It actually deletes all events at rq['day'].
           If p_handleEventSpan is True, we will use rq["deleteNext"] to
           delete successive events, too.'''
        obj = obj.o # Ensure p_obj is not a wrapper.
        rq = obj.REQUEST
        if not self.getEventsAt(obj, date): return
        daysDict = getattr(obj, self.name)[date.year()][date.month()]
        # Remember events, in case we must delete similar ones for next days.
        events = self.getEventsAt(obj, date)
        del daysDict[date.day()]
        if handleEventSpan and rq.has_key('deleteNext') and \
           (rq['deleteNext'] == 'True'):
            while True:
                date = date + 1
                if self.hasEventsAt(obj, date, events):
                    self.deleteEvent(obj, date, handleEventSpan=False)
                else:
                    break

    def process(self, obj):
        '''Processes an action coming from the calendar widget, ie, the creation
           or deletion of a calendar event.'''
        rq = obj.REQUEST
        action = rq['actionType']
        # Get the date for this action
        if action == 'createEvent':
            return self.createEvent(obj, DateTime(rq['day']))
        elif action == 'deleteEvent':
            return self.deleteEvent(obj, DateTime(rq['day']))

    def getCellStyle(self, obj, date, today):
        '''What CSS classes must apply to the table cell representing p_date
           in the calendar?'''
        res = []
        # We must distinguish between past and future dates.
        if date < today:
            res.append('even')
        else:
            res.append('odd')
        # Week-end days must have a specific style.
        if date.aDay() in ('Sat', 'Sun'):
            res.append('cellDashed')
        return ' '.join(res)
# ------------------------------------------------------------------------------
