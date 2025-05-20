import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO

# Konfigurasi halaman
st.set_page_config(
    page_title="Rekonsiliasi Keuangan",
    layout="wide",
    page_icon="📊"
)

# Gaya CSS tema pastel
st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #fdf6f0;
    font-family: 'Segoe UI', sans-serif;
    color: #333;
}
.stButton>button {
    background-color: #ffdcdc;
    color: black;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    padding: 0.4em 1.2em;
}
.stDownloadButton>button {
    background-color: #d4f5dd;
    color: black;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    padding: 0.4em 1.2em;
}
</style>
""", unsafe_allow_html=True)

# Header utama
st.title("📊 Aplikasi Rekonsiliasi Keuangan")
st.markdown("""
Aplikasi ini membandingkan data **invoice** dan **rekening koran**,
mendeteksi transaksi yang cocok dan yang tidak sesuai.
Silakan upload file pada sidebar untuk memulai.
""")

# Upload file
st.sidebar.header("📂 Upload File")
inv_file = st.sidebar.file_uploader("Invoice (CSV/XLSX)", type=["csv", "xlsx"])
bank_file = st.sidebar.file_uploader("Rekening Koran (CSV/XLSX)", type=["csv", "xlsx"])

@st.cache_data
def load_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

if inv_file and bank_file:
    df_inv = load_file(inv_file)
    df_bank = load_file(bank_file)

    # Normalisasi kolom
    for df in [df_inv, df_bank]:
        df.columns = df.columns.str.lower().str.strip()

    df_inv = df_inv.rename(columns={"tanggal": "date", "nominal": "amount", "deskripsi": "desc"})
    df_bank = df_bank.rename(columns={"tanggal": "date", "nominal": "amount", "deskripsi": "desc"})

    df_inv['date'] = pd.to_datetime(df_inv['date'])
    df_bank['date'] = pd.to_datetime(df_bank['date'])
    df_inv['amount'] = df_inv['amount'].astype(float)
    df_bank['amount'] = df_bank['amount'].astype(float)

    # Rekonsiliasi
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

    # Tampilkan hasil
    st.subheader("✅ Transaksi Cocok")
    st.dataframe(df_matched, use_container_width=True)

    with st.expander("❌ Invoice Tidak Terbayar"):
        st.dataframe(unmatched_inv, use_container_width=True)

    with st.expander("❌ Transaksi Bank Tidak Sesuai"):
        st.dataframe(unmatched_bank, use_container_width=True)

    # Unduh hasil rekonsiliasi
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_matched.to_excel(writer, sheet_name="Matched", index=False)
        unmatched_inv.to_excel(writer, sheet_name="Unmatched_Invoice", index=False)
        unmatched_bank.to_excel(writer, sheet_name="Unmatched_Bank", index=False)
        writer.close()

    st.download_button(
        label="💾 Unduh Hasil Rekonsiliasi",
        data=buffer.getvalue(),
        file_name="rekonsiliasi_hasil.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Silakan upload file invoice dan rekening koran terlebih dahulu.")
