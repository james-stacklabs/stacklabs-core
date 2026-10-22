#!/usr/bin/env python3
import os
import json
import sqlite3
import requests
import sys

# CONFIGURATION
TARGET_DIR = "/home/james/stacklabs"
DB_PATH = os.path.join(TARGET_DIR, "scripts/sovereign_search.db")
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

def get_embedding(text):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": text
        }, timeout=10)
        return response.json().get("embedding")
    except Exception as e:
        print(f"Embedding failure: {e}")
        return None

def cosine_similarity(v1, v2):
    dot = sum(x * y for x, y in zip(v1, v2))
    norm1 = sum(x * x for x in v1) ** 0.5
    norm2 = sum(x * x for x in v2) ** 0.5
    return dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0

def search(query, limit=5):
    if not os.path.exists(DB_PATH):
        print("Error: Index database not found. Run sovereign_indexer.py first.")
        return

    query_vector = get_embedding(query)
    if not query_vector:
        return

    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()
    cursor.execute("SELECT path, content, vector FROM embeddings")
    rows = cursor.fetchall()
    
    results = []
    for path, content, vector_json in rows:
        vector = json.loads(vector_json)
        score = cosine_similarity(query_vector, vector)
        results.append((path, content, score))
    
    # Sort by score descending
    results.sort(key=lambda x: x[2], reverse=True)
    
    print(f"\n--- SOVEREIGN SEARCH RESULTS FOR: '{query}' ---\n")
    for path, content, score in results[:limit]:
        print(f"[{score:.4f}] {path}")
        # Clean up content snippet (first 150 chars, no newlines)
        snippet = content.replace('\n', ' ').strip()[:150]
        print(f"    Snippet: {snippet}...\n")
        
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 sovereign_search.py 'your search query'")
    else:
        search(" ".join(sys.argv[1:]))
