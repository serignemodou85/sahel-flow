import streamlit as st

st.set_page_config(
    page_title="Sahel Flow — Surveillance alimentaire UEMOA",
    page_icon="",
    layout="wide",
)

with st.sidebar:
    st.title(" Sahel Flow")
    st.caption("Surveillance de la sécurité alimentaire — Zone UEMOA")
    st.markdown("---")
    st.markdown("**Pays couverts**")
    st.markdown("🇸🇳 Sénégal (SEN)  \n🇨🇮 Côte d'Ivoire (CIV)")
    st.markdown("---")
    st.markdown("**Sources de données**")
    st.markdown("- World Bank API — indicateurs macro")
    st.markdown("- WFP VAM — prix alimentaires mensuels")
    st.markdown("---")
    st.markdown("[GitHub](https://github.com/serignemodou85/sahel-flow)")

st.title(" Sahel Flow")
st.subheader("Surveillance de la sécurité alimentaire — Zone UEMOA")
st.markdown(
    """
    Sélectionnez une page dans la barre de navigation à gauche.

    | Page | Description |
    |---|---|
    | **Vue d'ensemble** | État actuel du risque alimentaire — SEN et CIV |
    | **Comparaison** | SEN vs CIV côte à côte sur une période choisie |
    | **Prix Alimentaires** | Exploration des prix par commodité et par pays |
    | **Inflation** | Historique macro-économique — indicateurs World Bank |
    | **Méthodologie** | Explication du modèle de score et de la stack technique |
    """
)
