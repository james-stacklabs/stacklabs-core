import sys
import json
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel

router = APIRouter()

class OptimizationPayload(BaseModel):
    raw_text: str
    macro_mode: str  # 'cinematic', 'raw_entropy', 'retro_16bit', 'mixed_media'
    style_sheet: str = "style_a"  # 'style_a', 'style_b', 'style_c', 'style_d', 'style_e'
    city_name: str = "Seattle"
    character_description: str = "an anxious sports advocate"

@router.post("/api/system/seeder/optimize")
def optimize_prompt(payload: OptimizationPayload):
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be blank.")
        
    # Enforce strict token boundaries by truncating incoming raw prompts to 1000 characters
    truncated = False
    if len(payload.raw_text) > 1000:
        base_text = payload.raw_text[:1000]
        truncated = True
    else:
        base_text = payload.raw_text
    
    # Process custom style sheets under the Brooks Exception
    style = payload.style_sheet.lower() if payload.style_sheet else "style_a"
    
    if style == "style_a" or "muppet" in style:
        style_desc = f"Styled under the Brooks Exception (Muppet Hell - Rowdy Fleece Puppets): Real-life high-resolution wide-angle background video plate of the {payload.city_name} streets at sunset. In the foreground, {payload.character_description} is rendered as a rowdy, unhinged fleece puppet with googly eyes waving a flag, close-up shot."
    elif style == "style_b" or "cartoon" in style or "90s" in style:
        style_desc = f"Styled under the Brooks Exception (90s Saturday Morning Cartoons): Thick black outline treatments, saturated ink layers, and high squash-and-stretch physics inspired by vintage Nickelodeon/MTV animations of {payload.character_description} with exaggerated facial expressions, holding a mega-phone."
    elif style == "style_c" or "cardboard" in style or "cutout" in style:
        style_desc = f"Styled under the Brooks Exception (Flat Cardboard Cutouts): 2D caricature drawings of {payload.character_description} mounted on visible wooden popsicle sticks sliding across a physical shadow-box stadium stage canvas."
    elif style == "style_d" or "pixel" in style or "retro" in style or "16-bit" in style:
        style_desc = f"Styled under the Brooks Exception (16-Bit Sandbox Retro): Exaggerated retro pixel-art animations of {payload.character_description} for high-leverage events (reusing Smyrna Heights sandbox assets)."
    elif style == "style_e" or "print" in style or "caricature" in style:
        style_desc = f"Styled under the Brooks Exception (Classic Print Caricatures): Rough-inked newspaper editorial sports caricatures of {payload.character_description}."
    else:
        style_desc = f"Styled under the Brooks Exception: represented as a creative parody of {payload.character_description}."

    # Apply strict macro processing logic based on the user's selected toggle button
    if payload.macro_mode == "cinematic":
        enriched = f"{base_text}. {style_desc}"
    elif payload.macro_mode == "mixed_media":
        enriched = f"{base_text}. {style_desc}"
    elif payload.macro_mode == "raw_entropy":
        enriched = f"{base_text}. Infuse strict structural fatalism, caps-lock volatility spikes, and raw unhinged stadium heartbreak terminology."
    elif payload.macro_mode == "retro_16bit":
        enriched = f"{base_text}. Aligned with the metsy-prime 16-bit Cozy Kiosk framework, utilizing rigid coordinates and tactical grid parameters."
    else:
        # Fallback to standard cinematic style sheet injection
        enriched = f"{base_text}. {style_desc}"
        
    return {
        "status": "WARNING" if truncated else "SUCCESS",
        "optimized_prompt": enriched,
        "warning": "Prompt truncated to 1000 characters due to API Token Budget Lock constraints." if truncated else None
    }

# Expose as a standalone app if executed directly via Uvicorn on Port 5057
app = FastAPI(title="Sovereign Prompt Decoder Gate")
app.include_router(router)
