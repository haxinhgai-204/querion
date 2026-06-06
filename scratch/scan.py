import os
import re

# Regex pattern from user's request
pattern = re.compile(
    r"router|@app|@router|fetch|axios|useState|useEffect|Controller|service|workflow|dataset|chat|provider|student|workspace|auth|login", 
    re.IGNORECASE
)

# Directories to exclude
exclude_dirs = {"node_modules", ".next", "dist", ".git", ".venv", "venv", "__pycache__", ".pids"}
exclude_files = {"features-scan.txt", "scan.py"}

output_file = "features-scan.txt"

print("Starting scan...")
match_count = 0

with open(output_file, "w", encoding="utf-8") as out:
    for root, dirs, files in os.walk("."):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file in exclude_files:
                continue
                
            file_path = os.path.join(root, file)
            # Try to read file as text
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.search(line):
                            out.write(f"{file_path}:{line_num}:{line.strip()}\n")
                            match_count += 1
            except Exception as e:
                # Skip binary/unreadable files
                continue

print(f"Scan complete. Found {match_count} matches. Output written to {output_file}")
