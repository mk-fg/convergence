
// Some logging where "Components" interface is inaccessible (workers) might
//  get lost with just about:config flag, but available if print_all=true is set in Logging.js.
// Changes require restart.
pref("convergence.logging.enabled", true);
