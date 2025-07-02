# auth.py
import hmac
import streamlit as st

def check_password():
    """
    Retorna `True` si el usuario ha ingresado la contraseña correcta.
    Caso contrario, muestra un cuadro de texto para ingresar password y retorna `False`.
    """
    def password_entered():
        """
        Verifica si la contraseña ingresada por el usuario coincide con la de Streamlit Secrets.
        Si coincide, setea una variable de sesión para no volver a pedirla en la misma sesión.
        Si no coincide, marca la variable de sesión como incorrecta.
        """
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Se elimina la contraseña de la sesión por seguridad.
        else:
            st.session_state["password_correct"] = False

    # Si el usuario ya validó correctamente la contraseña en esta sesión, retornamos True.
    if st.session_state.get("password_correct", False):
        return True

    # De lo contrario, mostramos el campo para ingresar la contraseña.
    st.text_input(
        "Ingrese la contraseña",
        type="password",
        on_change=password_entered,
        key="password"
    )

    # Si se validó como incorrecta, mostramos un mensaje de error.
    if "password_correct" in st.session_state and st.session_state["password_correct"] is False:
        st.error("❌ Contraseña incorrecta. Intente de nuevo.")

    # Retornamos False para indicar que no se ha validado o no coincide.
    return False
