
/**
  * This class represents a list of regexp patterns to check strings against.
  *
  **/


function PatternList(text) {
  this.source = text || '';
  this.patterns = new Array();

  var patterns = this.source.split('\n');

  for (var i=0; i<patterns.length; i++) {
    var pat = patterns[i];
    if (/^\s*(#.*)?$/.test(pat)) continue;
    try {
      pat = new RegExp(pat, 'i');
    } catch (err) {
      CV9BLog.settings('Failed to compile regexp - ' + err + ', skipping');
      continue;
    }
    this.patterns.push(pat);
  }

}

PatternList.prototype.testHost = function(str) {
  for (var i=0; i<this.patterns.length; i++) {
    if (this.patterns[i].test(str)) return true;
  }
  return false;
}
