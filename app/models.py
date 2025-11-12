from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TourQuery(BaseModel):
    """Request model for tour suggestions"""
    query: str = Field(..., description="User's query about tourist spots")
    top_k: Optional[int] = Field(20, description="Number of places to retrieve")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "top 10 spots in Rangamati",
                "top_k": 20
            }
        }

class TouristSpot(BaseModel):
    """Model for a single tourist spot"""
    name: str
    division: str
    description: Optional[str] = None
    image: Optional[str] = None
    url: Optional[str] = None
    categories: Optional[List[str]] = []

class TourData(BaseModel):
    """Response data model"""
    query: str
    location_detected: str
    location_type: str
    answer: str
    spots: List[Dict[str, Any]]
    total_found: int

class TourResponse(BaseModel):
    """Response model for tour suggestions"""
    success: bool
    data: Optional[TourData] = None
    error: Optional[str] = None