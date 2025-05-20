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
.stButton>button, .stDownloadButton>button {
    background-color: #4CAF50;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 0.5em 1.5em;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard Rekonsiliasi Pendapatan Ticketing")

with st.expander("ℹ️ Petunjuk Penggunaan", expanded=False):
    st.markdown("""
    1. Siapkan dua file: **Invoice** dan **Rekening Koran** dalam format CSV/XLSX
    2. Pastikan file memiliki kolom berikut:
       - `tanggal`, `nominal`, dan `deskripsi`
    3. Upload keduanya melalui form di bawah
    4. Hasil rekonsiliasi akan muncul secara otomatis beserta tabel dan grafik ringkasan
    5. Klik tombol unduh untuk menyimpan hasil rekonsiliasi ke Excel
    """)

uploaded = False

@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

with st.container():
    st.markdown("---")
    st.header("📂 Upload File")
    col_inv, col_bank = st.columns(2)
    with col_inv:
        inv_file = st.file_uploader("Upload Invoice", type=["csv", "xlsx"], key="inv")
    with col_bank:
        bank_file = st.file_uploader("Upload Rekening Koran", type=["csv", "xlsx"], key="bank")

    if inv_file and bank_file:
        uploaded = True
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
        st.info("Silakan upload kedua file untuk memulai proses rekonsiliasi.")
