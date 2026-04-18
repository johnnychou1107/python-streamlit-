- **AI 動態參數檢索**：整合 Google Gemini API，使用者僅需輸入化學式，系統即可自動檢索對應的 $K_a$ 或 $K_b$ 與價數。
- **高精確度數值演算**：捨棄傳統近似公式，針對緩衝區與當量點採用二次方程式求根，精確捕捉解離平衡細節。
- **互動式視覺化介面**：利用 Plotly 產出可動態縮放、標記關鍵點（當量點、半當量點）的滴定曲線圖。
- **雙向滴定支援**：支援「已知鹼滴定酸」與「已知酸滴定鹼」雙模式切換。

- **Frontend/Deployment**: Streamlit
- **Numerical Processing**: NumPy, Pandas
- **Visualization**: Plotly
- **AI Backend**: Google Generative AI (Gemini)
