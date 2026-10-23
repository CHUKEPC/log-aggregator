"""Alert management and event inspection endpoints.

Allows configuring pattern-based alerting rules and reviewing triggered notifications.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from log_aggregator.api.deps import get_alerter
from log_aggregator.exceptions import NotFoundError
from log_aggregator.schemas.alerts import (
    AlertEventResponse,
    AlertRuleCreate,
    AlertRuleResponse,
)
from log_aggregator.services.alerter import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_in: AlertRuleCreate,
    alerter: Annotated[AlertService, Depends(get_alerter)],
) -> AlertRuleResponse:
    """Create and register a new alert rule."""
    rule = alerter.create_rule(rule_in)
    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        condition=rule.condition,
        service=rule.service,
        level=rule.level,
        pattern=rule.pattern,
        threshold=rule.threshold,
        window_minutes=rule.window_minutes,
        webhook_url=rule.webhook_url,
        enabled=rule.enabled,
        created_at=rule.created_at,
    )


@router.get("/rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    alerter: Annotated[AlertService, Depends(get_alerter)],
) -> list[AlertRuleResponse]:
    """List all registered alert rules."""
    rules = alerter.list_rules()
    return [
        AlertRuleResponse(
            id=r.id,
            name=r.name,
            condition=r.condition,
            service=r.service,
            level=r.level,
            pattern=r.pattern,
            threshold=r.threshold,
            window_minutes=r.window_minutes,
            webhook_url=r.webhook_url,
            enabled=r.enabled,
            created_at=r.created_at,
        )
        for r in rules
    ]


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: str,
    alerter: Annotated[AlertService, Depends(get_alerter)],
) -> AlertRuleResponse:
    """Retrieve details for a specific alert rule."""
    try:
        r = alerter.get_rule(rule_id)
        return AlertRuleResponse(
            id=r.id,
            name=r.name,
            condition=r.condition,
            service=r.service,
            level=r.level,
            pattern=r.pattern,
            threshold=r.threshold,
            window_minutes=r.window_minutes,
            webhook_url=r.webhook_url,
            enabled=r.enabled,
            created_at=r.created_at,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: str,
    alerter: Annotated[AlertService, Depends(get_alerter)],
) -> None:
    """Delete an alert rule by ID."""
    try:
        alerter.delete_rule(rule_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


@router.get("/events", response_model=list[AlertEventResponse])
async def list_alert_events(
    alerter: Annotated[AlertService, Depends(get_alerter)],
    limit: Annotated[int, Query(ge=1, le=500, description="Max events to return")] = 50,
) -> list[AlertEventResponse]:
    """Retrieve history of triggered alert occurrences."""
    events = alerter.list_events(limit=limit)
    return [
        AlertEventResponse(
            id=e.id,
            rule_id=e.rule_id,
            rule_name=e.rule_name,
            triggered_at=e.triggered_at,
            message=e.message,
            count=e.count,
        )
        for e in events
    ]
