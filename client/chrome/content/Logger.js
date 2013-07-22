
/**
  * This global object is used for logging all the stuff.
  **/

var CV9BLog = { // my attempt to produce short yet fairly unique id

  // Set boolean value "convergence.logging.enabled"
  //  to "true" in about:config to enable logging to ff stdout.

  // Set print_all to true/false for explicit on/off regardless of about:config.
  // Some logging where "Components" interface is inaccessible (workers)
  //  might get lost with just about:config flag, but available if print_all=true here.
  print_all: null,

  // Print logging flag before the message.
  print_component: true,

  // These can be used to selectively enable some logging with print_all=false.
  print_flags: {
    'core' : false,
    'settings' : false,
    'worker' : false,
    'proto' : false,
    'ui' : false,
    'notary' : false,
    'pki' : false,
  },

  _init: function() {
    var add_helper = function(flag) {
      CV9BLog[flag] = function(line) { return CV9BLog.print(flag, line); }
    }
    for (var flag in CV9BLog.print_flags) { add_helper(flag); }
  },

  print: function(flag, line) {
    if (CV9BLog.print_all === null && typeof Components !== 'undefined') {
      var prefs = Components.classes['@mozilla.org/preferences-service;1']
        .getService(Components.interfaces.nsIPrefBranch);
      var state = prefs.prefHasUserValue('convergence.logging.enabled');
      if (state) CV9BLog.print_all = prefs.getBoolPref('convergence.logging.enabled');
      else CV9BLog.print_all = false;
    };

    if (!CV9BLog.print_flags[flag] && !CV9BLog.print_all) { return; }
    if (line.search('\n') != -1) line = '|\n  ' + line.replace(/^\s+|\s+$/, '').split('\n').join('\n  ');
    line = 'Convergence' + (CV9BLog.print_component ? '.' + flag : '') + ': ' + line + '\n';
    dump(line);
    try { Firebug.Console.log(line); } catch(e) { } // this line works in extensions
    try { console.log(line); } catch(e) { } // this line works in HTML files
  },

}

CV9BLog._init()
