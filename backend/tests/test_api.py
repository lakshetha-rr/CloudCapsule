import psycopg
import app.main as main_module

import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import get_connection
from app.main import app

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


client = TestClient(app)


@pytest.fixture
def test_module():
    """Create an isolated module and remove its records after the test."""
    unique_name = f"Test Module {uuid.uuid4().hex[:12]}"

    response = client.post(
        "/modules",
        json={
            "name": unique_name,
            "description": "Temporary module for automated API tests",
            "environment": "development",
        },
    )

    assert response.status_code == 201, response.text
    module_id = response.json()["id"]

    yield module_id

    # Remove only this test's events and module.
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM module_events WHERE module_id = %s",
            (module_id,),
        )
        connection.execute(
            "DELETE FROM modules WHERE id = %s",
            (module_id,),
        )


def test_database_health():
    response = client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "postgresql",
    }


def test_module_retrieval_and_update(test_module):
    module_id = test_module

    # Retrieve the module.
    response = client.get(f"/modules/{module_id}")
    assert response.status_code == 200
    assert response.json()["id"] == module_id

    # Confirm it appears in the module list.
    response = client.get("/modules")
    assert response.status_code == 200
    assert any(item["id"] == module_id for item in response.json())

    # Update only the description.
    response = client.patch(
        f"/modules/{module_id}",
        json={"description": "Updated by automated tests"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated by automated tests"
    assert response.json()["name"].startswith("Test Module ")


def test_empty_module_update_returns_400(test_module):
    response = client.patch(
        f"/modules/{test_module}",
        json={},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide at least one field to update"


def test_null_module_update_returns_422(test_module):
    response = client.patch(
        f"/modules/{test_module}",
        json={"description": None},
    )

    assert response.status_code == 422
    assert "cannot be null" in response.json()["detail"]


def test_updating_missing_module_returns_404():
    response = client.patch(
        "/modules/999999999",
        json={"description": "This module does not exist"},
    )

    assert response.status_code == 404


def test_lifecycle_transitions_and_audit(test_module):
    module_id = test_module

    # Registered -> Deploying -> Running.
    response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "deploy"},
    )
    assert response.status_code == 200
    assert response.json()["module"]["status"] == "running"
    assert response.json()["simulation"] is True

    # Running -> Stopped.
    response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "stop"},
    )
    assert response.status_code == 200
    assert response.json()["module"]["status"] == "stopped"

    # Stopped -> Running.
    response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "restart"},
    )
    assert response.status_code == 200
    assert response.json()["module"]["status"] == "running"

    # Deploying a running module must be rejected.
    response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "deploy"},
    )
    assert response.status_code == 409

    # Verify audit history.
    response = client.get(f"/modules/{module_id}/events")
    assert response.status_code == 200

    events = response.json()
    assert len(events) == 5

    # Events are returned newest first.
    assert events[0]["action"] == "deploy"
    assert events[0]["result"] == "rejected"
    assert events[0]["previous_status"] == "running"
    assert events[0]["new_status"] == "running"

    # Verify successful deployment transitions chronologically.
    deploy_events = [
        event
        for event in events
        if event["action"] == "deploy" and event["result"] == "success"
    ]
    assert [
        event["new_status"] for event in reversed(deploy_events)
    ] == ["deploying", "running"]


def test_rejected_lifecycle_action_records_audit_event(test_module):
    module_id = test_module

    # A newly created module is registered, so stopping it is invalid.
    response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "stop"},
    )

    assert response.status_code == 409
    assert "not allowed" in response.json()["detail"]

    events_response = client.get(f"/modules/{module_id}/events")
    assert events_response.status_code == 200

    events = events_response.json()
    assert len(events) == 1
    assert events[0]["action"] == "stop"
    assert events[0]["result"] == "rejected"
    assert events[0]["previous_status"] == "registered"
    assert events[0]["new_status"] == "registered"


def test_lifecycle_action_for_missing_module_returns_404():
    response = client.post(
        "/modules/999999999/actions",
        json={"action": "deploy"},
    )

    assert response.status_code == 404


def test_invalid_lifecycle_action_does_not_change_module_status(test_module):
    module_id = test_module

    # First move the module to running.
    deploy_response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "deploy"},
    )
    assert deploy_response.status_code == 200
    assert deploy_response.json()["module"]["status"] == "running"

    # Deploying an already-running module must not change its status.
    rejected_response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "deploy"},
    )
    assert rejected_response.status_code == 409

    module_response = client.get(f"/modules/{module_id}")
    assert module_response.status_code == 200
    assert module_response.json()["status"] == "running"


def test_missing_module_returns_404():
    response = client.get("/modules/999999999")
    assert response.status_code == 404


def test_invalid_lifecycle_action_returns_validation_error(test_module):
    response = client.post(
        f"/modules/{test_module}/actions",
        json={"action": "destroy"},
    )

    assert response.status_code == 422


def test_database_health_returns_503_on_database_error(monkeypatch):
    def raise_database_error():
        raise psycopg.OperationalError("simulated database outage")

    monkeypatch.setattr(main_module, "get_connection", raise_database_error)

    response = client.get("/health/database")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Database is unavailable",
    }
    assert "simulated database outage" not in response.text


def test_concurrent_stop_requests_preserve_lifecycle_consistency(test_module):
    module_id = test_module

    # Move the module to running before concurrent requests.
    deploy_response = client.post(
        f"/modules/{module_id}/actions",
        json={"action": "deploy"},
    )
    assert deploy_response.status_code == 200
    assert deploy_response.json()["module"]["status"] == "running"

    # Release two worker threads to send stop requests together.
    barrier = Barrier(2)

    def send_stop_request():
        barrier.wait(timeout=5)
        return client.post(
            f"/modules/{module_id}/actions",
            json={"action": "stop"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(send_stop_request),
            executor.submit(send_stop_request),
        ]
        responses = [future.result(timeout=15) for future in futures]

    # Exactly one request should stop the running module.
    assert sorted(response.status_code for response in responses) == [200, 409]

    module_response = client.get(f"/modules/{module_id}")
    assert module_response.status_code == 200
    assert module_response.json()["status"] == "stopped"

    events_response = client.get(f"/modules/{module_id}/events")
    assert events_response.status_code == 200
    events = events_response.json()

    # One successful stop and one rejected stop must be recorded.
    stop_events = [event for event in events if event["action"] == "stop"]
    assert len(stop_events) == 2
    assert sum(event["result"] == "success" for event in stop_events) == 1
    assert sum(event["result"] == "rejected" for event in stop_events) == 1


def test_lifecycle_database_failure_rolls_back_status_change(test_module):
    module_id = test_module

    # A registered module can be deployed. We force the audit insert
    # to fail so the status update and event must roll back together.
    with get_connection() as connection:
        connection.execute(
            """
            CREATE OR REPLACE FUNCTION test_reject_lifecycle_event()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.action = 'deploy' THEN
                    RAISE EXCEPTION 'simulated audit insert failure';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        connection.execute(
            """
            CREATE TRIGGER test_reject_lifecycle_event_trigger
            BEFORE INSERT ON module_events
            FOR EACH ROW
            EXECUTE FUNCTION test_reject_lifecycle_event()
            """
        )

    try:
        response = client.post(
            f"/modules/{module_id}/actions",
            json={"action": "deploy"},
        )

        assert response.status_code == 503

        module_response = client.get(f"/modules/{module_id}")
        assert module_response.status_code == 200
        assert module_response.json()["status"] == "registered"

        events_response = client.get(f"/modules/{module_id}/events")
        assert events_response.status_code == 200
        assert events_response.json() == []

    finally:
        # Remove only the temporary trigger and function created by this test.
        with get_connection() as connection:
            connection.execute(
                "DROP TRIGGER IF EXISTS test_reject_lifecycle_event_trigger "
                "ON module_events"
            )
            connection.execute(
                "DROP FUNCTION IF EXISTS test_reject_lifecycle_event()"
            )