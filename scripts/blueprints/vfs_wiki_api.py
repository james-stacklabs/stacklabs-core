from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
import os
import time
import re
import json
import math
import bisect
import sqlite3
import threading
from collections import deque

vfs_wiki_bp = APIRouter(prefix="/api/wiki", tags=["wiki"])
VFS_WIKI_ROOT = Path("/home/james/stacklabs/data/vfs_wiki")
CONCEPTS_DIR = VFS_WIKI_ROOT / "concepts"
DB_PATH = Path("/home/james/stacklabs/vfs/vfs_wiki.db")

_MONTHS_PATTERN = (
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)"
)
_TEMPORAL_OR_CONTAINER_RE = re.compile(
    rf"^(?:"
    rf"{_MONTHS_PATTERN}_\d{{1,2}}(?:_\d{{4}})?|"
    rf"\d{{1,2}}_{_MONTHS_PATTERN}(?:_\d{{4}})?|"
    rf"{_MONTHS_PATTERN}_\d{{4}}|"
    rf"\d{{3,4}}s?|"
    rf"\d{{4}}[-–]\d{{2,4}}|"
    rf"\d{{4}}_in_[a-z0-9_]+|"
    rf"list_of_[a-z0-9_]+|"
    rf"lists_of_[a-z0-9_]+|"
    rf"category:[a-z0-9_]+|"
    rf"template:[a-z0-9_]+|"
    rf"wikipedia:[a-z0-9_]+"
    rf")$"
)


def is_temporal_or_container_node(slug: str) -> bool:
    if not slug:
        return False
    return bool(_TEMPORAL_OR_CONTAINER_RE.match(slug))


def compute_adamic_adar(degree: int) -> float:
    if degree < 2:
        return 0.0
    return round(1.0 / math.log(degree), 4)


class CrawlRequest(BaseModel):
    source: str
    target: str
    filter: Optional[str] = None
    mode: str = "bridges"  # "bridges" or "path"
    dampen_super_hubs: bool = True
    max_hub_degree: int = 5000
    max_hub_ratio: float = 0.05
    min_bridge_degree: int = 2
    exclude_temporal_containers: bool = True


def slugify(title: str) -> str:
    if not title:
        return "unnamed_concept"
    s = title.strip().replace(" ", "_").lower()
    s = re.sub(r'[/\\:\*\?"<>\|\x00-\x1f]', "", s)
    return re.sub(r"_+", "_", s).strip("._")


_THREAD_LOCAL = threading.local()


def get_db_conn() -> Optional[sqlite3.Connection]:
    if not DB_PATH.is_file():
        return None
    if not hasattr(_THREAD_LOCAL, "conn") or _THREAD_LOCAL.conn is None:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        _THREAD_LOCAL.conn = conn
    return _THREAD_LOCAL.conn


_CONCEPTS_CACHE: Optional[List[str]] = None
_CONCEPTS_SET: Optional[Set[str]] = None
_SLUG_TO_ID: Dict[str, int] = {}
_ID_TO_SLUG: Dict[int, str] = {}
_DEGREE_MAP: Dict[str, int] = {}
_ADAMIC_ADAR_MAP: Dict[str, float] = {}
_OUTBOUND_LINKS_CACHE: Dict[str, Set[str]] = {}
_USE_SQLITE: bool = False
_SQLITE_CONCEPT_COUNT: int = 0


def _init_storage_plane():
    global _CONCEPTS_CACHE, _CONCEPTS_SET, _SLUG_TO_ID, _ID_TO_SLUG
    global _DEGREE_MAP, _ADAMIC_ADAR_MAP, _USE_SQLITE, _SQLITE_CONCEPT_COUNT

    merged_concepts: Set[str] = set()
    _SLUG_TO_ID.clear()
    _ID_TO_SLUG.clear()
    _DEGREE_MAP.clear()
    _ADAMIC_ADAR_MAP.clear()
    _USE_SQLITE = False
    _SQLITE_CONCEPT_COUNT = 0

    if DB_PATH.is_file():
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT id, slug, degree FROM concepts")
            rows = cursor.fetchall()
            conn.close()
            if rows:
                for cid, slug, deg in rows:
                    merged_concepts.add(slug)
                    _SLUG_TO_ID[slug] = cid
                    _ID_TO_SLUG[cid] = slug
                    d_val = deg or 0
                    _DEGREE_MAP[slug] = d_val
                    if d_val >= 2:
                        _ADAMIC_ADAR_MAP[slug] = compute_adamic_adar(d_val)
                _USE_SQLITE = True
                _SQLITE_CONCEPT_COUNT = len(rows)
        except Exception:
            pass

    if CONCEPTS_DIR.is_dir():
        try:
            for entry in os.scandir(CONCEPTS_DIR):
                if entry.is_dir():
                    merged_concepts.add(entry.name)
        except OSError:
            pass

    _CONCEPTS_CACHE = sorted(merged_concepts)
    _CONCEPTS_SET = merged_concepts


_init_storage_plane()


def invalidate_concepts_cache():
    global _CONCEPTS_CACHE, _CONCEPTS_SET, _OUTBOUND_LINKS_CACHE
    global _SLUG_TO_ID, _ID_TO_SLUG, _DEGREE_MAP, _ADAMIC_ADAR_MAP
    _CONCEPTS_CACHE = None
    _CONCEPTS_SET = None
    _SLUG_TO_ID.clear()
    _ID_TO_SLUG.clear()
    _DEGREE_MAP.clear()
    _ADAMIC_ADAR_MAP.clear()
    _OUTBOUND_LINKS_CACHE.clear()
    _init_storage_plane()


def get_concept_names() -> List[str]:
    global _CONCEPTS_CACHE
    if _CONCEPTS_CACHE is None:
        _init_storage_plane()
    return _CONCEPTS_CACHE or []


def get_concept_set() -> Set[str]:
    global _CONCEPTS_SET
    if _CONCEPTS_SET is None:
        get_concept_names()
    return _CONCEPTS_SET or set()


def get_concept_degree(slug: str) -> int:
    if slug in _DEGREE_MAP and _DEGREE_MAP[slug] > 0:
        return _DEGREE_MAP[slug]
    deg = len(get_outbound_links(slug))
    _DEGREE_MAP[slug] = deg
    if deg >= 2:
        _ADAMIC_ADAR_MAP[slug] = compute_adamic_adar(deg)
    return deg


def get_adamic_adar_score(slug: str) -> float:
    if slug in _ADAMIC_ADAR_MAP:
        return _ADAMIC_ADAR_MAP[slug]
    deg = get_concept_degree(slug)
    score = compute_adamic_adar(deg)
    _ADAMIC_ADAR_MAP[slug] = score
    return score


def compute_effective_hub_ceiling(
    max_hub_degree: int, max_hub_ratio: float, domain_size: Optional[int] = None
) -> int:
    v_size = domain_size if domain_size is not None else len(get_concept_names())
    if v_size <= 0:
        return max_hub_degree
    if max_hub_ratio <= 0.0 or max_hub_ratio >= 1.0:
        return max_hub_degree
    proportional_cap = max(10, int(v_size * max_hub_ratio))
    return min(max_hub_degree, proportional_cap)


def resolve_concept_slug(raw: str) -> Optional[str]:
    s = slugify(raw)
    if not s:
        return None
    concept_set = get_concept_set()
    if s in concept_set or (CONCEPTS_DIR / s).is_dir():
        return s
    s_apos = re.sub(r"_s(?=_|$)", "'s", s)
    if s_apos in concept_set or (CONCEPTS_DIR / s_apos).is_dir():
        return s_apos
    s_no_apos = s.replace("'", "_")
    if s_no_apos in concept_set or (CONCEPTS_DIR / s_no_apos).is_dir():
        return s_no_apos
    return None


def get_outbound_links(slug: str) -> Set[str]:
    if slug in _OUTBOUND_LINKS_CACHE:
        return _OUTBOUND_LINKS_CACHE[slug]

    links: Set[str] = set()
    if _USE_SQLITE and DB_PATH.is_file():
        src_id = _SLUG_TO_ID.get(slug)
        if src_id is not None:
            conn = get_db_conn()
            if conn:
                try:
                    cursor = conn.execute(
                        """
                        SELECT c.slug FROM edges e
                        JOIN concepts c ON e.target_id = c.id
                        WHERE e.source_id = ?
                        """,
                        (src_id,),
                    )
                    links.update(row[0] for row in cursor.fetchall())
                except Exception:
                    pass

    concept_dir = CONCEPTS_DIR / slug
    if concept_dir.is_dir():
        links_dir = concept_dir / "links"
        if links_dir.is_dir():
            try:
                for entry in os.scandir(links_dir):
                    links.add(entry.name)
            except OSError:
                pass
        try:
            for entry in os.scandir(concept_dir):
                if entry.name in ("links", "article.md", "README.md", "metadata.json"):
                    continue
                if entry.is_symlink() or entry.is_dir(follow_symlinks=False):
                    links.add(entry.name)
        except OSError:
            pass

    _OUTBOUND_LINKS_CACHE[slug] = links
    return links


def is_valid_intermediate_bridge(
    slug: str,
    src: str,
    tgt: str,
    min_bridge_degree: int,
    effective_max_hub_degree: int,
    dampen_super_hubs: bool,
    exclude_temporal_containers: bool,
) -> bool:
    if slug == src or slug == tgt:
        return True
    if exclude_temporal_containers and is_temporal_or_container_node(slug):
        return False
    deg = get_concept_degree(slug)
    if deg < min_bridge_degree:
        return False
    if dampen_super_hubs and deg > effective_max_hub_degree:
        return False
    return True


@vfs_wiki_bp.post("/cache/reload")
def reload_cache():
    invalidate_concepts_cache()
    names = get_concept_names()
    return {
        "status": "reloaded",
        "total_concepts": len(names),
        "sqlite_concepts": _SQLITE_CONCEPT_COUNT,
        "storage_mode": "hybrid_sqlite_wal_posix" if _USE_SQLITE else "filesystem_posix",
    }


@vfs_wiki_bp.api_route("/concepts", methods=["GET", "HEAD"])
def search_concepts(q: str = Query("", min_length=1), limit: int = 25):
    all_names = get_concept_names()
    if not all_names:
        return {"concepts": []}
    q_slug = slugify(q)
    if not q_slug:
        return {"concepts": []}

    start_idx = bisect.bisect_left(all_names, q_slug)
    prefix_matches = []
    for i in range(start_idx, len(all_names)):
        name = all_names[i]
        if name.startswith(q_slug):
            prefix_matches.append(name)
            if len(prefix_matches) >= limit * 2:
                break
        else:
            break

    prefix_matches.sort(key=lambda x: (len(x), x))

    if len(prefix_matches) >= limit:
        selected = prefix_matches[:limit]
    else:
        prefix_set = set(prefix_matches)
        substr_matches = []
        for name in all_names:
            if name not in prefix_set and q_slug in name:
                substr_matches.append(name)
                if len(prefix_matches) + len(substr_matches) >= limit * 3:
                    break
        substr_matches.sort(key=lambda x: (len(x), x))
        selected = (prefix_matches + substr_matches)[:limit]

    results = [{"slug": name, "title": name.replace("_", " ").title()} for name in selected]
    return {"concepts": results}


@vfs_wiki_bp.post("/swanson_crawl")
def execute_swanson_crawl(req: CrawlRequest):
    src_resolved = resolve_concept_slug(req.source)
    tgt_resolved = resolve_concept_slug(req.target)

    if not src_resolved:
        raise HTTPException(
            status_code=404, detail=f"Source concept '{slugify(req.source)}' not found in VFS."
        )
    if not tgt_resolved:
        raise HTTPException(
            status_code=404, detail=f"Target concept '{slugify(req.target)}' not found in VFS."
        )

    src = src_resolved
    tgt = tgt_resolved
    concept_set = get_concept_set()
    both_in_sqlite = (src in _SLUG_TO_ID) and (tgt in _SLUG_TO_ID)
    active_domain_size = (
        _SQLITE_CONCEPT_COUNT if (both_in_sqlite and _SQLITE_CONCEPT_COUNT > 0) else len(concept_set)
    )
    effective_max_hub = compute_effective_hub_ceiling(
        req.max_hub_degree, req.max_hub_ratio, domain_size=active_domain_size
    )

    t0 = time.perf_counter_ns()

    if req.mode == "path":
        if src == tgt:
            found_path = [src]
        else:
            q_fwd = deque([src])
            q_bwd = deque([tgt])
            parent_fwd: Dict[str, Optional[str]] = {src: None}
            parent_bwd: Dict[str, Optional[str]] = {tgt: None}
            depth_fwd: Dict[str, int] = {src: 0}
            depth_bwd: Dict[str, int] = {tgt: 0}
            found_path = None
            MAX_DEPTH = 5
            MAX_VISITED = 15000

            def build_bidirectional_path(meet_node: str) -> List[str]:
                path_left = []
                curr = meet_node
                while curr is not None:
                    path_left.append(curr)
                    curr = parent_fwd.get(curr)
                path_left.reverse()
                path_right = []
                curr = parent_bwd.get(meet_node)
                while curr is not None:
                    path_right.append(curr)
                    curr = parent_bwd.get(curr)
                return path_left + path_right

            while q_fwd and q_bwd:
                if len(parent_fwd) + len(parent_bwd) >= MAX_VISITED:
                    break
                if len(q_fwd) <= len(q_bwd):
                    curr = q_fwd.popleft()
                    curr_d = depth_fwd[curr]
                    if curr_d >= MAX_DEPTH:
                        continue
                    links = get_outbound_links(curr)
                    if tgt in links:
                        parent_fwd[tgt] = curr
                        found_path = build_bidirectional_path(tgt)
                        break
                    valid_inter = {
                        n
                        for n in (links & parent_bwd.keys())
                        if is_valid_intermediate_bridge(
                            n,
                            src,
                            tgt,
                            req.min_bridge_degree,
                            effective_max_hub,
                            req.dampen_super_hubs,
                            req.exclude_temporal_containers,
                        )
                    }
                    if valid_inter:
                        meet = min(
                            valid_inter,
                            key=lambda n: (depth_bwd.get(n, 99), get_concept_degree(n), n),
                        )
                        parent_fwd[meet] = curr
                        found_path = build_bidirectional_path(meet)
                        break
                    for link in sorted(links):
                        if link not in parent_fwd and link in concept_set:
                            if not is_valid_intermediate_bridge(
                                link,
                                src,
                                tgt,
                                req.min_bridge_degree,
                                effective_max_hub,
                                req.dampen_super_hubs,
                                req.exclude_temporal_containers,
                            ):
                                continue
                            parent_fwd[link] = curr
                            depth_fwd[link] = curr_d + 1
                            if depth_fwd[link] + 1 <= MAX_DEPTH:
                                q_fwd.append(link)
                            if len(parent_fwd) + len(parent_bwd) >= MAX_VISITED:
                                break
                else:
                    curr = q_bwd.popleft()
                    curr_d = depth_bwd[curr]
                    if curr_d >= MAX_DEPTH:
                        continue
                    links = get_outbound_links(curr)
                    if src in links:
                        parent_bwd[src] = curr
                        found_path = build_bidirectional_path(src)
                        break
                    valid_inter = {
                        n
                        for n in (links & parent_fwd.keys())
                        if is_valid_intermediate_bridge(
                            n,
                            src,
                            tgt,
                            req.min_bridge_degree,
                            effective_max_hub,
                            req.dampen_super_hubs,
                            req.exclude_temporal_containers,
                        )
                    }
                    if valid_inter:
                        meet = min(
                            valid_inter,
                            key=lambda n: (depth_fwd.get(n, 99), get_concept_degree(n), n),
                        )
                        parent_bwd[meet] = curr
                        found_path = build_bidirectional_path(meet)
                        break
                    for link in sorted(links):
                        if link not in parent_bwd and link in concept_set:
                            if not is_valid_intermediate_bridge(
                                link,
                                src,
                                tgt,
                                req.min_bridge_degree,
                                effective_max_hub,
                                req.dampen_super_hubs,
                                req.exclude_temporal_containers,
                            ):
                                continue
                            parent_bwd[link] = curr
                            depth_bwd[link] = curr_d + 1
                            if depth_bwd[link] + 1 <= MAX_DEPTH:
                                q_bwd.append(link)
                            if len(parent_fwd) + len(parent_bwd) >= MAX_VISITED:
                                break

        t1 = time.perf_counter_ns()
        latency_us = (t1 - t0) / 1000.0

        nodes_detail = []
        if found_path:
            for s in found_path:
                deg = get_concept_degree(s)
                nodes_detail.append(
                    {
                        "slug": s,
                        "title": s.replace("_", " ").title(),
                        "degree": deg,
                        "adamic_adar_score": get_adamic_adar_score(s),
                    }
                )

        return {
            "mode": "path",
            "source": src,
            "target": tgt,
            "path": found_path or [],
            "path_details": nodes_detail,
            "latency_us": round(latency_us, 3),
            "latency_ms": round(latency_us / 1000.0, 3),
            "hops": len(found_path) - 1 if found_path else -1,
            "super_hubs_dampened": req.dampen_super_hubs,
            "effective_max_hub_degree": effective_max_hub,
            "min_bridge_degree": req.min_bridge_degree,
            "temporal_containers_excluded": req.exclude_temporal_containers,
        }
    else:
        links_a = get_outbound_links(src)
        links_c = get_outbound_links(tgt)
        shared = links_a & links_c

        if req.filter:
            f_slug = slugify(req.filter)
            shared = {s for s in shared if f_slug in s}

        filtered_shared = {
            s
            for s in shared
            if is_valid_intermediate_bridge(
                s,
                src,
                tgt,
                req.min_bridge_degree,
                effective_max_hub,
                req.dampen_super_hubs,
                req.exclude_temporal_containers,
            )
        }

        t1 = time.perf_counter_ns()
        latency_us = (t1 - t0) / 1000.0

        bridges = []
        for s in filtered_shared:
            deg = get_concept_degree(s)
            aa_score = get_adamic_adar_score(s)
            bridges.append(
                {
                    "slug": s,
                    "title": s.replace("_", " ").title(),
                    "degree": deg,
                    "adamic_adar_score": aa_score,
                }
            )
        bridges.sort(key=lambda x: (-x["adamic_adar_score"], x["degree"], x["slug"]))

        return {
            "mode": "bridges",
            "ranking_algorithm": "adamic_adar_inverse_log_degree",
            "source": src,
            "target": tgt,
            "filter": req.filter,
            "total_bridges": len(bridges),
            "bridges": bridges,
            "latency_us": round(latency_us, 3),
            "latency_ms": round(latency_us / 1000.0, 3),
            "source_degree": len(links_a),
            "target_degree": len(links_c),
            "super_hubs_dampened": req.dampen_super_hubs,
            "effective_max_hub_degree": effective_max_hub,
            "min_bridge_degree": req.min_bridge_degree,
            "temporal_containers_excluded": req.exclude_temporal_containers,
        }


@vfs_wiki_bp.api_route("/crawl", methods=["GET", "HEAD"])
def execute_swanson_crawl_get(
    source: str = Query(..., min_length=1),
    target: str = Query(..., min_length=1),
    filter: Optional[str] = Query(None),
    mode: str = Query("path"),
    dampen_super_hubs: bool = Query(True),
    max_hub_degree: int = Query(5000),
    max_hub_ratio: float = Query(0.05),
    min_bridge_degree: int = Query(2),
    exclude_temporal_containers: bool = Query(True),
):
    return execute_swanson_crawl(
        CrawlRequest(
            source=source,
            target=target,
            filter=filter,
            mode=mode,
            dampen_super_hubs=dampen_super_hubs,
            max_hub_degree=max_hub_degree,
            max_hub_ratio=max_hub_ratio,
            min_bridge_degree=min_bridge_degree,
            exclude_temporal_containers=exclude_temporal_containers,
        )
    )


@vfs_wiki_bp.api_route("/concept/{slug}", methods=["GET", "HEAD"])
def get_concept_detail(slug: str):
    clean_slug = resolve_concept_slug(slug) or slugify(slug)
    title = clean_slug.replace("_", " ").title()
    article_content = ""
    metadata = {}

    conn = get_db_conn() if _USE_SQLITE else None
    if conn:
        try:
            cursor = conn.execute(
                "SELECT title, degree, article, metadata_json FROM concepts WHERE slug = ?",
                (clean_slug,),
            )
            row = cursor.fetchone()
            if row:
                title = row[0] or title
                if row[2]:
                    article_content = row[2]
                if row[3]:
                    try:
                        metadata = json.loads(row[3])
                    except Exception:
                        pass
        except Exception:
            pass

    if not article_content:
        concept_path = CONCEPTS_DIR / clean_slug
        if concept_path.is_dir():
            article_path = concept_path / "article.md"
            readme_path = concept_path / "README.md"
            if article_path.is_file():
                article_content = article_path.read_text(encoding="utf-8")
            elif readme_path.is_file():
                article_content = readme_path.read_text(encoding="utf-8")
            meta_path = concept_path / "metadata.json"
            if meta_path.is_file() and not metadata:
                try:
                    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

    if not article_content:
        article_content = f"# {title}\n\nConcept node registered in knowledge fabric."

    links = sorted(list(get_outbound_links(clean_slug)))
    deg = get_concept_degree(clean_slug)

    return {
        "slug": clean_slug,
        "title": metadata.get("title", title),
        "article": article_content,
        "metadata": metadata,
        "links": links,
        "link_count": len(links),
        "degree": deg,
        "adamic_adar_score": get_adamic_adar_score(clean_slug),
        "is_temporal_or_container": is_temporal_or_container_node(clean_slug),
    }


@vfs_wiki_bp.api_route("/stats", methods=["GET", "HEAD"])
def get_wiki_stats():
    storage_mode = (
        "hybrid_sqlite_wal_posix" if (_USE_SQLITE and DB_PATH.is_file()) else "filesystem_posix"
    )
    total_concepts = len(get_concept_names())
    cached_links = len(_OUTBOUND_LINKS_CACHE)

    cartridges = []
    if _USE_SQLITE and DB_PATH.is_file():
        conn = get_db_conn()
        if conn:
            try:
                cursor = conn.execute(
                    "SELECT name, description, node_count, edge_count, loaded_at FROM cartridges"
                )
                for row in cursor.fetchall():
                    cartridges.append(
                        {
                            "name": row[0],
                            "description": row[1],
                            "node_count": row[2],
                            "edge_count": row[3],
                            "loaded_at": row[4],
                        }
                    )
            except Exception:
                pass

    return {
        "status": "healthy",
        "storage_mode": storage_mode,
        "database_path": str(DB_PATH) if _USE_SQLITE else str(CONCEPTS_DIR),
        "total_concepts": total_concepts,
        "sqlite_concepts": _SQLITE_CONCEPT_COUNT,
        "cached_adjacency_nodes": cached_links,
        "super_hub_threshold": 5000,
        "max_hub_ratio": 0.05,
        "min_bridge_degree": 2,
        "ranking_algorithm": "adamic_adar_inverse_log_degree",
        "cartridges": cartridges,
    }
