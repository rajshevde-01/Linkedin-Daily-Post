"""
Canva-Style Professional Image Generator for LinkedIn Posts.
Generates 1200x628px images with catchy text, branding, and 6 premium templates.
"""
import os
import sys
import re
import random
import math
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
DARK_NAVY = (8, 15, 40)

# --- Canvas ---
WIDTH = 1200
HEIGHT = 628

FONTS_DIR = Path(__file__).parent / "fonts"
BRAND_NAME = "RAJ SHEVDE"
BRAND_TAGLINE = "Cybersecurity • Threat Intelligence"


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
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


# ============================================================
# TEXT EXTRACTION — Catchy headline + subtitle from post
# ============================================================
def extract_content(post_text: str) -> dict:
    """Extract headline, subtitle, and key takeaway from post text."""
    lines = [l.strip() for l in post_text.strip().split('\n') if l.strip()]
    
    # Clean all lines of emojis/special prefix chars
    clean_lines = []
    for l in lines:
        cleaned = re.sub(r'^[^\w\s"\']+', '', l).strip()
        # Skip very short lines, hashtag lines, source lines
        if cleaned and len(cleaned) > 10 and not cleaned.startswith('#') and not cleaned.startswith('🔗'):
            clean_lines.append(cleaned)
    
    if not clean_lines:
        return {"headline": "Cybersecurity Insight", "subtitle": "", "takeaway": ""}
    
    # Headline: first substantial line, truncated smartly
    headline = clean_lines[0]
    if len(headline) > 70:
        words = headline.split()
        short = ""
        for w in words:
            if len(short + " " + w) > 65:
                break
            short = (short + " " + w).strip()
        headline = short + "..."
    
    # Subtitle: second substantial line (if different enough)
    subtitle = ""
    if len(clean_lines) > 1:
        sub = clean_lines[1]
        if len(sub) > 60:
            words = sub.split()
            short = ""
            for w in words:
                if len(short + " " + w) > 55:
                    break
                short = (short + " " + w).strip()
            sub = short + "..."
        subtitle = sub
    
    # Takeaway: look for a line that sounds like a conclusion or key point
    takeaway = ""
    for l in clean_lines[-3:]:
        if any(kw in l.lower() for kw in ['bottom line', 'takeaway', 'lesson', 'remember', 'the reality', 'patch', 'update']):
            takeaway = l[:80]
            break
    
    return {"headline": headline, "subtitle": subtitle, "takeaway": takeaway}


# ============================================================
# DRAWING UTILITIES
# ============================================================
def draw_gradient(draw, width, height, color1, color2, direction="vertical"):
    """Draw a smooth gradient."""
    for i in range(height if direction == "vertical" else width):
        ratio = i / max(1, (height if direction == "vertical" else width) - 1)
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        if direction == "vertical":
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        else:
            draw.line([(i, 0), (i, height)], fill=(r, g, b))


def draw_text_wrapped(draw, text, font, max_width, start_x, start_y, fill=PURE_WHITE, line_spacing=10):
    """Draw word-wrapped text. Returns total height used."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test
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


def draw_shield_logo(draw, x, y, size=40, color=ELECTRIC_CYAN):
    """Draw a simple shield icon as the brand logo."""
    s = size
    # Shield shape using polygon
    points = [
        (x + s // 2, y),           # top center
        (x + s, y + s // 4),       # top right
        (x + s, y + s * 2 // 3),   # mid right
        (x + s // 2, y + s),       # bottom center (point)
        (x, y + s * 2 // 3),       # mid left
        (x, y + s // 4),           # top left
    ]
    draw.polygon(points, fill=color)
    # Inner shield (smaller, darker)
    inner_margin = size // 5
    inner_points = [
        (x + s // 2, y + inner_margin),
        (x + s - inner_margin, y + s // 4 + inner_margin // 2),
        (x + s - inner_margin, y + s * 2 // 3 - inner_margin // 2),
        (x + s // 2, y + s - inner_margin),
        (x + inner_margin, y + s * 2 // 3 - inner_margin // 2),
        (x + inner_margin, y + s // 4 + inner_margin // 2),
    ]
    draw.polygon(inner_points, fill=CHARCOAL)
    # Checkmark inside
    cx, cy = x + s // 2, y + s // 2
    draw.line([(cx - 6, cy), (cx - 1, cy + 5), (cx + 8, cy - 6)], fill=color, width=2)


def draw_brand_bar(draw, y_pos, bg_dark=True):
    """Draw the bottom brand bar with logo + name."""
    bar_height = 55
    bar_color = (15, 15, 25) if bg_dark else (230, 225, 218)
    text_color = PURE_WHITE if bg_dark else CHARCOAL
    
    # Brand bar background
    draw.rectangle([(0, y_pos), (WIDTH, y_pos + bar_height)], fill=bar_color)
    # Top accent line
    draw.rectangle([(0, y_pos), (WIDTH, y_pos + 2)], fill=ELECTRIC_CYAN)
    
    # Shield logo
    draw_shield_logo(draw, 30, y_pos + 10, size=35, color=ELECTRIC_CYAN)
    
    # Brand name
    font_brand = get_font("Inter", 16)
    draw.text((75, y_pos + 12), BRAND_NAME, font=font_brand, fill=text_color)
    
    font_tag = get_font("Inter", 12)
    draw.text((75, y_pos + 32), BRAND_TAGLINE, font=font_tag, fill=ELECTRIC_CYAN if bg_dark else DEEP_TEAL)
    
    # Right side: website/social
    font_right = get_font("Inter", 13)
    draw.text((WIDTH - 200, y_pos + 20), "linkedin.com/in/rajshevde", font=font_right, fill=(*text_color[:3], 150) if bg_dark else (*CHARCOAL, 150))


# ============================================================
# TEMPLATE 1: Dark Gradient (War Story)
# ============================================================
def template_dark_gradient(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    draw_gradient(draw, WIDTH, HEIGHT, DARK_NAVY, DEEP_TEAL)
    
    # Left accent bar
    draw.rectangle([(0, 0), (6, HEIGHT)], fill=ELECTRIC_CYAN)
    
    # Decorative floating circles (top right)
    for i in range(8):
        cx = WIDTH - 50 - random.randint(0, 200)
        cy = 20 + random.randint(0, 80)
        r = random.randint(2, 6)
        opacity_color = (*ELECTRIC_CYAN[:3],)
        draw.ellipse([(cx, cy), (cx + r*2, cy + r*2)], fill=opacity_color)
    
    # Category label
    font_label = get_font("Inter", 14)
    label = "FIELD REPORT"
    draw.rounded_rectangle([(80, 50), (80 + len(label)*9 + 20, 78)], radius=4, fill=ELECTRIC_CYAN)
    draw.text((90, 55), label, font=font_label, fill=CHARCOAL)
    
    # Headline
    font_title = get_font("Inter", 48)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 160, 80, 100, fill=PURE_WHITE)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 22)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 160, 80, 340, fill=(*PURE_WHITE[:3],))
    
    # Divider line
    draw.line([(80, HEIGHT - 80), (WIDTH - 80, HEIGHT - 80)], fill=ELECTRIC_CYAN, width=1)
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 2: Neon Split (Unpopular Opinion)
# ============================================================
def template_neon_split(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    split_x = 340
    
    # Left panel: gradient
    for i in range(split_x):
        ratio = i / split_x
        r = int(0 + (0 * ratio))
        g = int(160 + (52 * ratio))
        b = int(200 + (55 * ratio))
        draw.line([(i, 0), (i, HEIGHT)], fill=(r, g, b))
    
    # Right panel
    draw.rectangle([(split_x, 0), (WIDTH, HEIGHT)], fill=CHARCOAL)
    
    # Divider
    draw.line([(split_x, 0), (split_x, HEIGHT)], fill=AMBER_GOLD, width=3)
    
    # Left: Large icon
    font_icon = get_font("Inter", 160)
    draw.text((90, 130), "⚡", font=font_icon, fill=PURE_WHITE)
    
    # Left: label
    font_label = get_font("Inter", 14)
    draw.rounded_rectangle([(40, 50), (230, 78)], radius=4, fill=PURE_WHITE)
    draw.text((52, 55), "UNPOPULAR OPINION", font=font_label, fill=CHARCOAL)
    
    # Right: Headline
    font_title = get_font("Inter", 40)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - split_x - 100, split_x + 50, 100, fill=PURE_WHITE)
    
    # Right: Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 20)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - split_x - 100, split_x + 50, 340, fill=(*PURE_WHITE[:3],))
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 3: Clean Grid (Cheat Sheet)
# ============================================================
def template_clean_grid(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=CHARCOAL)
    
    # Grid
    grid_color = (40, 40, 65)
    for x in range(0, WIDTH, 40):
        draw.line([(x, 0), (x, HEIGHT)], fill=grid_color, width=1)
    for y in range(0, HEIGHT, 40):
        draw.line([(0, y), (WIDTH, y)], fill=grid_color, width=1)
    
    # Card
    margin = 50
    draw.rounded_rectangle(
        [(margin, margin), (WIDTH - margin, HEIGHT - margin)],
        radius=16, fill=(30, 30, 50), outline=ELECTRIC_CYAN, width=1
    )
    
    # Top-left label badge
    font_label = get_font("Inter", 13)
    draw.rounded_rectangle([(70, 65), (270, 90)], radius=12, fill=AMBER_GOLD)
    draw.text((82, 69), "QUICK REFERENCE GUIDE", font=font_label, fill=CHARCOAL)
    
    # Headline
    font_title = get_font("Inter", 42)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 180, 80, 120, fill=PURE_WHITE)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 20)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 180, 80, 320, fill=(*ELECTRIC_CYAN[:3],))
    
    # Accent dots top right inside card
    for i in range(3):
        draw.rounded_rectangle(
            [(WIDTH - 160 + i * 35, 70), (WIDTH - 135 + i * 35, 78)],
            radius=4, fill=ELECTRIC_CYAN if i == 0 else AMBER_GOLD if i == 1 else PURE_WHITE
        )
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 4: Terminal (Technical Deep-Dive)
# ============================================================
def template_terminal(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=NEAR_BLACK)
    
    # Window chrome
    chrome_h = 40
    draw.rectangle([(0, 0), (WIDTH, chrome_h)], fill=(35, 35, 45))
    draw.ellipse([(20, 12), (36, 28)], fill=(255, 95, 87))
    draw.ellipse([(46, 12), (62, 28)], fill=(255, 189, 46))
    draw.ellipse([(72, 12), (88, 28)], fill=(39, 201, 63))
    
    font_chrome = get_font("JetBrains", 13)
    draw.text((110, 13), "root@threat-lab:~ $ analysis", font=font_chrome, fill=(150, 150, 170))
    
    font_mono = get_font("JetBrains", 15)
    font_title = get_font("JetBrains", 30)
    
    y = chrome_h + 30
    draw.text((40, y), "$ cat /var/log/intel_brief.md", font=font_mono, fill=TERMINAL_GREEN)
    y += 35
    draw.text((40, y), "═" * 50, font=font_mono, fill=(60, 60, 80))
    y += 30
    
    # Headline
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 120, 40, y, fill=TERMINAL_GREEN)
    
    # Subtitle as a comment
    if content["subtitle"]:
        font_comment = get_font("JetBrains", 16)
        draw_text_wrapped(draw, f"# {content['subtitle']}", font_comment, WIDTH - 120, 40, y + 130, fill=(100, 200, 100))
    
    # Bottom prompt
    draw.text((40, HEIGHT - 75), "$ echo $RECOMMENDATION", font=font_mono, fill=(100, 100, 130))
    draw.text((40, HEIGHT - 50), "> Patch immediately. Monitor for IOCs. █", font=font_mono, fill=TERMINAL_GREEN)
    
    # Scanline effect
    for sy in range(0, HEIGHT, 3):
        draw.line([(0, sy), (WIDTH, sy)], fill=(0, 0, 0), width=1)
    
    return img


# ============================================================
# TEMPLATE 5: Bold Question (Poll for Change)
# ============================================================
def template_bold_question(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    draw_gradient(draw, WIDTH, HEIGHT, DEEP_TEAL, (0, 80, 105))
    
    # Large "?" watermark
    font_q = get_font("Inter", 380)
    draw.text((WIDTH - 340, 30), "?", font=font_q, fill=AMBER_GOLD)
    
    # Top accent
    draw.rectangle([(0, 0), (WIDTH, 5)], fill=AMBER_GOLD)
    
    # Label
    font_label = get_font("Inter", 14)
    draw.rounded_rectangle([(80, 40), (240, 66)], radius=4, fill=AMBER_GOLD)
    draw.text((92, 44), "POLL • YOUR TAKE?", font=font_label, fill=CHARCOAL)
    
    # Headline
    font_title = get_font("Inter", 46)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 300, 80, 100, fill=PURE_WHITE)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 20)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 300, 80, 360, fill=(*PURE_WHITE[:3],))
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 6: Minimal Pro (Practitioner Insight)
# ============================================================
def template_minimal_pro(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=OFF_WHITE)
    
    # Thin accent line on left
    draw.rectangle([(60, 80), (64, HEIGHT - 80)], fill=DEEP_TEAL)
    
    # Top label
    font_label = get_font("Inter", 13)
    draw.text((90, 65), "A PRACTITIONER'S PERSPECTIVE", font=font_label, fill=DEEP_TEAL)
    
    # Headline
    font_title = get_font("Inter", 42)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 200, 90, 110, fill=CHARCOAL)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 20)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 200, 90, 330, fill=(*DEEP_TEAL,))
    
    # Small accent dot
    draw.ellipse([(WIDTH - 90, 80), (WIDTH - 76, 94)], fill=AMBER_GOLD)
    draw.ellipse([(WIDTH - 70, 80), (WIDTH - 56, 94)], fill=ELECTRIC_CYAN)
    
    # Brand bar (light version)
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=False)
    
    return img


# ============================================================
# TEMPLATE 7: SOC Alert Dashboard
# ============================================================
def template_soc_alert(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # Dark background
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(8, 8, 16))
    
    # Top status bar (red severity)
    ALERT_RED = (220, 50, 47)
    draw.rectangle([(0, 0), (WIDTH, 50)], fill=(30, 10, 12))
    draw.rectangle([(0, 0), (WIDTH, 3)], fill=ALERT_RED)
    
    # Status indicators in top bar
    font_status = get_font("JetBrains", 12)
    draw.ellipse([(20, 18), (34, 32)], fill=ALERT_RED)
    draw.text((42, 18), "SEVERITY: CRITICAL", font=font_status, fill=ALERT_RED)
    
    draw.ellipse([(250, 18), (264, 32)], fill=AMBER_GOLD)
    draw.text((272, 18), "STATUS: ACTIVE", font=font_status, fill=AMBER_GOLD)
    
    draw.ellipse([(460, 18), (474, 32)], fill=TERMINAL_GREEN)
    draw.text((482, 18), "SOC TIER: 2", font=font_status, fill=TERMINAL_GREEN)
    
    # Timestamp right side
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    draw.text((WIDTH - 220, 18), ts, font=font_status, fill=(100, 100, 120))
    
    # Alert ID badge
    font_label = get_font("JetBrains", 13)
    alert_id = f"ALERT-{random.randint(1000, 9999)}"
    draw.rounded_rectangle([(40, 70), (190, 94)], radius=4, fill=ALERT_RED)
    draw.text((52, 74), alert_id, font=font_label, fill=PURE_WHITE)
    
    # Headline
    font_title = get_font("Inter", 42)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 120, 40, 115, fill=PURE_WHITE)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 19)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 120, 40, 310, fill=(180, 180, 200))
    
    # Bottom metrics bar
    metrics_y = HEIGHT - 100
    draw.line([(40, metrics_y), (WIDTH - 40, metrics_y)], fill=(40, 40, 60), width=1)
    
    font_metric = get_font("JetBrains", 14)
    metrics = [
        ("AFFECTED HOSTS", str(random.randint(12, 250)), ALERT_RED),
        ("INDICATORS", str(random.randint(5, 40)), AMBER_GOLD),
        ("TIME TO DETECT", f"{random.randint(2, 15)}m", TERMINAL_GREEN),
        ("CONFIDENCE", f"{random.randint(85, 99)}%", ELECTRIC_CYAN),
    ]
    mx = 50
    for label, value, color in metrics:
        draw.text((mx, metrics_y + 10), label, font=get_font("JetBrains", 10), fill=(80, 80, 100))
        draw.text((mx, metrics_y + 26), value, font=font_metric, fill=color)
        mx += 260
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 8: Threat Radar / Scan Grid
# ============================================================
def template_threat_radar(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(5, 10, 20))
    
    # Radar grid (concentric circles + crosshair)
    center_x, center_y = WIDTH - 200, HEIGHT // 2
    for r in range(50, 300, 60):
        draw.ellipse(
            [(center_x - r, center_y - r), (center_x + r, center_y + r)],
            outline=(0, 60, 80), width=1
        )
    # Crosshair
    draw.line([(center_x - 280, center_y), (center_x + 280, center_y)], fill=(0, 60, 80), width=1)
    draw.line([(center_x, center_y - 280), (center_x, center_y + 280)], fill=(0, 60, 80), width=1)
    
    # Threat dots on radar
    for _ in range(15):
        dx = random.randint(-200, 200)
        dy = random.randint(-200, 200)
        if dx * dx + dy * dy < 200 * 200:
            dot_color = random.choice([
                (220, 50, 47), AMBER_GOLD, ELECTRIC_CYAN, TERMINAL_GREEN
            ])
            dot_size = random.randint(3, 8)
            draw.ellipse(
                [(center_x + dx, center_y + dy), (center_x + dx + dot_size, center_y + dy + dot_size)],
                fill=dot_color
            )
    
    # Sweep line (static representation)
    import math as m
    angle = random.uniform(0, 2 * m.pi)
    sweep_end_x = center_x + int(250 * m.cos(angle))
    sweep_end_y = center_y + int(250 * m.sin(angle))
    draw.line([(center_x, center_y), (sweep_end_x, sweep_end_y)], fill=ELECTRIC_CYAN, width=2)
    
    # Left side content
    font_label = get_font("JetBrains", 12)
    draw.rounded_rectangle([(40, 40), (225, 64)], radius=4, fill=ELECTRIC_CYAN)
    draw.text((52, 44), "THREAT INTELLIGENCE", font=font_label, fill=CHARCOAL)
    
    font_title = get_font("Inter", 40)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH // 2 - 40, 40, 90, fill=PURE_WHITE)
    
    if content["subtitle"]:
        font_sub = get_font("Inter", 18)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH // 2 - 40, 40, 320, fill=(150, 200, 220))
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 9: Incident Response (Emergency Red)
# ============================================================
def template_incident_response(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    ALERT_RED = (200, 40, 40)
    DARK_RED = (40, 8, 8)
    
    # Dark red gradient
    draw_gradient(draw, WIDTH, HEIGHT, (15, 5, 8), DARK_RED)
    
    # Top red strip with pulse effect
    draw.rectangle([(0, 0), (WIDTH, 6)], fill=ALERT_RED)
    draw.rectangle([(0, HEIGHT - 62), (WIDTH, HEIGHT - 60)], fill=ALERT_RED)
    
    # Warning triangle icon
    tri_x, tri_y = WIDTH - 180, 50
    tri_size = 80
    points = [
        (tri_x + tri_size // 2, tri_y),
        (tri_x + tri_size, tri_y + tri_size),
        (tri_x, tri_y + tri_size),
    ]
    draw.polygon(points, fill=AMBER_GOLD)
    draw.text((tri_x + 30, tri_y + 25), "!", font=get_font("Inter", 40), fill=DARK_RED)
    
    # Label
    font_label = get_font("JetBrains", 14)
    draw.rounded_rectangle([(40, 40), (240, 66)], radius=4, fill=ALERT_RED)
    draw.text((52, 44), "INCIDENT RESPONSE", font=font_label, fill=PURE_WHITE)
    
    # Headline
    font_title = get_font("Inter", 44)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 250, 40, 90, fill=PURE_WHITE)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 19)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 120, 40, 310, fill=(220, 180, 180))
    
    # Response timeline at bottom
    timeline_y = HEIGHT - 100
    font_time = get_font("JetBrains", 11)
    phases = ["DETECT", "CONTAIN", "ERADICATE", "RECOVER"]
    phase_colors = [TERMINAL_GREEN, AMBER_GOLD, ALERT_RED, ELECTRIC_CYAN]
    px = 50
    for i, (phase, pcolor) in enumerate(zip(phases, phase_colors)):
        draw.rounded_rectangle([(px, timeline_y + 5), (px + 18, timeline_y + 23)], radius=9, fill=pcolor)
        draw.text((px + 25, timeline_y + 7), phase, font=font_time, fill=(180, 180, 190))
        if i < 3:
            draw.line([(px + 85, timeline_y + 14), (px + 120, timeline_y + 14)], fill=(60, 40, 40), width=1)
        px += 140 if i < 2 else 130
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 10: MITRE ATT&CK Framework
# ============================================================
def template_mitre_attack(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill=(10, 12, 22))
    
    # MITRE-style technique grid in background
    tactics = ["Recon", "Init Access", "Execution", "Persist", "Priv Esc", "Defense Ev", "Cred Access", "Lateral"]
    font_tactic = get_font("JetBrains", 9)
    
    cell_w = WIDTH // 8
    for i, tactic in enumerate(tactics):
        x = i * cell_w
        # Column header
        draw.rectangle([(x, 0), (x + cell_w - 2, 25)], fill=(30, 35, 55))
        draw.text((x + 5, 6), tactic.upper(), font=font_tactic, fill=(80, 90, 120))
        
        # Random technique cells (faded background effect)
        for j in range(random.randint(2, 5)):
            cell_y = 30 + j * 28
            highlighted = random.random() < 0.15
            cell_color = (60, 20, 20) if highlighted else (20, 22, 35)
            draw.rectangle([(x + 1, cell_y), (x + cell_w - 3, cell_y + 24)], fill=cell_color)
            if highlighted:
                draw.rectangle([(x + 1, cell_y), (x + 3, cell_y + 24)], fill=(200, 40, 40))
    
    # Content overlay card
    card_y = 180
    draw.rounded_rectangle(
        [(30, card_y), (WIDTH - 30, HEIGHT - 60)],
        radius=12, fill=(12, 14, 28, 230), outline=ELECTRIC_CYAN, width=1
    )
    
    # Label
    font_label = get_font("JetBrains", 12)
    draw.rounded_rectangle([(50, card_y + 15), (220, card_y + 38)], radius=4, fill=ELECTRIC_CYAN)
    draw.text((62, card_y + 18), "MITRE ATT&CK", font=font_label, fill=CHARCOAL)
    
    # Headline
    font_title = get_font("Inter", 38)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 120, 50, card_y + 55, fill=PURE_WHITE)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 17)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 120, 50, card_y + 190, fill=(150, 170, 200))
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
    return img


# ============================================================
# TEMPLATE 11: Breach Alert (Breaking News)
# ============================================================
def template_breach_alert(content: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    ALERT_RED = (200, 40, 40)
    
    # Dark background with slight red tint
    draw_gradient(draw, WIDTH, HEIGHT, (12, 5, 8), (20, 8, 12))
    
    # Top "BREAKING" banner
    draw.rectangle([(0, 0), (WIDTH, 60)], fill=ALERT_RED)
    font_break = get_font("Inter", 24)
    draw.text((WIDTH // 2 - 100, 15), "BREACH ALERT", font=font_break, fill=PURE_WHITE)
    
    # Side scan lines
    for i in range(0, HEIGHT, 8):
        alpha = random.randint(0, 15)
        draw.line([(0, i), (WIDTH, i)], fill=(200, 40, 40, alpha), width=1)
    
    # Shield icon (broken/cracked)
    draw_shield_logo(draw, WIDTH - 120, 80, size=60, color=ALERT_RED)
    
    # Headline
    font_title = get_font("Inter", 44)
    draw_text_wrapped(draw, content["headline"], font_title, WIDTH - 200, 50, 90, fill=PURE_WHITE)
    
    # Subtitle
    if content["subtitle"]:
        font_sub = get_font("Inter", 20)
        draw_text_wrapped(draw, content["subtitle"], font_sub, WIDTH - 120, 50, 320, fill=(220, 180, 180))
    
    # Bottom stats
    stats_y = HEIGHT - 100
    draw.line([(50, stats_y), (WIDTH - 50, stats_y)], fill=(60, 20, 20), width=1)
    font_stat = get_font("JetBrains", 12)
    
    records = f"{random.randint(1, 50)}M+ RECORDS"
    draw.text((60, stats_y + 10), records, font=font_stat, fill=ALERT_RED)
    draw.text((300, stats_y + 10), "DATA EXFILTRATION CONFIRMED", font=font_stat, fill=AMBER_GOLD)
    draw.text((650, stats_y + 10), "INVESTIGATION ONGOING", font=font_stat, fill=ELECTRIC_CYAN)
    
    # Brand bar
    draw_brand_bar(draw, HEIGHT - 55, bg_dark=True)
    
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
    "soc_alert": template_soc_alert,
    "threat_radar": template_threat_radar,
    "incident_response": template_incident_response,
    "mitre_attack": template_mitre_attack,
    "breach_alert": template_breach_alert,
}


def generate_post_image(post_text: str, template_name: str = None) -> str:
    """
    Generate a professional LinkedIn image from post text.
    Returns the path to the generated image.
    """
    content = extract_content(post_text)
    
    if template_name and template_name in TEMPLATES:
        template_fn = TEMPLATES[template_name]
    else:
        template_fn = random.choice(list(TEMPLATES.values()))
        template_name = [k for k, v in TEMPLATES.items() if v == template_fn][0]
    
    print(f"[INFO] Using template: {template_name}")
    print(f"[INFO] Headline: {content['headline'][:60]}...")
    img = template_fn(content)
    
    # Save
    images_dir = Path(__file__).parent.parent / "posts" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = images_dir / f"{timestamp}_{template_name}.png"
    
    img.save(str(filepath), "PNG", quality=95)
    print(f"[SUCCESS] Image saved: {filepath}")
    return str(filepath)


def test_all_templates():
    """Generate one sample of each template for visual review."""
    sample_post = """Ransomware gangs are now using AI-generated phishing lures to bypass email gateways.

We saw this firsthand during our latest incident response engagement. The payload was a polymorphic loader — it changed its hash on every execution.

Our SOC flagged the initial beacon within 8 minutes, but the lateral movement had already begun.

Bottom line: if your detection is still signature-based, you're already compromised.

🔗 Source: https://thehackernews.com/2026/03/ai-phishing.html
#Ransomware #ThreatIntel #SOC"""
    
    content = extract_content(sample_post)
    
    images_dir = Path(__file__).parent.parent / "posts" / "images" / "test"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    for name, fn in TEMPLATES.items():
        img = fn(content)
        filepath = images_dir / f"test_{name}.png"
        img.save(str(filepath), "PNG", quality=95)
        print(f"[OK] {name}: {filepath}")
    
    print(f"\n[SUCCESS] All {len(TEMPLATES)} test images saved to: {images_dir}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_all_templates()
    else:
        sample = "Ransomware gangs are now exploiting zero-day vulnerabilities faster than ever. Here's what changed."
        path = generate_post_image(sample)
        print(f"Generated: {path}")
