import os
import time
import logging
from typing import Tuple, List, Optional
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [ImagenUtil]: %(message)s")
logger = logging.getLogger("ImagenUtil")

CREDENTIALS_PATHS = [
    "/home/james/stacklabs/config/vertex_sa.json",
]
PROJECT_ID = "project-114213dc-6519-49c5-a0a"
LOCATION = "us-central1"

# Candidate model hierarchy in priority order
CANDIDATE_MODELS = [
    "imagen-3.0-generate-002",
    "imagen-3.0-generate-001"
]

_CACHED_WORKING_MODEL: Optional[str] = None
_CLIENT_INSTANCE: Optional[genai.Client] = None

def get_imagen_client() -> genai.Client:
    """Returns a singleton instance of the google.genai Client configured for Vertex AI."""
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is None:
        target_project = PROJECT_ID
        for p in CREDENTIALS_PATHS:
            if os.path.exists(p):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = p
                logger.info(f"Loaded Vertex credentials from: {p}")
                try:
                    import json
                    with open(p, "r") as f:
                        sa_data = json.load(f)
                        if "project_id" in sa_data:
                            target_project = sa_data["project_id"]
                            logger.info(f"Dynamically resolved Vertex project: {target_project}")
                except Exception as ex:
                    logger.warning(f"Could not parse project_id from {p}: {ex}")
                break
        _CLIENT_INSTANCE = genai.Client(
            vertexai=True,
            project=target_project,
            location=LOCATION
        )
    return _CLIENT_INSTANCE

def verify_imagen_model_health(force_refresh: bool = False, max_retries: int = 2) -> Tuple[bool, str]:
    """
    Pre-flight health check to ensure a valid, operational Imagen model is used before any generation.
    Tests candidate models in order and caches the first model that passes verification.
    Includes rate-limit (HTTP 429) backoff retry handling.
    """
    global _CACHED_WORKING_MODEL
    if _CACHED_WORKING_MODEL and not force_refresh:
        return True, _CACHED_WORKING_MODEL

    client = get_imagen_client()
    logger.info("Executing pre-flight Imagen API health verification...")

    for model_name in CANDIDATE_MODELS:
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Testing candidate model: {model_name} (attempt {attempt+1})...")
                res = client.models.generate_images(
                    model=model_name,
                    prompt="Pre-flight verification ping: solid cyan circle icon",
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/png",
                        aspect_ratio="1:1"
                    )
                )
                if res and res.generated_images:
                    _CACHED_WORKING_MODEL = model_name
                    logger.info(f"✅ Pre-flight health check passed! Verified operational model: {model_name}")
                    return True, model_name
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_sec = (attempt + 1) * 3
                    logger.warning(f"⚠️ Rate limit hit (429) for model '{model_name}'. Backing off for {wait_sec}s...")
                    time.sleep(wait_sec)
                else:
                    logger.warning(f"⚠️ Pre-flight check failed for model '{model_name}': {e}")
                    break

    logger.error("❌ CRITICAL: All candidate Imagen models failed pre-flight health check!")
    return False, ""

def generate_imagen_avatar(
    prompt: str,
    output_path: str,
    aspect_ratio: str = "1:1",
    number_of_images: int = 1,
    max_retries: int = 3
) -> Tuple[bool, str]:
    """
    Generates an image using a pre-flight verified Imagen model and saves it to output_path.
    Includes rate-limit retry handling.
    
    Returns:
        Tuple[bool, str]: (Success status, output_path or error_message)
    """
    is_healthy, working_model = verify_imagen_model_health()
    if not is_healthy or not working_model:
        err_msg = "Pre-flight health check failed. No working Imagen model available."
        logger.error(err_msg)
        return False, err_msg

    client = get_imagen_client()
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Generating image with model '{working_model}' (attempt {attempt+1}) for target path: {output_path}")
            res = client.models.generate_images(
                model=working_model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=number_of_images,
                    output_mime_type="image/png",
                    aspect_ratio=aspect_ratio
                )
            )
            if not res or not res.generated_images:
                return False, "Imagen API returned empty response."

            img_bytes = res.generated_images[0].image.image_bytes
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(img_bytes)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"✅ Image successfully generated and saved to {output_path} ({os.path.getsize(output_path)} bytes)")
                return True, output_path
            else:
                return False, f"File {output_path} was created but is empty."

        except Exception as e:
            err_str = str(e)
            if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_retries:
                wait_sec = (attempt + 1) * 4
                logger.warning(f"⚠️ Rate limit hit (429) during generation. Backing off for {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                logger.error(f"Failed to generate image with model '{working_model}': {e}")
                return False, str(e)

    return False, "Max retries exceeded for image generation."

if __name__ == "__main__":
    print("Testing imagen_util directly...")
    success, result = generate_imagen_avatar(
        prompt="A high-contrast 2D vector icon of a cyan baseball cap",
        output_path="/tmp/imagen_util_test.png"
    )
    print(f"Result: success={success}, output={result}")
