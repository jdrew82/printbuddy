"""Resolve which slicer-api sidecar to talk to.

Precedence (first match wins):

1. Explicit override (slice request / query param / Settings test target)
2. Per-printer ``Printer.preferred_slicer`` when a printer id is supplied
3. Global ``preferred_slicer`` setting (default ``bambu_studio``)

URL for the chosen slicer comes from the matching settings key, falling
back to ``SLICER_API_URL`` / ``BAMBU_STUDIO_API_URL`` env defaults.
"""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings as app_settings

SlicerId = Literal["bambu_studio", "orcaslicer"]
VALID_SLICERS: frozenset[str] = frozenset({"bambu_studio", "orcaslicer"})


def normalize_slicer_id(value: str | None) -> SlicerId | None:
    """Return a canonical slicer id, or ``None`` when missing/unknown."""
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned in VALID_SLICERS:
        return cleaned  # type: ignore[return-value]
    return None


async def resolve_slicer_preference(
    db: AsyncSession,
    *,
    override: str | None = None,
    printer_id: int | None = None,
    strict: bool = True,
) -> SlicerId | None:
    """Pick which slicer engine to use without resolving a URL.

    When ``strict`` is False (preset listings), an unknown global preference
    returns ``None`` so the Standard tier can degrade empty instead of 400.
    """
    from backend.app.api.routes.settings import get_setting
    from backend.app.models.printer import Printer

    chosen = normalize_slicer_id(override)
    if chosen is not None:
        return chosen

    if printer_id is not None:
        printer = await db.get(Printer, printer_id)
        if printer is not None:
            chosen = normalize_slicer_id(getattr(printer, "preferred_slicer", None))
            if chosen is not None:
                return chosen

    preferred = (await get_setting(db, "preferred_slicer")) or "bambu_studio"
    chosen = normalize_slicer_id(preferred)
    if chosen is None:
        if not strict:
            return None
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown preferred_slicer setting: {preferred!r}. "
                "Expected 'orcaslicer' or 'bambu_studio'."
            ),
        )
    return chosen


async def resolve_slicer_api_url_for(
    db: AsyncSession,
    slicer: SlicerId,
) -> str:
    """Resolve the sidecar base URL for an already-chosen slicer id."""
    from backend.app.api.routes.settings import get_setting

    if slicer == "orcaslicer":
        configured = await get_setting(db, "orcaslicer_api_url")
        url = (configured or app_settings.slicer_api_url).strip()
    else:
        configured = await get_setting(db, "bambu_studio_api_url")
        url = (configured or app_settings.bambu_studio_api_url).strip()
    if not url:
        raise HTTPException(
            status_code=400,
            detail=f"No sidecar URL configured for slicer '{slicer}'.",
        )
    return url


async def resolve_slicer_sidecar(
    db: AsyncSession,
    *,
    override: str | None = None,
    printer_id: int | None = None,
    require_url: bool = True,
) -> tuple[SlicerId | None, str | None]:
    """Resolve ``(slicer_id, api_url)`` using the shared precedence rules.

    When ``require_url`` is False (preset listings), a missing URL or unknown
    preference returns ``(slicer_or_None, None)`` so the Standard tier can
    degrade to empty instead of hard-failing the modal.
    """
    slicer = await resolve_slicer_preference(
        db,
        override=override,
        printer_id=printer_id,
        strict=require_url,
    )
    if slicer is None:
        return None, None
    try:
        url = await resolve_slicer_api_url_for(db, slicer)
    except HTTPException:
        if require_url:
            raise
        return slicer, None
    return slicer, url
