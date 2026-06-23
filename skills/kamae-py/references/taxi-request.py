"""Compact Kamae Python example for a taxi request aggregate."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Protocol, assert_never
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Waiting(DomainModel):
    kind: Literal["waiting"] = "waiting"
    request_id: UUID
    passenger_id: UUID
    created_at: datetime


class EnRoute(DomainModel):
    kind: Literal["en_route"] = "en_route"
    request_id: UUID
    passenger_id: UUID
    driver_id: UUID
    assigned_at: datetime


class InTrip(DomainModel):
    kind: Literal["in_trip"] = "in_trip"
    request_id: UUID
    passenger_id: UUID
    driver_id: UUID
    started_at: datetime


class Completed(DomainModel):
    kind: Literal["completed"] = "completed"
    request_id: UUID
    passenger_id: UUID
    driver_id: UUID
    started_at: datetime
    completed_at: datetime


class Cancelled(DomainModel):
    kind: Literal["cancelled"] = "cancelled"
    request_id: UUID
    passenger_id: UUID
    cancelled_at: datetime
    reason: str


type TaxiRequest = Annotated[
    Waiting | EnRoute | InTrip | Completed | Cancelled,
    Field(discriminator="kind"),
]
type CancellableRequest = Waiting | EnRoute | InTrip
TaxiRequestAdapter: TypeAdapter[TaxiRequest] = TypeAdapter(TaxiRequest)


def create_request(request_id: UUID, passenger_id: UUID, now: datetime) -> Waiting:
    return Waiting(request_id=request_id, passenger_id=passenger_id, created_at=now)


def assign_driver(waiting: Waiting, driver_id: UUID, now: datetime) -> EnRoute:
    return EnRoute(
        request_id=waiting.request_id,
        passenger_id=waiting.passenger_id,
        driver_id=driver_id,
        assigned_at=now,
    )


def start_trip(en_route: EnRoute, now: datetime) -> InTrip:
    return InTrip(
        request_id=en_route.request_id,
        passenger_id=en_route.passenger_id,
        driver_id=en_route.driver_id,
        started_at=now,
    )


def complete_trip(in_trip: InTrip, now: datetime) -> Completed:
    return Completed(
        request_id=in_trip.request_id,
        passenger_id=in_trip.passenger_id,
        driver_id=in_trip.driver_id,
        started_at=in_trip.started_at,
        completed_at=now,
    )


def cancel(request: CancellableRequest, reason: str, now: datetime) -> Cancelled:
    return Cancelled(
        request_id=request.request_id,
        passenger_id=request.passenger_id,
        cancelled_at=now,
        reason=reason,
    )


def describe(request: TaxiRequest) -> str:
    match request:
        case Waiting(created_at=created_at):
            return f"waiting since {created_at.isoformat()}"
        case EnRoute(driver_id=driver_id):
            return f"driver {driver_id} en route"
        case InTrip(started_at=started_at):
            return f"in trip since {started_at.isoformat()}"
        case Completed(completed_at=completed_at):
            return f"completed at {completed_at.isoformat()}"
        case Cancelled(reason=reason):
            return f"cancelled: {reason}"
        case _:
            assert_never(request)


class DriverAssigned(DomainModel):
    event_name: Literal["driver_assigned"] = "driver_assigned"
    event_id: UUID
    event_at: datetime
    aggregate_id: UUID
    driver_id: UUID
    passenger_id: UUID


def driver_assigned_event(en_route: EnRoute, now: datetime) -> DriverAssigned:
    return DriverAssigned(
        event_id=uuid4(),
        event_at=now,
        aggregate_id=en_route.request_id,
        driver_id=en_route.driver_id,
        passenger_id=en_route.passenger_id,
    )


class RequestResolver(Protocol):
    async def find_waiting(self, request_id: UUID) -> Waiting | None: ...


class RequestStore(Protocol):
    async def save_en_route(
        self,
        state: EnRoute,
        events: tuple[DriverAssigned, ...],
    ) -> None: ...


def parse_request(raw: object) -> TaxiRequest:
    return TaxiRequestAdapter.validate_python(raw)


def example() -> str:
    now = datetime.now(UTC)
    request = create_request(uuid4(), uuid4(), now)
    en_route = assign_driver(request, uuid4(), now)
    return describe(parse_request(en_route.model_dump(mode="python")))


if __name__ == "__main__":
    print(example())
