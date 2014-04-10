
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
    'worker_conn' : false,
    'worker_shuffle' : false,
    'proto' : false,
    'ui' : false,
    'notary' : false,
    'pki' : false,
  },

  // Dump messages directly to stderr, without dump() and such
  use_nspr: true,
  _nspr_fd: null,

  _init: function() {
    if (CV9BLog.print_all === null && typeof Components !== 'undefined') {
      var prefs = Components.classes['@mozilla.org/preferences-service;1']
        .getService(Components.interfaces.nsIPrefBranch);
      var state = prefs.prefHasUserValue('convergence.logging.enabled');
      if (state) CV9BLog.print_all = prefs.getBoolPref('convergence.logging.enabled');
      else CV9BLog.print_all = false;
    }

    // XXX: repeats messages, breaks stuff
    // Try to use Log.jsm, if available
    var log_jsm = false;
    // try {
    // 	Components.utils.import('resource://gre/modules/Log.jsm');
    // 	log_jsm = true;
    // } catch (e) { }

    var add_helper = function(flag) {
      if (log_jsm) {
        var log = Log.repository.getLogger('Convergence.' + flag);
        log.level = Log.Level.Debug;
        log.addAppender(new Log.DumpAppender(new Log.BasicFormatter()));
        CV9BLog[flag] = function(line, json) {
          log.debug(CV9BLog.format(line, json)); }
      } else {
        CV9BLog[flag] = function(line, json) {
          return CV9BLog.print(flag.replace('_', '.'), line, json); }
      }
    }
    for (var flag in CV9BLog.print_flags) { add_helper(flag); }
  },

  format: function(line, json) {
    if (json) line += CV9BLog.print_json(json);
    if (line.search('\n') != -1) line = '|\n  ' + line.replace(/^\s+|\s+$/, '').split('\n').join('\n  ');
    return line;
  },

  print: function(flag, line, json, no_nspr) {
    if (!CV9BLog.print_flags[flag] && !CV9BLog.print_all) return;
    line = CV9BLog.format(line, json);
    line = 'Convergence' + (CV9BLog.print_component ? '.' + flag : '') + ': ' + line + '\n';

    var nspr_err;
    if (!no_nspr) {
      try { CV9BLog.print_nspr(line); }
      catch (e) {
        CV9BLog.print(flag, 'NSPR logging error: ' + e, null, true);
        nspr_err = e;
      }
    }
    if (no_nspr || nspr_err) {
      // Bad (despite being high-level) way of logging, as it sends messages
      //  to different destinations, and probably drops some stuff entirely
      dump(line);
      try { Firebug.Console.log(line); } catch(e) { } // this line works in extensions
      try { console.log(line); } catch(e) { } // this line works in HTML files
    }
  },

  print_nspr: function(line) {
    if (!CV9BLog.use_nspr) throw 'Logging: NSPR disabled';
    if (typeof NSPR === 'undefined' || typeof NSPR.lib === 'undefined')
      throw 'Logging: NSPR unavailable (yet?)';
    if (CV9BLog._nspr_fd === null) {
      CV9BLog._nspr_fd = NSPR.lib.PR_GetSpecialFD(NSPR.lib.PR_StandardError);
      if (CV9BLog._nspr_fd.isNull()) {
        CV9BLog.use_nspr = false;
        throw 'Logging: NSPR failed to get stderr fd';
      }
    }
    // line = 'NSPR: ' + line;
    if (NSPR.lib.PR_Write(CV9BLog._nspr_fd, NSPR.lib.buffer(line), line.length) <= 0)
      throw 'Logging: NSPR write failure';
  },

  // Can be used as: CV9BLog.proto('Got object:' + CV9BLog.print_json(obj));
  print_json: function(obj, cut, indent) {
    if (indent == null) indent = '  ';
    if (cut == null) cut = 50;
    return '\n' + CV9BLog._print_json(obj, cut, indent);
  },
  _print_json: function(obj, cut, indent) {
    function IsArray(array) { return !( !array || (!array.length || array.length == 0)
      || typeof array !== 'object' || !array.constructor || array.nodeType || array.item ); }
    var result = '';
    if (indent == null) indent = '';
    if (cut == null) cut = 16384;
    for (var property in obj) {
      var value = obj[property];
      var txt = '<unknown type>';
      var t = typeof value;
      if (t == 'string') {
        if (value.length > cut) value = value.substr(0, cut) + '...';
        txt = '`' + value + "'"; }
      if (t == 'boolean' || t == 'number') txt = value.toString();
      else if (t == 'object')
        txt = '\n' + CV9BLog._print_json(value, cut, indent + '  ') + '\n';
      result += indent + property + ': ' + txt + '\n';
    }
    return result;
  },

}

CV9BLog._init()
