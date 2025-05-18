# app/api/v1/schemas/footprint.py
from pydantic import BaseModel, Field
from typing import Optional

class EnergySchema(BaseModel):
    applianceHours: Optional[float] = 0.0
    lightBulbs: Optional[float] = 0.0
    gasTanks: Optional[float] = 0.0
    hvacHours: Optional[float] = 0.0

class FoodSchema(BaseModel):
    redMeat: Optional[float] = 0.0
    whiteMeat: Optional[float] = 0.0
    dairy: Optional[float] = 0.0
    vegetarian: Optional[float] = 0.0

class TransportSchema(BaseModel):
    carKm: Optional[float] = 0.0
    publicKm: Optional[float] = 0.0
    domesticFlights: Optional[float] = 0.0
    internationalFlights: Optional[float] = 0.0

class WasteSchema(BaseModel):
    trashBags: Optional[float] = 0.0
    foodWaste: Optional[float] = 0.0
    plasticBottles: Optional[float] = 0.0
    paperPackages: Optional[float] = 0.0

class FootprintInputSchema(BaseModel):
    date: str
    energy: EnergySchema
    food: FoodSchema
    transport: TransportSchema
    waste: WasteSchema
    result: float = Field(..., description="Overall calculated carbon footprint result")