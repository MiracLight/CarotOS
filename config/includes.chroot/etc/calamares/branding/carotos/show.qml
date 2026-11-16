// CarotOS 1.4 kurulum slayt gosterisi (Calamares slideshowAPI 2, QtQuick).
// Turkce secilirse Turkce, diger tum dillerde Ingilizce gosterilir. Dil, Calamares'in
// Karsilama adiminda sectigi yerel ayardan (QLocale varsayilani) onActivate'te okunur.
// Simgeler bu dizindeki s-*.png dosyalaridir (sistem simge yoluna baglanmaz).
// Qt 6 ozellikleri ithal surumune gore acar (2.0'da Image.mipmap yok, dosya hic yuklenmez)
import QtQuick 2.15;
import calamares.slideshow 1.0;

Presentation {
    id: presentation

    property bool turkce: Qt.locale().name.substring(0, 2) === "tr"
    function t(tr, en) { return turkce ? tr : en; }
    function diliOku() { turkce = Qt.locale().name.substring(0, 2) === "tr"; }

    readonly property int sure: 11000
    readonly property bool canli: presentation.activatedInCalamares

    function nextSlide() { presentation.goToNextSlide(); }

    Timer {
        id: advanceTimer
        interval: presentation.sure
        running: presentation.canli
        repeat: true
        onTriggered: nextSlide()
    }

    // ------------------------------------------------------------------ arka plan
    Item {
        id: zemin
        anchors.fill: parent
        z: -1
        clip: true

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#11152a" }
                GradientStop { position: 0.55; color: "#161c35" }
                GradientStop { position: 1.0; color: "#1d2648" }
            }
        }

        // Yumusak isik lekeleri (radyal degrade, yavasca kayar)
        Canvas {
            id: isik1
            width: zemin.width * 0.9; height: width
            x: -width * 0.45; y: -height * 0.5
            opacity: 0.55
            onPaint: {
                var c = getContext("2d"); c.reset();
                var g = c.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width / 2);
                g.addColorStop(0, "rgba(91,141,239,0.55)"); g.addColorStop(1, "rgba(91,141,239,0)");
                c.fillStyle = g; c.fillRect(0, 0, width, height);
            }
            SequentialAnimation on x {
                running: presentation.canli; loops: Animation.Infinite
                NumberAnimation { to: -isik1.width * 0.30; duration: 12000; easing.type: Easing.InOutSine }
                NumberAnimation { to: -isik1.width * 0.45; duration: 12000; easing.type: Easing.InOutSine }
            }
        }
        Canvas {
            id: isik2
            width: zemin.width * 0.8; height: width
            x: zemin.width - width * 0.55; y: zemin.height - height * 0.45
            opacity: 0.45
            onPaint: {
                var c = getContext("2d"); c.reset();
                var g = c.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width / 2);
                g.addColorStop(0, "rgba(140,92,255,0.45)"); g.addColorStop(1, "rgba(140,92,255,0)");
                c.fillStyle = g; c.fillRect(0, 0, width, height);
            }
            SequentialAnimation on y {
                running: presentation.canli; loops: Animation.Infinite
                NumberAnimation { to: zemin.height - isik2.height * 0.60; duration: 14000; easing.type: Easing.InOutSine }
                NumberAnimation { to: zemin.height - isik2.height * 0.45; duration: 14000; easing.type: Easing.InOutSine }
            }
        }

        // Kaplumbaga kabugu motifi: yavas donen altigen cizgiler
        Repeater {
            model: [ { x: 0.88, y: 0.16, b: 150, s: 70000 }, { x: 0.08, y: 0.86, b: 210, s: 90000 },
                     { x: 0.72, y: 0.92, b: 90, s: 55000 } ]
            Canvas {
                width: modelData.b; height: modelData.b
                x: zemin.width * modelData.x - width / 2
                y: zemin.height * modelData.y - height / 2
                opacity: 0.10
                onPaint: {
                    var c = getContext("2d"); c.reset();
                    c.strokeStyle = "#8fb3ff"; c.lineWidth = 2;
                    c.beginPath();
                    for (var i = 0; i < 6; i++) {
                        var a = Math.PI / 3 * i - Math.PI / 6;
                        var px = width / 2 + (width / 2 - 2) * Math.cos(a);
                        var py = height / 2 + (height / 2 - 2) * Math.sin(a);
                        if (i === 0) c.moveTo(px, py); else c.lineTo(px, py);
                    }
                    c.closePath(); c.stroke();
                }
                RotationAnimation on rotation {
                    running: presentation.canli; loops: Animation.Infinite
                    from: 0; to: 360; duration: modelData.s
                }
            }
        }

        // Yukari suzulen kucuk parcaciklar
        Repeater {
            model: 18
            Rectangle {
                id: parca
                property real hiz: 16000 + (index * 2711) % 14000
                width: 2 + index % 3; height: width; radius: width / 2
                color: index % 4 === 0 ? "#b49bff" : "#8fb3ff"
                opacity: 0.18 + (index % 5) * 0.06
                x: (index * 137) % Math.max(1, zemin.width)
                y: zemin.height + 10
                SequentialAnimation on y {
                    running: presentation.canli; loops: Animation.Infinite
                    PauseAnimation { duration: (index * 977) % 9000 }
                    NumberAnimation { from: zemin.height + 10; to: -10; duration: parca.hiz }
                }
            }
        }
    }

    // ------------------------------------------------------------------ slayt duzeni
    // Satir ici bilesen dis kimlikleri (presentation) goremez: renkler burada tanimli.
    component CarotSlayt: Slide {
        id: slayt
        property string etiket: ""
        property string baslik: ""
        property string metin: ""
        property var simgeler: []          // bu dizindeki png adlari (1 ya da 3)
        property var cipler: []            // kucuk etiketler (arac adlari gibi)
        property string isaret: ""         // simge yoksa altigenin icindeki yazi
        readonly property color vurgu: "#5b8def"
        readonly property color vurguAcik: "#8fb3ff"
        readonly property color yazi: "#eef1f8"
        readonly property color soluk: "#a9b2c8"

        onVisibleChanged: if (visible) giris.restart()

        ParallelAnimation {
            id: giris
            NumberAnimation { target: gorsel; property: "opacity"; from: 0; to: 1; duration: 650; easing.type: Easing.OutCubic }
            NumberAnimation { target: gorsel; property: "scale"; from: 0.78; to: 1; duration: 800; easing.type: Easing.OutBack }
            SequentialAnimation {
                PauseAnimation { duration: 150 }
                ParallelAnimation {
                    NumberAnimation { target: metinKutu; property: "opacity"; from: 0; to: 1; duration: 650; easing.type: Easing.OutCubic }
                    NumberAnimation { target: kayma; property: "x"; from: 46; to: 0; duration: 750; easing.type: Easing.OutCubic }
                }
            }
            SequentialAnimation {
                PauseAnimation { duration: 450 }
                NumberAnimation { target: cizgi; property: "width"; from: 0; to: 64; duration: 600; easing.type: Easing.OutCubic }
            }
            SequentialAnimation {
                PauseAnimation { duration: 600 }
                NumberAnimation { target: ciplerKutu; property: "opacity"; from: 0; to: 1; duration: 700 }
            }
        }

        Row {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -12
            spacing: 44

            // Sol: parlayan altigen uzerinde simge(ler), etrafinda donen yay
            Item {
                id: gorsel
                width: 210; height: 210
                anchors.verticalCenter: parent.verticalCenter

                Canvas {
                    id: halka
                    anchors.fill: parent
                    onPaint: {
                        var c = getContext("2d"); c.reset();
                        c.lineWidth = 3; c.lineCap = "round";
                        var r = width / 2 - 4;
                        var renk = ["rgba(143,179,255,0.85)", "rgba(180,155,255,0.6)", "rgba(91,141,239,0.5)"];
                        for (var i = 0; i < 3; i++) {
                            c.strokeStyle = renk[i];
                            c.beginPath();
                            c.arc(width / 2, height / 2, r, i * 2.1, i * 2.1 + 1.1);
                            c.stroke();
                        }
                    }
                    RotationAnimation on rotation {
                        running: slayt.visible; loops: Animation.Infinite
                        from: 0; to: 360; duration: 18000
                    }
                }

                Canvas {
                    id: altigen
                    anchors.centerIn: parent
                    width: 172; height: 172
                    onPaint: {
                        var c = getContext("2d"); c.reset();
                        var g = c.createLinearGradient(0, 0, width, height);
                        g.addColorStop(0, "#2a3560"); g.addColorStop(1, "#1a2140");
                        c.beginPath();
                        for (var i = 0; i < 6; i++) {
                            var a = Math.PI / 3 * i - Math.PI / 6;
                            var px = width / 2 + (width / 2 - 3) * Math.cos(a);
                            var py = height / 2 + (height / 2 - 3) * Math.sin(a);
                            if (i === 0) c.moveTo(px, py); else c.lineTo(px, py);
                        }
                        c.closePath();
                        c.fillStyle = g; c.fill();
                        c.strokeStyle = "rgba(143,179,255,0.55)"; c.lineWidth = 2; c.stroke();
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: slayt.simgeler.length === 0
                    text: slayt.isaret
                    color: slayt.vurguAcik
                    font.pixelSize: 54; font.bold: true; font.family: "monospace"
                }

                Repeater {
                    model: slayt.simgeler
                    Image {
                        readonly property int n: slayt.simgeler.length
                        readonly property real aci: -Math.PI / 2 + index * 2 * Math.PI / Math.max(1, n)
                        width: n > 1 ? 66 : 108; height: width
                        x: gorsel.width / 2 - width / 2 + (n > 1 ? 40 * Math.cos(aci) : 0)
                        y: gorsel.height / 2 - height / 2 + (n > 1 ? 40 * Math.sin(aci) : 0)
                        source: modelData
                        fillMode: Image.PreserveAspectFit
                        smooth: true; mipmap: true
                    }
                }
            }

            // Sag: etiket, baslik, cizgi, metin, cipler
            Column {
                id: metinKutu
                width: Math.min(slayt.width - gorsel.width - 44 - 70, 470)
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                transform: Translate { id: kayma }

                Rectangle {
                    width: etiketYazi.implicitWidth + 22; height: 24; radius: 12
                    color: "#223064"; border.color: "#3d5fb8"; border.width: 1
                    Text {
                        id: etiketYazi
                        anchors.centerIn: parent
                        // Yerel ayara gore: Turkcede i -> İ ("GÜVENLİK PANELİ")
                        text: slayt.etiket.toLocaleUpperCase()
                        color: slayt.vurguAcik
                        font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.6
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: slayt.baslik
                    color: slayt.yazi
                    font.pixelSize: 30; font.bold: true
                }
                Rectangle {
                    id: cizgi
                    width: 64; height: 3; radius: 2
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: "#5b8def" }
                        GradientStop { position: 1.0; color: "#b49bff" }
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    lineHeight: 1.3
                    text: slayt.metin
                    color: slayt.soluk
                    font.pixelSize: 16
                }
                Flow {
                    id: ciplerKutu
                    width: parent.width
                    spacing: 7
                    visible: slayt.cipler.length > 0
                    Repeater {
                        model: slayt.cipler
                        Rectangle {
                            width: cipYazi.implicitWidth + 18; height: 26; radius: 13
                            color: "#1f2747"; border.color: "#34437a"; border.width: 1
                            Text {
                                id: cipYazi
                                anchors.centerIn: parent
                                text: modelData
                                color: "#c9d6ff"
                                font.pixelSize: 12; font.family: "monospace"
                            }
                        }
                    }
                }
            }
        }
    }

    // ------------------------------------------------------------------ slaytlar
    CarotSlayt {
        etiket: "CarotOS 1.4"
        baslik: t("Kurulum başladı", "Installation has started")
        metin: t("Bu birkaç dakika sürer. Bu arada kurduğun sistemde neler olduğuna bir göz at.",
                 "This takes a few minutes. Meanwhile, have a look at what comes with the system you are installing.")
        simgeler: ["logo.png"]
    }
    CarotSlayt {
        etiket: t("Güvenlik Paneli", "Security Panel")
        baslik: t("On araç, tek pencere", "Ten tools, one window")
        metin: t("Yüzlerce araç yerine en çok kullanılan on tanesi geliyor. Hepsini Güvenlik Paneli'nden komut ezberlemeden çalıştırabilirsin.",
                 "Instead of hundreds of tools you get the ten that get used the most. You can run all of them from the Security Panel without memorising commands.")
        simgeler: ["s-panel.png"]
        cipler: ["nmap", "tcpdump", "tshark", "aircrack-ng", "nikto", "sqlmap", "john", "hydra", "ufw", "fail2ban"]
    }
    CarotSlayt {
        etiket: t("Karşılama", "Welcome")
        baslik: t("İlk girişte seni karşılar", "It greets you on first login")
        metin: t("Neyi öğrenmek istediğini seçersin, Karşılama gerisini sırayla anlatır. Toplam 31 sayfa, istediğin yerden devam edebilirsin.",
                 "You choose what you want to learn and Welcome explains the rest in order. There are 31 pages and you can pick up wherever you left off.")
        simgeler: ["s-karsilama.png"]
    }
    CarotSlayt {
        etiket: "Former · GSD"
        baslik: t("Okumak yerine izle", "Watch instead of reading")
        metin: t("Former her aracın ekranını animasyonla adım adım gösterir. Tanımadığın bir terim çıkarsa GSD sözlüğünde 197 terimin sade bir açıklaması var.",
                 "Former shows each tool's screen step by step with animations. If you run into a term you don't know, the GSD dictionary explains 197 of them in plain words.")
        simgeler: ["s-former.png", "s-gsd.png"]
    }
    CarotSlayt {
        etiket: t("Komut Açıklayıcı", "Command Explainer")
        baslik: t("Bu komut ne yapıyor?", "What does this command do?")
        metin: t("Terminalde bir komut yaz ve Enter yerine Alt+E'ye bas. Komut çalıştırılmadan her parçasının ne işe yaradığı açıklanır.",
                 "Type a command in the terminal and press Alt+E instead of Enter. Each part of it is explained without the command being run.")
        isaret: ">_"
        cipler: ["Alt+E", "nmap -sV 192.168.1.0/24"]
    }
    CarotSlayt {
        etiket: "Poligon"
        baslik: t("Pratik yapacak bir yer", "A place to practise")
        metin: t("Öğretmen görevleri hazırlar, öğrenciler kendi bilgisayarından çözer. Her şey yerel ağda kalır, kimsenin gerçek sistemine dokunmazsın.",
                 "The teacher prepares tasks and students solve them from their own computers. Everything stays on the local network and nobody's real system is touched.")
        simgeler: ["s-poligon.png"]
    }
    CarotSlayt {
        etiket: t("Koruma", "Protection")
        baslik: t("Önce kendi bilgisayarın", "Your own computer first")
        metin: t("Carotene dosyaları virüse karşı tarar. USB Denetimi takılan belleğe sen açmadan bakar. Sistem Sağlığı 24 ayarı kontrol edip eksik olanı söyler.",
                 "Carotene scans your files for viruses. USB Check looks at a flash drive before you open it. System Health goes through 24 settings and tells you what is missing.")
        simgeler: ["s-carotene.png", "s-usb.png", "s-saglik.png"]
    }
    CarotSlayt {
        etiket: "CarotPot"
        baslik: t("Saldırganı izle", "Watch the attacker")
        metin: t("CarotPot yerel ağda sahte servisler açar ve onlara bağlanmaya çalışan herkesi kaydeder. Bir saldırının gerçekte nasıl göründüğünü kendin görürsün.",
                 "CarotPot opens fake services on your local network and logs everyone who tries to connect. You get to see what an attack really looks like.")
        simgeler: ["s-carotpot.png"]
    }
    CarotSlayt {
        etiket: t("Kurtarma", "Recovery")
        baslik: t("Bozarsan geri dön", "Break it, then go back")
        metin: t("Kurtarma, sistemin o anki halini bir kurtarma noktası olarak saklar. Bir ayarı kurcalayıp işler ters giderse o noktaya dönersin.",
                 "Recovery saves the current state of the system as a restore point. If you tinker with a setting and things go wrong, you go back to it.")
        simgeler: ["s-kurtarma.png"]
    }
    CarotSlayt {
        etiket: t("CarotOS Mağaza", "CarotOS Store")
        baslik: t("220 uygulama, açıklamasıyla", "220 apps, each explained")
        metin: t("Mağaza'da her uygulamanın ne işe yaradığı yazar. Beğendiğini kurarsın, işine yaramayanı aynı yerden kaldırırsın.",
                 "The Store tells you what each app is for. Install the ones you like and remove the ones you don't need from the same place.")
        simgeler: ["s-magaza.png"]
    }
    CarotSlayt {
        etiket: t("Son adım", "Last step")
        baslik: t("Kurulum bitince", "When it finishes")
        metin: t("Bilgisayarı yeniden başlat ve az önce oluşturduğun kullanıcıyla giriş yap. Takıldığın bir yer olursa carotos.org'a bak.",
                 "Restart the computer and log in with the user you just created. If you get stuck, take a look at carotos.org.")
        simgeler: ["logo.png"]
    }

    // ------------------------------------------------------------------ alt bant
    Item {
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 44
        z: 10

        Row {
            anchors.centerIn: parent
            spacing: 8
            Repeater {
                model: presentation.slides.length
                Rectangle {
                    width: index === presentation.currentSlide ? 26 : 8
                    height: 8; radius: 4
                    color: index === presentation.currentSlide ? "#5b8def" : "#33406b"
                    Behavior on width { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                }
            }
        }
        // Bir sonraki slayta kalan sure
        Rectangle {
            anchors.left: parent.left; anchors.bottom: parent.bottom
            height: 2; color: "#5b8def"; opacity: 0.7
            NumberAnimation on width {
                id: ilerleme
                running: presentation.canli
                from: 0; to: presentation.width; duration: presentation.sure
            }
        }
    }

    onCurrentSlideChanged: ilerleme.restart()

    Component.onCompleted: diliOku()
    function onActivate() { diliOku(); ilerleme.restart(); }
    function onLeave() { }
}
