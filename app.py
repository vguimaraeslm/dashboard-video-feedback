import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import ast

# --- 1. CONFIGURAÇÃO E ESTILO CLEAN ---
st.set_page_config(page_title="Painel de Vídeo", layout="wide", page_icon="📊")

st.markdown("""
<style>
    /* Fonte e Cores Básicas */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
        background-color: #F8F9FA;
        color: #212529;
    }
    
    /* Cartões de KPI e Gráficos com borda suave */
    .st-emotion-cache-1r6slb0, .st-emotion-cache-1wivap2 {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #E9ECEF;
        padding: 16px;
    }
    
    /* Remover menu do deploy */
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO E DADOS ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except: return None

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
            
            def limpar(x):
                try:
                    val = ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x
                    if isinstance(val, list) and len(val) > 0: return val[0]
                    return str(val)
                except: return str(x)
            
            if 'ai_category_topic' in df.columns:
                df['ai_category_topic'] = df['ai_category_topic'].apply(limpar)
        return df
    except: return pd.DataFrame()

df = get_data()

# --- 3. FILTROS ---
st.sidebar.header("🔍 Filtros")

if df.empty:
    st.warning("Sem dados.")
    st.stop()

# Filtros
dias = st.sidebar.slider("Período (dias)", 7, 90, 30)
data_corte = pd.Timestamp.now(tz=df['created_at'].dt.tz) - pd.Timedelta(days=dias)
df_periodo = df[df['created_at'] >= data_corte].copy()

marcas_disp = sorted(df_periodo['video_marca'].dropna().unique())
sel_marcas = st.sidebar.multiselect("Marcas", marcas_disp, default=marcas_disp)

if sel_marcas:
    df_filtrado = df_periodo[df_periodo['video_marca'].isin(sel_marcas)]
else:
    df_filtrado = df_periodo

if not df_filtrado.empty:
    ajustes_disp = sorted(df_filtrado['ai_category_topic'].dropna().unique())
    sel_ajustes = st.sidebar.multiselect("Tipo de Ajuste", ajustes_disp, default=ajustes_disp)
    if sel_ajustes:
        df_filtrado = df_filtrado[df_filtrado['ai_category_topic'].isin(sel_ajustes)]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

# --- 4. DASHBOARD ---

st.title(f"📊 Relatório de Ajustes ({dias} dias)")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🏠 Visão Geral", "🆚 Comparar Marcas", "📅 Linha do Tempo"])

# --- ABA 1: VISÃO GERAL ---
with tab1:
    k1, k2, k3, k4 = st.columns(4)
    total = len(df_filtrado)
    resolvidos = len(df_filtrado[df_filtrado['status'] == 'Resolvido']) if 'status' in df_filtrado.columns else 0
    
    k1.metric("Total Ajustes", total)
    k2.metric("Vídeos", df_filtrado['file_name'].nunique())
    k3.metric("Marcas", df_filtrado['video_marca'].nunique())
    k4.metric("Resolvidos", f"{(resolvidos/total*100):.0f}%")
    
    st.markdown("###")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("O que mais pedem?")
        contagem = df_filtrado['ai_category_topic'].value_counts().reset_index()
        contagem.columns = ['Ajuste', 'Qtd']
        
        # MUDANÇA: Eixo X agora é Ajuste (Vertical) e bargap alto
        fig_bar = px.bar(
            contagem.head(10), 
            x='Ajuste', y='Qtd', 
            text_auto=True,
            color_discrete_sequence=['#4F46E5']
        )
        # bargap=0.7 deixa as barras bem finas
        fig_bar.update_layout(bargap=0.7, xaxis_title=None)
        st.plotly_chart(fig_bar, use_container_width=True, key="bar_top")

    with c2:
        st.subheader("Status")
        if 'status' in df_filtrado.columns:
            fig_pie = px.pie(
                df_filtrado, 
                names='status', 
                hole=0.6,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="pie_status")

# --- ABA 2: COMPARAÇÃO ---
with tab2:
    st.subheader("Volume por Marca")
    
    qtd_marca = df_filtrado['video_marca'].value_counts().reset_index()
    qtd_marca.columns = ['Marca', 'Total']
    
    # MUDANÇA: Vertical e fina
    fig_comp = px.bar(
        qtd_marca, 
        x='Marca', y='Total',
        text_auto=True,
        color='Total',
        color_continuous_scale='Blues'
    )
    fig_comp.update_layout(bargap=0.7, xaxis_title=None)
    st.plotly_chart(fig_comp, use_container_width=True, key="bar_comp")
    
    st.markdown("#### Detalhe dos Ajustes por Marca")
    fig_stack = px.histogram(
        df_filtrado, 
        x="video_marca", 
        color="ai_category_topic", 
        barmode='group',
        text_auto=True,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    # bargap aqui também
    fig_stack.update_layout(bargap=0.6, xaxis_title=None) 
    st.plotly_chart(fig_stack, use_container_width=True, key="bar_stack")

# --- ABA 3: TEMPO ---
with tab3:
    st.subheader("Evolução Diária")
    df_tempo = df_filtrado.set_index('created_at').resample('D').size().reset_index(name='Quantidade')
    
    fig_line = px.line(
        df_tempo, 
        x='created_at', y='Quantidade',
        markers=True,
        line_shape='spline'
    )
    fig_line.update_traces(line_color='#10B981', line_width=3)
    fig_line.update_layout(xaxis_title=None)
    st.plotly_chart(fig_line, use_container_width=True, key="line_time")

# --- TABELA ---
st.markdown("---")
with st.expander("📋 Ver Tabela de Dados"):
    cols = ['created_at', 'video_marca', 'ai_category_topic', 'status', 'ai_summary']
    st.dataframe(df_filtrado[cols].sort_values('created_at', ascending=False), use_container_width=True, hide_index=True)