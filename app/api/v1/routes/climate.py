import logging
from fastapi import APIRouter, Depends, HTTPException
from app.climate.service import ClimateService
from ..schemas import (
    ClimateRequest, ErrorResponse, LocationData, 
    ClimateClassificationData, AggregatedClimateResponse, 
    AggregatedClimateData, YearlyClimateResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["climate"], prefix="/climate")

# Simple dependency provider
def get_climate_service() -> ClimateService:
    return ClimateService()


@router.post("/aggregated", response_model=AggregatedClimateResponse, responses={400: {"model": ErrorResponse}})
async def get_aggregated_climate_data(
    request: ClimateRequest,
    service: ClimateService = Depends(get_climate_service),
) -> AggregatedClimateResponse:
    """Get aggregated climate data for a city across multiple years.
    
    This endpoint:
    1. Geocodes the city name to get latitude/longitude
    2. Retrieves climate data from the CompactClimateModel
    3. Averages monthly temperatures and precipitation across all years
    4. Applies Köppen and Trewartha climate classification to averaged data
    5. Returns single classification for the entire period
    """
    logger.info(f"Aggregated climate data requested for {request.city}, years: {request.years}")
    
    try:
        # Get aggregated climate data using the enhanced service
        location, avg_monthly_temps, avg_monthly_precip, classification, distance_km = service.get_aggregated_climate_data(
            city=request.city,
            years=request.years
        )
        
        logger.info(f"Successfully retrieved aggregated data for {request.city} (distance: {distance_km:.2f}km)")
        
        # Create location data
        location_data = LocationData(
            city=location.city,
            latitude=location.latitude,
            longitude=location.longitude,
            country=location.country,
            display_name=location.display_name
        )
        
        # Create aggregated climate data
        climate_data = AggregatedClimateData(
            avg_monthly_temps=avg_monthly_temps,
            avg_monthly_precip=avg_monthly_precip,
            classification=ClimateClassificationData(
                koppen_code=classification.koppen_code,
                koppen_name=classification.koppen_name,
                trewartha_code=classification.trewartha_code,
                trewartha_name=classification.trewartha_name
            )
        )
        
        return AggregatedClimateResponse(
            location=location_data,
            start_year=min(request.years),
            end_year=max(request.years),
            climate_data=climate_data,
            distance_km=round(distance_km, 2)
        )
        
    except ValueError as e:
        logger.error(f"Client error for {request.city}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal server error for {request.city}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/yearly", response_model=YearlyClimateResponse, responses={400: {"model": ErrorResponse}})
async def get_yearly_climate_data(
    request: ClimateRequest,
    service: ClimateService = Depends(get_climate_service),
) -> YearlyClimateResponse:
    """Get yearly breakdown of climate classifications.
    
    This endpoint:
    1. Geocodes the city name to get latitude/longitude
    2. Retrieves climate data from the CompactClimateModel
    3. Applies Köppen and Trewartha climate classification to each year individually
    4. Returns dictionary of year → classification mappings
    """
    logger.info(f"Yearly climate data requested for {request.city}, years: {request.years}")
    
    try:
        # Get yearly climate data using the enhanced service
        location, year_classifications, distance_km = service.get_yearly_climate_data(
            city=request.city,
            years=request.years
        )
        
        logger.info(f"Successfully retrieved yearly data for {request.city} (distance: {distance_km:.2f}km)")
        
        # Create location data
        location_data = LocationData(
            city=location.city,
            latitude=location.latitude,
            longitude=location.longitude,
            country=location.country,
            display_name=location.display_name
        )
        
        # Convert classifications to API format
        yearly_data = {}
        for year, classification in year_classifications.items():
            yearly_data[year] = ClimateClassificationData(
                koppen_code=classification.koppen_code,
                koppen_name=classification.koppen_name,
                trewartha_code=classification.trewartha_code,
                trewartha_name=classification.trewartha_name
            )
        
        return YearlyClimateResponse(
            location=location_data,
            start_year=min(request.years),
            end_year=max(request.years),
            yearly_data=yearly_data,
            distance_km=round(distance_km, 2)
        )
        
    except ValueError as e:
        logger.error(f"Client error for {request.city}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal server error for {request.city}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

