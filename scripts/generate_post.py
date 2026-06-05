"""
Generate LinkedIn post using Google Gemini API.
"""
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import re

# Add scripts dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix console encoding for Windows to handle Unicode (e.g., premium icons)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from config import (
    GROQ_API_KEYS, 
    get_system_prompt, 
    get_image_system_prompt,
    POST_MIN_WORDS, 
    POST_MAX_WORDS,
    POST_ABSOLUTE_MIN
)
from fetch_news import get_news_context, get_raw_articles, format_news_context
from fetch_cve import get_cve_context
from fetch_knowledge import fetch_random_knowledge
from fetch_github import fetch_top_github_repo
from memory import search_memory, extract_keywords
from history import add_to_history
from generate_image import generate_post_image, generate_carousel_pdf

def _call_groq_with_retries(prompt: str, temperature: float = 0.7) -> str:
    """Robust helper to call Groq with API key rotation and model fallbacks."""
    try:
        from groq import Groq
    except ImportError:
        print("[ERROR] groq package not installed. Run: pip install groq")
        sys.exit(1)

    if not GROQ_API_KEYS:
        print("[ERROR] GROQ_API_KEY environment variable not set or invalid")
        sys.exit(1)

    import time
    max_retries = 3
    # Upgraded models to avoid 404s on deprecated ones
    models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    last_error = None
    
    for current_model in models_to_try:
        for key_idx, api_key in enumerate(GROQ_API_KEYS):
            client = Groq(api_key=api_key)
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=current_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    err_msg = str(e).lower()
                    last_error = e
                    if any(x in err_msg for x in ["429", "too many requests", "quota", "401", "invalid", "not found"]):
                        # Immediately fail this key/model combo 
                        break 
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(5)
                        else:
                            break
                            
    raise Exception(f"Exhausted all models/keys. Last error: {last_error}")


def generate_post(content: str, is_custom: bool = False, is_cve: bool = False, 
                  is_knowledge: bool = False, github_repo: dict = None, 
                  past_posts: list = None) -> str:
    """Generate a LinkedIn post using Groq API with word count enforcement."""
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        system_prompt = get_system_prompt(content, is_custom=is_custom, is_cve=is_cve, 
                                         is_knowledge=is_knowledge, github_repo=github_repo, 
                                         past_posts=past_posts)
        try:
            post_text = _call_groq_with_retries(system_prompt, temperature=0.7)
        except Exception as e:
            print(f"\n[FATAL] Post generation failed: {e}")
            sys.exit(1)
        
        word_count = len(post_text.split())
        print(f"[INFO] Attempt {attempt}/{max_attempts}: Generated {word_count} words")
        
        if word_count >= POST_ABSOLUTE_MIN:
            if word_count < POST_MIN_WORDS:
                print(f"[WARN] Post is {word_count} words (target: {POST_MIN_WORDS}-{POST_MAX_WORDS}). Slightly short but acceptable.")
            return post_text
        
        print(f"[WARN] Post is only {word_count} words (minimum: {POST_ABSOLUTE_MIN}). {'Retrying...' if attempt < max_attempts else 'Using best attempt.'}")
        
        if attempt == max_attempts:
            # On final attempt, if still too short, try to salvage
            print(f"[WARN] All {max_attempts} attempts produced short posts. Using last attempt ({word_count} words).")
            return post_text
    
    return post_text


def verify_post(post_text: str) -> str:
    """Perform a second-pass 'Sense Check' to remove AI-isms and improve flow."""
    from groq import Groq
    
    sense_check_prompt = f"""You are a brutal Executive Editor for a top-tier cybersecurity blog. You have ZERO tolerance for fluff, AI-speak, or generic content.
Review the LinkedIn post below. Your goal is to make it sound 100% like a battle-scarred human practitioner and 0% like an AI.

STRICT EDITING RULES:
1. **HOOK ENFORCEMENT**: The first line MUST be ≤8 words and wrapped in **double-asterisks**. If it's longer, rewrite it shorter and punchier. If it's missing bold markers, add them.
2. **CUT RUTHLESSLY**: Remove ANY sentence that doesn't contain a technical term, tool name, specific claim, statistic, or strong opinion. Generic filler = DELETE.
3. **FLATTEN THE TONE**: If ANY sentence sounds like a corporate marketing pitch, rewrite it to be dry, blunt, and practitioner-first. Replace "organizations should consider" with "patch it or get breached."
4. **BANNED WORD ENFORCEMENT**: Delete or rewrite any sentence containing: "Seamless", "Game-changer", "Revolutionize", "Leverage", "Crucial", "Robust", "Holistic", "Landscape", "Navigate", "Paradigm", "Cutting-edge", "State-of-the-art", "In an era", "The reality is", "It goes without saying", "Notably", "Moving forward", "Comprehensive", "Furthermore", "Essentially", "Ultimately".
5. **VARY SENTENCE LENGTH**: Ruthlessly enforce mixed lengths. Insert 3-word sentences. Break up any sentence longer than 25 words into two.
6. **NO CONCLUSION PARAGRAPHS**: Delete any concluding summary. The post must end on the CTA, a bold prediction, or a raw takeaway.
7. **PRESERVE PREMIUM DESIGN**: Do NOT remove **bolded** headers, technical terms, the `━━━━━━━━━━━━━━` separator, or premium icons (▸, ⚡, 🛡️).
8. **PRESERVE EXTRAS**: Keep hashtags and source links intact at the absolute bottom.
9. **DEPTH & LENGTH**: Ensure the post stays within **200-400 words**. If it's too short, expand the technical 'why' or add a micro-story. If it's too long, trim the least impactful sentences.

POST TO REVIEW:
{post_text}

Output ONLY the improved, finalized post text."""

    print("[INFO] Performing Hardened Sense Check (Pass 2/3)...")
    try:
        verified_text = _call_groq_with_retries(sense_check_prompt, temperature=0.4)
        print("[SUCCESS] Sense Check complete.")
        return verified_text
    except Exception as e:
        print(f"[WARN] Sense Check failed ({e}). Using original post.")
        return post_text


def final_polish(post_text: str) -> str:
    """Third pass: deduplication, compliance check, and power-closing enforcement."""
    
    polish_prompt = f"""You are a LinkedIn Algorithm Optimization Specialist. This post has already been written and edited. Your ONLY job is a final quality-assurance pass.

RULES (do NOT rewrite the post — only make surgical fixes):
1. **DEDUPLICATION**: If two paragraphs express the same idea in different words, merge them or delete the weaker one.
2. **HOOK VERIFY**: Confirm the first line is ≤8 words and **bolded**. If not, fix it.
3. **CLOSING VERIFY**: The last line before hashtags must be a bold prediction OR a polarizing question. If it's generic ("Stay safe out there"), replace it with something sharp and specific.
4. **WORD COUNT**: Count the words (excluding hashtags and source link). If under 200, add a 2-sentence practitioner anecdote. If over 400, trim the weakest paragraph.
5. **DATA CHECK**: Verify at least one concrete number/statistic/CVE exists in the body. If not, flag it by adding "[NEEDS DATA]" at the top (this will alert the pipeline).
6. **PRESERVE**: Do not change hashtags, source links, formatting markers, or separators.

POST:
{post_text}

Output ONLY the polished post text."""

    print("[INFO] Performing Final Polish (Pass 3/3)...")
    try:
        polished = _call_groq_with_retries(polish_prompt, temperature=0.3)
        print("[SUCCESS] Final Polish complete.")
        return polished
    except Exception as e:
        print(f"[WARN] Final Polish failed ({e}). Using sense-checked post.")
        return post_text


def generate_image_prompt(post_text: str) -> str:
    """Generate a high-quality DALL-E prompt based on the post content."""
    from groq import Groq
    system_prompt = get_image_system_prompt(post_text)

    print("[INFO] Generating premium Image Prompt...")
    try:
        image_prompt = _call_groq_with_retries(system_prompt, temperature=0.7)
        print("[SUCCESS] Image Prompt generated.")
        return image_prompt
    except Exception as e:
        print(f"[WARN] Image Prompt generation failed ({e}).")
        return ""


def save_post(post_text: str, image_prompt: str, date_str: str, image_path: str = "") -> str:
    """Save post and image prompt to posts/ directory and return the file path."""
    posts_dir = Path(__file__).parent.parent / "posts"
    posts_dir.mkdir(exist_ok=True)

    index = 1
    filepath = posts_dir / f"{date_str}-{index}.md"
    while filepath.exists():
        index += 1
        filepath = posts_dir / f"{date_str}-{index}.md"

    content = f"""---
date: {date_str}
status: pending
style: {get_style_for_display()}
word_count: {len(post_text.split())}
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
image_path: {image_path}
image_prompt: |
  {image_prompt}
---

{post_text}
"""
    filepath.write_text(content, encoding="utf-8")
    print(f"[INFO] Post saved to {filepath}")
    return str(filepath)


def get_style_for_display() -> str:
    """Get today's post style for metadata."""
    from config import get_today_style
    style, day = get_today_style()
    return f"{day}: {style}"


def score_articles(articles: list[dict]) -> dict:
    """Ask AI to pick the single most engaging article from the list."""
    from groq import Groq
    
    if not articles:
        return None

    # Limit to top 5 for prompt economy
    candidates = articles[:5]
    
    # Format candidates for the prompt
    options_text = ""
    for i, a in enumerate(candidates):
        options_text += f"--- INDEX {i} ---\nSource: {a.get('source')}\nTitle: {a.get('title')}\nSummary: {a.get('summary')}\n\n"

    scoring_prompt = f"""You are a LinkedIn Algorithm Expert & Chief Editor.
Review these {len(candidates)} cybersecurity news stories and pick the ONE that will generate the absolute highest engagement, comments, and shares on LinkedIn for a technical audience.

CRITERIA:
- High technical intrigue or shock value
- Relatability to practitioners (EDR, Zero Trust, AD, Cloud)
- Urgency or broad industry impact

ARTICLES:
{options_text}

Output ONLY the Index number of the winner. Do NOT say anything else. Just a single digit.
Example Response: 2"""

    print("[INFO] Asking AI to pick the most engaging topic...")
    try:
        answer = _call_groq_with_retries(scoring_prompt, temperature=0.1)
        
        # Extract first digit found
        match = re.search(r'\d', answer)
        if match:
            idx = int(match.group(0))
            if 0 <= idx < len(candidates):
                print(f"[SUCCESS] AI picked Article Index {idx}: {candidates[idx].get('title')[:60]}...")
                return candidates[idx]
        
        print("[WARN] Invalid AI choice index. Falling back to default top article.")
        return candidates[0]
    except Exception as e:
        print(f"[WARN] AI Topic Scoring failed ({e}). Falling back to top article.")
        return articles[0] if articles else None


def main():
    parser = argparse.ArgumentParser(description="Generate daily LinkedIn post")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date for the post (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print post without saving")
    parser.add_argument("--topic", default="",
                        help="Custom topic to write about (bypasses news fetching)")
    parser.add_argument("--cve", action="store_true",
                        help="Generate a threat intel post from live CVE data (bypasses news fetching)")
    parser.add_argument("--knowledge", action="store_true",
                        help="Generate a thought leadership post from a private note in the knowledge/ folder")
    parser.add_argument("--limit", type=int, default=0,
                        help="Maximum number of posts to generate per day (0 for no limit)")
    parser.add_argument("--carousel", action="store_true",
                        help="Generate a multi-page PDF Carousel slider instead of a single image")
    args = parser.parse_args()

    # Step 0: Check daily limit
    if args.limit > 0:
        posts_dir = Path(__file__).parent.parent / "posts"
        today_prefix = args.date
        existing_posts = list(posts_dir.glob(f"{today_prefix}*.md"))
        if len(existing_posts) >= args.limit:
            print(f"[WARN] Daily post limit reached ({args.limit}). Existing posts today: {len(existing_posts)}.")
            print("[WARN] Aborting generation.")
            sys.exit(0)

    # Step 1: Determine topic vs news
    is_custom = False
    is_cve = False
    is_knowledge = False
    content_to_use = ""
    used_custom_file = False
    
    custom_idea_file = Path(__file__).parent.parent / "custom_idea.txt"

    if args.topic:
        is_custom = True
        content_to_use = args.topic
        print(f"[INFO] Using custom topic from command line: {args.topic}")
    elif args.cve:
        is_cve = True
        print("[INFO] Using Live Incident Response Tracker (--cve flag)")
        content_to_use = get_cve_context()
    elif args.knowledge:
        print("[INFO] Using Personal Brain / Knowledge Base (--knowledge flag)")
        knowledge_result = fetch_random_knowledge()
        if knowledge_result:
            content_to_use, filename = knowledge_result
            is_knowledge = True
            print(f"[INFO] Successfully loaded knowledge source: {filename}")
        else:
            print("[WARN] Could not load knowledge. Falling back to news.")
            content_to_use = get_news_context()
    elif custom_idea_file.exists():
        file_content = custom_idea_file.read_text(encoding="utf-8").strip()
        if file_content:
            is_custom = True
            content_to_use = file_content
            used_custom_file = True
            print(f"[INFO] Using custom topic from custom_idea.txt")
        else:
            print("[INFO] custom_idea.txt is empty. Falling back to news.")
            content_to_use = get_news_context()
    else:
        print("[INFO] Fetching and scoring daily news...")
        raw_articles = get_raw_articles()
        if raw_articles:
            best_article = score_articles(raw_articles)
            if best_article:
                content_to_use = format_news_context([best_article])
            else:
                content_to_use = format_news_context(raw_articles)
        else:
            content_to_use = get_news_context()

    # Step 2: Fetch Semantic Context and GitHub Tools
    print("[INFO] Fetching semantic memory and tool recommendations...")
    # Extract keywords from the content to search memory and GitHub
    keywords = extract_keywords(content_to_use[:500])
    
    # Get Tool of the Day
    github_repo = None
    if keywords:
        github_repo = fetch_top_github_repo(keywords[0]) # Use the first significant keyword
        
    # Get Past Perspectives from memory
    past_posts = search_memory(keywords, top_k=3)
    
    # Step 3: Generate post
    print(f"\n[INFO] Generating {get_style_for_display()} post...")
    raw_post_text = generate_post(content_to_use, is_custom=is_custom, is_cve=is_cve, 
                                 is_knowledge=is_knowledge, github_repo=github_repo, 
                                 past_posts=past_posts)
    
    # Step 3.5: Sense Check & Image Prompt
    final_post_text = verify_post(raw_post_text)
    
    # Step 3.6: Final Polish (Pass 3/3 — dedup, compliance, power-closing)
    final_post_text = final_polish(final_post_text)
    
    image_prompt = generate_image_prompt(final_post_text)

    # Step 2.6: Log to history (extracting the main topic/link)
    try:
        # Extract title (first line) and first link found
        title_line = final_post_text.split("\n")[0][:100]
        links = re.findall(r'http\S+', final_post_text)
        first_link = links[0] if links else ""
        add_to_history(title_line, first_link)
        print(f"[INFO] Topic logged to history for anti-repetition.")
    except Exception as e:
        print(f"[WARN] Failed to log to history: {e}")

    # Step 2.7: Generate Canva-style image or Carousel PDF
    image_path = ""
    try:
        if args.carousel:
            print("[INFO] Creating PDF Carousel slider deck...")
            # Use title from first line if possible
            title_guess = final_post_text.split("\n")[0][:30].strip() or "Cyber Insight"
            image_path = generate_carousel_pdf(final_post_text, title=title_guess)
        else:
            image_path = generate_post_image(final_post_text)
            
        if image_path:
             print(f"[SUCCESS] Media deck generated: {image_path}")
    except Exception as e:
        print(f"[WARN] Media generation failed ({e}). Posting text-only.")

    if args.dry_run:
        print("\n=== GENERATED POST ===\n")
        print(final_post_text)
        print("\n=== IMAGE ===\n")
        print(f"Image saved at: {image_path}")
        return

    # Clean up the custom idea file if we successfully used it (so it doesn't repeat tomorrow)
    if used_custom_file and not args.dry_run:
        try:
            custom_idea_file.unlink()
            print("[INFO] Deleted custom_idea.txt after successful generation.")
        except Exception as e:
            print(f"[WARN] Could not delete custom_idea.txt: {e}")

    # Step 3: Save post
    filepath = save_post(final_post_text, image_prompt, args.date, image_path)

    # Step 4: Output for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"post_file={filepath}\n")
            f.write(f"image_path={image_path}\n")
            f.write(f"post_text<<EOF\n{final_post_text}\nEOF\n")

    print("\n[SUCCESS] Post generation complete!")


if __name__ == "__main__":
    main()
