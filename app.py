import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import urllib.parse
import os
import subprocess

# --- CONFIGURACIÓN INICIAL PARA LA NUBE ---
# Esto instala el navegador automáticamente si no encuentra uno.
def install_playwright():
    print("Verificando instalación de navegadores...")
    subprocess.run(["playwright", "install", "chromium"], check=False)

# Ejecutamos la instalación al inicio
try:
    install_playwright()
except Exception as e:
    print(f"Nota: {e}")

st.set_page_config(page_title="ScrapJoni Cloud", page_icon="📍", layout="wide")

# --- DATOS DE ZONAS ---
LOCATION_DATA = {
    "CABA": {
        "Capital Federal": ["Palermo", "Recoleta", "Belgrano", "Caballito", "Villa Urquiza", "San Telmo", "Microcentro", "Flores"]
    },
    "Buenos Aires": {
        "Zona Norte": ["Vicente López", "San Isidro", "Tigre", "San Fernando", "Olivos"],
        "Zona Sur": ["Avellaneda", "Lanús", "Lomas de Zamora", "Quilmes", "Bernal"],
        "Zona Oeste": ["Morón", "Ramos Mejía", "San Justo", "Ciudadela", "Haedo"]
    },
    "Córdoba": {
        "Capital": ["Centro", "Nueva Córdoba", "Cerro de las Rosas"]
    }
}

# --- MOTOR DE SCRAPING ---
def get_google_maps_data(search_query, max_results=10):
    data = []
    
    with sync_playwright() as p:
        # Configuración específica para servidores en la nube (Headless + No Sandbox)
        try:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
        except Exception as e:
            st.error(f"Error lanzando el navegador: {e}")
            return pd.DataFrame()

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # Navegamos
        print(f"Buscando: {search_query}")
        try:
            page.goto("https://www.google.com/maps", timeout=60000)
            
            # Esperar input y escribir
            page.wait_for_selector("input#searchboxinput", state="visible")
            page.fill("input#searchboxinput", search_query)
            page.keyboard.press("Enter")
            
            # Esperar resultados
            page.wait_for_selector('div[role="feed"]', timeout=15000)
            
            # Scroll para cargar más
            feed_selector = 'div[role="feed"]'
            for _ in range(4):
                page.evaluate(f"document.querySelector('{feed_selector}').scrollTo(0, document.querySelector('{feed_selector}').scrollHeight)")
                time.sleep(1.5)

            # Extraer
            results = page.locator('div[role="feed"] > div > div[jsaction]').all()
            
            count = 0
            for res in results:
                if count >= max_results: break
                
                try:
                    text_content = res.inner_text().split('\n')
                    if len(text_content) < 2: continue
                    
                    nombre = text_content[0]
                    
                    # Intentar limpiar rating
                    rating = "N/A"
                    for t in text_content:
                        if "estrellas" in t or ("(" in t and ")" in t and ("," in t or "." in t)):
                            rating = t
                            break

                    link_locator = res.locator("a").first
                    link = link_locator.get_attribute("href") if link_locator.count() > 0 else ""
                    
                    if "Anuncio" not in nombre:
                        data.append({
                            "Seleccionar": False,
                            "Nombre": nombre,
                            "Datos": " ".join(text_content[1:3]), # Info extra
                            "Rating": rating,
                            "Link": link
                        })
                        count += 1
                except:
                    continue
                    
        except Exception as e:
            st.error(f"Hubo un problema accediendo a Maps: {e}")
        finally:
            browser.close()
        
    return pd.DataFrame(data)

# --- INTERFAZ ---
st.title("📍 ScrapJoni Online")

# Sidebar
with st.sidebar:
    st.header("Configuración")
    provincia = st.selectbox("Provincia", list(LOCATION_DATA.keys()))
    partido = st.selectbox("Zona", list(LOCATION_DATA[provincia].keys()))
    localidad = st.selectbox("Localidad", ["Todas"] + LOCATION_DATA[provincia][partido])
    
    rubro = st.text_input("Rubro", placeholder="Ej: Gimnasios, Veterinarias")
    cantidad = st.slider("Resultados", 5, 30, 10)
    btn_buscar = st.button("Buscar", type="primary")

# Lógica
if btn_buscar and rubro:
    query = f"{rubro} en {localidad if localidad != 'Todas' else ''} {partido} {provincia} Argentina"
    with st.spinner("Scrapeando datos en la nube... (puede tardar unos 20 seg)"):
        df = get_google_maps_data(query, cantidad)
        
        if not df.empty:
            st.session_state.data = df
            st.success("¡Datos obtenidos!")
        else:
            st.error("No se encontraron resultados o Google pidió captcha.")

if 'data' in st.session_state:
    df = st.session_state.data
    
    # Tabla editable
    edited = st.data_editor(
        df,
        column_config={"Link": st.column_config.LinkColumn("Mapa")},
        hide_index=True,
        use_container_width=True
    )
    
    # Botones descarga
    seleccionados = edited[edited["Seleccionar"] == True]
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Descargar CSV Completo", df.to_csv(index=False).encode('utf-8'), "todos.csv")
    with col2:
        if len(seleccionados) > 0:
            st.download_button("Descargar Seleccionados", seleccionados.to_csv(index=False).encode('utf-8'), "seleccion.csv")
            
            # Botón Ruta
            if len(seleccionados) >= 2:
                destinos = [urllib.parse.quote(f"{row['Nombre']} {provincia}") for i, row in seleccionados.iterrows()]
                url = f"https://www.google.com/maps/dir/{'/'.join(destinos)}"
                st.link_button("🗺️ Ver Ruta de Viaje", url)
