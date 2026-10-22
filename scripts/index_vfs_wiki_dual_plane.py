#!/home/james/stacklabs/.venv/bin/python3
"""
StackLabs Dual-Plane Knowledge Fabric Compiler.
Path: /home/james/stacklabs/scripts/index_vfs_wiki_dual_plane.py
Author: James Carroll (Pilot) & Lead Systems Architect

Compiles raw POSIX concept directories and outbound links from
/home/james/stacklabs/data/vfs_wiki into a high-performance SQLite WAL
storage plane at /home/james/stacklabs/vfs/vfs_wiki.db.
Eliminates POSIX inode explosion and the 4KB page allocation tax.
"""

import os
import sys
import time
import json
import sqlite3
import argparse
import re
from pathlib import Path

DEFAULT_VFS_ROOT = Path("/home/james/stacklabs/data/vfs_wiki")
DEFAULT_DB_PATH = Path("/home/james/stacklabs/vfs/vfs_wiki.db")


def slugify(title: str) -> str:
    if not title:
        return "unnamed_concept"
    s = title.strip().replace(' ', '_').lower()
    s = re.sub(r'[/\\:\*\?"<>\|\x00-\x1f]', '', s)
    return re.sub(r'_+', '_', s).strip('._')[:120]


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = OFF;")
    conn.execute("PRAGMA cache_size = -64000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS concepts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            degree INTEGER DEFAULT 0,
            article TEXT,
            metadata_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            rel_type TEXT DEFAULT 'wikilink',
            PRIMARY KEY (source_id, target_id)
        ) WITHOUT ROWID;
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_concepts_slug ON concepts(slug);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cartridges (
            name TEXT PRIMARY KEY,
            description TEXT,
            node_count INTEGER,
            edge_count INTEGER,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
    return conn


def compile_vfs_wiki(vfs_root: Path, db_path: Path, limit: int = 0, store_articles: bool = False, batch_size: int = 10000):
    concepts_dir = vfs_root / "concepts"
    if not concepts_dir.is_dir():
        print(f"Error: Concepts directory not found at {concepts_dir}")
        sys.exit(1)

    print("====================================================================")
    print("🏛️ STACKLABS PLATFORM: DUAL-PLANE KNOWLEDGE FABRIC COMPILER")
    print("====================================================================")
    print(f"Source Directory: {concepts_dir}")
    print(f"Target Database:  {db_path}")

    t0 = time.perf_counter()
    conn = init_db(db_path)

    # Pass 1: Discover all concept directories
    print("\n[PASS 1] Discovering concept nodes and registering slugs...")
    concept_entries = []
    seen_entries = set()
    priority_seeds = [
        "metsapere", "metsalauka", "emmaste_parish", "hiiu_county",
        "estonia", "counties_of_estonia", "eastern_european_time",
        "eastern_european_summer_time"
    ]
    if limit > 0:
        for seed in priority_seeds:
            if (concepts_dir / seed).is_dir() and seed not in seen_entries:
                concept_entries.append(seed)
                seen_entries.add(seed)
    count = len(concept_entries)
    for entry in os.scandir(concepts_dir):
        if entry.is_dir() and entry.name not in seen_entries:
            concept_entries.append(entry.name)
            seen_entries.add(entry.name)
            count += 1
            if limit > 0 and count >= limit:
                break
    
    print(f"  ✔ Found {len(concept_entries):,} concept directories.")

    # Batch insert concept nodes
    concept_insert_rows = []
    for slug in concept_entries:
        title = slug.replace('_', ' ').title()
        concept_insert_rows.append((slug, title, 0, "", "{}"))

    print(f"  ✔ Inserting {len(concept_insert_rows):,} concept nodes into SQLite...")
    cursor = conn.cursor()
    for i in range(0, len(concept_insert_rows), batch_size):
        chunk = concept_insert_rows[i:i + batch_size]
        cursor.executemany("""
        INSERT INTO concepts (slug, title, degree, article, metadata_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO NOTHING;
        """, chunk)
        conn.commit()

    # Build in-memory mapping: slug -> id
    print("  ✔ Building in-memory slug-to-ID index...")
    cursor.execute("SELECT slug, id FROM concepts")
    slug_to_id = dict(cursor.fetchall())
    print(f"  ✔ Cached {len(slug_to_id):,} concept IDs in memory.")

    # Pass 2: Extract outbound links and compile edge graph
    print("\n[PASS 2] Ingesting directed outbound links...")
    edge_batch = []
    total_edges = 0
    degrees = {}
    processed_concepts = 0

    for slug in concept_entries:
        src_id = slug_to_id.get(slug)
        if src_id is None:
            continue

        concept_path = concepts_dir / slug
        links_dir = concept_path / "links"
        link_slugs = set()

        if links_dir.is_dir():
            try:
                for link_entry in os.scandir(links_dir):
                    link_slugs.add(link_entry.name)
            except OSError:
                pass

        try:
            for extra_entry in os.scandir(concept_path):
                if extra_entry.name in ("links", "article.md", "README.md", "metadata.json"):
                    continue
                if extra_entry.is_symlink() or extra_entry.is_dir(follow_symlinks=False):
                    link_slugs.add(extra_entry.name)
        except OSError:
            pass

        valid_targets = 0
        for target_slug in link_slugs:
            norm_target = slugify(target_slug)
            tgt_id = slug_to_id.get(norm_target)
            if tgt_id is not None and tgt_id != src_id:
                edge_batch.append((src_id, tgt_id, "wikilink"))
                valid_targets += 1

        degrees[src_id] = valid_targets
        processed_concepts += 1

        if len(edge_batch) >= batch_size:
            cursor.executemany("""
            INSERT OR IGNORE INTO edges (source_id, target_id, rel_type)
            VALUES (?, ?, ?)
            """, edge_batch)
            conn.commit()
            total_edges += len(edge_batch)
            edge_batch.clear()

        if processed_concepts % 25000 == 0:
            elapsed = time.perf_counter() - t0
            rate = processed_concepts / elapsed if elapsed > 0 else 0
            print(f"  ⚡ Processed {processed_concepts:,}/{len(concept_entries):,} concepts ({total_edges:,} edges) [{rate:.0f} concepts/sec]")

    if edge_batch:
        cursor.executemany("""
        INSERT OR IGNORE INTO edges (source_id, target_id, rel_type)
        VALUES (?, ?, ?)
        """, edge_batch)
        conn.commit()
        total_edges += len(edge_batch)
        edge_batch.clear()

    # Pass 3: Update node degrees
    print("\n[PASS 3] Updating node degrees...")
    degree_rows = [(deg, cid) for cid, deg in degrees.items()]
    for i in range(0, len(degree_rows), batch_size):
        chunk = degree_rows[i:i + batch_size]
        cursor.executemany("""
        UPDATE concepts SET degree = ? WHERE id = ?
        """, chunk)
        conn.commit()

    # Pass 4: Optional article text hydration
    if store_articles:
        print("\n[PASS 4] Hydrating article text...")
        article_updates = []
        for slug in concept_entries:
            cid = slug_to_id.get(slug)
            if cid is None:
                continue
            article_file = concepts_dir / slug / "article.md"
            if article_file.is_file():
                try:
                    text = article_file.read_text(encoding="utf-8", errors="replace")
                    article_updates.append((text, cid))
                except Exception:
                    pass
            if len(article_updates) >= 2000:
                cursor.executemany("UPDATE concepts SET article = ? WHERE id = ?", article_updates)
                conn.commit()
                article_updates.clear()
        if article_updates:
            cursor.executemany("UPDATE concepts SET article = ? WHERE id = ?", article_updates)
            conn.commit()

    # Register base cartridge record
    cursor.execute("""
    INSERT OR REPLACE INTO cartridges (name, description, node_count, edge_count)
    VALUES (?, ?, ?, ?)
    """, ("simplewiki_core", "Core Simple Wikipedia Inode Projection", len(concept_entries), total_edges))
    conn.commit()

    t1 = time.perf_counter()
    total_time = t1 - t0
    db_size_mb = db_path.stat().st_size / (1024 * 1024)

    print("\n====================================================================")
    print("✔ DUAL-PLANE KNOWLEDGE COMPILATION COMPLETE")
    print("====================================================================")
    print(f"Total Concepts: {len(concept_entries):,}")
    print(f"Total Edges:    {total_edges:,}")
    print(f"Database Size:  {db_size_mb:.2f} MB")
    print(f"Elapsed Time:   {total_time:.2f} seconds")
    print("====================================================================")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Compile VFS concept inodes into Dual-Plane SQLite WAL store")
    parser.add_argument("--vfs-root", type=Path, default=DEFAULT_VFS_ROOT, help="Root directory of VFS wiki")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Output SQLite database path")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of concepts for test indexing (0 = all)")
    parser.add_argument("--articles", action="store_true", help="Hydrate full article Markdown into SQLite")
    args = parser.parse_args()

    compile_vfs_wiki(
        vfs_root=args.vfs_root,
        db_path=args.db_path,
        limit=args.limit,
        store_articles=args.articles
    )


if __name__ == "__main__":
    main()
