import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import hashlib
import requests

SONARR_API_KEY = os.getenv("SONARR_API_KEY", "3a86bddfeefa4c93b104f33a534ffb72")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "3a86bddfeefa4c93b104f33a534ffb72")

app = FastAPI(title="Sovereign Cinema Media Server")

# Allow CORS for the kiosk
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the media vault natively, StaticFiles supports HTTP Range (206 Partial Content) out of the box
MEDIA_VAULT_PATH = "/home/james/stacklabs/media_vault"

if not os.path.exists(MEDIA_VAULT_PATH):
    print(f"CRITICAL: Media Vault not found at {MEDIA_VAULT_PATH}")
    # Create it so it doesn't crash
    os.makedirs(MEDIA_VAULT_PATH, exist_ok=True)

def discover_service_url(port: int, service_name: str, path_prefix: str = "") -> str:
    import socket
    hosts = ["127.0.0.1", "clio.taila01894.ts.net"]
    for host in hosts:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return f"http://{host}:{port}{path_prefix}"
        except OSError:
            continue
    # Fallback to local
    return f"http://127.0.0.1:{port}{path_prefix}"

@app.get("/api/media/{category}")
def get_media(category: str):
    valid_categories = {"tv_shows": "TV_Shows", "movies": "Movies"}
    if category.lower() not in valid_categories:
        return {"error": "Invalid category"}
        
    search_paths = []
    if category.lower() == "movies":
        search_paths.append(os.path.join(MEDIA_VAULT_PATH, "Movies"))
    else:
        search_paths.append(os.path.join(MEDIA_VAULT_PATH, "TV_Shows"))
        # Sonarr is dropping root folders directly into media_vault
        for d in os.listdir(MEDIA_VAULT_PATH):
            full_path = os.path.join(MEDIA_VAULT_PATH, d)
            if os.path.isdir(full_path) and d not in ["Movies", "TV_Shows"] and not d.startswith("0"):
                search_paths.append(full_path)
                
    # Fetch Sonarr series dynamically to match actual TV Show posters
    sonarr_series = []
    if category.lower() != "movies":
        try:
            sonarr_url = discover_service_url(8989, "sonarr", "/sonarr")
            res = requests.get(f"{sonarr_url}/api/v3/series?apikey={SONARR_API_KEY}", timeout=2)
            if res.status_code == 200:
                sonarr_series = res.json()
        except Exception as e:
            print(f"Failed to fetch Sonarr series: {e}")

    # Fetch Radarr movies dynamically to match actual Movie posters
    radarr_movies = []
    if category.lower() == "movies":
        try:
            radarr_url = discover_service_url(7878, "radarr", "")
            res = requests.get(f"{radarr_url}/api/v3/movie?apikey={RADARR_API_KEY}", timeout=2)
            if res.status_code == 200:
                radarr_movies = res.json()
        except Exception as e:
            print(f"Failed to fetch Radarr movies: {e}")

    items = []
    for folder_path in search_paths:
        if not os.path.exists(folder_path):
            continue
        for root, dirs, files in os.walk(folder_path, followlinks=True):
            for file in files:
                if file.endswith(('.mp4', '.mkv', '.avi')):
                    rel_path = os.path.relpath(os.path.join(root, file), MEDIA_VAULT_PATH)
                    
                    # Determine image based on category and matching logic
                    image_url = None
                    if category.lower() == "movies":
                        if "bull" in file.lower() and "durham" in file.lower():
                            image_url = "/01_Assets/Images/bull_durham.jpg"
                        else:
                            # Match movie files using Radarr metadata
                            file_title = os.path.splitext(file)[0].lower()
                            import re
                            file_title_clean = re.sub(r'[\._\-]', ' ', file_title)
                            
                            parent_folder = os.path.basename(root).lower()
                            for movie in radarr_movies:
                                movie_title = movie.get("title", "").lower()
                                movie_path = movie.get("path", "").lower()
                                folder_name = os.path.basename(movie_path)
                                
                                if (movie_title and movie_title in file_title_clean) or (folder_name and folder_name == parent_folder):
                                    poster = next((img for img in movie.get("images", []) if img.get("coverType") == "poster"), None)
                                    if poster:
                                        image_url = poster.get("url")
                                        if image_url:
                                            if image_url.startswith("/"):
                                                image_url = f"/radarr{image_url}"
                                            sep = "&" if "?" in image_url else "?"
                                            image_url = f"{image_url}{sep}apikey={RADARR_API_KEY}"
                                        break
                    else:
                        # Match TV show files using Sonarr metadata
                        rel_root = root.lower().replace(MEDIA_VAULT_PATH.lower(), "").strip("/")
                        for series in sonarr_series:
                            series_path = series.get("path", "").lower().replace("/media_vault/", "").strip("/")
                            if series_path and (series_path in rel_root or rel_root in series_path):
                                poster = next((img for img in series.get("images", []) if img.get("coverType") == "poster"), None)
                                if poster:
                                    image_url = poster.get("url")
                                    if image_url and "/sonarr/mediacover/" in image_url.lower():
                                        image_url = image_url.replace("/sonarr/MediaCover/", "/sonarr/api/v3/mediacover/")
                                        image_url = image_url.replace("/sonarr/mediacover/", "/sonarr/api/v3/mediacover/")
                                        sep = "&" if "?" in image_url else "?"
                                        image_url = f"{image_url}{sep}apikey={SONARR_API_KEY}"
                                    break
                        # Fallback for "From" show if not matched in Sonarr
                        if not image_url and "from" in rel_path.lower():
                            image_url = "/01_Assets/Images/from_tv_show.jpg"

                    # Ultimate fallback to default poster
                    if not image_url:
                        image_url = f"/01_Assets/Images/poster_{(int(hashlib.md5(file.encode()).hexdigest(), 16) % 3) + 1}.png"

                    items.append({
                        "id": file,
                        "title": os.path.splitext(file)[0].replace(".", " "),
                        "video_url": f"/stream/{rel_path}",
                        "image": image_url
                    })

    return items

app.mount("/", StaticFiles(directory=MEDIA_VAULT_PATH), name="media_vault")

if __name__ == "__main__":
    print("Initializing Sovereign Cinema Media Streaming Engine on port 8085...")
    uvicorn.run(app, host="0.0.0.0", port=8085, access_log=False)
