// CarotOS 1.4 kurulum slayt gosterisi (Calamares slideshowAPI 2, QtQuick).
// Metinler Turkce ve Ingilizce; sistem dili Turkce degilse Ingilizce gosterilir.
import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation {
    id: presentation

    property bool turkce: Qt.locale().name.substring(0, 2) === "tr"
    function t(tr, en) { return turkce ? tr : en; }

    function nextSlide() {
        presentation.goToNextSlide();
    }

    Timer {
        id: advanceTimer
        interval: 15000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b1e29" }
        Image {
            id: logo
            source: "logo.png"
            width: 140; height: 140
            fillMode: Image.PreserveAspectFit
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 40
        }
        Text {
            id: baslik1
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: logo.bottom
            anchors.topMargin: 24
            text: "CarotOS 1.4"
            color: "#5b8def"
            font.pixelSize: 30
            font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: baslik1.bottom
            anchors.topMargin: 16
            width: parent.width - 80
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "#e6e9f2"
            font.pixelSize: 16
            text: t("Siber güvenliğe yeni başlayanlar için hazırlanmış, Türkçe, açık kaynaklı bir Linux dağıtımı. Yüzlerce araç yerine on seçilmiş araç, her biri iyi anlatılmış.",
                    "An open-source Linux distribution made for people starting out in cybersecurity. Instead of hundreds of tools, ten carefully chosen ones, each well explained.")
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b1e29" }
        Text {
            id: baslik2
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 60
            text: t("On seçilmiş araç", "Ten chosen tools")
            color: "#5b8def"
            font.pixelSize: 28
            font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: baslik2.bottom
            anchors.topMargin: 24
            width: parent.width - 80
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "#e6e9f2"
            font.pixelSize: 16
            text: t("Ağ tarama, paket analizi, parola denetimi, web güvenliği ve savunma: her aracın ne işe yaradığı ve nasıl kullanıldığı Karşılama uygulamasında adım adım anlatılır.",
                    "Network scanning, packet analysis, password auditing, web security and defence: what every tool does and how to use it is explained step by step in the Welcome app.")
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b1e29" }
        Text {
            id: baslik3
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 60
            text: t("Hazır uygulamalar", "Built-in apps")
            color: "#5b8def"
            font.pixelSize: 28
            font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: baslik3.bottom
            anchors.topMargin: 24
            width: parent.width - 80
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "#e6e9f2"
            font.pixelSize: 16
            text: t("CarotOS Mağaza, Güvenlik Paneli, Sistem Sağlığı, USB Denetimi, Kurtarma, Carotene (virüs tarama) ve CarotPot (bal küpü) sistemle birlikte gelir.",
                    "CarotOS Store, Security Panel, System Health, USB Check, Recovery, Carotene (antivirus scanner) and CarotPot (honeypot) come with the system.")
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b1e29" }
        Text {
            id: baslik4
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 60
            text: t("İlk girişte Karşılama", "Welcome on first login")
            color: "#5b8def"
            font.pixelSize: 28
            font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: baslik4.bottom
            anchors.topMargin: 24
            width: parent.width - 80
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: "#e6e9f2"
            font.pixelSize: 16
            text: t("Kurulum bitince bilgisayarı yeniden başlatın. İlk girişte Karşılama sihirbazı açılır ve sizi adım adım yönlendirir. Sorular için: carotos.org",
                    "When the installation finishes, restart the computer. The Welcome wizard opens on first login and guides you step by step. Questions: carotos.org")
        }
    }

    function onActivate() { }
    function onLeave() { }
}
