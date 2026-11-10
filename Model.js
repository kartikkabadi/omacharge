function clampIndex(index, length) {
  if (length <= 0) return 0
  return Math.max(0, Math.min(length - 1, index))
}

// Validate a complete snapshot before QML binds to any of its nested fields.
function parseChargeStatus(raw) {
  if (typeof raw !== "string" || raw.length > 131072) throw new Error("Invalid battery status size")
  var next = JSON.parse(raw)
  function list(value, limit) { return Array.isArray(value) && value.length <= limit }
  function text(value, limit) { return typeof value === "string" && value.length <= limit }
  function percent(value) { return typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 100 }
  function values(value) { return list(value, 101) && value.every(percent) && value.every(function(v, i) { return i === 0 || v > value[i - 1] }) }
  if (!next || !list(next.controls, 16) || !list(next.batteries, 16) || !list(next.conflicts, 16)
      || typeof next.installed !== "boolean" || !text(next.error, 2000)
      || !next.conflicts.every(function(v) { return text(v, 160) })
      || !next.batteries.every(function(v) { return v && text(v.id, 80) })) throw new Error("Invalid battery status")
  var seen = {}
  next.controls.forEach(function(c) {
    if (!c || !text(c.id, 80) || !/^[A-Za-z0-9_.:-]+$/.test(c.id) || seen[c.id]
        || !text(c.driver, 80) || !text(c.label, 160) || !text(c.warning, 2000)
        || ["threshold", "toggle", "charge-types", "pair", "framework"].indexOf(c.kind) < 0
        || ["", "apple", "msi"].indexOf(c.derived) < 0 || typeof c.shared !== "boolean"
        || typeof c.persisted !== "boolean" || !values(c.stopValues) || !c.stopValues.length || !values(c.startValues)
        || !percent(c.gap) || c.gap < 1 || !percent(c.fullStart)
        || c.stopValues.indexOf(c.careStop) < 0 || c.stopValues.indexOf(c.fullStop) < 0
        || (c.end !== null && !percent(c.end)) || (c.start !== null && !percent(c.start))) throw new Error("Invalid charge control")
    seen[c.id] = true
  })
  return next
}

function selectProfileIndex(index, delta, profiles) {
  var values = Array.isArray(profiles) ? profiles : []
  if (values.length === 0) return 0
  return clampIndex(index + delta, values.length)
}

function parseKeyValue(raw) {
  var next = {}
  var lines = String(raw || "").split("\n")
  for (var i = 0; i < lines.length; i++) {
    var idx = lines[i].indexOf("\t")
    if (idx <= 0) continue
    next[lines[i].substring(0, idx)] = lines[i].substring(idx + 1).trim()
  }
  return next
}

function parseProfiles(raw, previousIndex) {
  var lines = String(raw || "").split("\n")
  var list = []
  var active = ""
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim()
    if (!line) continue
    var parts = line.split("\t")
    list.push(parts[0])
    if (parts[1] === "1") active = parts[0]
  }
  return {
    profiles: list,
    activeProfile: active,
    profileIndex: clampIndex(previousIndex || 0, list.length)
  }
}

function profileIcon(name) {
  if (name === "power-saver") return "󰌪"
  if (name === "balanced") return "󰊚"
  if (name === "performance") return "󰓅"
  return "󰂄"
}

function batteryFraction(device) {
  return device && device.isPresent ? Math.max(0, Math.min(1, device.percentage)) : 0
}

function chargeThresholdActive(device, onBattery, states) {
  var d = device || {}
  var s = states || {}
  if (!(d && d.isPresent && !onBattery)) return false

  var fraction = batteryFraction(d)
  if (d.state === s.Discharging) return false
  if (d.state === s.PendingCharge) return true
  if (d.state === s.FullyCharged && fraction < 0.99) return true
  if (d.state !== s.Charging || fraction >= 0.99) return false

  return Number(d.changeRate || 0) <= 0.2 || Number(d.timeToFull || 0) >= 8 * 60 * 60
}

function batteryIcon(device, onBattery, states) {
  var d = device || {}
  if (!d.isPresent) return ""

  var chargingIcons = ["󰢜", "󰂆", "󰂇", "󰂈", "󰢝", "󰂉", "󰢞", "󰂊", "󰂋", "󰂅"]
  var defaultIcons = ["󰁺", "󰁻", "󰁼", "󰁽", "󰁾", "󰁿", "󰂀", "󰂁", "󰂂", "󰁹"]
  var index = Math.max(0, Math.min(9, Math.floor(d.percentage * 10)))
  var threshold = chargeThresholdActive(d, onBattery, states)

  if (threshold) return defaultIcons[index]
  if (d.state === states.FullyCharged) return "󰂅"
  if (!onBattery) return chargingIcons[index]
  return defaultIcons[index]
}

function modeLabel(device, onBattery, states, tr) {
  var t = typeof tr === "function" ? tr : function(key, english) { return english }
  var d = device || {}
  if (!d.isPresent) return ""

  var percentage = d.isPresent ? d.percentage : 0
  if (chargeThresholdActive(d, onBattery, states)) return t("power.threshold", "Threshold")
  if (onBattery) return t("power.onBattery", "On battery")
  if (!onBattery && percentage >= 1) return t("power.fullyCharged", "Fully charged")
  return t("power.charging", "Charging")
}

// omarchy-battery-status --shell answers in plain digits with the unit
// attached ("13.1W", "75-80%"); the panel writes each number in the
// language's digits and decimal separator, keeping its decimals and unit.
function localizeReading(raw, fmt) {
  var f = typeof fmt === "function" ? fmt : function(v, d) { return d === undefined ? String(v) : Number(v).toFixed(d) }
  return String(raw === undefined || raw === null ? "" : raw).replace(/\d+(?:\.\d+)?/g, function(number) {
    var dot = number.indexOf(".")
    return f(Number(number), dot < 0 ? undefined : number.length - dot - 1)
  })
}

function profileLabel(name, tr) {
  var t = typeof tr === "function" ? tr : function(key, english) { return english }
  var value = String(name || "")
  if (value === "power-saver") return t("power.profilePowerSaver", "Power-saver")
  if (value === "balanced") return t("power.profileBalanced", "Balanced")
  if (value === "performance") return t("power.profilePerformance", "Performance")
  return value.charAt(0).toUpperCase() + value.slice(1)
}

if (typeof module !== "undefined") {
  module.exports = {
    parseChargeStatus: parseChargeStatus,
    clampIndex: clampIndex,
    selectProfileIndex: selectProfileIndex,
    parseKeyValue: parseKeyValue,
    parseProfiles: parseProfiles,
    profileIcon: profileIcon,
    batteryFraction: batteryFraction,
    chargeThresholdActive: chargeThresholdActive,
    batteryIcon: batteryIcon,
    modeLabel: modeLabel,
    profileLabel: profileLabel,
    localizeReading: localizeReading
  }
}
