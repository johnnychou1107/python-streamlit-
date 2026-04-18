import plotly
import streamlit as st
import google.generativeai as genai
import math 
import numpy as np 
import plotly.express as px
import pandas as pd
st.set_page_config(page_title="滴定曲線模擬器", layout="wide")

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
genai.configure(api_key="AIzaSyD25nsFNf5-pIDwS8UocDNzlz5dIWuY9rA")

def get_chem_info(name, type="acid"):
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"請查詢化學物質'{name}'的{type}價數(n)與{'Ka' if type=='acid' else 'Kb'}值。請嚴格遵守回傳格式:'n,數值'，不要有任何文字。例如回傳'1,1.8e-5'。如果是強酸或強鹼，數值請填 1000。"

    try:
        response=model.generate_content(prompt)
        result=response.text.strip().split(",")
        n=int(result[0])
        k=float(result[1])
        return n, k
    except Exception as e:
        st.error(f"AI查詢錯誤: {e}|AI回傳原始文字: {response.text if 'response' in locals() else '無回應'}")
        return 1,1000.0

def get_ph(v_titrant,v_analyte,m_analyte,m_titrant,k_analyte,na,nb,mode):
    kw=1e-14
    is_excess = False
    mol_analyte_initial = m_analyte * v_analyte * (na if mode=="已知鹼滴定酸" else nb) / 1000
    mol_titrant_added = m_titrant * v_titrant * (nb if mode=="已知鹼滴定酸" else na) / 1000

    if k_analyte >= 1000:   # 強酸或強鹼
        if mol_titrant_added < mol_analyte_initial:
            conc=(mol_analyte_initial - mol_titrant_added) / ((v_titrant+v_analyte)/1000)
        elif abs(mol_titrant_added - mol_analyte_initial)  < 1e-9:
            conc = 1e-7
        else:
            conc=(mol_titrant_added - mol_analyte_initial) / ((v_titrant+v_analyte)/1000)
            is_excess = True
        
    else:   # 弱酸或弱鹼
        if v_titrant< 1e-9:
            conc = math.sqrt(k_analyte*m_analyte)
            
        elif abs(mol_titrant_added - mol_analyte_initial)  < 1e-9:
            cs = mol_titrant_added / ((v_titrant+v_analyte)/1000)
            conc = (-(kw/k_analyte)+math.sqrt((kw/k_analyte)**2+4*cs*(kw/k_analyte)))/2
            is_excess = True
            
        elif mol_titrant_added < mol_analyte_initial:
            ca = (mol_analyte_initial - mol_titrant_added) / ((v_titrant+v_analyte)/1000)
            cb = mol_titrant_added / ((v_titrant+v_analyte)/1000)   
            # 解 [H+]^2 + (ka + cs)[H+] - ka * ca = 0
            a = 1
            b = k_analyte + cb
            c = -k_analyte * ca
            conc = (-b + math.sqrt(b**2 - 4*a*c)) / (2*a)
            
        else:
            excess_mol_base = mol_titrant_added - mol_analyte_initial
            conc = excess_mol_base / ((v_titrant+v_analyte)/1000)    
            is_excess = True   

    p_value = -math.log10(conc)
    
    if mode=="已知鹼滴定酸":
        return p_value if not is_excess else 14 - p_value
    else:
        return 14 - p_value if not is_excess else p_value

def get_curve_data(acid_vol, acid_conc, base_vol, base_conc, na, nb, ka, kb, mode):
    target_v = base_vol if mode=="已知鹼滴定酸" else acid_vol
    current_k = ka if mode=="已知鹼滴定酸" else kb
    v_range = np.linspace(0, target_v*2, 500)
    ph_list =[]

    for v in v_range:
        ph = get_ph(v, acid_vol if mode=="已知鹼滴定酸" else base_vol, 
                    acid_conc if mode=="已知鹼滴定酸" else base_conc, 
                    base_conc if mode=="已知鹼滴定酸" else acid_conc, 
                    current_k, na, nb, mode)
        ph_list.append(ph)
    return pd.DataFrame({"體積 (mL)": v_range, "pH": ph_list})

import plotly.express as px

def draw_titration_plot(df, mode, v_eq, ph_eq, v_half, ph_half):
    fig = px.line(df, x="體積 (mL)", y="pH", 
                  title=f"化學滴定模擬曲線 ({mode})",
                  labels={"體積 (mL)": "滴入體積 (mL)", "pH": "溶液 pH 值"})
    
    fig.update_traces(
        line=dict(width=3, color='#1f77b4'), 
        hovertemplate="<b>滴入體積</b>: %{x:.2f} mL<br><b>pH 值</b>: %{y:.2f}<extra></extra>"
    )
   
    fig.update_yaxes(range=[0, 14], dtick=2)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightPink')
    fig.add_scatter(
        x=[v_eq], y=[ph_eq],
        mode="markers+text",
        name="當量點",
        text=["當量點"],
        textposition="top center",
        marker=dict(color="red", size=12, symbol="star")
    )
    if v_half>0:
        fig.add_scatter(
            x=[v_half], y=[ph_half],
            mode="markers+text",
            name="半當量點",
            text=["半當量點"],
            textposition="bottom center",
            marker=dict(color="green", size=12, symbol="star")
        )
    fig.update_layout(showlegend=True)
    return fig


st.title("🧪 化學滴定模擬器")
st.info(("""
**💡 使用說明**
1. 輸入化學式後點擊「AI 獲取數據」，接著調整濃度與體積即可產出圖表。
2. 目前支援的化學物質：`HCl`、`H2SO4`、`H3PO4`、`CH3COOH`、`NaOH`、`Ca(OH)2`、`NH3`。
3. 如果輸入其他化學式，系統將預設其為強酸或強鹼 (Ka/Kb = 1000)。
4. 若需精確查詢，請務必點擊 **「AI 獲取數據」**。
"""))

with st.container(border=True):
    is_acid_into_base = st.toggle(
        "切換滴定方向：左（鹼滴酸） / 右（酸滴鹼）", 
        value=False
    )
    mode = "已知酸滴定鹼" if is_acid_into_base else "已知鹼滴定酸"
    st.write(f"當前模式：**:blue[{mode}]**")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📍 待測物配置 (Analyte)") 
    if mode == "已知鹼滴定酸":
        acid_name = st.text_input("請輸入酸的化學式", value="hcl").lower().strip()
    else:
        base_name = st.text_input("請輸入鹼的化學式", value="naoh").lower().strip()
    


with col2:
    st.subheader("📍 滴定劑配置 (Titrant)")
    if mode == "已知鹼滴定酸":
        base_name = st.text_input("請輸入鹼的化學式", value="naoh").lower().strip()
    else:
        acid_name = st.text_input("請輸入酸的化學式", value="hcl").lower().strip()
    if st.button("使用AI獲取詳細數據"):
        with st.spinner("查詢中..."):
            aina, aika = get_chem_info(acid_name, "acid")
            ainb, aikb = get_chem_info(base_name, "base")
            st.session_state['n_a']=aina
            st.session_state['k_a']=aika
            st.session_state['n_b']=ainb
            st.session_state['k_b']=aikb
            st.success(f"AI查詢完成！{acid_name}的n為{aina}，Ka為{aika}；{base_name}的n為{ainb}，Kb為{aikb}")
        pass

st.divider()
base_db={
    "naoh": {"n": 1, "kb": 1000},
    "ca(oh)2": {"n": 2, "kb": 1000},
    "nh3": {"n": 1, "kb": 1.8e-5}    
}
acid_db={
    "hcl": {"n": 1, "ka": 1000},
    "h2so4": {"n": 2, "ka": 1000},
    "h3po4": {"n": 3, "ka": 7.5e-3},
    "ch3cooh": {"n": 1, "ka": 1.8e-5}, 
}



if 'last_base' not in st.session_state or st.session_state['last_base']!=base_name:
    base_info = base_db.get(base_name, {"n": 1, "kb": 1000})
    st.session_state['n_b']=base_info['n']
    st.session_state['k_b']=base_info['kb']
    st.session_state['last_base']=base_name


if 'last_acid' not in st.session_state or st.session_state['last_acid']!=acid_name:
    acid_info = acid_db.get(acid_name, {"n": 1, "ka": 1000})
    st.session_state['n_a']=acid_info['n']
    st.session_state['k_a']=acid_info['ka']
    st.session_state['last_acid']=acid_name



current_info = {
    "acid": {"n": st.session_state['n_a'], "k": st.session_state['k_a']},
    "base": {"n": st.session_state['n_b'], "k": st.session_state['k_b']}
}

st.write(f"偵測到{base_name}，其價數為: {current_info['base']['n']}，Kb值為: {current_info['base']['k']}")
st.write(f"偵測到{acid_name}，其價數為: {current_info['acid']['n']}，Ka值為: {current_info['acid']['k']}")
tab1, tab2, tab3 = st.tabs(["滴定曲線模擬", "原始數據報表", "化學原理"])

with tab1:
    if mode=="已知鹼滴定酸":
        st.subheader("已知鹼滴定酸")
        base_vol = st.number_input("滴定管耗用體積 (ml):", value=20.0)
        base_conc = st.number_input("鹼的濃度 (M):", value=0.1)
        acid_vol = st.number_input("酸的體積 (mL):", value=50.0)
        if st.button("計算"):
            acid_conc=(base_vol * base_conc * current_info['base']['n']) / (acid_vol * current_info['acid']['n'])
            st.success(f"酸的濃度為: {acid_conc:.4f} M")
            st.subheader("滴定曲線模擬")
            with st.spinner("模擬滴定曲線中..."):
                v_eq=(acid_vol * current_info['acid']['n']*acid_conc) / (base_conc * current_info['base']['n'])
                v_half=v_eq/2
                ph_eq = get_ph(v_eq, acid_vol, acid_conc, base_conc, current_info['acid']['k'], current_info['acid']['n'], current_info['base']['n'], mode)
                if current_info['acid']['k']<100:
                    ph_half = get_ph(v_half, acid_vol, acid_conc, base_conc, current_info['acid']['k'], current_info['acid']['n'], current_info['base']['n'], mode)
                else:
                    v_half, ph_half = 0, 0
                curve_data = get_curve_data(acid_vol, acid_conc, base_vol, base_conc, 
                                            current_info['acid']['n'], current_info['base']['n'],
                                            current_info['acid']['k'], current_info['base']['k'], mode)
                st.session_state['curve_data']=curve_data
                fig = draw_titration_plot(curve_data, mode, v_eq, ph_eq, v_half, ph_half)
                st.plotly_chart(fig, use_container_width=True)

    elif mode=="已知酸滴定鹼":
        st.subheader("已知酸滴定鹼")
        acid_vol = st.number_input("滴定管耗用體積 (ml):", value=20.0)
        acid_conc = st.number_input("酸的濃度 (M):", value=0.1)
        base_vol = st.number_input("鹼的體積 (mL):", value=50.0)
        if st.button("計算"):
            base_conc=(acid_vol * acid_conc * current_info['acid']['n']) / (base_vol * current_info['base']['n'])
            st.success(f"鹼的濃度為: {base_conc:.4f} M")
            st.subheader("滴定曲線模擬")
            with st.spinner("模擬滴定曲線中..."):
                v_eq=(base_vol * current_info['base']['n']*base_conc) / (acid_conc * current_info['acid']['n'])
                v_half=v_eq/2
                ph_eq = get_ph(v_eq, base_vol, base_conc, acid_conc, current_info['base']['k'], current_info['acid']['n'], current_info['base']['n'], mode)
                if current_info['base']['k']<100:
                    ph_half = get_ph(v_half, base_vol, base_conc, acid_conc, current_info['base']['k'], current_info['acid']['n'], current_info['base']['n'], mode)
                else:
                    v_half, ph_half = 0, 0
                curve_data = get_curve_data(acid_vol, acid_conc, base_vol, base_conc, 
                                            current_info['acid']['n'], current_info['base']['n'],
                                            current_info['acid']['k'], current_info['base']['k'], mode)
                st.session_state['curve_data']=curve_data
                fig = draw_titration_plot(curve_data, mode, v_eq, ph_eq, v_half, ph_half)
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("📊 數據詳細清單")
    if 'curve_data' in st.session_state:
        st.dataframe(st.session_state['curve_data'], use_container_width=True)
    else:
        st.warning("請先在「滴定曲線模擬」分頁點擊計算。")

with tab3:
    st.subheader("📖 滴定原理與演算法")
    st.markdown("""
    本模擬器採用 **精確二次方程式公式解**：
    1. **緩衝區**：解 $[H^+]^2 + (K_a + C_s)[H^+] - K_a C_a = 0$。
    2. **當量點**：考慮共軛酸鹼水解平衡。
    3. **AI 功能**：串接 Google Gemini API 獲取最新的 $K_a$ / $K_b$ 數據。
    """)

