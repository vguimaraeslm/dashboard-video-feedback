import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import ast

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Monitor de Qualidade de Vídeo", layout="wide", page_icon="🎬")

# --- ESTILO CSS PERSONALIZADO (Para dar um ar mais "Pro") ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
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
    st.error(f"Erro de conexão com o Supabase: {e}")
    st.stop()

# --- CARREGAMENTO DE DADOS (ATUALIZADO PARA 60 SEGUNDOS) ---
@st.cache_data(ttl=60)  # <--- MUDANÇA AQUI: Cache de 1 minuto
def get_data():
    response = supabase.table("video_feedbacks").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Limpeza robusta de tópicos
        def limpar_topico(x):
            try:
                # Se for lista ou string parecida com lista
                val = ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x
                if isinstance(val, list) and len(val) > 0:
                    return val[0] # Pega o primeiro tópico
                return str(val)
            except:
                return str(x)
        
        if 'ai_category_topic' in df.columns:
            df['ai_category_topic'] = df['ai_category_topic'].apply(limpar_topico)
            
    return df

# Carrega dados
with st.spinner('Atualizando dados...'):
    df = get_data()

if df.empty:
    st.info("Aguardando dados... Nenhuma solicitação encontrada no banco.")
    st.stop()

# --- BARRA LATERAL (FILTROS INTELIGENTES) ---
st.sidebar.title("Filtros")

# Filtro de Data (Últimos X dias é mais útil que mês fixo)
dias = st.sidebar.slider("Período de Análise (Dias)", 1, 90, 30)
data_corte = pd.Timestamp.now(tz=df['created_at'].dt.tz) - pd.Timedelta(days=dias)
df_filtrado = df[df['created_at'] >= data_corte].copy()

# Filtro de Marca
todas_marcas = sorted(df_filtrado['video_marca'].dropna().unique())
marca_sel = st.sidebar.multiselect("Filtrar Marcas", todas_marcas, default=todas_marcas)

if marca_sel:
    df_filtrado = df_filtrado[df_filtrado['video_marca'].isin(marca_sel)]

# --- DASHBOARD PRINCIPAL ---

st.title("🎬 Monitor de Ajustes de Vídeo")
st.markdown(f"Analisando solicitações dos últimos **{dias} dias**.")
st.divider()

# 1. KPIs DE TOPO
col1, col2, col3, col4 = st.columns(4)
total_solicitacoes = len(df_filtrado)
total_videos = df_filtrado['file_name'].nunique()
resolvidos = len(df_filtrado[df_filtrado['status'] == 'Resolvido']) if 'status' in df_filtrado.columns else 0
pendentes = total_solicitacoes - resolvidos

col1.metric("Total de Ajustes", total_solicitacoes)
col2.metric("Vídeos Impactados", total_videos)
col3.metric("Ajustes Pendentes", pendentes, delta_color="inverse")
col4.metric("Taxa de Resolução", f"{(resolvidos/total_solicitacoes*100):.0f}%" if total_solicitacoes else "0%")

st.divider()

# 2. A VISÃO ESTRATÉGICA (HEATMAP)
# Cruzamento: Qual marca pede qual tipo de ajuste?
st.subheader("🔥 Mapa de Calor: Onde estão os problemas?")
st.markdown("Este gráfico mostra a concentração de pedidos. Quanto mais escuro, mais frequente é aquele tipo de ajuste para aquela marca.")

if not df_filtrado.empty and 'ai_category_topic' in df_filtrado.columns:
    # Cria uma tabela cruzada
    heatmap_data = df_filtrado.groupby(['video_marca', 'ai_category_topic']).size().reset_index(name='Quantidade')
    
    fig_heatmap = px.density_heatmap(
        heatmap_data, 
        x="video_marca", 
        y="ai_category_topic", 
        z="Quantidade", 
        color_continuous_scale="Reds",
        labels={"video_marca": "Marca", "ai_category_topic": "Tipo de Ajuste", "Quantidade": "Pedidos"}
    )
    fig_heatmap.update_layout(xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig_heatmap, use_container_width=True)

# 3. DETALHAMENTO (PARETO)
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Principais Motivos de Ajuste")
    # Gráfico de barras horizontais ordenado (Pareto)
    top_motivos = df_filtrado['ai_category_topic'].value_counts().head(10).sort_values(ascending=True)
    fig_motivos = px.bar(
        top_motivos, 
        orientation='h', 
        text_auto=True,
        color_discrete_sequence=['#FF4B4B'] # Cor padrão do Streamlit
    )
    fig_motivos.update_layout(xaxis_title="Quantidade", yaxis_title=None, showlegend=False)
    st.plotly_chart(fig_motivos, use_container_width=True)

with col_g2:
    st.subheader("Volume por Marca")
    # Gráfico de barras simples para volume
    top_marcas = df_filtrado['video_marca'].value_counts().head(10).sort_values(ascending=True)
    fig_marcas = px.bar(
        top_marcas, 
        orientation='h', 
        text_auto=True,
        color_discrete_sequence=['#1F77B4']
    )
    fig_marcas.update_layout(xaxis_title="Quantidade", yaxis_title=None, showlegend=False)
    st.plotly_chart(fig_marcas, use_container_width=True)

# 4. TABELA OPERACIONAL
st.divider()
with st.expander("📋 Ver Lista de Solicitações (Dados Brutos)"):
    cols_show = ['created_at', 'video_marca', 'video_versao', 'ai_category_topic', 'ai_summary', 'status']
    cols_final = [c for c in cols_show if c in df_filtrado.columns]
    
    st.dataframe(
        df_filtrado[cols_final].sort_values('created_at', ascending=False),
        use_container_width=True,
        hide_index=True
    )