import ast
import contextlib
import difflib
import html
import importlib
import io
import json
import os
import random
import re
import secrets
import shutil
import socket
import string
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

# İsteğe bağlı kütüphane kontrolleri
try:
    import pyttsx3
    TTS_ENGINE = pyttsx3.init()
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except Exception:
    SR_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPL_AVAILABLE = True
except Exception:
    MPL_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False

# Mobil Web Sunucusu İçin Flask Kontrolü
try:
    from flask import Flask, jsonify, request, render_template_string
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False

# ==============================================================================
# SİSTEM KODLAMASI VE ÇEVRE AYARLARI
# ==============================================================================
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

MEMORY_FILE = Path(__file__).with_name("klavye_hafiza.json")
APP_VERSION = "39.0.0-SEAMLESS-CONTEXT"

DEFAULT_MEMORY = {
    "name": "Kullanıcı",
    "favorite_topics": [],
    "notes": ["Örnek Not: v39.0 Kesintisiz Bağlam ve Hafıza aktif edildi."],
    "snippets": [
        {"title": "Tkinter Şablonu", "code": "import tkinter as tk\nroot = tk.Tk()\nroot.mainloop()"},
        {"title": "Mobil Sunucu Testi", "code": "print('Mobil API aktif.')"}
    ],
    "favorites": ["Örnek Favori: Gelişmiş Türkçe Semantik Analiz motoru harika çalışıyor."],
    "logs": ["Sistem v39.0 Seamless Context Ultimate ile başlatıldı."],
    "conversation": [],
    "knowledge_base": {
        "tarih": {"value": "Tarih, insanlığın geçmişteki olaylarını tarafsız ve belgeli olarak inceleyen bilim dalıdır.", "updated_at": "Güvenilir Kaynak"},
        "bilim": {"value": "Bilim, evrenin yapısını gözlem ve deney yöntemleriyle inceleyen sistematik bilgi bütünüdür.", "updated_at": "Güvenilir Kaynak"}
    },
    "learned_questions": {
        "klavye ai nedir": "Klavye AI; geçmiş konuşmaları hatırlayan, cümlenin altındaki asıl niyeti anlayan ve tüm ofis araçlarını barındıran nihai asistandır."
    },
    "kanban": {
        "todo": ["Derin Türkçe anlama yeteneğini test et", "Sohbet bağlamı hafızasını dene"],
        "doing": ["Doğal Dil İşleme (NLP) optimizasyonu"],
        "done": ["Aktif Öğrenme", "Uzun Süreli Hafıza"]
    },
    "journal": [],
    "passwords": [],
    "reminders": [],
    "macros": [{"key": "Alt+Shift+H", "text": "Klavye AI ile hızlı yanıt verilmiştir."}],
    "rss_feeds": ["https://news.ycombinator.com/rss"],
    "preferences": {"tone": "samimi", "language": "tr", "theme": "dark"},
    "api_key": "",
    "api_provider": "OpenAI",
    "daily_goals": ["Cümleleri yüzeysel okuma, anlamını kavra.", "Geçmiş konuşmayı asla unutma."],
}

def load_memory() -> dict:
    default = json.loads(json.dumps(DEFAULT_MEMORY))
    try:
        if MEMORY_FILE.exists():
            with MEMORY_FILE.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, dict):
                default.update(loaded)
    except Exception:
        pass
    return default

def save_memory(memory: dict):
    try:
        data = memory.copy()
        conv = data.get("conversation", [])
        if len(conv) > 100: data["conversation"] = conv[-100:]
        logs = data.get("logs", [])
        if len(logs) > 100: data["logs"] = logs[-100:]
        with MEMORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except Exception:
        pass

def log_system_event(memory: dict, message: str):
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    memory.setdefault("logs", []).append(f"[{timestamp}] {message}")
    save_memory(memory)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ==============================================================================
# 🧠 YEREL TÜRKÇE NLP VE NORMALİZASYON
# ==============================================================================
def normalize_turkish_text(text: str) -> str:
    if not text: return ""
    text = text.replace('İ', 'i').replace('I', 'ı')
    text = text.lower()
    replacements = {'â': 'a', 'î': 'i', 'û': 'u'}
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r'\s+', ' ', text)
    return text.strip("?!. ,;:()")

def speak_text(text: str):
    if TTS_AVAILABLE:
        def run():
            try:
                clean = re.sub(r'[#*`_\[\]()]+', '', text)
                TTS_ENGINE.say(clean[:300])
                TTS_ENGINE.runAndWait()
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

# ==============================================================================
# MOBİL WEB SERVER & API (FLASK)
# ==============================================================================
flask_app = None
if FLASK_AVAILABLE:
    flask_app = Flask(__name__)
    
    MOBILE_HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Klavye AI Mobil Ultimate v39</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #121212; color: #ffffff; margin: 0; padding: 15px; }
            .header { text-align: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 15px; }
            .chat-box { background: #1e1e1e; border-radius: 10px; padding: 15px; height: 350px; overflow-y: auto; margin-bottom: 15px; border: 1px solid #333; display: flex; flex-direction: column; }
            .msg { margin-bottom: 10px; padding: 10px 14px; border-radius: 8px; max-width: 85%; word-break: break-word; }
            .user { background: #007bff; align-self: flex-end; margin-left: auto; }
            .bot { background: #2d2d2d; border: 1px solid #444; align-self: flex-start; }
            .input-group { display: flex; gap: 8px; }
            input[type="text"] { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #444; background: #2d2d2d; color: #fff; font-size: 16px; }
            button { padding: 12px 20px; border-radius: 8px; border: none; background: #28a745; color: #fff; font-weight: bold; font-size: 16px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📱 Klavye AI Mobil Ultimate</h2>
            <p style="font-size: 12px; color: #888;">Gelişmiş Hafıza Modülü (v39)</p>
        </div>
        <div class="chat-box" id="chatBox">
            <div class="msg bot">Merhaba! Mobilden Klavye AI'a bağlandınız. Bütün konuşmalarımızı hatırlıyorum, önceki mesajlarımıza atıfta bulunabilirsiniz!</div>
        </div>
        <div class="input-group">
            <input type="text" id="userInput" placeholder="Mesajınızı yazın..." onkeypress="if(event.key==='Enter') sendMsg()">
            <button onclick="sendMsg()">Gönder</button>
        </div>
        <script>
            function sendMsg() {
                const inp = document.getElementById('userInput');
                const chat = document.getElementById('chatBox');
                if(!inp.value.trim()) return;
                
                const userDiv = document.createElement('div');
                userDiv.className = 'msg user';
                userDiv.innerText = inp.value;
                chat.appendChild(userDiv);
                
                const query = inp.value;
                inp.value = '';
                chat.scrollTop = chat.scrollHeight;
                
                fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({prompt: query})
                })
                .then(r => r.json())
                .then(data => {
                    const botDiv = document.createElement('div');
                    botDiv.className = 'msg bot';
                    botDiv.innerText = data.response;
                    chat.appendChild(botDiv);
                    chat.scrollTop = chat.scrollHeight;
                });
            }
        </script>
    </body>
    </html>
    """

    @flask_app.route("/")
    def index():
        return render_template_string(MOBILE_HTML_TEMPLATE)

    @flask_app.route("/api/chat", methods=["POST"])
    def api_chat():
        data = request.get_json() or {}
        prompt = data.get("prompt", "")
        mem = load_memory()
        reply = perform_precise_research(prompt, mem)
        return jsonify({"response": reply})

def start_mobile_server_thread(port=5000):
    if FLASK_AVAILABLE and flask_app:
        def run():
            flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return True
    return False

# ==============================================================================
# YARDIMCI SERVİSLER
# ==============================================================================
def clean_system_temp_files() -> str:
    temp_dir = tempfile.gettempdir()
    deleted_files = 0
    freed_bytes = 0
    try:
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                try:
                    fp = os.path.join(root, f)
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    deleted_files += 1
                    freed_bytes += size
                except Exception:
                    pass
        freed_mb = freed_bytes / (1024 * 1024)
        return f"🧹 **Sistem Temizliği Tamamlandı!**\n\n📂 **Konum:** {temp_dir}\n🗑️ **Silinen Dosya:** {deleted_files} adet\n💾 **Kazanılan Alan:** {freed_mb:.2f} MB"
    except Exception as e:
        return f"⚠️ Hata: {str(e)}"

def generate_markdown_report(memory: dict) -> str:
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    report = [
        f"# 📊 Klavye AI - Sistem Raporu (v39)",
        f"**Tarih:** {now_str} | **Kullanıcı:** {memory.get('name', 'Kullanıcı')}\n",
        "---",
        "## 📋 Kanban Durumu",
        f"- Yapılacak: {len(memory.get('kanban', {}).get('todo', []))}",
        f"- Devam Eden: {len(memory.get('kanban', {}).get('doing', []))}",
        f"- Tamamlanan: {len(memory.get('kanban', {}).get('done', []))}\n",
        "## 📝 Son Notlar",
    ]
    for note in memory.get("notes", [])[-5:]: report.append(f"- {note}")
    return "\n".join(report)

def fetch_rss_headlines() -> str:
    try:
        url = "https://news.ycombinator.com/rss"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            content = resp.read().decode("utf-8")
        titles = re.findall(r'<title>(.*?)</title>', content)[1:8]
        return "🌐 **Son Teknoloji Başlıkları (RSS):**\n\n" + "\n".join([f"• {t}" for t in titles])
    except Exception as e:
        return f"⚠️ RSS Akışı Alınamadı: {str(e)}"

def get_system_resource_info() -> str:
    if not PSUTIL_AVAILABLE: return "⚠️ 'psutil' yüklü değil."
    try:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return (
            f"💻 **Sistem Performansı (Ultimate İzleyici)**\n\n"
            f"🧠 **CPU:** %{cpu_usage}\n"
            f"📊 **RAM:** %{ram.percent} ({ram.used // (1024**2)} MB / {ram.total // (1024**2)} MB)\n"
            f"💾 **Disk:** %{disk.percent} ({disk.free // (1024**3)} GB Boş)"
        )
    except Exception as e: return f"⚠️ Hata: {str(e)}"

def translate_text_online(text: str, target_lang: str) -> str:
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([sentence[0] for sentence in data[0] if sentence[0]])
            return f"🔤 **Çeviri ({target_lang.upper()})**\n\n{translated}"
    except Exception as e: return f"⚠️ Çeviri Hatası: {str(e)}"

def organize_folder_files(folder_path: str) -> str:
    if not folder_path or not os.path.exists(folder_path): return "⚠️ Geçersiz yol."
    categories = {
        "Belgeler": [".pdf", ".docx", ".txt", ".xlsx"],
        "Görseller": [".png", ".jpg", ".jpeg", ".gif"],
        "Kurulumlar": [".exe", ".msi"],
        "Kodlar": [".py", ".js", ".html", ".json"]
    }
    moved_count = 0
    try:
        p = Path(folder_path)
        for item in p.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                target_cat = "Diğer"
                for cat, exts in categories.items():
                    if ext in exts:
                        target_cat = cat
                        break
                cat_dir = p / target_cat
                cat_dir.mkdir(exist_ok=True)
                shutil.move(str(item), str(cat_dir / item.name))
                moved_count += 1
        return f"✨ **Düzenleme Tamamlandı!** ({moved_count} dosya)"
    except Exception as e: return f"⚠️ Hata: {str(e)}"

def execute_python_code(code_str: str) -> str:
    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
            exec(code_str, {"__name__": "__main__"})
        res = output_buffer.getvalue()
        return res if res else "✅ Kod çalıştırıldı (Çıktı yok)."
    except Exception as e: return f"⚠️ Hata:\n{str(e)}"

def check_website_status(url: str) -> str:
    try:
        if not url.startswith("http"): url = "https://" + url
        start_time = datetime.now()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=7) as resp:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return f"🟢 **Online**\n🔗 {url}\n📡 Kod: {resp.status}\n⚡ Süre: {elapsed:.2f} ms"
    except Exception as e:
        return f"🔴 **Offline / Hata**\n🔗 {url}\n⚠️ {str(e)}"

def analyze_spreadsheet(file_path: str) -> str:
    if not PANDAS_AVAILABLE: return "⚠️ 'pandas' yüklü değil."
    try:
        df = pd.read_csv(file_path) if file_path.endswith(".csv") else pd.read_excel(file_path)
        return f"📊 **Tablo Analizi** ({Path(file_path).name})\n📏 **Boyut:** {df.shape[0]} Satır, {df.shape[1]} Sütun\n\n**Önizleme:**\n{df.head().to_string()}"
    except Exception as e: return f"⚠️ Hata: {str(e)}"

def generate_email_draft(topic: str, tone: str, recipient: str) -> str:
    return f"✉️ **E-Posta Taslağı**\n\n👤 **Alıcı:** {recipient}\n📌 **Konu:** {topic}\n🎨 **Ton:** {tone}\n\n---\nSayın Yetkili,\n\n{topic} hakkında bilgi arz ederim.\n\nSaygılarımla,\nKlavye AI Ultimate"

def generate_secure_password(length=14, use_symbols=True) -> str:
    alphabet = string.ascii_letters + string.digits + ("!@#$%^&*()_+-=[]{}|;:,.<>?" if use_symbols else "")
    return "".join(secrets.choice(alphabet) for _ in range(length))

def summarize_url_content(url: str) -> str:
    try:
        if not url.startswith("http"): url = "https://" + url
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html_content = resp.read().decode("utf-8", errors="ignore")
        words = re.sub(r'\s+', ' ', re.sub('<[^<]+?>', ' ', html_content)).strip().split()
        return f"🌐 **URL Özet Raporu** ({url})\n\n{' '.join(words[:140])}..."
    except Exception as e: return f"⚠️ Hata: {str(e)}"

def read_pdf_file(file_path: str) -> str:
    try:
        if not PDF_AVAILABLE: return "⚠️ 'PyPDF2' yüklü değil."
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:10]:
                if page.extract_text(): text += page.extract_text() + "\n"
        return f"📄 **PDF Analizi** ({Path(file_path).name})\n\n{' '.join(text.split()[:200])}..."
    except Exception as e: return f"⚠️ Hata: {str(e)}"

def fetch_live_weather() -> str:
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=40.75&longitude=29.82&current_weather=true"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            cw = json.loads(resp.read().decode("utf-8")).get("current_weather", {})
            return f"🌦️ **Anlık Hava Durumu (Kocaeli)**\n\n🌡️ **Sıcaklık:** {cw.get('temperature')}°C\n💨 **Rüzgar:** {cw.get('windspeed')} km/s"
    except Exception as e: return f"⚠️ Hava durumu alınamadı: {str(e)}"

def search_web_duckduckgo(query: str) -> str:
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            abstract = data.get("AbstractText", "")
            if abstract:
                return f"🌐 **Araştırma Sonucu:**\n\n{abstract}"
            
            topics = data.get("RelatedTopics", [])
            for t in topics:
                if "Text" in t:
                    return f"🌐 **Araştırma Sonucu:**\n\n{t['Text']}"
        
        wiki_url = f"https://tr.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
        req_wiki = urllib.request.Request(wiki_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_wiki, timeout=6) as resp_w:
            w_data = json.loads(resp_w.read().decode("utf-8"))
            search_results = w_data.get("query", {}).get("search", [])
            if search_results:
                title = search_results[0]["title"]
                snippet = re.sub(r'<[^<]+?>', '', search_results[0]["snippet"])
                return f"📚 **Ansiklopedik Kaynak ({title}):**\n\n{snippet}..."
    except Exception:
        pass
    return None

# ==============================================================================
# 🧠 AKILLI İLETİŞİM, DERİN NLP VE *KESİNTİSİZ BAĞLAM* MOTORU (v39 HAFIZA)
# ==============================================================================
def call_cloud_ai(prompt: str, api_key: str, provider: str = "OpenAI", history: list = None, memory_context: dict = None) -> str:
    if not api_key or len(api_key.strip()) < 5: return None
    try:
        user_name = memory_context.get("name", "Kullanıcı") if memory_context else "Kullanıcı"
        time_now = datetime.now().strftime("%H:%M")
        
        # SİSTEM PROMPTU (Yapay zekaya hafızasını kullanmasını açıkça emrediyoruz)
        system_persona = (
            f"Senin adın 'Klavye AI'. Sen sadece metin okuyan bir bot değil, son derece zeki, "
            f"söylenenin arkasındaki niyeti algılayabilen ve MÜKEMMEL BİR HAFIZAYA SAHİP bir 'Düşünce Ortağı'sın.\n"
            f"Şu anki saat: {time_now}. Hitap ettiğin kişinin adı: {user_name}.\n\n"
            
            f"🎯 DİL VE HAFIZA (NLP) MOTORU KURALLARI:\n"
            f"1. SOHBET BAĞLAMI (ÇOK ÖNEMLİ): Geçmiş mesajları asla unutma. Kullanıcı 'o nedir?', 'peki bu nasıl olur?', "
            f"'şunu açıkla' veya 'örnek ver' gibi eksik zamirler kullandığında, KESİNLİKLE geçmiş mesajlara bak ve hangi konudan bahsedildiğini anla.\n"
            f"2. NİYET OKUMA: Kullanıcının cümlesini yüzeysel okuma. Cümlenin alt metnini ve önceki konuşmayla bağlantısını kur.\n"
            f"3. YAPI VE AKICILIK: Robotik ve sıkıcı olma ('Ben bir yapay zekayım' demek kesinlikle yasaktır). Doğal, insansı, sıcak ve zeki cevaplar ver.\n"
        )
        
        messages = [{"role": "system", "content": system_persona}]
        
        # v39 HAFIZA GÜNCELLEMESİ: Hafıza limiti 6'dan 30 mesaja (15 soru-cevap) çıkarıldı!
        if history:
            for msg in history[-30:]:
                role = msg.get("role", "user")
                if role in ["user", "assistant"]:
                    messages.append({"role": role, "content": msg.get("content", "")})
        
        # TEKRAR HATASI ÇÖZÜMÜ: Eğer son mesaj zaten şu anki prompt ise, tekrar ekleme.
        if not history or history[-1].get("content") != prompt:
            messages.append({"role": "user", "content": prompt})

        # API ÇAĞRILARI
        if provider == "OpenAI":
            url = "https://api.openai.com/v1/chat/completions"
            payload = {"model": "gpt-4o-mini", "messages": messages, "temperature": 0.75}
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
                
        elif provider == "Gemini":
            url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            payload = {"model": "gemini-2.5-flash", "messages": messages, "temperature": 0.75}
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
                
    except Exception as e: return f"⚠️ API Hatası (Bulut bağlantısı koptu veya anahtar geçersiz): {str(e)}"
    return None

def perform_precise_research(query: str, memory: dict) -> str:
    if memory is None: memory = {}
    user_name = memory.get('name', 'Kullanıcı')
    raw_query = query
    clean_query = normalize_turkish_text(query)
    
    # 1. ÖĞRETME KOMUTU KONTROLÜ
    if clean_query.startswith("ogret") or ("=" in clean_query and "ogret" in clean_query):
        try:
            split_char = "=" if "=" in raw_query else ":"
            parts = raw_query.split(split_char, 1)
            q_part = parts[0].lower().replace("öğret", "").replace("ogret", "").strip(": ").strip()
            a_part = parts[1].strip()
            
            if q_part and a_part:
                norm_q = normalize_turkish_text(q_part)
                memory.setdefault("learned_questions", {})[norm_q] = a_part
                save_memory(memory)
                return f"🧠 **Yeni Bilgi Derin Hafızaya Kazındı!**\n\nArtık '{q_part}' sorusunun semantik yapısını biliyorum. Teşekkürler {user_name}!"
        except Exception:
            pass

    # 2. BİLGİ BANKASI VE KALICI HAFIZA KONTROLÜ
    kb = memory.get("knowledge_base", {})
    for key, item in kb.items():
        norm_key = normalize_turkish_text(key)
        if norm_key in clean_query: 
            val = item.get('value') if isinstance(item, dict) else item
            return f"📚 **Bilgi Bankasından Hızlı Çıkarım:**\n\n{val}"

    learned_db = memory.get("learned_questions", {})
    for l_key, l_val in learned_db.items():
        norm_l_key = normalize_turkish_text(l_key)
        if norm_l_key in clean_query or clean_query == norm_l_key: 
            return f"🛡️ **Bana Öğrettiğin Kalıcı Bilgi:**\n\n{l_val}"

    # 3. YEREL SELAMLAŞMA
    greetings = ["naber", "merhaba", "selam", "nasilsin", "gunaydin", "iyi aksamlar", "hey", "selamlar"]
    if any(g == clean_query for g in greetings) or (any(g in clean_query for g in greetings) and len(clean_query.split()) <= 4):
        hour = datetime.now().hour
        time_greeting = "Günaydın" if 5 <= hour < 12 else "Tünaydın" if 12 <= hour < 18 else "İyi akşamlar"
        responses = [
            f"{time_greeting} {user_name}! Bütün geçmiş konuşmalarımızı hatırlıyorum, sohbetimize nereden devam edelim?",
            f"Selam {user_name}! Zihnim tamamen açık. Bana anlattığın hiçbir şeyi unutmuyorum. 🚀"
        ]
        return random.choice(responses)
            
    # 4. BULUT AI BAĞLANTISI (BÜTÜN GEÇMİŞİ ALIR)
    conversation = memory.get("conversation", [])
    api_key = memory.get("api_key", "").strip()
    
    if api_key:
        cloud_reply = call_cloud_ai(raw_query, api_key, memory.get("api_provider", "OpenAI"), history=conversation, memory_context=memory)
        if cloud_reply and not cloud_reply.startswith("⚠️"): 
            return cloud_reply 
            
    # 5. YEDEK İNTERNET ARAMASI
    web_result = search_web_duckduckgo(raw_query)
    if web_result:
        return web_result
        
    return (
        f"Hmm, bu cümleyi semantik olarak inceledim ancak hafızamda veya genel web ağında **'{raw_query}'** niyetini karşılayan kesin bir veri bulamadım.\n\n"
        f"💡 **Bunu bana sen öğretebilirsin:**\n"
        f"`Öğret: {raw_query} = [Cevabın]` yazarak kalıcı hafızama ekleyebilirsin.\n"
        f"Veya Ayarlar sekmesinden API anahtarı bağlayarak sınırsız zeka modumu (Bulut AI) aktif edebilirsin!"
    )

# ==============================================================================
# MASAÜSTÜ CROSS-PLATFORM ULTIMATE ARAYÜZ (TÜM ARAÇLAR)
# ==============================================================================
class KlavyeCrossPlatformApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Klavye AI Pro Asistan v{APP_VERSION}")
        self.root.geometry("1720x1020")

        self.memory = load_memory()
        self.is_dark_mode = self.memory.get("preferences", {}).get("theme", "dark") == "dark"

        self.pomo_time = 25 * 60
        self.pomo_running = False

        self.create_main_layout()
        self.apply_theme()
        
        self.root.bind("<Control-Return>", lambda e: self.send_message_async())
        log_system_event(self.memory, "KlavyeCrossPlatformApp v39.0 Seamless Context başarıyla başlatıldı.")

    def create_main_layout(self):
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        self.info_label = ttk.Label(top_frame, text=f"🌐 Klavye AI v39.0 Kesintisiz Bağlam | Kullanıcı: {self.memory.get('name', 'Kullanıcı')}", font=("Segoe UI", 11, "bold"))
        self.info_label.pack(side=tk.LEFT)

        ttk.Button(top_frame, text="🎨 Tema", command=self.toggle_theme).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_frame, text="🧹 Temizle", command=self.clear_chat_screen).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_frame, text="💾 Dışa Aktar", command=self.export_chat).pack(side=tk.RIGHT, padx=2)
        ttk.Button(top_frame, text="📱 Mobil Sunucu", command=self.start_mobile_server).pack(side=tk.RIGHT, padx=5)

        self.status_bar = ttk.Label(self.root, text="Durum: Hazır | Sohbet Hafızası & Derin Türkçe Motoru Devrede | Tüm Kodlar Entegre", relief=tk.SUNKEN, anchor=tk.W, font=("Segoe UI", 9))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tüm 25+ Sekme (Eksiksiz Entegrasyon)
        self.chat_tab = ttk.Frame(self.notebook); self.notebook.add(self.chat_tab, text="💬 Sohbet"); self.build_chat_tab()
        self.kb_tab = ttk.Frame(self.notebook); self.notebook.add(self.kb_tab, text="📚 Bilgi Bankası"); self.build_kb_tab()
        self.mob_tab = ttk.Frame(self.notebook); self.notebook.add(self.mob_tab, text="📱 Mobil Bağlantı"); self.build_mob_tab()
        self.learn_tab = ttk.Frame(self.notebook); self.notebook.add(self.learn_tab, text="🧠 Öğrenme"); self.build_learn_tab()
        self.rem_tab = ttk.Frame(self.notebook); self.notebook.add(self.rem_tab, text="🔔 Bildirimler"); self.build_rem_tab()
        self.rep_tab = ttk.Frame(self.notebook); self.notebook.add(self.rep_tab, text="📊 Raporlar"); self.build_rep_tab()
        self.clean_tab = ttk.Frame(self.notebook); self.notebook.add(self.clean_tab, text="🧹 Temp Temizlik"); self.build_clean_tab()
        self.voice_tab = ttk.Frame(self.notebook); self.notebook.add(self.voice_tab, text="🎙️ Sesli Not"); self.build_voice_tab()
        self.rss_tab = ttk.Frame(self.notebook); self.notebook.add(self.rss_tab, text="🌐 RSS Haberler"); self.build_rss_tab()
        self.macro_tab = ttk.Frame(self.notebook); self.notebook.add(self.macro_tab, text="⌨️ Makrolar"); self.build_macro_tab()
        self.system_tab = ttk.Frame(self.notebook); self.notebook.add(self.system_tab, text="💻 Sistem"); self.build_system_tab()
        self.trans_tab = ttk.Frame(self.notebook); self.notebook.add(self.trans_tab, text="🔤 Çevirmen"); self.build_trans_tab()
        self.cleaner_tab = ttk.Frame(self.notebook); self.notebook.add(self.cleaner_tab, text="📁 Dosya Düzenleyici"); self.build_cleaner_tab()
        self.terminal_tab = ttk.Frame(self.notebook); self.notebook.add(self.terminal_tab, text="💻 Terminal"); self.build_terminal_tab()
        self.kanban_tab = ttk.Frame(self.notebook); self.notebook.add(self.kanban_tab, text="📋 Kanban"); self.build_kanban_tab()
        self.journal_tab = ttk.Frame(self.notebook); self.notebook.add(self.journal_tab, text="🔐 Günlük"); self.build_journal_tab()
        self.network_tab = ttk.Frame(self.notebook); self.notebook.add(self.network_tab, text="🌐 Ağ İzleme"); self.build_network_tab()
        self.excel_tab = ttk.Frame(self.notebook); self.notebook.add(self.excel_tab, text="📊 Excel"); self.build_excel_tab()
        self.email_tab = ttk.Frame(self.notebook); self.notebook.add(self.email_tab, text="✉️ E-Posta"); self.build_email_tab()
        self.vault_tab = ttk.Frame(self.notebook); self.notebook.add(self.vault_tab, text="🔒 Şifre Kasası"); self.build_vault_tab()
        self.pdf_tab = ttk.Frame(self.notebook); self.notebook.add(self.pdf_tab, text="📄 PDF"); self.build_pdf_tab()
        self.pomo_tab = ttk.Frame(self.notebook); self.notebook.add(self.pomo_tab, text="⏱️ Pomodoro"); self.build_pomo_tab()
        self.weather_tab = ttk.Frame(self.notebook); self.notebook.add(self.weather_tab, text="🌦️ Hava Durumu"); self.build_weather_tab()
        self.url_tab = ttk.Frame(self.notebook); self.notebook.add(self.url_tab, text="🌐 URL Özet"); self.build_url_tab()
        self.chart_tab = ttk.Frame(self.notebook); self.notebook.add(self.chart_tab, text="📊 Grafikler"); self.build_chart_tab()
        self.tasks_tab = ttk.Frame(self.notebook); self.notebook.add(self.tasks_tab, text="📋 Görevler"); self.build_tasks_tab()
        self.notes_tab = ttk.Frame(self.notebook); self.notebook.add(self.notes_tab, text="📝 Notlar"); self.build_notes_tab()
        self.snippets_tab = ttk.Frame(self.notebook); self.notebook.add(self.snippets_tab, text="💻 Kodlar"); self.build_snippets_tab()
        self.favorites_tab = ttk.Frame(self.notebook); self.notebook.add(self.favorites_tab, text="⭐ Favoriler"); self.build_favorites_tab()
        self.logs_tab = ttk.Frame(self.notebook); self.notebook.add(self.logs_tab, text="📊 Günlükler"); self.build_logs_tab()
        self.settings_tab = ttk.Frame(self.notebook); self.notebook.add(self.settings_tab, text="⚙️ Ayarlar"); self.build_settings_tab()

    # --- SOHBET ---
    def build_chat_tab(self):
        quick_frame = ttk.Frame(self.chat_tab, padding=5)
        quick_frame.pack(fill=tk.X)
        ttk.Button(quick_frame, text="⭐ Favorilere Ekle", command=self.add_to_favorites).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="📋 Son Yanıtı Kopyala", command=self.copy_last_response).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="🔊 Sesli Dinle", command=self.speak_last_response).pack(side=tk.LEFT, padx=2)

        chat_frame = ttk.Frame(self.chat_tab, padding=5)
        chat_frame.pack(fill=tk.BOTH, expand=True)
        self.chat_area = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        input_frame = ttk.Frame(self.chat_tab, padding=5)
        input_frame.pack(fill=tk.X)
        self.input_box = tk.Text(input_frame, height=3, font=("Segoe UI", 10), wrap=tk.WORD)
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ttk.Button(input_frame, text="Soru Sor (Ctrl+Enter)", command=self.send_message_async).pack(side=tk.RIGHT, fill=tk.Y)
        self.append_chat("Yapay Zeka", "Merhaba! v39 'Seamless Context' (Kesintisiz Bağlam) devrede. Artık bana 'peki o nedir?', 'önceki dediğin ne anlama geliyor?' gibi sorular sorabilirsin. Bütün geçmiş sohbetimizi aklımda tutuyorum!")

    def append_chat(self, sender: str, text: str):
        self.chat_area.config(state=tk.NORMAL)
        full_message = f"{sender}:\n{text}\n\n" + "-"*40 + "\n\n"
        self.chat_area.insert(tk.END, full_message)
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def send_message_async(self):
        text = self.input_box.get("1.0", tk.END).strip("\n")
        if not text: return
        self.input_box.delete("1.0", tk.END)
        self.append_chat("Sen", text)
        
        # Kullanıcı mesajını arayüzde gösterir göstermez hafızaya (history) ekliyoruz.
        self.memory.setdefault("conversation", []).append({"role": "user", "content": text})
        
        def task():
            reply = perform_precise_research(text, self.memory)
            if "öğret:" in text.lower() or "=" in text:
                self.root.after(0, self.refresh_learn_list)
            self.root.after(0, lambda: self.finalize_chat_response(reply))
        threading.Thread(target=task, daemon=True).start()

    def finalize_chat_response(self, reply):
        self.append_chat("Yapay Zeka", reply)
        self.memory.setdefault("conversation", []).append({"role": "assistant", "content": reply})
        save_memory(self.memory)
        self.refresh_logs_view()
        speak_text(reply)

    def speak_last_response(self):
        conv = self.memory.get("conversation", [])
        if conv:
            resps = [c.get("content") for c in conv if c.get("role") == "assistant"]
            if resps:
                speak_text(resps[-1])

    # --- BİLGİ BANKASI ---
    def build_kb_tab(self):
        frame = ttk.Frame(self.kb_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="📚 Yerel Bilgi Bankası Yönetimi", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        self.kb_listbox = tk.Listbox(frame, font=("Segoe UI", 10))
        self.kb_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        add_frame = ttk.LabelFrame(frame, text="Yeni Bilgi Ekle", padding=10)
        add_frame.pack(fill=tk.X, pady=10)
        ttk.Label(add_frame, text="Anahtar Kelime (Örn: wifi şifresi):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.kb_key_entry = ttk.Entry(add_frame, font=("Segoe UI", 10), width=35)
        self.kb_key_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(add_frame, text="Yanıt / Bilgi:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.kb_val_entry = ttk.Entry(add_frame, font=("Segoe UI", 10), width=50)
        self.kb_val_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(add_frame, text="Bilgi Bankasına Kaydet", command=self.add_to_knowledge_base).grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)
        self.refresh_kb_list()

    def add_to_knowledge_base(self):
        key = self.kb_key_entry.get().strip().lower()
        val = self.kb_val_entry.get().strip()
        if key and val:
            self.memory.setdefault("knowledge_base", {})[key] = {
                "value": val,
                "updated_at": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            save_memory(self.memory)
            self.kb_key_entry.delete(0, tk.END)
            self.kb_val_entry.delete(0, tk.END)
            self.refresh_kb_list()

    def refresh_kb_list(self):
        self.kb_listbox.delete(0, tk.END)
        for k, v in self.memory.get("knowledge_base", {}).items():
            content = v.get("value") if isinstance(v, dict) else v
            self.kb_listbox.insert(tk.END, f"🔑 [{k}] -> {content}")

    # --- ÖĞRENME MODÜLÜ ---
    def build_learn_tab(self):
        frame = ttk.Frame(self.learn_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.learn_listbox = tk.Listbox(frame, font=("Segoe UI", 10))
        self.learn_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.learn_listbox.bind("<<ListboxSelect>>", self.on_learn_select)
        self.learn_view = scrolledtext.ScrolledText(frame, height=5, font=("Segoe UI", 10), wrap=tk.WORD)
        self.learn_view.pack(fill=tk.X, pady=5)
        self.learn_view.config(state=tk.DISABLED)
        teach_frame = ttk.LabelFrame(frame, text="Yeni Bilgi Öğret", padding=10)
        teach_frame.pack(fill=tk.X, pady=10)
        self.teach_question_entry = ttk.Entry(teach_frame, font=("Segoe UI", 10), width=30)
        self.teach_question_entry.grid(row=0, column=1, padx=5, pady=2)
        self.teach_answer_entry = ttk.Entry(teach_frame, font=("Segoe UI", 10), width=50)
        self.teach_answer_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(teach_frame, text="Kaydet", command=self.add_learned_item).grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)
        self.refresh_learn_list()

    def add_learned_item(self):
        q, a = self.teach_question_entry.get().strip(), self.teach_answer_entry.get().strip()
        if q and a:
            norm_q = normalize_turkish_text(q)
            self.memory.setdefault("learned_questions", {})[norm_q] = a
            save_memory(self.memory)
            self.refresh_learn_list()

    def refresh_learn_list(self):
        self.learn_listbox.delete(0, tk.END)
        for q in self.memory.get("learned_questions", {}).keys(): self.learn_listbox.insert(tk.END, f"🛡️ {q.capitalize()}")

    def on_learn_select(self, event):
        sel = self.learn_listbox.curselection()
        if sel:
            keys = list(self.memory.get("learned_questions", {}).keys())
            if sel[0] < len(keys):
                self.learn_view.config(state=tk.NORMAL)
                self.learn_view.delete("1.0", tk.END)
                self.learn_view.insert(tk.END, self.memory.get("learned_questions", {}).get(keys[sel[0]], ""))
                self.learn_view.config(state=tk.DISABLED)

    # --- MOBİL BAĞLANTI ---
    def build_mob_tab(self):
        frame = ttk.Frame(self.mob_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="📱 Mobil Cihazlardan (Android / iOS) Bağlantı Paneli", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        ttk.Button(frame, text="🚀 Mobil Sunucuyu Başlat", command=self.start_mobile_server).pack(anchor=tk.W, pady=10)
        self.mob_status_lbl = ttk.Label(frame, text="Sunucu Durumu: Kapalı", font=("Segoe UI", 10, "bold"), foreground="red")
        self.mob_status_lbl.pack(anchor=tk.W)

    def start_mobile_server(self):
        if not FLASK_AVAILABLE:
            messagebox.showerror("Hata", "'Flask' yüklü değil. Kurulum: pip install flask")
            return
        if start_mobile_server_thread(5000):
            self.mob_status_lbl.config(text=f"Sunucu Durumu: 🟢 Aktif (http://{get_local_ip()}:5000)", foreground="green")

    # --- BİLDİRİMLER ---
    def build_rem_tab(self):
        frame = ttk.Frame(self.rem_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        input_f = ttk.Frame(frame)
        input_f.pack(fill=tk.X, pady=5)
        self.rem_entry = ttk.Entry(input_f, font=("Segoe UI", 10), width=40)
        self.rem_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(input_f, text="Ekle", command=self.add_reminder).pack(side=tk.LEFT, padx=5)
        self.rem_listbox = tk.Listbox(frame, font=("Segoe UI", 10))
        self.rem_listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        self.refresh_reminders()

    def add_reminder(self):
        text = self.rem_entry.get().strip()
        if text:
            self.memory.setdefault("reminders", []).append({"text": text, "time": datetime.now().strftime("%H:%M")})
            save_memory(self.memory)
            self.rem_entry.delete(0, tk.END)
            self.refresh_reminders()

    def refresh_reminders(self):
        self.rem_listbox.delete(0, tk.END)
        for r in self.memory.get("reminders", []): self.rem_listbox.insert(tk.END, f"⏰ [{r.get('time')}] {r.get('text')}")

    # --- RAPORLAR ---
    def build_rep_tab(self):
        frame = ttk.Frame(self.rep_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="📄 Rapor Oluştur", command=lambda: self.rep_area.insert(tk.END, generate_markdown_report(self.memory))).pack(anchor=tk.W, pady=5)
        self.rep_area = scrolledtext.ScrolledText(frame, font=("Consolas", 10), wrap=tk.WORD)
        self.rep_area.pack(fill=tk.BOTH, expand=True, pady=10)

    # --- TEMP TEMİZLİK ---
    def build_clean_tab(self):
        frame = ttk.Frame(self.clean_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="🚀 Temizliği Başlat", command=lambda: self.clean_area.insert(tk.END, clean_system_temp_files())).pack(anchor=tk.W, pady=5)
        self.clean_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 11), wrap=tk.WORD, height=10)
        self.clean_area.pack(fill=tk.BOTH, expand=True, pady=10)

    # --- SESLİ NOT ---
    def build_voice_tab(self):
        frame = ttk.Frame(self.voice_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="🎤 Konuşmayı Dinle", command=self.record_voice_note).pack(anchor=tk.W, pady=5)
        self.voice_text_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD, height=10)
        self.voice_text_area.pack(fill=tk.BOTH, expand=True, pady=10)

    def record_voice_note(self):
        if not SR_AVAILABLE: return
        def task():
            try:
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    audio = r.listen(source, timeout=5)
                text = r.recognize_google(audio, language="tr-TR")
                self.root.after(0, lambda: self.voice_text_area.insert(tk.END, f"• {text}\n"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Hata", f"Ses çözümlenemedi: {str(e)}"))
        threading.Thread(target=task, daemon=True).start()

    # --- RSS HABERLER ---
    def build_rss_tab(self):
        frame = ttk.Frame(self.rss_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="🔄 Akışı Yenile", command=self.load_rss).pack(anchor=tk.W, pady=5)
        self.rss_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD)
        self.rss_area.pack(fill=tk.BOTH, expand=True, pady=10)
        self.load_rss()

    def load_rss(self):
        def task():
            res = fetch_rss_headlines()
            self.root.after(0, lambda: [self.rss_area.delete("1.0", tk.END), self.rss_area.insert(tk.END, res)])
        threading.Thread(target=task, daemon=True).start()

    # --- MAKROLAR ---
    def build_macro_tab(self):
        frame = ttk.Frame(self.macro_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.macro_listbox = tk.Listbox(frame, font=("Consolas", 10))
        self.macro_listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        for m in self.memory.get("macros", []): self.macro_listbox.insert(tk.END, f"🔑 [{m.get('key')}] -> {m.get('text')}")

    # --- SİSTEM İZLEME ---
    def build_system_tab(self):
        frame = ttk.Frame(self.system_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        self.sys_info_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 11), wrap=tk.WORD, height=12)
        self.sys_info_area.pack(fill=tk.BOTH, expand=True, pady=10)
        ttk.Button(frame, text="🔄 Yenile", command=self.refresh_system_info).pack(anchor=tk.W)
        self.refresh_system_info()

    def refresh_system_info(self):
        self.sys_info_area.config(state=tk.NORMAL)
        self.sys_info_area.delete("1.0", tk.END)
        self.sys_info_area.insert(tk.END, get_system_resource_info())
        self.sys_info_area.config(state=tk.DISABLED)

    # --- ÇEVİRMEN ---
    def build_trans_tab(self):
        frame = ttk.Frame(self.trans_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        top_f = ttk.Frame(frame)
        top_f.pack(fill=tk.X, pady=5)
        self.trans_lang_combo = ttk.Combobox(top_f, values=["en (İngilizce)", "tr (Türkçe)", "de (Almanca)"], state="readonly", width=15)
        self.trans_lang_combo.pack(side=tk.LEFT, padx=5)
        self.trans_lang_combo.set("en (İngilizce)")
        ttk.Button(top_f, text="Çevir", command=self.run_translation).pack(side=tk.LEFT, padx=10)
        self.trans_input_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD, height=5)
        self.trans_input_area.pack(fill=tk.X, pady=5)
        self.trans_output_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD, height=8)
        self.trans_output_area.pack(fill=tk.BOTH, expand=True, pady=5)

    def run_translation(self):
        text = self.trans_input_area.get("1.0", tk.END).strip()
        lang_code = self.trans_lang_combo.get().split()[0]
        if text:
            def task():
                res = translate_text_online(text, lang_code)
                self.root.after(0, lambda: [self.trans_output_area.delete("1.0", tk.END), self.trans_output_area.insert(tk.END, res)])
            threading.Thread(target=task, daemon=True).start()

    # --- DOSYA DÜZENLEYİCİ ---
    def build_cleaner_tab(self):
        frame = ttk.Frame(self.cleaner_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="📂 Klasör Seç ve Düzenle", command=self.browse_and_organize_folder).pack(anchor=tk.W, pady=5)
        self.cleaner_result_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD)
        self.cleaner_result_area.pack(fill=tk.BOTH, expand=True, pady=10)

    def browse_and_organize_folder(self):
        path = filedialog.askdirectory()
        if path:
            def task():
                res = organize_folder_files(path)
                self.root.after(0, lambda: [self.cleaner_result_area.delete("1.0", tk.END), self.cleaner_result_area.insert(tk.END, res)])
            threading.Thread(target=task, daemon=True).start()

    # --- TERMİNAL ---
    def build_terminal_tab(self):
        frame = ttk.Frame(self.terminal_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.term_code_box = scrolledtext.ScrolledText(frame, font=("Consolas", 11), wrap=tk.WORD, height=10)
        self.term_code_box.pack(fill=tk.BOTH, expand=True, pady=5)
        self.term_code_box.insert("1.0", "print('Klavye AI Terminal Aktif!')")
        ttk.Button(frame, text="▶️ Çalıştır", command=self.run_terminal_code).pack(anchor=tk.W, pady=5)
        self.term_output_area = scrolledtext.ScrolledText(frame, font=("Consolas", 10), wrap=tk.WORD, height=6)
        self.term_output_area.pack(fill=tk.BOTH, expand=True, pady=5)

    def run_terminal_code(self):
        code = self.term_code_box.get("1.0", tk.END).strip()
        if code:
            res = execute_python_code(code)
            self.term_output_area.delete("1.0", tk.END)
            self.term_output_area.insert(tk.END, res)

    # --- KANBAN ---
    def build_kanban_tab(self):
        frame = ttk.Frame(self.kanban_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        cols_frame = ttk.Frame(frame)
        cols_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        col1 = ttk.LabelFrame(cols_frame, text="📌 Yapılacaklar", padding=10)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.kanban_todo_list = tk.Listbox(col1, font=("Segoe UI", 10))
        self.kanban_todo_list.pack(fill=tk.BOTH, expand=True, pady=5)
        col2 = ttk.LabelFrame(cols_frame, text="⚡ Devam Edenler", padding=10)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.kanban_doing_list = tk.Listbox(col2, font=("Segoe UI", 10))
        self.kanban_doing_list.pack(fill=tk.BOTH, expand=True, pady=5)
        col3 = ttk.LabelFrame(cols_frame, text="✅ Tamamlananlar", padding=10)
        col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.kanban_done_list = tk.Listbox(col3, font=("Segoe UI", 10))
        self.kanban_done_list.pack(fill=tk.BOTH, expand=True, pady=5)

        control_frame = ttk.Frame(frame, padding=5)
        control_frame.pack(fill=tk.X, pady=5)
        self.kanban_entry = ttk.Entry(control_frame, font=("Segoe UI", 10), width=40)
        self.kanban_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Ekle", command=self.add_kanban_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="➡️ İlerlet", command=self.advance_kanban_task).pack(side=tk.RIGHT, padx=5)
        self.refresh_kanban_lists()

    def add_kanban_task(self):
        t = self.kanban_entry.get().strip()
        if t:
            self.memory.setdefault("kanban", {"todo": [], "doing": [], "done": []}).setdefault("todo", []).append(t)
            save_memory(self.memory)
            self.kanban_entry.delete(0, tk.END)
            self.refresh_kanban_lists()

    def advance_kanban_task(self):
        kanban = self.memory.setdefault("kanban", {"todo": [], "doing": [], "done": []})
        if self.kanban_todo_list.curselection():
            item = kanban["todo"].pop(self.kanban_todo_list.curselection()[0])
            kanban.setdefault("doing", []).append(item)
        elif self.kanban_doing_list.curselection():
            item = kanban["doing"].pop(self.kanban_doing_list.curselection()[0])
            kanban.setdefault("done", []).append(item)
        save_memory(self.memory)
        self.refresh_kanban_lists()

    def refresh_kanban_lists(self):
        self.kanban_todo_list.delete(0, tk.END)
        self.kanban_doing_list.delete(0, tk.END)
        self.kanban_done_list.delete(0, tk.END)
        kanban = self.memory.get("kanban", {"todo": [], "doing": [], "done": []})
        for item in kanban.get("todo", []): self.kanban_todo_list.insert(tk.END, f"• {item}")
        for item in kanban.get("doing", []): self.kanban_doing_list.insert(tk.END, f"⚡ {item}")
        for item in kanban.get("done", []): self.kanban_done_list.insert(tk.END, f"✔️ {item}")

    # --- GÜNLÜK ---
    def build_journal_tab(self):
        frame = ttk.Frame(self.journal_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.journal_title_entry = ttk.Entry(frame, font=("Segoe UI", 10), width=50)
        self.journal_title_entry.pack(anchor=tk.W, pady=5)
        self.journal_text_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD, height=8)
        self.journal_text_area.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Button(frame, text="Kaydet", command=self.save_journal_entry).pack(anchor=tk.W, pady=5)
        self.journal_listbox = tk.Listbox(frame, font=("Segoe UI", 10), height=5)
        self.journal_listbox.pack(fill=tk.X, pady=5)
        self.refresh_journal_list()

    def save_journal_entry(self):
        t, c = self.journal_title_entry.get().strip(), self.journal_text_area.get("1.0", tk.END).strip()
        if t and c:
            self.memory.setdefault("journal", []).append({"title": t, "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "content": c})
            save_memory(self.memory)
            self.refresh_journal_list()

    def refresh_journal_list(self):
        self.journal_listbox.delete(0, tk.END)
        for item in self.memory.get("journal", []): self.journal_listbox.insert(tk.END, f"🔒 [{item.get('date')}] {item.get('title')}")

    # --- AĞ İZLEME ---
    def build_network_tab(self):
        frame = ttk.Frame(self.network_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        net_f = ttk.Frame(frame)
        net_f.pack(fill=tk.X, pady=5)
        self.net_url_entry = ttk.Entry(net_f, font=("Segoe UI", 10), width=40)
        self.net_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(net_f, text="Ping Testi", command=self.run_network_test).pack(side=tk.RIGHT, padx=5)
        self.net_result_area = scrolledtext.ScrolledText(frame, font=("Consolas", 10), wrap=tk.WORD, height=10)
        self.net_result_area.pack(fill=tk.BOTH, expand=True, pady=10)

    def run_network_test(self):
        url = self.net_url_entry.get().strip()
        if url:
            def task():
                res = check_website_status(url)
                self.root.after(0, lambda: [self.net_result_area.delete("1.0", tk.END), self.net_result_area.insert(tk.END, res)])
            threading.Thread(target=task, daemon=True).start()

    # --- EXCEL ---
    def build_excel_tab(self):
        frame = ttk.Frame(self.excel_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="📂 Tablo Seç (.csv / .xlsx)", command=self.browse_and_analyze_spreadsheet).pack(anchor=tk.W, pady=5)
        self.excel_result_area = scrolledtext.ScrolledText(frame, font=("Consolas", 10), wrap=tk.WORD)
        self.excel_result_area.pack(fill=tk.BOTH, expand=True, pady=10)

    def browse_and_analyze_spreadsheet(self):
        path = filedialog.askopenfilename(filetypes=[("Tablo", "*.csv *.xlsx *.xls"), ("Tüm", "*.*")])
        if path:
            def task():
                res = analyze_spreadsheet(path)
                self.root.after(0, lambda: [self.excel_result_area.delete("1.0", tk.END), self.excel_result_area.insert(tk.END, res)])
            threading.Thread(target=task, daemon=True).start()

    # --- E-POSTA ---
    def build_email_tab(self):
        frame = ttk.Frame(self.email_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        form = ttk.Frame(frame)
        form.pack(fill=tk.X, pady=5)
        ttk.Label(form, text="Alıcı:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.email_recipient_entry = ttk.Entry(form, font=("Segoe UI", 10), width=40)
        self.email_recipient_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(form, text="Konu:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.email_topic_entry = ttk.Entry(form, font=("Segoe UI", 10), width=50)
        self.email_topic_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(form, text="Ton:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.email_tone_combo = ttk.Combobox(form, values=["Resmi / Kurumsal", "Samimi / Dostane"], state="readonly")
        self.email_tone_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        self.email_tone_combo.set("Resmi / Kurumsal")
        ttk.Button(form, text="Taslak Oluştur", command=self.create_email_draft).grid(row=3, column=1, sticky=tk.E, padx=5, pady=10)
        self.email_result_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD, height=8)
        self.email_result_area.pack(fill=tk.BOTH, expand=True, pady=10)

    def create_email_draft(self):
        draft = generate_email_draft(self.email_topic_entry.get(), self.email_tone_combo.get(), self.email_recipient_entry.get())
        self.email_result_area.delete("1.0", tk.END)
        self.email_result_area.insert(tk.END, draft)

    # --- ŞİFRE KASASI ---
    def build_vault_tab(self):
        frame = ttk.Frame(self.vault_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        gen = ttk.LabelFrame(frame, text="Şifre Üretici", padding=10)
        gen.pack(fill=tk.X, pady=5)
        self.pwd_len_spin = ttk.Spinbox(gen, from_=8, to=32, width=5)
        self.pwd_len_spin.grid(row=0, column=1, padx=5, pady=2)
        self.pwd_sym_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(gen, text="Özel Karakterler", variable=self.pwd_sym_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5)
        ttk.Button(gen, text="Üret", command=self.generate_and_show_pwd).grid(row=2, column=0, padx=5, pady=5)
        self.pwd_output_entry = ttk.Entry(gen, font=("Consolas", 11), width=35)
        self.pwd_output_entry.grid(row=2, column=1, padx=5, pady=5)
        
        vault = ttk.LabelFrame(frame, text="Şifre Kasası", padding=10)
        vault.pack(fill=tk.BOTH, expand=True, pady=10)
        add_v = ttk.Frame(vault)
        add_v.pack(fill=tk.X, pady=5)
        self.vault_site_entry = ttk.Entry(add_v, width=15)
        self.vault_site_entry.pack(side=tk.LEFT, padx=2)
        self.vault_user_entry = ttk.Entry(add_v, width=15)
        self.vault_user_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(add_v, text="Ekle", command=self.add_to_vault).pack(side=tk.RIGHT, padx=5)
        self.vault_listbox = tk.Listbox(vault, font=("Consolas", 10))
        self.vault_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.refresh_vault_list()

    def generate_and_show_pwd(self):
        self.pwd_output_entry.delete(0, tk.END)
        self.pwd_output_entry.insert(0, generate_secure_password(int(self.pwd_len_spin.get()), self.pwd_sym_var.get()))

    def add_to_vault(self):
        s, u, p = self.vault_site_entry.get().strip(), self.vault_user_entry.get().strip(), self.pwd_output_entry.get().strip()
        if s and u and p:
            self.memory.setdefault("passwords", []).append({"site": s, "user": u, "pwd": p})
            save_memory(self.memory)
            self.refresh_vault_list()

    def refresh_vault_list(self):
        self.vault_listbox.delete(0, tk.END)
        for item in self.memory.get("passwords", []): self.vault_listbox.insert(tk.END, f"🔒 Site: {item.get('site')} | Kullanıcı: {item.get('user')}")

    # --- PDF ---
    def build_pdf_tab(self):
        frame = ttk.Frame(self.pdf_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Button(frame, text="📂 Belge Seç (.pdf / .txt)", command=self.browse_and_read_pdf).pack(anchor=tk.W, pady=5)
        self.pdf_result_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD)
        self.pdf_result_area.pack(fill=tk.BOTH, expand=True, pady=10)

    def browse_and_read_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF ve Metin", "*.pdf *.txt"), ("Tüm", "*.*")])
        if path:
            def task():
                res = f"📄 Rapor:\n\n{open(path, 'r', encoding='utf-8', errors='ignore').read()[:1500]}" if path.endswith(".txt") else read_pdf_file(path)
                self.root.after(0, lambda: [self.pdf_result_area.delete("1.0", tk.END), self.pdf_result_area.insert(tk.END, res)])
            threading.Thread(target=task, daemon=True).start()

    # --- POMODORO ---
    def build_pomo_tab(self):
        frame = ttk.Frame(self.pomo_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        self.pomo_timer_label = ttk.Label(frame, text="25:00", font=("Consolas", 48, "bold"))
        self.pomo_timer_label.pack(pady=20)
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Başlat", command=self.start_pomo).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Durdur", command=self.pause_pomo).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Sıfırla", command=self.reset_pomo).pack(side=tk.LEFT, padx=5)

    def start_pomo(self):
        if not self.pomo_running:
            self.pomo_running = True
            self.run_pomo_countdown()

    def pause_pomo(self): self.pomo_running = False
    def reset_pomo(self):
        self.pomo_running = False
        self.pomo_time = 25 * 60
        self.pomo_timer_label.config(text="25:00")

    def run_pomo_countdown(self):
        if self.pomo_running and self.pomo_time > 0:
            self.pomo_time -= 1
            self.pomo_timer_label.config(text=f"{self.pomo_time // 60:02d}:{self.pomo_time % 60:02d}")
            self.root.after(1000, self.run_pomo_countdown)

    # --- HAVA DURUMU ---
    def build_weather_tab(self):
        frame = ttk.Frame(self.weather_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        self.weather_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 11), height=8, wrap=tk.WORD)
        self.weather_area.pack(fill=tk.BOTH, expand=True, pady=10)
        ttk.Button(frame, text="Güncelle", command=self.load_weather_data).pack(anchor=tk.W)
        self.load_weather_data()

    def load_weather_data(self):
        def task():
            res = fetch_live_weather()
            self.root.after(0, lambda: [self.weather_area.delete("1.0", tk.END), self.weather_area.insert(tk.END, res)])
        threading.Thread(target=task, daemon=True).start()

    # --- URL ÖZET ---
    def build_url_tab(self):
        frame = ttk.Frame(self.url_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        url_input_frame = ttk.Frame(frame)
        url_input_frame.pack(fill=tk.X, pady=5)
        self.url_entry = ttk.Entry(url_input_frame, font=("Segoe UI", 10), width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(url_input_frame, text="Özetle", command=self.process_url_summary).pack(side=tk.RIGHT, padx=5)
        self.url_result_area = scrolledtext.ScrolledText(frame, font=("Segoe UI", 10), wrap=tk.WORD)
        self.url_result_area.pack(fill=tk.BOTH, expand=True, pady=10)

    def process_url_summary(self):
        url = self.url_entry.get().strip()
        if url:
            def task():
                res = summarize_url_content(url)
                self.root.after(0, lambda: [self.url_result_area.delete("1.0", tk.END), self.url_result_area.insert(tk.END, res)])
            threading.Thread(target=task, daemon=True).start()

    # --- GRAFİKLER ---
    def build_chart_tab(self):
        frame = ttk.Frame(self.chart_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="📈 Çizgi", command=lambda: self.draw_chart("line")).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="📊 Sütun", command=lambda: self.draw_chart("bar")).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🥧 Pasta", command=lambda: self.draw_chart("pie")).pack(side=tk.LEFT, padx=5)
        self.chart_frame_container = ttk.Frame(frame)
        self.chart_frame_container.pack(fill=tk.BOTH, expand=True, pady=10)
        if MPL_AVAILABLE: self.draw_chart("bar")

    def draw_chart(self, chart_type):
        if not MPL_AVAILABLE: return
        for widget in self.chart_frame_container.winfo_children(): widget.destroy()
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        cats, vals = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"], [45, 60, 75, 50, 90, 110]
        if chart_type == "line": ax.plot(cats, vals, marker="o", color="#bd93f9")
        elif chart_type == "bar": ax.bar(cats, vals, color="#50fa7b")
        elif chart_type == "pie": ax.pie(vals, labels=cats, autopct="%1.1f%%")
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # --- GÖREVLER / NOTLAR / LİSTELER ---
    def build_tasks_tab(self):
        frame = ttk.Frame(self.tasks_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.task_listbox = tk.Listbox(frame, font=("Segoe UI", 10))
        self.task_listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        self.refresh_list(self.task_listbox, self.memory.get("daily_goals", []), "• ")

    def build_notes_tab(self):
        frame = ttk.Frame(self.notes_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.notes_listbox = tk.Listbox(frame, font=("Segoe UI", 10))
        self.notes_listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        self.refresh_list(self.notes_listbox, self.memory.get("notes", []), "📝 ")

    def build_snippets_tab(self):
        frame = ttk.Frame(self.snippets_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.snippet_listbox = tk.Listbox(frame, font=("Consolas", 10))
        self.snippet_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.refresh_list(self.snippet_listbox, [s.get("title") for s in self.memory.get("snippets", [])], "💻 ")

    def build_favorites_tab(self):
        frame = ttk.Frame(self.favorites_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.fav_listbox = tk.Listbox(frame, font=("Segoe UI", 10))
        self.fav_listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        self.refresh_list(self.fav_listbox, [f[:60] + "..." for f in self.memory.get("favorites", [])], "⭐ ")

    def build_logs_tab(self):
        frame = ttk.Frame(self.logs_tab, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        self.logs_text = scrolledtext.ScrolledText(frame, font=("Consolas", 9), wrap=tk.WORD)
        self.logs_text.pack(fill=tk.BOTH, expand=True, pady=10)
        self.refresh_logs_view()

    def refresh_list(self, listbox, items, prefix):
        listbox.delete(0, tk.END)
        for i in items: listbox.insert(tk.END, f"{prefix}{i}")

    def refresh_logs_view(self):
        self.logs_text.config(state=tk.NORMAL)
        self.logs_text.delete("1.0", tk.END)
        for log in self.memory.get("logs", []): self.logs_text.insert(tk.END, f"{log}\n")
        self.logs_text.config(state=tk.DISABLED)

    # --- AYARLAR ---
    def build_settings_tab(self):
        frame = ttk.Frame(self.settings_tab, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Kullanıcı Adı:").pack(anchor=tk.W)
        self.name_entry = ttk.Entry(frame, font=("Segoe UI", 10))
        self.name_entry.pack(fill=tk.X, pady=(0, 10))
        self.name_entry.insert(0, self.memory.get("name", "Kullanıcı"))
        ttk.Label(frame, text="AI Sağlayıcı:").pack(anchor=tk.W)
        self.provider_combo = ttk.Combobox(frame, values=["OpenAI", "Gemini"], state="readonly", font=("Segoe UI", 10))
        self.provider_combo.pack(fill=tk.X, pady=(0, 10))
        self.provider_combo.set(self.memory.get("api_provider", "OpenAI"))
        ttk.Label(frame, text="API Anahtarı (Bulut NLP İçin Şart):").pack(anchor=tk.W)
        self.api_key_entry = ttk.Entry(frame, show="*", font=("Segoe UI", 10))
        self.api_key_entry.pack(fill=tk.X, pady=(0, 15))
        self.api_key_entry.insert(0, self.memory.get("api_key", ""))
        ttk.Button(frame, text="Kaydet", command=self.save_settings).pack(anchor=tk.W)

    def save_settings(self):
        self.memory["name"] = self.name_entry.get().strip() or "Kullanıcı"
        self.memory["api_key"] = self.api_key_entry.get().strip()
        self.memory["api_provider"] = self.provider_combo.get().strip()
        save_memory(self.memory)
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi!")

    def apply_theme(self):
        text_bg, text_fg = ("#282a36", "#f8f8f2") if self.is_dark_mode else ("#ffffff", "#000000")
        self.chat_area.config(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        self.input_box.config(bg=text_bg, fg=text_fg, insertbackground=text_fg)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.memory.setdefault("preferences", {})["theme"] = "dark" if self.is_dark_mode else "light"
        save_memory(self.memory)
        self.apply_theme()

    def clear_chat_screen(self):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def copy_last_response(self):
        conv = self.memory.get("conversation", [])
        if conv:
            resps = [c.get("content") for c in conv if c.get("role") == "assistant"]
            if resps:
                self.root.clipboard_clear()
                self.root.clipboard_append(resps[-1])

    def add_to_favorites(self):
        conv = self.memory.get("conversation", [])
        if conv:
            resps = [c.get("content") for c in conv if c.get("role") == "assistant"]
            if resps and resps[-1] not in self.memory.setdefault("favorites", []):
                self.memory["favorites"].append(resps[-1])
                save_memory(self.memory)

    def export_chat(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w", encoding="utf-8") as f: f.write(self.chat_area.get("1.0", tk.END))


if __name__ == "__main__":
    root = tk.Tk()
    app = KlavyeCrossPlatformApp(root)
    root.mainloop()
    