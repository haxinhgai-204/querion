import os
import sys

# Configure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

file_path = "docs/BAO_CAO_TOT_NGHIEP.md"
temp_path = "docs/BAO_CAO_TOT_NGHIEP_clean.md"

# 1. Read binary content
with open(file_path, "rb") as f:
    raw_data = f.read()

print("Original size in bytes:", len(raw_data))

# 2. Decode with utf-8, replacing bad bytes, then encode back to utf-8
decoded_content = raw_data.decode("utf-8", errors="replace")
print("Decoded size in chars:", len(decoded_content))

# Look for replacement characters to see what was replaced
replaced_count = decoded_content.count("\ufffd")
print(f"Number of invalid bytes replaced: {replaced_count}")

# 3. Write clean content as UTF-8
with open(temp_path, "w", encoding="utf-8") as f:
    f.write(decoded_content)

print("Clean file written to:", temp_path)

# Let's inspect where the replacement characters are (if any)
lines = decoded_content.split("\n")
for i, line in enumerate(lines, 1):
    if "\ufffd" in line:
        print(f"Replaced char on line {i}: {line.strip()[:100]}")

# 4. Overwrite original file
if os.path.exists(temp_path):
    if os.path.exists(file_path):
        os.remove(file_path)
    os.rename(temp_path, file_path)
    print("Successfully overwrote original file with clean UTF-8 encoding.")
