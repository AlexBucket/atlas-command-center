"""Obsidian vault intelligence — stats, tags, graph, timeline."""

import os
import re
import json
from datetime import datetime, date
from collections import Counter, defaultdict

VAULT_PATH = os.environ.get("VAULT_PATH", "/vault")


def _find_md_files(root: str) -> list[str]:
    """Recursively find all .md files in the vault."""
    files = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith(".md"):
                files.append(os.path.join(dirpath, f))
    return sorted(files)


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter between --- markers."""
    fm = {}
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            block = content[3:end].strip()
            for line in block.split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if val.startswith("[") and val.endswith("]"):
                        val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
                    fm[key] = val
    return fm


def _extract_wikilinks(content: str) -> list[str]:
    """Extract [[Note Name]] or [[Folder/Note Name]] links."""
    links = re.findall(r'\[\[([^\]]+)\]\]', content)
    # Strip display text: [[Note|Display]] → Note
    return [l.split("|")[0].split("#")[0].strip() for l in links]


def _extract_tags(content: str, frontmatter: dict) -> list[str]:
    """Extract tags from frontmatter and inline #tags."""
    tags = set()
    # Frontmatter tags
    fm_tags = frontmatter.get("tags", [])
    if isinstance(fm_tags, str):
        fm_tags = [fm_tags]
    for t in fm_tags:
        tags.add(t.strip().lower())
    # Inline #tags (not in code blocks)
    for m in re.finditer(r'(?<!\w)#([a-zA-Z][a-zA-Z0-9_/-]+)', content):
        tags.add(m.group(1).lower())
    return sorted(tags)


def _read_file(path: str) -> tuple[str, dict]:
    """Read a file and return (content, frontmatter)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        fm = _parse_frontmatter(content)
        return content, fm
    except Exception as e:
        return "", {"error": str(e)}


def _relative_path(path: str, root: str) -> str:
    """Get relative path from vault root."""
    return os.path.relpath(path, root).replace("\\", "/")


def _get_file_times(path: str) -> dict:
    """Get file creation and modification times."""
    stat = os.stat(path)
    return {
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "size": stat.st_size,
    }


# ── Public API ────────────────────────────────────────────────


def get_stats() -> dict:
    """Get overall vault statistics."""
    if not os.path.isdir(VAULT_PATH):
        return {"error": f"Vault not found at {VAULT_PATH}"}

    files = _find_md_files(VAULT_PATH)
    total_notes = len(files)
    total_words = 0
    total_links = 0
    all_tags = Counter()
    all_links = []
    recent = []
    monthly = defaultdict(int)

    for fp in files:
        content, fm = _read_file(fp)
        words = len(content.split())
        total_words += words

        links = _extract_wikilinks(content)
        total_links += len(links)
        all_links.extend(links)

        tags = _extract_tags(content, fm)
        for t in tags:
            all_tags[t] += 1

        rel = _relative_path(fp, VAULT_PATH)
        times = _get_file_times(fp)

        # Track monthly counts
        mod_month = times["modified"][:7]
        monthly[mod_month] += 1

        recent.append({
            "path": rel,
            "title": fm.get("title", os.path.splitext(os.path.basename(fp))[0]),
            "words": words,
            "links": len(links),
            "tags": tags,
            "created": times["created"],
            "modified": times["modified"],
        })

    # Sort recent by modified time
    recent.sort(key=lambda x: x["modified"], reverse=True)

    # Build tag cloud
    tag_cloud = [{"tag": t, "count": c} for t, c in all_tags.most_common(50)]

    # Build monthly timeline
    timeline = [{"month": m, "count": c} for m, c in sorted(monthly.items())]

    return {
        "total_notes": total_notes,
        "total_words": total_words,
        "total_links": total_links,
        "avg_words": round(total_words / max(total_notes, 1)),
        "tag_cloud": tag_cloud,
        "monthly_timeline": timeline,
        "recent_notes": recent[:20],
    }


def get_graph() -> dict:
    """Build a force-directed graph of note connections."""
    if not os.path.isdir(VAULT_PATH):
        return {"error": f"Vault not found at {VAULT_PATH}"}

    files = _find_md_files(VAULT_PATH)
    nodes = []
    edges = []
    node_map = {}  # title → index

    # First pass: create nodes
    for fp in files:
        content, fm = _read_file(fp)
        rel = _relative_path(fp, VAULT_PATH)
        title = fm.get("title", os.path.splitext(os.path.basename(fp))[0])
        name = os.path.splitext(os.path.basename(fp))[0]
        folder = os.path.dirname(rel)

        # Use the note name (without extension) as the key for matching wikilinks
        key = name
        node_map[key] = len(nodes)
        nodes.append({
            "id": len(nodes),
            "label": title,
            "title": rel,
            "group": folder.split("/")[0] if folder else "root",
            "size": min(30, max(10, len(content) // 500)),
        })

    # Second pass: create edges from wikilinks
    for fp in files:
        content, _ = _read_file(fp)
        links = _extract_wikilinks(content)
        name = os.path.splitext(os.path.basename(fp))[0]
        source_idx = node_map.get(name)

        if source_idx is None:
            continue

        seen = set()
        for target in links:
            if target in node_map and target not in seen:
                edges.append({
                    "from": source_idx,
                    "to": node_map[target],
                })
                seen.add(target)

    return {
        "nodes": nodes,
        "edges": edges,
        "total_notes": len(nodes),
        "total_connections": len(edges),
    }


def get_tags() -> dict:
    """Get tag cloud data."""
    stats = get_stats()
    if "error" in stats:
        return stats
    return {"tag_cloud": stats.get("tag_cloud", [])}


def get_timeline() -> dict:
    """Get monthly note creation timeline."""
    stats = get_stats()
    if "error" in stats:
        return stats
    return {"timeline": stats.get("monthly_timeline", [])}


def get_recent() -> dict:
    """Get recently modified notes."""
    stats = get_stats()
    if "error" in stats:
        return stats
    return {"notes": stats.get("recent_notes", [])}


def get_note(path: str) -> dict:
    """Get a specific note by path."""
    full_path = os.path.join(VAULT_PATH, path)
    if not os.path.exists(full_path) or not full_path.endswith(".md"):
        return {"error": "Note not found"}
    content, fm = _read_file(full_path)
    return {
        "path": path,
        "title": fm.get("title", os.path.splitext(os.path.basename(path))[0]),
        "content": content,
        "frontmatter": fm,
        "links": _extract_wikilinks(content),
        "tags": _extract_tags(content, fm),
        "times": _get_file_times(full_path),
    }