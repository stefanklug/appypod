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

// AJAX machinery
var isIe = (navigator.appName == "Microsoft Internet Explorer");
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
      if (hookElem) hookElem.innerHTML = "<div align=\"center\"><img src=\"skyn/waiting.gif\"/><\/div>";
    }
    if (xhrObjects[pos].xhr.readyState == 4) {
      // We have received the HTML chunk
      var hookElem = document.getElementById(hook);
      if (hookElem && (xhrObjects[pos].xhr.status == 200)) {
        hookElem.innerHTML = xhrObjects[pos].xhr.responseText;
        // Call a custom Javascript function if required
        if (xhrObjects[pos].onGet) {
          xhrObjects[pos].onGet(xhrObjects[pos], hookElem);
        }
        // Eval inner scripts if any.
        var innerScripts = document.getElementsByName("appyHook");
        for (var i=0; i<innerScripts.length; i++) {
          eval(innerScripts[i].innerHTML);
        }
        xhrObjects[pos].freed = 1;
      }
    }
  }
}

function askAjaxChunk(hook,mode,url,page,macro,params,beforeSend,onGet) {
  /* This function will ask to get a chunk of HTML on the server through a
     XMLHttpRequest. p_mode can be 'GET' or 'POST'. p_url is the URL of a
     given server object. On this URL we will call the page "ajax.pt" that
     will call a specific p_macro in a given p_page with some additional
     p_params (must be an associative array) if required.

     p_hook is the ID of the HTML element that will be filled with the HTML
     result from the server.

     p_beforeSend is a Javascript function to call before sending the request.
     This function will get 2 args: the XMLHttpRequest object and the
     p_params. This method can return, in a string, additional parameters to
     send, ie: "&param1=blabla&param2=blabla".

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
    var paramsFull = 'page=' + page + '&macro=' + macro;
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
    var urlFull = url + '/skyn/ajax';
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
function askQueryResult(hookId, objectUrl, contentType, searchName,
                        startNumber, sortKey, sortOrder, filterKey) {
  // Sends an Ajax request for getting the result of a query.
  var params = {'type_name': contentType, 'search': searchName,
                'startNumber': startNumber};
  if (sortKey) params['sortKey'] = sortKey;
  if (sortOrder) params['sortOrder'] = sortOrder;
  if (filterKey) {
    var filterWidget = document.getElementById(hookId + '_' + filterKey);
    if (filterWidget && filterWidget.value) {
      params['filterKey'] = filterKey;
      params['filterValue'] = filterWidget.value;
    }
  }
  askAjaxChunk(hookId,'GET',objectUrl, 'result', 'queryResult', params);
}

function askObjectHistory(hookId, objectUrl, maxPerPage, startNumber) {
  // Sends an Ajax request for getting the history of an object
  var params = {'maxPerPage': maxPerPage, 'startNumber': startNumber};
  askAjaxChunk(hookId, 'GET', objectUrl, 'page', 'objectHistory', params);
}

function askRefField(hookId, objectUrl, fieldName, innerRef, startNumber,
                     action, actionParams){
  // Sends an Ajax request for getting the content of a reference field.
  var startKey = hookId + '_startNumber';
  var params = {'fieldName': fieldName, 'innerRef': innerRef, };
  params[startKey] =  startNumber;
  if (action) params['action'] = action;
  if (actionParams) {
    for (key in actionParams) { params[key] = actionParams[key]; };
  }
  askAjaxChunk(hookId, 'GET', objectUrl, 'widgets/ref', 'viewContent',params);
}

function askComputedField(hookId, objectUrl, fieldName) {
  // Sends an Ajax request for getting the content of a computed field
  var params = {'fieldName': fieldName};
  askAjaxChunk(hookId, 'GET', objectUrl, 'widgets/computed', 'viewContent', params);
}

// Function used by checkbox widgets for having radio-button-like behaviour
function toggleCheckbox(visibleCheckbox, hiddenBoolean) {
  vis = document.getElementById(visibleCheckbox);
  hidden = document.getElementById(hiddenBoolean);
  if (vis.checked) hidden.value = 'True';
  else hidden.value = 'False';
}

// Functions used for master/slave relationships between widgets
function getMasterValue(widget) {
  // Returns an array of selected options in a select widget
  res = new Array();
  if (widget.type == 'checkbox') {
    var mv = widget.checked + '';
    mv = mv.charAt(0).toUpperCase() + mv.substr(1);
    res.push(mv);
  }
  else { // SELECT widget
    for (var i=0; i < widget.options.length; i++) {
      if (widget.options[i].selected) res.push(widget.options[i].value);
    }
  }
  return res;
}

function updateSlaves(masterValues, appyTypeId) {
  // Given the value(s) selected in a master field, this function updates the
  // state of all corresponding slaves.
  var slaves = cssQuery('table.slave_' + appyTypeId);
  for (var i=0; i< slaves.length; i++){
    slaves[i].style.display = "none";
  }
  for (var i=0; i < masterValues.length; i++) {
    var activeSlaves = cssQuery('table.slaveValue_' + appyTypeId + '_' + masterValues[i]);
    for (var j=0; j < activeSlaves.length; j++){
      activeSlaves[j].style.display = "";
    }
  }
}

function initSlaves() {
  // When the current page is loaded, we must set the correct state for all
  // slave fields.
  var masters = cssQuery('.appyMaster');
  for (var i=0; i < masters.length; i++) {
    var cssClasses = masters[i].className.split(' ');
    for (var j=0; j < cssClasses.length; j++) {
      if (cssClasses[j].indexOf('master_') == 0) {
        var appyId = cssClasses[j].split('_')[1];
        var masterValue = [];
        if (masters[i].nodeName == 'SPAN'){
          var idField = masters[i].id;
          if (idField == '') {
            masterValue.push(idField);
          }
          else {
            if ((idField[0] == '(') || (idField[0] == '[')) {
              // There are multiple values, split it
              var subValues = idField.substring(1, idField.length-1).split(',');
              for (var k=0; k < subValues.length; k++){
                var subValue = subValues[k].replace(' ','');
                masterValue.push(subValue.substring(1, subValue.length-1));
              }
            }
            else { masterValue.push(masters[i].id);
            }
          }
        }
        else { masterValue = getMasterValue(masters[i]);
        }
        updateSlaves(masterValue, appyId);
      }
    }
  }
}

// Function used for triggering a workflow transition
function triggerTransition(transitionId, msg) {
  var theForm = document.getElementById('triggerTransitionForm');
  theForm.workflow_action.value = transitionId;
  if (!msg) {
    theForm.submit();
  }
  else { // Ask the user to confirm.
   askConfirm('form', 'triggerTransitionForm', msg);
  }
}

function onDeleteObject(objectUid) {
  f = document.getElementById('deleteForm');
  f.objectUid.value = objectUid;
  askConfirm('form', 'deleteForm', delete_confirm);
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
  var imgSrc = 'skyn/expand.gif';
  if (state == 'collapsed') {
    // Show the HTML zone
    displayValue = 'block';
    imgSrc = 'skyn/collapse.gif';
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
function generatePodDocument(contextUid, fieldName, podFormat, queryData) {
  var theForm = document.getElementsByName("podTemplateForm")[0];
  theForm.objectUid.value = contextUid;
  theForm.fieldName.value = fieldName;
  theForm.podFormat.value = podFormat;
  theForm.askAction.value = "False";
  theForm.queryData.value = queryData;
  var askActionWidget = document.getElementById(contextUid + '_' + fieldName);
  if (askActionWidget && askActionWidget.checked) {
      theForm.askAction.value = "True";
  }
  theForm.submit();
}
// Functions for opening and closing a popup
function openPopup(popupId, msg) {
  // Put the message into the popup
  var confirmElem = document.getElementById('appyConfirmText');
  confirmElem.innerHTML = msg;
  // Open the popup
  var popup = document.getElementById(popupId);
  // Put it at the right place on the screen
  var scrollTop = window.pageYOffset || document.documentElement.scrollTop || 0;
  popup.style.top = (scrollTop + 150) + 'px';
  popup.style.display = "block";
  // Show the greyed zone
  var greyed = document.getElementById('grey');
  greyed.style.top = scrollTop + 'px';
  greyed.style.display = "block";
}

function closePopup(popupId) {
  // Close the popup
  var popup = document.getElementById(popupId);
  popup.style.display = "none";
  // Hide the greyed zone
  var greyed = document.getElementById('grey');
  greyed.style.display = "none";
}

// Function triggered when an action needs to be confirmed by the user
function askConfirm(actionType, action, msg) {
  /* Store the actionType (send a form, call an URL or call a script) and the
     related action, and shows the confirm popup. If the user confirms, we
     will perform the action. */
  var confirmForm = document.getElementById('confirmActionForm');
  confirmForm.actionType.value = actionType;
  confirmForm.action.value = action;
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
    // We must submit the form whose id is in "action"
    document.getElementById(action).submit();
  }
  else if (actionType == 'url') {
    // We must go to the URL defined in "action"
    window.location = action;
  }
  else if (actionType == 'script') {
    // We must execute Javascript code in "action"
    eval(action);
  }
}

// Function that finally posts the edit form after the user has confirmed that
// she really wants to post it.
function postConfirmedEditForm() {
  var theForm = document.getElementById('appyEditForm');
  theForm.confirmed.value = "True";
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
      left.src  = "skyn/tabLeft.png";
      tab.style.backgroundImage = "url(skyn/tabBg.png)";
      right.src = "skyn/tabRight.png";
  }
  if (action == 'hide') {
      left.src  = "skyn/tabLeftu.png";
      tab.style.backgroundImage = "url(skyn/tabBgu.png)";
      right.src = "skyn/tabRightu.png";
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
function initTab(cookieId, defaultValue) {
  var toSelect = readCookie(cookieId);
  if (!toSelect) { showTab(defaultValue) }
  else { showTab(toSelect); }
}