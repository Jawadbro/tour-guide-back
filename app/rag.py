# app/rag.py - UPDATED VERSION WITH GENERAL QUERY FIX

import os
import json
from typing import List, Dict, Any
import google.generativeai as genai
from app.config import settings

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")


def load_places_data() -> List[Dict]:
    """Load the places.json file"""
    places_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'places.json')
    with open(places_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_location_info(query: str) -> Dict[str, Any]:
    """
    Extract location and intent from user query
    """
    query_lower = query.lower()
    
    # Divisions
    divisions = {
        'dhaka': ['dhaka'],
        'chittagong': ['chittagong', 'chattogram', 'ctg'],
        'khulna': ['khulna'],
        'sylhet': ['sylhet'],
        'barisal': ['barisal', 'barishal'],
        'rajshahi': ['rajshahi'],
        'rangpur': ['rangpur'],
        'mymensingh': ['mymensingh']
    }
    
    # Popular specific locations
    specific_places = {
        'rangamati': ['rangamati'],
        'cox\'s bazar': ['cox', 'coxs bazar', "cox's bazar", 'coxsbazar'],
        'sundarbans': ['sundarban', 'sundarbans'],
        'bandarban': ['bandarban'],
        'sajek': ['sajek'],
        'saint martin': ['saint martin', 'st martin'],
        'kuakata': ['kuakata'],
        'ratargul': ['ratargul'],
        'srimangal': ['srimangal', 'sreemangal'],
        'paharpur': ['paharpur'],
        'mahasthangarh': ['mahasthangarh'],
        'jaflong': ['jaflong'],
        'tanguar haor': ['tanguar', 'tanguar haor']
    }
    
    # Extract count
    count = 10
    for num in range(1, 51):
        if f'top {num}' in query_lower or f'{num} spot' in query_lower or f'{num} place' in query_lower:
            count = num
            break
    
    # Check for specific places first (higher priority)
    for place, keywords in specific_places.items():
        for keyword in keywords:
            if keyword in query_lower:
                return {
                    'location': place,
                    'type': 'specific',
                    'count': count,
                    'search_keywords': [place] + keywords
                }
    
    # Check for divisions
    for division, keywords in divisions.items():
        for keyword in keywords:
            if keyword in query_lower:
                return {
                    'location': division,
                    'type': 'division',
                    'count': count,
                    'search_keywords': keywords
                }
    
    # Check for general Bangladesh
    if any(word in query_lower for word in ['bangladesh', 'bd', 'country', 'nation']):
        return {
            'location': 'bangladesh',
            'type': 'general',
            'count': count,
            'search_keywords': ['bangladesh']
        }
    
    # Unknown - fallback
    return {
        'location': query,
        'type': 'unknown',
        'count': count,
        'search_keywords': [query]
    }


def calculate_relevance_score(place: Dict, location_info: Dict) -> float:
    """
    Calculate how relevant a place is to the query
    Returns a score from 0-100
    """
    score = 0.0
    
    place_name = (place.get('name') or '').lower()
    place_division = (place.get('division') or '').lower()
    place_desc = (place.get('description') or '').lower()
    place_url = (place.get('url') or '').lower()
    
    location = location_info['location'].lower()
    location_type = location_info['type']
    search_keywords = location_info.get('search_keywords', [location])
    
    if location_type == 'specific':
        for keyword in search_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower == place_name:
                score += 50
            elif keyword_lower in place_name:
                score += 30
            if keyword_lower in place_desc:
                score += 15
            if keyword_lower in place_url:
                score += 10
            if keyword_lower in place_division:
                score += 5
    
    elif location_type == 'division':
        for keyword in search_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower == place_division:
                score += 40
            elif keyword_lower in place_division:
                score += 25
            if keyword_lower in place_desc:
                score += 15
            if keyword_lower in place_url:
                score += 10
            if keyword_lower in place_name:
                score += 5
    
    elif location_type == 'general':
        # Include only famous tourist spots
        famous_keywords = [
            'cox', 'sundarban', 'saint martin', 'rangamati', 
            'bandarban', 'sajek', 'kuakata', 'paharpur', 'ratargul', 'srimangal'
        ]
        
        matched = False
        for keyword in famous_keywords:
            if keyword in place_name or keyword in place_desc:
                score += 30
                matched = True
                break
        
        if not matched:
            return 0  # Exclude generic places
        
        if place.get('description') and len(place.get('description', '')) > 50:
            score += 5
        if place.get('image'):
            score += 5
    
    return score


def filter_and_rank_places(places: List[Dict], location_info: Dict) -> List[Dict]:
    scored_places = []
    for place in places:
        score = calculate_relevance_score(place, location_info)
        if score > 5:
            place_copy = place.copy()
            place_copy['_relevance_score'] = score
            scored_places.append(place_copy)
    
    scored_places.sort(key=lambda x: x['_relevance_score'], reverse=True)
    
    for place in scored_places:
        place.pop('_relevance_score', None)
    
    return scored_places


def generate_friendly_response(query: str, spots: List[Dict], location_info: Dict) -> str:
    location_name = location_info['location'].title()
    spots_context = ""
    for i, spot in enumerate(spots[:10], 1):
        spots_context += f"\n{i}. **{spot['name']}**"
        if spot.get('division'):
            spots_context += f" ({spot['division']})"
        if spot.get('description'):
            desc = spot['description'][:200] + "..." if len(spot['description']) > 200 else spot['description']
            spots_context += f"\n   {desc}"
        spots_context += "\n"
    
    prompt = f"""You are "Rahim", a friendly and enthusiastic Bangladeshi tour guide...
User asked: "{query}"
Tourist spots in/around {location_name}:{spots_context}
Write a warm, conversational response (3-4 short paragraphs)...
"""
    
    response = model.generate_content(prompt)
    return response.text


def get_tour_suggestions(query: str, top_k: int = 20) -> Dict[str, Any]:
    try:
        places = load_places_data()
        location_info = extract_location_info(query)
        ranked_places = filter_and_rank_places(places, location_info)
        if not ranked_places:
            return {"success": False, "error": "No matching tourist places found."}
        final_spots = ranked_places[:top_k]
        friendly_text = generate_friendly_response(query, final_spots, location_info)
        return {
            "success": True,
            "query": query,
            "location": location_info["location"],
            "type": location_info["type"],
            "count": len(final_spots),
            "suggestions": final_spots,
            "ai_message": friendly_text
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
