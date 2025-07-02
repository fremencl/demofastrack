import streamlit as st
from PIL import Image
from pathlib import Path

# 1) IMPORTAR LA FUNCIÓN DE AUTH
from auth import check_password

def get_project_root() -> Path:
    """Returns the project root folder."""
    return Path(__file__).parent

def load_image(image_name: str) -> Image:
    """Loads an image from the specified path."""
    image_path = Path(get_project_root()) / f"assets/{image_name}"
    print(f"Trying to load image from: {image_path}")  # Para depurar
    return Image.open(image_path)

# Configuración de la aplicación
st.set_page_config(
    page_title="FASTRACK",
    page_icon=":dollar:",
    initial_sidebar_state="expanded",
)

# 2) CHECK PASSWORD (SE DETIENE SI FALLA)
if not check_password():
    st.stop()

# Crear tres columnas y mostrar la imagen en la columna central
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(load_image("Logo.jpg"), width=150)

# Títulos y subtítulos
st.write("### SISTEMA TRACKING DE CILINDROS - FASTRACK :chart_with_upwards_trend:")
st.write("#### URKINOX RANCAGUA")

st.markdown("---")

# Mensaje en la barra lateral
st.sidebar.success("Selecciona un modelo de consulta")

# Contenido introductorio y descripción de la aplicación
st.write("")
st.markdown(
    """##### Bienvenido al sistema de gestion de cilindros de URKINOX

    
Elije el modelo de consulta que necesitas:

- **Movimientos por Cilindro**: Te permitirá consultar todos los movimientos asociados a una serie específica.
- **Cilindros por cliente**: Te permitirá conocer los cilindros en un cliente especifico al momento de ejecutar la consulta.
- **Rotacion**: Te mostrará el listado de cilindros que no han retornado en 30 dias.
- **Cilindros por ubicacion**: Te permitirá conocer los cilindros disponibles en local o clientes
- **Cilindros por fecha**: Te permitirá conocer el detalle de todos los movimientos durante un periodo determinado.

:moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag::moneybag:
    """
)
