import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import ast

# --- 1. CONFIGURAÇÃO E ESTILO CLEAN ---
st.set_page_config(page_title="Painel de Vídeo", layout="wide", page_icon="📊")

# CSS para limpar a interface (Fundo cinza claro, cartões brancos)
st.markdown("""
<style>
    /* Fonte e Cores Básicas */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
        background-color: #F8F9FA;
        color: #212529;
    }
    
    /* Cartões de KPI e Gráficos */
    .st-emotion-cache-1r6slb0, .st-emotion-cache-1wivap2 {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #E9ECEF;
        padding: 16px;
    }

    /* Ajuste de Títulos */
    h3 { font-size: 1.2rem; font-weight: 600; color: #495057; }
    
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
            
            # Limpeza simples de lista
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

# --- 3. BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔍 Filtros")

if df.empty:
    st.warning("Sem dados.")
    st.stop()

# 1. Filtro de Data (Slider simples)
dias = st.sidebar.slider("Período (últimos dias)", 7, 90, 30)
data_corte = pd.Timestamp.now(tz=df['created_at'].dt.tz) - pd.Timedelta(days=dias)
df_periodo = df[df['created_at'] >= data_corte].copy()

# 2. Filtro de Marca (Multiselect)
marcas_disp = sorted(df_periodo['video_marca'].dropna().unique())
sel_marcas = st.sidebar.multiselect("Selecione a(s) Marca(s)", marcas_disp, default=marcas_disp)

# Aplica filtro de marca
if sel_marcas:
    df_filtrado = df_periodo[df_periodo['video_marca'].isin(sel_marcas)]
else:
    df_filtrado = df_periodo

# 3. Filtro de Ajuste (Depende da Marca selecionada)
if not df_filtrado.empty:
    ajustes_disp = sorted(df_filtrado['ai_category_topic'].dropna().unique())
    sel_ajustes = st.sidebar.multiselect("Tipo de Ajuste", ajustes_disp, default=ajustes_disp)
    
    # Aplica filtro de ajuste
    if sel_ajustes:
        df_filtrado = df_filtrado[df_filtrado['ai_category_topic'].isin(sel_ajustes)]

# Se zerou tudo
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado com esses filtros.")
    st.stop()

# --- 4. DASHBOARD (ABAS) ---

st.title(f"📊 Relatório de Ajustes ({dias} dias)")
st.markdown("---")

# ABAS PARA ORGANIZAR
tab1, tab2, tab3 = st.tabs(["🏠 Visão Geral", "🆚 Comparar Marcas", "📅 Linha do Tempo"])

# --- ABA 1: VISÃO GERAL (O Básico que funciona) ---
with tab1:
    # KPIs Simples
    k1, k2, k3, k4 = st.columns(4)
    total = len(df_filtrado)
    resolvidos = len(df_filtrado[df_filtrado['status'] == 'Resolvido']) if 'status' in df_filtrado.columns else 0
    
    k1.metric("Total de Ajustes", total)
    k2.metric("Vídeos", df_filtrado['file_name'].nunique())
    k3.metric("Marcas Ativas", df_filtrado['video_marca'].nunique())
    k4.metric("Resolvidos", f"{(resolvidos/total*100):.0f}%")
    
    st.markdown("###") # Espaço
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("O que mais pedem?")
        # Gráfico de Barras Horizontal (Simples e direto)
        contagem = df_filtrado['ai_category_topic'].value_counts().reset_index()
        contagem.columns = ['Ajuste', 'Qtd']
        
        fig_bar = px.bar(
            contagem.head(10), 
            x='Qtd', y='Ajuste', 
            orientation='h', 
            text_auto=True,
            title="",
            color_discrete_sequence=['#4F46E5'] # Roxo padrão
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}) # Ordena do maior pro menor
        st.plotly_chart(fig_bar, use_container_width=True, key="graf_barras_top")

    with c2:
        st.subheader("Status dos Pedidos")
        # Gráfico de Rosca (Donut)
        if 'status' in df_filtrado.columns:
            fig_pie = px.pie(
                df_filtrado, 
                names='status', 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="graf_pizza_status")

# --- ABA 2: COMPARAÇÃO (Marcas) ---
with tab2:
    st.subheader("Comparativo: Quem demanda mais?")
    
    # Gráfico de Barras Vertical por Marca
    qtd_marca = df_filtrado['video_marca'].value_counts().reset_index()
    qtd_marca.columns = ['Marca', 'Total Ajustes']
    
    fig_comp = px.bar(
        qtd_marca, 
        x='Marca', y='Total Ajustes',
        text_auto=True,
        color='Total Ajustes',
        color_continuous_scale='Blues' # Escala azul simples
    )
    st.plotly_chart(fig_comp, use_container_width=True, key="graf_comp_marcas")
    
    st.markdown("#### Detalhe por Tipo de Ajuste")
    # Barras Empilhadas (Stacked Bar) - Ótimo para comparar composição
    fig_stack = px.histogram(
        df_filtrado, 
        x="video_marca", 
        color="ai_category_topic", 
        barmode='group', # Ou 'stack' se preferir empilhado
        text_auto=True,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    st.plotly_chart(fig_stack, use_container_width=True, key="graf_stack_marcas")

# --- ABA 3: TEMPO (Evolução) ---
with tab3:
    st.subheader("Evolução dos Pedidos no Tempo")
    
    # Agrupar por dia ou semana
    df_tempo = df_filtrado.set_index('created_at').resample('D').size().reset_index(name='Quantidade')
    
    fig_line = px.line(
        df_tempo, 
        x='created_at', y='Quantidade',
        markers=True,
        line_shape='spline' # Linha curva suave
    )
    fig_line.update_traces(line_color='#10B981', line_width=3) # Verde
    st.plotly_chart(fig_line, use_container_width=True, key="graf_linha_tempo")

# --- TABELA FINAL ---
st.markdown("---")
with st.expander("📋 Ver Dados Brutos (Tabela)"):
    colunas = ['created_at', 'video_marca', 'ai_category_topic', 'status', 'ai_summary']
    st.dataframe(
        df_filtrado[colunas].sort_values('created_at', ascending=False),
        use_container_width=True,
        hide_index=True
    )