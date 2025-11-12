import json
import faiss
import numpy as np
import google.generativeai as genai
from pathlib import Path
from app.config import settings, EMBED_MODEL, FAISS_INDEX_PATH

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

def create_embeddings():
    # Load tourist spot data
    with open("../data/places.json", "r", encoding="utf-8") as f:
        places = json.load(f)

    print(f"📚 Loaded {len(places)} places for embedding...")

    texts = [f"{p['name']}: {p['description']}" for p in places if p.get("description")]
    embeddings = []

    batch_size = 10
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"Embedding batch {i // batch_size + 1}/{(len(texts) // batch_size) + 1}")

        result = genai.embed_content(
            model=EMBED_MODEL,
            content=batch,
            task_type="retrieval_document"
        )
        batch_embeddings = result["embedding"] if isinstance(result["embedding"][0], list) else [result["embedding"]]
        embeddings.extend(batch_embeddings)

    embeddings = np.array(embeddings, dtype="float32")
    dim = embeddings.shape[1]

    # Create FAISS index
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    Path(FAISS_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, FAISS_INDEX_PATH)

    with open("../data/place_mapping.json", "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)

    print(f"✅ FAISS index created with {len(places)} places at {FAISS_INDEX_PATH}")

if __name__ == "__main__":
    create_embeddings()
