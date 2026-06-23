import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import UUID


def load_example() -> ModuleType:
    path = Path("skills/kamae-py/references/taxi-request.py")
    spec = importlib.util.spec_from_file_location("taxi_request_example", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_assign_driver_round_trips_through_type_adapter() -> None:
    module = load_example()
    now = datetime(2026, 6, 23, tzinfo=UTC)
    request_id = UUID("00000000-0000-0000-0000-000000000001")
    passenger_id = UUID("00000000-0000-0000-0000-000000000002")
    driver_id = UUID("00000000-0000-0000-0000-000000000003")

    waiting = module.create_request(request_id, passenger_id, now)
    en_route = module.assign_driver(waiting, driver_id, now)
    parsed = module.parse_request(en_route.model_dump(mode="python"))

    assert isinstance(parsed, module.EnRoute)
    assert parsed.driver_id == driver_id
    assert module.describe(parsed) == f"driver {driver_id} en route"
