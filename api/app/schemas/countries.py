from pydantic import BaseModel


class CountryResponse(BaseModel):
    code: str       # "SEN"
    name: str       # "Sénégal"
    currency: str   # "XOF"
