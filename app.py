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
                
                current_count = page.locator('div[role="feed"] > div > div[jsaction]').count()
                
                if current_count == items_found:
                    retries += 1
                    time.sleep(1)
                else:
                    retries = 0
                    items_found = current_count
                
                # Feedback visual
                prog = min(current_count / max_results, 1.0)
                progress_bar.progress(prog)
                status_text.caption(f"🔎 Detectados: {current_count} / {max_results}")
                
                if current_count >= max_results:
                    break

            # 3. Extracción
            elements = page.locator('div[role="feed"] > div > div[jsaction]').all()
            limit = min(len(elements), max_results)
            
            status_text.text("⛏️ Procesando datos encontrados...")
            
            if not modo_full:
                # --- MODO RÁPIDO ---
                for i in range(limit):
                    try:
                        text = elements[i].inner_text().split('\n')
                        if len(text) < 2 or "Anuncio" in text[0]: continue
                        link = ""
                        try: link = elements[i].locator("a").first.get_attribute("href")
                        except: pass
                        
                        data.append({
                            "Nombre": text[0],
                            "Rating": text[1] if len(text)>1 else "-",
                            "Dirección": "N/A (Modo Rápido)",
                            "Teléfono": "N/A (Modo Rápido)",
                            "Link": link
                        })
                    except: pass
            else:
                # --- MODO FULL ---
                for i in range(limit):
                    try:
                        current = page.locator('div[role="feed"] > div > div[jsaction]').nth(i)
                        nombre_raw = current.inner_text().split('\n')[0]
                        if "Anuncio" in nombre_raw: continue
                        
                        current.click()
                        try: page.wait_for_selector('button[data-item-id^="address"]', timeout=2500)
                        except: pass
                        
                        direccion, telefono, rating = "No data", "No data", "-"
                        link = page.url
                        
                        try: direccion = page.locator('button[data-item-id^="address"]').first.get_attribute("aria-label").replace("Dirección: ", "")
                        except: pass
                        try: telefono = page.locator('button[data-item-id^="phone"]').first.get_attribute("aria-label").replace("Teléfono: ", "")
                        except: pass
                        try: rating = page.locator('div[jsaction^="pane.rating"]').first.inner_text().split('\n')[0]
                        except: pass
                        
                        data.append({
                            "Nombre": nombre_raw,
                            "Rating": rating,
                            "Dirección": direccion,
                            "Teléfono": telefono,
                            "Link": link
                        })
                        try: page.locator('button[aria-label="Atrás"]').click()
                        except: pass
                    except: continue

        except Exception as e:
            st.error(f"Error durante el proceso: {e}")
        finally:
            browser.close()
            # Ahora es seguro limpiar porque las creamos al principio
            progress_bar.empty()
            status_text.empty()
            
    return pd.DataFrame(data)

# --- 6. INTERFAZ DE USUARIO ---

st.markdown("<h1 style='text-align: center;'>🚀 ScrapJoni <span style='color:#2563eb'>Ultimate</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-top: -15px;'>Suite de Prospección y Geolocalización Comercial</p>", unsafe_allow_html=True)

with st.container():
    st.subheader("🛠️ Parámetros de Búsqueda")
    c1, c2 = st.columns([2, 1])
    with c1:
        rubro = st.text_input("¿Qué rubro buscas?", placeholder="Ej: Pizzería, Odontología, Gimnasio")
    with c2:
        modo = st.radio("Modo de Rastreo", ["⚡ Turbo (Solo Lista)", "🐢 Full (Con Teléfono)"], horizontal=True)

    c3, c4, c5 = st.columns(3)
    with c3: region = st.selectbox("Región", list(LOCATION_DATA.keys()))
    with c4: partido = st.selectbox("Partido / Zona", list(LOCATION_DATA[region].keys()))
    with c5: localidad = st.selectbox("Localidad", ["Todas"] + LOCATION_DATA[region][partido])

    st.write("")
    col_slide, col_badge = st.columns([3, 1])
    with col_slide:
        cantidad = st.slider("Objetivo de Resultados (Máx 1000)", 10, 1000, 20)
    
    with col_badge:
        es_full = "Full" in modo
        factor = 5.0 if es_full else 0.2
        secs = cantidad * factor
        time_str = f"{int(secs)} seg" if secs < 60 else f"{math.ceil(secs/60)} min"
        icon_t = "⚡" if not es_full else "🐢"
        st.markdown(f"<div style='margin-top: 10px;'><div class='time-badge'>{icon_t} Estimado: {time_str}</div></div>", unsafe_allow_html=True)

    btn_buscar = st.button(f"🔍 INICIAR BÚSQUEDA ({cantidad} REGISTROS)")

# --- 7. LÓGICA DE PROCESAMIENTO ---

if 'data' not in st.session_state:
    st.session_state.data = None

if btn_buscar and rubro:
    loc_final = localidad if localidad != "Todas" else partido
    query = f"{rubro} en {loc_final}, {partido}, {region}, Argentina"
    
    with st.spinner(f"Ejecutando ScrapJoni... Por favor espera..."):
        df_result = get_google_maps_data(query, cantidad, es_full)
        
        if not df_result.empty:
            df_result[['Teléfono', 'Link WhatsApp']] = df_result['Teléfono'].apply(lambda x: pd.Series(clean_phone_and_generate_wa(x)))
            coords = df_result['Link'].apply(extract_coords_from_url)
            df_result['lat'] = coords.apply(lambda x: x[0])
            df_result['lon'] = coords.apply(lambda x: x[1])
            df_result.insert(0, "Seleccionar", False)
            st.session_state.data = df_result
            st.success(f"¡Éxito! Se descargaron {len(df_result)} resultados.")
        else:
            st.error("No se encontraron resultados o Google pidió verificación. Intenta reducir la cantidad.")

# --- 8. VISUALIZACIÓN Y FILTROS ---

if st.session_state.data is not None:
    df = st.session_state.data.copy()
    st.markdown("---")
    
    with st.sidebar:
        st.header("🔍 Filtros de Resultados")
        solo_con_tel = st.checkbox("Solo con Teléfono")
        if solo_con_tel:
            df = df[df["Teléfono"] != "No data"]
            df = df[df["Teléfono"] != "No encontrado"]
        
        try:
            df['RatingNum'] = pd.to_numeric(df['Rating'].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
            min_rating = st.slider("Rating Mínimo", 0.0, 5.0, 0.0, 0.5)
            df = df[df['RatingNum'] >= min_rating]
        except: pass
        st.metric("Resultados Filtrados", len(df))

    tab1, tab2, tab3 = st.tabs(["📋 Tabla de Datos", "🗺️ Mapa Interactivo", "📊 Estadísticas"])
    
    with tab1:
        edited_df = st.data_editor(
            df,
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Sel.", default=False),
                "Link": st.column_config.LinkColumn("Maps"),
                "Link WhatsApp": st.column_config.LinkColumn("WhatsApp"),
                "lat": None, "lon": None, "RatingNum": None
            },
            hide_index=True, use_container_width=True, height=500
        )
        sel_rows = edited_df[edited_df["Seleccionar"] == True]
        c1, c2 = st.columns(2)
        with c1:
            csv = edited_df.drop(columns=["Seleccionar", "lat", "lon", "RatingNum"], errors='ignore').to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV Filtrado", csv, "scrapjoni_leads.csv", "text/csv")
        with c2:
            if len(sel_rows) >= 2:
                destinos = []
                for _, row in sel_rows.iterrows():
                    val = row['Dirección'] if row['Dirección'] not in ["No data", "N/A (Modo Rápido)"] else f"{row['Nombre']} {partido}"
                    destinos.append(urllib.parse.quote(val))
                url_ruta = f"https://www.google.com/maps/dir/{'/'.join(destinos[:10])}"
                st.link_button("🗺️ Ver Ruta de Viaje (Seleccionados)", url_ruta)

    with tab2:
        map_data = df.dropna(subset=['lat', 'lon'])
        if not map_data.empty:
            st.map(map_data, latitude='lat', longitude='lon', size=20, color='#2563eb')
            st.caption(f"Mostrando {len(map_data)} locales geolocalizados.")
        else:
            st.warning("No se pudieron extraer coordenadas suficientes para el mapa.")

    with tab3:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Locales", len(df))
        con_tel = len(df[~df['Teléfono'].isin(["No data", "No encontrado", "N/A (Modo Rápido)"])])
        m2.metric("Con Teléfono", con_tel)
        m3.metric("Promedio Rating", f"{df['RatingNum'].mean():.1f} ⭐")
