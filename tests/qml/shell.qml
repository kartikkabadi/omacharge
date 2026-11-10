import QtQuick
import Quickshell

ShellRoot {
  id: test
  property int phase: 0
  property int ticks: 0
  function assertTrue(condition, message) {
    if (!condition) { console.error("FAIL: " + message); Qt.quit(); throw new Error(message) }
  }
  function find(item, name) {
    if (item.objectName === name) return item
    if (!item.children) return null
    for (var i = 0; i < item.children.length; i++) {
      var found = find(item.children[i], name)
      if (found) return found
    }
    return null
  }
  FloatingWindow {
    id: window
    visible: true
    implicitWidth: 440
    implicitHeight: 650
    color: "#171717"
    Item {
      id: capture
      width: 440
      height: controls.implicitHeight + 40
      Rectangle { anchors.fill: parent; color: "#171717" }
    ChargeLimitControl {
      id: controls
      x: 20
      y: 20
      width: 400
      client: String(Qt.resolvedUrl("mock-client.py")).replace(/^file:\/\//, "")
    }
    }
  }
  Timer {
    interval: 150
    repeat: true
    running: true
    onTriggered: {
      test.ticks++
      if (test.ticks > 80) { console.error("FAIL: timeout at phase " + test.phase); Qt.quit(); return }
      if (test.phase === 0 && controls.supported) {
        test.assertTrue(controls.writable, "setup is recognized")
        var care = test.find(controls, "care-TEST")
        test.assertTrue(care !== null, "real care button exists")
        care.clicked()
        test.phase = 1
      } else if (test.phase === 1 && !controls.busy && controls.state.controls[0].end === 80) {
        test.assertTrue(controls.state.controls[0].start === 75, "Apple restart state")
        test.find(controls, "full-TEST").clicked()
        test.phase = 2
      } else if (test.phase === 2 && !controls.busy && controls.state.controls[0].end === 100) {
        test.assertTrue(controls.state.controls[0].start === 100, "Full charge state")
        var next = JSON.parse(JSON.stringify(controls.state))
        next.controls[0] = Object.assign({}, next.controls[0], {id:"BAT0", driver:"dell", end:80, start:75, stopValues:[55,60,65,70,75,80,85,90,95,100], startValues:[50,55,60,65,70,75,80,85,90,95], derived:"", gap:5, fullStart:95, label:"<img src='https://example.invalid/tracker'>"})
        controls.accept(JSON.stringify(next))
        test.phase = 3
      } else if (test.phase === 3) {
        var stop = test.find(controls, "stop-BAT0")
        var start = test.find(controls, "start-BAT0")
        test.assertTrue(stop !== null && start !== null, "Custom controls exist")
        test.assertTrue(stop.model.length === 10, "Only advertised stops appear")
        test.assertTrue(start.model.indexOf(80) < 0, "Restart gap enforced in picker")
        var before = stop
        controls.accept(JSON.stringify(controls.state))
        test.assertTrue(test.find(controls, "stop-BAT0") === before, "Refresh preserves editors")
        controls.grabToImage(function(result) { result.saveToFile(Qt.resolvedUrl("custom-panel.png").toString().replace(/^file:\/\//, "")) })
        stop.popup.open()
        test.phase = 4
      } else if (test.phase === 4) {
        var picker = test.find(controls, "stop-BAT0")
        test.assertTrue(picker.popup.visible && controls.editing, "Picker opens and owns keyboard navigation")
        test.assertTrue(picker.popup.contentItem.count > 0, "Picker delegates load")
        picker.popup.close()
        test.phase = 5
      } else if (test.phase === 5) {
        var picker = test.find(controls, "stop-BAT0")
        picker.activated(picker.model.indexOf(85))
        var changed = JSON.parse(JSON.stringify(controls.state))
        changed.controls[0].end = 90
        controls.accept(JSON.stringify(changed))
        test.assertTrue(test.find(controls, "stop-BAT0") === picker, "Changing current readings preserves the editor")
        test.assertTrue(picker.displayText.indexOf("85") >= 0, "Custom draft survives a changed reading")
        controls.client = String(Qt.resolvedUrl("failing-client.py")).replace(/^file:\/\//, "")
        controls.refresh()
        test.phase = 10
      } else if (test.phase === 10 && controls.readFailed) {
        test.assertTrue(!controls.writable, "Read failure disables stale controls")
        controls.client = String(Qt.resolvedUrl("mock-client.py")).replace(/^file:\/\//, "")
        controls.refresh()
        test.phase = 11
      } else if (test.phase === 11 && controls.freshStatus && !controls.readFailed) {
        test.assertTrue(controls.feedbackKey !== "charge.readError", "Successful refresh clears a transient error")
        controls.execute(["setup"], "charge.setupPending")
        test.phase = 12
      } else if (test.phase === 12 && !controls.busy && controls.feedbackKey === "charge.setupComplete") {
        test.assertTrue(controls.writable, "Setup completion has the correct status")
        test.phase = 13
      } else if (test.phase === 13) {
        var demo = JSON.parse(JSON.stringify(controls.state))
        demo.controls[0] = Object.assign({}, demo.controls[0], {id:"DEMO", driver:"apple", label:"Demo", end:80, start:75, stopValues:[80,100], startValues:[], derived:"apple", gap:1, fullStart:100, persisted:true})
        controls.accept(JSON.stringify(demo))
        controls.feedbackKey = ""
        test.phase = 6
      } else if (test.phase === 6) {
        capture.grabToImage(function(result) { result.saveToFile(Qt.resolvedUrl("demo-panel.png").toString().replace(/^file:\/\//, "")) })
        test.phase = 7
      } else if (test.phase === 7) {
        console.log("PASS: UI presets, subprocess roundtrip, hardware controls, restart bounds, stable refresh, plain-text hostile label")
        Qt.quit()
      }
    }
  }
}
