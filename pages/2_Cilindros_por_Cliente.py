import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# ---------------------------------------------------------------
# Autenticación simple
# ---------------------------------------------------------------
from auth import check_password
if not check_password():
    st.stop()

# ---------------------------------------------------------------
# Leer una pestaña de Google Sheets y normalizar columnas
# ---------------------------------------------------------------
def get_gsheet_data(sheet: str) -> pd.DataFrame | None:
    try:
        creds = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        client = gspread.authorize(
            service_account.Credentials.from_service_account_info(creds, scopes=scopes)
        )
        df = pd.DataFrame(client.open("TEST TRAZABILIDAD").worksheet(sheet).get_all_records())
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ---------------------------------------------------------------
# Cargar datos y limpieza mínima
# ---------------------------------------------------------------
df_proc = get_gsheet_data("PROCESO")
df_det  = get_gsheet_data("DETALLE")

if df_proc is None or df_det is None:
    st.stop()

# — eliminar columnas duplicadas que puedan venir en DETALLE
dup_cols = [c for c in ["PROCESO", "FECHA", "HORA", "CLIENTE", "UBICACION"] if c in df_det.columns]
df_det = df_det.drop(columns=dup_cols, errors="ignore")

# — normalizar campos clave
df_det["SERIE"]  = df_det["SERIE"].astype(str).str.replace(",", "", regex=False)
df_proc["IDPROC"] = df_proc["IDPROC"].astype(str)
df_det["IDPROC"]  = df_det["IDPROC"].astype(str)

# ---------------------------------------------------------------
# Merge trazabilidad completo (cada fila = un movimiento individual)
# ---------------------------------------------------------------
df_mov = df_det.merge(
    df_proc[["IDPROC", "FECHA", "HORA", "PROCESO", "CLIENTE", "UBICACION"]],
    on="IDPROC",
    how="left"
)

# — FECHA_HORA para ordenar (si HORA viene vacía se rellena 00:00:00)
df_mov["HORA"] = df_mov["HORA"].fillna("00:00:00").astype(str)
df_mov["FECHA"] = pd.to_datetime(df_mov["FECHA"], errors="coerce", dayfirst=True)
df_mov["FECHA_HORA"] = pd.to_datetime(
    df_mov["FECHA"].dt.strftime("%Y-%m-%d") + " " + df_mov["HORA"],
    errors="coerce"
)

# ---------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------
st.title("FASTRACK")
st.subheader("CONSULTA DE CILINDROS POR CLIENTE")

clientes = df_proc["CLIENTE"].dropna().unique()
cliente_sel = st.selectbox("Seleccione el cliente:", clientes)

# ---------------------------------------------------------------
# Lógica principal
# ---------------------------------------------------------------
if st.button("Buscar cilindros del cliente") and cliente_sel:

    # 1. Último movimiento global de cada cilindro
    df_ult = (
        df_mov
        .sort_values("FECHA_HORA", ascending=False, na_position="last")
        .drop_duplicates("SERIE", keep="first")
    )

    # 2. Cilindros cuyo último proceso es DESPACHO o ENTREGA
    df_en_cliente = df_ult[df_ult["PROCESO"].isin(["DESPACHO", "ENTREGA"])]

    # 3. …y cuyo CLIENTE coincide con el seleccionado
    df_en_cliente = df_en_cliente[df_en_cliente["CLIENTE"] == cliente_sel]

    if not df_en_cliente.empty:
        st.success(f"Cilindros actualmente en el cliente: {cliente_sel}")

        cols_show = ["SERIE", "IDPROC", "FECHA", "HORA", "PROCESO", "SERVICIO"]
        cols_show = [c for c in cols_show if c in df_en_cliente.columns]

        st.dataframe(df_en_cliente[cols_show])

        st.download_button(
            "⬇️ Descargar CSV",
            data=df_en_cliente[cols_show].to_csv(index=False).encode("utf-8"),
            file_name=f"cilindros_{cliente_sel}.csv",
            mime="text/csv",
        )
    else:
        st.warning("El cliente no tiene cilindros pendientes de devolución.")
