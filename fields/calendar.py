# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
import types
from appy import Object
from appy.gen import Field
from appy.px import Px
from DateTime import DateTime
from BTrees.IOBTree import IOBTree
from persistent.list import PersistentList

# ------------------------------------------------------------------------------
class Calendar(Field):
    '''This field allows to produce an agenda (monthly view) and view/edit
       events on it.'''
    jsFiles = {'view': ('calendar.js',)}
    DateTime = DateTime
    timelineBgColors = {'Fri': '#a6a6a6', 'Sat': '#c0c0c0', 'Sun': '#c0c0c0'}

    # For timeline rendering, the row displaying month names
    pxTimeLineMonths = Px('''
     <tr><th></th> <!-- Names of months -->
      <th for="mInfo in monthsInfos"
          colspan=":mInfo.colspan">::mInfo.month</th><th></th></tr>''')

    # For timeline rendering, the row displaying day letters
    pxTimelineDayLetters = Px('''
     <tr><td></td> <!-- Days (letters) -->
      <td for="date in grid"><b>:namesOfDays[date.aDay()].name[0]</b></td>
      <td></td></tr>''')

    # For timeline rendering, the row displaying day numbers
    pxTimelineDayNumbers = Px('''
      <tr><td></td> <!-- Days (numbers) -->
       <td for="date in grid"><b>:str(date.day()).zfill(2)</b></td>
       <td></td></tr>''')

    # Timeline view for a calendar
    pxViewTimeline = Px('''
     <table cellpadding="0" cellspacing="0" class="list timeline"
            var="monthsInfos=field.getTimelineMonths(grid, zobj)">
      <!-- Column specifiers -->
      <colgroup>
       <!-- Names of calendars -->
       <col></col>
       <col for="date in grid"
            style=":field.getColumnStyle(zobj, date, render, today)"></col>
       <col></col>
      </colgroup>
      <!-- Header rows (months and days) -->
      <x>:field.pxTimeLineMonths</x>
      <x>:field.pxTimelineDayLetters</x><x>:field.pxTimelineDayNumbers</x>
      <!-- The calendar in itself -->
      <tr if="allEventTypes">
       <td class="tlName"></td>
       <td for="date in grid"></td>
       <td></td>
      </tr>
      <!-- Other calendars -->
      <tr for="other in otherCalendars"
          var2="tlName=field.getTimelineName(*other)">
       <td class="tlLeft">::tlName</td>
       <!-- A cell in this other calendar -->
       <x for="date in grid"
          var2="inRange=field.dateInRange(date, startDate, endDate)">
        <td if="not inRange"></td>
        <td if="inRange"
            var2="events=field.getOtherEventsAt(zobj, date, other, eventNames,\
                                                render, colors, single=True)"
            style=":field.getCellStyle(zobj, date, render, \
                                   events)">::field.getTimelineCell(events)</td>
       </x>
       <td class="tlRight">::tlName</td>
      </tr>
      <!-- Footer (repetition of months and days) -->
      <x>:field.pxTimelineDayNumbers</x><x>:field.pxTimelineDayLetters</x>
      <x>:field.pxTimeLineMonths</x>
     </table>''')

    # Month view for a calendar
    pxViewMonth = Px('''
      <table cellpadding="0" cellspacing="0" width="100%" class="list"
             style="font-size: 95%"
             var="rowHeight=int(field.height/float(len(grid)))">
       <!-- 1st row: names of days -->
       <tr height="22px">
        <th for="dayId in field.weekDays"
            width="14%">:namesOfDays[dayId].short</th>
       </tr>
       <!-- The calendar in itself -->
       <tr for="row in grid" valign="top" height=":rowHeight">
        <x for="date in row"
           var2="inRange=field.dateInRange(date, startDate, endDate);
                 cssClasses=field.getCellClass(zobj, date, render, today)">
         <!-- Dump an empty cell if we are out of the supported date range -->
         <td if="not inRange" class=":cssClasses"></td>
         <!-- Dump a normal cell if we are in range -->
         <td if="inRange"
             var2="events=field.getEventsAt(zobj, date);
                   spansDays=field.hasEventsAt(zobj, date+1, events);
                   mayCreate=mayEdit and not events;
                   mayDelete=mayEdit and events and field.mayDelete(obj,events);
                   day=date.day();
                   dayString=date.strftime('%Y/%m/%d');
                   js=mayEdit and 'toggleVisibility(this, %s)' % q('img') \
                      or ''"
             style=":date.isCurrentDay() and 'font-weight:bold' or \
                                             'font-weight:normal'"
             class=":cssClasses" onmouseover=":js" onmouseout=":js">
          <span>:day</span>
          <span if="day == 1">:_('month_%s_short' % date.aMonth())</span>
          <!-- Icon for adding an event -->
          <x if="mayCreate">
           <img class="clickable" style="visibility:hidden"
                var="info=field.getApplicableEventsTypesAt(zobj, date, \
                            allEventTypes, preComputed, True)"
                if="info and info.eventTypes" src=":url('plus')"
                onclick=":'openEventPopup(%s, %s, %s, null, %s, %s)' % \
                 (q('new'), q(field.name), q(dayString), q(info.eventTypes),\
                  q(info.message))"/>
          </x>
          <!-- Icon for deleting an event -->
          <img if="mayDelete" class="clickable" style="visibility:hidden"
               src=":url('delete')"
               onclick=":'openEventPopup(%s, %s, %s, %s, null, null)' % \
                 (q('del'), q(field.name), q(dayString), q(spansDays))"/>
          <!-- A single event is allowed for the moment -->
          <div if="events" var2="eventType=events[0].eventType">
           <span style="color: grey">:eventNames[eventType]</span>
          </div>
          <!-- Events from other calendars -->
          <x if="otherCalendars"
             var2="otherEvents=field.getOtherEventsAt(zobj, date, \
                                otherCalendars, eventNames, render, colors)">
           <div style=":'color: %s; font-style: italic' % event.color"
                for="event in otherEvents">:event.name</div>
          </x>
          <!-- Additional info -->
          <x var="info=field.getAdditionalInfoAt(zobj, date, preComputed)"
             if="info">::info</x>
         </td>
        </x>
       </tr>
      </table>

      <!-- Popup for creating a calendar event -->
      <div if="allEventTypes"
           var="prefix='%s_newEvent' % field.name;
                popupId=prefix + 'Popup'"
           id=":popupId" class="popup" align="center">
       <form id=":prefix + 'Form'" method="post">
        <input type="hidden" name="fieldName" value=":field.name"/>
        <input type="hidden" name="month" value=":month"/>
        <input type="hidden" name="name" value=":field.name"/>
        <input type="hidden" name="action" value="process"/>
        <input type="hidden" name="actionType" value="createEvent"/>
        <input type="hidden" name="day"/>

        <!-- Choose an event type -->
        <div align="center" style="margin-bottom: 3px">:_('which_event')</div>
        <select name="eventType">
         <option value="">:_('choose_a_value')</option>
         <option for="eventType in allEventTypes"
                 value=":eventType">:eventNames[eventType]</option>
        </select><br/><br/>
        <!--Span the event on several days -->
        <div align="center" class="discreet" style="margin-bottom: 3px">
         <span>:_('event_span')</span>
         <input type="text" size="3" name="eventSpan"/>
        </div>
        <input type="button"
               value=":_('object_save')"
               onclick=":'triggerCalendarEvent(%s, %s, %s, %s, \
                          %s_maxEventLength)' % (q('new'), q(ajaxHookId), \
                          q(field.name), q(objUrl), field.name)"/>
        <input type="button"
               value=":_('object_cancel')"
               onclick=":'closePopup(%s)' % q(popupId)"/>
       </form>
      </div>

      <!-- Popup for deleting a calendar event -->
      <div var="prefix='%s_delEvent' % field.name;
                popupId=prefix + 'Popup'"
           id=":popupId" class="popup" align="center">
       <form id=":prefix + 'Form'" method="post">
        <input type="hidden" name="fieldName" value=":field.name"/>
        <input type="hidden" name="month" value=":month"/>
        <input type="hidden" name="name" value=":field.name"/>
        <input type="hidden" name="action" value="process"/>
        <input type="hidden" name="actionType" value="deleteEvent"/>
        <input type="hidden" name="day"/>
        <div align="center"
             style="margin-bottom: 5px">:_('action_confirm')</div>

        <!-- Delete successive events ? -->
        <div class="discreet" style="margin-bottom: 10px"
             id=":prefix + 'DelNextEvent'">
          <input type="checkbox" name="deleteNext_cb"
                 id=":prefix + '_cb'"
                 onClick=":'toggleCheckbox(%s, %s)' % \
                           (q('%s_cb' % prefix), q('%s_hd' % prefix))"/>
          <input type="hidden" id=":prefix + '_hd'" name="deleteNext"/>
          <span>:_('del_next_events')</span>
        </div>
        <input type="button" value=":_('yes')"
               onClick=":'triggerCalendarEvent(%s, %s, %s, %s)' % \
                 (q('del'), q(ajaxHookId), q(field.name), q(objUrl))"/>
        <input type="button" value=":_('no')"
               onclick=":'closePopup(%s)' % q(popupId)"/>
       </form>
      </div>''')

    pxView = pxCell = Px('''
     <div var="defaultDate=field.getDefaultDate(zobj);
               defaultDateMonth=defaultDate.strftime('%Y/%m');
               ajaxHookId=zobj.id + field.name;
               month=req.get('month', defaultDate.strftime('%Y/%m'));
               monthDayOne=field.DateTime('%s/01' % month);
               render=req.get('render', field.render);
               today=field.DateTime('00:00');
               grid=field.getGrid(month, render);
               allEventTypes=field.getEventTypes(zobj);
               preComputed=field.getPreComputedInfo(zobj, monthDayOne, grid);
               previousMonth=field.getSiblingMonth(month, 'previous');
               nextMonth=field.getSiblingMonth(month, 'next');
               mayEdit=zobj.mayEdit(field.writePermission);
               objUrl=zobj.absolute_url();
               startDate=field.getStartDate(zobj);
               endDate=field.getEndDate(zobj);
               otherCalendars=field.getOtherCalendars(zobj, preComputed);
               eventNames=field.getEventNames(zobj, allEventTypes, \
                                              otherCalendars);
               colors=field.getColors(zobj);
               namesOfDays=field.getNamesOfDays(_)"
          id=":ajaxHookId">
      <script>:'var %s_maxEventLength = %d;' % \
                (field.name, field.maxEventLength)</script>

      <!-- Month chooser -->
      <div style="margin-bottom: 5px"
           var="fmt='%Y/%m/%d';
                goBack=not startDate or (startDate.strftime(fmt) &lt; \
                                         grid[0][0].strftime(fmt));
                goForward=not endDate or (endDate.strftime(fmt) &gt; \
                                          grid[-1][-1].strftime(fmt))">
       <!-- Go to the previous month -->
       <img class="clickable" if="goBack" src=":url('arrowLeft')"
            onclick=":'askCalendar(%s,%s,%s,%s,%s)' % (q(ajaxHookId), \
                       q(objUrl), q(render), q(field.name), q(previousMonth))"/>
       <!-- Go back to the default date -->
       <input type="button" if="goBack or goForward"
              var="fmt='%Y/%m';
                   label=(defaultDate.strftime(fmt)==today.strftime(fmt)) and \
                         'today' or 'goto_source'"
              value=":_(label)"
              onclick=":'askCalendar(%s,%s,%s,%s,%s)' % (q(ajaxHookId), \
                      q(objUrl), q(render), q(field.name), q(defaultDateMonth))"
              disabled=":defaultDate.strftime(fmt)==monthDayOne.strftime(fmt)"/>
       <!-- Go to the next month -->
       <img class="clickable" if="goForward" src=":url('arrowRight')"
            onclick=":'askCalendar(%s,%s,%s,%s,%s)' % (q(ajaxHookId), \
                       q(objUrl), q(render), q(field.name), q(nextMonth))"/>
       <span>:_('month_%s' % monthDayOne.aMonth())</span>
       <span>:month.split('/')[0]</span>
      </div>
      <x>:getattr(field, 'pxView%s' % render.capitalize())</x>
     </div>''')

    pxEdit = pxSearch = ''

    def __init__(self, eventTypes, eventNameMethod=None, validator=None,
                 default=None, show=('view', 'xml'), page='main', group=None,
                 layouts=None, move=0, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=300,
                 colspan=1, master=None, masterValue=None, focus=False,
                 mapping=None, label=None, maxEventLength=50, render='month',
                 otherCalendars=None, timelineName=None, additionalInfo=None,
                 startDate=None, endDate=None, defaultDate=None, colors=None,
                 showUncolored=False, preCompute=None, applicableEvents=None,
                 view=None, xml=None, delete=True):
        Field.__init__(self, validator, (0,1), default, show, page, group,
                       layouts, move, False, True, False, specificReadPermission,
                       specificWritePermission, width, height, None, colspan,
                       master, masterValue, focus, False, mapping, label, None,
                       None, None, None, True, view, xml)
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
        if callable(eventTypes) and not eventNameMethod:
            raise Exception("When param 'eventTypes' is a method, you must " \
                            "give another method in param 'eventNameMethod'.")
        # It is not possible to create events that span more days than
        # maxEventLength.
        self.maxEventLength = maxEventLength
        # Various render modes exist. Default is the classical "month" view.
        # It can also be "timeline": in this case, on the x axis, we have one
        # column per day, and on the y axis, we have one row per calendar (this
        # one and others as specified in "otherCalendars", see below).
        self.render = render
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
        # When displaying a timeline calendar, a name is shown for every other
        # calendar. If "timelineName" is None (the default), this name will be
        # the title of the object where the other calendar is defined. Else, it
        # will be the result of the method specified in "timelineName". This
        # method must return a string and accepts 3 args: object, name and color
        # (corresponding to a sub-list produced by "otherCalendars" hereabove).
        self.timelineName = timelineName
        # One may want to add, day by day, custom information in the calendar.
        # When a method is given in p_additionalInfo, for every cell of the
        # month view, this method will be called with 2 args: the cell's date
        # and the result of self.preCompute. The method's result (a string that
        # can hold text or a chunk of XHTML) will be inserted in the cell.
        self.additionalInfo = additionalInfo
        # One may limit event encoding and viewing to some period of time,
        # via p_startDate and p_endDate. Those parameters, if given, must hold
        # methods accepting no arg and returning a Zope DateTime instance. The
        # startDate and endDate will be converted to UTC at 00.00.
        self.startDate = startDate
        self.endDate = endDate
        # If a default date is specified, it must be a method accepting no arg
        # and returning a DateTime instance. As soon as the calendar is shown,
        # the month where this date is included will be shown. If not default
        # date is specified, it will be 'now' at the moment the calendar is
        # shown.
        self.defaultDate = defaultDate
        # "colors" must be or return a dict ~{s_eventType: s_color}~ giving a
        # color to every event type defined in this calendar or in any calendar
        # from "otherCalendars". In a timeline, cells are too small to display
        # translated names for event types, so colors are used instead.
        self.colors = colors or {}
        # For event types that are not present in self.colors hereabove, must we
        # still show them? If yes, they will be represented by a dot with a
        # tooltip containing the event name.
        self.showUncolored = showUncolored
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
        # May the user delete events in this calendar? If "delete" is a method,
        # it must accept an event type as single arg.
        self.delete = delete

    def getPreComputedInfo(self, obj, monthDayOne, grid):
        '''Returns the result of calling self.preComputed, or None if no such
           method exists.'''
        if self.preCompute:
            return self.preCompute(obj.appy(), monthDayOne, grid)

    def getSiblingMonth(self, month, prevNext):
        '''Gets the next or previous month (depending of p_prevNext) relative
           to p_month.'''
        dayOne = DateTime('%s/01 UTC' % month)
        if prevNext == 'previous':
            refDate = dayOne - 1
        elif prevNext == 'next':
            refDate = dayOne + 33
        return refDate.strftime('%Y/%m')

    weekDays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    def getNamesOfDays(self, _):
        '''Returns the translated names of all week days, short and long
           versions.'''
        res = {}
        for day in self.weekDays:
            name = _('day_%s' % day)
            short = _('day_%s_short' % day)
            res[day] = Object(name=name, short=short)
        return res

    def getGrid(self, month, render):
        '''Creates a list of DateTime objects representing the calendar grid to
           render for a given p_month. If p_render is "month", it is a list of
           lists (one sub-list for every week; indeed, every week is rendered as
           a row). If p_render is "timeline", the result is a linear list of
           DateTime instances.'''
        # Month is a string "YYYY/mm"
        currentDay = DateTime('%s/01 UTC' % month)
        currentMonth = currentDay.month()
        isLinear = render == 'timeline'
        if isLinear: res = []
        else: res = [[]]
        dayOneNb = currentDay.dow() or 7 # This way, Sunday is 7 and not 0
        if dayOneNb != 1:
            previousDate = DateTime(currentDay)
            # If the 1st day of the month is not a Monday, integrate the last
            # days of the previous month.
            for i in range(1, dayOneNb):
                previousDate = previousDate - 1
                if isLinear:
                    target = res
                else:
                    target = res[0]
                target.insert(0, previousDate)
        finished = False
        while not finished:
            # Insert currentDay in the result
            if isLinear:
                res.append(currentDay)
            else:
                if len(res[-1]) == 7:
                    # Create a new row
                    res.append([currentDay])
                else:
                    res[-1].append(currentDay)
            currentDay += 1
            if currentDay.month() != currentMonth:
                finished = True
        # Complete, if needed, the last row with the first days of the next
        # month. Indeed, we must have a complete week, ending with a Sunday.
        if isLinear: target = res
        else: target = res[-1]
        while target[-1].dow() != 0:
            target.append(currentDay)
            currentDay += 1
        return res

    def getOtherCalendars(self, obj, preComputed):
        '''Returns the list of other calendars whose events must also be shown
           on this calendar.'''
        if self.otherCalendars:
            res = self.otherCalendars(obj.appy(), preComputed)
            # Replace field names with field objects
            for i in range(len(res)):
                res[i][1] = res[i][0].getField(res[i][1])
            return res

    def getTimelineName(self, obj, name, color):
        '''Returns the name of this calendar as must be shown in a timeline.'''
        if not self.timelineName:
            return '<a href="%s">%s</a>' % (obj.url, obj.title)
        return self.timelineName(self, obj, name, color)

    def getTimelineCell(self, events):
        '''Gets the content of a cell in a timeline calendar.'''
        # Currently a single event is allowed
        if not events or not events[0].symbol: return ''
        return events[0].symbol

    def getAdditionalInfoAt(self, obj, date, preComputed):
        '''If the user has specified a method in self.additionalInfo, we call
           it for displaying this additional info in the calendar, at some
           p_date.'''
        if not self.additionalInfo: return
        return self.additionalInfo(obj.appy(), date, preComputed)

    def getEventTypes(self, obj):
        '''Returns the (dynamic or static) event types as defined in
           self.eventTypes.'''
        if callable(self.eventTypes): return self.eventTypes(obj.appy())
        return self.eventTypes

    def getColors(self, obj):
        '''Gets the colors for event types managed by this calendar and
           otherCalendars (from self.colors).'''
        if callable(self.colors): return self.colors(obj)
        return self.colors

    def dateInRange(self, date, startDate, endDate):
        '''Is p_date within the range (possibly) defined for this calendar by
           p_startDate and p_endDate ?'''
        tooEarly = startDate and (date < startDate)
        tooLate = endDate and not tooEarly and (date > endDate)
        return not tooEarly and not tooLate

    def getApplicableEventsTypesAt(self, obj, date, allEventTypes, preComputed,
                                   forBrowser=False):
        '''Returns the event types that are applicable at a given p_date. More
           precisely, it returns an object with 2 attributes:
           * "events" is the list of applicable event types;
           * "message", not empty if some event types are not applicable,
                        contains a message explaining those event types are
                        not applicable.
        '''
        if not allEventTypes: return # There may be no event type at all
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
            if not res.message: res.message = ''
        return res

    def getEventsAt(self, obj, date):
        '''Returns the list of events that exist at some p_date (=day).'''
        obj = obj.o # Ensure p_obj is not a wrapper.
        if not hasattr(obj.aq_base, self.name): return
        years = getattr(obj, self.name)
        year = date.year()
        if year not in years: return
        months = years[year]
        month = date.month()
        if month not in months: return
        days = months[month]
        day = date.day()
        if day not in days: return
        return days[day]

    def getEventTypeAt(self, obj, date):
        '''Returns the event type of the first event defined at p_day, or None
           if unspecified.'''
        events = self.getEventsAt(obj, date)
        if not events: return
        return events[0].eventType

    def getEventsByType(self, obj, eventType, minDate=None, maxDate=None,
                        sorted=True, groupSpanned=False):
        '''Returns all the events of a given p_eventType. If p_eventType is
           None, it returns events of all types. The return value is a list of
           2-tuples whose 1st elem is a DateTime instance and whose 2nd elem is
           the event.
           If p_sorted is True, the list is sorted in chronological order. Else,
           the order is random, but the result is computed faster.
           If p_minDate and/or p_maxDate is/are specified, it restricts the
           search interval accordingly.
           If p_groupSpanned is True, events spanned on several days are
           grouped into a single event. In this case, tuples in the result
           are 3-tuples: (DateTime_startDate, DateTime_endDate, event).
        '''
        # Prevent wrong combinations of parameters
        if groupSpanned and not sorted:
            raise Exception('Events must be sorted if you want to get ' \
                            'spanned events to be grouped.')
        obj = obj.o # Ensure p_obj is not a wrapper.
        res = []
        if not hasattr(obj, self.name): return res
        # Compute "min" and "max" tuples
        if minDate:
            minYear = minDate.year()
            minMonth = (minYear, minDate.month())
            minDay = (minYear, minDate.month(), minDate.day())
        if maxDate:
            maxYear = maxDate.year()
            maxMonth = (maxYear, maxDate.month())
            maxDay = (maxYear, maxDate.month(), maxDate.day())
        # Browse years
        years = getattr(obj, self.name)
        for year in years.keys():
            # Don't take this year into account if outside interval
            if minDate and (year < minYear): continue
            if maxDate and (year > maxYear): continue
            months = years[year]
            # Browse this year's months
            for month in months.keys():
                # Don't take this month into account if outside interval
                thisMonth = (year, month)
                if minDate and (thisMonth < minMonth): continue
                if maxDate and (thisMonth > maxMonth): continue
                days = months[month]
                # Browse this month's days
                for day in days.keys():
                    # Don't take this day into account if outside interval
                    thisDay = (year, month, day)
                    if minDate and (thisDay < minDay): continue
                    if maxDate and (thisDay > maxDay): continue
                    events = days[day]
                    # Browse this day's events
                    for event in events:
                        # Filter unwanted events
                        if eventType and (event.eventType != eventType):
                            continue
                        # We have found a event.
                        date = DateTime('%d/%d/%d UTC' % (year, month, day))
                        if groupSpanned:
                            singleRes = [date, None, event]
                        else:
                            singleRes = (date, event)
                        res.append(singleRes)
        # Sort the result if required
        if sorted: res.sort(key=lambda x: x[0])
        # Group events spanned on several days if required
        if groupSpanned:
            # Browse events in reverse order and merge them when appropriate
            i = len(res) - 1
            while i > 0:
                currentDate = res[i][0]
                lastDate = res[i][1]
                previousDate = res[i-1][0]
                currentType = res[i][2].eventType
                previousType = res[i-1][2].eventType
                if (previousDate == (currentDate-1)) and \
                   (previousType == currentType):
                    # A merge is needed
                    del res[i]
                    res[i-1][1] = lastDate or currentDate
                i -= 1
        return res

    def hasEventsAt(self, obj, date, otherEvents):
        '''Returns True if, at p_date, an event is found of the same type as
           p_otherEvents.'''
        if not otherEvents: return False
        events = self.getEventsAt(obj, date)
        if not events: return False
        return events[0].eventType == otherEvents[0].eventType

    def getOtherEventsAt(self, obj, date, otherCalendars, eventNames, render,
                         colors, single=False):
        '''Gets events that are defined in p_otherCalendars at some p_date.
           If p_single is True, p_otherCalendars does not contain the list of
           all other calendars, but information about a single calendar.'''
        res = []
        if single: otherCalendars = [otherCalendars]
        isTimeline = render == 'timeline'
        for o, field, color in otherCalendars:
            events = field.getEventsAt(o.o, date)
            if events:
                eventType = events[0].eventType
                info = Object(color=color)
                if isTimeline:
                    # Get the background color for this cell if it has been
                    # defined, or (a) nothing if showUncolored is False, (b) a
                    # tooltipped dot else.
                    if eventType in colors:
                        info.bgColor = colors[eventType]
                        info.symbol = None
                    else:
                        info.bgColor = None
                        if self.showUncolored:
                            info.symbol = '<acronym title="%s">▪</acronym>' % \
                                          eventNames[eventType]
                        else:
                            info.symbol = None
                else:
                    # Get the event name
                    info.name = eventNames[eventType]
                res.append(info)
        return res

    def getEventName(self, obj, eventType):
        '''Gets the name of the event corresponding to p_eventType as it must
           appear to the user.'''
        if self.eventNameMethod:
            return self.eventNameMethod(obj.appy(), eventType)
        else:
            return obj.translate('%s_event_%s' % (self.labelId, eventType))

    def getEventNames(self, obj, eventTypes, otherCalendars):
        '''Computes a dict of event names, keyed by event types, for all events
           in this calendar and p_otherCalendars).'''
        res = {}
        if eventTypes:
            for et in eventTypes:
                res[et] = self.getEventName(obj, et)
        if not otherCalendars: return res
        for other, field, color in otherCalendars:
            eventTypes = field.getEventTypes(other)
            if eventTypes:
                for et in eventTypes:
                    if et not in res:
                        res[et] = field.getEventName(other, et)
        return res

    def getStartDate(self, obj):
        '''Get the start date for this calendar if defined'''
        if self.startDate:
            d = self.startDate(obj.appy())
            # Return the start date without hour, in UTC
            return DateTime('%d/%d/%d UTC' % (d.year(), d.month(), d.day()))

    def getEndDate(self, obj):
        '''Get the end date for this calendar if defined'''
        if self.endDate:
            d = self.endDate(obj.appy())
            # Return the end date without hour, in UTC.
            return DateTime('%d/%d/%d UTC' % (d.year(), d.month(), d.day()))

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
        # Check that the "preferences" dict exists or not
        if not hasattr(obj.aq_base, self.name):
            # 1st level: create a IOBTree whose keys are years
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
        # Create and store the event, excepted if an event already exists
        if not events:
            event = Object(eventType=eventType)
            events.append(event)
        # Span the event on the successive days if required
        if handleEventSpan and eventSpan:
            nbOfDays = min(int(eventSpan), self.maxEventLength)
            for i in range(nbOfDays):
                date = date + 1
                self.createEvent(obj, date, handleEventSpan=False)

    def mayDelete(self, obj, events):
        '''May the user delete p_events?'''
        if not self.delete: return
        if callable(self.delete): return self.delete(obj, events[0].eventType)
        return True

    def deleteEvent(self, obj, date, handleEventSpan=True):
        '''Deletes an event. It actually deletes all events at p_date.
           If p_handleEventSpan is True, we will use rq["deleteNext"] to
           delete successive events, too.'''
        obj = obj.o # Ensure p_obj is not a wrapper.
        if not self.getEventsAt(obj, date): return
        daysDict = getattr(obj, self.name)[date.year()][date.month()]
        # Remember events, in case we must delete similar ones for next days.
        events = self.getEventsAt(obj, date)
        del daysDict[date.day()]
        rq = obj.REQUEST
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
        # Security check
        obj.mayEdit(self.writePermission, raiseError=True)
        # Get the date for this action
        if action == 'createEvent':
            return self.createEvent(obj, DateTime(rq['day']))
        elif action == 'deleteEvent':
            return self.deleteEvent(obj, DateTime(rq['day']))

    def getColumnStyle(self, obj, date, render, today):
        '''What style(s) must apply to the table column representing p_date
           in the calendar? For timelines only.'''
        if render != 'timeline': return ''
        # Cells representing specific days must have a specific background color
        res = ''
        day = date.aDay()
        if day in Calendar.timelineBgColors:
            res = 'background-color: %s' % Calendar.timelineBgColors[day]
        return res

    def getCellStyle(self, obj, date, render, events):
        '''Gets the cell style to apply to the cell corresponding to p_date.'''
        if render != 'timeline': return '' # Currently, for timelines only
        if not events: return ''
        # Currently, a single event is allowed
        event = events[0]
        return event.bgColor and ('background-color: %s' % event.bgColor) or ''

    def getCellClass(self, obj, date, render, today):
        '''What CSS class(es) must apply to the table cell representing p_date
           in the calendar?'''
        if render != 'month': return '' # Currently, for month rendering only
        res = []
        # We must distinguish between past and future dates
        if date < today:
            res.append('even')
        else:
            res.append('odd')
        # Week-end days must have a specific style
        if date.aDay() in ('Sat', 'Sun'):
            res.append('cellDashed')
        return ' '.join(res)

    def getTimelineMonths(self, grid, obj):
        '''Given the p_grid of dates, this method returns the list of
           corresponding months.'''
        res = []
        for date in grid:
            if not res:
                # Get the month correspoding to the first day in the grid
                m = Object(month=date.aMonth(), colspan=1, year=date.year())
                res.append(m)
            else:
                # Augment current month' colspan or create a new one
                current = res[-1]
                if date.aMonth() == current.month:
                    current.colspan += 1
                else:
                    m = Object(month=date.aMonth(), colspan=1, year=date.year())
                    res.append(m)
        # Replace month short names by translated names whose format may vary
        # according to colspan (a higher colspan allow us to produce a longer
        # month name).
        for m in res:
            text = '%s %d' % (obj.translate('month_%s' % m.month), m.year)
            if m.colspan < 6:
                # Short version: a single letter with an acronym
                m.month = '<acronym title="%s">%s</acronym>' % (text, text[0])
            else:
                m.month = text
        return res
# ------------------------------------------------------------------------------
