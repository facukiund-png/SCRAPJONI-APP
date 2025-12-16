import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import urllib.parse
import subprocess
import math

# --- 1. INSTALACIÓN AUTOMÁTICA EN LA NUBE ---
def install_playwright():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=False)
    except:
        pass

try:
    install_playwright()
except:
    pass

st.set_page_config(page_title="ScrapJoni V4", page_icon="📍", layout="wide")

# --- 2. ESTILOS VISUALES (MODO CLARO / LIGHT) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
    div[data-testid="stExpander"], div.stContainer {
        background-color: #ffffff; border-radius: 12px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); padding: 20px;
    }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important; color: #334155 !important;
        border: 1px solid #cbd5e1 !important; border-radius: 8px;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white; border: none; padding: 0.8rem 2rem;
        font-size: 1.1rem; font-weight: bold; border-radius: 8px; width: 100%;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    }
    /* Estilo para el tiempo estimado */
    .time-badge {
        background-color: #dbeafe; color: #1e40af;
        padding: 5px 10px; border-radius: 6px; font-weight: bold; font-size: 0.9em;
        border: 1px solid #93c5fd; display: inline-block; margin-top: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. BASE DE DATOS GEOGRÁFICA COMPLETA ---
LOCATION_DATA = {
    "CABA (Ciudad Autónoma)": {
        "Comuna 1": ["Retiro", "San Nicolás", "Puerto Madero", "San Telmo", "Monserrat", "Constitución"],
        "Comuna 2": ["Recoleta"],
        "Comuna 3": ["Balvanera", "San Cristóbal"],
        "Comuna 4": ["La Boca", "Barracas", "Parque Patricios", "Nueva Pompeya"],
        "Comuna 5": ["Almagro", "Boedo"],
        "Comuna 6": ["Caballito"],
        "Comuna 7": ["Flores", "Parque Chacabuco"],
        "Comuna 8": ["Villa Soldati", "Villa Riachuelo", "Villa Lugano"],
        "Comuna 9": ["Liniers", "Mataderos", "Parque Avellaneda"],
        "Comuna 10": ["Villa Real", "Monte Castro", "Versalles", "Floresta", "Vélez Sársfield", "Villa Luro"],
        "Comuna 11": ["Villa General Mitre", "Villa del Parque", "Villa Santa Rita", "Villa Devoto"],
        "Comuna 12": ["Coghlan", "Saavedra", "Villa Urquiza", "Villa Pueyrredón"],
        "Comuna 13": ["Núñez", "Belgrano", "Colegiales"],
        "Comuna 14": ["Palermo"],
        "Comuna 15": ["Chacarita", "Villa Crespo", "La Paternal", "Villa Ortúzar", "Agronomía", "Parque Chas"]
    },
    "GBA Zona Norte": {
        "Vicente López": ["Vicente López", "Olivos", "Florida", "La Lucila", "Villa Martelli", "Munro", "Carapachay"],
        "San Isidro": ["San Isidro", "Acassuso", "Martínez", "Beccar", "Boulogne", "Villa Adelina"],
        "Tigre": ["Tigre", "Don Torcuato", "General Pacheco", "El Talar", "Benavídez", "Nordelta"],
        "San Fernando": ["San Fernando", "Victoria", "Virreyes"],
        "San Martín": ["San Martín", "Villa Ballester", "San Andrés", "José León Suárez"],
        "Pilar": ["Pilar", "Del Viso", "Derqui", "Fátima"],
        "Escobar": ["Belén de Escobar", "Garín", "Ingeniero Maschwitz"]
    },
    "GBA Zona Sur": {
        "Avellaneda": ["Avellaneda", "Sarandí", "Villa Domínico", "Wilde", "Gerli"],
        "Lanús": ["Lanús Oeste", "Lanús Este", "Remedios de Escalada", "Monte Chingolo"],
        "Lomas de Zamora": ["Lomas de Zamora", "Banfield", "Temperley", "Turdera", "Llavallol"],
        "Quilmes": ["Quilmes", "Bernal", "Don Bosco", "Ezpeleta", "San Francisco Solano"],
        "Almirante Brown": ["Adrogué", "Burzaco", "Longchamps", "Rafael Calzada"],
        "Esteban Echeverría": ["Monte Grande", "Luis Guillón", "El Jagüel", "Canning"],
        "Ezeiza": ["Ezeiza", "Tristán Suárez"],
        "Berazategui": ["Berazategui", "Hudson"]
    },
    "GBA Zona Oeste": {
        "La Matanza": ["San Justo", "Ramos Mejía", "Lomas del Mirador", "Tapiales", "Isidro Casanova", "Laferrere", "Virrey del Pino"],
        "Morón": ["Morón", "Castelar", "Haedo", "El Palomar", "Villa Sarmiento"],
        "Tres de Febrero": ["Caseros", "Ciudadela", "Santos Lugares", "Sáenz Peña", "Martín Coronado"],
        "Merlo": ["Merlo", "San Antonio de Padua", "Libertad"],
        "Moreno": ["Moreno", "Paso del Rey"],
        "Hurlingham": ["Hurlingham", "William Morris"],
        "Ituzaingó": ["Ituzaingó", "Villa Udaondo"]
    }
}

# --- 4. MOTOR DE SCRAPING OPTIMIZADO PARA 1000 ITEMS ---
def get_google_maps_data(search_query, max_results=10, modo_full=False):
    data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        page = context.new_page()
        
        try:
            # Navegar
            page.goto("https://www.google.com/maps", timeout=60000)
            page.wait_for_selector("input#searchboxinput", state="visible")
            page.fill("input#searchboxinput", search_query)
            page.keyboard.press("Enter")
            page.wait_for_selector('div[role="feed"]', timeout=20000)
            
            # --- SCROLL INFINITO HASTA LLEGAR AL OBJETIVO ---
            feed_selector = 'div[role="feed"]'
            items_found = 0
            retries = 0
            
            # Bucle de carga (Scrollear hasta tener suficientes elementos visuales)
            while items_found < max_results and retries < 20:
                # Scrollear al fondo
                page.evaluate(f"document.querySelector('{feed_selector}').scrollTo(0, document.querySelector('{feed_selector}').scrollHeight)")
                time.sleep(1.5) # Esperar carga
                
                # Contar cuántos tenemos cargados en el DOM
                current_items = page.locator('div[role="feed"] > div > div[jsaction]').count()
                
                if current_items == items_found:
                    retries += 1 # No cargó nada nuevo
                else:
                    retries = 0 # Cargó nuevos
                    items_found = current_items
                
                # Salir si ya tenemos suficientes (con margen de error)
                if items_found >= max_results:
                    break

            # Obtener elementos finales
            items = page.locator('div[role="feed"] > div > div[jsaction]').all()
            
            # --- MODO RÁPIDO (LISTA) ---
            if not modo_full:
                count = 0
                for item in items:
                    if count >= max_results: break
                    try:
                        text = item.inner_text().split('\n')
                        if len(text) < 2 or "Anuncio" in text[0]: continue
                        
                        link = ""
                        try: link = item.locator("a").first.get_attribute("href")
                        except: pass

                        data.append({
                            "Seleccionar": False,
                            "Nombre": text[0],
                            "Dirección": "Modo Rápido",
                            "Teléfono": "Modo Rápido",
                            "Rating": text[1] if len(text) > 1 else "-",
                            "Link": link
                        })
                        count += 1
                    except: continue

            # --- MODO FULL (DETAIL) ---
            else:
                count = 0
                limit = min(len(items), max_results)

                for i in range(limit):
                    try:
                        # Refrescar lista (DOM inestable)
                        current_items = page.locator('div[role="feed"] > div > div[jsaction]').all()
                        if i >= len(current_items): break
                        
                        target = current_items[i]
                        nombre_raw = target.inner_text().split('\n')[0]
                        if "Anuncio" in nombre_raw: continue

                        # CLICK
                        target.click()
                        time.sleep(2) # Pausa breve para carga
                        
                        direccion, telefono, rating, link = "No encontrada", "No encontrado", "-", page.url
                        
                        try:
                            # Estrategia rápida de extracción por aria-label
                            direccion = page.locator('button[data-item-id^="address"]').first.get_attribute("aria-label").replace("Dirección: ", "")
                        except: pass
                        
                        try:
                            telefono = page.locator('button[data-item-id^="phone"]').first.get_attribute("aria-label").replace("Teléfono: ", "")
                        except: pass

                        try:
                            rating = page.locator('div[jsaction^="pane.rating"]').first.inner_text().split('\n')[0]
                        except: pass

                        data.append({
                            "Seleccionar": False,
                            "Nombre": nombre_raw,
                            "Dirección": direccion,
                            "Teléfono": telefono,
                            "Rating": rating,
                            "Link": link
                        })
                        count += 1
                        
                        # Volver atrás si hay botón
                        try:
                            page.locator('button[aria-label="Atrás"]').click()
                        except: pass
                        
                    except:
                        continue
                        
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
            
    return pd.DataFrame(data)

# --- 5. INTERFAZ ---

st.markdown("<h1 style='text-align: center; color: #1e40af;'>📍 ScrapJoni <span style='color: #64748b; font-size:0.6em'>Unlimited</span></h1>", unsafe_allow_html=True)

with st.container():
    st.subheader("⚙️ Configuración")
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        rubro = st.text_input("1. ¿Qué rubro buscas?", placeholder="Ej: Pizzería, Odontología")
    
    with col_b:
        st.markdown("##### Tipo de Rastreo")
        modo_busqueda = st.radio("Precisión:", ["⚡ Rápido", "🐢 Full (Con Tél/Dir)"], index=0)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        region = st.selectbox("2. Región", list(LOCATION_DATA.keys()))
    with col2:
        partido = st.selectbox("3. Partido", list(LOCATION_DATA[region].keys()))
    with col3:
        localidad = st.selectbox("4. Localidad", ["Todas"] + LOCATION_DATA[region][partido])

    # --- SLIDER CON CÁLCULO DE TIEMPO ---
    st.markdown("##### Cantidad de Resultados (Máx 1000)")
    
    cantidad = st.slider("Mueve la barra para ajustar:", 10, 1000, 20)
    
    # Lógica de cálculo de tiempo
    es_full = "Full" in modo_busqueda
    if es_full:
        # Estimamos 6 segundos por item en modo Full (Click + Copy + Back)
        segundos = cantidad * 6
    else:
        # Estimamos 0.2 segundos por item en modo Rápido
        segundos = cantidad * 0.2
    
    # Formateo de tiempo
    if segundos < 60:
        tiempo_texto = f"{int(segundos)} segundos"
    elif segundos < 3600:
        tiempo_texto = f"{math.ceil(segundos/60)} minutos"
    else:
        horas = segundos / 3600
        tiempo_texto = f"{round(horas, 1)} horas"

    # Color del badge según la duración
    color_badge = "#dbeafe" # Azul claro
    if segundos > 300: color_badge = "#fef3c7" # Amarillo (5 mins+)
    if segundos > 1800: color_badge = "#fee2e2" # Rojo (30 mins+)
    
    st.markdown(f"""
        <div style="background-color: {color_badge}; color: #1e293b; padding: 10px; border-radius: 8px; border: 1px solid #cbd5e1; display: inline-block;">
            ⏱️ Tiempo estimado: <strong>{tiempo_texto}</strong> <br>
            <span style="font-size: 0.8em; opacity: 0.8">Modo: {'Lento y detallado' if es_full else 'Velocidad máxima'}</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    btn_buscar = st.button(f"🔍 INICIAR BÚSQUEDA ({cantidad} REGISTROS)")

# --- 6. EJECUCIÓN ---

if 'df_resultados' not in st.session_state:
    st.session_state.df_resultados = None

if btn_buscar and rubro:
    loc_final = localidad if localidad != "Todas" else partido
    query = f"{rubro} en {loc_final}, {partido}, {region}, Argentina"
    
    with st.spinner(f"Trabajando... Extrayendo {cantidad} locales. Tiempo aprox: {tiempo_texto}"):
        df = get_google_maps_data(query, max_results=cantidad, modo_full=es_full)
        
        if not df.empty:
            st.session_state.df_resultados = df
            st.success(f"¡Listo! Se descargaron {len(df)} locales.")
        else:
            st.error("Google Maps no arrojó resultados o pidió verificación. Intenta con menos cantidad.")

if st.session_state.df_resultados is not None:
    df = st.session_state.df_resultados
    
    st.markdown("### 📋 Resultados")
    edited_df = st.data_editor(df, column_config={"Seleccionar": st.column_config.CheckboxColumn("Sel.", default=False), "Link": st.column_config.LinkColumn("Mapa")}, hide_index=True, use_container_width=True, height=500)
    
    sel = edited_df[edited_df["Seleccionar"] == True]
    
    c1, c2 = st.columns(2)
    with c1:
        csv = edited_df.drop(columns=["Seleccionar"]).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Todo (CSV)", csv, "scrapjoni_full.csv", "text/csv")
    with c2:
        if len(sel) >= 2:
            # Ruta optimizada (si hay direccion usa direccion, sino nombre)
            destinos = []
            for _, row in sel.iterrows():
                val = row['Dirección'] if "No encontrada" not in row['Dirección'] and "Rápido" not in row['Dirección'] else f"{row['Nombre']} {partido}"
                destinos.append(urllib.parse.quote(val))
            url = f"https://www.google.com/maps/dir/{'/'.join(destinos[:10])}" # Limite 10 para URL
            st.link_button("🗺️ Ver Ruta (Máx 10)", url)
