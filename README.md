# 🚀 Daily LinkedIn Post Automation

Fully automated daily LinkedIn posts on cybersecurity, threat intelligence, and SOC operations. Runs 100% in the cloud via GitHub Actions — works even when your PC is off.

---

## ⚙️ How It Works

```
2:00 PM & 5:00 PM IST  →  Fetch news  →  AI Content Scoring  →  Sense Check  →  Generate Carousel PDF/Image
                                                                               ↓
                                                                    Create GitHub Issue for review
                                                                               ↓
                                                                     Approve / Reject / Ignore
                                                                               ↓
3:00 PM & 11:11 PM IST →  Auto-post to LinkedIn (with slider document or image attachment)
```

---

## 📅 Content Sources (Rotate Automatically)

Each post is generated from one of four content sources, chosen probabilistically:

| Source | Description |
|--------|-------------|
| 📰 **RSS News** | Latest articles from Wired, TechCrunch, The Hacker News, BleepingComputer, etc. |
| 🛡️ **CVE Tracker** | Live zero-day and vulnerability intelligence from CISA |
| 🧠 **Personal Brain** | Private notes, code snippets, and architecture docs from your `knowledge/` folder |
| ✍️ **Custom Topic** | A user-defined topic passed via `--topic` flag |

---

## 🎨 Post Styles (Rotates Daily by Day of Week)

| Day | Theme |
|-----|-------|
| Monday | SOC (Security Operations Center) Operations & Analysts |
| Tuesday | VAPT (Vulnerability Assessment & Penetration Testing) |
| Wednesday | Digital Forensics & Incident Response (DFIR) |
| Thursday | Global Cyber Attacks & Threat Intelligence |
| Friday | Week in Review — Major Cybersecurity Breaches |
| Saturday | Cybersecurity Career Advice & Certifications |
| Sunday | Open Source Security Tools & Frameworks |

---

## 🖊️ Post Formats (Practitioners Vernacular)

Each post is written in one of 6 rotating formats, enhanced with **Multi-Model Sense Check** to ensure it sounds like a real practitioner:

| # | Format | Description |
|---|--------|-------------|
| 1 | 🎬 **The War Story** | Dramatic 4 AM incident response bridge call narrative |
| 2 | 🔥 **Unpopular Opinion** | Arguments that challenge common industry 'best practices' |
| 3 | 📌 **Technical Cheat Sheet** | Scannable blueprints for Senior Engineers |
| 4 | 🧪 **Technical Deep-Dive** | Dense analysis with hash types, registry keys, and `code` snippets |
| 5 | 🗳️ **Trolley Problem Poll** | Provocative architectural trade-off comparisons |
| 6 | 🧵 **Practitioner Insight** | Casual, Slack-style over-the-shoulder wisdom |

> [!TIP]
> **Sense Check**: Every post is double-checked by a separate AI model to strip out 'AI-speak', marketing fluff, and ensure natural human tone.

---

## 🖼️ Professional Image Generation (V3)

Every post automatically generates a **1200×628px LinkedIn-optimized image** using Pillow — zero external APIs needed.

### 11 Templates (6 Core + 5 SOC-Style)

| # | Template | Style |
|---|---|---|
| 1 | 🌑 **Dark Gradient** | Navy → Teal gradient, Cyan accent |
| 2 | ⚡ **Neon Split** | Cyan panel + Charcoal split |
| 3 | 📊 **Clean Grid** | Charcoal card with grid pattern |
| 4 | 💻 **Terminal** | Hacker terminal, green monospace |
| 5 | ❓ **Bold Question** | Teal gradient, large Gold "?" |
| 6 | ✨ **Minimal Pro** | Off-white, dark text, clean |
| 7 | 🚨 **SOC Alert** | Severity dashboard with live metrics |
| 8 | 📡 **Threat Radar** | Radar circles with threat dots |
| 9 | 🔴 **Incident Response** | Red gradient, NIST timeline |
| 10 | 🧩 **MITRE ATT&CK** | Framework grid background |
| 11 | 💀 **Breach Alert** | Breaking news banner, scan lines |

- **Color Palette**: Deep Teal · Electric Cyan · Amber Gold
- **Smart Text**: Headline + subtitle auto-extracted from post content
- **Test all templates**: `python scripts/generate_image.py --test`

---

## 📄 PDF Carousel Sliders (V4 Premium)

You can generate multi-page PDF documents optimized for maximum algorithmic reach on LinkedIn.

- **How to generate**: Run `python scripts/generate_post.py --carousel`
- **Logic**: Automatically splits nodes on `\n\n` into gorgeous layout slides including standard frame paginations & swipe frames.

---

## 🔔 Slack & Discord Webhooks (V4 Premium)

Get live alerts in your company messaging triggers when a post gets drafted locally:
- **Configure**: Add `SLACK_WEBHOOK_URL` or `DISCORD_WEBHOOK_URL` in GitHub Action Secrets.
- **Workflow**: Automated streams dispatch preview contents back directly to target webhook links.

---

## 🔁 Anti-Repetition System

| Feature | How It Works |
|---------|--------------|
| 📜 **Topic Memory** | Tracks previously used titles and links in `history.json` — prevents duplicate content |
| 🎭 **Technical Moods** | Randomized AI personas (battle-scarred analyst, methodical architect, etc.) for varied tone |
| 🚫 **AI-Speak Ban** | Aggressive filtering of phrases like "game-changer", "landscape", "crucial" |

---

## 🔧 Setup (One-Time)

### 1. Get API Keys

**Groq API Key** (required — free):
1. Go to [Groq Console](https://console.groq.com)
2. Create an API key
3. Save it for GitHub Secrets

**LinkedIn API** (required for auto-posting):
1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Create an app → Request `w_member_social` permission
3. Generate an access token
4. Find your Person URN: `urn:li:person:YOUR_ID`

### 2. Add GitHub Secrets

Go to: **Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|-------------|-------|
| `GROQ_API_KEY` | Your Groq API key (supports comma-separated multiple keys for rotation) |
| `LINKEDIN_ACCESS_TOKEN` | Your LinkedIn access token |
| `LINKEDIN_PERSON_URN` | `urn:li:person:YOUR_ID` |

> `GITHUB_TOKEN` is automatically available — no setup needed.

### 3. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: LinkedIn post automation"
git remote add origin https://github.com/YOUR_USERNAME/Daily-Linkedin-Post.git
git push -u origin main
```

### 4. Enable Workflows

Go to repo → **Actions** tab → Enable workflows if prompted.

---

## 📆 Daily Flow (Two Posts Per Day)

1. **2:00 PM & 5:00 PM IST** — GitHub Actions generates a post + image and creates a GitHub Issue
2. **You get an email** from GitHub with the full post content for review
3. **Optionally respond** by commenting `approve` or `reject` on the issue
4. **3:00 PM & 11:11 PM IST** — Post goes live on LinkedIn (with image), skipped if rejected
5. **Post limit**: Maximum **1 post per day** enforced automatically

---

## ▶️ Manual Trigger

Trigger any workflow manually from the **Actions** tab:
- **Generate Post**: Actions → "Generate Post & Send Confirmation" → Run workflow
- **Post to LinkedIn**: Actions → "Auto-Post to LinkedIn" → Run workflow

---

## 🧪 Local Testing

```bash
pip install -r requirements.txt

# Fetch latest news
python scripts/fetch_news.py

# Test post generation (dry run, no file saved)
export GROQ_API_KEY="your-key"
python scripts/generate_post.py --dry-run

# Generate Carousel Slider (.pdf)
python scripts/generate_post.py --dry-run --carousel

# Generate and save for a specific date
python scripts/generate_post.py --date 2026-03-03

# Generate from a custom topic
python scripts/generate_post.py --topic "Zero Trust Architecture"

# Generate from live CVE feed
python scripts/generate_post.py --cve

# Generate from Personal Brain (knowledge/ folder)
python scripts/generate_post.py --knowledge

# Test all 11 image templates
python scripts/generate_image.py --test
```

---

## 📁 Project Structure

```
Daily-Linkedin-Post/
├── .github/workflows/
│   ├── generate_post.yml     # Phase 1: Generate + notify (2 PM & 5 PM IST)
│   └── auto_post.yml         # Phase 2: Auto-post to LinkedIn (3 PM & 11:11 PM IST)
├── scripts/
│   ├── config.py             # Prompts, format styles, RSS feeds, post settings
│   ├── fetch_news.py         # RSS news fetcher (tiered feeds)
│   ├── fetch_cve.py          # Live CVE / zero-day threat intelligence fetcher
│   ├── fetch_knowledge.py    # Personal Brain reader (from knowledge/ folder)
│   ├── generate_post.py      # Groq AI post generator + sense check
│   ├── generate_image.py     # Pillow image generator (11 templates)
│   ├── post_to_linkedin.py   # LinkedIn API poster (text + image upload)
│   ├── history.py            # Topic memory / anti-repetition tracker
│   └── notify.py             # GitHub Issue confirmation system
├── knowledge/                # Your private notes, snippets, diagrams (Personal Brain)
│   └── README.md
├── posts/                    # Generated posts saved as YYYY-MM-DD-N.md
│   └── images/               # Generated post images (1200×628px)
├── requirements.txt
└── README.md
```

---

## 🧠 Personal Brain Feature

Drop any `.md`, `.txt`, or `.py` files into the `knowledge/` folder. The automation will randomly use them as post inspiration — generating authentic, behind-the-scenes content from your own notes and work.

```
knowledge/
├── architecture-notes.md
├── incident-writeup.md
└── code-snippets.py
```

---

*Built with [Groq](https://groq.com) • [Pillow](https://pillow.readthedocs.io) • [LinkedIn API](https://developer.linkedin.com) • [GitHub Actions](https://github.com/features/actions)*
