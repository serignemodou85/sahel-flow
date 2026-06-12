from fastapi import APIRouter, Depends

from app.db.deps import get_conn
from app.schemas.countries import CountryResponse
from app.services import countries_service

router = APIRouter(tags=["countries"])


@router.get("/countries", response_model=list[CountryResponse])
def list_countries(conn=Depends(get_conn)) -> list[CountryResponse]:
    """Liste les pays UEMOA ayant des données dans au moins une source.

    Un pays apparaît dès qu'il a des enregistrements dans ht_worldbank_indicators
    ou ht_wfp_food_prices. Reflète l'état réel de la DB — pas une liste hardcodée.
    """
    return countries_service.get_countries(conn)
