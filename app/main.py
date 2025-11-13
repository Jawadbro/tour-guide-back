# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
from app.models import TourQuery, TourResponse
from app.rag import get_tour_suggestions, extract_location_info, filter_and_rank_places, generate_friendly_response, load_places_data
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


@app.api_route("/", methods=["GET", "HEAD"])
async def root() -> Dict[str, Any]:
    return {
        "message": "Welcome to BD Tour Guide API! 🇧🇩",
        "status": "active",
        "version": settings.API_VERSION,
        "endpoints": {
            "query": "POST /api/query",
            "suggest": "POST /api/suggest",
            "suggest_simple": "GET /api/suggest-simple?query=...",
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


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "BD Tour Guide",
        "version": settings.API_VERSION
    }


# Unified endpoint for frontend chat (AI + RAG)
@app.post("/api/query")
async def query_places(payload: Dict[str, Any]) -> JSONResponse:
    """
    Returns both RAG suggestions and AI fallback response.
    Frontend should display ai_message and suggestions.
    """
    try:
        query = payload.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Query is required.")

        # Load data and extract info
        places = load_places_data()
        location_info = extract_location_info(query)
        ranked_places = filter_and_rank_places(places, location_info)

        # AI-friendly response
        response_text = generate_friendly_response(query, ranked_places[:10], location_info)

        return JSONResponse({
            "success": True,
            "query": query,
            "type": location_info.get("type", "unknown"),
            "ai_message": response_text,
            "suggestions": ranked_places[:10]  # top 10 spots
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoint for structured RAG suggestions
@app.post("/api/suggest", response_model=TourResponse)
async def suggest_places(query_data: TourQuery) -> Dict[str, Any]:
    try:
        result = get_tour_suggestions(query=query_data.query, top_k=query_data.top_k or 20)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error", "No results found"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Simple GET endpoint for quick suggestions
@app.get("/api/suggest-simple")
async def suggest_places_simple(query: str) -> Dict[str, Any]:
    try:
        result = get_tour_suggestions(query=query, top_k=20)
        # Mark fallback type if no RAG suggestions
        if result.get("success") and len(result.get("suggestions", [])) == 0:
            result["type"] = "ai_fallback"
        else:
            result["type"] = "rag_result"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to get dataset statistics
@app.get("/api/stats")
async def get_stats() -> Dict[str, Any]:
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