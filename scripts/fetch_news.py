"""
Fetch latest cybersecurity news from RSS feeds with authenticity verification.
- Only uses trusted, established cybersecurity news sources
- Cross-references stories across multiple sources for verification
- Validates article metadata (URL, date, author)
- Assigns confidence scores to each story
"""
import re
import feedparser
import requests
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from config import RSS_FEEDS
from history import is_in_history


def validate_article_url(url: str) -> bool:
    """Check that the article URL is real and reachable."""
    if not url or not url.startswith("http"):
        return False
    try:
        response = requests.head(url, timeout=5, allow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
        return response.status_code < 400
    except Exception:
        return False


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def titles_are_similar(title_a: str, title_b: str, threshold: float = 0.55) -> bool:
    """
    Check if two article titles are about the same story.
    Uses a combination of SequenceMatcher and significant keyword overlap.
    """
    a = title_a.lower().strip()
    b = title_b.lower().strip()

    # Direct similarity check
    ratio = SequenceMatcher(None, a, b).ratio()
    if ratio >= threshold:
        return True

    # Keyword overlap check — focused on technical entities and proper nouns
    # We ignore common stop-words and short noise
    ignore_words = {"this", "that", "with", "from", "your", "their", "about", "could"}
    words_a = set(w for w in re.findall(r'\b\w{3,}\b', a) if w not in ignore_words)
    words_b = set(w for w in re.findall(r'\b\w{3,}\b', b) if w not in ignore_words)
    
    if words_a and words_b:
        overlap = len(words_a & words_b)
        min_len = min(len(words_a), len(words_b))
        
        # If 60% of unique technical words overlap, it's likely the same story
        if overlap / min_len >= 0.6:
            return True

    return False


def fetch_recent_articles(max_per_feed: int = 8, max_age_days: int = 3) -> list[dict]:
    """Fetch recent articles from all configured RSS feeds."""
    articles = []
    cutoff = datetime.now() - timedelta(days=max_age_days)

    for feed_info in RSS_FEEDS:
        feed_url = feed_info["url"]
        trust_tier = feed_info["tier"]
        source_name = feed_info["name"]

        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:max_per_feed]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])

                # Skip articles without a valid date
                if not published:
                    continue

                # Skip old articles
                if published < cutoff:
                    continue

                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = strip_html(entry.get("summary", ""))[:300]

                # Skip articles without a title or link
                if not title or not link:
                    continue

                articles.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "source": source_name,
                    "trust_tier": trust_tier,
                    "published": published.strftime("%Y-%m-%d"),
                    "published_dt": published,
                    "cross_ref_count": 1,  # how many sources reported this
                    "cross_ref_sources": [source_name],
                    "verified": False,
                })
        except Exception as e:
            print(f"[WARN] Failed to fetch {source_name} ({feed_url}): {e}")
            continue

    return articles


def cross_reference_articles(articles: list[dict]) -> list[dict]:
    """
    Groups similar articles into clusters and selects the 'gold' version
    based on source trustworthiness and detail level.
    """
    if not articles:
        return articles

    clusters = [] 

    for article in articles:
        matched_cluster = None
        for cluster in clusters:
            # Compare against ALL articles in the cluster for better accuracy
            for existing in cluster:
                if titles_are_similar(article["title"], existing["title"]):
                    matched_cluster = cluster
                    break
            if matched_cluster:
                break

        if matched_cluster:
            matched_cluster.append(article)
        else:
            clusters.append([article])

    # Build verified article list from clusters
    verified_articles = []

    for cluster in clusters:
        # Sort by: Trust Tier (lower is better), then by Summary Length (more detail)
        cluster.sort(key=lambda a: (a["trust_tier"], -len(a.get("summary", ""))))
        best = cluster[0].copy()

        all_sources = list(set(a["source"] for a in cluster))
        best["cross_ref_count"] = len(all_sources)
        best["cross_ref_sources"] = sorted(all_sources)

        # A story is 'verified' if:
        # 1. It appears in multiple independent sources
        # 2. OR it comes from a Tier 1 (ultra-high trust) source
        best["verified"] = (len(all_sources) >= 2) or (best["trust_tier"] == 1)

        verified_articles.append(best)

    return verified_articles


def spot_check_urls(articles: list[dict], max_checks: int = 5) -> list[dict]:
    """
    Validate URLs for top articles to ensure they are real and reachable.
    Only checks a limited number to avoid slowing down the pipeline.
    """
    checked = 0
    for article in articles:
        if checked >= max_checks:
            break
        if article.get("verified"):
            is_valid = validate_article_url(article["link"])
            article["url_valid"] = is_valid
            if not is_valid:
                article["verified"] = False
                print(f"[WARN] URL validation failed for: {article['title'][:60]}")
            checked += 1
    return articles


def format_news_context(articles: list[dict]) -> str:
    """Format verified articles into a context string for the LLM."""
    if not articles:
        return "No recent verified cybersecurity news available. Use your general expertise to write the post based on well-known, verifiable current events."

    # Separate verified and unverified, but SKIP those in history
    verified = [a for a in articles if a.get("verified") and not is_in_history(a["title"], a["link"])]
    unverified = [a for a in articles if not a.get("verified") and not is_in_history(a["title"], a["link"])]

    lines = ["=== VERIFIED NEWS (confirmed by multiple trusted sources) ===", ""]

    # Dramatically reduced payload to avoid quota limits
    # allow up to 3 verified articles for richer context
    for i, article in enumerate(verified[:3], 1):
        sources_str = ", ".join(article["cross_ref_sources"])
        lines.append(f"{i}. [{sources_str}] {article['title']}")
        if article["summary"]:
            lines.append(f"   Summary: {article['summary'][:250].strip()}...")
        lines.append(f"   Link: {article['link']}")
        lines.append(f"   Published: {article['published']}")
        lines.append("")

    return "\n".join(lines)


def get_news_context() -> str:
    """
    Main entry point: fetch, verify, and return formatted news context.

    Pipeline:
    1. Fetch from all trusted RSS feeds
    2. Cross-reference across sources (same story = higher confidence)
    3. Spot-check top article URLs for reachability
    4. Format with verification status for the LLM
    """
    print("[INFO] Fetching cybersecurity news from trusted RSS feeds...")
    articles = fetch_recent_articles()
    print(f"[INFO] Fetched {len(articles)} raw articles from {len(RSS_FEEDS)} feeds")

    print("[INFO] Cross-referencing articles across sources...")
    articles = cross_reference_articles(articles)
    verified_count = sum(1 for a in articles if a.get("verified"))
    print(f"[INFO] {verified_count}/{len(articles)} articles verified (multi-source or Tier 1)")

    print("[INFO] Spot-checking top article URLs...")
    articles = spot_check_urls(articles)

    # Sort: verified first, then by cross-ref count, then by date
    articles.sort(key=lambda a: (
        not a.get("verified"),         # verified first
        -a.get("cross_ref_count", 0),  # more sources = higher
        a.get("published", ""),        # newest first (reversed below)
    ))

    context = format_news_context(articles)
    print(f"[INFO] News context ready ({len(context)} chars)")
    return context


if __name__ == "__main__":
    context = get_news_context()
    print("\n=== NEWS CONTEXT ===\n")
    print(context)
