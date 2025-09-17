import requests
import json
import os
import time
from bs4 import BeautifulSoup
import hashlib
import re

# Configuració (ara des de variables d'entorn)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Preu màxim configurable (per defecte 650€)
MAX_PRICE = int(os.getenv("MAX_PRICE", "650"))

# Mode test (només mostra informació, no envia missatges)
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# Arxiu per guardar anuncis ja vistos
SEEN_ADS_FILE = "seen_ads.json"

# URLs de cerca - Idealista (amb filtre de preu)
IDEALISTA_URLS = {
    "Idealista Terrassa": f"https://www.idealista.com/alquiler-viviendas/terrassa-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Sabadell": f"https://www.idealista.com/alquiler-viviendas/sabadell-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Sant Quirze": f"https://www.idealista.com/alquiler-viviendas/sant-quirze-del-valles-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Matadepera": f"https://www.idealista.com/alquiler-viviendas/matadepera-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Rubí": f"https://www.idealista.com/alquiler-viviendas/rubi-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Castellar": f"https://www.idealista.com/alquiler-viviendas/castellar-del-valles-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Sentmenat": f"https://www.idealista.com/alquiler-viviendas/sentmenat-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Sant Llorenç": f"https://www.idealista.com/alquiler-viviendas/sant-llorenc-savall-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Polinyà": f"https://www.idealista.com/alquiler-viviendas/polinya-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Santa Perpètua": f"https://www.idealista.com/alquiler-viviendas/santa-perpetua-de-mogoda-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Cerdanyola": f"https://www.idealista.com/alquiler-viviendas/cerdanyola-del-valles-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Bellaterra": f"https://www.idealista.com/alquiler-viviendas/cerdanyola-del-valles-barcelona/bellaterra/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Barberà": f"https://www.idealista.com/alquiler-viviendas/barbera-del-valles-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Badia del Vallès": f"https://www.idealista.com/alquiler-viviendas/badia-del-valles-barcelona/con-precio-hasta_{MAX_PRICE}/",
    "Idealista Ripollet": f"https://www.idealista.com/alquiler-viviendas/ripollet-barcelona/con-precio-hasta_{MAX_PRICE}/",
}

# URLs de cerca - Fotocasa (filtrem per preu després)
FOTOCASA_URLS = {
    "Fotocasa Terrassa": "https://www.fotocasa.es/es/alquiler/pisos/terrassa/todas-las-zonas/l",
    "Fotocasa Sabadell": "https://www.fotocasa.es/es/alquiler/pisos/sabadell/todas-las-zonas/l", 
    "Fotocasa Sant Quirze": "https://www.fotocasa.es/es/alquiler/pisos/sant-quirze-del-valles/todas-las-zonas/l",
    "Fotocasa Matadepera": "https://www.fotocasa.es/es/alquiler/pisos/matadepera/todas-las-zonas/l",
    "Fotocasa Rubí": "https://www.fotocasa.es/es/alquiler/pisos/rubi/todas-las-zonas/l",
    "Fotocasa Castellar": "https://www.fotocasa.es/es/alquiler/pisos/castellar-del-valles/todas-las-zonas/l",
    "Fotocasa Sentmenat": "https://www.fotocasa.es/es/alquiler/pisos/sentmenat/todas-las-zonas/l",
    "Fotocasa Sant Llorenç": "https://www.fotocasa.es/es/alquiler/pisos/sant-llorenc-savall/todas-las-zonas/l",
    "Fotocasa Polinyà": "https://www.fotocasa.es/es/alquiler/pisos/polinya/todas-las-zonas/l",
    "Fotocasa Santa Perpètua": "https://www.fotocasa.es/es/alquiler/pisos/santa-perpetua-de-mogoda/todas-las-zonas/l",
    "Fotocasa Cerdanyola": "https://www.fotocasa.es/es/alquiler/pisos/cerdanyola-del-valles/todas-las-zonas/l",
    "Fotocasa Barberà": "https://www.fotocasa.es/es/alquiler/pisos/barbera-del-valles/todas-las-zonas/l",
    "Fotocasa Badia del Vallès": "https://www.fotocasa.es/es/alquiler/pisos/badia-del-valles/todas-las-zonas/l",
    "Fotocasa Ripollet": "https://www.fotocasa.es/es/alquiler/pisos/ripollet/todas-las-zonas/l",
}

def load_seen_ads():
    """Carrega la llista d'anuncis ja vistos"""
    try:
        if os.path.exists(SEEN_ADS_FILE):
            with open(SEEN_ADS_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except:
        return set()

def save_seen_ads(seen_ads):
    """Guarda la llista d'anuncis vistos"""
    try:
        with open(SEEN_ADS_FILE, 'w') as f:
            json.dump(list(seen_ads), f)
    except Exception as e:
        print(f"Error guardant anuncis vistos: {e}")

def send_telegram_message(message):
    """Envia un missatge via Telegram"""
    if TEST_MODE:
        print("🧪 MODE TEST: Missatge que s'enviaria:")
        print(message)
        print("-" * 50)
        return
        
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram no configurat, saltant notificació")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ Missatge enviat per Telegram")
        else:
            print(f"❌ Error enviant Telegram: {response.status_code}")
    except Exception as e:
        print(f"❌ Error enviant Telegram: {e}")

def extract_price_from_text(price_text):
    """Extreu el preu numèric d'un text"""
    if not price_text:
        return 0
    
    # Buscar números amb €
    numbers = re.findall(r'[\d.,]+', price_text.replace('.', '').replace(',', ''))
    if numbers:
        try:
            return int(numbers[0])
        except:
            return 0
    return 0

def get_idealista_ads(url, source_name):
    """Extreu anuncis d'Idealista"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"🔍 Buscant a {source_name}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        ads = []
        
        # Selectors per Idealista (pot necessitar ajustos)
        articles = soup.select('article.item')
        
        for article in articles[:5]:  # Limitem a 5 primers
            try:
                # Enllaç
                link_elem = article.select_one('a.item-link')
                if not link_elem:
                    continue
                
                link = "https://www.idealista.com" + link_elem.get('href', '')
                
                # Preu
                price_elem = article.select_one('.item-price')
                price = price_elem.get_text(strip=True) if price_elem else "No preu"
                
                # Títol/descripció
                title_elem = article.select_one('.item-title')
                title = title_elem.get_text(strip=True) if title_elem else "Sense títol"
                
                # Detalls
                details_elem = article.select_one('.item-detail')
                details = details_elem.get_text(strip=True) if details_elem else ""
                
                ads.append({
                    'id': hashlib.md5(link.encode()).hexdigest(),
                    'title': title,
                    'price': price,
                    'details': details,
                    'link': link,
                    'source': source_name
                })
                
            except Exception as e:
                print(f"Error processant anunci: {e}")
                continue
        
        print(f"📊 Trobats {len(ads)} anuncis a {source_name}")
        return ads
        
    except requests.RequestException as e:
        print(f"❌ Error accedint a {source_name}: {e}")
        return []
    except Exception as e:
        print(f"❌ Error inesperat a {source_name}: {e}")
        return []

def get_fotocasa_ads(url, source_name):
    """Extreu anuncis de Fotocasa"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"🔍 Buscant a {source_name}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        ads = []
        
        # Selectors per Fotocasa (poden necessitar ajustos)
        articles = soup.select('article.re-SearchResult')
        if not articles:
            articles = soup.select('.re-SearchResult-itemRow')
        if not articles:
            articles = soup.select('[data-testid="search-result-item"]')
        
        for article in articles[:8]:  # Limitem a 8 primers
            try:
                # Enllaç
                link_elem = article.select_one('a[href*="/anuncio/"]')
                if not link_elem:
                    link_elem = article.select_one('a')
                
                if not link_elem:
                    continue
                
                link = link_elem.get('href', '')
                if not link.startswith('http'):
                    link = "https://www.fotocasa.es" + link
                
                # Preu
                price_elem = article.select_one('[data-testid="price"]')
                if not price_elem:
                    price_elem = article.select_one('.re-SearchResult-price')
                if not price_elem:
                    price_elem = article.select_one('.fc-Price')
                
                price_text = price_elem.get_text(strip=True) if price_elem else "No preu"
                price_value = extract_price_from_text(price_text)
                
                # Filtrar per preu màxim
                if price_value > MAX_PRICE and price_value > 0:
                    continue
                
                # Títol
                title_elem = article.select_one('[data-testid="property-title"]')
                if not title_elem:
                    title_elem = article.select_one('.re-SearchResult-title')
                if not title_elem:
                    title_elem = article.select_one('h3')
                
                title = title_elem.get_text(strip=True) if title_elem else "Sense títol"
                
                # Detalls (habitacions, m², etc.)
                details_elem = article.select_one('[data-testid="property-features"]')
                if not details_elem:
                    details_elem = article.select_one('.re-SearchResult-info')
                
                details = details_elem.get_text(strip=True) if details_elem else ""
                
                ads.append({
                    'id': hashlib.md5(link.encode()).hexdigest(),
                    'title': title,
                    'price': price_text,
                    'details': details,
                    'link': link,
                    'source': source_name
                })
                
            except Exception as e:
                print(f"Error processant anunci de Fotocasa: {e}")
                continue
        
        print(f"📊 Trobats {len(ads)} anuncis a {source_name} (≤{MAX_PRICE}€)")
        return ads
        
    except requests.RequestException as e:
        print(f"❌ Error accedint a {source_name}: {e}")
        return []
    except Exception as e:
        print(f"❌ Error inesperat a {source_name}: {e}")
        return []

def check_for_new_ads():
    """Comprova si hi ha nous anuncis a Idealista i Fotocasa"""
    seen_ads = load_seen_ads()
    all_new_ads = []
    
    # Comprovar Idealista
    print("🔍 Cercant a Idealista...")
    for source_name, url in IDEALISTA_URLS.items():
        ads = get_idealista_ads(url, source_name)
        
        for ad in ads:
            if ad['id'] not in seen_ads:
                all_new_ads.append(ad)
                seen_ads.add(ad['id'])
    
    # Comprovar Fotocasa
    print("🔍 Cercant a Fotocasa...")
    for source_name, url in FOTOCASA_URLS.items():
        ads = get_fotocasa_ads(url, source_name)
        
        for ad in ads:
            if ad['id'] not in seen_ads:
                all_new_ads.append(ad)
                seen_ads.add(ad['id'])
    
    # Guardar anuncis vistos
    save_seen_ads(seen_ads)
    
    return all_new_ads

def format_ad_message(ads):
    """Formata els anuncis per al missatge de Telegram"""
    if not ads:
        return None
    
    message = f"🏠 <b>Nous pisos trobats! ({len(ads)})</b>\n\n"
    
    for ad in ads[:3]:  # Màxim 3 per missatge
        message += f"📍 <b>{ad['source']}</b>\n"
        message += f"💰 {ad['price']}\n"
        message += f"🏡 {ad['title'][:100]}...\n" if len(ad['title']) > 100 else f"🏡 {ad['title']}\n"
        if ad['details']:
            message += f"📋 {ad['details'][:80]}...\n" if len(ad['details']) > 80 else f"📋 {ad['details']}\n"
        message += f"🔗 <a href='{ad['link']}'>Veure anunci</a>\n\n"
    
    return message

def main():
    """Funció principal"""
    print("🚀 Iniciant cerca de pisos...")
    print(f"💰 Preu màxim: {MAX_PRICE}€")
    print(f"📍 Cercant en {len(IDEALISTA_URLS)} ciutats a Idealista")
    print(f"📍 Cercant en {len(FOTOCASA_URLS)} ciutats a Fotocasa")
    print(f"🔍 Total: {len(IDEALISTA_URLS) + len(FOTOCASA_URLS)} cerques simultànies")
    
    if TEST_MODE:
        print("🧪 MODE TEST ACTIVAT - No s'enviaran missatges")
    
    # Comprovar configuració de Telegram
    if not TEST_MODE and (not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID):
        print("⚠️  Telegram no configurat! Afegeix TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID als secrets de GitHub")
        return
    
    # Buscar nous anuncis
    new_ads = check_for_new_ads()
    
    if new_ads:
        print(f"🎉 Trobats {len(new_ads)} anuncis nous!")
        
        # Enviar notificació
        message = format_ad_message(new_ads)
        if message:
            send_telegram_message(message)
        
        # Si hi ha més de 3, enviar un segon missatge
        if len(new_ads) > 3:
            remaining_ads = new_ads[3:]
            message2 = format_ad_message(remaining_ads)
            if message2:
                time.sleep(1)  # Petita pausa
                send_telegram_message(message2)
    else:
        print("😴 Cap anunci nou trobat")
    
    print("✅ Execució completada")

if __name__ == "__main__":
    main()
