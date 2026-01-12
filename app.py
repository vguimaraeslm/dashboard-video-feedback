import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import ast

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Monitor de Qualidade", layout="wide", page_icon="🎬")

# --- CSS PARA ESTILO "ENVATO / SAAS MODERNO" ---
st.markdown("""
<style>
    /* Remove padding excessivo do topo */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Estilo dos Cards (Caixas Brancas com Sombra) */
    .stPlotlyChart, div[data-testid="stMetric"], div.stDataFrame {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #E5E7EB;
    }

    /* Títulos mais limpos */
    h1, h2, h3 {
        color: #111827;
        font-family: 'Inter', sans-serif;
    }
    
    /* Ajuste nas métricas para ficarem centralizadas e bonitas */
    div[data-testid="stMetric"] {
        text-align: center;
        background-color: #FFFFFF; 
    }
    
    /* Cor do valor da métrica */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #4F46E5; /* Cor Indigo */
    }

    /* Fundo da Sidebar mais limpo */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O BANCO ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=60)
def get_data():
    response = supabase.table("video_feedbacks").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        
        def limpar_topico(x):
            try:
                val = ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x
                if isinstance(val, list) and len(val) > 0:
                    return val[0]
                return str(val)
            except:
                return str(x)
        
        if 'ai_category_topic' in df.columns:
            df['ai_category_topic'] = df['ai_category_topic'].apply(limpar_topico)
            
    return df

df = get_data()

# --- BARRA LATERAL (Clean) ---
st.sidebar.markdown("### 🎛️ Filtros")
dias = st.sidebar.slider("Período (Dias)", 1, 90, 30)

# Lógica de Filtro
if not df.empty:
    data_corte = pd.Timestamp.now(tz=df['created_at'].dt.tz) - pd.Timedelta(days=dias)
    df_filtrado = df[df['created_at'] >= data_corte].copy()
    
    todas_marcas = sorted(df_filtrado['video_marca'].dropna().unique())
    marca_sel = st.sidebar.multiselect("Marcas", todas_marcas, default=todas_marcas)
    
    if marca_sel:
        df_filtrado = df_filtrado[df_filtrado['video_marca'].isin(marca_sel)]
else:
    df_filtrado = pd.DataFrame()

# Se estiver vazio
if df_filtrado.empty:
    st.warning("Sem dados para o período selecionado.")
    st.stop()

# --- DASHBOARD ---

# Cabeçalho simples
st.title("Analytics de Qualidade")
st.markdown(f"<span style='color: #6B7280'>Monitoramento de ajustes nos últimos {dias} dias</span>", unsafe_allow_html=True)
st.markdown("---")

# 1. KPIs (CARDS)
col1, col2, col3, col4 = st.columns(4)

total = len(df_filtrado)
videos = df_filtrado['file_name'].nunique()
resolvidos = len(df_filtrado[df_filtrado['status'] == 'Resolvido']) if 'status' in df_filtrado.columns else 0
pendentes = total - resolvidos
taxa = (resolvidos/total*100) if total else 0

col1.metric("Total de Ajustes", total)
col2.metric("Vídeos Impactados", videos)
col3.metric("Pendentes", pendentes)
col4.metric("Taxa de Resolução", f"{taxa:.0f}%")

st.markdown("###") # Espaço extra

# 2. HEATMAP (Visual Limpo)
st.subheader("Onde estão os gargalos?")
if 'ai_category_topic' in df_filtrado.columns:
    heatmap_data = df_filtrado.groupby(['video_marca', 'ai_category_topic']).size().reset_index(name='Quantidade')
    
    if not heatmap_data.empty:
        fig_heat = px.density_heatmap(
            heatmap_data, 
            x="video_marca", 
            y="ai_category_topic", 
            z="Quantidade", 
            color_continuous_scale=["#EEF2FF", "#6366F1", "#312E81"], # Gradiente Azul/Roxo Profissional
        )
        # Limpeza visual do gráfico
        fig_heat.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(t=0, l=0, r=0, b=0)
        )
        st.plotly_chart(fig_heat, use_container_width=True, key="heatmap_v2")

# 3. GRÁFICOS LADO A LADO
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Top Motivos de Ajuste")
    top_motivos = df_filtrado['ai_category_topic'].value_counts().head(8).sort_values(ascending=True)
    
    fig_bar = px.bar(
        top_motivos, 
        orientation='h', 
        text_auto=True,
        color_discrete_sequence=['#4F46E5'] # Indigo
    )
    fig_bar.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title=None, 
        yaxis_title=None, 
        showlegend=False,
        margin=dict(t=0, l=0, r=0, b=0)
    )
    st.plotly_chart(fig_bar, use_container_width=True, key="bar_motivos_v2")

with col_right:
    st.subheader("Volume por Marca")
    top_marcas = df_filtrado['video_marca'].value_counts().head(8).sort_values(ascending=True)
    
    fig_vol = px.bar(
        top_marcas, 
        orientation='h', 
        text_auto=True,
        color_discrete_sequence=['#10B981'] # Verde Esmeralda para diferenciar
    )
    fig_vol.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title=None, 
        yaxis_title=None, 
        showlegend=False,
        margin=dict(t=0, l=0, r=0, b=0)
    )
    st.plotly_chart(fig_vol, use_container_width=True, key="bar_marcas_v2")

# 4. TABELA
st.markdown("###")
with st.expander("Ver Dados Detalhados"):
    cols = ['created_at', 'video_marca', 'ai_category_topic', 'ai_summary', 'status']
    cols = [c for c in cols if c in df_filtrado.columns]
    st.dataframe(df_filtrado[cols].sort_values('created_at', ascending=False), use_container_width=True, hide_index=True)