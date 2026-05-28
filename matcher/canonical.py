"""Canonical company name normalization.

Used by score_job and the catalog loaders to make 'Bio-Reference Laboratories'
and 'BioReference' match the same network entry.

Extracted from fetch_jobs.py 2026-05-28 (Phase 1 of split refactor).
"""
import re


def canonical_company(name):
    """Normalize a company name for fuzzy matching against catalogs/network.
    Strips common suffixes (Inc, LLC, Corp), trailing parenthetical, all
    punctuation, collapses whitespace, lowercases. This is the canonical
    form used by both score_job() boost lookups AND catalog loaders so they
    agree on identity.
    Examples:
        'Bio-Reference Laboratories' -> 'bioreference laboratories'
        'BioReference'               -> 'bioreference'
        'Prescryptive Health, Inc.'  -> 'prescryptive health'
        'PillPack (Amazon)'          -> 'pillpack'
    """
    if not name:
        return ''
    n = str(name).lower()
    # Drop trailing parenthetical (e.g. "(Amazon)", "(One Medical)")
    n = re.sub(r'\s*\([^)]*\)\s*$', '', n)
    # Drop common entity suffixes
    n = re.sub(r',?\s*(inc|llc|corp|corporation|ltd|plc|co|company)\.?\s*$', '', n)
    # Strip all non-alphanumeric (hyphens, periods, commas, slashes)
    n = re.sub(r'[^a-z0-9 ]+', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n
