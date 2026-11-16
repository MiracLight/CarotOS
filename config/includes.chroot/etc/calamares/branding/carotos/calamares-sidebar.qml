/* CarotOS 1.4 Calamares kenar cubugu (branding.desc: "sidebar: qml").
   Calamares 3.3 bu dosyayi marka dizininde arar (searchQmlFile, QmlSearch::Both);
   ornek: calamares/src/calamares/calamares-sidebar.qml (GPL-3.0-or-later).
   Adimlar ViewManager modelinden gelir ("display" = Calamares'in cevirdigi adim adi).
   Renkler slayt gosterisiyle (show.qml) ayni; Branding enum'larina baglanmaz. */
import io.calamares.core 1.0

import QtQuick 2.3

Rectangle {
    id: kenar
    anchors.fill: parent
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#11152a" }
        GradientStop { position: 1.0; color: "#1a2142" }
    }

    readonly property color vurgu: "#5b8def"
    readonly property color yazi: "#eef1f8"
    readonly property color soluk: "#8791aa"
    readonly property int simdiki: ViewManager.currentStepIndex

    // Sag kenarda ince ayirici
    Rectangle {
        anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom
        width: 1; color: "#26305a"
    }

    // ---- ust: logo ve ad
    Column {
        id: ust
        anchors.top: parent.top; anchors.topMargin: 18
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 6
        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            source: "logo.png"
            width: 54; height: 54
            sourceSize.width: 108; sourceSize.height: 108
            fillMode: Image.PreserveAspectFit
            smooth: true; mipmap: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "CarotOS"
            color: kenar.yazi
            font.pixelSize: 15; font.bold: true; font.letterSpacing: 0.5
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: surumYazi.implicitWidth + 14; height: 18; radius: 9
            color: "#223064"; border.color: "#3d5fb8"; border.width: 1
            Text {
                id: surumYazi
                anchors.centerIn: parent
                text: "1.4"
                color: "#8fb3ff"
                font.pixelSize: 10; font.bold: true
            }
        }
    }

    // ---- orta: adimlar
    Column {
        id: adimlar
        anchors.top: ust.bottom; anchors.topMargin: 22
        anchors.left: parent.left; anchors.right: parent.right
        anchors.leftMargin: 8; anchors.rightMargin: 9
        spacing: 2

        Repeater {
            id: adimTekrar
            model: ViewManager
            Item {
                id: satir
                readonly property bool simdi: index === kenar.simdiki
                readonly property bool bitti: index < kenar.simdiki
                width: adimlar.width
                height: 34

                // Simdiki adim: yumusak vurgu zemini ve soldaki cizgi
                Rectangle {
                    anchors.fill: parent
                    radius: 8
                    color: kenar.vurgu
                    opacity: satir.simdi ? 0.18 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 250 } }
                }
                Rectangle {
                    anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                    width: 3; height: 18; radius: 2
                    color: kenar.vurgu
                    visible: satir.simdi
                }

                // Siradaki adima baglanan ince cizgi
                Rectangle {
                    x: daire.x + daire.width / 2 - 1
                    y: daire.y + daire.height
                    width: 2; height: satir.height - daire.height + 2
                    color: satir.bitti ? "#3d5fb8" : "#2a3358"
                    visible: index < adimTekrar.count - 1
                }

                Rectangle {
                    id: daire
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    width: 20; height: 20; radius: 10
                    color: satir.simdi ? kenar.vurgu : (satir.bitti ? "#223064" : "transparent")
                    border.width: satir.simdi ? 0 : 1.5
                    border.color: satir.bitti ? kenar.vurgu : "#3a4570"
                    Text {
                        anchors.centerIn: parent
                        text: satir.bitti ? "✓" : (index + 1)
                        color: satir.simdi ? "#ffffff" : (satir.bitti ? "#8fb3ff" : kenar.soluk)
                        font.pixelSize: satir.bitti ? 11 : 10
                        font.bold: true
                    }
                }

                Text {
                    anchors.left: daire.right; anchors.leftMargin: 10
                    anchors.right: parent.right; anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: display
                    elide: Text.ElideRight
                    color: satir.simdi ? "#ffffff" : (satir.bitti ? "#c9d6ff" : kenar.soluk)
                    font.pixelSize: 13
                    font.bold: satir.simdi
                }
            }
        }
    }

    // ---- alt: Hakkinda (ve hata ayiklama kipi aciksa Debug)
    Row {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 6

        Rectangle {
            width: hakkindaYazi.implicitWidth + 22; height: 26; radius: 13
            color: hakkindaFare.containsMouse ? "#2a3870" : "#1f2747"
            border.color: "#34437a"; border.width: 1
            Text {
                id: hakkindaYazi
                anchors.centerIn: parent
                // qsTr ceviri degisince bagi yeniden degerlendirir; Turkce katalog yoksa elle
                text: (qsTr("About") === "About" && Qt.locale().name.substring(0, 2) === "tr")
                      ? "Hakkında" : qsTr("About")
                color: "#c9d6ff"
                font.pixelSize: 11
            }
            MouseArea {
                id: hakkindaFare
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: if (typeof debug !== "undefined") debug.about()
            }
        }
        Rectangle {
            visible: typeof debug !== "undefined" && debug.enabled
            width: debugYazi.implicitWidth + 22; height: 26; radius: 13
            color: "#1f2747"; border.color: "#34437a"; border.width: 1
            Text {
                id: debugYazi
                anchors.centerIn: parent
                text: qsTr("Debug")
                color: "#c9d6ff"
                font.pixelSize: 11
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: debug.toggle()
            }
        }
    }
}
