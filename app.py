import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets.get("SUPABASE_URL", "TU_URL")
KEY = st.secrets.get("SUPABASE_KEY", "TU_KEY")
supabase: Client = create_client(URL, KEY)

st.set_page_config(page_title="Nuestra App Custom", layout="wide")

# --- FUNCIONES CORE ---
def obtener_items(categoria):
    res = supabase.table('couple_data').select("*").eq('category', categoria).execute()
    return res.data

def guardar_item(categoria, contenido):
    supabase.table('couple_data').insert({"category": categoria, "content": contenido}).execute()

# --- INTERFAZ DINÁMICA ---
st.title("🛠️ Panel de Control Nacho & Fran")

menu = st.sidebar.selectbox("Seleccionar Módulo", ["Dashboard", "Personalizador de Campos", "Registrar Datos", "Álbum y Archivos"])

if menu == "Personalizador de Campos":
    st.header("✨ Crea nuevos espacios")
    st.info("Aquí defines qué campos quieres que tenga tu próximo registro (ej: 'Color', 'Ubicación', 'Calificación')")
    
    nuevo_modulo = st.text_input("Nombre del nuevo módulo (ej: Mis Restaurantes)")
    campos = st.text_area("Nombres de los campos (separados por coma)", placeholder="Nombre, Dirección, Precio, Nota")
    
    if st.button("Crear Módulo"):
        lista_campos = [c.strip() for c in campos.split(",")]
        # Guardamos la configuración del módulo en una categoría especial 'config'
        guardar_item("config_modulos", {"nombre": nuevo_modulo, "campos": lista_campos})
        st.success(f"¡Módulo {nuevo_modulo} creado con éxito!")

elif menu == "Registrar Datos":
    st.header("📝 Registro de Actividades")
    
    # Cargamos los módulos que hemos creado dinámicamente
    modulos_config = obtener_items("config_modulos")
    opciones_modulos = [m['content']['nombre'] for m in modulos_config]
    
    if not opciones_modulos:
        st.warning("Aún no has creado módulos. Ve a 'Personalizador de Campos'.")
    else:
        seleccion = st.selectbox("¿Qué quieres registrar hoy?", opciones_modulos)
        
        # Buscamos los campos de ese módulo
        config_actual = next(m for m in modulos_config if m['content']['nombre'] == seleccion)
        campos_a_llenar = config_actual['content']['campos']
        
        # Generamos el formulario dinámicamente
        nuevo_registro = {}
        with st.form("dynamic_form"):
            st.write(f"### Nuevo ingreso para: {seleccion}")
            for campo in campos_a_llenar:
                nuevo_registro[campo] = st.text_input(campo)
            
            if st.form_submit_button("Guardar Registro"):
                guardar_item(f"data_{seleccion}", nuevo_registro)
                st.success("¡Datos guardados!")

elif menu == "Dashboard":
    st.header("📊 Ver nuestros datos")
    modulos_config = obtener_items("config_modulos")
    
    for mod in modulos_config:
        nombre_mod = mod['content']['nombre']
        with st.expander(f"Ver {nombre_mod}"):
            datos_raw = obtener_items(f"data_{nombre_mod}")
            if datos_raw:
                # Convertimos el JSON de Supabase en una tabla bonita de Pandas
                df = pd.DataFrame([d['content'] for d in datos_raw])
                st.table(df)
                
                # BOTÓN DESCARGABLE
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(f"Descargar {nombre_mod} (CSV)", csv, f"{nombre_mod}.csv", "text/csv")
            else:
                st.write("No hay datos aún.")
