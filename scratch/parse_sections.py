import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
docs_dir = "docs"
keywords = ["fastapi", "next.js", "postgres", "pgvector", "redis", "minio", "công nghệ"]

for filename in os.listdir(docs_dir):
    if filename.endswith(".md"):
        filepath = os.path.join(docs_dir, filename)
        # Try utf-16-le first, then utf-8
        content = None
        for enc in ["utf-16-le", "utf-8", "latin-1"]:
            try:
                with open(filepath, "r", encoding=enc, errors="replace") as f:
                    content = f.read()
                # If we successfully read and it's not gibberish (i.e. if it was utf-16-le, it shouldn't be full of CJK characters unless it's actually UTF-16)
                # Let's count CJK characters to detect incorrect encoding
                cjk_count = sum(1 for c in content[:200] if ord(c) > 0x4e00 and ord(c) < 0x9fff)
                if cjk_count > 50:
                    continue  # Try next encoding
                break
            except Exception:
                pass
        
        if content:
            print(f"\n=== File: {filename} ===")
            content_lower = content.lower()
            matches = []
            for kw in keywords:
                count = content_lower.count(kw)
                if count > 0:
                    matches.append(f"'{kw}': {count} times")
            if matches:
                print(", ".join(matches))
                # Print lines containing "công nghệ" or technologies
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if any(kw in line.lower() for kw in ["công nghệ", "fastapi", "next.js", "docker", "postgres", "redis", "minio", "react flow"]):
                        if i < 150: # Limit output lines to print only early references or outline
                            print(f"  Line {i}: {line.strip()[:100]}")
