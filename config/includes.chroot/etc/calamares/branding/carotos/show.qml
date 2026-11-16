// CarotOS 1.4 kurulum slayt gosterisi (Calamares slideshowAPI 2, QtQuick).
// Turkce secilirse Turkce, diger tum dillerde Ingilizce gosterilir.
// Dil, Calamares'in Karsilama adiminda sectigi yerel ayardan (QLocale varsayilani) okunur;
// slayt gosterisi acilista yuklendigi icin onActivate'te yeniden okunur.
import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation {
    id: presentation

    property bool turkce: Qt.locale().name.substring(0, 2) === "tr"
    function t(tr, en) { return turkce ? tr : en; }
    function diliOku() { turkce = Qt.locale().name.substring(0, 2) === "tr"; }

    property color zemin: "#1b1e29"
    property color kart: "#232838"
    property color vurgu: "#5b8def"
    property color yazi: "#e6e9f2"
    property color soluk: "#9aa3b8"

    // Slaytlarin disinda beyaz kenar kalmasin
    Rectangle { anchors.fill: parent; color: presentation.zemin; z: -1 }

    function nextSlide() { presentation.goToNextSlide(); }

    Timer {
        id: advanceTimer
        interval: 12000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    // Ortak slayt duzeni: ustte simge rozeti, baslik, vurgu cizgisi, metin.
    // Satir ici bilesen dis kimlikleri (presentation) goremez: renkler burada tekrar tanimli.
    component CarotSlayt: Slide {
        id: slayt
        property string rozet: ""
        property string baslik: ""
        property string metin: ""
        readonly property color zemin: "#1b1e29"
        readonly property color kart: "#232838"
        readonly property color vurgu: "#5b8def"
        readonly property color yazi: "#e6e9f2"
        readonly property color soluk: "#9aa3b8"
        Rectangle { anchors.fill: parent; color: slayt.zemin }
        Column {
            anchors.centerIn: parent
            width: Math.min(parent.width - 80, 620)
            spacing: 18
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 76; height: 76; radius: 38
                color: slayt.kart
                border.color: slayt.vurgu
                border.width: 2
                Text {
                    anchors.centerIn: parent
                    text: slayt.rozet
                    color: slayt.vurgu
                    font.pixelSize: 34
                    font.bold: true
                }
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: slayt.baslik
                color: slayt.yazi
                font.pixelSize: 28
                font.bold: true
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 56; height: 3; radius: 2
                color: slayt.vurgu
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                lineHeight: 1.25
                text: slayt.metin
                color: slayt.soluk
                font.pixelSize: 16
            }
        }
    }

    CarotSlayt {
        rozet: "1.4"
        baslik: "CarotOS 1.4"
        metin: t("Siber güvenliğe yeni başlayanlar için hazırlanmış, Türkçe, açık kaynaklı bir Linux dağıtımı. Yüzlerce araç yerine on seçilmiş araç, her biri iyi anlatılmış.",
                 "An open-source Linux distribution made for people starting out in cybersecurity. Instead of hundreds of tools, ten carefully chosen ones, each well explained.")
    }
    CarotSlayt {
        rozet: "10"
        baslik: t("On seçilmiş araç", "Ten chosen tools")
        metin: t("Ağ tarama, paket analizi, parola denetimi, web güvenliği ve savunma: her aracın ne işe yaradığı ve nasıl kullanıldığı Karşılama uygulamasında adım adım anlatılır.",
                 "Network scanning, packet analysis, password auditing, web security and defence: what every tool does and how to use it is explained step by step in the Welcome app.")
    }
    CarotSlayt {
        rozet: "13"
        baslik: t("Hazır uygulamalar", "Built-in apps")
        metin: t("CarotOS Mağaza, Güvenlik Paneli, Sistem Sağlığı, USB Denetimi, Kurtarma, Carotene (virüs tarama) ve CarotPot (bal küpü) sistemle birlikte gelir.",
                 "CarotOS Store, Security Panel, System Health, USB Check, Recovery, Carotene (antivirus scanner) and CarotPot (honeypot) come with the system.")
    }
    CarotSlayt {
        rozet: "✓"
        baslik: t("İlk girişte Karşılama", "Welcome on first login")
        metin: t("Kurulum bitince bilgisayarı yeniden başlatın. İlk girişte Karşılama sihirbazı açılır ve sizi adım adım yönlendirir. Sorular için: carotos.org",
                 "When the installation finishes, restart the computer. The Welcome wizard opens on first login and guides you step by step. Questions: carotos.org")
    }

    // Sayfa noktalari
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18
        spacing: 10
        z: 10
        Repeater {
            model: presentation.slides.length
            Rectangle {
                width: index === presentation.currentSlide ? 22 : 8
                height: 8; radius: 4
                color: index === presentation.currentSlide ? presentation.vurgu : "#3a4157"
            }
        }
    }

    Component.onCompleted: diliOku()
    function onActivate() { diliOku(); }
    function onLeave() { }
}
