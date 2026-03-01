"""
Script to fetch a random piece of personal knowledge from the local directory.
"""
import os
import random
from pathlib import Path

from typing import Tuple, Optional

# Maximum tokens/words to read from a single personal file so we don't blow up the Groq context window
MAX_KNOWLEDGE_CHARS = 10000 
SUPPORTED_EXTENSIONS = {'.md', '.txt', '.py'}

def fetch_random_knowledge(knowledge_dir_path: Optional[str | Path] = None) -> Optional[Tuple[str, str]]:
    """
    Scans the knowledge directory for supported text files, randomly picks one,
    and returns its content and filename.
    
    Returns:
        Tuple of (content_string, source_filename) or None if folder is empty/missing.
    """
    if not knowledge_dir_path:
        knowledge_dir_path = Path(__file__).parent.parent / "knowledge"
    else:
        knowledge_dir_path = Path(knowledge_dir_path)

    if not knowledge_dir_path.exists() or not knowledge_dir_path.is_dir():
        print(f"[WARN] Knowledge directory not found at {knowledge_dir_path}")
        return None

    # Find all supported files, excluding the README
    valid_files = []
    for file_path in knowledge_dir_path.rglob("*"):
        if file_path.is_file():
            # Skip the instructional readme
            if file_path.name.lower() == "readme.md":
                continue
            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                valid_files.append(file_path)

    if not valid_files:
        print("[WARN] No valid knowledge files found in the knowledge directory.")
        return None

    # Pick a random file
    selected_file = random.choice(valid_files)
    print(f"[INFO] Selected personal knowledge file: {selected_file.name}")

    try:
        with open(selected_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Truncate if massively long to save context window
        if len(content) > MAX_KNOWLEDGE_CHARS:
            print(f"[INFO] Truncating {selected_file.name} to first {MAX_KNOWLEDGE_CHARS} characters.")
            content = content[:MAX_KNOWLEDGE_CHARS]
            
        return content, selected_file.name
    
    except Exception as e:
        print(f"[ERROR] Failed to read knowledge file {selected_file.name}: {e}")
        return None

if __name__ == "__main__":
    result = fetch_random_knowledge()
    if result:
        content, name = result
        print(f"\n--- SUCCESS: Read {name} ---")
        print(content[:500] + "...\n(truncated for preview)")
    else:
        print("\n--- NO CONTENT FOUND ---")
