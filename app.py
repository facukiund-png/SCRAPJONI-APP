import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import urllib.parse
import subprocess
import math
import re

# --- 1. SETUP E INSTALACIÓN ---
def install_playwright():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=False)
    except:
        pass

try:
    install_playwright()
except:
    pass

st.set_page_config(page_title="ScrapJoni Ultimate", page_icon="🚀", layout="wide")

# --- 2. ESTILOS VISUALES PRO ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 800 !important; }
    div[data-testid="stExpander"], div.stContainer, div[data-testid="stMetric"] {
        background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); padding: 15px;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #f1f5f9 !important; color: #334155 !important;
        border: 1px solid #cbd5e1 !important; border-radius: 8px;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white; border: none; padding: 0.8rem 2rem; font-size: 1rem; 
        font-weight: bold; border-radius: 10px; width: 100%; transition: transform 0.2s;
    }
    div.stButton > button:hover {
        transform: scale(1.02); box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
    }
    .time-badge {
        background-color: #eff6ff; color: #1d4ed8; padding: 6px 12px; 
        border-radius: 20px; font-weight: 600; font-size: 0.85em;
        border: 1px solid #bfdbfe; display: inline-flex; align-items: center; gap: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNCIONES DE AYUDA ---
def clean_phone_and_generate_wa(phone_text):
    if not phone_text or phone_text in ["No data", "Modo Rápido", "No encontrado"]:
        return None, None
    raw_nums = re.sub(r'\D', '', phone_text)
    wa_link = None
    if len(raw_nums) == 10:
        wa_link = f"https://wa.me/549{raw_nums}"
    elif len(raw_nums) >= 11 and raw_nums.startswith("54"):
        wa_link = f"https://wa.me/{raw_nums}"
    return phone_text, wa_link

def extract_coords_from_url(url):
    if not url or "google" not in url: return None, None
    match = re.search(r'@([-.\d]+),([-.\d]+)', url)
    if match: return float(match.group(1)), float(match.group(2))
    match2 = re.search(r'!3d([-.\d]+)!4d([-.\d]+)', url)
    if match2: return float(match2.group(1)), float(match2.group(2))
    return None, None

# --- 4. BASE DE DATOS GEOGRÁFICA ---
LOCATION_DATA = {
    "CABA (Ciudad Autónoma)": {
        "Comuna 1 (Centro)": ["Retiro", "San Nicolás", "San Telmo", "Monserrat", "Constitución"],
        "Comuna 2 (Recoleta)": ["Recoleta"],
        "Comuna 3 (Balvanera)": ["Balvanera", "San Cristóbal"],
        "Comuna 4 (La Boca)": ["La Boca", "Barracas", "Parque Patricios"],
        "Comuna 5 (Almagro)": ["Almagro", "Boedo"],
        "Comuna 6 (Caballito)": ["Caballito"],
        "Comuna 7 (Flores)": ["Flores", "Parque Chacabuco"],
        "Comuna 8 (Lugano)": ["Villa Soldati", "Villa Lugano"],
        "Comuna 9 (Liniers)": ["Liniers", "Mataderos"],
        "Comuna 10 (Villa Luro)": ["Floresta", "Vélez Sársfield", "Villa Luro"],
        "Comuna 11 (Devoto)": ["Villa del Parque", "Villa Devoto"],
        "Comuna 12 (Saavedra)": ["Saavedra", "Villa Urquiza"],
        "Comuna 13 (Belgrano)": ["Núñez", "Belgrano", "Colegiales"],
        "Comuna 14 (Palermo)": ["Palermo"],
        "Comuna 15 (Chacarita)": ["Chacarita", "Villa Crespo", "Paternal"]
    },
    "GBA Zona Norte": {
        "Vicente López": ["Olivos", "Florida", "Munro", "Vicente López"],
        "San Isidro": ["San Isidro", "Martínez", "Beccar", "Boulogne"],
        "Tigre": ["Tigre", "Nordelta", "Don Torcuato", "Pacheco"],
        "San Fernando": ["San Fernando", "Victoria"],
        "San Martín": ["San Martín", "Villa Ballester", "José León Suárez"],
        "Pilar": ["Pilar", "Del Viso"],
        "Escobar": ["Escobar", "Garín"]
    },
    "GBA Zona Oeste": {
        "La Matanza": ["San Justo", "Ramos Mejía", "Lomas del Mirador", "Laferrere", "Virrey del Pino"],
        "Morón": ["Morón", "Castelar", "Haedo", "Palomar"],
        "Tres de Febrero": ["Caseros", "Ciudadela", "Santos Lugares", "Saenz Peña"],
        "Merlo": ["Merlo", "Padua"],
        "Moreno": ["Moreno", "Paso del Rey"],
        "Ituzaingó": ["Ituzaingó"]
    },
    "GBA Zona Sur": {
        "Avellaneda": ["Avellaneda", "Wilde", "Sarandí"],
        "Lanús": ["Lanús Oeste", "Lanús Este", "Remedios de Escalada"],
        "Lomas de Zamora": ["Lomas", "Banfield", "Temperley"],
        "Quilmes": ["Quilmes", "Bernal", "Solano"],
        "Berazategui": ["Berazategui"],
        "Ezeiza": ["Ezeiza", "Canning"]
    }
}

# --- 5. MOTOR DE SCRAPING (CORE) ---
def get_google_maps_data(search_query, max_results=10, modo_full=False):
    data = []
    
    # --- CORRECCIÓN DEL ERROR ---
    # Inicializamos las variables de UI AQUÍ afuera del try/catch
    # para que siempre existan, pase lo que pase.
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--blink-settings=imagesEnabled=false']
            )
        except Exception as e:
            st.error(f"Error iniciando navegador: {e}")
            return pd.DataFrame()

        page = browser.new_page()
        
        try:
            # 1. Búsqueda
            status_text.text("Conectando con Google Maps...")
            page.goto("https://www.google.com/maps", timeout=45000) # Aumenté el timeout
            page.wait_for_selector("input#searchboxinput", state="visible")
            page.fill("input#searchboxinput", search_query)
            page.keyboard.press("Enter")
            
            try:
                page.wait_for_selector('div[role="feed"]', timeout=15000)
            except:
                status_text.warning("No se cargó la lista de resultados. Intentando de nuevo...")
                return pd.DataFrame() 
            
            # 2. Scroll Logic
            feed_selector = 'div[role="feed"]'
            items_found = 0
            retries = 0
            
            while items_found < max_results and retries < 15:
                page.evaluate(f"document.querySelector('{feed_selector}').scrollTo(0, document.querySelector('{feed_selector}').scrollHeight)")
                time.sleep(0.8)
                
                current_count = page.locator('div[role="feed"] > div > div[jsaction]').count
