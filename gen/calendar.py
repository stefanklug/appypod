# ------------------------------------------------------------------------------
from appy import Object
from appy.gen import Type
from DateTime import DateTime
from BTrees.IOBTree import IOBTree
from persistent.list import PersistentList

# ------------------------------------------------------------------------------
class Calendar(Type):
    '''This field allows to produce an agenda and view/edit events on it.'''
    jsFiles = {'view': ('widgets/calendar.js',)}

    def __init__(self, eventTypes, validator=None, default=None, show='view',
                 page='main', group=None, layouts=None, move=0,
                 specificReadPermission=False, specificWritePermission=False,
                 width=None, height=300, colspan=1, master=None,
                 masterValue=None, focus=False, mapping=None, label=None,
                 maxEventLength=50):
        Type.__init__(self, validator, (0,1), None, default, False, False,
                      show, page, group, layouts, move, False, False,
                      specificReadPermission, specificWritePermission,
                      width, height, None, colspan, master, masterValue, focus,
                      False, True, mapping, label)
        # eventTypes is a list of strings that identify the types of events
        # that are supported by this calendar.
        self.eventTypes = eventTypes
        # It is not possible to create events that span more days than
        # maxEventLength.
        self.maxEventLength = maxEventLength

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

    def getEventsAt(self, obj, date, asDict=True):
        '''Returns the list of events that exist at some p_date (=day).'''
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

    def hasEventsAt(self, obj, date, otherEvents):
        '''Returns True if, at p_date, an event is found of the same type as
           p_otherEvents.'''
        if not otherEvents: return False
        events = self.getEventsAt(obj, date, asDict=False)
        if not events: return False
        return events[0].eventType == otherEvents[0]['eventType']

    def createEvent(self, obj, date, handleEventSpan=True):
        '''Create a new event in the calendar, at some p_date (day). If
           p_handleEventSpan is True, we will use rq["eventSpan"] and also
           create the same event for successive days.'''
        rq = obj.REQUEST
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
            event = Object(eventType=rq['eventType'])
            events.append(event)
        # Span the event on the successive days if required
        if handleEventSpan and rq['eventSpan']:
            nbOfDays = min(int(rq['eventSpan']), self.maxEventLength)
            for i in range(nbOfDays):
                date = date + 1
                self.createEvent(obj, date, handleEventSpan=False)

    def deleteEvent(self, obj, date, handleEventSpan=True):
        '''Deletes an event. It actually deletes all events at rq['day'].
           If p_handleEventSpan is True, we will use rq["deleteNext"] to
           delete successive events, too.'''
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
# ------------------------------------------------------------------------------
