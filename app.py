import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO

st.set_page_config(
    page_title="Rekonsiliasi Keuangan",
    layout="wide",
    page_icon="📊"
)

st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .block-container {
        padding: 2rem 2rem 2rem 2rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Aplikasi Rekonsiliasi Invoice & Rekening Koran")
st.write("""
Aplikasi ini membantu membandingkan data invoice dan rekening koran untuk mendeteksi transaksi yang cocok dan tidak cocok secara otomatis.
Silakan upload kedua file pada panel sebelah kiri.
""")

# Sidebar upload
st.sidebar.header("🔽 Upload Data")
inv_file = st.sidebar.file_uploader("Invoice (CSV/XLSX)", type=["csv", "xlsx"])
bank_file = st.sidebar.file_uploader("Rekening Koran (CSV/XLSX)", type=["csv", "xlsx"])

# Load file
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

    # Format kolom
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

    st.markdown("---")
    st.subheader("🔍 Hasil Rekonsiliasi")
    st.success(f"Jumlah Transaksi Cocok: {len(df_matched)}")
    st.dataframe(df_matched, use_container_width=True)

    with st.expander("❌ Invoice Tidak Terbayar"):
        st.dataframe(unmatched_inv, use_container_width=True)

    with st.expander("❌ Transaksi Bank Tidak Sesuai Invoice"):
        st.dataframe(unmatched_bank, use_container_width=True)

    # Download
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_matched.to_excel(writer, sheet_name="Matched", index=False)
        unmatched_inv.to_excel(writer, sheet_name="Unmatched_Invoice", index=False)
        unmatched_bank.to_excel(writer, sheet_name="Unmatched_Bank", index=False)
        writer.close()

    st.download_button(
        label="📥 Unduh Hasil Rekonsiliasi (Excel)",
