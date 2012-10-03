function askMonthView(hookId, objectUrl, fieldName, month) {
  // Sends an Ajax request for getting the view month of a calendar field
  var params = {'fieldName': fieldName, 'month': month};
  askAjaxChunk(hookId,'GET',objectUrl,'widgets/calendar','viewMonth', params);
}

function openEventPopup(action, fieldName, day, spansDays) {
  /* Opens the popup for creating (or deleting, depending on p_action) a
     calendar event at some p_day. When action is "del", we need to know
     (from p_spansDays) if the event spans more days, in order to propose a
     checkbox allowing to delete events for those successive days. */
  var prefix = fieldName + '_' + action + 'Event';
  var f = document.getElementById(prefix + 'Form');
  f.day.value = day;
  if (action == 'del') {
    var elem = document.getElementById(prefix + 'DelNextEvent');
    var cb = elem.getElementsByTagName('input');
    cb[0].checked = false;
    cb[1].value = 'False';
    if (spansDays == 'True') { elem.style.display = 'block' }
    else { elem.style.display = 'none' }
  }
  openPopup(prefix + 'Popup');
}

function triggerCalendarEvent(action, hookId, fieldName, objectUrl) {
  /* Sends an Ajax request for triggering a calendar event (create or delete an
     event) and refreshing the view month. */
  var prefix = fieldName + '_' + action + 'Event';
  var f = document.getElementById(prefix + 'Form');
  if (action == 'new') {
    // Check that eventSpan is empty or contains a valid number
    var spanNumber = f.eventSpan.value.replace(' ', '');
    if (spanNumber) {
      if (isNaN(parseInt(spanNumber))) {
        f.eventSpan.style.background = wrongTextInput;
        return;
      }
    }
  }
  var elems = f.elements;
  var params = {};
  // Put form elements into "params".
  for (var i=0; i < elems.length; i++) {
    params[elems[i].name] = elems[i].value;
  }
  closePopup(prefix + 'Popup');
  askAjaxChunk(hookId,'POST',objectUrl,'widgets/calendar','viewMonth',params);
}
