import QtQuick
import QtQuick.Controls as Controls
import qs.Commons
import qs.Commons as Commons

Controls.ComboBox {
  id: root
  property color foreground: Commons.Color.foreground
  property string fontFamily: Style.font.family
  implicitHeight: Style.space(34)
  leftPadding: Style.space(10)
  rightPadding: Style.space(28)
  font.family: fontFamily
  font.pixelSize: Style.font.bodySmall
  opacity: enabled ? 1 : 0.5

  background: Rectangle {
    color: root.down ? Style.pressedFillFor(root.foreground, Commons.Color.accent)
      : root.hovered ? Style.hoverFillFor(root.foreground, Commons.Color.accent) : Commons.Color.background
    border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, root.activeFocus ? 0.8 : 0.4)
    border.width: 1
    radius: Style.cornerRadius
  }
  contentItem: Text {
    textFormat: Text.PlainText
    text: root.displayText
    color: root.foreground
    font: root.font
    verticalAlignment: Text.AlignVCenter
    elide: Text.ElideRight
  }
  indicator: Text {
    textFormat: Text.PlainText
    text: "▾"
    color: root.foreground
    font: root.font
    anchors.right: parent.right
    anchors.rightMargin: Style.space(10)
    anchors.verticalCenter: parent.verticalCenter
  }
  delegate: Controls.ItemDelegate {
    required property var modelData
    required property int index
    width: root.width
    implicitHeight: Style.space(30)
    highlighted: root.highlightedIndex === index
    contentItem: Text {
      textFormat: Text.PlainText
      text: Commons.I18n.formatNumber(Number(modelData)) + "%"
      color: root.foreground
      font: root.font
      verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
      color: parent.highlighted ? Style.hoverFillFor(root.foreground, Commons.Color.accent) : Commons.Color.background
      radius: Math.min(4, Style.cornerRadius)
    }
  }
  popup: Controls.Popup {
    focus: true
    y: root.height + Style.space(4)
    width: root.width
    padding: 1
    implicitHeight: Math.min(list.contentHeight + 2, Style.space(240))
    background: Rectangle {
      color: Commons.Color.background
      border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.4)
      border.width: 1
      radius: Style.cornerRadius
    }
    contentItem: ListView {
      id: list
      clip: true
      model: root.popup.visible ? root.delegateModel : null
      currentIndex: root.highlightedIndex
      boundsBehavior: Flickable.StopAtBounds
      Controls.ScrollIndicator.vertical: Controls.ScrollIndicator { }
    }
  }
}
