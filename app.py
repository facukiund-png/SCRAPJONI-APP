import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import urllib.parse
import subprocess

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

st.set_page_config(page_title="ScrapJoni V3", page_icon="📍", layout="wide")

# --- 2. ESTILOS VISUALES (MODO CLARO / LIGHT) ---
st.markdown("""
    <style>
    /* Forzar tema claro y limpio */
    .stApp {
        background-color: #f8fafc; /* Gris muy muy claro casi blanco */
        color: #1e293b; /* Texto gris oscuro */
    }
    
    /* Encabezados */
    h1, h2, h3 {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    
    /* Contenedores y Cards */
    div[data-testid="stExpander"], div.stContainer {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        padding: 20px;
    }
    
    /* Inputs y Selects */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px;
    }
    
    /* Botón Principal */
    div.stButton > button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
        width: 100%;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4);
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
        "Tigre": ["Tigre", "Don Torcuato", "General Pacheco", "El Talar", "Benavídez", "Nordelta", "Rincón de Milberg"],
        "San Fernando": ["San Fernando", "Victoria", "Virreyes"],
        "San Martín": ["San Martín", "Villa Ballester", "San Andrés", "José León Suárez", "Villa Maipú"],
        "Pilar": ["Pilar", "Del Viso", "Derqui", "Fátima"],
        "Escobar": ["Belén de Escobar", "Garín", "Ingeniero Maschwitz", "Maquinista Savio"]
    },
    "GBA Zona Sur": {
        "Avellaneda": ["Avellaneda", "Sarandí", "Villa Domínico", "Wilde", "Gerli", "Piñeyro", "Dock Sud"],
        "Lanús": ["Lanús Oeste", "Lanús Este", "Remedios de Escalada", "Monte Chingolo", "Valentín Alsina"],
        "Lomas de Zamora": ["Lomas de Zamora", "Banfield", "Temperley", "Turdera", "Llavallol", "Fiorito"],
        "Quilmes": ["Quilmes", "Bernal", "Don Bosco", "Ezpeleta", "San Francisco Solano", "Villa La Florida"],
        "Almirante Brown": ["Adrogué", "Burzaco", "Longchamps", "Rafael Calzada", "Claypole", "Glew"],
        "Esteban Echeverría": ["Monte Grande", "Luis Guillón", "El Jagüel", "Canning"],
        "Ezeiza": ["Ezeiza", "Tristán Suárez", "La Unión"],
        "Berazategui": ["Berazategui", "Hudson", "Plátanos", "Ranelagh"]
    },
    "GBA Zona Oeste": {
        "La Matanza": ["San Justo", "Ramos Mejía", "Lomas del Mirador", "Tapiales", "Isidro Casanova", "Laferrere", "Virrey del Pino", "González Catán", "Aldo Bonzi"],
        "Morón": ["Morón", "Castelar", "Haedo", "El Palomar", "Villa Sarmiento"],
        "Tres de Febrero": ["Caseros", "Ciudadela", "Santos Lugares", "Sáenz Peña", "Martín Coronado", "Loma Hermosa", "Pablo Podestá"],
        "Merlo": ["Merlo", "San Antonio de Padua", "Libertad", "Mariano Acosta"],
        "Moreno": ["Moreno", "Paso del Rey", "Trujui", "La Reja"],
        "Hurlingham": ["Hurlingham", "William Morris", "Villa Tesei"],
        "Ituzaingó": ["Ituzaingó", "Villa Udaondo"]
    }
}

# --- 4. MOTOR DE SCRAPING (LÓGICA DOBLE: RÁPIDA vs FULL) ---
def get_google_maps_data(search_query, max_results=10, modo_full=False):
    data = []
    
    with sync_playwright() as p:
        # Lanzar navegador
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            # 1. Búsqueda Inicial
            page.goto("https://www.google.com/maps", timeout=60000)
            page.wait_for_selector("input#searchboxinput", state="visible")
            page.fill("input#searchboxinput", search_query)
            page.keyboard.press("Enter")
            
            # Esperar carga de lista
            page.wait_for_selector('div[role="feed"]', timeout=20000)
            
            # Scroll para cargar resultados
            feed_selector = 'div[role="feed"]'
            for _ in range(5):
                page.evaluate(f"document.querySelector('{feed_selector}').scrollTo(0, document.querySelector('{feed_selector}').scrollHeight)")
                time.sleep(2)

            # Obtener elementos de la lista
            # Google Maps a veces cambia la estructura, usamos el selector más común para items
            items = page.locator('div[role="feed"] > div > div[jsaction]').all()
            
            # --- MODO RÁPIDO (Solo lista) ---
            if not modo_full:
                count = 0
                for item in items:
                    if count >= max_results: break
                    try:
                        text_content = item.inner_text().split('\n')
                        if len(text_content) < 2 or "Anuncio" in text_content[0]: continue
                        
                        link = ""
                        try:
                            link = item.locator("a").first.get_attribute("href")
                        except: pass

                        data.append({
                            "Seleccionar": False,
                            "Nombre": text_content[0],
                            "Dirección": "Ver en Mapa (Modo Rápido)",
                            "Teléfono": "No disponible (Modo Rápido)",
                            "Rating": text_content[1] if len(text_content) > 1 else "-",
                            "Link": link
                        })
                        count += 1
                    except: continue

            # --- MODO FULL (Click en cada uno) ---
            else:
                # Este modo es más lento porque entra a la ficha
                count = 0
                # Re-seleccionamos locators para iterar
                # Nota: Al hacer click el DOM cambia, es complejo en headless.
                # Estrategia: Iteramos por índice.
                
                total_items_visual = len(items)
                limit = min(total_items_visual, max_results)

                for i in range(limit):
                    try:
                        # Re-capturar la lista porque el DOM se refresca
                        current_items = page.locator('div[role="feed"] > div > div[jsaction]').all()
                        if i >= len(current_items): break
                        
                        target = current_items[i]
                        
                        # Extraer nombre antes del click
                        nombre_raw = target.inner_text().split('\n')[0]
                        if "Anuncio" in nombre_raw: continue

                        # CLICK para ver detalles
                        target.click()
                        time.sleep(3) # Esperar que cargue el panel lateral
                        
                        # Extraer datos del panel de detalle
                        direccion = "No encontrada"
                        telefono = "No encontrado"
                        rating = "-"
                        link = page.url
                        
                        # Intentar sacar dirección (busca el icono de pin o texto)
                        try:
                            # Buscamos botones que contengan el dato
                            all_buttons = page.locator('button[data-item-id^="address"]', ).all()
                            if all_buttons:
                                direccion = all_buttons[0].get_attribute("aria-label").replace("Dirección: ", "")
                        except: pass
                        
                        # Intentar sacar teléfono (busca icono de teléfono)
                        try:
                            phone_buttons = page.locator('button[data-item-id^="phone"]').all()
                            if phone_buttons:
                                telefono = phone_buttons[0].get_attribute("aria-label").replace("Teléfono: ", "")
                        except: pass

                        # Intentar rating
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
                        
                        # VOLVER ATRÁS (Click en la X o botón atrás)
                        # A veces es mejor buscar el botón "Atrás"
                        try:
                            back_btn = page.locator('button[aria-label="Atrás"]')
                            if back_btn.count() > 0:
                                back_btn.click()
                            else:
                                # Si no hay botón atrás, cerramos búsqueda (riesgoso)
                                pass
                        except: pass
                        
                        time.sleep(1) # Esperar que vuelva la lista
                        
                    except Exception as e:
                        print(f"Error en item {i}: {e}")
                        continue

        except Exception as e:
            print(f"Error general: {e}")
        finally:
            browser.close()
            
    return pd.DataFrame(data)


# --- 5. INTERFAZ DE USUARIO ---

st.markdown("<h1 style='text-align: center; color: #1e40af; margin-bottom: 30px;'>📍 ScrapJoni <span style='font-size: 0.6em; color: #64748b;'>Online Pro</span></h1>", unsafe_allow_html=True)

# Container Principal de Configuración
with st.container():
    st.subheader("⚙️ Configura tu Búsqueda")
    
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        # INPUT 1: Rubro
        rubro = st.text_input("1. ¿Qué rubro buscas?", placeholder="Ej: Pizzería, Odontología, Ferretería")
    
    with col_b:
        # INPUT DE MODO (TOGGLE)
        st.markdown("##### Tipo de Rastreo")
        modo_busqueda = st.radio(
            "Selecciona precisión:",
            ["⚡ Rápido (Sin Tél/Dir)", "🐢 Full (Con Tél/Dir Exacto)"],
            index=0,
            help="El modo Full tarda más porque entra a cada ficha para copiar el teléfono."
        )

    # SEPARADOR
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        # INPUT 2: Región
        region = st.selectbox("2. Zona / Región", list(LOCATION_DATA.keys()))
    
    with col2:
        # INPUT 3: Partido
        partidos_opc = list(LOCATION_DATA[region].keys())
        partido = st.selectbox("3. Partido / Comuna", partidos_opc)
        
    with col3:
        # INPUT 4: Localidad
        localidades_opc = LOCATION_DATA[region][partido]
        localidad = st.selectbox("4. Localidad", ["Todas las localidades"] + localidades_opc)

    # SLIDER CANTIDAD
    cantidad = st.slider("Cantidad de resultados a extraer:", 5, 20, 10, help="En modo Full, recomendamos máximo 10 para no saturar.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # BOTÓN DE ACCIÓN
    btn_buscar = st.button(f"🔍 BUSCAR AHORA ({'FULL' if 'Full' in modo_busqueda else 'RÁPIDO'})")


# --- 6. RESULTADOS ---

if 'df_resultados' not in st.session_state:
    st.session_state.df_resultados = None

if btn_buscar and rubro:
    # Preparar Query
    loc_final = localidad if localidad != "Todas las localidades" else partido
    query = f"{rubro} en {loc_final}, {partido}, {region}, Argentina"
    
    es_full = "Full" in modo_busqueda
    
    msg_espera = "⏳ Extrayendo teléfonos y direcciones exactas... Esto puede tomar 1-2 minutos." if es_full else "🚀 Escaneando listado rápido..."
    
    with st.spinner(msg_espera):
        df = get_google_maps_data(query, max_results=cantidad, modo_full=es_full)
        
        if not df.empty:
            st.session_state.df_resultados = df
            st.balloons()
            st.success(f"¡Éxito! Se encontraron {len(df)} resultados.")
        else:
            st.error("No se encontraron resultados o Google bloqueó la conexión. Intenta bajar la cantidad o esperar unos minutos.")

# MOSTRAR TABLA Y ACCIONES
if st.session_state.df_resultados is not None:
    df = st.session_state.df_resultados
    
    st.markdown("### 📋 Resultados")
    
    # Tabla Interactiva
    edited_df = st.data_editor(
        df,
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn("Sel.", default=False),
            "Link": st.column_config.LinkColumn("Mapa"),
        },
        hide_index=True,
        use_container_width=True,
        height=500
    )
    
    seleccionados = edited_df[edited_df["Seleccionar"] == True]
    
    st.markdown("---")
    st.subheader("📥 Exportar Datos")
    
    c1, c2 = st.columns(2)
    
    with c1:
        # CSV FULL
        csv = edited_df.drop(columns=["Seleccionar"]).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Listado Completo (CSV)",
            data=csv,
            file_name="scrapjoni_resultados.csv",
            mime="text/csv"
        )
    
    with c2:
        # BOTÓN DE RUTA
        if len(seleccionados) >= 2:
            st.write(f"Has seleccionado {len(seleccionados)} puntos para la ruta.")
            
            # Construir ruta
            # Si tenemos direccion exacta (Modo Full), la usamos. Si no, Nombre + Partido
            destinos = []
            for _, row in seleccionados.iterrows():
                if "No encontrada" not in row["Dirección"] and "Modo Rápido" not in row["Dirección"]:
                    q = urllib.parse.quote(f"{row['Dirección']}, {partido}")
                else:
                    q = urllib.parse.quote(f"{row['Nombre']} {partido}")
                destinos.append(q)
            
            url_maps = f"https://www.google.com/maps/dir/{'/'.join(destinos)}"
            
            st.link_button("🗺️ Ver Ruta Optimizada en Google Maps", url_maps)
        else:
            st.info("Selecciona al menos 2 casillas arriba para generar el mapa de ruta.")

else:
    # Espaciador visual si no hay datos
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#94a3b8;'>ScrapJoni V3.0 - Designed by Suipa Agency</div>", unsafe_allow_html=True)
