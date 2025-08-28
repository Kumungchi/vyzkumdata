# DEPLOYMENT_GUIDE.md

# 🚀 Průvodce produkčním nasazením aplikace

## 📋 Přehled aplikace

**Emoční profil aplikace** je Streamlit aplikace pro zobrazování osobních reportů účastníků studie emočního hodnocení slov. Každý účastník má přístup pouze ke svým datům přes unikátní URL s jeho ID.

## ⚙️ Technické požadavky

### Minimální systémové požadavky:
- **Python**: 3.8+
- **RAM**: 2GB (4GB doporučeno)
- **Disk**: 1GB volného místa
- **CPU**: 2 cores (4 doporučeno)

### Závislosti:
```bash
pip install -r requirements.txt
```

## 🔧 Instalace a konfigurace

### 1. Příprava prostředí

```bash
# Clone repository
git clone <your-repo-url>
cd vyzkumdata

# Vytvoření virtuálního prostředí
python -m venv venv
source venv/bin/activate  # Linux/Mac
# nebo
venv\Scripts\activate  # Windows

# Instalace závislostí
pip install -r requirements.txt
```

### 2. Konfigurace dat

Ujistěte se, že máte v složce `data/`:
- `vybrana_slova_30.csv` - baseline data se sloupci: Valence, Arousal
- `hand_dataset.csv` - data účastníků se sloupci: ID, Term, Pos X, Pos Y, Pos Z, First reaction time
- `users.csv` (volitelné) - metadata o uživatelích

### 3. Testování před nasazením

```bash
# Spuštění unit testů
python test_app.py

# Lokální testování
streamlit run app.py

# Test konkrétního uživatele
# http://localhost:8501?ID=PCZ001
```

## 🌐 Nasazení možnosti

### Option 1: Streamlit Cloud (Doporučeno pro rychlé nasazení)

1. **Nahrajte kód na GitHub**
2. **Přihlaste se na [share.streamlit.io](https://share.streamlit.io)**
3. **Připojte GitHub repository**
4. **Nastavte environment variables** (pokud potřebujete)
5. **Deploy!**

**Výhody:**
- ✅ Rychlé nasazení
- ✅ Automatické updates z GitHubu
- ✅ SSL certifikát zdarma
- ✅ Basic monitoring

### Option 2: Docker container

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"]
```

```bash
# Build a spuštění
docker build -t emotional-profile-app .
docker run -p 8501:8501 emotional-profile-app
```

### Option 3: Tradiční server (Ubuntu/CentOS)

```bash
# Instalace závislostí
sudo apt update
sudo apt install python3 python3-pip nginx

# Setup aplikace
cd /opt/
sudo git clone <your-repo>
cd vyzkumdata
sudo pip3 install -r requirements.txt

# Systemd service
sudo nano /etc/systemd/system/emotional-app.service
```

```ini
[Unit]
Description=Emotional Profile Streamlit App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/vyzkumdata
ExecStart=/usr/bin/python3 -m streamlit run app.py --server.headless true --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Spuštění služby
sudo systemctl daemon-reload
sudo systemctl enable emotional-app
sudo systemctl start emotional-app
```

## 🔒 Bezpečnostní doporučení

### 1. HTTPS (Povinné pro produkci)
```nginx
# /etc/nginx/sites-available/emotional-app
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Firewall
```bash
# Pouze potřebné porty
sudo ufw allow 22     # SSH
sudo ufw allow 80     # HTTP
sudo ufw allow 443    # HTTPS
sudo ufw enable
```

### 3. Backup strategie
```bash
# Automatický backup dat
#!/bin/bash
# backup-data.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backups/emotional-data-$DATE.tar.gz /opt/vyzkumdata/data/
find /backups/ -name "emotional-data-*" -mtime +30 -delete
```

### 4. Monitoring a logy
```bash
# Log monitoring
tail -f /var/log/emotional-app/app.log

# System monitoring
sudo apt install htop iotop
```

## 📊 Monitoring a údržba

### 1. Health check endpoint
Aplikace automaticky loguje:
- ✅ Uživatelské aktivity
- ✅ Performance metriky
- ✅ Chyby a výjimky
- ✅ Systémové zdroje

### 2. Regular maintenance
```bash
# Čištění logů (týdně)
find /var/log/ -name "*.log" -mtime +7 -delete

# Update závislostí (měsíčně)
pip list --outdated
pip install -U package_name

# Backup verification (denně)
tar -tzf /backups/latest-backup.tar.gz > /dev/null && echo "Backup OK"
```

## 🔧 Troubleshooting

### Časté problémy:

**1. Aplikace se nespustí**
```bash
# Zkontroluj logy
journalctl -u emotional-app -f

# Zkontroluj porty
sudo netstat -tlnp | grep :8501

# Zkontroluj závislosti
pip check
```

**2. Výkonové problémy**
```bash
# Monitor paměti
free -h
top -p $(pgrep -f streamlit)

# Monitor disku
df -h
du -sh /opt/vyzkumdata/
```

**3. Chyby v datech**
```bash
# Validace CSV souborů
python -c "import pandas as pd; print(pd.read_csv('data/hand_dataset.csv', sep=';').info())"
```

## 📈 Škálování pro více uživatelů

### Load balancer setup (pro >100 současných uživatelů)
```nginx
upstream emotional_backend {
    server 127.0.0.1:8501;
    server 127.0.0.1:8502;
    server 127.0.0.1:8503;
}

server {
    location / {
        proxy_pass http://emotional_backend;
    }
}
```

### Database upgrade (pro >1000 účastníků)
- Zvážit přechod z CSV na PostgreSQL/MySQL
- Implementovat connection pooling
- Přidat Redis cache pro často načítaná data

## 🎯 URL distribuce účastníkům

### Automatické generování URL:
```python
# generate_participant_urls.py
import pandas as pd

participants = pd.read_csv('data/hand_dataset.csv', sep=';')
base_url = "https://your-domain.com"

for participant_id in participants['ID'].unique():
    print(f"{participant_id}: {base_url}?ID={participant_id}")
```

### Email template:
```html
<h2>Váš osobní emoční profil</h2>
<p>Vážený/á účastníku/účastnice,</p>
<p>děkujeme za účast v naší studii! Váš osobní report je dostupný na:</p>
<p><a href="https://your-domain.com?ID={{participant_id}}">{{participant_id}}</a></p>
<p>Tento odkaz je určen pouze pro Vás a obsahuje pouze Vaše data.</p>
```

## 📞 Podpora

### Kontaktní informace:
- **Email**: support@your-domain.com  
- **Dokumentace**: [GitHub Wiki](link)
- **Bug reporting**: [GitHub Issues](link)

### SLA pro produkci:
- **Uptime**: 99.5%
- **Response time**: <2s pro 95% požadavků
- **Support**: 8:00-18:00 pracovní dny

---

*Poslední aktualizace: 28. srpna 2025*
