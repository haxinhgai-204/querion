import os

# Directories to exclude from the tree
exclude_dirs = {"node_modules", ".next", "dist", "build", ".git", "venv", ".venv", "__pycache__", ".pids"}
exclude_files = {"cau-truc.txt", "tree_scan.py"}

def generate_tree(dir_path, prefix=""):
    try:
        entries = os.listdir(dir_path)
    except PermissionError:
        return []
        
    # Filter out excluded items
    entries = [e for e in entries if e not in exclude_dirs and e not in exclude_files]
    
    # Sort entries: directories first, then files
    entries.sort(key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))
    
    lines = []
    for i, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        
        lines.append(f"{prefix}{connector}{entry}")
        
        if os.path.isdir(path):
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(generate_tree(path, new_prefix))
            
    return lines

# Start tree generation from the current directory
lines = ["."] + generate_tree(".")
output_file = "cau-truc.txt"

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Tree structure written successfully to {output_file}")
