"""
Fetch latest Known Exploited Vulnerabilities (KEV) from CISA.
This provides raw, live threat intelligence for incident response posts.
"""
import requests
from datetime import datetime
from history import is_in_history

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

def get_latest_cves(limit=5):
    """Fetch the latest CVEs added to the CISA KEV catalog."""
    try:
        response = requests.get(CISA_KEV_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        vulnerabilities = data.get("vulnerabilities", [])
        
        vulnerabilities.sort(key=lambda x: x.get("dateAdded", ""), reverse=True)
        
        # Filter out those already in history
        filtered = [v for v in vulnerabilities if not is_in_history(v.get("cveID", ""), "")]
        
        return filtered[:limit]
    except Exception as e:
        print(f"[ERROR] Failed to fetch CISA KEV catalog: {e}")
        return []

def format_cve_context(cves: list[dict]) -> str:
    """Format CVEs into a context string for the LLM."""
    if not cves:
        return "No recent CVE data available. Discuss general threat hunting principles."

    lines = ["=== LIVE THREAT INTELLIGENCE (CISA KEV CATALOG) ===", ""]
    
    for i, cve in enumerate(cves, 1):
        lines.append(f"{i}. [{cve.get('cveID', 'Unknown CVE')}] - {cve.get('vulnerabilityName', 'Unnamed Vuln')}")
        lines.append(f"   [!] Vendor: {cve.get('vendorProject', 'Unknown')}")
        lines.append(f"   [!] Product: {cve.get('product', 'Unknown')}")
        lines.append(f"   [!] Critical Impact: {cve.get('shortDescription', 'No description provided.')}")
        lines.append(f"   [>] Action Required: {cve.get('requiredAction', 'Unknown action.')}")
        lines.append(f"   [i] Date Added: {cve.get('dateAdded', 'Unknown date')}")
        
        notes = cve.get('notes')
        if notes and "http" in notes:
            lines.append(f"   [🔗] Adv: {notes}")
        else:
            lines.append(f"   [🔗] Adv: https://nvd.nist.gov/vuln/detail/{cve.get('cveID')}")
        
        lines.append("")

    return "\n".join(lines)

def get_cve_context() -> str:
    """Fetch and format the latest CVE intelligence."""
    print("[INFO] Fetching latest threat intelligence from CISA KEV...")
    cves = get_latest_cves()
    context = format_cve_context(cves)
    print(f"[INFO] CVE context ready ({len(context)} chars)")
    return context

if __name__ == "__main__":
    context = get_cve_context()
    print("\n=== CVE CONTEXT ===\n")
    print(context)
