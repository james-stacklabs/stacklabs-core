import os
import sys

# Ensure cmdb_core can be imported from the current structure
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import cmdb_core

def seed_github_repos():
    print("[+] Initiating GitHub Repository CMDB Injection...")
    cmdb = cmdb_core.cmdb

    repos = [
        "jc2pointzero/Project-Greebles",
        "jc2pointzero/apiary",
        "jc2pointzero/apiary-sdlc-engine",
        "jc2pointzero/pizzabot",
        "jc2pointzero/greenstack-ecosystem-framework",
        "jc2pointzero/greenstack-2.0",
        "jc2pointzero/bondiBot",
        "jc2pointzero/HoloDex",
        "jc2pointzero/sam-tracker"
    ]

    for repo in repos:
        repo_name = repo.split('/')[-1]
        node_id = f"REPO-{repo_name.upper()[:8]}"
        
        cmdb.register_node(
            node_id=node_id,
            hardware=f"GitHub Repository: {repo}",
            agent_class="Code Repository (Logical CI)",
            status="ACTIVE",
            primary_directives=["Version Control", "Source of Truth", "Cloud Backup"],
            manifest_path=f"https://github.com/{repo}",
            s_value=1.0
        )
        print(f"  -> Registered: {node_id} ({repo})")

    print("\n[+] GitHub Repo Seeding Complete!")

if __name__ == "__main__":
    seed_github_repos()
