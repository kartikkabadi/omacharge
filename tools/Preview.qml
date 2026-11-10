import QtQuick
import Quickshell

ShellRoot {
  id: demo
  property int step: 0
  property bool captured: false
  property var original: null
  FloatingWindow {
    id: window
    visible: true
    implicitWidth: 560
    implicitHeight: 900
    color: "#000000"
    Item {
      id: stage
      width: 560
      height: controls.implicitHeight + 105
      Rectangle { anchors.fill: parent; color: "#000000" }
      Text {
        x: 28; y: 20
        text: "OMACHARGE / VANTABLACK"
        textFormat: Text.PlainText
        color: "#ffffff"
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 14
        font.bold: true
      }
      Text {
        x: 28; y: 47
        text: "SIMULATED HARDWARE · REAL QML"
        textFormat: Text.PlainText
        color: "#7a7a7a"
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: 10
        font.letterSpacing: 1
      }
      ChargeLimitControl {
        id: controls
        x: 28; y: 76
        width: 504
        foreground: "#ffffff"
        client: String(Qt.resolvedUrl("mock-status.py")).replace(/^file:\/\//, "")
      }
    }
  }
  function capture(name) {
    if (captured) return
    captured = true
    stage.grabToImage(function(result) {
      var path = String(Qt.resolvedUrl(name)).replace(/^file:\/\//, "")
      if (!result.saveToFile(path)) { console.error("Capture failed"); Qt.quit(); return }
      console.log("SAVED " + name)
      demo.step++
      demo.captured = false
    }, Qt.size(stage.width*2, stage.height*2))
  }
  Timer {
    interval: 300
    repeat: true
    running: true
    onTriggered: {
      if (!controls.supported) return
      if (demo.step === 0) {
        demo.original=JSON.parse(JSON.stringify(controls.state))
        demo.capture("battery-care.png")
      } else if (demo.step === 1) {
        var custom=JSON.parse(JSON.stringify(demo.original))
        custom.controls[0]=Object.assign({},custom.controls[0],{id:"BAT0",driver:"dell",derived:"",gap:5,fullStart:95,end:85,start:70,stopValues:Array.from({length:46},function(_,i){return i+55}),startValues:Array.from({length:46},function(_,i){return i+50}),saved:{end:85,start:70,source:"plugin"}})
        controls.accept(JSON.stringify(custom))
        demo.step++
      } else if (demo.step === 2) {
        demo.capture("custom-limits.png")
      } else if (demo.step === 3) {
        var mode=JSON.parse(JSON.stringify(demo.original))
        mode.controls[0]=Object.assign({},mode.controls[0],{id:"platform-lenovo",driver:"lenovo",kind:"charge-types",shared:true,derived:"",end:1,start:null,stopValues:[0,1],startValues:[],careStop:1,fullStop:0,warning:"The conservation percentage is fixed by the firmware and cannot be read.",saved:{end:1,start:null,source:"plugin"}})
        controls.accept(JSON.stringify(mode))
        demo.step++
      } else if (demo.step === 4) {
        demo.capture("conservation.png")
      } else {
        console.log("PREVIEW COMPLETE")
        Qt.quit()
      }
    }
  }
}
