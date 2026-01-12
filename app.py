import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import ast

# --- 1. CONFIGURAÇÃO INICIAL E FONTE ---
st.set_page_config(page_title="Analytics de Qualidade", layout="wide", page_icon="✨")

# --- 2. CSS AVANÇADO (Design System) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Reset Geral */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #F8FAFC; /* Slate 50 */
        color: #1E293B; /* Slate 800 */
    }

    /* Remove padding excessivo do topo */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* ESTILO DOS CARDS (KPIs) */
    .kpi-card {
        background-color: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        border: 1px solid #E2E8F0;
        text-align: left;
        height: 140px; /* Altura fixa para alinhamento perfeito */
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: transform 0.2s ease-in-out;
    }
    
    .kpi-card:hover {
        border-color: #6366F1;
        transform: translateY(-2px);
    }

    .kpi-label {
        font-size: 0.875rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 2.25rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1;
    }

    .kpi-sub {
        font-size: 0.875rem;
        color: #10B981;
        margin-top: 8px;
        font-weight: 500;
    }

    /* Container dos Gráficos */
    .chart-container {
        background-color: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
        margin-bottom: 24px;
    }
    
    /* Remove decorações padrão */
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
</style>
""", unsafe_allow_html=True)

# --- 3. CONEXÃO E DADOS ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

@st.cache_data(ttl=60)
def get_data():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("video_feedbacks").select("*").execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'])
            
            def limpar_topico(x):
                try:
                    val = ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x
                    if isinstance(val, list) and len(val) > 0: return val[0]
                    return str(val)
                except: return str(x)
            
            if 'ai_category_topic' in df.columns:
                df['ai_category_topic'] = df['ai_category_topic'].apply(limpar_topico)
        return df
    except:
        return pd.DataFrame()

df = get_data()

# --- 4. SIDEBAR ---
st.sidebar.markdown("### ⚙️ Configurações")
if not df.empty:
    dias = st.sidebar.slider("Janela de Tempo (Dias)", 1, 90, 30)
    data_corte = pd.Timestamp.now(tz=df['created_at'].dt.tz) - pd.Timedelta(days=dias)
    df_filtrado = df[df['created_at'] >= data_corte].copy()
    
    todas_marcas = sorted(df_filtrado['video_marca'].dropna().unique())
    marca_sel = st.sidebar.multiselect("Filtrar Marcas", todas_marcas, default=todas_marcas)
    if marca_sel:
        df_filtrado = df_filtrado[df_filtrado['video_marca'].isin(marca_sel)]
else:
    df_filtrado = pd.DataFrame()
    dias = 30

if df_filtrado.empty:
    st.warning("Sem dados para exibir. Tente ampliar o filtro de data.")
    st.stop()

# --- 5. DASHBOARD LAYOUT ---

st.markdown("## Overview de Qualidade")
st.markdown("---")

# CÁLCULO DE MÉTRICAS
total = len(df_filtrado)
videos_unicos = df_filtrado['file_name'].nunique()
resolvidos = len(df_filtrado[df_filtrado['status'] == 'Resolvido']) if 'status' in df_filtrado.columns else 0
taxa_res = (resolvidos/total*100) if total else 0
pendentes = total - resolvidos

# --- BLOCO DE KPIs (HTML PURO) ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total de Ajustes</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-sub" style="color: #64748B">Nos últimos {dias} dias</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Vídeos Únicos</div>
        <div class="kpi-value">{videos_unicos}</div>
        <div class="kpi-sub" style="color: #64748B">Analisados</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Ajustes Pendentes</div>
        <div class="kpi-value" style="color: #EF4444">{pendentes}</div>
        <div class="kpi-sub" style="color: #EF4444">Atenção requerida</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Taxa de Resolução</div>
        <div class="kpi-value" style="color: #10B981">{taxa_res:.0f}%</div>
        <div class="kpi-sub">Eficiência do fluxo</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("###")

# --- GRÁFICOS ---

col_main, col_sec = st.columns([2, 1]) 

with col_main:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("#### 🔥 Mapa de Calor: Marcas vs. Problemas")
    
    if 'ai_category_topic' in df_filtrado.columns:
        heat_data = df_filtrado.groupby(['video_marca', 'ai_category_topic']).size().reset_index(name='Qtd')
        
        # AQUI ESTAVA O ERRO: Mudamos de "Plum" para "Purples"
        fig_heat = px.density_heatmap(
            heat_data, x="video_marca", y="ai_category_topic", z="Qtd",
            color_continuous_scale="Purples", # <--- CORRIGIDO AQUI
        )
        fig_heat.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="", yaxis_title="",
            margin=dict(l=0, r=0, t=30, b=0),
            height=350
        )
        st.plotly_chart(fig_heat, use_container_width=True, key="heatmap_clean")
    st.markdown('</div>', unsafe_allow_html=True)

with col_sec:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown("#### 🏆 Top Motivos")
    
    top_issues = df_filtrado['ai_category_topic'].value_counts().head(6).sort_values(ascending=True)
    
    fig_bar = go.Figure(go.Bar(
        x=top_issues.values,
        y=top_issues.index,
        orientation='h',
        marker_color='#6366F1', # Indigo 500
        text=top_issues.values,
        textposition='auto',
    ))
    
    fig_bar.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=False),
        margin=dict(l=0, r=0, t=30, b=0),
        height=350,
        showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True, key="bar_clean")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TABELA DE DADOS ---
st.markdown('<div class="chart-container">', unsafe_allow_html=True)
st.markdown("#### 📋 Detalhamento Recente")

cols_view = ['created_at', 'video_marca', 'ai_category_topic', 'status', 'ai_summary']
if not df_filtrado.empty:
    df_display = df_filtrado[cols_view].sort_values('created_at', ascending=False).head(50)
    
    st.dataframe(
        df_display, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "created_at": st.column_config.DatetimeColumn("Data", format="DD/MM HH:mm"),
            "video_marca": "Marca",
            "ai_category_topic": "Tópico",
            "status": "Status",
            "ai_summary": "Resumo IA"
        }
    )
st.markdown('</div>', unsafe_allow_html=True)