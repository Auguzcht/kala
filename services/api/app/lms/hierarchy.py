"""Generic folder/module hierarchy resolution over an LMS content tree.

Deliberately LMS-agnostic and institution-agnostic: it only assumes every
content item has ``lms_content_id`` and ``parent_id`` (already true of
LMSConnector.get_content()'s contract, see lms/base.py). It does not assume
any particular nesting depth or naming convention ("Module N", "Week N",
a flat course with no folders at all, whatever a given institution actually
uses in Blackboard). This is what lets the same ingest pipeline serve MMCM's
module-per-course convention and any other Cintana school's own structure
without a code change, only the data shape differs.

folder_path is the full ancestor chain, root to immediate parent, as
[{"lmsRef": ..., "title": ...}, ...]. Top-level content (no ancestors) gets
an empty list. module_ref is a convenience default, the top-level ancestor's
title, since "the first folder level is the course's organizing unit" holds
for MMCM's Blackboard courses and is a reasonable default elsewhere too, but
callers that need a different depth (e.g. a school that organizes by week
under module) should use the full folder_path instead of module_ref.
"""
from __future__ import annotations


def build_folder_paths(content_items: list[dict]) -> dict[str, list[dict]]:
    """Map every content item's lms_content_id to its ancestor chain.

    content_items is the flat list LMSConnector.get_content() returns
    (folders and leaf content mixed together, each with lms_content_id,
    parent_id, and title). Folders appear as items in this same list (their
    own get_content() entries), so this walks up via parent_id lookups
    rather than assuming a separate folder-listing call exists.
    """
    by_id = {item["lms_content_id"]: item for item in content_items}

    def ancestors(item: dict, _seen: frozenset[str] = frozenset()) -> list[dict]:
        parent_id = item.get("parent_id")
        if not parent_id or parent_id in _seen or parent_id not in by_id:
            return []
        parent = by_id[parent_id]
        return ancestors(parent, _seen | {parent_id}) + [
            {"lmsRef": parent_id, "title": parent.get("title") or "Untitled"}
        ]

    return {item["lms_content_id"]: ancestors(item) for item in content_items}


def module_ref_for(folder_path: list[dict]) -> str | None:
    """Convenience default: the top-level ancestor's title, or None for
    content that lives at the course root with no enclosing folder."""
    return folder_path[0]["title"] if folder_path else None
