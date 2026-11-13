"""SliceRequest accepts optional slicer / printer_id overrides."""

from backend.app.schemas.slicer import SliceRequest


def _base(**overrides) -> dict:
    data = {
        "printer_preset": {"source": "local", "id": "1"},
        "process_preset": {"source": "local", "id": "2"},
        "filament_presets": [{"source": "local", "id": "3"}],
    }
    data.update(overrides)
    return data


def test_slice_request_default_omits_slicer():
    req = SliceRequest.model_validate(_base())
    assert req.slicer is None
    assert req.printer_id is None


def test_slice_request_accepts_slicer_and_printer_id():
    req = SliceRequest.model_validate(
        _base(slicer="orcaslicer", printer_id=42),
    )
    assert req.slicer == "orcaslicer"
    assert req.printer_id == 42
