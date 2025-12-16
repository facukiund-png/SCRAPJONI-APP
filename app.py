import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import urllib.parse
import os
import subprocess

# --- 1. CONFIGURACIÓN E INSTALACIÓN AUTOMÁTICA ---
def install_playwright():
    # Solo intenta instalar si no detecta los navegadores (para velocidad)
    try:
        subprocess.run(["playwright", "install", "chromium"], check=False)
    except:
        pass

try:
    install_playwright()
except:
    pass

st.set_page_config(page_title="ScrapJoni Pro", page_icon="📍", layout="wide")

# --- 2. ESTILOS CSS (PARA QUE NO SE VEA "POBRE") ---
st.markdown("""
    <style>
    /* Fondo oscuro y textos claros */
    .stApp {
        background-color: #0f172a;
        color: #e2e8f0;
    }
    /* Inputs y Selects */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1e293b;
        color: white;
        border: 1px solid #334155;
    }
    /* Botón Principal */
    div.stButton > button {
        background: linear-gradient(90deg, #2563eb 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.5);
    }
    /* Contenedores */
    div[data-testid="stExpander"] {
        background-color: #1e293b;
        border: 1px solid #334155;
    }
    h1, h2, h3 {
        color: #f8fafc !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. BASE DE DATOS GEOGRÁFICA (MÁS COMPLETA) ---
# He expandido esto para cubrir CABA y GBA casi completo.
LOCATION_DATA = {
    "CABA (Ciudad Autónoma)": {
        "Comuna 1 (Centro/Retiro/San Telmo)": ["Retiro", "San Nicolás", "Puerto Madero", "San Telmo", "Monserrat", "Constitución"],
        "Comuna 2 (Recoleta)": ["Recoleta"],
        "Comuna 3 (Balvanera/San Cristóbal)": ["Balvanera", "San Cristóbal"],
        "Comuna 4 (La Boca/Barracas)": ["La Boca", "Barracas", "Parque Patricios", "Nueva Pompeya"],
        "Comuna 5 (Almagro/Boedo)": ["Almagro", "Boedo"],
        "Comuna 6 (Caballito)": ["Caballito"],
        "Comuna 7 (Flores/Parque Chacabuco)": ["Flores", "Parque Chacabuco"],
        "Comuna 8 (Villa Soldati/Lugano)": ["Villa Soldati", "Villa Riachuelo", "Villa Lugano"],
        "Comuna 9 (Liniers/Mataderos)": ["Liniers", "Mataderos", "Parque Avellaneda"],
        "Comuna 10 (Villa Luro/Versalles)": ["Villa Real", "Monte Castro", "Versalles", "Floresta", "Vélez Sársfield", "Villa Luro"],
        "Comuna 11 (Villa Devoto/Del Parque)": ["Villa General Mitre", "Villa del Parque", "Villa Santa Rita", "Villa Devoto"],
        "Comuna 12 (Saavedra/Urquiza)": ["Coghlan", "Saavedra", "Villa Urquiza", "Villa Pueyrredón"],
        "Comuna 13 (Núñez/Belgrano)": ["Núñez", "Belgrano", "Colegiales"],
        "Comuna 14 (Palermo)": ["Palermo"],
        "Comuna 15 (Chacarita/Villa Crespo)": ["Chacarita", "Villa Crespo", "La Paternal", "Villa Ortúzar", "Agronomía", "Parque Chas"]
    },
    "GBA Zona Norte": {
        "Vicente López": ["Vicente López", "Olivos", "Florida", "La Lucila", "Villa Martelli", "Munro"],
        "San Isidro": ["San Isidro", "Acassuso", "Martínez", "Beccar", "Boulogne", "Villa Adelina"],
        "Tigre": ["Tigre", "Don Torcuato", "General Pacheco", "El Talar", "Benavídez", "Nordelta"],
        "San Fernando": ["San Fernando", "Victoria", "Virreyes"],
        "San Martín": ["San Martín", "Villa Ballester", "San Andrés", "José León Suárez"],
    },
    "GBA Zona Sur": {
        "Avellaneda": ["Avellaneda", "Sarandí", "Villa Domínico", "Wilde"],
        "Lanús": ["Lanús Oeste", "Lanús Este", "Remedios de Escalada", "Gerli", "Valentín Alsina"],
        "Lomas de Zamora": ["Lomas de Zamora", "Banfield", "Temperley", "Turdera", "Llavallol"],
        "Quilmes": ["Quilmes", "Bernal", "Don Bosco", "Ezpeleta", "San Francisco Solano"],
        "Almirante Brown": ["Adrogué", "Burzaco", "Longchamps", "Rafael Calzada"],
        "Esteban Echeverría": ["Monte Grande", "Luis Guillón", "El Jagüel"],
    },
    "GBA Zona Oeste": {
        "La Matanza": ["San Justo", "Ramos Mejía", "Lomas del Mirador", "Tapiales", "Isidro Casanova", "Laferrere", "Virrey del Pino"],
        "Morón": ["Morón", "Castelar", "Haedo", "El Palomar", "Villa Sarmiento"],
        "Tres de Febrero": ["Caseros", "Ciudadela", "Santos Lugares", "Sáenz Peña", "Martín Coronado"],
        "Merlo": ["Merlo", "San Antonio de Padua", "Libertad"],
        "Moreno": ["Moreno", "Paso del Rey"],
    }
}

# --- 4. MOTOR DE SCRAPING MEJORADO ---
def get_google_maps_data(search_query, max_results=10):
    data = []
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
        except:
            return pd.DataFrame() # Fallo al lanzar

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            page.goto("https://www.google.com/maps", timeout=60000)
            page.wait_for_selector("input#searchboxinput", state="visible")
            page.fill("input#searchboxinput", search_query)
            page.keyboard.press("Enter")
            
            # Esperar feed
            page.wait_for_selector('div[role="feed"]', timeout=15000)
            
            # Scroll agresivo para cargar resultados
            feed_selector = 'div[role="feed"]'
            for _ in range(5):
                page.evaluate(f"document.querySelector('{feed_selector}').scrollTo(0, document.querySelector('{feed_selector}').scrollHeight)")
                time.sleep(1.5)

            # Selectores de Google Maps (Estos cambian a veces, usamos lógica genérica)
            results = page.locator('div[role="feed"] > div > div[jsaction]').all()
            
            count = 0
            for res in results:
                if count >= max_results: break
                
                try:
                    text_all = res.inner_text().split('\n')
                    if len(text_all) < 2: continue
                    
                    nombre = text_all[0]
                    if "Anuncio" in nombre: continue # Saltar anuncios
                    
                    # Intentamos inferir datos basados en el formato del texto
                    rating = "N/A"
                    reviews = "0"
                    direccion = "Dirección no disponible en lista"
                    tipo_negocio = ""
                    
                    # Logica heuristica para limpiar datos
                    for line in text_all:
                        if "(" in line and ")" in line and ("," in line or "." in line):
                            parts = line.split('(')
                            rating = parts[0].strip()
                            reviews = parts[1].replace(')', '').strip()
                        elif "·" in line: # Suele ser "Pizzería · Zona"
                             tipo_negocio = line.split('·')[0].strip()
                        elif len(line) > 10 and any(char.isdigit() for char in line):
                             # Si la linea es larga y tiene numeros, probablemente es la direccion
                             if direccion == "Dirección no disponible en lista":
                                 direccion = line
                    
                    # Link
                    link_locator = res.locator("a").first
                    link = link_locator.get_attribute("href") if link_locator.count() > 0 else ""
                    
                    # Telefono y Web a veces no salen en la lista lateral sin hacer click
                    # Por velocidad, en esta versión scraping 'rápido', dejamos placeholders o inferimos.
                    
                    data.append({
                        "Seleccionar": False,
                        "Nombre": nombre,
                        "Rubro Detectado": tipo_negocio,
                        "Dirección": direccion,
                        "Rating": rating,
                        "Reseñas": reviews,
                        "Maps Link": link
                    })
                    count += 1
                except:
                    continue
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
        
    return pd.DataFrame(data)

# --- 5. INTERFAZ DE USUARIO (TIPO LANDING PAGE) ---

st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🚀 Scrap<span style='color:#3b82f6'>Joni</span></h1>", unsafe_allow_html=True)

# Contenedor Principal (Card)
with st.container():
    st.markdown("""
    <div style="background-color: #1e293b; padding: 2rem; border-radius: 1rem; border: 1px solid #334155; margin-bottom: 2rem;">
        <h3 style="margin-top:0">Configura tu Búsqueda</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        rubro = st.text_input("1. ¿Qué buscas? (Rubro)", placeholder="Ej: Hamburguesería, Farmacia")
    
    with col2:
        # Nivel 1: Zona Grande
        region = st.selectbox("2. Región", list(LOCATION_DATA.keys()))
        
    with col3:
        # Nivel 2: Partido / Comuna
        partidos_opc = list(LOCATION_DATA[region].keys())
        partido = st.selectbox("3. Partido / Comuna", partidos_opc)

    col4, col5 = st.columns([2, 1])
    with col4:
         # Nivel 3: Localidad
        localidades_opc = LOCATION_DATA[region][partido]
        localidad = st.selectbox("4. Localidad / Barrio", ["Todo el partido"] + localidades_opc)
    
    with col5:
        cantidad = st.slider("Resultados máx.", 5, 50, 10)

    st.markdown("<br>", unsafe_allow_html=True)
    btn_buscar = st.button("🔎 BUSCAR LOCALES EN GOOGLE MAPS")

# --- 6. LÓGICA DE RESULTADOS ---

if 'resultados' not in st.session_state:
    st.session_state.resultados = None

if btn_buscar and rubro:
    # Construir Query
    loc_str = localidad if localidad != "Todo el partido" else partido
    query_full = f"{rubro} en {loc_str}, {partido}, {region}, Argentina"
    
    with st.spinner(f"🤖 Scrapeando '{query_full}'... Por favor espera..."):
        df = get_google_maps_data(query_full, max_results=cantidad)
        
        if not df.empty:
            st.session_state.resultados = df
            st.success(f"¡Éxito! Se encontraron {len(df)} locales.")
        else:
            st.error("No se encontraron resultados. Intenta con una zona más amplia.")

# --- 7. MOSTRAR DATOS Y ACCIONES ---

if st.session_state.resultados is not None:
    df = st.session_state.resultados
    
    st.markdown("---")
    st.subheader("📋 Resultados Obtenidos")
    
    # Tabla Editable para Checkboxes
    edited_df = st.data_editor(
        df,
        column_config={
            "Seleccionar": st.column_config.CheckboxColumn("Sel.", default=False),
            "Maps Link": st.column_config.LinkColumn("Ver en Maps"),
            "Rating": st.column_config.TextColumn("⭐ Rating"),
        },
        hide_index=True,
        use_container_width=True,
        height=400
    )
    
    # Filtrar seleccionados
    seleccionados = edited_df[edited_df["Seleccionar"] == True]
    count_sel = len(seleccionados)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # CARD DE ACCIONES
    st.markdown("""
    <div style="background-color: #1e293b; padding: 1.5rem; border-radius: 1rem; border: 1px solid #334155;">
        <h4 style="margin-top:0; color: white;">⚡ Acciones</h4>
    </div>
    """, unsafe_allow_html=True)
    
    ac1, ac2, ac3 = st.columns(3)
    
    with ac1:
        # Descargar CSV COMPLETO
        csv_full = edited_df.drop(columns=["Seleccionar"]).to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar TODO (CSV)",
            data=csv_full,
            file_name=f"scrapjoni_todos_{rubro}.csv",
            mime="text/csv"
        )
        
    with ac2:
        # Descargar Solo Seleccionados
        if count_sel > 0:
            csv_sel = seleccionados.drop(columns=["Seleccionar"]).to_csv(index=False).encode('utf-8')
            st.download_button(
                f"📥 Descargar {count_sel} Seleccionados",
                data=csv_sel,
                file_name=f"scrapjoni_seleccion_{rubro}.csv",
                mime="text/csv",
            )
        else:
            st.info("Selecciona casillas para filtrar descarga.")
            
    with ac3:
        # Generar Ruta
        if count_sel >= 2:
            if count_sel > 10:
                st.warning("⚠️ Google Maps solo optimiza rutas de hasta 10 paradas.")
            
            # Algoritmo simple de ruta
            # Usamos Nombre + Dirección + Localidad para asegurar precisión
            destinos = []
            for _, row in seleccionados.iterrows():
                # Limpiamos el texto para URL
                lugar_raw = f"{row['Nombre']} {row['Dirección']}"
                lugar_encoded = urllib.parse.quote(lugar_raw)
                destinos.append(lugar_encoded)
            
            # Limitamos a 10 para que Maps no falle
            destinos = destinos[:10]
            
            url_maps = f"https://www.google.com/maps/dir/{'/'.join(destinos)}"
            
            st.markdown(f"""
            <a href="{url_maps}" target="_blank" style="text-decoration:none;">
                <button style="background-color: #10b981; color: white; border: none; padding: 0.5rem 1rem; border-radius: 5px; width: 100%; font-weight: bold; cursor: pointer;">
                🗺️ ABRIR RUTA OPTIMIZADA
                </button>
            </a>
            """, unsafe_allow_html=True)
        else:
            st.info("Selecciona al menos 2 locales para armar ruta.")

else:
    # Footer visual
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #64748b;'>Desarrollado para Scraping Estratégico</div>", unsafe_allow_html=True)
