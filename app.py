from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gizli_anahtar'
socketio = SocketIO(app)

# Lobideki kullanıcıları tutmak için basit bir sözlük (Prodüksiyonda veritabanı önerilir)
# Format: {'lobi_kodu': {'socket_id': 'KullanıcıAdı'}}
lobiler = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('lobiye_katil')
def on_join(data):
    username = data['username']
    room = data['room']
    
    join_room(room)
    
    if room not in lobiler:
        lobiler[room] = {}
    

    is_admin = (len(lobiler[room]) == 0)

   
    lobiler[room][request.sid] = username
    
   
    emit('kullanici_listesi', list(lobiler[room].values()), to=room)
    

    emit('admin_yetkisi', {'admin_mi': is_admin}, to=request.sid)

@socketio.on('cekilisi_baslat')
def on_start(data):
    room = data['room']
    
    if room in lobiler and len(lobiler[room]) > 1:
        katilimcilar = list(lobiler[room].values())
        random.shuffle(katilimcilar) # Listeyi karıştır
        
        eslesmeler = {}
        n = len(katilimcilar)
        
        # Dairesel eşleşme mantığı
        for i in range(n):
            veren = katilimcilar[i]
            alan = katilimcilar[(i + 1) % n] # Listenin sonundaki başa döner
            eslesmeler[veren] = alan
            
        # Şimdi herkese SADECE kendi sonucunu gönderelim
        # lobiler[room] içinde {sid: isim} var.
        for sid, isim in lobiler[room].items():
            kime_alacak = eslesmeler[isim]
            socketio.emit('sonuc_ekrani', {'kime': kime_alacak}, room=sid)

if __name__ == '__main__':

    socketio.run(app, debug=True)
