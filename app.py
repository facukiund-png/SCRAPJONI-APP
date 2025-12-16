import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import urllib.parse
import subprocess
import math

# --- 1. SETUP ---
def install_playwright():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=False)
    except:
        pass

try:
    install_playwright()
except:
    pass

st.set_page_config(page_title="ScrapJoni Turbo", page_icon="⚡", layout="wide")

# --- 2. ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    div.stButton > button {
        background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%); /* ROJO TURBO */
        color: white; font-weight: bold; border: none; padding: 0.8rem; width: 100%; border-radius: 8px;
    }
    .time-badge {
        background-color: #fee2e2; color: #991b1b; padding: 5px 10px; border-radius: 6px; 
        font-weight: bold; border: 1px solid #fecaca; display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATOS GEOGRÁFICOS (Resumido para el ejemplo, tu lista completa sigue funcionando) ---
# ... (MANTÉN TU DICCIONARIO LOCATION_DATA COMPLETO AQUÍ) ...
# Para que el código entre en la respuesta, uso una versión corta, pero TÚ USA LA TUYA COMPLETA
LOCATION_DATA = {
    "CABA": {"Capital": ["Palermo", "Recoleta", "Belgrano", "Caballito"]},
    "GBA Zona Norte": {"Vicente López": ["Olivos", "Munro"], "San Isidro": ["Martinez"]},
    "GBA Zona Oeste": {"La Matanza": ["San Justo", "Ramos Mejía"], "Tres de Febrero": ["Ciudadela", "Caseros"]},
    "GBA Zona Sur": {"Avellaneda": ["Wilde"], "Lanús": ["Lanús Oeste"]}
}

# --- 4. MOTOR TURBO ---
def get_google_maps_data(search_query, max_results=10, modo_full=False):
    data = []
    
    with sync_playwright() as p:
        # Optimizaciones de navegador para velocidad
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage', 
                '--disable-gpu',
                '--blink-settings=imagesEnabled=false' # NO CARGAR IMÁGENES (MÁS RÁPIDO)
            ]
        )
        page = browser.new_page()
        
        try:
            # Navegar
            page.goto("https://www.google.com/maps", timeout=30000)
            page.wait_for_selector("input#searchboxinput", state="visible")
            page.fill("input#searchboxinput", search_query)
            page.keyboard.press("Enter")
            
            # Esperar feed (reducido el timeout)
            try:
                page.wait_for_selector('div[role="feed"]', timeout=10000)
            except:
                return pd.DataFrame() # Falló la búsqueda inicial
            
            # --- SCROLL INTELIGENTE ---
            feed_selector = 'div[role="feed"]'
            
            # Si quiere 1000, calculamos cuántos scrolls aproximados necesita
            # Cada scroll carga unos 10-20 items.
            last_count = 0
            stuck_counter = 0
            
            # Barra de progreso en la UI
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            while True:
                # Scroll rápido
                page.evaluate(f"document.querySelector('{feed_selector}').scrollTo(0, document.querySelector('{feed_selector}').scrollHeight)")
                time.sleep(0.7) # Reducido de 1.5 a 0.7s
                
                # Contar elementos cargados
                items = page.locator('div[role="feed"] > div > div[jsaction]').count()
                
                # Actualizar barra
                progreso = min(items / max_results, 1.0)
                progress_bar.progress(progreso)
                status_text.text(f"Cargados: {items} / {max_results}")
                
                if items >= max_results:
                    break
                
                if items == last_count:
                    stuck_counter += 1
                    time.sleep(1) # Esperar un poco más si se traba
                    if stuck_counter > 4: break # Si se traba 4 veces, salimos con lo que hay
                else:
                    stuck_counter = 0
                
                last_count = items

            # Extracción
            elements = page.locator('div[role="feed"] > div > div[jsaction]').all()
            limit = min(len(elements), max_results)
            
            if not modo_full:
                # --- MODO RÁPIDO (EXTRACCIÓN INMEDIATA) ---
                # Usamos evaluate_all para extraer todo de una sola vez con Javascript (MUCHO MAS RAPIDO)
                # en lugar de iterar con Python uno por uno.
                
                js_script = """
                (elements) => {
                    return elements.map(e => {
                        let text = e.innerText.split('\\n');
                        let link = e.querySelector('a') ? e.querySelector('a').href : '';
                        if (text.length < 2 || text[0].includes('Anuncio')) return null;
                        return {
                            "Nombre": text[0],
                            "Rating": text[1] || '-',
                            "Link": link,
                            "Dirección": "Modo Rápido",
                            "Teléfono": "Modo Rápido"
                        };
                    }).filter(Boolean);
                }
                """
                # Seleccionamos el contenedor padre y ejecutamos script sobre hijos
                # Nota: Playwright Python no soporta evaluate_all directo sobre objetos locator en lista
                # Así que iteramos rápido en Python pero sin esperas
                
                for i in range(limit):
                    try:
                        text = elements[i].inner_text().split('\n')
                        if len(text) < 2 or "Anuncio" in text[0]: continue
                        
                        data.append({
                            "Seleccionar": False,
                            "Nombre": text[0],
                            "Dirección": "Modo Rápido",
                            "Teléfono": "Modo Rápido", 
                            "Rating": text[1],
                            "Link": "" # Sacar el link toma tiempo extra, en modo turbo a veces se obvia o se saca rápido
                        })
                    except: pass

            else:
                # --- MODO FULL (CLICK UNO POR UNO) ---
                # Aquí no hay magia, si quieres el teléfono hay que entrar.
                # Optimizamos reduciendo los tiempos de espera al mínimo.
                for i in range(limit):
                    try:
                        # Refrescar items
                        current = page.locator('div[role="feed"] > div > div[jsaction]').nth(i)
                        
                        # Extraer nombre rápido
                        nombre = current.inner_text().split('\n')[0]
                        if "Anuncio" in nombre: continue
                        
                        current.click()
                        
                        # Esperar SOLO a que aparezca el botón de dirección o teléfono (máx 2 seg)
                        try:
                            page.wait_for_selector('button[data-item-id^="address"]', timeout=2000)
                        except: pass 
                        
                        # Extracción rápida
                        direccion = "No data"
                        telefono = "No data"
                        
                        try:
                            direccion = page.locator('button[data-item-id^="address"]').first.get_attribute("aria-label").replace("Dirección: ", "")
                        except: pass
                        
                        try:
                            telefono = page.locator('button[data-item-id^="phone"]').first.get_attribute("aria-label").replace("Teléfono: ", "")
                        except: pass
                        
                        data.append({
                            "Seleccionar": False,
                            "Nombre": nombre,
                            "Dirección": direccion,
                            "Teléfono": telefono,
                            "Rating": "-",
                            "Link": page.url
                        })
                        
                        # Intentar cerrar o volver rapido
                        # A veces es mas rapido hacer click en el mapa para deseleccionar que buscar el boton atras
                        # Pero el boton atras es más seguro.
                        try: page.locator('button[aria-label="Atrás"]').click()
                        except: pass
                        
                    except: continue

        except Exception as e:
            print(e)
        finally:
            browser.close()
            
    return pd.DataFrame(data)

# --- 5. INTERFAZ ---
st.title("⚡ ScrapJoni TURBO")

with st.container():
    c1, c2 = st.columns([3, 1])
    with c1:
        rubro = st.text_input("Rubro", "Pizzería")
    with c2:
        # Selector de precisión con advertencia de tiempo
        modo = st.selectbox("Modo", ["⚡ VELOCIDAD (Lista)", "🐢 EXACTITUD (Teléfonos)"])

    c3, c4, c5 = st.columns(3)
    # (Aquí irían tus selectores de Provincia/Partido/Localidad completos)
    # Uso placeholders para el ejemplo:
    with c3: region = st.selectbox("Región", list(LOCATION_DATA.keys()))
    with c4: partido = st.selectbox("Partido", list(LOCATION_DATA[region].keys()))
    with c5: localidad = st.selectbox("Localidad", ["Todas"] + LOCATION_DATA[region][partido])

    # Slider hasta 1000
    cantidad = st.slider("Cantidad", 10, 1000, 50)
    
    # Calculadora de tiempo
    es_full = "EXACTITUD" in modo
    t_item = 4.0 if es_full else 0.1 # Tiempos optimizados
    total_seg = cantidad * t_item
    
    msg_tiempo = f"{int(total_seg)} seg" if total_seg < 60 else f"{int(total_seg/60)} min"
    
    st.markdown(f"""
        <div class="time-badge">
            ⏱️ Tiempo estimado: {msg_tiempo} <br>
            <small>{'Extracción lenta (entra a cada local)' if es_full else 'Extracción rápida (solo lista)'}</small>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("BUSCAR AHORA"):
        loc = localidad if localidad != "Todas" else partido
        q = f"{rubro} en {loc} {partido} {region} Argentina"
        
        with st.spinner("Scrapeando..."):
            df = get_google_maps_data(q, cantidad, es_full)
            if not df.empty:
                st.session_state.df = df
                st.success(f"Encontrados: {len(df)}")
            else:
                st.error("Sin resultados.")

if 'df' in st.session_state:
    df = st.session_state.df
    edited = st.data_editor(df, use_container_width=True)
    
    csv = edited.to_csv(index=False).encode('utf-8')
    st.download_button("📥 DESCARGAR CSV", csv, "data.csv", "text/csv")
