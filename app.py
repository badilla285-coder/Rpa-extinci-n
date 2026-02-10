import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Se recomienda usar st.secrets para mayor seguridad en producción
URL = st.secrets.get("SUPABASE_URL", "TU_URL_AQUÍ")
KEY = st.secrets.get("SUPABASE_KEY", "TU_KEY_AQUÍ")
supabase: Client = create_client(URL, KEY)

# --- ESTÉTICA PERSONALIZADA ---
st.set_page_config(page_title="Us ❤️ | Planner", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }
    .main { background-color: #fdf2f4; }
    div[data-testid="stExpander"] { border: none; background-color: white; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .stButton>button { width: 100%; border-radius: 25px; background-color: #ff4b6b; color: white; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #ff758c; transform: scale(1.02); }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE DATOS ---
def load_data(category):
    try:
        res = supabase.table('couple_data').select("*").eq('category', category).order('created_at', desc=True).execute()
        return res.data
    except: return []

def save_data(category, content):
    data = {"category": category, "content": content, "created_at": str(datetime.now())}
    supabase.table('couple_data').insert(data).execute()

# --- INTERFAZ ---
st.title("🍓 Nuestro Planner Dinámico")

tabs = st.tabs(["📌 Tareas & Metas", "💰 Ahorros", "✈️ Viajes", "🗓️ Calendario", "📸 Álbum", "⚙️ Config"])

# --- TAB 1: TAREAS (DINÁMICO) ---
with tabs[0]:
    st.subheader("Checklist de Vida")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        task_text = st.text_input("¿Qué haremos hoy?", placeholder="Ej: Ir al cine, comprar departamento...")
    with col_b:
        task_type = st.selectbox("Tipo", ["Tarea", "Meta", "Salida"])
    
    if st.button("✨ Registrar Actividad"):
        save_data("actividades", {"nombre": task_text, "tipo": task_type, "status": False})
        st.success("¡Agregado!")
        st.rerun()

    items = load_data("actividades")
    for item in items:
        c = item['content']
        col1, col2 = st.columns([0.8, 0.2])
        is_done = col1.checkbox(f"{c['tipo']}: {c['nombre']}", value=c['status'], key=item['id'])
        # Aquí podrías añadir lógica para actualizar el status en Supabase

# --- TAB 2: AHORROS (CON HISTORIAL) ---
with tabs[1]:
    st.subheader("Nuestra Libertad Financiera")
    ahorros = load_data("ahorro")
    total = sum([float(a['content']['monto']) for a in ahorros])
    st.metric("Total en la cuenta", f"${total:,.0f} CLP")
    
    with st.expander("➕ Registrar nuevo aporte"):
        monto = st.number_input("Monto $", min_value=0)
        quien = st.radio("¿Quién ahorró?", ["Nacho", "Francisca", "Ambos"])
        motivo = st.text_input("Motivo/Meta")
        if st.button("Confirmar Aporte"):
            save_data("ahorro", {"monto": monto, "quien": quien, "motivo": motivo})
            st.balloons()
            st.rerun()

# --- TAB 3: VIAJES & SALIDAS ---
with tabs[2]:
    st.subheader("Próximos Destinos")
    with st.form("form_viajes"):
        destino = st.text_input("Lugar")
        fecha_p = st.date_input("Fecha estimada")
        presupuesto = st.number_input("Presupuesto estimado", min_value=0)
        items_viaje = st.text_area("Cosas que llevar / Lugares que ver (separados por coma)")
        if st.form_submit_button("Guardar Plan de Viaje"):
            save_data("viajes", {"destino": destino, "fecha": str(fecha_p), "presupuesto": presupuesto, "check": items_viaje})
            st.rerun()

# --- TAB 5: ÁLBUM (STORAGE) ---
with tabs[4]:
    st.subheader("Nuestros Recuerdos")
    # Nota: Aquí se requiere integrar Supabase Storage para subir archivos reales.
    # Por ahora, usamos una galería de registros.
    foto_url = st.text_input("URL de la foto (o súbela en Config)")
    nota_foto = st.text_area("¿Qué sentiste este día?")
    if st.button("Añadir al recuerdo"):
        save_data("fotos", {"url": foto_url, "nota": nota_foto})
        st.rerun()
