
/**
  * This global object is used for logging all the stuff.
  **/

var CV9BLog = { // my attempt to produce short yet fairly unique id

  print_all: true,
  print_component: true,
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
    if (!CV9BLog.print_flags[flag] && !CV9BLog.print_all) { return; }
    if (line.search('\n') != -1) line = '|\n  ' + line.replace(/^\s+|\s+$/, '').split('\n').join('\n  ');
    line = 'Convergence' + (CV9BLog.print_component ? '.' + flag : '') + ': ' + line + '\n';
    dump(line);
    try { Firebug.Console.log(line); } catch(e) { } // this line works in extensions
    try { console.log(line); } catch(e) { } // this line works in HTML files
  },

  // stolen from: http://stackoverflow.com/questions/130404/javascript-data-formatting-pretty-printer
  print_json : function(obj, indent) {
    function IsArray(array) { return !( !array || (!array.length || array.length == 0)
      || typeof array !== 'object' || !array.constructor || array.nodeType || array.item ); }
    var result = '';
    if (indent == null) indent = '';
    for (var property in obj){
      var value = obj[property];
      var txt = '<unknown type>';
      var t = typeof value;
      if (t == 'string' || t == 'boolean' || t == 'number') txt = "'" + value + "'";
      else if (t == 'object') {
        var od = this.pretty_print_json(value, indent + '	');
        txt = '\n' + indent + '{\n' + od + '\n' + indent + '}';
      }
      result += indent + "'" + property + "' : " + txt + ',\n';
    }
    return result.replace(/,\n$/, '');
  },

}

CV9BLog._init()
