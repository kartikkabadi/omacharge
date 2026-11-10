import QtQuick
import QtQuick.Controls as Controls
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "ChargeModel.js" as ChargeModel

Column {
  id: root
  property color foreground: Commons.Color.foreground
  property string fontFamily: Style.font.family
  property bool opened: false
  property bool hasCursor: false
  property int cursorIndex: 0
  property int selectedDevice: 0
  property var state: ({controls: [], batteries: [], conflicts: [], installed: false, error: ""})
  property string errorDetail: ""
  property string feedbackKey: ""
  property int generation: 0
  property bool freshStatus: false
  property bool readFailed: false
  property var deviceIds: []
  readonly property bool supported: state.controls.length > 0
  readonly property bool busy: action.running
  readonly property bool writable: freshStatus && state.installed && state.conflicts.length === 0 && !busy && !state.error
  property string client: decodeURIComponent(String(Qt.resolvedUrl("client.py")).replace(/^file:\/\//, ""))
  readonly property bool editing: {
    for (var i = 0; i < devices.count; i++) {
      var card = devices.itemAt(i)
      if (card && card.editing) return true
    }
    return false
  }
  signal hoveredChoice(int index)
  signal applied()
  spacing: Style.space(10)
  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

  function refresh() {
    if (!reader.running && !busy) {
      reader.generation = generation
      reader.output = ""
      reader.error = ""
      reader.running = true
    }
  }
  function accept(raw) {
    var next = ChargeModel.parse(raw)
    var selectedId = state.controls[selectedDevice] ? state.controls[selectedDevice].id : ""
    var nextIds = next.controls.map(function(d) { return d.id })
    if (JSON.stringify(next.controls) === JSON.stringify(state.controls)) next.controls = state.controls
    state = next
    if (JSON.stringify(nextIds) !== JSON.stringify(deviceIds)) deviceIds = nextIds
    selectedDevice = Math.max(0, nextIds.indexOf(selectedId))
    freshStatus = true
    readFailed = false
    if (feedbackKey === "charge.readError") { feedbackKey = ""; errorDetail = "" }
  }
  function readError(detail) {
    freshStatus = false
    readFailed = true
    feedbackKey = "charge.readError"
    errorDetail = String(detail || "").slice(0, 2000)
  }
  function execute(command, feedback) {
    if (busy) return
    generation++
    errorDetail = ""
    feedbackKey = feedback
    action.output = ""
    action.error = ""
    action.command = ["/usr/bin/python3", client].concat(command)
    action.running = true
  }
  function apply(device, end, start) {
    if (!writable || !device || end === null || device.stopValues.indexOf(end) < 0) return
    var args = ["set", device.id, String(end)]
    if (start !== null && start !== undefined) args.push(String(start))
    execute(args, "charge.applying")
  }
  function setLimit(limit) {
    var device = state.controls[selectedDevice]
    if (device) apply(device, limit === 80 ? device.careStop : device.fullStop, null)
  }
  function activate() { setLimit(cursorIndex === 0 ? 80 : 100) }
  onOpenedChanged: if (opened) refresh()
  Component.onCompleted: refresh()

  Process {
    id: reader
    property int generation: 0
    property string output: ""
    property string error: ""
    command: ["/usr/bin/python3", root.client, "status"]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: reader.output = text }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: reader.error = text }
    onExited: function(code) {
      if (reader.generation !== root.generation) {
        Qt.callLater(function() { root.refresh() })
        return
      }
      try {
        if (code !== 0) throw new Error("status unavailable")
        root.accept(output)
      } catch (e) { root.readError(reader.error) }
    }
  }
  Process {
    id: action
    property string output: ""
    property string error: ""
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: action.output = text }
    stderr: StdioCollector { waitForEnd: true; onStreamFinished: action.error = text }
    onExited: function(code) {
      if (code === 0) {
        try {
          // The root helper returns status; the bridge adds setup state on refresh.
          var next = JSON.parse(output)
          if (next.installed === undefined) next.installed = true
          root.accept(JSON.stringify(next))
          root.feedbackKey = action.command[action.command.length - 1] === "setup" ? "charge.setupComplete" : "charge.applied"
          root.applied()
        } catch (e) { root.readError("") }
      } else {
        root.feedbackKey = "charge.setError"
        root.errorDetail = error.trim().slice(0, 2000)
      }
      // Process.running can remain true until onExited returns.
      Qt.callLater(function() { root.refresh() })
    }
  }
  Timer { interval: 5000; repeat: true; running: root.opened && !root.busy; onTriggered: root.refresh() }

  PanelSeparator { foreground: root.foreground }
  PanelSectionHeader { text: strings.t("charge.title"); foreground: root.foreground; fontFamily: root.fontFamily }
  CareText { visible: root.supported; text: strings.t("charge.holdInfo") }

  CareText {
    visible: !root.supported
    text: strings.t(root.state.batteries.length === 0 ? "charge.noBattery" : "charge.unsupported")
  }
  CareText {
    visible: root.state.conflicts.indexOf("tlp.service") >= 0
    text: strings.t("charge.conflict")
  }
  CareText {
    visible: root.state.error !== ""
    text: root.state.error || ""
  }
  Column {
    width: parent.width
    spacing: Style.space(8)
    visible: !root.state.installed && (root.supported || root.readFailed)
    CareText { text: strings.t("charge.setupInfo") }
    Button {
      text: strings.t("charge.setup")
      foreground: root.foreground
      fontFamily: root.fontFamily
      bordered: true
      enabled: !root.busy
      Accessible.role: Accessible.Button
      Accessible.name: text
      Accessible.onPressAction: clicked()
      onClicked: root.execute(["setup"], "charge.setupPending")
    }
  }

  Repeater {
    id: devices
    model: root.deviceIds
    delegate: Column {
      id: card
      required property var modelData
      required property int index
      property var device: root.state.controls.filter(function(d) { return d.id === card.modelData })[0]
        || ({ id: String(modelData), driver: "", label: "", kind: "threshold", shared: false, end: null, start: null,
              stopValues: [100], startValues: [], derived: "", gap: 1, fullStart: 95, careStop: null, fullStop: 100,
              persisted: false, warning: "", saved: null })
      readonly property bool editing: stopPicker.popup.visible || startPicker.popup.visible
      property int endDraft: device.stopValues.indexOf(device.end) >= 0 ? device.end : device.careStop !== null ? device.careStop : device.stopValues[0]
      property int startDraft: device.startValues.indexOf(device.start) >= 0 && device.start <= endDraft - device.gap ? device.start : defaultStart(endDraft)
      readonly property var validStarts: device.startValues.filter(function(v) { return v <= card.endDraft - card.device.gap })
      onDeviceChanged: {
        if (device.stopValues.indexOf(endDraft) < 0) endDraft = device.stopValues[0]
        if (validStarts.indexOf(startDraft) < 0) startDraft = defaultStart(endDraft)
      }
      HoverHandler { onHoveredChanged: if (hovered) root.selectedDevice = card.index }
      Connections {
        target: root
        function onApplied() {
          card.endDraft = card.device.stopValues.indexOf(card.device.end) >= 0 ? card.device.end : card.device.stopValues[0]
          card.startDraft = card.device.startValues.indexOf(card.device.start) >= 0 ? card.device.start : card.defaultStart(card.endDraft)
        }
      }
      width: root.width
      spacing: Style.space(8)
      function defaultStart(end) {
        var wanted = end === 100 ? device.fullStart : end - 5
        var allowed = device.startValues.filter(function(v) { return v <= end - card.device.gap })
        if (!allowed.length) return 0
        return allowed.reduce(function(a, b) { return Math.abs(b - wanted) < Math.abs(a - wanted) ? b : a })
      }
      function pick(index) {
        root.selectedDevice = card.index
        root.hoveredChoice(index)
      }
      function currentLabel() {
        if (device.end === null) return strings.t("charge.unknown")
        if (device.kind === "toggle" || device.kind === "charge-types")
          return strings.t(device.end === 1 ? "charge.conservationOn" : "charge.conservationOff")
        return strings.t("charge.current").arg(Commons.I18n.formatNumber(device.end))
      }
      CareText {
        opacity: 1
        text: strings.t("charge.device").arg(card.device.shared ? strings.t("charge.allBatteries")
          : root.state.controls.length === 1 ? strings.t("charge.internalBattery") : strings.t("charge.batteryId").arg(card.device.label))
          .arg(strings.t("hardware." + card.device.driver, card.device.driver))
      }
      CareText { text: card.currentLabel() }
      Row {
        id: presets
        width: parent.width
        spacing: Style.space(6)
        Button {
          objectName: "care-" + card.device.id
          width: (presets.width - presets.spacing) / 2
          text: strings.t("charge.care")
          foreground: root.foreground
          fontFamily: root.fontFamily
          fontSize: Style.font.bodySmall
          bordered: true
          active: card.device.careStop !== null && card.device.end === card.device.careStop
          hasCursor: root.hasCursor && root.selectedDevice === card.index && root.cursorIndex === 0
          enabled: root.writable && card.device.careStop !== null
          opacity: enabled ? 1 : 0.5
          Accessible.role: Accessible.Button
          Accessible.name: text
          Accessible.onPressAction: clicked()
          onClicked: root.apply(card.device, card.device.careStop, null)
          onHovered: function(h) { if (h) card.pick(0) }
        }
        Button {
          objectName: "full-" + card.device.id
          width: (presets.width - presets.spacing) / 2
          text: strings.t("charge.full")
          foreground: root.foreground
          fontFamily: root.fontFamily
          fontSize: Style.font.bodySmall
          bordered: true
          active: card.device.fullStop !== null && card.device.end === card.device.fullStop
          hasCursor: root.hasCursor && root.selectedDevice === card.index && root.cursorIndex === 1
          enabled: root.writable && card.device.fullStop !== null
          opacity: enabled ? 1 : 0.5
          Accessible.role: Accessible.Button
          Accessible.name: text
          Accessible.onPressAction: clicked()
          onClicked: root.apply(card.device, card.device.fullStop, null)
          onHovered: function(h) { if (h) card.pick(1) }
        }
      }
      CareText {
        visible: card.device.derived === "apple"
        text: strings.t("charge.appleInfo").arg(Commons.I18n.formatNumber(80)).arg(Commons.I18n.formatNumber(75))
      }
      CareText {
        visible: card.device.start !== null && card.device.derived !== "apple"
        text: card.device.start === 0 ? strings.t("charge.autoRestart") : strings.t("charge.restart").arg(Commons.I18n.formatNumber(card.device.start === null ? 0 : card.device.start))
      }
      // The lists come from the backend's capability table, never brand guesses in QML.
      Row {
        id: customRow
        width: parent.width
        spacing: Style.space(6)
        visible: card.device.stopValues.length > 2 || card.device.startValues.length > 0
        enabled: root.writable
        ThresholdPicker {
          id: stopPicker
          foreground: root.foreground
          fontFamily: root.fontFamily
          objectName: "stop-" + card.device.id
          width: (customRow.width - customRow.spacing) / 2
          model: card.device.stopValues
          currentIndex: Math.max(0, model.indexOf(card.endDraft))
          displayText: strings.t("charge.stopAt").arg(Commons.I18n.formatNumber(card.endDraft))
          Accessible.name: strings.t("charge.maximum")
          onActivated: function(index) {
            card.endDraft = model[index]
            if (card.validStarts.indexOf(card.startDraft) < 0) card.startDraft = card.defaultStart(card.endDraft)
          }
        }
        ThresholdPicker {
          id: startPicker
          foreground: root.foreground
          fontFamily: root.fontFamily
          objectName: "start-" + card.device.id
          visible: card.device.startValues.length > 0
          width: stopPicker.width
          model: card.validStarts
          currentIndex: Math.max(0, model.indexOf(card.startDraft))
          displayText: strings.t("charge.startAt").arg(Commons.I18n.formatNumber(card.startDraft))
          Accessible.name: strings.t("charge.minimum")
          onActivated: function(index) { card.startDraft = model[index] }
        }
      }
      Button {
        visible: customRow.visible
        text: strings.t("charge.applyCustom")
        foreground: root.foreground
        fontFamily: root.fontFamily
        fontSize: Style.font.bodySmall
        bordered: true
        enabled: root.writable
        Accessible.role: Accessible.Button
        Accessible.name: text
        Accessible.onPressAction: clicked()
        onClicked: root.apply(card.device, card.endDraft, card.device.startValues.length ? card.startDraft : null)
      }
      CareText {
        text: strings.t(card.device.persisted ? "charge.saved" : "charge.unsaved")
        font.pixelSize: Style.font.caption
      }
      CareText { visible: card.device.fullStop === null; text: strings.t("charge.noFullCharge") }
      CareText { visible: card.device.warning !== ""; text: card.device.warning }
    }
  }
  CareText {
    visible: root.feedbackKey !== ""
    text: strings.t(root.feedbackKey) + (root.errorDetail ? "\n" + root.errorDetail : "")
  }
  component CareText: Text {
    width: parent.width
    textFormat: Text.PlainText
    font.family: root.fontFamily
    font.pixelSize: Style.font.bodySmall
    color: root.foreground
    opacity: 0.7
    wrapMode: Text.Wrap
  }
}
