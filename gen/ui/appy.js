var wrongTextInput = '#F9EDBE none';

// Functions related to user authentication
function cookiesAreEnabled() {
  // Test whether cookies are enabled by attempting to set a cookie and then
  // change its value
  var c = "areYourCookiesEnabled=0";
  document.cookie = c;
  var dc = document.cookie;
  // Cookie not set? Fail
  if (dc.indexOf(c) == -1) return 0;
  // Change test cookie
  c = "areYourCookiesEnabled=1";
  document.cookie = c;
  dc = document.cookie;
  // Cookie not changed?  fail
  if (dc.indexOf(c) == -1) return 0;
  // Delete cookie
  document.cookie = "areYourCookiesEnabled=; expires=Thu, 01-Jan-70 00:00:01 GMT";
  return 1;
}

function setLoginVars() {
  // Indicate if JS is enabled
  document.getElementById('js_enabled').value = 1;
  // Indicate if cookies are enabled
  document.getElementById('cookies_enabled').value = cookiesAreEnabled();
  // Copy login and password length to alternative vars since current vars will
  // be removed from the request by zope's authentication mechanism.
  document.getElementById('login_name').value = document.getElementById('__ac_name').value;
  password = document.getElementById('__ac_password');
  emptyPassword = document.getElementById('pwd_empty');
  if (password.value.length==0) emptyPassword.value = '1';
  else emptyPassword.value = '0';
}

function showLoginForm() {
  // Hide the login link.
  var loginLink = document.getElementById('loginLink');
  loginLink.style.display = "none";
  // Displays the login form.
  var loginFields = document.getElementById('loginFields');
  loginFields.style.display = "inline";
}

function goto(url) { window.location = url }
function len(dict) {
  var res = 0;
  for (var key in dict) res += 1;
  return res;
}

function switchLanguage(selectWidget, siteUrl) {
  var language = selectWidget.options[selectWidget.selectedIndex].value;
  goto(siteUrl + '/config/changeLanguage?language=' + language);
}

var isIe = (navigator.appName == "Microsoft Internet Explorer");

function getElementsHavingName(tag, name) {
  if (!isIe) return document.getElementsByName(name);
  var elems = document.getElementsByTagName(tag);
  var res = new Array();
  for (var i=0; i<elems.length; i++) {
    var nameAttr = elems[i].attributes['name'];
    if (nameAttr && (nameAttr.value == name)) res.push(elems[i]);
  }
  return res;
}

// AJAX machinery
var xhrObjects = new Array(); // An array of XMLHttpRequest objects
function XhrObject() { // Wraps a XmlHttpRequest object
  this.freed = 1; // Is this xhr object already dealing with a request or not?
  this.xhr = false;
  if (window.XMLHttpRequest) this.xhr = new XMLHttpRequest();
  else this.xhr = new ActiveXObject("Microsoft.XMLHTTP");
  this.hook = '';  /* The ID of the HTML element in the page that will be
                      replaced by result of executing the Ajax request. */
  this.onGet = ''; /* The name of a Javascript function to call once we
                      receive the result. */
  this.info = {};  /* An associative array for putting anything else. */
}

/* When inserting HTML at some DOM node in a page via Ajax, scripts defined in
   this chunk of HTML are not executed. This function, typically used as "onGet"
   param for the askAjaxChunk function below, will evaluate those scripts. */
function evalInnerScripts(xhrObject, hookElem) {
  var scripts = hookElem.getElementsByTagName('script');
  for (var i=0; i<scripts.length; i++) { eval(scripts[i].innerHTML) }
}

function injectChunk(elem, content){
  if (!isIe) elem.innerHTML = content;
  else {
    if (elem.tagName != 'TABLE') elem.innerHTML = content;
    else {
      /* IE doesn't want to replace content of a table. Force it to do so via
         a temporary DOM element. */
      var temp = document.createElement('div');
      temp.innerHTML = content;
      temp.firstChild.id = elem.id;
      elem.parentNode.replaceChild(temp.firstChild, elem);
    }
  }
}

function getAjaxChunk(pos) {
  // This function is the callback called by the AJAX machinery (see function
  // askAjaxChunk below) when an Ajax response is available.
  // First, find back the correct XMLHttpRequest object
  if ( (typeof(xhrObjects[pos]) != 'undefined') &&
       (xhrObjects[pos].freed == 0)) {
    var hook = xhrObjects[pos].hook;
    if (xhrObjects[pos].xhr.readyState == 1) {
      // The request has been initialized: display the waiting radar
      var hookElem = document.getElementById(hook);
      if (hookElem)
        injectChunk(hookElem, "<div align=\"center\"><img src=\"ui/waiting.gif\"/><\/div>");
    }
    if (xhrObjects[pos].xhr.readyState == 4) {
      // We have received the HTML chunk
      var hookElem = document.getElementById(hook);
      if (hookElem && (xhrObjects[pos].xhr.status == 200)) {
        injectChunk(hookElem, xhrObjects[pos].xhr.responseText);
        // Call a custom Javascript function if required
        if (xhrObjects[pos].onGet) {
          xhrObjects[pos].onGet(xhrObjects[pos], hookElem);
        }
        // Eval inner scripts if any.
        var innerScripts = getElementsHavingName('div', 'appyHook');
        for (var i=0; i<innerScripts.length; i++) {
          eval(innerScripts[i].innerHTML);
        }
        xhrObjects[pos].freed = 1;
      }
    }
  }
}

function askAjaxChunk(hook,mode,url,px,params,beforeSend,onGet) {
  /* This function will ask to get a chunk of XHTML on the server through a
     XMLHttpRequest. p_mode can be 'GET' or 'POST'. p_url is the URL of a
     given server object. On this object we will call method "ajax" that will
     call a specific p_px with some additional p_params (must be an associative
     array) if required. If p_px is of the form <field name>:<px name>, the PX
     will be found on the field named <field name> instead of being found
     directly on the object at p_url.

     p_hook is the ID of the XHTML element that will be filled with the XHTML
     result from the server.

     p_beforeSend is a Javascript function to call before sending the request.
     This function will get 2 args: the XMLHttpRequest object and the p_params.
     This method can return, in a string, additional parameters to send, ie:
     "&param1=blabla&param2=blabla".

     p_onGet is a Javascript function to call when we will receive the answer.
     This function will get 2 args, too: the XMLHttpRequest object and the
     HTML node element into which the result has been inserted.
  */
  // First, get a non-busy XMLHttpRequest object.
  var pos = -1;
  for (var i=0; i < xhrObjects.length; i++) {
    if (xhrObjects[i].freed == 1) { pos = i; break; }
  }
  if (pos == -1) {
    pos = xhrObjects.length;
    xhrObjects[pos] = new XhrObject();
  }
  xhrObjects[pos].hook = hook;
  xhrObjects[pos].onGet = onGet;
  if (xhrObjects[pos].xhr) {
    var rq = xhrObjects[pos];
    rq.freed = 0;
    // Construct parameters
    var paramsFull = 'px=' + px;
    if (params) {
      for (var paramName in params)
        paramsFull = paramsFull + '&' + paramName + '=' + params[paramName];
    }
    // Call beforeSend if required
    if (beforeSend) {
       var res = beforeSend(rq, params);
       if (res) paramsFull = paramsFull + res;
    }
    // Construct the URL to call
    var urlFull = url + '/ajax';
    if (mode == 'GET') {
      urlFull = urlFull + '?' + paramsFull;
    }
    // Perform the asynchronous HTTP GET or POST
    rq.xhr.open(mode, urlFull, true);
    if (mode == 'POST') {
      // Set the correct HTTP headers
      rq.xhr.setRequestHeader(
        "Content-Type", "application/x-www-form-urlencoded");
      rq.xhr.setRequestHeader("Content-length", paramsFull.length);
      rq.xhr.setRequestHeader("Connection", "close");
      rq.xhr.onreadystatechange = function(){ getAjaxChunk(pos); }
      rq.xhr.send(paramsFull);
    }
    else if (mode == 'GET') {
      rq.xhr.onreadystatechange = function() { getAjaxChunk(pos); }
      if (window.XMLHttpRequest) { rq.xhr.send(null); }
      else if (window.ActiveXObject) { rq.xhr.send(); }
    }
  }
}

/* The functions below wrap askAjaxChunk for getting specific content through
   an Ajax request. */
function askQueryResult(hookId, objectUrl, className, searchName, popup,
                        startNumber, sortKey, sortOrder, filterKey) {
  // Sends an Ajax request for getting the result of a query.
  var params = {'className': className, 'search': searchName,
                'startNumber': startNumber, 'popup': popup};
  if (sortKey) params['sortKey'] = sortKey;
  if (sortOrder) params['sortOrder'] = sortOrder;
  if (filterKey) {
    var filterWidget = document.getElementById(hookId + '_' + filterKey);
    if (filterWidget && filterWidget.value) {
      params['filterKey'] = filterKey;
      params['filterValue'] = filterWidget.value;
    }
  }
  askAjaxChunk(hookId, 'GET', objectUrl, 'pxQueryResult', params, null,
               evalInnerScripts);
}

function askObjectHistory(hookId, objectUrl, maxPerPage, startNumber) {
  // Sends an Ajax request for getting the history of an object
  var params = {'maxPerPage': maxPerPage, 'startNumber': startNumber};
  askAjaxChunk(hookId, 'GET', objectUrl, 'pxHistory', params);
}

function askRefField(hookId, objectUrl, fieldName, innerRef, startNumber,
                     action, actionParams){
  // Sends an Ajax request for getting the content of a reference field.
  var startKey = hookId + '_startNumber';
  var scope = hookId.split('_').pop();
  var params = {'innerRef': innerRef, 'scope': scope};
  params[startKey] = startNumber;
  if (action) params['action'] = action;
  if (actionParams) {
    for (key in actionParams) {
      if ((key == 'move') && (typeof actionParams[key] == 'object')) {
        // Get the new index from an input field
        var id = actionParams[key].id;
        id = id.substr(0, id.length-4);
        var input = document.getElementById(id);
        if (isNaN(input.value)) {
          input.style.background = wrongTextInput;
          return;
        }
        params[key] = 'index_' + input.value;
      }
      else params[key] = actionParams[key];
    };
  }
  var px = (scope == 'objs')? ':pxView': ':pxViewPickList';
  askAjaxChunk(hookId, 'GET', objectUrl, fieldName + px, params, null,
               evalInnerScripts);
}

function askField(hookId, objectUrl, layoutType, showChanges, masterValues,
                  requestValue, error, className){
  // Sends an Ajax request for getting the content of any field.
  var fieldName = hookId.split('_')[1];
  var params = {'layoutType': layoutType, 'showChanges': showChanges};
  if (masterValues) params['masterValues'] = masterValues.join('*');
  if (requestValue) params[fieldName] = requestValue;
  if (error) params[fieldName + '_error'] = error;
  var px = fieldName + ':pxRender';
  if (className) px = className + ':' + px;
  askAjaxChunk(hookId, 'GET', objectUrl, px, params, null, evalInnerScripts);
}

function doInlineSave(objectUid, name, objectUrl, content){
  /* Ajax-saves p_content of field named p_name on object whose id is
     p_objectUid and whose URL is p_objectUrl. Asks a confirmation before
     doing it. */
  var doIt = confirm(save_confirm);
  var params = {'action': 'storeFromAjax', 'layoutType': 'view'};
  var hook = null;
  if (!doIt) {
    params['cancel'] = 'True';
    hook = objectUid + '_' + name;
  }
  else { params['fieldContent'] = encodeURIComponent(content) }
  askAjaxChunk(hook, 'POST', objectUrl, name + ':pxRender', params, null,
               evalInnerScripts);
}

// Used by checkbox widgets for having radio-button-like behaviour.
function toggleCheckbox(visibleCheckbox, hiddenBoolean) {
  vis = document.getElementById(visibleCheckbox);
  hidden = document.getElementById(hiddenBoolean);
  if (vis.checked) hidden.value = 'True';
  else hidden.value = 'False';
}

// JS implementation of Python ''.rsplit.
function _rsplit(s, delimiter, limit) {
  var elems = s.split(delimiter);
  var exc = elems.length - limit;
  if (exc <= 0) return elems;
  // Merge back first elements to get p_limit elements.
  var head = '';
  var res = [];
  for (var i=0; i < elems.length; i++) {
    if (exc > 0) { head += elems[i] + delimiter; exc -= 1 }
    else { if (exc == 0) { res.push(head + elems[i]); exc -= 1 }
           else res.push(elems[i]) }
  }
  return res;
}

// (Un)checks a checkbox corresponding to a linked object.
function toggleCb(checkbox) {
  var name = checkbox.getAttribute('name');
  var elems = _rsplit(name, '_', 3);
  // Get the DOM node corresponding to the Ref field.
  var node = document.getElementById(elems[0] + '_' + elems[1]);
  // Get the array that stores checkbox statuses.
  var statuses = node['_appy_' + elems[2] + '_cbs'];
  // Get the array semantics
  var semantics = node['_appy_' + elems[2] + '_sem'];
  var uid = checkbox.value;
  if (semantics == 'unchecked') {
    if (!checkbox.checked) statuses[uid] = null;
    else {if (uid in statuses) delete statuses[uid]};
  }
  else { // semantics is 'checked'
    if (checkbox.checked) statuses[uid] = null;
    else {if (uid in statuses) delete statuses[uid]};
  }
}

// Initialise checkboxes of a Ref field or Search.
function initCbs(id) {
  var elems = _rsplit(id, '_', 3);
  // Get the DOM node corresponding to the Ref field.
  var node = document.getElementById(elems[0] + '_' + elems[1]);
  // Get the array that stores checkbox statuses.
  var statuses = node['_appy_' + elems[2] + '_cbs'];
  // Get the array semantics
  var semantics = node['_appy_' + elems[2] + '_sem'];
  var value = (semantics == 'unchecked')? false: true;
  // Update visible checkboxes.
  var checkboxes = getElementsHavingName('input', id);
  for (var i=0; i < checkboxes.length; i++) {
    if (checkboxes[i].value in statuses) checkboxes[i].checked = value;
    else checkboxes[i].checked = !value;
  }
}

// Toggle all checkboxes of a Ref field or Search.
function toggleAllCbs(id) {
  var elems = _rsplit(id, '_', 3);
  // Get the DOM node corresponding to the Ref field.
  var node = document.getElementById(elems[0] + '_' + elems[1]);
  // Empty the array that stores checkbox statuses.
  var statuses = node['_appy_' + elems[2] + '_cbs'];
  for (var key in statuses) delete statuses[key];
  // Switch the array semantics.
  var semAttr = '_appy_' + elems[2] + '_sem';
  if (node[semAttr] == 'unchecked') node[semAttr] = 'checked';
  else node[semAttr] = 'unchecked';
  // Update the visible checkboxes
  initCbs(id);
}

// Shows/hides a dropdown menu
function toggleDropdown(dropdownId, forcedValue){
  var dropdown = document.getElementById(dropdownId);
  // Force to p_forcedValue if specified
  if (forcedValue) {dropdown.style.display = forcedValue}
  else {
    var displayValue = dropdown.style.display;
    if (displayValue == 'block') dropdown.style.display = 'none';
    else dropdown.style.display = 'block';
  }
}

// Function that sets a value for showing/hiding sub-titles.
function setSubTitles(value, tag) {
  createCookie('showSubTitles', value);
  // Get the sub-titles
  var subTitles = getElementsHavingName(tag, 'subTitle');
  if (subTitles.length == 0) return;
  // Define the display style depending on p_tag.
  var displayStyle = 'inline';
  if (tag == 'tr') displayStyle = 'table-row';
  for (var i=0; i < subTitles.length; i++) {
    if (value == 'true') subTitles[i].style.display = displayStyle;
    else subTitles[i].style.display = 'none';
  }
}

// Function that toggles the value for showing/hiding sub-titles.
function toggleSubTitles(tag) {
  // Get the current value
  var value = readCookie('showSubTitles');
  if (value == null) value = 'true';
  // Toggle the value
  var newValue = 'true';
  if (value == 'true') newValue = 'false';
  if (!tag) tag = 'div';
  setSubTitles(newValue, tag);
}

// Functions used for master/slave relationships between widgets
function getSlaveInfo(slave, infoType) {
  // Returns the appropriate info about slavery, depending on p_infoType.
  var cssClasses = slave.className.split(' ');
  var masterInfo = null;
  // Find the CSS class containing master-related info.
  for (var j=0; j < cssClasses.length; j++) {
    if (cssClasses[j].indexOf('slave*') == 0) {
      // Extract, from this CSS class, master name or master values.
      masterInfo = cssClasses[j].split('*');
      if (infoType == 'masterName') return masterInfo[1];
      else return masterInfo.slice(2); 
    }
  }
}

function getMasterValues(master) {
  // Returns the list of values that p_master currently has.
  var res = null;
  if ((master.tagName == 'INPUT') && (master.type != 'checkbox')) {
    res = master.value;
    if ((res.charAt(0) == '(') || (res.charAt(0) == '[')) {
      // There are multiple values, split it
      values = res.substring(1, res.length-1).split(',');
      res = [];
      var v = null;
      for (var i=0; i < values.length; i++){
        v = values[i].replace(' ', '');
        res.push(v.substring(1, v.length-1));
      }
    }
    else res = [res]; // A single value
  }
  else if (master.type == 'checkbox') {
    res = master.checked + '';
    res = res.charAt(0).toUpperCase() + res.substr(1);
    res = [res];
  }
  else { // SELECT widget
    res = [];
    for (var i=0; i < master.options.length; i++) {
      if (master.options[i].selected) res.push(master.options[i].value);
    }
  }
  return res;
}

function getSlaves(master) {
  // Gets all the slaves of master.
  allSlaves = getElementsHavingName('table', 'slave');
  res = [];  
  masterName = master.attributes['name'].value;
  // Remove leading 'w_' if the master is in a search screen.
  if (masterName.indexOf('w_') == 0) masterName = masterName.slice(2);
  if (master.type == 'checkbox') {
    masterName = masterName.substr(0, masterName.length-8);
  }
  slavePrefix = 'slave*' + masterName + '*';
  for (var i=0; i < allSlaves.length; i++){
    cssClasses = allSlaves[i].className.split(' ');
    for (var j=0; j < cssClasses.length; j++) {
      if (cssClasses[j].indexOf(slavePrefix) == 0) {
        res.push(allSlaves[i]);
        break;
      }
    }
  }
  return res;
}

function updateSlaves(master, slave, objectUrl, layoutType, requestValues,
                      errors, className){
  /* Given the value(s) in a master field, we must update slave's visibility or
     value(s). If p_slave is given, it updates only this slave. Else, it updates
     all slaves of p_master. */
  var slaves = null;
  if (slave) { slaves = [slave]; }
  else { slaves = getSlaves(master); }
  masterValues = getMasterValues(master);
  for (var i=0; i < slaves.length; i++) {
    slaveryValues = getSlaveInfo(slaves[i], 'masterValues');
    if (slaveryValues[0] != '+') {
      // Update slaves visibility depending on master values.
      var showSlave = false;
      for (var j=0; j < slaveryValues.length; j++) {
        for (var k=0; k< masterValues.length; k++) {
          if (slaveryValues[j] == masterValues[k]) showSlave = true;
        }
      } 
      if (showSlave) slaves[i].style.display = '';
      else slaves[i].style.display = 'none';
    }
    else {
      // Update slaves' values depending on master values.
      var slaveId = slaves[i].id;
      var slaveName = slaveId.split('_')[1];
      var reqValue = null;
      if (requestValues && (slaveName in requestValues))
        reqValue = requestValues[slaveName];
      var err = null;
      if (errors && (slaveName in errors))
        err = errors[slaveName];
      askField(slaveId, objectUrl, layoutType, false, masterValues, reqValue,
               err, className);
    }
  }
}

function initSlaves(objectUrl, layoutType, requestValues, errors) {
  /* When the current page is loaded, we must set the correct state for all
     slave fields. For those that are updated via Ajax requests, their
     p_requestValues and validation p_errors must be carried to those
     requests. */
  slaves = getElementsHavingName('table', 'slave');
  i = slaves.length -1;
  while (i >= 0) {
    masterName = getSlaveInfo(slaves[i], 'masterName');
    master = document.getElementById(masterName);
    // If master is not here, we can't hide its slaves when appropriate.
    if (master) {
      updateSlaves(master,slaves[i],objectUrl,layoutType,requestValues,errors);}
    i -= 1;
  }
}

// Function used to submit the appy form on pxEdit
function submitAppyForm(button) {
  var theForm = document.getElementById('appyForm');
  // On which button has the user clicked?
  theForm.button.value = button;
  theForm.submit();
}

// Function used for triggering a workflow transition
function triggerTransition(formId, transitionId, msg) {
  var theForm = document.getElementById(formId);
  theForm.transition.value = transitionId;
  if (!msg) { theForm.submit(); }
  else { // Ask the user to confirm.
   askConfirm('form', formId, msg, true);
  }
}

function onDeleteObject(objectUid) {
  f = document.getElementById('deleteForm');
  f.objectUid.value = objectUid;
  askConfirm('form', 'deleteForm', action_confirm);
}

function onDeleteEvent(objectUid, eventTime) {
  f = document.getElementById('deleteEventForm');
  f.objectUid.value = objectUid;
  f.eventTime.value = eventTime;
  askConfirm('form', 'deleteEventForm', action_confirm);
}

function onLink(action, sourceUid, fieldName, targetUid) {
  f = document.getElementById('linkForm');
  f.linkAction.value = action;
  f.sourceUid.value = sourceUid;
  f.fieldName.value = fieldName;
  f.targetUid.value = targetUid;
  f.submit();
}

function onLinkMany(action, id) {
  var elems = _rsplit(id, '_', 3);
  // Get the DOM node corresponding to the Ref field.
  var node = document.getElementById(elems[0] + '_' + elems[1]);
  // Get the uids of (un-)checked objects.
  var statuses = node['_appy_' + elems[2] + '_cbs'];
  var uids = '';
  for (var uid in statuses) uids += uid + ',';
  // Get the array semantics
  var semantics = node['_appy_' + elems[2] + '_sem'];
  // Show an error messagge if non element is selected.
  if ((semantics == 'checked') && (len(statuses) == 0)) {
    openPopup('alertPopup', no_elem_selected);
    return;
  }
  // Fill the form and ask for a confirmation
  f = document.getElementById('linkForm');
  f.linkAction.value = action + '_many';
  f.sourceUid.value = elems[0];
  f.fieldName.value = elems[1];
  f.targetUid.value = uids;
  f.semantics.value = semantics;
  askConfirm('form', 'linkForm', action_confirm);
}

function onUnlockPage(objectUid, pageName) {
  f = document.getElementById('unlockForm');
  f.objectUid.value = objectUid;
  f.pageName.value = pageName;
  askConfirm('form', 'unlockForm', action_confirm);
}

function createCookie(name, value, days) {
  if (days) {
    var date = new Date();
    date.setTime(date.getTime()+(days*24*60*60*1000));
    var expires = "; expires="+date.toGMTString();
  } else expires = "";
  document.cookie = name+"="+escape(value)+expires+"; path=/;";
}

function readCookie(name) {
  var nameEQ = name + "=";
  var ca = document.cookie.split(';');
  for (var i=0; i < ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0)==' ') { c = c.substring(1,c.length); }
    if (c.indexOf(nameEQ) == 0) {
      return unescape(c.substring(nameEQ.length,c.length));
    }
  }
  return null;
}

function toggleCookie(cookieId) {
  // What is the state of this boolean (expanded/collapsed) cookie?
  var state = readCookie(cookieId);
  if ((state != 'collapsed') && (state != 'expanded')) {
    // No cookie yet, create it.
    createCookie(cookieId, 'collapsed');
    state = 'collapsed';
  }
  var hook = document.getElementById(cookieId); // The hook is the part of
  // the HTML document that needs to be shown or hidden.
  var displayValue = 'none';
  var newState = 'collapsed';
  var imgSrc = 'ui/expand.gif';
  if (state == 'collapsed') {
    // Show the HTML zone
    displayValue = 'block';
    imgSrc = 'ui/collapse.gif';
    newState = 'expanded';
  }
  // Update the corresponding HTML element
  hook.style.display = displayValue;
  var img = document.getElementById(cookieId + '_img');
  img.src = imgSrc;
  // Inverse the cookie value
  createCookie(cookieId, newState);
}

// Function that allows to generate a document from a pod template.
function generatePod(uid, fieldName, template, podFormat, queryData,
                     customParams, getChecked) {
  var f = document.getElementById('podForm');
  f.objectUid.value = uid;
  f.fieldName.value = fieldName;
  f.template.value = template;
  f.podFormat.value = podFormat;
  f.queryData.value = queryData;
  if (customParams) { f.customParams.value = customParams; }
  else { f.customParams.value = ''; }
  f.action.value = 'generate';
  f.checkedUids.value = '';
  f.checkedSem.value = '';
  if (getChecked) {
    // We must collect selected objects from a Ref field.
    var node = document.getElementById(uid + '_' + getChecked);
    if (node && node.hasOwnProperty('_appy_objs_cbs')) {
      var uids = [];
      for (var uid in node['_appy_objs_cbs']) uids.push(uid);
      f.checkedUids.value = uids.join();
      f.checkedSem.value = node['_appy_objs_sem'];
    }
  }
  f.submit();
}

// Function that allows to (un-)freeze a document from a pod template.
function freezePod(uid, fieldName, template, podFormat, action) {
  var f = document.getElementById('podForm');
  f.objectUid.value = uid;
  f.fieldName.value = fieldName;
  f.template.value = template;
  f.podFormat.value = podFormat;
  f.action.value = action;
  askConfirm('form', 'podForm', action_confirm);
}

// Function that allows to upload a file for freezing it in a pod field.
function uploadPod(uid, fieldName, template, podFormat) {
  var f = document.getElementById('uploadForm');
  f.objectUid.value = uid;
  f.fieldName.value = fieldName;
  f.template.value = template;
  f.podFormat.value = podFormat;
  f.uploadedFile.value = null;
  openPopup('uploadPopup');
}

function protectAppyForm() {
  window.onbeforeunload = function(e){
    theForm = document.getElementById("appyForm");
    if (theForm.button.value == "") {
      var e = e || window.event;
      if (e) {e.returnValue = warn_leave_form;}
      return warn_leave_form;
    }
  }
}

// Functions for opening and closing a popup
function openPopup(popupId, msg, width, height) {
  // Put the message into the popup
  if (msg) {
    var msgHook = (popupId == 'alertPopup')? 'appyAlertText': 'appyConfirmText';
    var confirmElem = document.getElementById(msgHook);
    confirmElem.innerHTML = msg;
  }
  // Open the popup
  var popup = document.getElementById(popupId);
  // Put it at the right place on the screen and give it the right dimensions
  var scrollTop = document.documentElement.scrollTop || window.pageYOffset || 0;
  popup.style.top = (scrollTop + 150) + 'px';
  if (width) popup.style.width = width + 'px';
  if (height) popup.style.height = height + 'px';
  if (popupId == 'iframePopup') {
    // Initialize iframe's width.
    var iframe = document.getElementById('appyIFrame');
    if (!width) width = window.innerWidth - 200;
    if (!height) {
      height = window.innerHeight - 200;
      popup.style.top = ((window.innerHeight - height) / 2).toFixed() + 'px';
    }
    popup.style.left = ((window.innerWidth - width) / 2).toFixed() + 'px';
    popup.style.width = width + 'px';
    iframe.style.width = (width-20) + 'px';
    popup.style.height = height + 'px';
    iframe.style.height = (height-20) + 'px';
  }
  popup.style.display = 'block';
}

function closePopup(popupId) {
  // Close the popup
  var container = window.parent.document;
  var popup = container.getElementById(popupId);
  popup.style.display = 'none';
  popup.style.width = null;
  if (popupId == 'iframePopup') {
    // Reinitialise the enclosing iframe.
    var iframe = container.getElementById('appyIFrame');
    iframe.style.width = null;
    iframe.innerHTML = '';
    // Leave the form silently if we are on an edit page
    iframe.contentWindow.onbeforeunload = null;
  }
}

function backFromPopup() {
  closePopup('iframePopup');
  window.parent.location = window.parent.location;
}

// Function triggered when an action needs to be confirmed by the user
function askConfirm(actionType, action, msg, showComment) {
  /* Store the actionType (send a form, call an URL or call a script) and the
     related action, and shows the confirm popup. If the user confirms, we
     will perform the action. If p_showComment is true, an input field allowing
     to enter a comment will be shown in the popup. */
  var confirmForm = document.getElementById('confirmActionForm');
  confirmForm.actionType.value = actionType;
  confirmForm.action.value = action;
  var commentArea = document.getElementById('commentArea');
  if (showComment) commentArea.style.display = 'block';
  else commentArea.style.display = 'none';
  openPopup("confirmActionPopup", msg);
}

// Function triggered when an action confirmed by the user must be performed
function doConfirm() {
  // The user confirmed: perform the required action.
  closePopup('confirmActionPopup');
  var confirmForm = document.getElementById('confirmActionForm');
  var actionType = confirmForm.actionType.value;
  var action = confirmForm.action.value;
  if (actionType == 'form') {
    /* Submit the form whose id is in "action", and transmmit him the comment
       from the popup when relevant */
    var theForm = document.getElementById(action);
    if ((confirmForm.comment.style.display != 'none') &&
        (confirmForm.comment.value)) {
      theForm.comment.value = confirmForm.comment.value;
    }
    theForm.submit();
  }
  // We must go to the URL defined in "action"
  else if (actionType == 'url') { goto(action) }
  else if (actionType == 'script') {
    // We must execute Javascript code in "action"
    eval(action);
  }
  else if (actionType == 'form+script') {
    var elems = action.split('+');
    // Submit the form in elems[0] and execute the JS code in elems[1]
    document.getElementById(elems[0]).submit();
    eval(elems[1]);
  }
}

// Function triggered when the user asks password reinitialisation
function doAskPasswordReinit() {
  // Check that the user has typed a login
  var theForm = document.getElementById('askPasswordReinitForm');
  var login = theForm.login.value.replace(' ', '');
  if (!login) { theForm.login.style.background = wrongTextInput; }
  else {
    closePopup('askPasswordReinitPopup');
    theForm.submit();
  }
}

// Function that finally posts the edit form after the user has confirmed that
// she really wants to post it.
function postConfirmedEditForm() {
  var theForm = document.getElementById('appyForm');
  theForm.confirmed.value = "True";
  theForm.button.value = 'save';
  theForm.submit();
}

// Function that shows or hides a tab. p_action is 'show' or 'hide'.
function manageTab(tabId, action) {
  // Manage the tab content (show it or hide it)
  var content = document.getElementById('tabcontent_' + tabId);
  if (action == 'show')   { content.style.display = 'table-row'; }
  else                    { content.style.display = 'none'; }
  // Manage the tab itself (show as selected or unselected)
  var left = document.getElementById('tab_' + tabId + '_left');
  var tab = document.getElementById('tab_' + tabId);
  var right = document.getElementById('tab_' + tabId + '_right');
  if (action == 'show') {
      left.src  = "ui/tabLeft.png";
      tab.style.backgroundImage = "url(ui/tabBg.png)";
      right.src = "ui/tabRight.png";
  }
  if (action == 'hide') {
      left.src  = "ui/tabLeftu.png";
      tab.style.backgroundImage = "url(ui/tabBgu.png)";
      right.src = "ui/tabRightu.png";
  }
}

// Function used for displaying/hiding content of a tab
function showTab(tabId) {
  // 1st, show the tab to show
  manageTab(tabId, 'show');
  // Compute the number of tabs.
  var idParts = tabId.split('_');
  var prefix = idParts[0] + '_';
  // Store the currently selected tab in a cookie.
  createCookie('tab_' + idParts[0], tabId);
  var nbOfTabs = idParts[2]*1;
  // Then, hide the other tabs.
  for (var i=0; i<nbOfTabs; i++) {
     var idTab = prefix + (i+1) + '_' + nbOfTabs;
     if (idTab != tabId) {
       manageTab(idTab, 'hide');
     }
  }
}

// Function that initializes the state of a tab
function initTab(tabsId, defaultValue) {
  var selectedTabId = readCookie(tabsId);
  if (!selectedTabId) { showTab(defaultValue) }
  else {
    /* Ensure the selected tab exists (it could be absent because of field
       visibility settings) */
    var selectedTab = document.getElementById('tab_' + selectedTabId);
    if (selectedTab) { showTab(selectedTabId) }
    else { showTab(defaultValue) }
  }
}

// List-related Javascript functions
function updateRowNumber(row, rowIndex, action) {
  /* Within p_row, we update every field whose name and id include the row index
     with new p_rowIndex. If p_action is 'set', p_rowIndex becomes the new
     index. If p_action is 'add', new index becomes:
     existing index + p_rowIndex. */
  var tagTypes = ['input', 'select', 'img', 'textarea'];
  var currentIndex = -1;
  for (var i=0; i < tagTypes.length; i++) {
    var widgets = row.getElementsByTagName(tagTypes[i]);
    for (var j=0; j < widgets.length; j++) {
      var id = widgets[j].id;
      if (!id) continue;
      var name = widgets[j].name;
      // Extract the suffix if there is one (ie, if the field is a Date part:
      // _img, _day,...).
      var iSuffix = id.lastIndexOf('_');
      var idSuffix = '';
      if (iSuffix != -1) {
        idSuffix = id.substring(iSuffix);
        id = id.substring(0, iSuffix);
      }
      var nSuffix = name.lastIndexOf('_');
      var nameSuffix = '';
      if (nSuffix != -1) {
        nameSuffix = name.substring(nSuffix);
        name = name.substring(0, nSuffix);
      }
      // Compute the current row index if not already done.
      idNbIndex = id.lastIndexOf('*') + 1;
      nameNbIndex = name.lastIndexOf('*') + 1;
      if (currentIndex == -1) {
        currentIndex = parseInt(id.substring(idNbIndex));
      }
      // Compute the new values for attributes "id" and "name".
      newId = id.substring(0, idNbIndex);
      newName = name.substring(0, nameNbIndex);
      newIndex = rowIndex;
      if (action == 'add') newIndex = newIndex + currentIndex;
      var oldId = widgets[j].id;
      widgets[j].id = newId + String(newIndex) + idSuffix;
      if (name) widgets[j].name = newName + String(newIndex) + nameSuffix;
      /* In the case of an img that must show a calendar, update the script that
         is triggered when clicking on it. */
      if ((tagTypes[i] == 'img') && (idSuffix == '_img')) {
        var scripts = row.getElementsByTagName('script');
        for (var k=0; k < scripts.length; k++) {
          var text = scripts[k].text;
          if (text.indexOf(oldId) != -1) {
            var oldIdField = oldId.substring(0, oldId.length-4);
            var newIdField = widgets[j].id.substring(0, widgets[j].id.length-4);
            text = text.replace(oldIdField, newIdField);
            scripts[k].text = text.replace(oldId, widgets[j].id);
            eval(scripts[k].text);
            break;
          }
        }
      }
    }
  }
}
function insertRow(tableId) {
  // This function adds a new row in table with ID p_tableId.
  table = document.getElementById(tableId);
  newRow = table.rows[1].cloneNode(true);
  newRow.style.display = 'table-row';
  // Within newRow, incorporate the row number within field names and ids.
  table.tBodies[0].appendChild(newRow);
  updateRowNumber(newRow, table.rows.length-4, 'set');
}

function deleteRow(tableId, deleteImg) {
  row = deleteImg.parentNode.parentNode;
  table = document.getElementById(tableId);
  allRows = table.rows;
  toDeleteIndex = -1; // Will hold the index of the row to delete.
  for (var i=0; i < allRows.length; i++) {
    if (toDeleteIndex == -1) {
      if (row == allRows[i]) toDeleteIndex = i;
    }
    else {
      // Decrement higher row numbers by 1 because of the deletion
      updateRowNumber(allRows[i], -1, 'add');
    }
  }
  table.deleteRow(toDeleteIndex);
}

function onSelectDate(cal) {
  var p = cal.params;
  var update = (cal.dateClicked || p.electric);
  if (update && p.inputField) {
    var fieldName = cal.params.inputField.id;
    // Update day
    var dayValue = cal.date.getDate() + '';
    if (dayValue.length == 1) dayValue = '0' + dayValue;
    document.getElementById(fieldName + '_day').value = dayValue;
    // Update month
    var monthValue = (cal.date.getMonth() + 1) + '';
    if (monthValue.length == 1) monthValue = '0' + monthValue;
    document.getElementById(fieldName + '_month').value = monthValue;
    // Update year
    var year = document.getElementById(fieldName + '_year');
    if (!year) {
      // On the search screen, the 'from year' field has a special name.
      var yearId = 'w_' + fieldName.split('_')[0] + '*date';
      year = document.getElementById(yearId);
    }
    year.value = cal.date.getFullYear() + '';
  }
  if (update && p.singleClick && cal.dateClicked) {
    cal.callCloseHandler();
  }
}
