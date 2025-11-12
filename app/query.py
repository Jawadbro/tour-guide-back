import json
import faiss
import numpy as np
import google.generativeai as genai
from app.config import settings, EMBED_MODEL, LLM_MODEL, FAISS_INDEX_PATH, TOP_K

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# Load FAISS and mapping
index = faiss.read_index(FAISS_INDEX_PATH)
with open("../data/place_mapping.json", "r", encoding="utf-8") as f:
    places = json.load(f)

def query_ai(user_query: str):
    """Return JSON response with AI-generated text + top recommended tourist spots"""

    # Step 1: Embed user query
    query_embed = genai.embed_content(
        model=EMBED_MODEL,
        content=user_query,
        task_type="retrieval_query"
    )["embedding"]
    query_vector = np.array(query_embed, dtype="float32").reshape(1, -1)

    # Step 2: Retrieve most similar places
    D, I = index.search(query_vector, TOP_K)
    retrieved = [places[i] for i in I[0]]

    # Step 3: Create context
    context = "\n\n".join([
        f"{p['name']} ({p.get('division','Unknown')}): {p.get('description','No description')}"
        for p in retrieved
    ])

    # Step 4: Generate friendly tour guide answer
    prompt = (
        f"You are a friendly Bangladeshi tour guide. "
        f"The user asks: '{user_query}'. "
        f"Here are some relevant tourist spots:\n\n{context}\n\n"
        f"Now respond warmly, like a local friend giving personal suggestions — "
        f"use emotional and helpful language, mention what to expect, travel tips, and must-visit highlights."
    )

    model = genai.GenerativeModel(LLM_MODEL)
    response = model.generate_content(prompt)

    ai_answer = response.text.strip()

    # Step 5: Return clean JSON
    return {
        "query": user_query,
        "answer": ai_answer,
        "spots": [
            {
                "name": p["name"],
                "division": p.get("division"),
                "description": p.get("description", ""),
                "image": p.get("image", None)
            }
            for p in retrieved
        ]
    }

# --- CLI test mode ---
if __name__ == "__main__":
    print("🌍 BD Tour Guide (Gemini Mode)")
    while True:
        q = input("\nAsk about a place or division in Bangladesh: ")
        if q.lower() in ["exit", "quit"]:
            break
        result = query_ai(q)
        print("\n🤖 AI Guide Says:\n")
        print(result["answer"])
        print("\n📸 Recommended Spots:\n")
        for s in result["spots"]:
            print(f"• {s['name']} ({s.get('division','Unknown')}) → {s.get('image', 'No image')}")
