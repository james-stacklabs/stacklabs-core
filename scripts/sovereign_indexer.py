#!/usr/bin/env python3
import os
import json
import requests
import sys
import chromadb
import uuid

# CONFIGURATION
TARGET_DIR = "/home/james/stacklabs"
DB_PATH = os.path.join(TARGET_DIR, "scripts/chroma_db")
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
ALLOWED_EXTENSIONS = {'.html', '.md', '.txt', '.py', '.js', '.tsx'}
EXCLUDE_DIRS = {'node_modules', '.git', '.venv', '__pycache__', '.next', 'ui_archive', 'chroma_db'}

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

def chunk_text(text, size, overlap):
    chunks = []
    for i in range(0, len(text), size - overlap):
        chunks.append(text[i:i + size])
    return chunks

def index_files(target_dir):
    print(f"--- INITIALIZING CHROMA DB AT: {DB_PATH} ---")
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(
        name="sovereign_knowledge",
        metadata={"hnsw:space": "cosine"}
    )
    
    print(f"--- STARTING SOVEREIGN INDEXING: {target_dir} ---")
    
    for root, dirs, files in os.walk(target_dir):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, TARGET_DIR)
                
                try:
                    mtime = os.path.getmtime(file_path)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    if not content.strip():
                        continue
                        
                    chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
                    
                    if not chunks:
                        continue
                        
                    print(f"Indexing: {rel_path} ({len(chunks)} chunks)...")
                    
                    ids = [f"{rel_path}_{i}_{str(uuid.uuid4())[:8]}" for i in range(len(chunks))]
                    embeddings = []
                    documents = []
                    metadatas = []
                    
                    for chunk in chunks:
                        vector = get_embedding(chunk)
                        if vector:
                            embeddings.append(vector)
                            documents.append(chunk)
                            metadatas.append({"path": rel_path, "last_modified": mtime})
                    
                    if embeddings:
                        collection.add(
                            documents=documents,
                            embeddings=embeddings,
                            metadatas=metadatas,
                            ids=ids
                        )
                except Exception as e:
                    print(f"Error indexing {rel_path}: {e}")
                    
    print("--- INDEXING COMPLETE ---")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign Search Indexer (ChromaDB)")
    parser.add_argument("--target", default=TARGET_DIR, help="Specific directory to index")
    args = parser.parse_args()
    
    target_path = os.path.abspath(args.target)
    index_files(target_path)
