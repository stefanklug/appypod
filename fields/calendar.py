# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
import types
from appy import Object
from appy.shared import utils as sutils
from appy.gen import Field
from appy.px import Px
from DateTime import DateTime
from BTrees.IOBTree import IOBTree
from persistent.list import PersistentList
from persistent import Persistent

# ------------------------------------------------------------------------------
class Timeslot:
    '''A timeslot defines a time range within a single day'''
    def __init__(self, id, start=None, end=None, name=None, eventTypes=None):
        # A short, human-readable string identifier, unique among all timeslots
        # for a given Calendar. Id "main" is reserved for the main timeslot that
        # represents the whole day.
        self.id = id
        # The time range can be defined by p_start ~(i_hour, i_minute)~ and
        # p_end (idem), or by a simple name, like "AM" or "PM".
        self.start = start
        self.end = end
        self.name = name or id
        # The event types (among all event types defined at the Calendar level)
        # that can be assigned to this slot.
        self.eventTypes = eventTypes # "None" means "all"
        # "day part" is the part of the day (from 0 to 1.0) that is taken by
        # the timeslot.
        self.dayPart = 1.0

    def allows(self, eventType):
        '''It is allowed to have an event of p_eventType in this timeslot?'''
        # self.eventTypes being None means that no restriction applies
        if not self.eventTypes: return True
        return eventType in self.eventTypes

# ------------------------------------------------------------------------------
class Validation:
    '''The validation process for a calendar consists in "converting" some event
       types being "wishes" to other event types being the corresponding
       validated events. This class holds information about this validation
       process. For more information, see the Calendar constructor, parameter
       "validation".'''
    def __init__(self, method, schema, removeDiscarded=False):
        # p_method holds a method that must return True if the currently logged
        # user can validate whish events.
        self.method = method
        # p_schema must hold a dict whose keys are the event types being wishes
        # and whose values are the event types being the corresponding validated
        # event types.
        self.schema = schema
        # When discarding events, mmust we simply let them there or remove it?
        self.removeDiscarded = removeDiscarded

# ------------------------------------------------------------------------------
class Other:
    '''Identifies a Calendar field that must be shown within another Calendar
       (see parameter "others" in class Calendar).'''
    def __init__(self, obj, name, color='grey'):
        # The object on which this calendar is defined
        self.obj = obj
        # The other calendar instance
        self.field = obj.getField(name)
        # The color into which events from this calendar must be shown (in the
        # month rendering) in the calendar integrating this one.
        self.color = color

    def getEventsInfoAt(self, res, calendar, date, eventNames, inTimeline,
                        colors):
        '''Gets the events defined at p_date in this calendar and append them in
           p_res.'''
        events = self.field.getEventsAt(self.obj.o, date)
        if not events: return
        for event in events:
            eventType = event.eventType
            # Gathered info will be an Object instance
            info = Object(event=event, color=self.color)
            if inTimeline:
                # Get the background color for this cell if it has been defined,
                # or (a) nothing if showUncolored is False, (b) a tooltipped dot
                # else.
                if eventType in colors:
                    info.bgColor = colors[eventType]
                    info.symbol = None
                else:
                    info.bgColor = None
                    if calendar.showUncolored:
                        info.symbol = '<acronym title="%s">▪</acronym>' % \
                                      eventNames[eventType]
                    else:
                        info.symbol = None
            else:
                # Get the event name
                info.name = eventNames[eventType]
            res.append(info)

    def mayValidate(self):
        '''Is validation enabled for this other calendar?'''
        return self.field.mayValidate(self.obj)

# ------------------------------------------------------------------------------
class Total:
    '''Represents a computation that will be executed on a series of cells
       within a timeline calendar.'''
    def __init__(self, initValue): self.value = initValue
    def __repr__(self): return '<Total=%s>' % str(self.value)

class Totals:
    '''For a timeline calendar, if you want to add rows or columns representing
       totals computed from other rows/columns (representing agendas), specify
       it via Totals instances (see Agenda fields "totalRows" and "totalCols"
       below).'''
    def __init__(self, name, label, onCell, initValue=0):
        # "name" must hold a short name or acronym and will directly appear
        # at the beginning of the row. It must be unique within all Totals
        # instances defined for a given Calendar field.
        self.name = name
        # "label" is a i18n label that will be used to produce a longer name
        # that will be shown as an acronym tag around the name.
        self.label = label
        # A method that will be called every time a cell is walked in the
        # agenda. It will get these args:
        # * date       - the date representing the current day;
        # * other      - the Other instance representing the currently walked
        #                calendar;
        # * events     - the list of events (as Event instances) defined at that
        #                day in this calendar. Be careful: this can be None;
        # * total      - the Total instance (see above) corresponding to the
        #                current column;
        # * last       - a boolean that is True if we are walking the last shown
        #                calendar;
        # * checked    - a value "checked" indicating the status of the possible
        #                validation checkbox corresponding to this cell. If
        #                there is a checkbox in this cell, the value will be
        #                True or False; else, the value will be None.
        # * preCompute - the result of Calendar.preCompute (see below)
        self.onCell = onCell
        # "initValue" is the initial value given to created Total instances
        self.initValue = initValue

# ------------------------------------------------------------------------------
class Event(Persistent):
    '''An event as will be stored in the database'''
    def __init__(self, eventType, timeslot='main'):
        self.eventType = eventType
        self.timeslot = timeslot

    def getName(self, allEventNames=None, xhtml=True):
        '''Gets the name for this event, that depends on it type and may include
           the timeslot if not "main".'''
        # If we have the translated names for event types, use it.
        if allEventNames:
            res = allEventNames[self.eventType]
        else:
            res = self.eventType
        if self.timeslot != 'main':
            # Prefix it with the timeslot
            prefix = xhtml and ('<b>[%s]</b> ' % self.timeslot) or \
                               ('[%s] ' % self.timeslot)
            res = '%s%s' % (prefix, res)
        return res

    def sameAs(self, other):
        '''Is p_self the same as p_other?'''
        return (self.eventType == other.eventType) and \
               (self.timeslot == other.timeslot)

    def getDayPart(self, field):
        '''What is the day part taken by this event ?'''
        return field.getTimeslot(self.timeslot).dayPart

# ------------------------------------------------------------------------------
class Calendar(Field):
    '''This field allows to produce an agenda (monthly view) and view/edit
       events on it.'''
    jsFiles = {'view': ('calendar.js',)}
    DateTime = DateTime
    # Access to Calendar utility classes via the Calendar class
    Timeslot = Timeslot
    Validation = Validation
    Other = Other
    Totals = Totals
    Event = Event
    IterSub = sutils.IterSub
    # Error messages
    TIMELINE_WITH_EVENTS = 'A timeline calendar has the objective to display ' \
      'a series of other calendars. Its own calendar is disabled: it is ' \
      'useless to define event types for it.'
    MISSING_EVENT_NAME_METHOD = "When param 'eventTypes' is a method, you " \
      "must give another method in param 'eventNameMethod'."
    TIMESLOT_USED = 'An event is already defined at this timeslot.'
    DAY_FULL = 'No more place for adding this event.'
    TOTALS_MISUSED = 'Totals can only be specified for timelines ' \
      '(render == "timeline").'

    timelineBgColors = {'Fri': '#dedede', 'Sat': '#c0c0c0', 'Sun': '#c0c0c0'}
    validCbStatuses = {'validated': True, 'discarded': False}

    # For timeline rendering, the row displaying month names
    pxTimeLineMonths = Px('''
     <tr>
      <th class="hidden"></th>
      <th for="mInfo in monthsInfos" colspan=":mInfo.colspan">::mInfo.month</th>
      <th class="hidden"></th>
     </tr>''')

    # For timeline rendering, the row displaying day letters
    pxTimelineDayLetters = Px('''
     <tr>
      <td class="hidden"></td>
      <td for="date in grid"><b>:namesOfDays[date.aDay()].name[0]</b></td>
      <td class="hidden"></td>
     </tr>''')

    # For timeline rendering, the row displaying day numbers
    pxTimelineDayNumbers = Px('''
     <tr>
      <td class="hidden"></td>
      <td for="date in grid"><b>:str(date.day()).zfill(2)</b></td>
      <td class="hidden"></td>
     </tr>''')

    # Legend for a timeline calendar
    pxTimelineLegend = Px('''
     <table align="center" class="discreet"
            var="items=field.getLegendItems(allEventTypes, allEventNames, \
                                            colors, url, _)">
      <tr for="row in field.splitList(items, 4)">
       <x for="item in row">
        <td><table> <!-- A colored cell (as mono-cell sub-table) -->
          <tr height="9px"><td width="9px" style=":item.style">&nbsp;</td></tr>
        </table></td>
        <!-- The event name -->
        <td width="115px">:item.name</td>
       </x>
      </tr>
     </table>''')

    # Displays the total rows at the bottom of a timeline calendar
    pxTotalRows = Px('''
     <tbody id=":'%s_trs' % ajaxHookId"
            var="totals=field.computeTotals('row', zobj, grid, others, \
                                            preComputed)">
      <script>:field.getAjaxDataTotals('rows', ajaxHookId)</script>
      <tr for="row in field.totalRows" var2="rowTitle=_(row.label)">
       <td class="tlLeft">
        <acronym title=":rowTitle"><b>:row.name</b></acronym></td>
       <td for="date in grid">::totals[row.name][loop.date.nb].value</td>
       <td class="tlRight">
        <acronym title=":rowTitle"><b>:row.name</b></acronym></td>
      </tr>
     </tbody>''')

    # Displays the total columns besides the calendar, as a separate table
    pxTotalCols = Px('''
     <table cellpadding="0" cellspacing="0" class="list timeline"
            style="float:right" id=":'%s_tcs' % ajaxHookId"
            var="totals=field.computeTotals('col', zobj, grid, others, \
                                            preComputed)">
      <script>:field.getAjaxDataTotals('cols', ajaxHookId)</script>
      <tr for="i in range(2)"> <!-- 2 empty rows -->
       <td for="col in field.totalCols" class="hidden">&nbsp;</td>
      </tr>
      <tr> <!-- The column headers -->
       <th for="col in field.totalCols">
        <acronym title=":_(col.label)">:col.name</acronym>
       </th>
      </tr>
      <!-- Re-create one row for every other calendar -->
      <x var="i=-1" for="otherGroup in others">
       <tr for="other in otherGroup" var2="@i=i+1">
        <td for="col in field.totalCols">::totals[col.name][i].value</td>
       </tr>
       <!-- The separator between groups of other calendars -->
       <x if="not loop.otherGroup.last">::field.getOthersSep(\
         len(field.totalCols))</x>
      </x>
      <!-- Add empty rows for every total row -->
      <tr for="i in range(len(field.totalRows))">
       <td for="col in field.totalCols">&nbsp;</td>
      </tr>
      <tr> <!-- Repeat the column headers -->
       <th for="col in field.totalCols">
        <acronym title=":_(col.label)">:col.name</acronym>
       </th>
      </tr>
      <tr for="i in range(2)"> <!-- 2 empty rows -->
       <td for="col in field.totalCols" class="hidden">&nbsp;</td>
      </tr>
     </table>''')

    # Ajax-call pxTotalRows or pxTotalCols
    pxTotalsFromAjax = Px('''
     <x var="month=req['month'];
             totalType=req['totalType'].capitalize();
             ajaxHookId=zobj.id + field.name;
             monthDayOne=field.DateTime('%s/01' % month);
             grid=field.getGrid(month, 'timeline');
             preComputed=field.getPreComputedInfo(zobj, monthDayOne, grid);
             others=field.getOthers(zobj, \
               preComputed)">:getattr(field, 'pxTotal%s' % totalType)</x>''')

    # Timeline view for a calendar
    pxViewTimeline = Px('''
     <table cellpadding="0" cellspacing="0" class="list timeline"
            id=":ajaxHookId + '_cal'" style="display: inline-block"
            var="monthsInfos=field.getTimelineMonths(grid, zobj)">
      <colgroup> <!-- Column specifiers -->
       <col/> <!-- 1st col: Names of calendars -->
       <col for="date in grid"
            style=":field.getColumnStyle(zobj, date, render, today)"/>
       <col/>
      </colgroup>
      <tbody>
       <!-- Header rows (months and days) -->
       <x>:field.pxTimeLineMonths</x>
       <x>:field.pxTimelineDayLetters</x><x>:field.pxTimelineDayNumbers</x>
       <!-- Other calendars -->
       <x for="otherGroup in others">
        <tr for="other in otherGroup"
            var2="tlName=field.getTimelineName(other);
                 mayValidate=mayValidate and other.mayValidate()">
         <td class="tlLeft">::tlName</td>
         <!-- A cell in this other calendar -->
         <x for="date in grid"
            var2="inRange=field.dateInRange(date, startDate, endDate)">
          <td if="not inRange"></td>
          <x if="inRange">::field.getTimelineCell(req, zobj)</x>
         </x>
         <td class="tlRight">::tlName</td>
        </tr>
        <!-- The separator between groups of other calendars -->
        <x if="not loop.otherGroup.last">::field.getOthersSep(len(grid)+2)</x>
       </x>
      </tbody>
      <!-- Total rows -->
      <x if="field.totalRows">:field.pxTotalRows</x>
      <tbody> <!-- Footer (repetition of months and days) -->
       <x>:field.pxTimelineDayNumbers</x><x>:field.pxTimelineDayLetters</x>
       <x>:field.pxTimeLineMonths</x>
      </tbody>
     </table>
     <!-- Total columns, as a separate table -->
     <x if="field.totalCols">:field.pxTotalCols</x>
     <x>:field.pxTimelineLegend</x>''')

    # Popup for adding an event in the month view
    pxAddPopup = Px('''
     <div var="popupId=ajaxHookId + '_new'"
          id=":popupId" class="popup" align="center">
      <form id=":popupId + 'Form'" method="post" action="/process">
       <input type="hidden" name="fieldName" value=":field.name"/>
       <input type="hidden" name="month" value=":month"/>
       <input type="hidden" name="name" value=":field.name"/>
       <input type="hidden" name="actionType" value="createEvent"/>
       <input type="hidden" name="day"/>

       <!-- Choose an event type -->
       <div align="center" style="margin-bottom: 3px">:_('which_event')</div>
       <select name="eventType" style="margin-bottom: 10px">
        <option value="">:_('choose_a_value')</option>
        <option for="eventType in eventTypes"
                value=":eventType">:allEventNames[eventType]</option>
       </select>
       <!-- Choose a timeslot -->
       <div if="showTimeslots" style="margin-bottom: 10px">
        <span class="discreet">:_('timeslot')</span>
        <select if="showTimeslots" name="timeslot">
         <option value="main">:_('timeslot_main')</option>
         <option for="timeslot in field.timeslots"
                 if="timeslot.id != 'main'">:timeslot.name</option>
        </select>
       </div>
       <!-- Span the event on several days -->
       <div align="center" class="discreet" style="margin-bottom: 3px">
        <span>:_('event_span')</span>
        <input type="text" size="3" name="eventSpan"/>
       </div>
       <input type="button"
              value=":_('object_save')"
              onclick=":'triggerCalendarEvent(%s, %s, %s_maxEventLength)' % \
                        (q(ajaxHookId), q('new'), field.name)"/>
       <input type="button"
              value=":_('object_cancel')"
              onclick=":'closePopup(%s)' % q(popupId)"/>
      </form>
     </div>''')

    # Popup for removing events in the month view
    pxDelPopup = Px('''
     <div var="popupId=ajaxHookId + '_del'"
          id=":popupId" class="popup" align="center">
      <form id=":popupId + 'Form'" method="post" action="/process">
       <input type="hidden" name="fieldName" value=":field.name"/>
       <input type="hidden" name="month" value=":month"/>
       <input type="hidden" name="name" value=":field.name"/>
       <input type="hidden" name="actionType" value="deleteEvent"/>
       <input type="hidden" name="timeslot" value="main"/>
       <input type="hidden" name="day"/>
       <div align="center"
            style="margin-bottom: 5px">:_('action_confirm')</div>

       <!-- Delete successive events ? -->
       <div class="discreet" style="margin-bottom: 10px"
            id=":ajaxHookId + '_DelNextEvent'"
            var="cbId=popupId + '_cb'; hdId=popupId + '_hd'">
         <input type="checkbox" name="deleteNext_cb" id=":cbId"
                onClick=":'toggleCheckbox(%s, %s)' % (q(cbId), q(hdId))"/>
         <input type="hidden" id=":hdId" name="deleteNext"/>
         <label lfor=":cbId" class="simpleLabel">:_('del_next_events')</label>
       </div>
       <input type="button" value=":_('yes')"
              onClick=":'triggerCalendarEvent(%s, %s)' % \
                        (q(ajaxHookId), q('del'))"/>
       <input type="button" value=":_('no')"
              onclick=":'closePopup(%s)' % q(popupId)"/>
      </form>
     </div>''')

    # Month view for a calendar
    pxViewMonth = Px('''
      <table cellpadding="0" cellspacing="0" width="100%" class="list"
             style="font-size: 95%" id=":ajaxHookId + '_cal'"
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
                   single=events and (len(events) == 1);
                   spansDays=field.hasEventsAt(zobj, date+1, events);
                   mayCreate=mayEdit and not field.dayIsFull(date, events);
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
                var="info=field.getApplicableEventTypesAt(zobj, date, \
                           eventTypes, preComputed, True)"
                if="info and info.eventTypes" src=":url('plus')"
                var2="freeSlots=field.getFreeSlotsAt(date, events, slotIds,\
                                                     slotIdsStr, True)"
                onclick=":'openEventPopup(%s,%s,%s,null,null,%s,%s,%s)' % \
                 (q(ajaxHookId), q('new'), q(dayString), q(info.eventTypes), \
                  q(info.message), q(freeSlots))"/>
          </x>
          <!-- Icon for deleting event(s) -->
          <img if="mayDelete" class="clickable" style="visibility:hidden"
               src=":url(single and 'delete' or 'deleteMany')"
               onclick=":'openEventPopup(%s,%s,%s,%s,%s)' %  (q(ajaxHookId), \
                          q('del'), q(dayString), q('main'), q(spansDays))"/>
          <!-- Events -->
          <x if="events">
          <div for="event in events" style="color: grey">
           <!-- Checkbox for validating the event -->
           <input type="checkbox" checked="checked" class="smallbox"
               if="mayValidate and (event.eventType in field.validation.schema)"
               id=":'%s_%s_%s' % (date.strftime('%Y%m%d'), event.eventType, \
                                  event.timeslot)"
               onclick=":'onCheckCbCell(this,%s)' % q(ajaxHookId)"/>
           <x>::event.getName(allEventNames)</x>
           <!-- Icon for delete this particular event -->
            <img if="mayDelete and not single" class="clickable"
                 src=":url('delete')"  style="visibility:hidden"
                 onclick=":'openEventPopup(%s,%s,%s,%s)' % (q(ajaxHookId), \
                            q('del'), q(dayString), q(event.timeslot))"/>
          </div>
          </x>
          <!-- Events from other calendars -->
          <x if="others"
             var2="otherEvents=field.getOtherEventsAt(zobj, date, \
                                others, allEventNames, render, colors)">
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

      <!-- Popups for creating and deleting a calendar event -->
      <x if="mayEdit and eventTypes">
       <x>:field.pxAddPopup</x><x>:field.pxDelPopup</x></x>''')

    pxView = pxCell = Px('''
     <div var="defaultDate=field.getDefaultDate(zobj);
               defaultDateMonth=defaultDate.strftime('%Y/%m');
               ajaxHookId=zobj.id + field.name;
               month=req.get('month', defaultDate.strftime('%Y/%m'));
               monthDayOne=field.DateTime('%s/01' % month);
               render=req.get('render', field.render);
               today=field.DateTime('00:00');
               grid=field.getGrid(month, render);
               eventTypes=field.getEventTypes(zobj);
               preComputed=field.getPreComputedInfo(zobj, monthDayOne, grid);
               previousMonth=field.getSiblingMonth(month, 'previous');
               nextMonth=field.getSiblingMonth(month, 'next');
               mayEdit=zobj.mayEdit(field.writePermission);
               objUrl=zobj.absolute_url();
               startDate=field.getStartDate(zobj);
               endDate=field.getEndDate(zobj);
               others=field.getOthers(zobj, preComputed);
               events=field.getAllEvents(zobj, eventTypes, others);
               allEventTypes=events[0];
               allEventNames=events[1];
               colors=field.getColors(zobj);
               namesOfDays=field.getNamesOfDays(_);
               showTimeslots=len(field.timeslots) &gt; 1;
               slotIds=[slot.id for slot in field.timeslots];
               slotIdsStr=','.join(slotIds);
               mayValidate=field.mayValidate(zobj)"
          id=":ajaxHookId">
      <script>:'var %s_maxEventLength = %d;' % \
                (field.name, field.maxEventLength)</script>
      <script>:field.getAjaxData(ajaxHookId, zobj, render=render, \
                 month=defaultDateMonth)</script>

      <!-- Actions (month chooser, validation) -->
      <div style="margin-bottom: 5px"
           var="fmt='%Y/%m/%d';
                goBack=not startDate or (startDate.strftime(fmt) &lt; \
                                         grid[0][0].strftime(fmt));
                goForward=not endDate or (endDate.strftime(fmt) &gt; \
                                          grid[-1][-1].strftime(fmt))">
       <!-- Go to the previous month -->
       <img class="clickable" if="goBack" src=":url('arrowLeft')"
            onclick=":'askMonth(%s,%s)' % (q(ajaxHookId), q(previousMonth))"/>
       <!-- Go back to the default date -->
       <input type="button" if="goBack or goForward"
              var="fmt='%Y/%m';
                   label=(defaultDate.strftime(fmt)==today.strftime(fmt)) and \
                         'today' or 'goto_source'"
              value=":_(label)"
              onclick=":'askMonth(%s,%s)' % (q(ajaxHookId),q(defaultDateMonth))"
              disabled=":defaultDate.strftime(fmt)==monthDayOne.strftime(fmt)"/>
       <!-- Go to the next month -->
       <img class="clickable" if="goForward" src=":url('arrowRight')"
            onclick=":'askMonth(%s,%s)' % (q(ajaxHookId), q(nextMonth))"/>
       <span>:_('month_%s' % monthDayOne.aMonth())</span>
       <span>:month.split('/')[0]</span>
       <!-- Validate button, with checkbox for automatic checbox selection -->
       <x if="mayValidate">
        <input if="mayValidate" type="button" value=":_('validate_events')"
               class="buttonSmall button" style=":url('validate', bg=True)"
               var2="js='validateEvents(%s,%s)' % (q(ajaxHookId), q(month))"
               onclick=":'askConfirm(%s,%s,%s)' % (q('script'), q(js, False), \
                         q(_('validate_events_confirm')))"/>
        <input type="checkbox" checked="checked" id=":'%s_auto' % ajaxHookId"
               class="smallbox"/>
        <label lfor="selectAuto" class="simpleLabel">:_('select_auto')</label>
       </x>
      </div>
      <!-- The top PX, if defined -->
      <x if="field.topPx">::field.topPx</x>
      <!-- The calendar in itself -->
      <x>:getattr(field, 'pxView%s' % render.capitalize())</x>
      <!-- The bottom PX, if defined -->
      <x if="field.bottomPx">::field.bottomPx</x>
     </div>''')

    pxEdit = pxSearch = ''

    def __init__(self, eventTypes=None, eventNameMethod=None, validator=None,
                 default=None, show=('view', 'xml'), page='main', group=None,
                 layouts=None, move=0, specificReadPermission=False,
                 specificWritePermission=False, width=None, height=300,
                 colspan=1, master=None, masterValue=None, focus=False,
                 mapping=None, label=None, maxEventLength=50, render='month',
                 others=None, timelineName=None, additionalInfo=None,
                 startDate=None, endDate=None, defaultDate=None, timeslots=None,
                 colors=None, showUncolored=False, preCompute=None,
                 applicableEvents=None, totalRows=None, totalCols=None,
                 validation=None, topPx=None, bottomPx=None, view=None,
                 xml=None, delete=True):
        # The "validator" attribute, allowing field-specific validation, behaves
        # differently for the Calendar field. If specified, it must hold a
        # method that will be executed every time a user wants to create an
        # event (or series of events) in the calendar. This method must accept
        # those args:
        #  - date       the date of the event (as a DateTime instance);
        #  - eventType  the event type (one among p_eventTypes);
        #  - timeslot   the timeslot for the event (see param "timeslots"
        #               below);
        #  - span       the number of additional days on wich the event will
        #               span (will be 0 if the user wants to create an event
        #               for a single day).
        # If validation succeeds (ie, the event creation can take place), the
        # method must return True (boolean). Else, it will be canceled and an
        # error message will be shown. If the method returns False (boolean), it
        # will be a standard error message. If the method returns a string, it
        # will be used as specific error message.
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
        if (render == 'timeline') and eventTypes:
            raise Exception(Calendar.TIMELINE_WITH_EVENTS)
        self.eventNameMethod = eventNameMethod
        if callable(eventTypes) and not eventNameMethod:
            raise Exception(Calendar.MISSING_EVENT_NAME_METHOD)
        # It is not possible to create events that span more days than
        # maxEventLength.
        self.maxEventLength = maxEventLength
        # Various render modes exist. Default is the classical "month" view.
        # It can also be "timeline": in this case, on the x axis, we have one
        # column per day, and on the y axis, we have one row per calendar (this
        # one and others as specified in "others", see below).
        self.render = render
        # When displaying a given month for this agenda, one may want to
        # pre-compute, once for the whole month, some information that will then
        # be given as arg for other methods specified in subsequent parameters.
        # This mechanism exists for performance reasons, to avoid recomputing
        # this global information several times. If you specify a method in
        # p_preCompute, it will be called every time a given month is shown, and
        # will receive 2 args: the first day of the currently shown month (as a
        # DateTime instance) and the grid of all shown dates (as a result of
        # calling m_getGrid below). This grid may hold a little more than dates
        # of the current month. Subsequently, the return of your method will be
        # given as arg to other methods that you may specify as args of other
        # parameters of this Calendar class (see comments below).
        self.preCompute = preCompute
        # If a method is specified in parameter "others" below, it must accept a
        # single arg (the result of self.preCompute) and must return a list of
        # calendars whose events must be shown within this agenda. More
        # precisely, the method can return:
        # - a single Other instance (see at the top of this file);
        # - a list of Other instances;
        # - a list of lists of Other instances, when it has sense to group other
        #   calendars (the timeline rendering exploits this).
        self.others = others
        # When displaying a timeline calendar, a name is shown for every other
        # calendar. If "timelineName" is None (the default), this name will be
        # the title of the object where the other calendar is defined. Else, it
        # will be the result of the method specified in "timelineName". This
        # method must return a string and accepts an Other instance as single
        # arg.
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
        # "timeslots" are a way to define, within a single day, time ranges. It
        # must be a list of Timeslot instances (see above). If you define
        # timeslots, the first one must be the one representing the whole day
        # and must have id "main".
        if not timeslots: self.timeslots = [Timeslot('main')]
        else:
            self.timeslots = timeslots
            self.checkTimeslots()
        # "colors" must be or return a dict ~{s_eventType: s_color}~ giving a
        # color to every event type defined in this calendar or in any calendar
        # from "others". In a timeline, cells are too small to display
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
        # In a timeline calendar, if you want to specify additional rows
        # representing totals, give in "totalRows" a list of TotalRow instances
        # (see above).
        if totalRows and (self.render != 'timeline'):
            raise Exception(Calendar.TOTALS_MISUSED)
        self.totalRows = totalRows or []
        # Similarly, you can specify additional columns in "totalCols"
        if totalCols and (self.render != 'timeline'):
            raise Exception(Calendar.TOTALS_MISUSED)
        self.totalCols = totalCols or []
        # A validation process can be associated to a Calendar event. It
        # consists in identifying validators and letting them "convert" event
        # types being wished to final, validated event types. If you want to
        # enable this, define a Validation instance (see the hereabove class)
        # in parameter "validation".
        self.validation = validation
        # May the user delete events in this calendar? If "delete" is a method,
        # it must accept an event type as single arg.
        self.delete = delete
        # You may specify PXs that will show specific information, respectively,
        # before and after the calendar.
        self.topPx = topPx
        self.bottomPx = bottomPx

    def checkTimeslots(self):
        '''Checks whether self.timeslots defines corect timeslots'''
        # The first timeslot must be the global one, named 'main'
        if self.timeslots[0].id != 'main':
            raise Exception('The first timeslot must have id "main" and is ' \
                            'the one representing the whole day.')
        # Set the day parts for every timeslot
        count = len(self.timeslots) - 1 # Count the timeslots, main excepted
        for timeslot in self.timeslots:
            if timeslot.id == 'main': continue
            timeslot.dayPart = 1.0 / count

    def log(self, obj, msg, date=None):
        '''Logs m_msg, field-specifically prefixed.'''
        prefix = '%s:%s' % (obj.id, self.name)
        if date: prefix += '@%s' % date.strftime('%Y/%m/%d')
        obj.log('%s: %s' % (prefix, msg))

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
            # If I write "previousDate = DateTime(currentDay)", the date is
            # converted from UTC to GMT
            previousDate = DateTime('%s/01 UTC' % month)
            # If the 1st day of the month is not a Monday, integrate the last
            # days of the previous month.
            for i in range(1, dayOneNb):
                previousDate -= 1
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

    def getOthers(self, obj, preComputed):
        '''Returns the list of other calendars whose events must also be shown
           on this calendar.'''
        res = None
        if self.others:
            res = self.others(obj.appy(), preComputed)
            if res:
                # Ensure we have a list of lists
                if isinstance(res, Other): res = [res]
                if isinstance(res[0], Other): res = [res]
        if res != None: return res
        return [[]]

    def getOthersSep(self, colspan):
        '''Produces the separator between groups of other calendars'''
        return '<tr style="height: 8px"><th colspan="%s" style="background-' \
               'color: grey"></th></tr>' % colspan

    def getTimelineName(self, other):
        '''Returns the name of some p_other calendar as must be shown in a
           timeline.'''
        if not self.timelineName:
            return '<a href="%s">%s</a>' % (other.obj.url, other.obj.title)
        return self.timelineName(self, other)

    def getTimelineCell(self, req, obj):
        '''Gets the content of a cell in a timeline calendar'''
        # Unwrap some variables from the PX context
        c = req.pxContext
        date = c['date']; other = c['other']; render = 'timeline'
        allEventNames = c['allEventNames']
        # Get the events defined at that day, in the current calendar
        events = self.getOtherEventsAt(obj, date, other, allEventNames, render,
                                       c['colors'])
        # Define the cell's style
        style = self.getCellStyle(obj, date, render, events) or ''
        if style: style = ' style="%s"' % style
        # If a timeline cell hides more than one event, put event names in the
        # "title" attribute.
        title = ''
        if len(events) > 1:
            title = ', '.join(['%s (%s)' % (allEventNames[e.event.eventType], \
                                            e.event.timeslot) for e in events])
            title = ' title="%s"' % title
        # Define its content
        content = ''
        if events and c['mayValidate']:
            # If at least one event from p_events is in the validation schema,
            # propose a unique checkbox, that will allow to validate or not all
            # validable events at p_date.
            for info in events:
                if info.event.eventType in other.field.validation.schema:
                    cbId = '%s_%s_%s' % (other.obj.id, other.field.name,
                                         date.strftime('%Y%m%d'))
                    totalRows = self.totalRows and 'true' or 'false'
                    totalCols = self.totalCols and 'true' or 'false'
                    content = '<input type="checkbox" checked="checked" ' \
                      'class="smallbox" id="%s" onclick="onCheckCbCell(this,' \
                      '\'%s\',%s,%s)"/>' % \
                      (cbId, c['ajaxHookId'], totalRows, totalCols)
                    break
        elif len(events) == 1:
            # A single event: if not colored, show a symbol. When there are
            # multiple events, a background image is already shown (see the
            # "style" attribute), so do not show any additional info.
            content = events[0].symbol or '' 
        return '<td%s%s>%s</td>' % (style, title, content)

    def getLegendItems(self, allEventTypes, allEventNames, colors, url, _):
        '''Gets information needed to produce the legend for a timeline.'''
        # Produce one legend item by event type shown and colored
        res = []
        for eventType in allEventTypes:
            if eventType not in colors: continue
            res.append(Object(name=allEventNames[eventType],
                              style='background-color: %s' % colors[eventType]))
        # Add the background indicating that several events are hidden behind
        # the timeline cell
        res.append(Object(name=_('several_events'),
                          style=url('angled', bg=True)))
        return res

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
        '''Gets the colors for event types managed by this calendar and others
           (from self.colors).'''
        if callable(self.colors): return self.colors(obj)
        return self.colors

    def dayIsFull(self, date, events):
        '''In the calendar full at p_date? Defined events at this p_date are in
           p_events. We check here if the main timeslot is used or if all
           others are used.'''
        if not events: return
        for e in events:
            if e.timeslot == 'main': return True
        return len(events) == len(self.timeslots)-1

    def dateInRange(self, date, startDate, endDate):
        '''Is p_date within the range (possibly) defined for this calendar by
           p_startDate and p_endDate ?'''
        tooEarly = startDate and (date < startDate)
        tooLate = endDate and not tooEarly and (date > endDate)
        return not tooEarly and not tooLate

    def getApplicableEventTypesAt(self, obj, date, eventTypes, preComputed,
                                  forBrowser=False):
        '''Returns the event types that are applicable at a given p_date. More
           precisely, it returns an object with 2 attributes:
           * "events" is the list of applicable event types;
           * "message", not empty if some event types are not applicable,
                        contains a message explaining those event types are
                        not applicable.
        '''
        if not eventTypes: return # There may be no event type at all
        if not self.applicableEvents:
            # Keep p_eventTypes as is
            message = None
        else:
            eventTypes = eventTypes[:]
            message = self.applicableEvents(obj.appy(), date, eventTypes,
                                            preComputed)
        res = Object(eventTypes=eventTypes, message=message)
        if forBrowser:
            res.eventTypes = ','.join(res.eventTypes)
            if not res.message: res.message = ''
        return res

    def getFreeSlotsAt(self, date, events, slotIds, slotIdsStr,
                       forBrowser=False):
        '''Gets the free timeslots in this calendar for some p_date. As a
           precondition, we know that the day is not full (so timeslot "main"
           cannot be taken). p_events are those already defined at p_date.
           p_slotIds is the precomputed list of timeslot ids.'''
        if not events: return forBrowser and slotIdsStr or slotIds
        # Remove any taken slot
        res = slotIds[1:] # "main" cannot be chosen: p_events is not empty
        for event in events: res.remove(event.timeslot)
        # Return the result
        if not forBrowser: return res
        return ','.join(res)

    def getTimeslot(self, id):
        '''Get the timeslot corresponding to p_id'''
        for slot in self.timeslots:
            if slot.id == id: return slot

    def getEventsAt(self, obj, date):
        '''Returns the list of events that exist at some p_date (=day). p_date
           can be:
           * a DateTime instance;
           * a tuple (i_year, i_month, i_day);
           * a string YYYYmmdd.
        '''
        obj = obj.o # Ensure p_obj is not a wrapper
        if not hasattr(obj.aq_base, self.name): return
        years = getattr(obj, self.name)
        # Get year, month and name from p_date
        if isinstance(date, tuple):
            year, month, day = date
        elif isinstance(date, str):
            year, month, day = int(date[:4]), int(date[4:6]), int(date[6:8])
        else:
            year, month, day = date.year(), date.month(), date.day()
        # Dig into the oobtree
        if year not in years: return
        months = years[year]
        if month not in months: return
        days = months[month]
        if day not in days: return
        return days[day]

    def getEventTypeAt(self, obj, date):
        '''Returns the event type of the first event defined at p_day, or None
           if unspecified.'''
        events = self.getEventsAt(obj, date)
        if not events: return
        return events[0].eventType

    def standardizeDateRange(self, range):
        '''p_range can have various formats (see m_walkEvents below). This
           method standardizes the date range as a 6-tuple
           (startYear, startMonth, startDay, endYear, endMonth, endDay).'''
        if not range: return
        if isinstance(range, int):
            # p_range represents a year
            return (range, 1, 1, range, 12, 31)
        elif isinstance(range[0], int):
            # p_range represents a month
            year, month = range
            return (year, month, 1, year, month, 31)
        else:
            # p_range is a tuple (start, end) of DateTime instances
            start, end = range
            return (start.year(), start.month(), start.day(),
                    end.year(),   end.month(),   end.day())

    def walkEvents(self, obj, callback, dateRange=None):
        '''Walks on p_obj, the calendar value in chronological order for this
           field and calls p_callback for every day containing events. The
           callback must accept 3 args: p_obj, the current day (as a DateTime
           instance) and the list of events at that day (the database-stored
           PersistentList instance). If the callback returns True we stop the
           walk.

           If p_dateRange is specified, it limits the walk to this range. It
           can be:
           * an integer, representing a year;
           * a tuple of integers (year, month) representing a given month
             (first month is numbered 1);
           * a tuple (start, end) of DateTime instances.
        '''
        obj = obj.o
        if not hasattr(obj, self.name): return
        yearsDict = getattr(obj, self.name)
        if not yearsDict: return
        # Standardize date range
        if dateRange:
            startYear, startMonth, startDay, endYear, endMonth, endDay = \
              self.standardizeDateRange(dateRange)
        # Browse years
        years = list(yearsDict.keys())
        years.sort()
        for year in years:
            # Ignore this year if out of range
            if dateRange:
                if (year < startYear) or (year > endYear): continue
                isStartYear = year == startYear
                isEndYear = year == endYear
            # Browse this year's months
            monthsDict = yearsDict[year]
            if not monthsDict: continue
            months = list(monthsDict.keys())
            months.sort()
            for month in months:
                # Ignore this month if out of range
                if dateRange:
                    if (isStartYear and (month < startMonth)) or \
                       (isEndYear and (month > endMonth)): continue
                    isStartMonth = isStartYear and (month == startMonth)
                    isEndMonth = isEndYear and (month == endMonth)
                # Browse this month's days
                daysDict = monthsDict[month]
                if not daysDict: continue
                days = list(daysDict.keys())
                days.sort()
                for day in days:
                    # Ignore this day if out of range
                    if dateRange:
                        if (isStartMonth and (day < startDay)) or \
                           (isEndMonth and (day > endDay)): continue
                    date = DateTime('%d/%d/%d UTC' % (year, month, day))
                    stop = callback(obj, date, daysDict[day])
                    if stop: return

    def getEventsByType(self, obj, eventType, minDate=None, maxDate=None,
                        sorted=True, groupSpanned=False):
        '''Returns all the events of a given p_eventType. If p_eventType is
           None, it returns events of all types. p_eventType can also be a
           list or tuple. The return value is a list of 2-tuples whose 1st elem
           is a DateTime instance and whose 2nd elem is the event.

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
        obj = obj.o # Ensure p_obj is not a wrapper
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
                        if eventType:
                            if isinstance(eventType, str):
                                keepIt = (event.eventType == eventType)
                            else:
                                keepIt = (event.eventType in eventType)
                            if not keepIt: continue
                        # We have found a event
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

    def hasEventsAt(self, obj, date, events):
        '''Returns True if, at p_date, events are exactly of the same type as
           p_events.'''
        if not events: return
        others = self.getEventsAt(obj, date)
        if not others: return
        if len(events) != len(others): return
        i = 0
        while i < len(events):
            if not events[i].sameAs(others[i]): return
            i += 1
        return True

    def getOtherEventsAt(self, obj, date, others, eventNames, render, colors):
        '''Gets events that are defined in p_others at some p_date. If p_single
           is True, p_others does not contain the list of all other calendars,
           but information about a single calendar.'''
        res = []
        isTimeline = render == 'timeline'
        if isinstance(others, Other):
            others.getEventsInfoAt(res, self, date, eventNames, isTimeline,
                                   colors)
        else:
            for other in sutils.IterSub(others):
                other.getEventsInfoAt(res, self, date, eventNames, isTimeline,
                                      colors)
        return res

    def getEventName(self, obj, eventType):
        '''Gets the name of the event corresponding to p_eventType as it must
           appear to the user.'''
        if self.eventNameMethod:
            return self.eventNameMethod(obj.appy(), eventType)
        else:
            return obj.translate('%s_event_%s' % (self.labelId, eventType))

    def getAllEvents(self, obj, eventTypes, others):
        '''Computes:
           * the list of all event types (from this calendar and p_others);
           * a dict of event names, keyed by event types, for all events
             in this calendar and p_others).'''
        res = [[], {}]
        if eventTypes:
            for et in eventTypes:
                res[0].append(et)
                res[1][et] = self.getEventName(obj, et)
        if not others: return res
        for other in sutils.IterSub(others):
            eventTypes = other.field.getEventTypes(other.obj)
            if eventTypes:
                for et in eventTypes:
                    if et not in res[1]:
                        res[0].append(et)
                        res[1][et] = other.field.getEventName(other.obj, et)
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
            # Return the end date without hour, in UTC
            return DateTime('%d/%d/%d UTC' % (d.year(), d.month(), d.day()))

    def getDefaultDate(self, obj):
        '''Get the default date that must appear as soon as the calendar is
           shown.'''
        if self.defaultDate:
            return self.defaultDate(obj.appy())
        else:
            return DateTime() # Now

    def checkCreateEvent(self, obj, eventType, timeslot, events):
        '''Checks if one may create an event of p_eventType in p_timeslot.
           Events already defined at p_date are in p_events. If the creation is
           not possible, an error message is returned.'''
        # The following errors should not occur if we have a normal user behind
        # the ui.
        for e in events:
            if e.timeslot == timeslot: return Calendar.TIMESLOT_USED
            elif e.timeslot == 'main': return Calendar.DAY_FULL
        if events and (timeslot == 'main'): return Calendar.DAY_FULL
        # Get the Timeslot and check if, at this timeslot, it is allowed to
        # create an event of p_eventType.
        for slot in self.timeslots:
            if slot.id == timeslot:
                # I have the timeslot
                if not slot.allows(eventType):
                    _ = obj.translate
                    return _('timeslot_misfit', mapping={'slot': timeslot})

    def mergeEvent(self, eventType, timeslot, events):
        '''If, after adding an event of p_eventType, all timeslots are used with
           events of the same type, we can merge them and create a single event
           of this type in the main timeslot.'''
        # When defining an event in the main timeslot, no merge is needed
        if timeslot == 'main': return
        # Merge is required when all non-main timeslots are used by events of
        # the same type.
        if len(events) != (len(self.timeslots)-2): return
        for event in events:
            if event.eventType != eventType: return
        # If we are here, we must merge all events
        del events[:]
        events.append(Event(eventType))
        return True

    def createEvent(self, obj, date, eventType, timeslot='main', eventSpan=None,
                    handleEventSpan=True):
        '''Create a new event in the calendar, at some p_date (day). If
           p_handleEventSpan is True, we will use p_eventSpan and also create
           the same event for successive days.'''
        obj = obj.o # Ensure p_obj is not a wrapper
        rq = obj.REQUEST
        # Get values from parameters
        if not eventType: eventType = rq['eventType']
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
        # Return an error if the creation cannot occur
        error = self.checkCreateEvent(obj, eventType, timeslot, events)
        if error: return error
        # Merge this event with others when relevant
        merged = self.mergeEvent(eventType, timeslot, events)
        if not merged:
            # Create and store the event
            events.append(Event(eventType, timeslot))
            # Sort events in the order of timeslots
            if len(events) > 1:
                timeslots = [slot.id for slot in self.timeslots]
                events.data.sort(key=lambda e: timeslots.index(e.timeslot))
                events._p_changed = 1
        # Span the event on the successive days if required
        suffix = ''
        if handleEventSpan and eventSpan:
            for i in range(eventSpan):
                date = date + 1
                self.createEvent(obj, date, eventType, timeslot,
                                 handleEventSpan=False)
                suffix = ', span+%d' % eventSpan
        if handleEventSpan:
            msg = 'added %s, slot %s%s' % (eventType, timeslot, suffix)
            self.log(obj, msg, date)

    def mayDelete(self, obj, events):
        '''May the user delete p_events?'''
        if not self.delete: return
        if callable(self.delete): return self.delete(obj, events[0].eventType)
        return True

    def deleteEvent(self, obj, date, timeslot, handleEventSpan=True):
        '''Deletes an event. If t_timeslot is "main", it deletes all events at
           p_date, be there a single event on the main timeslot or several
           events on other timeslots. Else, it only deletes the event at
           p_timeslot. If p_handleEventSpan is True, we will use
           rq["deleteNext"] to delete successive events, too.'''
        obj = obj.o # Ensure p_obj is not a wrapper
        if not self.getEventsAt(obj, date): return
        daysDict = getattr(obj, self.name)[date.year()][date.month()]
        events = self.getEventsAt(obj, date)
        count = len(events)
        eNames = ', '.join([e.getName(xhtml=False) for e in events])
        if timeslot == 'main':
            # Delete all events; delete them also in the following days when
            # relevant.
            del daysDict[date.day()]
            rq = obj.REQUEST
            suffix = ''
            if handleEventSpan and rq.has_key('deleteNext') and \
               (rq['deleteNext'] == 'True'):
                nbOfDays = 0
                while True:
                    date = date + 1
                    if self.hasEventsAt(obj, date, events):
                        self.deleteEvent(obj, date, timeslot,
                                         handleEventSpan=False)
                        nbOfDays += 1
                    else:
                        break
                if nbOfDays: suffix = ', span+%d' % nbOfDays
            if handleEventSpan:
                msg = '%s deleted (%d)%s.' % (eNames, count, suffix)
                self.log(obj, msg, date)
        else:
            # Delete the event at p_timeslot
            i = len(events) - 1
            while i >= 0:
                if events[i].timeslot == timeslot:
                    msg = '%s deleted at slot %s.' % \
                          (events[i].getName(xhtml=False), timeslot)
                    del events[i]
                    self.log(obj, msg, date)
                    break
                i -= 1

    def validate(self, obj, date, eventType, timeslot, span=0):
        '''The validation process for a calendar is a bit different from the
           standard one, that checks a "complete" request value. Here, we only
           check the validity of some insertion of events within the
           calendar.'''
        if not self.validator: return
        res = self.validator(obj, date, eventType, timeslot, span)
        if isinstance(res, basestring):
            # Validation failed, and we have the error message in "res"
            return res
        if not res:
            # Validation failed, without specific message: return a standard one
            return obj.translate('field_invalid')
        return res

    def process(self, obj):
        '''Processes an action coming from the calendar widget, ie, the creation
           or deletion of a calendar event.'''
        rq = obj.REQUEST
        action = rq['actionType']
        # Security check
        obj.mayEdit(self.writePermission, raiseError=True)
        # Get the date and timeslot for this action
        date = DateTime(rq['day'])
        eventType = rq.get('eventType')
        timeslot = rq.get('timeslot', 'main')
        eventSpan = rq.get('eventSpan') or 0
        eventSpan = min(int(eventSpan), self.maxEventLength)
        if action == 'createEvent':
            # Trigger validation
            valid = self.validate(obj.appy(), date, eventType, timeslot,
                                  eventSpan)
            if isinstance(valid, basestring): return valid
            return self.createEvent(obj, date, eventType, timeslot, eventSpan)
        elif action == 'deleteEvent':
            return self.deleteEvent(obj, date, timeslot)

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
        if render != 'timeline': return # Currently, for timelines only
        if not events: return
        elif len(events) > 1:
            # Return a special background indicating that several events are
            # hidden behing this cell.
            return 'background-image: url(%s/ui/angled.png)' % \
                   obj.getTool().getSiteUrl()
        else:
            event = events[0]
            if event.bgColor: return 'background-color: %s' % event.bgColor

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

    def splitList(self, l, sub): return sutils.splitList(l, sub)
    def mayValidate(self, obj):
        '''May the currently logged user validate wish events ?'''
        if not self.validation: return
        return self.validation.method(obj.appy())

    def getAjaxData(self, hook, zobj, **params):
        '''Initializes an AjaxData object on the DOM node corresponding to
           this calendar field.'''
        params = sutils.getStringDict(params)
        return "new AjaxData('%s', '%s:pxView', %s, null, '%s')" % \
               (hook, self.name, params, zobj.absolute_url())

    def getAjaxDataTotals(self, type, hook):
        '''Initializes an AjaxData object on the DOM node corresponding to
           the zone containing the total rows/cols (depending on p_type) in a
           timeline calendar.'''
        suffix = (type == 'rows') and 'trs' or 'tcs'
        return "new AjaxData('%s_%s', '%s:pxTotalsFromAjax', {}, '%s')" % \
               (hook, suffix, self.name, hook)

    def validateEvents(self, obj):
        '''Validate or discard events from the request'''
        rq = obj.REQUEST.form
        counts = {'validated': 0, 'discarded': 0}
        removeDiscarded = self.validation.removeDiscarded
        tool = obj.getTool()
        for action in ('validated', 'discarded'):
            if not rq[action]: continue
            for info in rq[action].split(','):
                if rq['render'] == 'month':
                    # Every checkbox corresponds to an event at at given date,
                    # with a given event type at a given timeslot, in this
                    # calendar (self) on p_obj.
                    date, eventType, timeslot = info.split('_')
                    # Get the events defined at that date
                    events = self.getEventsAt(obj, date)
                    i = len(events) - 1
                    while i >= 0:
                        # Get the event at that timeslot
                        event = events[i]
                        if event.timeslot == timeslot:
                            # We have found the event
                            if event.eventType != eventType:
                                raise Exception('Wrong event type')
                            # Validate or discard it
                            if action == 'validated':
                                schema = self.validation.schema
                                event.eventType = schema[eventType]
                            else:
                                if removeDiscarded: del events[i]
                            counts[action] += 1
                        i -= 1
                elif rq['render'] == 'timeline':
                    # Every checkbox corresponds to a given date in some
                    # calendar (self, or one among self.others). It means that
                    # all "impactable" events at that date will be the target
                    # of the action.
                    otherId, fieldName, date = info.split('_')
                    otherObj = tool.getObject(otherId)
                    otherField = otherObj.getAppyType(fieldName)
                    # Get, on this calendar, the events defined at that date
                    events = otherField.getEventsAt(otherObj, date)
                    # Among them, validate or discard any impactable one
                    schema = otherField.validation.schema
                    i = len(events) - 1
                    while i >= 0:
                        event = events[i]
                        # Take this event into account only if in the schema
                        if event.eventType in schema:
                            if action == 'validated':
                                event.eventType = schema[event.eventType]
                            else:
                                # "self" imposes its own "removeDiscarded"
                                if removeDiscarded: del events[i]
                            counts[action] += 1
                        i -= 1
        if not counts['validated'] and not counts['discarded']:
            return obj.translate('action_null')
        part = not removeDiscarded and ' (but not removed)' or ''
        self.log(obj, '%d event(s) validated and %d discarded%s.' % \
                 (counts['validated'], counts['discarded'], part))
        return obj.translate('validate_events_done', mapping=counts)

    def getValidationCheckboxesStatus(self, obj):
        '''Gets the status of the validation checkboxes from the request'''
        res = {}
        req = obj.REQUEST
        for status, value in Calendar.validCbStatuses.iteritems():
            ids = req.get(status)
            if ids:
                for id in ids.split(','): res[id] = value
        return res

    def computeTotals(self, totalType, obj, grid, others, preComputed):
        '''Compute the totals for every column (p_totalType == 'row') or row
           (p_totalType == "col").'''
        obj = obj.appy()
        allTotals = getattr(self, 'total%ss' % totalType.capitalize())
        if not allTotals: return
        # Count other calendars and dates in the grid
        othersCount = 0
        for group in others: othersCount += len(group)
        datesCount = len(grid)
        isRow = totalType == 'row'
        # Initialise, for every (row or col) totals, Total instances
        totalCount = isRow and datesCount or othersCount
        lastCount = isRow and othersCount or datesCount
        res = {}
        for totals in allTotals:
            res[totals.name] = [Total(totals.initValue) \
                                for i in range(totalCount)]
        # Get the status of validation checkboxes
        status = self.getValidationCheckboxesStatus(obj.request)
        # Walk every date within every calendar
        indexes = {'i': -1, 'j': -1}
        ii = isRow and 'i' or 'j'
        jj = isRow and 'j' or 'i'
        for other in sutils.IterSub(others):
            indexes['i'] += 1
            indexes['j'] = -1
            for date in grid:
                indexes['j'] += 1
                # Get the events in this other calendar at this date
                events = other.field.getEventsAt(other.obj, date)
                # From info @this date, update the total for every totals
                last = indexes[ii] == lastCount - 1
                # Get the status of the validation checkbox that is possibly
                # present at this date for this calendar
                checked = None
                cbId = '%s_%s_%s' % (other.obj.id, other.field.name,
                                     date.strftime('%Y%m%d'))
                if cbId in status: checked = status[cbId]
                # Update the Total instance for every totals at this date
                for totals in allTotals:
                    total = res[totals.name][indexes[jj]]
                    totals.onCell(obj, date, other, events, total, last,
                                  checked, preComputed)
        return res
# ------------------------------------------------------------------------------
