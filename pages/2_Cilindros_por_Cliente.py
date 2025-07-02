import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd

# 1) Importamos la función de autenticación
from auth import check_password

# Primero verificamos la contraseña.
if not check_password():
    st.stop()

# ------------------------------------------------------------------
# Función de carga desde Google Sheets
# ------------------------------------------------------------------
def get_gsheet_data(sheet_name: str) -> pd.DataFrame | None:
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        client = gspread.authorize(credentials)
        sheet = client.open("TRAZABILIDAD").worksheet(sheet_name)
        df = pd.DataFrame(sheet.get_all_records())
        # Normalizar nombres de columnas a mayúsculas sin espacios
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return None

# ------------------------------------------------------------------
# Cargar datos
# ------------------------------------------------------------------
df_proceso = get_gsheet_data("PROCESO")
df_detalle = get_gsheet_data("DETALLE")

# ------------------------------------------------------------------
# Normalizar columna SERIE y asegurar texto en df_detalle
# ------------------------------------------------------------------
if df_detalle is not None and "SERIE" in df_detalle.columns:
    df_detalle["SERIE"] = (
        df_detalle["SERIE"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("FASTRACK")
st.subheader("CONSULTA DE CILINDROS POR CLIENTE")

if df_proceso is not None:
    clientes_unicos = df_proceso["CLIENTE"].unique()
    cliente_seleccionado = st.selectbox(
        "Seleccione el cliente:", clientes_unicos
    )
else:
    cliente_seleccionado = None

# ------------------------------------------------------------------
# Botón de búsqueda
# ------------------------------------------------------------------
if st.button("Buscar Cilindros del Cliente"):
    if cliente_seleccionado and df_proceso is not None and df_detalle is not None:
        # 1) IDs de procesos para el cliente
        ids_procesos_cliente = df_proceso.loc[
            df_proceso["CLIENTE"] == cliente_seleccionado, "IDPROC"
        ]

        # 2) Para esos procesos, obtengo todos los detalles (incluye SERIE y SERVICIO)
        df_cilindros_cliente = df_detalle.loc[
            df_detalle["IDPROC"].isin(ids_procesos_cliente),
            ["IDPROC", "SERIE", "SERVICIO"]
        ]

        # 3) Filtrar procesos por esos IDs y ordenar
        df_procesos_filtrados = df_proceso.loc[
            df_proceso["IDPROC"].isin(df_cilindros_cliente["IDPROC"])
        ].sort_values(by=["FECHA", "HORA"])

        # 4) Quedarme con el último proceso por IDPROC
        df_ultimos_procesos = df_procesos_filtrados.drop_duplicates(
            subset="IDPROC", keep="last"
        )

        # 5) Mantener solo procesos de DESPACHO o ENTREGA
        cilindros_en_cliente = df_ultimos_procesos.loc[
            df_ultimos_procesos["PROCESO"].isin(["DESPACHO", "ENTREGA"])
        ]

        # 6) Unir con df_cilindros_cliente para traer SERIE y SERVICIO
        ids_cilindros_en_cliente = df_cilindros_cliente.loc[
            df_cilindros_cliente["IDPROC"].isin(cilindros_en_cliente["IDPROC"])
        ].merge(
            df_ultimos_procesos[["IDPROC", "FECHA"]],
            on="IDPROC",
            how="left",
        )

        # ----------------------------------------------------------
        # Mostrar resultados y botón de descarga
        # ----------------------------------------------------------
        if not ids_cilindros_en_cliente.empty:
            st.write(f"Cilindros actualmente en el cliente: {cliente_seleccionado}")

            # Incluir SERVICIO al mostrar la tabla
            st.dataframe(
                ids_cilindros_en_cliente[["SERIE", "IDPROC", "FECHA", "SERVICIO"]]
            )

            def convert_to_csv(df: pd.DataFrame) -> bytes:
                return df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇️ Descargar resultados en CSV",
                data=convert_to_csv(ids_cilindros_en_cliente),
                file_name=f"cilindros_{cliente_seleccionado}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No se encontraron cilindros en el cliente seleccionado.")
    else:
        st.warning("Por favor, seleccione un cliente.")
