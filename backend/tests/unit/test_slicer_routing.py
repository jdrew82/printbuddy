"""Unit tests for dual-slicer routing precedence."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.app.services import slicer_routing as routing


class TestNormalizeSlicerId:
    def test_valid_ids(self):
        assert routing.normalize_slicer_id("bambu_studio") == "bambu_studio"
        assert routing.normalize_slicer_id("orcaslicer") == "orcaslicer"
        assert routing.normalize_slicer_id("  bambu_studio  ") == "bambu_studio"

    def test_unknown_or_empty(self):
        assert routing.normalize_slicer_id(None) is None
        assert routing.normalize_slicer_id("") is None
        assert routing.normalize_slicer_id("prusaslicer") is None


class TestResolveSlicerPreference:
    @pytest.mark.asyncio
    async def test_override_wins(self):
        db = MagicMock()
        chosen = await routing.resolve_slicer_preference(
            db,
            override="orcaslicer",
            printer_id=99,
        )
        assert chosen == "orcaslicer"
        db.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_printer_preference_before_global(self):
        db = AsyncMock()
        db.get = AsyncMock(
            return_value=SimpleNamespace(preferred_slicer="orcaslicer"),
        )

        async def fake_get_setting(_db, key):
            return {"preferred_slicer": "bambu_studio"}.get(key)

        with patch(
            "backend.app.api.routes.settings.get_setting",
            new=fake_get_setting,
        ):
            chosen = await routing.resolve_slicer_preference(db, printer_id=7)
        assert chosen == "orcaslicer"
        db.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_global_default(self):
        db = MagicMock()

        async def fake_get_setting(_db, key):
            return {"preferred_slicer": "orcaslicer"}.get(key)

        with patch(
            "backend.app.api.routes.settings.get_setting",
            new=fake_get_setting,
        ):
            chosen = await routing.resolve_slicer_preference(db)
        assert chosen == "orcaslicer"

    @pytest.mark.asyncio
    async def test_unknown_global_strict_raises(self):
        db = MagicMock()

        async def fake_get_setting(_db, key):
            return {"preferred_slicer": "prusaslicer"}.get(key)

        with (
            patch(
                "backend.app.api.routes.settings.get_setting",
                new=fake_get_setting,
            ),
            pytest.raises(HTTPException) as exc,
        ):
            await routing.resolve_slicer_preference(db, strict=True)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_global_lenient_returns_none(self):
        db = MagicMock()

        async def fake_get_setting(_db, key):
            return {"preferred_slicer": "prusaslicer"}.get(key)

        with patch(
            "backend.app.api.routes.settings.get_setting",
            new=fake_get_setting,
        ):
            chosen = await routing.resolve_slicer_preference(db, strict=False)
        assert chosen is None


class TestResolveSlicerSidecar:
    @pytest.mark.asyncio
    async def test_resolves_url_for_override(self):
        async def fake_get_setting(_db, key):
            return {
                "preferred_slicer": "bambu_studio",
                "orcaslicer_api_url": "http://orca:3000",
            }.get(key)

        with patch(
            "backend.app.api.routes.settings.get_setting",
            new=fake_get_setting,
        ):
            slicer, url = await routing.resolve_slicer_sidecar(
                MagicMock(),
                override="orcaslicer",
            )
        assert slicer == "orcaslicer"
        assert url == "http://orca:3000"

    @pytest.mark.asyncio
    async def test_missing_url_require_false(self):
        async def fake_get_setting(_db, key):
            return {
                "preferred_slicer": "bambu_studio",
                "bambu_studio_api_url": "",
            }.get(key)

        with (
            patch(
                "backend.app.api.routes.settings.get_setting",
                new=fake_get_setting,
            ),
            patch(
                "backend.app.services.slicer_routing.app_settings.bambu_studio_api_url",
                "",
            ),
        ):
            slicer, url = await routing.resolve_slicer_sidecar(
                MagicMock(),
                require_url=False,
            )
        assert slicer == "bambu_studio"
        assert url is None
