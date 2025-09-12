from fastapi import APIRouter, Depends, Query
from app.climate.service import ClimateService
from app.climate.models import ClimateResponse

router = APIRouter(tags=["climate"], prefix="/climate")

# Simple dependency provider
def get_service() -> ClimateService:
    return ClimateService()

@router.get("", response_model=ClimateResponse)
async def get_climate(
    place: str = Query(..., min_length=1, description="Place name (city, region, etc.)"),
    start_year: int = Query(..., ge=0),
    end_year: int = Query(..., ge=0),
    aggregate: bool = Query(False, description="If true returns aggregate summary"),
    service: ClimateService = Depends(get_service),
) -> ClimateResponse:
    return service.fetch(place=place, start_year=start_year, end_year=end_year, aggregate=aggregate)
