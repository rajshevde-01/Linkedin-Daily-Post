# 🚀 Daily LinkedIn Post Automation

Fully automated daily LinkedIn posts on tech, cybersecurity, and leadership topics. Runs 100% in the cloud via GitHub Actions — works even when your PC is off.

---

## ⚙️ How It Works

```
2:00 PM & 5:00 PM IST  →  Fetch content → Generate post (Groq AI) → Create GitHub Issue for review
                                                                              ↓
                                                                   You get an email notification
                                                                              ↓
                                                              Approve / Reject / Ignore (1–6 hours)
                                                                              ↓
3:00 PM & 11:11 PM IST →  Check response → Auto-post to LinkedIn (if approved or no response)
```

---

## 📅 Content Sources (Rotate Automatically)

Each post is generated from one of four content sources, chosen probabilistically:

| Source | Description |
|--------|-------------|
| 📰 **RSS News** | Latest articles from Wired, TechCrunch, The Hacker News, BleepingComputer, etc. |
| 🛡️ **CVE Tracker** | Live zero-day and vulnerability intelligence |
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

## 🖊️ Post Formats (Randomly Selected Each Run)

Each post is written in one of 6 rotating formats for maximum variety:

| # | Format | Description |
|---|--------|-------------|
| 1 | 🎬 **Storytelling Narrative** | Cinematic scene-setter, short punchy paragraphs, pure story — no bullets |
| 2 | 📋 **X Things I Learned** | Numbered list (4–6 items), each with emoji + bold label + punchy explanation |
| 3 | 🔥 **Controversial Take** | Bold challenge statement, Myth vs Reality framing, dramatic single-line paragraphs |
| 4 | 📌 **Data Dump / Report** | TL;DR up top, emoji section headers (`📊 THE NUMBERS:`, `✅ THE FIX:`), stats-heavy |
| 5 | 🗳️ **Standard Bullet Format** | Bullet points, emojis on key points, ends with a comment poll |
| 6 | 🧵 **Mini Thread** | Twitter/X thread style (`1/ 2/ 3/`) condensed into a single LinkedIn post |

> **Emoji rule**: Every post uses 3–6 intentional emojis for engagement and scannability.

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

1. **2:00 PM & 5:00 PM IST** — GitHub Actions generates a post and creates a GitHub Issue
2. **You get an email** from GitHub with the full post content for review
3. **Optionally respond** by commenting `approve` or `reject` on the issue
4. **3:00 PM & 11:11 PM IST** — Post goes live on LinkedIn (if approved or no response), skipped if rejected
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

# Generate and save for a specific date
python scripts/generate_post.py --date 2026-03-03

# Generate from a custom topic
python scripts/generate_post.py --topic "Zero Trust Architecture"

# Generate from live CVE feed
python scripts/generate_post.py --cve

# Generate from Personal Brain (knowledge/ folder)
python scripts/generate_post.py --knowledge

# Enforce daily post limit
python scripts/generate_post.py --limit 1
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
│   ├── generate_post.py      # Groq AI post generator
│   ├── post_to_linkedin.py   # LinkedIn API poster
│   └── notify.py             # GitHub Issue confirmation system
├── knowledge/                # Your private notes, snippets, diagrams (Personal Brain)
│   └── README.md
├── posts/                    # Generated posts saved as YYYY-MM-DD-N.md
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

*Built with [Groq](https://groq.com) • [LinkedIn API](https://developer.linkedin.com) • [GitHub Actions](https://github.com/features/actions)*
