#!/usr/bin/env python3
"""
scripts/core/hoist_inline_imports.py
=============================================================================
SOVEREIGN OS: AST INLINE IMPORT HOISTER & COMPILER GUARDIAN
=============================================================================
Detects scoped inline imports inside functions/methods and safely hoists
them to module-level headers. Validates each modification with py_compile.
=============================================================================
"""

import sys
import ast
import py_compile
from pathlib import Path
from typing import List, Tuple, Set

SAFE_MODULES = {
    "os", "sys", "json", "time", "datetime", "re", "math", "random",
    "uuid", "base64", "urllib", "urllib.parse", "subprocess", "pathlib",
    "Path", "typing", "logging", "shutil", "hashlib", "sqlite3", "tempfile",
    "copy", "glob", "traceback", "io", "dotenv", "load_dotenv", "fastapi",
    "HTTPException", "APIRouter", "httpx", "requests", "pydantic", "yaml"
}

def is_safe_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(alias.name.split('.')[0] in SAFE_MODULES for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        mod = (node.module or "").split('.')[0]
        return mod in SAFE_MODULES or any(alias.name in SAFE_MODULES for alias in node.names)
    return False

def hoist_imports_in_file(file_path: Path) -> Tuple[bool, int, str]:
    """Hoists safe inline imports to top of file. Returns (success, count, msg)."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        return False, 0, f"Parse error: {e}"

    lines = content.splitlines()
    
    # Collect inline import nodes
    inline_nodes: List[ast.AST] = []
    
    class ScopeVisitor(ast.NodeVisitor):
        def __init__(self):
            self.depth = 0
            
        def visit_FunctionDef(self, node):
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1
            
        def visit_AsyncFunctionDef(self, node):
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1
            
        def visit_Import(self, node):
            if self.depth > 0 and is_safe_import(node):
                inline_nodes.append(node)
            self.generic_visit(node)
            
        def visit_ImportFrom(self, node):
            if self.depth > 0 and is_safe_import(node):
                inline_nodes.append(node)
            self.generic_visit(node)

    visitor = ScopeVisitor()
    visitor.visit(tree)

    if not inline_nodes:
        return True, 0, "No safe inline imports to hoist"

    # Sort nodes by line number ascending
    inline_nodes.sort(key=lambda n: n.lineno)

    hoisted_statements: Set[str] = set()
    lines_to_comment: Set[int] = set()

    for node in inline_nodes:
        # Extract source text for import
        start_line = node.lineno - 1
        end_line = getattr(node, 'end_lineno', node.lineno) - 1
        
        stmt_lines = lines[start_line:end_line + 1]
        stmt_text = " ".join(l.strip() for l in stmt_lines)
        
        hoisted_statements.add(stmt_text)
        for ln in range(start_line, end_line + 1):
            lines_to_comment.add(ln)

    # Find insertion point at top of file (after shebang / module docstring)
    insertion_idx = 0
    if lines and lines[0].startswith("#!"):
        insertion_idx = 1

    # Check for module docstring
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        doc_node = tree.body[0]
        end_doc_line = getattr(doc_node, 'end_lineno', doc_node.lineno)
        insertion_idx = max(insertion_idx, end_doc_line)

    # Prepare new lines
    new_lines = []
    
    # 1. Header lines up to insertion point
    new_lines.extend(lines[:insertion_idx])
    
    # 2. Insert hoisted statements
    new_lines.append("")
    new_lines.append("# --- Hoisted Module-Level Imports (Sovereign AST Hygiene) ---")
    for stmt in sorted(hoisted_statements):
        new_lines.append(stmt)
    new_lines.append("# -------------------------------------------------------------")
    new_lines.append("")

    # 3. Rest of lines with inline imports commented out
    for idx, line in enumerate(lines[insertion_idx:], start=insertion_idx):
        if idx in lines_to_comment:
            # Preserve indentation
            indent = len(line) - len(line.lstrip())
            new_lines.append(" " * indent + f"# [Hoisted to header] {line.strip()}")
        else:
            new_lines.append(line)

    new_content = "\n".join(new_lines) + "\n"

    # Write and test compilation
    file_path.write_text(new_content, encoding="utf-8")
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True, len(inline_nodes), f"Hoisted {len(inline_nodes)} inline import(s)"
    except Exception as e:
        # Rollback immediately on failure
        file_path.write_text(content, encoding="utf-8")
        return False, 0, f"Rollback due to compile error: {e}"

def main():
    repo_root = Path(__file__).resolve().parents[2]
    scripts_dir = repo_root / "scripts"
    
    targets = [
        scripts_dir / "sdlc_portal_server.py",
        scripts_dir / "fanstack_relay.py",
        scripts_dir / "the_skew_relay.py",
        scripts_dir / "fanstack_chatbots.py",
        scripts_dir / "the_skew_chatbots.py",
        scripts_dir / "sam_tracker_server.py",
        scripts_dir / "stack_seeder_cli.py",
        scripts_dir / "routers" / "brand.py",
        scripts_dir / "routers" / "system_ops.py",
        scripts_dir / "routers" / "entertainment.py",
        scripts_dir / "routers" / "legal.py",
        scripts_dir / "routers" / "media.py",
    ]

    total_hoisted = 0
    success_files = 0

    print("[*] Starting AST Inline Import Hoisting on Core Scripts...")
    for target in targets:
        if not target.is_file():
            continue
        ok, count, msg = hoist_imports_in_file(target)
        if ok and count > 0:
            print(f"[OK] {target.name}: {msg}")
            total_hoisted += count
            success_files += 1
        elif not ok:
            print(f"[WARN] {target.name}: {msg}")
        else:
            print(f"[SKIP] {target.name}: {msg}")

    print(f"\n[DONE] Hoisted {total_hoisted} inline imports across {success_files} files.")

if __name__ == "__main__":
    main()
