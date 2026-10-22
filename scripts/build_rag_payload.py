import os
import glob

knowledge_dir = "/home/james/.gemini/antigravity/knowledge/"
output_file = "/home/james/stacklabs/dna/dropzone/daily_24042026/NOTEBOOK_LM_SOVEREIGN_MASTER_PAYLOAD_APR26.md"

with open(output_file, "w") as out:
    out.write("# SOVEREIGN OS: MASTER CONTEXT PACKAGE (RAG PAYLOAD)\n\n")
    out.write("This package contains the absolute ground-truth lore, rules, architecture, and historical context of the Sovereign Ecosystem as of April 2026. It is designed for NotebookLM ingestion.\n\n")
    
    # Find all overview.md files in the knowledge items
    for overview_file in glob.glob(os.path.join(knowledge_dir, "*", "artifacts", "overview.md")):
        with open(overview_file, "r") as f:
            content = f.read()
            out.write("================================================================================\n")
            out.write(f"--- FILE: {os.path.basename(os.path.dirname(os.path.dirname(overview_file)))} ---\n")
            out.write("================================================================================\n\n")
            out.write(content)
            out.write("\n\n")
    
    # Also include the architecture markdown files
    for arch_file in glob.glob(os.path.join(knowledge_dir, "sovereign_master_knowledge", "artifacts", "*", "*.md")):
        with open(arch_file, "r") as f:
            content = f.read()
            out.write("================================================================================\n")
            out.write(f"--- FILE: {os.path.basename(arch_file)} ---\n")
            out.write("================================================================================\n\n")
            out.write(content)
            out.write("\n\n")

print(f"Payload successfully written to {output_file}")
