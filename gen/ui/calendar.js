function toggleVisibility(node, nodeType){
  // Toggle visibility of all elements having p_nodeType within p_node
  var elements = node.getElementsByTagName(nodeType);
  for (var i=0; i<elements.length; i++){
    var sNode = elements[i];
    if (sNode.style.visibility == 'hidden') sNode.style.visibility = 'visible';
    else sNode.style.visibility = 'hidden';
  }
}

function askCalendar(hookId, objectUrl, render, fieldName, month) {
  // Sends an Ajax request for getting the calendar, at p_month
  var params = {'month': month, 'render': render};
  askAjaxChunk(hookId, 'GET', objectUrl, fieldName+':pxView', params);
}

function enableOptions(select, enabled, selectFirst, message){
  /* This function disables, in p_select, all options that are not in p_enabled.
     p_enabled is a string containing a comma-separated list of option names.
     If p_selectFirst is True, the first option from p_enabled will be selected
     by default. p_message will be shown (as "title") for disabled options. */
  // Get p_enabled as a dict
  var l = enabled.split(',');
  var d = {};
  for (var i=0; i < l.length; i++) d[l[i]] = true;
  // Remember if we have already selected the first enabled option
  var isSelected = false;
  var options = select.options;
  // Disable options not being p_enabled
  for (var i=0; i<options.length; i++) {
    options[i].selected = false;
    if (!options[i].value) continue;
    if (options[i].value in d) {
      options[i].disabled = false;
      options[i].title = '';
      // Select it?
      if (selectFirst && !isSelected) {
        options[i].selected = true;
        isSelected = true;
      }
    }
    else {
      options[i].disabled = true;
      options[i].title = message;
    }
  }
}

function openEventPopup(action, fieldName, day, timeslot, spansDays,
                        applicableEventTypes, message, freeSlots) {
  /* Opens the popup for creating (or deleting, depending on p_action) a
     calendar event at some p_day. When action is "del", we need to know the
     p_timeslot where the event is assigned and if the event spans more days
     (from p_spansDays), in order to propose a checkbox allowing to delete
     events for those successive days. When action is "new", a possibly
     restricted list of applicable event types for this day is given in
     p_applicableEventTypes; p_message contains an optional message explaining
     why not applicable types are not applicable. When "new", p_freeSlots may
     list the available timeslots at p_day. */
  var prefix = fieldName + '_' + action + 'Event';
  var f = document.getElementById(prefix + 'Form');
  f.day.value = day;
  if (action == 'del') {
    if (f.timeslot) f.timeslot.value = timeslot;
    // Show or hide the checkbox for deleting the event for successive days
    var elem = document.getElementById(prefix + 'DelNextEvent');
    var cb = elem.getElementsByTagName('input');
    cb[0].checked = false;
    cb[1].value = 'False';
    if (spansDays == 'True') elem.style.display = 'block';
    else elem.style.display = 'none';
  }
  else if (action == 'new') {
    // Reinitialise field backgrounds
    f.eventType.style.background = '';
    if (f.eventSpan) f.eventSpan.style.background = '';
    // Disable unapplicable events and non-free timeslots
    enableOptions(f.eventType, applicableEventTypes, false, message);
    if (f.timeslot) enableOptions(f.timeslot, freeSlots, true, 'Not free');
  }
  openPopup(prefix + 'Popup');
}

function triggerCalendarEvent(action, hookId, fieldName, objectUrl,
                              maxEventLength) {
  /* Sends an Ajax request for triggering a calendar event (create or delete an
     event) and refreshing the view month. */
  var prefix = fieldName + '_' + action + 'Event';
  var f = document.getElementById(prefix + 'Form');
  if (action == 'new') {
    // Check that an event span has been specified
    if (f.eventType.selectedIndex == 0) {
      f.eventType.style.background = wrongTextInput;
      return;
    }
    if (f.eventSpan) {
      // Check that eventSpan is empty or contains a valid number
      var spanNumber = f.eventSpan.value.replace(' ', '');
      if (spanNumber) {
        spanNumber = parseInt(spanNumber);
        if (isNaN(spanNumber) || (spanNumber > maxEventLength)) {
          f.eventSpan.style.background = wrongTextInput;
          return;
        }
      }
    }
  }
  var elems = f.elements;
  var params = {};
  // Put form elements into "params"
  for (var i=0; i < elems.length; i++) {
    params[elems[i].name] = elems[i].value;
  }
  closePopup(prefix + 'Popup');
  askAjaxChunk(hookId, 'POST', objectUrl, fieldName+':pxView', params);
}
