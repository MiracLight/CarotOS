#!/usr/bin/env python3
"""
CarotOS Security Panel
A GTK3 desktop application that gives common security tools a guided,
bilingual interface with light/dark theming and optional privileged
execution via pkexec.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import subprocess
import shutil
import threading
import shlex
import signal
import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "carotos-panel")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")
DEFAULT_SETTINGS = {"language": "tr", "theme": "dark"}


def load_settings():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return {**DEFAULT_SETTINGS, **data}
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
    except Exception:
        pass


STRINGS = {
    "app_title": {"tr": "CarotOS Güvenlik Paneli", "en": "CarotOS Security Panel"},
    "sidebar_title": {"tr": "CarotOS", "en": "CarotOS"},
    "run": {"tr": "Çalıştır", "en": "Run"},
    "run_root": {"tr": "Root ile çalıştır", "en": "Run as root"},
    "stop": {"tr": "Durdur", "en": "Stop"},
    "clear": {"tr": "Çıktıyı temizle", "en": "Clear output"},
    "ready": {"tr": "Hazır", "en": "Ready"},
    "running": {"tr": "{tool} çalışıyor…", "en": "{tool} running…"},
    "settings": {"tr": "Ayarlar", "en": "Settings"},
    "settings_desc": {
        "tr": "Görünüm ve dil tercihlerini buradan değiştir. Değişiklikler anında uygulanır.",
        "en": "Change appearance and language here. Changes apply immediately.",
    },
    "language": {"tr": "Dil", "en": "Language"},
    "theme": {"tr": "Tema", "en": "Theme"},
    "theme_dark": {"tr": "Koyu", "en": "Dark"},
    "theme_light": {"tr": "Açık", "en": "Light"},
    "when_to_use": {"tr": "Ne zaman kullanılır", "en": "When to use it"},
    "example": {"tr": "Örnek", "en": "Example"},
    "not_found": {"tr": "'{cmd}' sistemde bulunamadı.", "en": "'{cmd}' was not found on the system."},
    "build_error": {"tr": "Komut oluşturulamadı: {err}", "en": "Could not build command: {err}"},
    "finished": {"tr": "Bitti — çıkış kodu {code}", "en": "Finished — exit code {code}"},
    "stopped": {"tr": "Durduruldu", "en": "Stopped"},
    "needs_target": {"tr": "Lütfen gerekli alanları doldur.", "en": "Please fill in the required fields."},
    "root_hint": {
        "tr": "Bu araç yönetici yetkisi gerektirir. \"Root ile çalıştır\" düğmesini kullan; şifre penceresi açılır.",
        "en": "This tool needs administrator rights. Use \"Run as root\"; a password dialog will appear.",
    },
    "choose_file": {"tr": "Dosya seç", "en": "Choose file"},
    "firewall": {"tr": "Güvenlik Duvarı", "en": "Firewall"},
    "firewall_desc": {
        "tr": "Sisteme gelen bağlantıları engelleyip engellemeyeceğini buradan aç/kapat.",
        "en": "Turn incoming connection blocking on or off here.",
    },
    "firewall_on": {"tr": "Etkin", "en": "Enabled"},
    "firewall_off": {"tr": "Kapalı", "en": "Disabled"},
    "firewall_unknown": {"tr": "Durum bilinmiyor — yenile", "en": "Status unknown — refresh"},
    "firewall_checking": {"tr": "Kontrol ediliyor…", "en": "Checking…"},
    "firewall_updating": {"tr": "Güncelleniyor…", "en": "Updating…"},
    "refresh": {"tr": "Yenile", "en": "Refresh"},
}


def T(key, lang, **kw):
    text = STRINGS.get(key, {}).get(lang, key)
    return text.format(**kw) if kw else text


def _v(values, key, default=""):
    raw = values.get(key, "")
    if isinstance(raw, str):
        return raw.strip()
    return raw if raw is not None else default


_EXTRA_BIN_DIRS = ["/usr/sbin", "/sbin", "/usr/local/sbin"]


def resolve_binary(name):
    """Find a command even if it lives in /usr/sbin and isn't on the
    normal user's PATH (common for ufw, fail2ban-client, etc.)."""
    found = shutil.which(name)
    if found:
        return found
    for d in _EXTRA_BIN_DIRS:
        candidate = os.path.join(d, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


TOOLS = [
    {
        "name": "nmap",
        "tagline": {"tr": "Ağ ve port keşfi", "en": "Network & port discovery"},
        "what": {
            "tr": "Bir ağdaki cihazları, açık portları ve çalışan servisleri haritalar.",
            "en": "Maps devices on a network, their open ports, and running services.",
        },
        "when": {
            "tr": "Bir sunucunun hangi kapıları açık, arkasında ne çalışıyor bilmek istediğinde.",
            "en": "When you want to know which doors a host has open and what runs behind them.",
        },
        "example": {"tr": "Kendi makineni tara: hedef = 127.0.0.1", "en": "Scan your own machine: target = 127.0.0.1"},
        "needs_root": False,
        "root_optional": True,
        "fields": [
            ("target", {"tr": "Hedef (IP veya alan adı)", "en": "Target (IP or hostname)"}, "text", "",
             {"tr": "örn. 192.168.1.1", "en": "e.g. 192.168.1.1"}),
            ("scan", {"tr": "Tarama türü", "en": "Scan type"}, "combo",
             [{"tr": "Hızlı", "en": "Quick"},
              {"tr": "Tüm portlar", "en": "All ports"},
              {"tr": "Servis / sürüm", "en": "Service / version"},
              {"tr": "Gizli SYN (root)", "en": "Stealth SYN (root)"}], None),
        ],
        "build": lambda v: (
            ["nmap", "-T4", "-F", _v(v, "target")] if _v(v, "scan_key") == 0 else
            ["nmap", "-p-", _v(v, "target")] if _v(v, "scan_key") == 1 else
            ["nmap", "-sV", _v(v, "target")] if _v(v, "scan_key") == 2 else
            ["nmap", "-sS", _v(v, "target")]
        ),
        "requires": ["target"],
    },
    {
        "name": "tcpdump",
        "tagline": {"tr": "Ağ paketi yakalama", "en": "Network packet capture"},
        "what": {
            "tr": "Ağ arayüzünden geçen ham paketleri yakalar ve ekrana döker.",
            "en": "Captures raw packets passing through a network interface and prints them.",
        },
        "when": {
            "tr": "Bir bağlantının gerçekten ne trafiği ürettiğini kendi gözünle görmek istediğinde.",
            "en": "When you want to see with your own eyes what traffic a connection produces.",
        },
        "example": {"tr": "eth0 üzerinde 50 paket yakala", "en": "Capture 50 packets on eth0"},
        "needs_root": True,
        "fields": [
            ("iface", {"tr": "Arayüz", "en": "Interface"}, "text", "eth0",
             {"tr": "örn. eth0, wlan0", "en": "e.g. eth0, wlan0"}),
            ("count", {"tr": "Paket sayısı", "en": "Packet count"}, "text", "50", None),
            ("filter", {"tr": "Filtre (opsiyonel)", "en": "Filter (optional)"}, "text", "",
             {"tr": "örn. port 80", "en": "e.g. port 80"}),
        ],
        "build": lambda v: ["tcpdump", "-i", _v(v, "iface", "eth0"), "-c", _v(v, "count", "50")]
        + (shlex.split(_v(v, "filter")) if _v(v, "filter") else []),
        "requires": ["iface"],
    },
    {
        "name": "tshark",
        "tagline": {"tr": "Wireshark — terminal sürümü", "en": "Wireshark — terminal edition"},
        "what": {
            "tr": "Wireshark'ın komut satırı hâli; paketleri yakalar ve protokol ayrıntısıyla çözümler.",
            "en": "The command-line side of Wireshark; captures packets and dissects them with protocol detail.",
        },
        "when": {
            "tr": "tcpdump'tan daha okunur, protokol bazında ayrıştırılmış çıktı istediğinde.",
            "en": "When you want output that's more readable and dissected per protocol than tcpdump.",
        },
        "example": {"tr": "eth0 üzerinde 50 paket çözümle", "en": "Dissect 50 packets on eth0"},
        "needs_root": True,
        "fields": [
            ("iface", {"tr": "Arayüz", "en": "Interface"}, "text", "eth0",
             {"tr": "örn. eth0, wlan0", "en": "e.g. eth0, wlan0"}),
            ("count", {"tr": "Paket sayısı", "en": "Packet count"}, "text", "50", None),
        ],
        "build": lambda v: ["tshark", "-i", _v(v, "iface", "eth0"), "-c", _v(v, "count", "50")],
        "requires": ["iface"],
    },
    {
        "name": "aircrack-ng",
        "tagline": {"tr": "Kablosuz ağ güvenlik testi", "en": "Wireless security testing"},
        "what": {
            "tr": "Yakalanmış kablosuz el sıkışma dosyalarını analiz eder ve WEP/WPA anahtarlarını test eder.",
            "en": "Analyses captured wireless handshake files and tests WEP/WPA keys.",
        },
        "when": {
            "tr": "Kendi Wi-Fi ağının parola dayanıklılığını sınamak istediğinde.",
            "en": "When you want to test the password strength of your own Wi-Fi network.",
        },
        "example": {"tr": "Bir .cap dosyası seç ve çözümle", "en": "Pick a .cap file and analyse it"},
        "needs_root": False,
        "fields": [
            ("capfile", {"tr": "Yakalama dosyası (.cap)", "en": "Capture file (.cap)"}, "file", "", None),
        ],
        "build": lambda v: ["aircrack-ng", _v(v, "capfile")],
        "requires": ["capfile"],
    },
    {
        "name": "nikto",
        "tagline": {"tr": "Web sunucu tarayıcı", "en": "Web server scanner"},
        "what": {
            "tr": "Bir web sunucusunu bilinen açıklar, eski yazılımlar ve riskli dosyalar için tarar.",
            "en": "Scans a web server for known vulnerabilities, outdated software, and risky files.",
        },
        "when": {
            "tr": "Kendi web sunucunun bariz güvenlik açıkları taşıyıp taşımadığını görmek istediğinde.",
            "en": "When you want to see whether your own web server carries obvious security holes.",
        },
        "example": {"tr": "Hedef = http://localhost", "en": "Target = http://localhost"},
        "needs_root": False,
        "fields": [
            ("target", {"tr": "Hedef URL / IP", "en": "Target URL / IP"}, "text", "",
             {"tr": "örn. http://localhost", "en": "e.g. http://localhost"}),
        ],
        "build": lambda v: ["nikto", "-h", _v(v, "target")],
        "requires": ["target"],
    },
    {
        "name": "sqlmap",
        "tagline": {"tr": "SQL injection testi", "en": "SQL injection testing"},
        "what": {
            "tr": "Web adreslerindeki parametreleri SQL injection açıkları için otomatik dener.",
            "en": "Automatically probes parameters in web addresses for SQL injection flaws.",
        },
        "when": {
            "tr": "Kendi web uygulamanın veritabanı girdilerini yeterince koruyup korumadığını test ederken.",
            "en": "When testing whether your own web app protects its database inputs well enough.",
        },
        "example": {"tr": "URL = http://localhost/page?id=1", "en": "URL = http://localhost/page?id=1"},
        "needs_root": False,
        "fields": [
            ("url", {"tr": "Hedef URL", "en": "Target URL"}, "text", "",
             {"tr": "örn. http://host/p?id=1", "en": "e.g. http://host/p?id=1"}),
            ("extra", {"tr": "Ek parametreler", "en": "Extra parameters"}, "text", "--batch", None),
        ],
        "build": lambda v: ["sqlmap", "-u", _v(v, "url")]
        + (shlex.split(_v(v, "extra")) if _v(v, "extra") else []),
        "requires": ["url"],
    },
    {
        "name": "john",
        "tagline": {"tr": "Parola kırma (John the Ripper)", "en": "Password cracking (John the Ripper)"},
        "what": {
            "tr": "Parola özet (hash) dosyalarını sözlük ve kaba kuvvetle çözmeye çalışır.",
            "en": "Attempts to crack password hash files with dictionaries and brute force.",
        },
        "when": {
            "tr": "Bir sistemden alınmış parola özetlerinin ne kadar zayıf olduğunu ölçerken.",
            "en": "When measuring how weak password hashes taken from a system are.",
        },
        "example": {"tr": "Hash dosyası seç, istersen kelime listesi ekle", "en": "Pick a hash file, optionally add a wordlist"},
        "needs_root": False,
        "fields": [
            ("hashfile", {"tr": "Hash dosyası", "en": "Hash file"}, "file", "", None),
            ("wordlist", {"tr": "Kelime listesi (opsiyonel)", "en": "Wordlist (optional)"}, "file", "", None),
        ],
        "build": lambda v: ["john"]
        + (["--wordlist=" + _v(v, "wordlist")] if _v(v, "wordlist") else [])
        + [_v(v, "hashfile")],
        "requires": ["hashfile"],
    },
    {
        "name": "hydra",
        "tagline": {"tr": "Oturum açma kaba kuvvet testi", "en": "Login brute-force testing"},
        "what": {
            "tr": "SSH, FTP gibi servislere kullanıcı ve parola listeleriyle giriş denemeleri yapar.",
            "en": "Tries logins against services like SSH and FTP using username and password lists.",
        },
        "when": {
            "tr": "Kendi servislerinin zayıf parolalara karşı ne kadar dayanıklı olduğunu sınarken.",
            "en": "When testing how well your own services resist weak passwords.",
        },
        "example": {"tr": "Hedef IP + servis + kullanıcı/parola listeleri", "en": "Target IP + service + user/pass lists"},
        "needs_root": False,
        "fields": [
            ("target", {"tr": "Hedef IP", "en": "Target IP"}, "text", "",
             {"tr": "örn. 192.168.1.10", "en": "e.g. 192.168.1.10"}),
            ("service", {"tr": "Servis", "en": "Service"}, "text", "ssh",
             {"tr": "örn. ssh, ftp", "en": "e.g. ssh, ftp"}),
            ("userlist", {"tr": "Kullanıcı listesi", "en": "Username list"}, "file", "", None),
            ("passlist", {"tr": "Parola listesi", "en": "Password list"}, "file", "", None),
        ],
        "build": lambda v: ["hydra", "-L", _v(v, "userlist"), "-P", _v(v, "passlist"),
                            _v(v, "target"), _v(v, "service", "ssh")],
        "requires": ["target", "userlist", "passlist"],
    },
    {
        "name": "ufw",
        "tagline": {"tr": "Güvenlik duvarı", "en": "Firewall"},
        "what": {
            "tr": "Sisteme gelen ve giden bağlantıları basit kurallarla yönetir.",
            "en": "Manages incoming and outgoing connections with simple rules.",
        },
        "when": {
            "tr": "Hangi portların açık olduğunu görmek ya da bir portu açıp kapatmak istediğinde.",
            "en": "When you want to see which ports are open, or open and close one.",
        },
        "example": {"tr": "\"Durum\" ile mevcut kuralları listele", "en": "List current rules with \"Status\""},
        "needs_root": True,
        "fields": [
            ("action", {"tr": "İşlem", "en": "Action"}, "combo",
             [{"tr": "Durum", "en": "Status"},
              {"tr": "Etkinleştir", "en": "Enable"},
              {"tr": "Devre dışı bırak", "en": "Disable"},
              {"tr": "Port izni ver", "en": "Allow port"}], None),
            ("port", {"tr": "Port (izin için)", "en": "Port (for allow)"}, "text", "",
             {"tr": "örn. 22", "en": "e.g. 22"}),
        ],
        "build": lambda v: (
            ["ufw", "status", "verbose"] if _v(v, "action_key") == 0 else
            ["ufw", "enable"] if _v(v, "action_key") == 1 else
            ["ufw", "disable"] if _v(v, "action_key") == 2 else
            ["ufw", "allow", _v(v, "port")]
        ),
        "requires": [],
    },
    {
        "name": "fail2ban",
        "tagline": {"tr": "Kaba kuvvet koruması", "en": "Brute-force protection"},
        "what": {
            "tr": "Tekrarlayan başarısız giriş denemelerini tespit edip saldıran adresleri engeller.",
            "en": "Detects repeated failed login attempts and blocks the attacking addresses.",
        },
        "when": {
            "tr": "Koruma servisinin çalışıp çalışmadığını ve hangi kuralların aktif olduğunu görmek için.",
            "en": "To see whether the protection service is running and which rules are active.",
        },
        "example": {"tr": "\"Genel durum\" ile özeti gör", "en": "See the overview with \"Overall status\""},
        "needs_root": True,
        "fields": [
            ("action", {"tr": "İşlem", "en": "Action"}, "combo",
             [{"tr": "Genel durum", "en": "Overall status"}], None),
        ],
        "build": lambda v: ["fail2ban-client", "status"],
        "requires": [],
    },
]


class ToolPage(Gtk.Box):
    def __init__(self, tool, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.tool = tool
        self.app = app
        self.widgets = {}
        self.process = None
        self.set_border_width(20)

        self.title = Gtk.Label(xalign=0)
        self.pack_start(self.title, False, False, 0)
        self.tagline = Gtk.Label(xalign=0)
        self.pack_start(self.tagline, False, False, 0)

        self.info = Gtk.Label(xalign=0)
        self.info.set_line_wrap(True)
        self.info.set_xalign(0)
        info_frame = Gtk.Frame()
        info_frame.get_style_context().add_class("info-frame")
        info_inner = Gtk.Box()
        info_inner.set_border_width(10)
        info_inner.pack_start(self.info, True, True, 0)
        info_frame.add(info_inner)
        self.pack_start(info_frame, False, False, 4)

        self.form = Gtk.Grid(column_spacing=12, row_spacing=8)
        self.pack_start(self.form, False, False, 6)
        self._build_fields()

        self.root_hint = Gtk.Label(xalign=0)
        self.root_hint.set_line_wrap(True)
        self.root_hint.get_style_context().add_class("hint-label")
        self.pack_start(self.root_hint, False, False, 0)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pack_start(btn_row, False, False, 4)

        self.run_btn = Gtk.Button()
        self.run_btn.get_style_context().add_class("suggested-action")
        self.run_btn.connect("clicked", lambda b: self.run(as_root=False))
        btn_row.pack_start(self.run_btn, False, False, 0)

        self.root_btn = Gtk.Button()
        self.root_btn.connect("clicked", lambda b: self.run(as_root=True))
        btn_row.pack_start(self.root_btn, False, False, 0)

        self.stop_btn = Gtk.Button()
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self.stop)
        btn_row.pack_start(self.stop_btn, False, False, 0)

        self.clear_btn = Gtk.Button()
        self.clear_btn.connect("clicked", lambda b: self.output_buffer.set_text(""))
        btn_row.pack_end(self.clear_btn, False, False, 0)

        self.preview = Gtk.Label(xalign=0)
        self.preview.set_selectable(True)
        self.preview.set_line_wrap(True)
        self.preview.get_style_context().add_class("preview-label")
        self.pack_start(self.preview, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_shadow_type(Gtk.ShadowType.IN)
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_cursor_visible(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.output_buffer = self.output_view.get_buffer()
        scroller.add(self.output_view)
        self.pack_start(scroller, True, True, 0)

    def _build_fields(self):
        for i, field in enumerate(self.tool["fields"]):
            key, label, kind, default, *rest = field
            placeholder = rest[0] if rest else None
            lbl = Gtk.Label(xalign=0)
            self.form.attach(lbl, 0, i, 1, 1)
            if kind == "combo":
                widget = Gtk.ComboBoxText()
                for _opt in default:
                    widget.append_text("")
                widget.set_active(0)
                options = default
            elif kind == "file":
                widget = Gtk.FileChooserButton(title="")
                widget.set_width_chars(28)
                options = None
            else:
                widget = Gtk.Entry()
                if isinstance(default, str):
                    widget.set_text(default)
                widget.set_width_chars(32)
                options = None
            self.form.attach(widget, 1, i, 1, 1)
            self.widgets[key] = {"kind": kind, "widget": widget, "label": label,
                                 "options": options, "placeholder": placeholder, "lbl": lbl}

    def retranslate(self):
        lang = self.app.lang
        t = self.tool
        self.title.set_markup(f"<span size='xx-large' weight='bold'>{t['name']}</span>")
        self.tagline.set_markup(f"<span foreground='{self.app.accent}'>{t['tagline'][lang]}</span>")
        info_markup = (
            f"{GLib.markup_escape_text(t['what'][lang])}\n\n"
            f"<b>{T('when_to_use', lang)}:</b> {GLib.markup_escape_text(t['when'][lang])}\n"
            f"<b>{T('example', lang)}:</b> {GLib.markup_escape_text(t['example'][lang])}"
        )
        self.info.set_markup(info_markup)

        for key, d in self.widgets.items():
            d["lbl"].set_text(d["label"][lang])
            if d["kind"] == "combo":
                active = d["widget"].get_active()
                d["widget"].remove_all()
                for opt in d["options"]:
                    d["widget"].append_text(opt[lang])
                d["widget"].set_active(active if active >= 0 else 0)
            elif d["kind"] == "file":
                d["widget"].set_title(T("choose_file", lang))
            else:
                if d["placeholder"]:
                    d["widget"].set_placeholder_text(d["placeholder"][lang])

        self.run_btn.set_label(T("run", lang))
        self.root_btn.set_label(T("run_root", lang))
        self.stop_btn.set_label(T("stop", lang))
        self.clear_btn.set_label(T("clear", lang))

        if t.get("needs_root"):
            self.root_hint.set_markup(f"⚠ {GLib.markup_escape_text(T('root_hint', lang))}")
            self.root_hint.show()
            self.root_btn.show()
        else:
            self.root_hint.hide()
            if t.get("root_optional"):
                self.root_btn.show()
            else:
                self.root_btn.hide()

    def _collect(self):
        values = {}
        for key, d in self.widgets.items():
            if d["kind"] == "combo":
                values[key] = d["widget"].get_active_text() or ""
                values[key + "_key"] = d["widget"].get_active()
            elif d["kind"] == "file":
                values[key] = d["widget"].get_filename() or ""
            else:
                values[key] = d["widget"].get_text()
        return values

    def run(self, as_root):
        lang = self.app.lang
        values = self._collect()
        for req in self.tool.get("requires", []):
            if not _v(values, req):
                self.append(f"[!] {T('needs_target', lang)}\n")
                return
        try:
            cmd = self.tool["build"](values)
        except Exception as exc:
            self.append(f"[!] {T('build_error', lang, err=exc)}\n")
            return
        cmd = [c for c in cmd if c != ""]
        if not cmd:
            return
        resolved = resolve_binary(cmd[0])
        if resolved is None:
            self.append(f"[!] {T('not_found', lang, cmd=cmd[0])}\n")
            return
        cmd[0] = resolved
        self.run_as_root = as_root
        if as_root:
            cmd = ["pkexec"] + cmd
        self.preview.set_markup("<tt>$ " + GLib.markup_escape_text(" ".join(shlex.quote(c) for c in cmd)) + "</tt>")
        self.output_buffer.set_text("")
        self.run_btn.set_sensitive(False)
        self.root_btn.set_sensitive(False)
        self.stop_btn.set_sensitive(True)
        self.app.set_status(T("running", lang, tool=self.tool["name"]))
        threading.Thread(target=self._worker, args=(cmd,), daemon=True).start()

    def _worker(self, cmd):
        lang = self.app.lang
        try:
            # start_new_session: araci kendi surec grubunda baslatir; boylece
            # pkexec ile root olarak calisan alt sureci de sinyalle ulasabiliriz
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, start_new_session=True)
            for line in self.process.stdout:
                GLib.idle_add(self.append, line)
            self.process.wait()
            GLib.idle_add(self.append, f"\n[{T('finished', lang, code=self.process.returncode)}]\n")
        except Exception as exc:
            GLib.idle_add(self.append, f"[!] {exc}\n")
        finally:
            GLib.idle_add(self._done)

    def _done(self):
        self.run_btn.set_sensitive(True)
        self.root_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)
        self.app.set_status(T("ready", self.app.lang))

    def stop(self, _b):
        if not (self.process and self.process.poll() is None):
            return
        lang = self.app.lang
        try:
            pgid = os.getpgid(self.process.pid)
        except OSError:
            pgid = None

        if getattr(self, "run_as_root", False):
            # pkexec ile baslatilan araclar root'a aittir; normal kullanici
            # onlari dogrudan olduremez. kill'i de root ile calistiririz.
            # Surec grubunun tamamina TERM gonderilir (negatif PGID).
            target = f"-{pgid}" if pgid else str(self.process.pid)
            try:
                subprocess.run(["pkexec", "kill", "-TERM", target],
                               timeout=30)
            except Exception as exc:
                self.append(f"[!] {exc}\n")
        else:
            try:
                if pgid:
                    os.killpg(pgid, signal.SIGTERM)
                else:
                    self.process.terminate()
            except OSError:
                self.process.terminate()

        self.append(f"\n[{T('stopped', lang)}]\n")

    def append(self, text):
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, text)
        mark = self.output_buffer.create_mark(None, self.output_buffer.get_end_iter(), False)
        self.output_view.scroll_to_mark(mark, 0, False, 0, 0)
        return False


class SettingsPage(Gtk.Box):
    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.app = app
        self.set_border_width(20)
        self.title = Gtk.Label(xalign=0)
        self.pack_start(self.title, False, False, 0)
        self.desc = Gtk.Label(xalign=0)
        self.desc.set_line_wrap(True)
        self.pack_start(self.desc, False, False, 0)
        grid = Gtk.Grid(column_spacing=16, row_spacing=14)
        grid.set_margin_top(10)
        self.pack_start(grid, False, False, 0)
        self.lang_label = Gtk.Label(xalign=0)
        grid.attach(self.lang_label, 0, 0, 1, 1)
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append("tr", "Türkçe")
        self.lang_combo.append("en", "English")
        self.lang_combo.set_active_id(app.lang)
        self.lang_combo.connect("changed", self.on_lang)
        grid.attach(self.lang_combo, 1, 0, 1, 1)
        self.theme_label = Gtk.Label(xalign=0)
        grid.attach(self.theme_label, 0, 1, 1, 1)
        self.theme_combo = Gtk.ComboBoxText()
        self.theme_combo.append("dark", "")
        self.theme_combo.append("light", "")
        self.theme_combo.set_active_id(app.theme)
        self.theme_combo.connect("changed", self.on_theme)
        grid.attach(self.theme_combo, 1, 1, 1, 1)

        # --- Firewall section ---
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(10)
        sep.set_margin_bottom(4)
        self.pack_start(sep, False, False, 0)

        self.fw_title = Gtk.Label(xalign=0)
        self.pack_start(self.fw_title, False, False, 0)
        self.fw_desc = Gtk.Label(xalign=0)
        self.fw_desc.set_line_wrap(True)
        self.pack_start(self.fw_desc, False, False, 0)

        fw_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        fw_row.set_margin_top(8)
        self.pack_start(fw_row, False, False, 0)

        self.fw_switch = Gtk.Switch()
        self.fw_switch.set_sensitive(False)
        self.fw_switch.connect("state-set", self.on_switch)
        fw_row.pack_start(self.fw_switch, False, False, 0)

        self.fw_status_label = Gtk.Label(xalign=0)
        fw_row.pack_start(self.fw_status_label, False, False, 0)

        self.fw_refresh_btn = Gtk.Button()
        self.fw_refresh_btn.connect("clicked", lambda b: self.refresh_firewall())
        fw_row.pack_start(self.fw_refresh_btn, False, False, 0)

        self._fw_state = None
        self.retranslate()
        GLib.idle_add(self.refresh_firewall)

    def refresh_firewall(self):
        self.fw_switch.set_sensitive(False)
        self.fw_status_label.set_text(T("firewall_checking", self.app.lang))
        threading.Thread(target=self._check_firewall_worker, daemon=True).start()
        return False

    def _check_firewall_worker(self):
        ufw_path = resolve_binary("ufw") or "/usr/sbin/ufw"
        try:
            result = subprocess.run(
                ["pkexec", ufw_path, "status"],
                capture_output=True, text=True, timeout=30,
            )
            active = "Status: active" in result.stdout
            GLib.idle_add(self._apply_firewall_state, active, True)
        except Exception:
            GLib.idle_add(self._apply_firewall_state, None, False)

    def _apply_firewall_state(self, active, known):
        self._fw_state = active if known else None
        self.fw_switch.handler_block_by_func(self.on_switch)
        if known:
            self.fw_switch.set_active(bool(active))
            self.fw_switch.set_sensitive(True)
            lang = self.app.lang
            self.fw_status_label.set_text(T("firewall_on" if active else "firewall_off", lang))
        else:
            self.fw_switch.set_sensitive(False)
            self.fw_status_label.set_text(T("firewall_unknown", self.app.lang))
        self.fw_switch.handler_unblock_by_func(self.on_switch)
        return False

    def on_switch(self, switch, state):
        self.fw_switch.set_sensitive(False)
        self.fw_status_label.set_text(T("firewall_updating", self.app.lang))
        threading.Thread(target=self._set_firewall_worker, args=(state,), daemon=True).start()
        return True

    def _set_firewall_worker(self, enable):
        ufw_path = resolve_binary("ufw") or "/usr/sbin/ufw"
        try:
            action = "enable" if enable else "disable"
            subprocess.run(["pkexec", ufw_path, action], capture_output=True, text=True, timeout=30)
        except Exception:
            pass
        GLib.idle_add(self.refresh_firewall)

    def retranslate(self):
        lang = self.app.lang
        self.title.set_markup(f"<span size='xx-large' weight='bold'>{T('settings', lang)}</span>")
        self.desc.set_text(T("settings_desc", lang))
        self.lang_label.set_text(T("language", lang))
        self.theme_label.set_text(T("theme", lang))
        active = self.theme_combo.get_active_id()
        self.theme_combo.handler_block_by_func(self.on_theme)
        self.theme_combo.remove_all()
        self.theme_combo.append("dark", T("theme_dark", lang))
        self.theme_combo.append("light", T("theme_light", lang))
        self.theme_combo.set_active_id(active or self.app.theme)
        self.theme_combo.handler_unblock_by_func(self.on_theme)

        self.fw_title.set_markup(f"<span size='large' weight='bold'>{T('firewall', lang)}</span>")
        self.fw_desc.set_text(T("firewall_desc", lang))
        self.fw_refresh_btn.set_label(T("refresh", lang))
        if self._fw_state is not None:
            self.fw_status_label.set_text(T("firewall_on" if self._fw_state else "firewall_off", lang))
        elif hasattr(self, "fw_status_label"):
            pass

    def on_lang(self, combo):
        new = combo.get_active_id()
        if new and new != self.app.lang:
            self.app.set_language(new)

    def on_theme(self, combo):
        new = combo.get_active_id()
        if new and new != self.app.theme:
            self.app.set_theme(new)


class PanelApp(Gtk.Window):
    ACCENT = "#87979B"

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.lang = self.settings["language"]
        self.theme = self.settings["theme"]
        self.accent = self.ACCENT
        self.set_default_size(1000, 660)
        self.connect("destroy", Gtk.main_quit)

        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(root)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.set_size_request(230, -1)
        sidebar.get_style_context().add_class("sidebar")
        root.pack_start(sidebar, False, False, 0)

        self.header = Gtk.Label(xalign=0)
        self.header.set_margin_top(16)
        self.header.set_margin_start(14)
        self.header.set_margin_bottom(12)
        sidebar.pack_start(self.header, False, False, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("nav-list")
        self.listbox.connect("row-selected", self.on_selected)
        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        nav_scroll.add(self.listbox)
        sidebar.pack_start(nav_scroll, True, True, 0)

        self.status = Gtk.Label(xalign=0)
        self.status.set_margin_start(12)
        self.status.set_margin_top(6)
        self.status.set_margin_bottom(8)
        self.status.get_style_context().add_class("status-label")
        sidebar.pack_start(self.status, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        root.pack_start(self.stack, True, True, 0)

        self.pages = {}
        for tool in TOOLS:
            page = ToolPage(tool, self)
            self.stack.add_named(page, tool["name"])
            self.pages[tool["name"]] = page

        self.settings_page = SettingsPage(self)
        self.stack.add_named(self.settings_page, "__settings__")

        self._build_nav()
        self.apply_theme()
        self.retranslate()

        first = self.listbox.get_row_at_index(0)
        if first:
            self.listbox.select_row(first)

    def _build_nav(self):
        for tool in TOOLS:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            box.set_border_width(9)
            name = Gtk.Label(xalign=0)
            name.set_markup(f"<b>{tool['name']}</b>")
            tag = Gtk.Label(xalign=0)
            tag.get_style_context().add_class("nav-sub")
            box.pack_start(name, False, False, 0)
            box.pack_start(tag, False, False, 0)
            row.add(box)
            row.kind = "tool"
            row.tool = tool
            row.tag_label = tag
            self.listbox.add(row)

        sep_row = Gtk.ListBoxRow()
        sep_row.set_selectable(False)
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        sep_row.add(sep)
        self.listbox.add(sep_row)

        settings_row = Gtk.ListBoxRow()
        sbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sbox.set_border_width(9)
        self.settings_nav_label = Gtk.Label(xalign=0)
        sbox.pack_start(self.settings_nav_label, False, False, 0)
        settings_row.add(sbox)
        settings_row.kind = "settings"
        self.listbox.add(settings_row)

    def on_selected(self, _lb, row):
        if row is None or not hasattr(row, "kind"):
            return
        if row.kind == "tool":
            self.stack.set_visible_child_name(row.tool["name"])
        elif row.kind == "settings":
            self.stack.set_visible_child_name("__settings__")

    def set_status(self, text):
        self.status.set_text(text)

    def set_language(self, lang):
        self.lang = lang
        self.settings["language"] = lang
        save_settings(self.settings)
        self.retranslate()

    def set_theme(self, theme):
        self.theme = theme
        self.settings["theme"] = theme
        save_settings(self.settings)
        self.apply_theme()

    def retranslate(self):
        self.set_title(T("app_title", self.lang))
        self.header.set_markup(f"<span size='large' weight='bold'>{T('sidebar_title', self.lang)}</span>")
        self.status.set_text(T("ready", self.lang))
        for row in self.listbox.get_children():
            if getattr(row, "kind", None) == "tool":
                row.tag_label.set_text(row.tool["tagline"][self.lang])
            elif getattr(row, "kind", None) == "settings":
                self.settings_nav_label.set_markup(f"<b>⚙  {T('settings', self.lang)}</b>")
        for page in self.pages.values():
            page.retranslate()
        self.settings_page.retranslate()

    def apply_theme(self):
        if self.theme == "dark":
            bg = "#1f2325"; sidebar = "#2b2f31"; fg = "#e6e6e6"
            sub = "#9aa4a8"; field = "#2b2f31"; info_bg = "#262b2d"
        else:
            bg = "#f4f5f6"; sidebar = "#e4e7e9"; fg = "#1f2325"
            sub = "#5c666a"; field = "#ffffff"; info_bg = "#eceef0"

        Gtk.Settings.get_default().set_property(
            "gtk-application-prefer-dark-theme", self.theme == "dark")

        css = f"""
        window {{ background-color: {bg}; color: {fg}; }}
        .sidebar {{ background-color: {sidebar}; }}
        .sidebar label {{ color: {fg}; }}
        .nav-sub {{ color: {sub}; font-size: 90%; }}
        .status-label {{ color: {sub}; font-size: 90%; }}
        .nav-list row:selected {{ background-color: {self.ACCENT}; }}
        .nav-list row:selected label {{ color: #ffffff; }}
        .info-frame {{ background-color: {info_bg}; border-radius: 6px; }}
        .info-frame label {{ color: {fg}; }}
        .hint-label {{ color: #c9a227; font-size: 92%; }}
        .preview-label {{ color: {sub}; font-size: 90%; }}
        textview {{ background-color: {field}; color: {fg}; }}
        textview text {{ background-color: {field}; color: {fg}; }}
        entry {{ background-color: {field}; color: {fg}; }}
        label {{ color: {fg}; }}
        """
        self.css_provider.load_from_data(css.encode())


if __name__ == "__main__":
    app = PanelApp()
    app.show_all()
    for page in app.pages.values():
        page.retranslate()
    Gtk.main()
