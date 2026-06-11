from typing import Final

# ── Pays UEMOA trackés ────────────────────────────────────────────────────────
# Zone restreinte à SEN + CIV. Ne pas ajouter d'autres pays sans ajuster
# les sources d'ingestion et les marts dbt.
UEMOA_COUNTRIES: Final[dict[str, str]] = {
    "SEN": "Sénégal",
    "CIV": "Côte d'Ivoire",
}

# ── Indicateurs World Bank ────────────────────────────────────────────────────
# Codes officiels World Bank API. Utilisés comme valeurs pour indicator_code
# dans ht_worldbank_indicators et comme filtres dans l'ingestion.
WB_INDICATORS: Final[dict[str, str]] = {
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "NY.GDP.PCAP.CD":  "GDP per capita (current USD)",
    "SN.ITK.DEFC.ZS":  "Prevalence of undernourishment (% of population)",
    "AG.PRD.FOOD.XD":  "Food production index",
    "SP.POP.TOTL":     "Population, total",
}

# ── Commodités WFP ────────────────────────────────────────────────────────────
# Noms tels que retournés par l'API WFP VAM pour les marchés SEN/CIV.
# À valider contre les vraies réponses API à l'étape 5.
WFP_COMMODITIES: Final[list[str]] = [
    "Millet",
    "Sorghum",
    "Maize",
    "Rice (imported)",
    "Wheat flour",
]

# ── Mapping ISO3 → ISO2 ───────────────────────────────────────────────────────
# L'API WFP Data Bridges n'accepte que les codes ISO 2 dans ses paramètres.
# World Bank accepte ISO3 directement — ce mapping est propre à WFP.
UEMOA_ISO2_CODES: Final[dict[str, str]] = {
    "SEN": "SN",
    "CIV": "CI",
}

# ── Devise UEMOA ──────────────────────────────────────────────────────────────
# XOF = Franc CFA, commun à SEN et CIV. Taux fixe EUR.
UEMOA_CURRENCY: Final[str] = "XOF"
