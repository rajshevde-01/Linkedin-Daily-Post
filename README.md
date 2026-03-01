# Daily LinkedIn Post Automation

Fully automated daily LinkedIn posts on cybersecurity topics. Runs in the cloud via GitHub Actions — works even when your PC is off.

## How It Works

```
2:00 PM & 5:00 PM IST  →  Fetch news (RSS) → Generate post (Groq) → Create GitHub Issue for review
                                                                            ↓
                                                                   You get an email notification
                                                                            ↓
                                                              Approve / Reject / Ignore (1-6 hours)
                                                                            ↓
3:00 PM & 11:11 PM IST →  Check response → Auto-post to LinkedIn (if approved or no response)
```

**Post style rotates daily:**
| Day | Style |
|-----|-------|
| Monday | Threat of the week + how to detect it |
| Tuesday | SOC tool tip or workflow hack |
| Wednesday | Real-world incident lesson learned |
| Thursday | Cybersecurity career advice |
| Friday | Week in review — top 3 threats |
| Saturday | Beginner-friendly security tip |
| Sunday | Motivational/mindset post |

## Setup (One-Time)

### 1. Get API Keys

**Groq API Key** (required):
1. Go to [Groq Console](https://console.groq.com)
2. Create an API key
3. Save it — you'll add it to GitHub Secrets

**LinkedIn API** (required for auto-posting):
1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com/)
2. Create an app → Request `w_member_social` permission
3. Generate an access token
4. Find your Person URN: `urn:li:person:YOUR_ID`

### 2. Add GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

| Secret Name | Value |
|-------------|-------|
| `GROQ_API_KEY` | Your Groq API key |
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

Go to repo → Actions tab → Enable workflows if prompted.

## Daily Flow (Two Posts)

1. **2:00 PM & 5:00 PM IST** — GitHub Actions runs, generates a post, creates a GitHub Issue
2. **You get an email** from GitHub with the post content
3. **You can respond** by commenting `approve` or `reject` on the issue
4. **3:00 PM & 11:11 PM IST** — If you approved or didn't respond, the post goes live on LinkedIn. If you rejected, it's skipped.

## Manual Trigger

You can manually trigger either workflow from the Actions tab:
- **Generate Post**: Actions → "Generate Post & Send Confirmation" → Run workflow
- **Post to LinkedIn**: Actions → "Auto-Post to LinkedIn" → Run workflow

## Local Testing

```bash
pip install -r requirements.txt

# Test news fetching
python scripts/fetch_news.py

# Test post generation (needs GROQ_API_KEY env var)
export GROQ_API_KEY="your-key"
python scripts/generate_post.py --dry-run

# Generate and save
python scripts/generate_post.py --date 2026-02-28

# Generate using a custom topic
python scripts/generate_post.py --topic "Zero Trust Architecture"

# Generate using latest CVEs
python scripts/generate_post.py --cve
```

## Project Structure

```
Daily-Linkedin-Post/
├── .github/workflows/
│   ├── generate_post.yml    # Phase 1: Generate + notify (5:00 PM IST)
│   └── auto_post.yml        # Phase 2: Auto-post (11:11 PM IST)
├── scripts/
│   ├── config.py            # Configuration, prompts, RSS feeds
│   ├── fetch_news.py        # RSS news fetcher
│   ├── generate_post.py     # Groq post generator
│   ├── post_to_linkedin.py  # LinkedIn API poster
│   └── notify.py            # GitHub Issue confirmation system
├── posts/                   # Generated posts (YYYY-MM-DD.md)
├── requirements.txt
└── README.md
```
