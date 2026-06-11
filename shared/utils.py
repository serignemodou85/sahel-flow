from datetime import datetime, timezone


def month_start(dt: datetime) -> datetime:
    """Ramène une date au 1er du mois à 00:00:00 UTC.

    Utilisé pour normaliser la colonne "time" de ht_wfp_food_prices
    avant insertion : toutes les données d'un mois partagent la même valeur.
    """
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)


def year_start(year: int) -> datetime:
    """Retourne le 1er janvier de l'année à 00:00:00 UTC.

    Utilisé pour normaliser la colonne "time" de ht_worldbank_indicators :
    les données annuelles World Bank sont stockées au 1er janvier.
    """
    return datetime(year, 1, 1, tzinfo=timezone.utc)
