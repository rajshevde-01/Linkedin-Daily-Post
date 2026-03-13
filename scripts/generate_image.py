"""
Canva-Style Professional Image Generator for LinkedIn Posts.
Generates 1200x628px images with 6 premium templates.
"""
import os
import sys
import random
import math
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- Brand Palette ---
DEEP_TEAL = (10, 46, 54)        # #0A2E36
ELECTRIC_CYAN = (0, 212, 255)   # #00D4FF
AMBER_GOLD = (255, 184, 0)      # #FFB800
CHARCOAL = (26, 26, 46)         # #1A1A2E
OFF_WHITE = (245, 240, 235)     # #F5F0EB
PURE_WHITE = (255, 255, 255)
TERMINAL_GREEN = (0, 255, 65)   # #00FF41
NEAR_BLACK = (12, 12, 18)       # #0C0C12

# --- Canvas ---
WIDTH = 1200
HEIGHT = 628

FONTS_DIR = Path(__file__).parent / "fonts"

def get_font(name="Inter", size=40):
    """Load a font, with fallback to default."""
    font_map = {
        "Inter": FONTS_DIR / "Inter.ttf",
        "JetBrains": FONTS_DIR / "JetBrainsMono-Regular.ttf",
    }
    font_path = font_map.get(name)
    try:
        if font_path and font_path.exists():
            return ImageFont.truetype(str(font_path), size)
    except Exception:
        pass
    # Fallback
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def extract_headline(post_text: str) -> str:
    """Extract or create a short headline from post text."""
    lines = [l.strip() for l in post_text.strip().split('\n') if l.strip()]
    if not lines:
        return "Cybersecurity Insight"
    
    first_line = lines[0]
    # Remove emojis and special chars from start
    import re
    first_line = re.sub(r'^[^\w\s]+', '', first_line).strip()
    
    # If first line is too long, truncate smartly
    if len(first_line) > 80:
        words = first_line.split()
        headline = ""
        for word in words:
            if len(headline + " " + word) > 75:
                break
            headline = (headline + " " + word).strip()
        return headline + "..."
    
    return first_line if first_line else "Cybersecurity Insight"


def draw_gradient(draw, width, height, color1, color2, direction="vertical"):
    """Draw a smooth gradient background."""
    for i in range(height if direction == "vertical" else width):
        ratio = i / (height if direction == "vertical" else width)
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        if direction == "vertical":
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        else:
            draw.line([(i, 0), (i, height)], fill=(r, g, b))


def draw_text_wrapped(draw, text, font, max_width, start_x, start_y, fill=PURE_WHITE, line_spacing=12):
    """Draw text that wraps within max_width and return total text height."""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    
    y = start_y
    for line in lines:
        draw.text((start_x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing
    
    return y - start_y


# ============================================================
# TEMPLATE 1: Dark Gradient (War Story)
# ============================================================
def template_dark_gradient(headline: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Background gradient: Navy → Deep Teal
    draw_gradient(draw, WIDTH, HEIGHT, (8, 15, 40), DEEP_TEAL)
    
    # Cyan accent bar on left
    draw.rectangle([(0, 0), (6, HEIGHT)], fill=ELECTRIC_CYAN)
    
    # Decorative thin line
    draw.line([(60, HEIGHT - 80), (WIDTH - 60, HEIGHT - 80)], fill=(*ELECTRIC_CYAN, 80), width=1)
    
    # Headline
    font_title = get_font("Inter", 52)
    draw_text_wrapped(draw, headline, font_title, WIDTH - 160, 80, 160, fill=PURE_WHITE)
    
    # Bottom accent text
    font_small = get_font("Inter", 18)
    draw.text((80, HEIGHT - 60), "— FIELD REPORT", font=font_small, fill=ELECTRIC_CYAN)
    
    # Top-right decorative dots
    for i in range(5):
        x = WIDTH - 80 + (i * 12)
        draw.ellipse([(x, 30), (x + 4, 34)], fill=AMBER_GOLD)
    
    return img


# ============================================================
# TEMPLATE 2: Neon Split (Unpopular Opinion)
# ============================================================
def template_neon_split(headline: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Left panel: Cyan block (30% width)
    split_x = 360
    draw_gradient(draw, split_x, HEIGHT, (0, 160, 200), ELECTRIC_CYAN)
    draw.rectangle([(0, 0), (split_x, HEIGHT)], fill=None)
    
    # Right panel: Charcoal
    draw.rectangle([(split_x, 0), (WIDTH, HEIGHT)], fill=CHARCOAL)
    
    # Left panel: Large "!" or "⚡"
    font_symbol = get_font("Inter", 180)
    draw.text((100, 180), "!", font=font_symbol, fill=PURE_WHITE)
    
    # Right panel: Headline
    font_title = get_font("Inter", 44)
    draw_text_wrapped(draw, headline, font_title, WIDTH - split_x - 100, split_x + 50, 140, fill=PURE_WHITE)
    
    # Right panel: Bottom accent
    font_small = get_font("Inter", 16)
    draw.text((split_x + 50, HEIGHT - 60), "UNPOPULAR OPINION", font=font_small, fill=AMBER_GOLD)
    
    # Divider line
    draw.line([(split_x, 0), (split_x, HEIGHT)], fill=AMBER_GOLD, width=3)
    
    return img


# ============================================================
# TEMPLATE 3: Clean Grid (Cheat Sheet)
# ============================================================
def template_clean_grid(headline: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Charcoal background
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=CHARCOAL)
    
    # Subtle grid pattern
    grid_color = (40, 40, 65)
    for x in range(0, WIDTH, 40):
        draw.line([(x, 0), (x, HEIGHT)], fill=grid_color, width=1)
    for y in range(0, HEIGHT, 40):
        draw.line([(0, y), (WIDTH, y)], fill=grid_color, width=1)
    
    # Central card with slight padding
    card_margin = 60
    card_rect = [(card_margin, card_margin), (WIDTH - card_margin, HEIGHT - card_margin)]
    draw.rounded_rectangle(card_rect, radius=16, fill=(30, 30, 50), outline=ELECTRIC_CYAN, width=1)
    
    # Headline centered
    font_title = get_font("Inter", 46)
    draw_text_wrapped(draw, headline, font_title, WIDTH - 200, 100, 160, fill=PURE_WHITE)
    
    # Bottom label
    font_small = get_font("Inter", 16)
    draw.text((100, HEIGHT - 100), "📋 QUICK REFERENCE GUIDE", font=font_small, fill=AMBER_GOLD)
    
    # Top corner accent dots
    for i in range(3):
        draw.rounded_rectangle(
            [(WIDTH - 140 + i * 35, 80), (WIDTH - 115 + i * 35, 88)],
            radius=4, fill=ELECTRIC_CYAN if i == 0 else AMBER_GOLD if i == 1 else PURE_WHITE
        )
    
    return img


# ============================================================
# TEMPLATE 4: Terminal (Technical Deep-Dive)
# ============================================================
def template_terminal(headline: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Pure black background
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=NEAR_BLACK)
    
    # Terminal window chrome
    chrome_height = 40
    draw.rectangle([(0, 0), (WIDTH, chrome_height)], fill=(35, 35, 45))
    # Traffic light dots
    draw.ellipse([(20, 12), (36, 28)], fill=(255, 95, 87))  # Red
    draw.ellipse([(46, 12), (62, 28)], fill=(255, 189, 46))  # Yellow
    draw.ellipse([(72, 12), (88, 28)], fill=(39, 201, 63))   # Green
    
    # Terminal title
    font_small = get_font("JetBrains", 13)
    draw.text((110, 13), "root@threat-lab:~", font=font_small, fill=(150, 150, 170))
    
    # Main content in terminal
    font_mono = get_font("JetBrains", 16)
    font_title = get_font("JetBrains", 32)
    
    y = chrome_height + 40
    draw.text((40, y), "$ cat /var/log/analysis.md", font=font_mono, fill=TERMINAL_GREEN)
    y += 40
    draw.text((40, y), "---", font=font_mono, fill=(100, 100, 120))
    y += 30
    
    # Headline in bright green
    draw_text_wrapped(draw, headline, font_title, WIDTH - 120, 40, y, fill=TERMINAL_GREEN)
    
    # Bottom prompt with blinking cursor
    draw.text((40, HEIGHT - 60), "$ █", font=font_mono, fill=TERMINAL_GREEN)
    
    # Scanline effect (subtle horizontal lines)
    for sy in range(0, HEIGHT, 4):
        draw.line([(0, sy), (WIDTH, sy)], fill=(0, 0, 0, 15), width=1)
    
    return img


# ============================================================
# TEMPLATE 5: Bold Question (Poll for Change)
# ============================================================
def template_bold_question(headline: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Teal → Cyan gradient
    draw_gradient(draw, WIDTH, HEIGHT, DEEP_TEAL, (0, 100, 130))
    
    # Large "?" watermark
    font_q = get_font("Inter", 400)
    # Semi-transparent question mark in background
    draw.text((WIDTH - 350, 50), "?", font=font_q, fill=(255, 184, 0, 40))
    
    # Headline centered
    font_title = get_font("Inter", 50)
    
    # Center the text vertically
    draw_text_wrapped(draw, headline, font_title, WIDTH - 200, 100, 180, fill=PURE_WHITE)
    
    # Bottom label
    font_small = get_font("Inter", 18)
    draw.text((100, HEIGHT - 60), "WHAT DO YOU THINK?", font=font_small, fill=AMBER_GOLD)
    
    # Top accent line
    draw.rectangle([(0, 0), (WIDTH, 5)], fill=AMBER_GOLD)
    
    return img


# ============================================================
# TEMPLATE 6: Minimal Pro (Practitioner Insight)
# ============================================================
def template_minimal_pro(headline: str) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Off-white background
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=OFF_WHITE)
    
    # Thin Teal accent line on left
    draw.rectangle([(60, 100), (64, HEIGHT - 100)], fill=DEEP_TEAL)
    
    # Headline in dark text
    font_title = get_font("Inter", 46)
    draw_text_wrapped(draw, headline, font_title, WIDTH - 240, 100, 180, fill=CHARCOAL)
    
    # Bottom subtle label
    font_small = get_font("Inter", 16)
    draw.text((100, HEIGHT - 70), "A PRACTITIONER'S PERSPECTIVE", font=font_small, fill=(*DEEP_TEAL, 180))
    
    # Small accent dot
    draw.ellipse([(WIDTH - 100, HEIGHT - 70), (WIDTH - 88, HEIGHT - 58)], fill=AMBER_GOLD)
    
    return img


# ============================================================
# MAIN ENGINE
# ============================================================
TEMPLATES = {
    "war_story": template_dark_gradient,
    "unpopular_opinion": template_neon_split,
    "cheat_sheet": template_clean_grid,
    "deep_dive": template_terminal,
    "poll": template_bold_question,
    "insight": template_minimal_pro,
}

TEMPLATE_NAMES = list(TEMPLATES.keys())


def generate_post_image(post_text: str, template_name: str = None) -> str:
    """
    Generate a professional LinkedIn image from post text.
    Returns the path to the generated image.
    """
    headline = extract_headline(post_text)
    
    if template_name and template_name in TEMPLATES:
        template_fn = TEMPLATES[template_name]
    else:
        template_fn = random.choice(list(TEMPLATES.values()))
        template_name = [k for k, v in TEMPLATES.items() if v == template_fn][0]
    
    print(f"[INFO] Using template: {template_name}")
    img = template_fn(headline)
    
    # Save to posts/images/
    images_dir = Path(__file__).parent.parent / "posts" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{template_name}.png"
    filepath = images_dir / filename
    
    img.save(str(filepath), "PNG", quality=95)
    print(f"[SUCCESS] Image saved: {filepath}")
    return str(filepath)


def test_all_templates():
    """Generate one sample of each template for visual review."""
    test_headlines = [
        "The logs didn't match the traffic. Our SOC knew instantly — lateral movement confirmed.",
        "Your SIEM is just an expensive graveyard for logs. Change my mind.",
        "Zero Trust Architecture: 5 Essential Controls for 2026",
        "CVE-2026-1234: Remote Code Execution in Apache Struts via OGNL Injection",
        "You have 1 hour until the deadline. Patch the critical CVE or investigate the anomaly?",
        "Just wrapped up a call with our red team and this keeps bugging me...",
    ]
    
    images_dir = Path(__file__).parent.parent / "posts" / "images" / "test"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    for i, (name, fn) in enumerate(TEMPLATES.items()):
        headline = test_headlines[i]
        img = fn(headline)
        filepath = images_dir / f"test_{name}.png"
        img.save(str(filepath), "PNG", quality=95)
        print(f"[OK] {name}: {filepath}")
    
    print(f"\n[SUCCESS] All 6 test images saved to: {images_dir}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_all_templates()
    else:
        # Quick single test
        sample = "Ransomware gangs are now exploiting zero-day vulnerabilities faster than ever. Here's what changed."
        path = generate_post_image(sample)
        print(f"Generated: {path}")
