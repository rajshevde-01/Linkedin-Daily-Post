import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from fpdf import FPDF

# Paths
ROOT_DIR = Path(__file__).parent.parent
HISTORY_FILE = ROOT_DIR / "history.json"
OUTPUT_DIR = ROOT_DIR
POSTS_DIR = ROOT_DIR / "posts"

class WeeklyDigestPDF(FPDF):
    def header(self):
        # Premium header with dark border and title
        self.set_font("helvetica", "B", 18)
        self.set_text_color(0, 81, 99) # Teal-ish
        self.cell(0, 10, "📬 CYBERSECURITY WEEKLY DIGEST", ln=True, align="C")
        self.set_font("helvetica", "I", 10)
        self.set_text_color(100, 100, 100)
        today = datetime.now().strftime("%B %d, %Y")
        self.cell(0, 10, f"Generated on {today}", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_weekly_pdf():
    if not HISTORY_FILE.exists():
        print("[ERROR] history.json not found")
        return

    with open(HISTORY_FILE, "r") as f:
        history = json.load(f)

    posts = history.get("posts", [])
    if not posts:
        print("[INFO] No posts in history to generate digest.")
        return

    # Filter posts from the last 7 days
    cutoff = datetime.now() - timedelta(days=7)
    recent_posts = [
        p for p in posts
        if datetime.strptime(p["posted_at"], "%Y-%m-%d %H:%M:%S") >= cutoff
    ]

    # Sort by engagement
    recent_posts.sort(
        key=lambda x: (x.get("metrics", {}).get("likes", 0) + x.get("metrics", {}).get("comments", 0)),
        reverse=True
    )

    top_posts = recent_posts[:5]

    # Initialize PDF
    pdf = WeeklyDigestPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Overview
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Weekly Overview: {len(recent_posts)} Posts Generated", ln=True)
    pdf.ln(5)

    for i, post in enumerate(top_posts, 1):
        # Post Header
        pdf.set_font("helvetica", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        engagement = post.get("metrics", {}).get("likes", 0) + post.get("metrics", {}).get("comments", 0)
        pdf.cell(0, 10, f"#{i}: {post['title'].replace('**', '').upper()}", ln=True, fill=True)
        
        # Stats
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 8, f"Engagement: {engagement} (👍 {post.get('metrics', {}).get('likes', 0)} / 💬 {post.get('metrics', {}).get('comments', 0)})", ln=True)
        pdf.set_text_color(0, 0, 0)
        
        # Content Preview or Full Content (if MD exists)
        date_str = post["posted_at"][:10]
        # Find the file in posts/
        md_file = None
        for f in POSTS_DIR.glob(f"{date_str}-*.md"):
            md_file = f
            break
            
        if md_file and md_file.exists():
            content = md_file.read_text(encoding="utf-8")
            # Basic cleanup of MD artifacts
            content = content.replace("---", "").strip()
            # Just take first 500 chars for digest
            pdf.set_font("helvetica", "", 9)
            pdf.multi_cell(0, 5, content[:600] + "...")
        else:
            pdf.set_font("helvetica", "I", 9)
            pdf.multi_cell(0, 5, f"Summary: {post.get('content_preview', 'No content available.')}")

        pdf.ln(10)

    # Save PDF
    output_path = OUTPUT_DIR / f"Weekly_Digest_{datetime.now().strftime('%Y%V')}.pdf"
    pdf.output(str(output_path))
    print(f"[SUCCESS] Weekly Digest PDF generated: {output_path.name}")

if __name__ == "__main__":
    generate_weekly_pdf()
