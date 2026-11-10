import QtQuick
import QtQuick.Controls as Controls
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui

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
  readonly property bool supported: state.controls.length > 0
  readonly property bool busy: action.running
  readonly property bool writable: state.installed && state.conflicts.length === 0 && !busy && !state.error
  property string client: String(Qt.resolvedUrl("client.py")).replace(/^file:\/\//, "")
  readonly property bool editing: {
    for (var i = 0; i < devices.count; i++) {
      var card = devices.itemAt(i)
      if (card && card.editing) return true
    }
    return false
  }
  signal hoveredChoice(int index)
  spacing: Style.space(10)
  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

  function refresh() {
    if (!reader.running && !busy) {
      reader.generation = generation
      reader.running = true
    }
  }
  function accept(raw) {
    var next = JSON.parse(raw)
    if (!Array.isArray(next.controls) || next.controls.length > 16 || !Array.isArray(next.batteries)
        || !Array.isArray(next.conflicts) || typeof next.installed !== "boolean") throw new Error("Invalid battery status")
    if (JSON.stringify(next.controls) === JSON.stringify(state.controls)) next.controls = state.controls
    state = next
    selectedDevice = Math.min(selectedDevice, Math.max(0, next.controls.length - 1))
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
    if (!writable || !device) return
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
    command: ["/usr/bin/python3", root.client, "status"]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: reader.output = text }
    onExited: function(code) {
      if (reader.generation !== root.generation) { root.refresh(); return }
      try {
        if (code !== 0) throw new Error("status unavailable")
        root.accept(output)
      } catch (e) { root.feedbackKey = "charge.readError" }
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
          root.feedbackKey = "charge.applied"
        } catch (e) { root.feedbackKey = "charge.readError" }
      } else {
        root.feedbackKey = "charge.setError"
        root.errorDetail = error.trim().slice(0, 2000)
      }
      root.refresh()
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
    visible: root.state.conflicts.length > 0
    text: strings.t("charge.conflict")
  }
  CareText {
    visible: root.state.error !== ""
    text: root.state.error || ""
  }
  Column {
    width: parent.width
    spacing: Style.space(8)
    visible: root.supported && !root.state.installed
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
    model: root.state.controls
    delegate: Column {
      id: card
      required property var modelData
      required property int index
      property var device: modelData
      readonly property bool editing: stopPicker.popup.visible || startPicker.popup.visible
      property int endDraft: device.end === null ? device.careStop : device.end
      property int startDraft: device.start === null ? defaultStart(endDraft) : device.start
      readonly property var validStarts: device.startValues.filter(function(v) { return v <= card.endDraft - card.device.gap })
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
          active: card.device.end === card.device.careStop
          hasCursor: root.hasCursor && root.selectedDevice === card.index && root.cursorIndex === 0
          enabled: root.writable
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
          active: card.device.end === card.device.fullStop
          hasCursor: root.hasCursor && root.selectedDevice === card.index && root.cursorIndex === 1
          enabled: root.writable
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
        Controls.ComboBox {
          id: stopPicker
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
        Controls.ComboBox {
          id: startPicker
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
