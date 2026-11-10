// Validate process output before it enters the long-lived shell's bindings.
function integer(value) { return typeof value === "number" && isFinite(value) && Math.floor(value) === value }
function percent(value) { return value === null || (integer(value) && value >= 0 && value <= 100) }
function string(value, limit) { return typeof value === "string" && value.length <= limit }
function values(list, allowEmpty) {
  if (!Array.isArray(list) || list.length > 101 || (!allowEmpty && !list.length)) return false
  var seen = ({})
  for (var i = 0; i < list.length; i++) {
    var v = list[i]
    if (!integer(v) || v < 0 || v > 100 || seen[v]) return false
    seen[v] = true
  }
  return true
}
function parse(raw) {
  if (typeof raw !== "string" || raw.length > 131072) throw new Error("Status exceeds the size limit")
  var data = JSON.parse(raw)
  if (!data || typeof data !== "object" || Array.isArray(data) || typeof data.installed !== "boolean"
      || !string(data.version, 32) || !Array.isArray(data.controls) || data.controls.length > 16
      || !Array.isArray(data.batteries) || data.batteries.length > 16
      || !Array.isArray(data.conflicts) || data.conflicts.length > 8 || !string(data.error, 2000)) throw new Error("Invalid battery status")
  var ids = ({})
  for (var i = 0; i < data.controls.length; i++) {
    var d = data.controls[i]
    if (!d || typeof d !== "object" || !string(d.id, 80) || !/^[A-Za-z0-9_.:-]+$/.test(d.id) || ids[d.id]
        || !string(d.driver, 64) || !/^[a-z0-9-]+$/.test(d.driver) || !string(d.label, 160)
        || ["threshold", "pair", "toggle", "charge-types", "framework"].indexOf(d.kind) < 0
        || typeof d.shared !== "boolean" || !values(d.stopValues, false) || !values(d.startValues, true)
        || ["", "apple", "msi"].indexOf(d.derived) < 0 || !integer(d.gap) || d.gap < 1 || d.gap > 10
        || !integer(d.fullStart) || d.fullStart < 0 || d.fullStart > 100
        || !percent(d.end) || !percent(d.start) || !percent(d.careStop) || !percent(d.fullStop)
        || (d.careStop !== null && d.stopValues.indexOf(d.careStop) < 0)
        || (d.fullStop !== null && d.stopValues.indexOf(d.fullStop) < 0)
        || typeof d.persisted !== "boolean" || !string(d.warning, 2000)) throw new Error("Invalid charge control")
    if (d.saved !== null && (!d.saved || typeof d.saved !== "object" || !percent(d.saved.end) || !percent(d.saved.start)
        || ["plugin", "asahi"].indexOf(d.saved.source) < 0)) throw new Error("Invalid saved setting")
    ids[d.id] = true
  }
  for (var b = 0; b < data.batteries.length; b++) {
    var battery = data.batteries[b]
    if (!battery || !string(battery.id, 80)) throw new Error("Invalid battery")
  }
  for (var c = 0; c < data.conflicts.length; c++) if (!string(data.conflicts[c], 100)) throw new Error("Invalid service state")
  return data
}
if (typeof module !== "undefined") module.exports = {parse: parse}
