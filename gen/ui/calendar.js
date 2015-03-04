function toggleVisibility(node, nodeType){
  // Toggle visibility of all elements having p_nodeType within p_node
  var elements = node.getElementsByTagName(nodeType);
  for (var i=0; i<elements.length; i++){
    var sNode = elements[i];
    if (sNode.style.visibility == 'hidden') sNode.style.visibility = 'visible';
    else sNode.style.visibility = 'hidden';
  }
}

// Sends an Ajax request for getting the calendar, at p_month
function askMonth(hookId, month) {askAjax(hookId, null, {'month': month})}

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

function openEventPopup(hookId, action, day, timeslot, spansDays,
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
  var popupId = hookId + '_' + action;
  var f = document.getElementById(popupId + 'Form');
  f.day.value = day;
  if (action == 'del') {
    if (f.timeslot) f.timeslot.value = timeslot;
    // Show or hide the checkbox for deleting the event for successive days
    var elem = document.getElementById(hookId + '_DelNextEvent');
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
  openPopup(popupId);
}

function triggerCalendarEvent(hookId, action, maxEventLength) {
  /* Sends an Ajax request for triggering a calendar event (create or delete an
     event) and refreshing the view month. */
  var popupId = hookId + '_' + action;
  var formId = popupId + 'Form';
  var f = document.getElementById(formId);
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
  closePopup(popupId);
  askAjax(hookId, formId);
}

// Function for validating and discarding calendar events
function validateEvents(hookId) {
  // Collect checkboxes from hookId and identify checked and unchecked ones
  var validated = [];
  var discarded = [];
  var node = document.getElementById(hookId + '_cal');
  var cbs = node.getElementsByTagName('input');
  for (var i=0; i<cbs.length; i++) {
    if (cbs[i].type != 'checkbox') continue;
    if (cbs[i].checked) validated.push(cbs[i].id);
    else discarded.push(cbs[i].id);
  }
  validated = validated.join()
  discarded = discarded.join()
  var params = {'action': 'validateEvents', 'validated': validated,
                'discarded': discarded, 'mode': 'POST'};
  askAjax(hookId, null, params);
}
