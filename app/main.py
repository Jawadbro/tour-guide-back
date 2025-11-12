# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import TourQuery, TourResponse
from app.rag import (
    load_places_data,
    extract_location_info,
    filter_and_rank_places,
    generate_friendly_response
)
from app.config import settings

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tour-guide-front-lemon.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to BD Tour Guide API! 🇧🇩",
        "status": "active",
        "version": settings.API_VERSION,
        "endpoints": {
            "query": "POST /api/query",
            "suggest": "POST /api/suggest",
            "suggest_simple": "POST /api/suggest-simple?query=...",
            "health": "GET /health",
            "stats": "GET /api/stats"
        },
        "example_queries": [
            "top 10 spots in Rangamati",
            "best places to visit in Chittagong",
            "tourist attractions in Bangladesh",
            "where should I go in Sylhet?"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "BD Tour Guide",
        "version": settings.API_VERSION
    }

# 🧠 Unified endpoint for the frontend React chat
@app.post("/api/query")
async def query_places(payload: dict):
    """
    Unified query endpoint for frontend chat interface.
    Returns both Rahim's friendly response and a list of suggested spots.
    """
    try:
        query = payload.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query is required.")

        # Load places data
        places = load_places_data()

        # Extract intent + location info
        location_info = extract_location_info(query)

        # Filter & rank places
        ranked_places = filter_and_rank_places(places, location_info)

        # Generate natural response
        response_text = generate_friendly_response(query, ranked_places[:10], location_info)

        return {
            "success": True,
            "response": response_text,
            "spots": ranked_places[:10]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/suggest", response_model=TourResponse)
async def suggest_places(query_data: TourQuery):
    """Legacy endpoint for RAG suggestions."""
    try:
        from app.rag import get_tour_suggestions
        result = get_tour_suggestions(
            query=query_data.query,
            top_k=query_data.top_k or 20
        )
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "No results found"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/suggest-simple")
async def suggest_places_simple(query: str):
    """Simple endpoint for basic suggestions."""
    try:
        from app.rag import get_tour_suggestions
        result = get_tour_suggestions(query=query, top_k=20)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Dataset statistics endpoint."""
    try:
        places = load_places_data()

        division_counts = {}
        category_counts = {}

        for place in places:
            division = place.get("division", "Unknown")
            division_counts[division] = division_counts.get(division, 0) + 1

            categories = place.get("categories", ["General"])
            for c in categories:
                category_counts[c] = category_counts.get(c, 0) + 1

        return {
            "success": True,
            "data": {
                "total_places": len(places),
                "by_division": division_counts,
                "by_category": category_counts,
                "places_with_images": sum(1 for p in places if p.get("image")),
                "places_with_descriptions": sum(1 for p in places if p.get("description"))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
