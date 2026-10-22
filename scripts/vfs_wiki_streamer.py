#!/home/james/stacklabs/.venv/bin/python3
"""
scripts/vfs_wiki_streamer.py
============================
Streaming Wikipedia Ingestion Engine & POSIX Inode Projector.
Governed by: Monograph 12 (Latency-Inverted Knowledge Fabric),
Invariant 1 (Small Ball Metal), and Invariant 15 (Two-Call Verification).

Author: James Carroll (Pilot), Lead Systems Architect, StackLabs LLC
"""

import os
import sys
import re
import bz2
import json
import time
import shutil
import urllib.request
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

DEFAULT_DUMP_URL = "https://dumps.wikimedia.org/simplewiki/latest/simplewiki-latest-pages-articles.xml.bz2"
DEFAULT_OUTPUT_DIR = Path("/home/james/stacklabs/data/vfs_wiki")

RE_WIKILINK = re.compile(r'\[\[([^\|\]\n]+)(?:\|[^\]\n]*)?\]\]')
RE_CATEGORY = re.compile(r'\[\[Category:([^\|\]\n]+)(?:\|[^\]\n]*)?\]\]', re.IGNORECASE)
RE_REDIRECT = re.compile(r'#(?:REDIRECT)\s*\[\[([^\]]+)\]\]', re.IGNORECASE)
RE_CLEAN_TEMPLATES = re.compile(r'\{\{[^}]*\}\}')
RE_CLEAN_COMMENTS = re.compile(r'<!--.*?-->', re.DOTALL)
RE_CLEAN_REFS = re.compile(r'<ref[^>]*>.*?</ref>|<ref[^/>]*/>', re.DOTALL | re.IGNORECASE)
RE_CLEAN_TAGS = re.compile(r'<[^>]+>')

def slugify(title: str) -> str:
    """Normalize Wikipedia title into deterministic filesystem slug."""
    if not title:
        return "unnamed_concept"
    s = title.strip().replace(' ', '_').lower()
    # Remove filesystem-hazardous characters
    s = re.sub(r'[/\\:\*\?"<>\|\x00-\x1f]', '', s)
    # Collapse consecutive underscores
    s = re.sub(r'_+', '_', s).strip('._')
    return s[:120] if s else "unnamed_concept"

def clean_wikitext_to_markdown(raw_text: str) -> str:
    """Strip heavy wikitext markup down to readable Markdown prose."""
    if not raw_text:
        return ""
    text = RE_CLEAN_COMMENTS.sub('', raw_text)
    text = RE_CLEAN_REFS.sub('', text)
    text = RE_CLEAN_TEMPLATES.sub('', text)
    text = RE_CLEAN_TAGS.sub('', text)
    # Convert bold / italics
    text = re.sub(r"'''(.*?)'''", r'**\1**', text)
    text = re.sub(r"''(.*?)''", r'*\1*', text)
    # Simplify wikilinks in prose: [[Target|Anchor]] -> Anchor, [[Target]] -> Target
    text = re.sub(r'\[\[(?:[^\|\]\n]+\|)?([^\]\n]+)\]\]', r'\1', text)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def decompress_stream(stream_obj, chunk_size: int = 256 * 1024):
    """
    Robust decompressor handling multi-stream concatenated bz2 (pbzip2).
    Yields decompressed byte slices incrementally.
    """
    decompressor = bz2.BZ2Decompressor()
    while True:
        chunk = stream_obj.read(chunk_size)
        if not chunk:
            break
        while chunk:
            try:
                decompressed_data = decompressor.decompress(chunk)
                if decompressed_data:
                    yield decompressed_data
                if decompressor.eof:
                    chunk = decompressor.unused_data
                    decompressor = bz2.BZ2Decompressor()
                else:
                    break
            except EOFError:
                chunk = decompressor.unused_data + chunk
                decompressor = bz2.BZ2Decompressor()

class WikipediaVFSStreamer:
    def __init__(self, output_dir: Path, limit: int = 0):
        self.output_dir = output_dir
        self.concepts_dir = output_dir / "concepts"
        self.categories_dir = output_dir / "categories"
        self.redirects_dir = output_dir / "redirects"
        self.limit = limit  # If limit <= 0, process entire dump without stopping
        self._created_categories = set()
        
        self.stats = {
            "articles_processed": 0,
            "redirects_processed": 0,
            "symlinks_created": 0,
            "categories_linked": 0,
            "start_time": 0.0,
            "elapsed_sec": 0.0,
        }

    def init_layout(self):
        """Create pristine directory topology."""
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.categories_dir.mkdir(parents=True, exist_ok=True)
        self.redirects_dir.mkdir(parents=True, exist_ok=True)

    def process_page(self, title: str, page_id: str, text: str, is_redirect: bool, redirect_target: str = None):
        if not title:
            return

        source_slug = slugify(title)
        if not source_slug or source_slug == "unnamed_concept":
            return

        # Case 1: Redirect -> atomic symlink
        if is_redirect and redirect_target:
            target_slug = slugify(redirect_target)
            if not target_slug or target_slug == "unnamed_concept":
                return
            redirect_path = self.redirects_dir / source_slug
            if redirect_path.is_symlink() or redirect_path.exists():
                try:
                    redirect_path.unlink()
                except OSError:
                    pass
            try:
                # relative link: ../concepts/<target_slug>
                os.symlink(f"../concepts/{target_slug}", redirect_path)
                self.stats["redirects_processed"] += 1
            except OSError:
                pass
            return

        # Case 2: Full concept article
        concept_dir = self.concepts_dir / source_slug
        links_dir = concept_dir / "links"
        concept_dir.mkdir(exist_ok=True)
        links_dir.mkdir(exist_ok=True)

        # Extract categories
        categories = [c.strip() for c in RE_CATEGORY.findall(text) if c.strip()]
        
        # Extract directed Wikilinks (excluding Category: and File: links)
        raw_links = RE_WIKILINK.findall(text)
        valid_targets = set()
        for raw in raw_links:
            clean_target = raw.strip()
            if clean_target and not clean_target.startswith(('Category:', 'File:', 'Image:', 'Template:', 'Help:', 'Wikipedia:')):
                t_slug = slugify(clean_target)
                if t_slug and t_slug != "unnamed_concept" and t_slug != source_slug:
                    valid_targets.add(t_slug)

        # Write clean article markdown
        clean_prose = clean_wikitext_to_markdown(text)
        article_file = concept_dir / "article.md"
        with open(article_file, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{clean_prose}\n")

        # Write metadata JSON
        meta = {
            "title": title,
            "page_id": page_id,
            "slug": source_slug,
            "categories": categories,
            "link_count": len(valid_targets)
        }
        with open(concept_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Create relative symlinks for directed edges
        # Inode path: concepts/<source>/links/<target> -> ../../concepts/<target>
        for t_slug in valid_targets:
            link_path = links_dir / t_slug
            try:
                os.symlink(f"../../concepts/{t_slug}", link_path)
                self.stats["symlinks_created"] += 1
            except FileExistsError:
                pass
            except OSError:
                pass

        # Link categories
        for cat in categories:
            cat_slug = slugify(cat)
            if not cat_slug or cat_slug == "unnamed_concept":
                continue
            cat_dir = self.categories_dir / cat_slug / "members"
            if cat_slug not in self._created_categories:
                cat_dir.mkdir(parents=True, exist_ok=True)
                self._created_categories.add(cat_slug)
            cat_member_link = cat_dir / source_slug
            try:
                os.symlink(f"../../../concepts/{source_slug}", cat_member_link)
                self.stats["categories_linked"] += 1
            except FileExistsError:
                pass
            except OSError:
                pass

        self.stats["articles_processed"] += 1

    def stream_from_file_or_url(self, source_path_or_url: str):
        self.init_layout()
        self.stats["start_time"] = time.time()
        
        limit_desc = f"{self.limit:,} articles" if self.limit > 0 else "Unlimited (Full SimpleWiki Corpus)"
        print(f"🚀 [VFS WIKI STREAMER] Streaming from: {source_path_or_url}")
        print(f"🎯 Target Directory: {self.output_dir}")
        print(f"⚡ Ingestion Limit: {limit_desc}\n")

        is_url = source_path_or_url.startswith(("http://", "https://"))
        
        if is_url:
            req = urllib.request.Request(
                source_path_or_url,
                headers={"User-Agent": "StackLabs-VFS-Research/1.0 (james@stacklabsllc.com)"}
            )
            response = urllib.request.urlopen(req, timeout=30)
            stream_obj = response
        else:
            stream_obj = open(source_path_or_url, "rb")

        try:
            # Incremental XML parser setup
            parser = ET.XMLPullParser(events=("start", "end"))
            
            title = ""
            page_id = ""
            ns = ""
            text = ""
            is_redirect = False
            redirect_title = None

            last_log = time.time()
            data_generator = decompress_stream(stream_obj)

            for decompressed_data in data_generator:
                parser.feed(decompressed_data)

                for event, elem in parser.read_events():
                    tag = elem.tag.split('}')[-1] # strip XML namespace

                    if event == "start":
                        if tag == "page":
                            title, page_id, ns, text = "", "", "", ""
                            is_redirect = False
                            redirect_title = None
                        elif tag == "redirect":
                            is_redirect = True
                            redirect_title = elem.get("title")

                    elif event == "end":
                        if tag == "title":
                            title = elem.text or ""
                        elif tag == "id" and not page_id: # first id in page
                            page_id = elem.text or ""
                        elif tag == "ns":
                            ns = elem.text or ""
                        elif tag == "text":
                            text = elem.text or ""
                        elif tag == "page":
                            # Only process main articles (ns == 0)
                            if ns == "0":
                                # Also check if text has redirect markup
                                if not is_redirect and text:
                                    red_m = RE_REDIRECT.search(text[:200])
                                    if red_m:
                                        is_redirect = True
                                        redirect_title = red_m.group(1)

                                self.process_page(title, page_id, text, is_redirect, redirect_title)

                                if (self.stats["articles_processed"] % 10000 == 0) or (time.time() - last_log > 5.0):
                                    elapsed = time.time() - self.stats["start_time"]
                                    rate = self.stats["articles_processed"] / elapsed if elapsed > 0 else 0
                                    print(f"  ⚡ Ingested: {self.stats['articles_processed']:,} articles | "
                                          f"Symlinks: {self.stats['symlinks_created']:,} | "
                                          f"Categories: {self.stats['categories_linked']:,} | "
                                          f"Rate: {rate:.1f} art/sec | "
                                          f"Elapsed: {elapsed:.1f}s")
                                    last_log = time.time()

                            elem.clear() # Free XML memory immediately

                    if self.limit > 0 and self.stats["articles_processed"] >= self.limit:
                        break

                if self.limit > 0 and self.stats["articles_processed"] >= self.limit:
                    break

        finally:
            stream_obj.close()
            self.stats["elapsed_sec"] = time.time() - self.stats["start_time"]

        print(f"\n✔ [INGESTION COMPLETE] {self.stats['articles_processed']:,} articles ingested in {self.stats['elapsed_sec']:.2f}s.")
        print(f"  • Redirects: {self.stats['redirects_processed']:,}")
        print(f"  • Symlinks Created: {self.stats['symlinks_created']:,}")
        print(f"  • Categories Linked: {self.stats['categories_linked']:,}")
        return self.stats

def main():
    parser = argparse.ArgumentParser(description="StackLabs Wikipedia VFS Streaming Ingestion Engine")
    parser.add_argument("--source", default=DEFAULT_DUMP_URL, help="Dump URL or local bz2 filepath")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Output root directory")
    parser.add_argument("--limit", type=int, default=0, help="Max articles to ingest (0 = unlimited)")
    args = parser.parse_args()

    streamer = WikipediaVFSStreamer(Path(args.output), limit=args.limit)
    streamer.stream_from_file_or_url(args.source)

if __name__ == "__main__":
    main()
