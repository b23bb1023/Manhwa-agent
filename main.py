from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import re

app = FastAPI()

@app.get("/scrape")
def scrape_chapter(url: str):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            print(f"--- Scraping: {url} ---")
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except:
                print("Page load timeout, attempting parse anyway...")

            # --- 1. FIND CHAPTERS ---
            selectors = [
                'h3.text-sm.text-white.font-medium', 
                'a[href*="/chapter/"] h3',
                'a[href*="/chapter/"]'
            ]
            
            found_texts = []
            for sel in selectors:
                try:
                    elements = page.locator(sel).all_inner_texts()
                    if elements: found_texts.extend(elements)
                except: continue

            chapters = []
            for text in found_texts:
                match = re.search(r'(?:Chapter|Ch\.?|Episode)\s*(\d+)', text, re.IGNORECASE)
                if match: chapters.append(int(match.group(1)))
                elif text.strip().isdigit(): chapters.append(int(text.strip()))

            # --- 2. FIND THUMBNAIL ---
            thumbnail_url = ""
            try:
                # Asura specific: The image is usually the first one in the relative container or has alt text matching the series
                # We try a few common locations for cover images
                img_selectors = [
                    'img[alt*="cover"]',
                    'div.relative img',   # Common wrapper for posters
                    'div.grid img',       # Grid layout poster
                    'img'                 # Fallback: grab first significant image
                ]
                
                for sel in img_selectors:
                    # Get the first matching image
                    imgs = page.locator(sel).all()
                    for img in imgs:
                        src = img.get_attribute("src")
                        # Filter out tiny icons or logos
                        if src and "http" in src and "logo" not in src and "icon" not in src:
                            thumbnail_url = src
                            print(f"Found thumbnail: {thumbnail_url}")
                            break
                    if thumbnail_url: break
            except Exception as e:
                print(f"Thumbnail error: {e}")

            browser.close()
            
            # --- RESULTS ---
            clean_chapters = [c for c in chapters if c < 2000]
            max_chap = max(clean_chapters) if clean_chapters else 0
            
            return {
                "status": "success",
                "latest_chapter": max_chap,
                "thumbnail": thumbnail_url
            }
            
    except Exception as e:
        return {"status": "error", "message": str(e), "latest_chapter": 0, "thumbnail": ""}