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

# ===================== Custom CSS =====================
st.markdown("""
<style>
body {
    background-color: #f2f4f8;
    font-family: 'Segoe UI', sans-serif;
    color: #2c3e50;
}
.stButton>button, .stDownloadButton>button {
    background-color: #4CAF50;
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 6px;
    padding: 0.6em 1.5em;
    margin-top: 1em;
}
h1, h2, h3 {
    color: #1a2530;
}
</style>
""", unsafe_allow_html=True)

# ===================== Header =====================
st.title("📊 Dashboard Rekonsiliasi Keuangan")
st.markdown("""
Selamat datang di aplikasi rekonsiliasi keuangan.
Bandingkan file invoice dan rekening koran Anda untuk menemukan transaksi yang cocok dan tidak cocok.
""")

# ===================== Instructions =====================
with st.expander("📘 Cara Menggunakan Aplikasi", expanded=False):
    st.markdown("""
    - Siapkan dua file (CSV/XLSX) untuk invoice dan rekening koran
    - Kolom wajib: `tanggal`, `nominal`, dan `deskripsi`
    - Upload file di bawah
    - Lihat hasil rekonsiliasi dan unduh Excel hasilnya
    """)

# ===================== Upload Section =====================
st.header("📥 Upload Data")
col1, col2 = st.columns(2)
inv_file = col1.file_uploader("File Invoice", type=["csv", "xlsx"], key="invoice")
bank_file = col2.file_uploader("File Rekening Koran", type=["csv", "xlsx"], key="bank")

@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

# ===================== Process Logic =====================
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

    # ===================== Summary =====================
    st.header("📈 Ringkasan Rekonsiliasi")
    col1, col2, col3 = st.columns(3)
    col1.metric("Transaksi Cocok", len(df_matched))
    col2.metric("Invoice Belum Dibayar", len(unmatched_inv))
    col3.metric("Transaksi Bank Tidak Sesuai", len(unmatched_bank))

    chart_data = pd.DataFrame({
        "Kategori": ["Matched", "Unmatched Invoice", "Unmatched Bank"],
        "Jumlah": [len(df_matched), len(unmatched_inv), len(unmatched_bank)]
    })
    fig = px.pie(chart_data, names='Kategori', values='Jumlah', title='Distribusi Transaksi')
    st.plotly_chart(fig, use_container_width=True)

    # ===================== Data Tabs =====================
    st.header("📋 Detail Transaksi")
    tab1, tab2, tab3 = st.tabs(["✅ Matched", "❌ Invoice Belum Dibayar", "❌ Transaksi Bank Tidak Sesuai"])

    with tab1:
        st.dataframe(df_matched, use_container_width=True)
    with tab2:
        st.dataframe(unmatched_inv, use_container_width=True)
    with tab3:
        st.dataframe(unmatched_bank, use_container_width=True)

    # ===================== Download =====================
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
    st.warning("Silakan upload kedua file untuk memulai proses rekonsiliasi.")
