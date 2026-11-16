// CarotOS 1.4 kurulum slayt gosterisi (Calamares slideshowAPI 2, QtQuick).
// Metinler Turkce, Ingilizce ve 7 dilde (de ru es pt ja zh fr); dil Qt.locale() ile secilir,
// listede olmayan dillerde Ingilizce gosterilir.
import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation {
    id: presentation

    property string dilKodu: Qt.locale().name.substring(0, 2)
    // t(tr, en, {de: ..., ru: ..., es: ..., pt: ..., ja: ..., zh: ..., fr: ...})
    function t(tr, en, diger) {
        if (dilKodu === "tr") return tr;
        if (diger !== undefined && diger[dilKodu] !== undefined) return diger[dilKodu];
        return en;
    }

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
                    "An open-source Linux distribution made for people starting out in cybersecurity. Instead of hundreds of tools, ten carefully chosen ones, each well explained.",
                    {de: "Eine quelloffene Linux-Distribution für alle, die in die Cybersicherheit einsteigen. Statt Hunderten von Werkzeugen zehn sorgfältig ausgewählte, jedes gut erklärt.", ru: "Дистрибутив Linux с открытым исходным кодом для тех, кто только начинает путь в кибербезопасности. Вместо сотен инструментов десять тщательно отобранных, каждый хорошо объяснён.", es: "Una distribución Linux de código abierto pensada para quienes empiezan en ciberseguridad. En lugar de cientos de herramientas, diez elegidas con cuidado, cada una bien explicada.", pt: "Uma distribuição Linux de código aberto feita para quem está começando em cibersegurança. Em vez de centenas de ferramentas, dez escolhidas com cuidado, cada uma bem explicada.", ja: "サイバーセキュリティを学び始める人のための、オープンソースの Linux ディストリビューションです。何百ものツールの代わりに、丁寧に選んだ 10 のツールを、それぞれきちんと解説します。", zh: "一款为刚入门网络安全的人准备的开源 Linux 发行版。不堆几百个工具，只精选十个，并把每一个都讲清楚。", fr: "Une distribution Linux libre conçue pour celles et ceux qui débutent en cybersécurité. Au lieu de centaines d'outils, dix outils soigneusement choisis, chacun bien expliqué."})
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b1e29" }
        Text {
            id: baslik2
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 60
            text: t("On seçilmiş araç", "Ten chosen tools",
                    {de: "Zehn ausgewählte Werkzeuge", ru: "Десять избранных инструментов", es: "Diez herramientas elegidas", pt: "Dez ferramentas escolhidas", ja: "厳選した 10 のツール", zh: "精选的十个工具", fr: "Dix outils choisis"})
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
                    "Network scanning, packet analysis, password auditing, web security and defence: what every tool does and how to use it is explained step by step in the Welcome app.",
                    {de: "Netzwerk-Scans, Paketanalyse, Passwortprüfung, Websicherheit und Verteidigung: Was jedes Werkzeug tut und wie man es benutzt, wird in der Willkommen-App Schritt für Schritt erklärt.", ru: "Сканирование сети, анализ пакетов, проверка паролей, веб-безопасность и защита: что делает каждый инструмент и как им пользоваться, шаг за шагом объясняется в приложении «Добро пожаловать».", es: "Escaneo de redes, análisis de paquetes, auditoría de contraseñas, seguridad web y defensa: qué hace cada herramienta y cómo se usa se explica paso a paso en la aplicación Bienvenida.", pt: "Varredura de rede, análise de pacotes, auditoria de senhas, segurança web e defesa: o que cada ferramenta faz e como usá-la é explicado passo a passo no aplicativo Boas-vindas.", ja: "ネットワークスキャン、パケット分析、パスワード監査、Web セキュリティ、防御。それぞれのツールが何をするのか、どう使うのかは、「ようこそ」アプリで一歩ずつ説明されます。", zh: "网络扫描、数据包分析、密码审计、Web 安全与防御：每个工具的用途和用法，都会在“欢迎”应用中一步步讲解。", fr: "Analyse réseau, analyse de paquets, audit de mots de passe, sécurité web et défense : ce que fait chaque outil et comment l'utiliser est expliqué pas à pas dans l'application Bienvenue."})
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b1e29" }
        Text {
            id: baslik3
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 60
            text: t("Hazır uygulamalar", "Built-in apps",
                    {de: "Mitgelieferte Apps", ru: "Встроенные приложения", es: "Aplicaciones incluidas", pt: "Aplicativos incluídos", ja: "標準アプリ", zh: "内置应用", fr: "Applications intégrées"})
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
                    "CarotOS Store, Security Panel, System Health, USB Check, Recovery, Carotene (antivirus scanner) and CarotPot (honeypot) come with the system.",
                    {de: "CarotOS Store, Sicherheitspanel, Systemzustand, USB-Prüfung, Wiederherstellung, Carotene (Virenscanner) und CarotPot (Honeypot) gehören zum System.", ru: "CarotOS Магазин, Security Panel, Здоровье системы, USB Check, Восстановление, Carotene (антивирус) и CarotPot (honeypot) входят в состав системы.", es: "Tienda de CarotOS, Panel de seguridad, Salud del sistema, Revisión de USB, Recuperación, Carotene (escáner antivirus) y CarotPot (honeypot) vienen con el sistema.", pt: "Loja do CarotOS, Painel de Segurança, Saúde do Sistema, Verificação de USB, Recuperação, Carotene (antivírus) e CarotPot (honeypot) vêm com o sistema.", ja: "CarotOS ストア、セキュリティパネル、システムヘルス、USBチェック、リカバリー、Carotene(ウイルススキャナー)、CarotPot(ハニーポット)が最初から入っています。", zh: "CarotOS 商店、安全面板、系统健康、USB 检查、恢复、Carotene（病毒扫描器）和 CarotPot（蜜罐）都随系统一起提供。", fr: "Boutique CarotOS, Panneau de sécurité, Santé du système, Contrôle USB, Récupération, Carotene (antivirus) et CarotPot (pot de miel) sont fournis avec le système."})
        }
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#1b1e29" }
        Text {
            id: baslik4
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 60
            text: t("İlk girişte Karşılama", "Welcome on first login",
                    {de: "Willkommen bei der ersten Anmeldung", ru: "Приветствие при первом входе", es: "Bienvenida en el primer inicio de sesión", pt: "Boas-vindas no primeiro login", ja: "初回ログイン時のようこそ", zh: "首次登录时的欢迎向导", fr: "Bienvenue à la première connexion"})
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
                    "When the installation finishes, restart the computer. The Welcome wizard opens on first login and guides you step by step. Questions: carotos.org",
                    {de: "Wenn die Installation fertig ist, starte den Computer neu. Bei der ersten Anmeldung öffnet sich der Willkommens-Assistent und führt dich Schritt für Schritt. Fragen: carotos.org", ru: "Когда установка закончится, перезагрузи компьютер. При первом входе откроется мастер приветствия и шаг за шагом всё покажет. Вопросы: carotos.org", es: "Cuando termine la instalación, reinicia el ordenador. En el primer inicio de sesión se abre el asistente de bienvenida y te guía paso a paso. Preguntas: carotos.org", pt: "Quando a instalação terminar, reinicie o computador. No primeiro login, o assistente de boas-vindas é aberto e orienta você passo a passo. Dúvidas: carotos.org", ja: "インストールが終わったらコンピューターを再起動してください。最初のログイン時に「ようこそ」ウィザードが開き、一歩ずつ案内します。質問はこちら: carotos.org", zh: "安装完成后请重启电脑。首次登录时会打开欢迎向导，一步步带你上手。有问题请访问：carotos.org", fr: "Quand l'installation est terminée, redémarre l'ordinateur. À la première connexion, l'assistant de bienvenue s'ouvre et te guide pas à pas. Questions : carotos.org"})
        }
    }

    function onActivate() { }
    function onLeave() { }
}
