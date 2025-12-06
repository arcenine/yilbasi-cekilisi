import eventlet
eventlet.monkey_patch()
import os
import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import google.generativeai as genai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gizli_anahtar_buraya'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- YAPAY ZEKA AYARLARI ---
# Render'daki Environment Variable'dan anahtarı çeker
api_key = os.environ.get("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None
    print("UYARI: GOOGLE_API_KEY bulunamadı. Yapay zeka çalışmayacak.")

# --- VERİ SAKLAMA ---
# { 'oda_adi': {'socket_id': 'isim', ...} }
lobiler = {}

@app.route('/')
def index():
    return render_template('index.html')

# --- LOBİ SİSTEMİ ---
@socketio.on('lobiye_katil')
def on_join(data):
    username = data['username']
    room = data['room']
    
    join_room(room)
    
    # Odayı kontrol et, yoksa oluştur
    if room not in lobiler:
        lobiler[room] = {}
    
    # Kural: Oda boşken giren ilk kişi YÖNETİCİDİR.
    is_admin = (len(lobiler[room]) == 0)

    # Kullanıcıyı kaydet
    lobiler[room][request.sid] = username
    
    # 1. Odadaki herkese güncel listeyi gönder
    emit('kullanici_listesi', list(lobiler[room].values()), to=room)
    
    # 2. Sadece odaya giren kişiye yönetici olup olmadığını söyle
    emit('admin_yetkisi', {'admin_mi': is_admin}, to=request.sid)

# --- ÇEKİLİŞ ALGORİTMASI ---
@socketio.on('cekilisi_baslat')
def on_start(data):
    room = data['room']
    
    # Odada en az 2 kişi olmalı
    if room in lobiler and len(lobiler[room]) > 1:
        katilimcilar = list(lobiler[room].values())
        random.shuffle(katilimcilar) # Listeyi karıştır
        
        eslesmeler = {}
        n = len(katilimcilar)
        
        # Dairesel eşleşme (Kimse kendine çıkmaz)
        for i in range(n):
            veren = katilimcilar[i]
            alan = katilimcilar[(i + 1) % n] 
            eslesmeler[veren] = alan
            
        # Sonuçları kişiye özel gönder
        for sid, isim in lobiler[room].items():
            kime_alacak = eslesmeler[isim]
            socketio.emit('sonuc_ekrani', {'kime': kime_alacak}, room=sid)

# --- YAPAY ZEKA HEDİYE ÖNERİSİ ---
@socketio.on('hediye_fikri_ver')
def ai_oneri(data):
    if not model:
        emit('ai_cevabi', {'cevap': "Hata: API Anahtarı sunucuda ayarlanmamış."})
        return

    ilgi_alanlari = data.get('ilgi', '')
    dil = data.get('lang', 'tr')
    
    # Promptu dile göre ayarla
    if dil == 'en':
        prompt = f"Suggest 3 creative, fun, and short gift ideas for someone who likes: {ilgi_alanlari}. Don't write explanations, just list items."
    else:
        prompt = f"Şu ilgi alanlarına sahip biri için 3 tane yaratıcı, eğlenceli ve kısa hediye önerisi yap: {ilgi_alanlari}. Açıklama yazma, sadece maddeler halinde ürünleri yaz."

    try:
        response = model.generate_content(prompt)
        temiz_cevap = response.text.replace('*', '').strip()
        emit('ai_cevabi', {'cevap': temiz_cevap})
    except Exception as e:
        print(f"AI Hatası: {e}")
        emit('ai_cevabi', {'cevap': "Üzgünüm, şu an öneri yapamıyorum. Lütfen tekrar dene."})

# --- BAŞLATMA ---
if __name__ == '__main__':
    socketio.run(app, debug=True)

