import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO
import plotly.express as px

st.set_page_config(
    page_title="Rekonsiliasi Keuangan",
    layout="wide",
    page_icon="📊"
)

st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #f0f4f8;
    font-family: 'Segoe UI', sans-serif;
    color: #2c3e50;
}
.sidebar .sidebar-content {
    background-color: #eaf0f6;
    padding: 1.5em;
}
.stButton>button, .stDownloadButton>button {
    background-color: #4CAF50;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 0.5em 1.5em;
    margin-top: 10px;
}
.stDataFrame, .dataframe {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 1em;
}
.metric-container {
    display: flex;
    gap: 2em;
    justify-content: flex-start;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard Rekonsiliasi Pendapatan Ticketing")
st.markdown("""
Bandingkan dan cocokkan transaksi dari data Invoice dan Rekening Koran secara otomatis. 
Gunakan grafik dan tab untuk menganalisis transaksi yang cocok dan yang belum.
""")

# Sidebar upload
st.sidebar.header("📂 Upload File")
inv_file = st.sidebar.file_uploader("Upload Invoice (CSV/XLSX)", type=["csv", "xlsx"])
bank_file = st.sidebar.file_uploader("Upload Rekening Koran (CSV/XLSX)", type=["csv", "xlsx"])

@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

if inv_file and bank_file:
    df_inv = load_file(inv_file)
    df_bank = load_file(bank_file)

    for df in [df_inv, df_bank]:
        df.columns = df.columns.str.lower().str.strip()

    df_inv = df_inv.rename(columns={"tanggal": "date", "nominal": "amount", "deskripsi": "desc"})
    df_bank = df_bank.rename(columns={"tanggal": "date", "nominal": "amount", "deskripsi": "desc"})

    df_inv['date'] = pd.to_datetime(df_inv['date'])
    df_bank['date'] = pd.to_datetime(df_bank['date'])
    df_inv['amount'] = df_inv['amount'].astype(float)
    df_bank['amount'] = df_bank['amount'].astype(float)

    matched = []
    unmatched_inv = df_inv.copy()
    unmatched_bank = df_bank.copy()

    for idx_inv, row_inv in df_inv.iterrows():
        match = df_bank[
            (df_bank['amount'] == row_inv['amount']) &
            (df_bank['date'].between(row_inv['date'] - timedelta(days=1), row_inv['date'] + timedelta(days=1)))
        ]
        if not match.empty:
            match_row = match.iloc[0]
            matched.append({
                "invoice_date": row_inv['date'].strftime('%Y-%m-%d'),
                "bank_date": match_row['date'].strftime('%Y-%m-%d'),
                "amount": row_inv['amount'],
                "invoice_desc": row_inv['desc'],
                "bank_desc": match_row['desc']
            })
            unmatched_inv = unmatched_inv.drop(idx_inv)
            unmatched_bank = unmatched_bank.drop(match_row.name)

    df_matched = pd.DataFrame(matched)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Transaksi Cocok", len(df_matched))
    col2.metric("Invoice Belum Dibayar", len(unmatched_inv))
    col3.metric("Transaksi Bank Tidak Sesuai", len(unmatched_bank))

    # Visualisasi
    chart_data = pd.DataFrame({
        "Kategori": ["Matched", "Unmatched Invoice", "Unmatched Bank"],
        "Jumlah": [len(df_matched), len(unmatched_inv), len(unmatched_bank)]
    })
    fig = px.pie(chart_data, names='Kategori', values='Jumlah', title='Distribusi Transaksi')
    st.plotly_chart(fig, use_container_width=True)

    tab1, tab2, tab3 = st.tabs(["✅ Matched", "❌ Unmatched Invoice", "❌ Unmatched Bank"])

    with tab1:
        st.dataframe(df_matched, use_container_width=True)
    with tab2:
        st.dataframe(unmatched_inv, use_container_width=True)
    with tab3:
        st.dataframe(unmatched_bank, use_container_width=True)

    # Unduh Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_matched.to_excel(writer, sheet_name="Matched", index=False)
        unmatched_inv.to_excel(writer, sheet_name="Unmatched_Invoice", index=False)
        unmatched_bank.to_excel(writer, sheet_name="Unmatched_Bank", index=False)
        writer.close()

    st.download_button(
        label="💾 Unduh Hasil Rekonsiliasi (Excel)",
        data=buffer.getvalue(),
        file_name="rekonsiliasi_hasil.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("Silakan upload file invoice dan rekening koran untuk memulai.")
