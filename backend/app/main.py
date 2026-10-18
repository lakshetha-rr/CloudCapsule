
import logging
import psycopg
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.database import get_connection


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("cloudcapsule")


Environment = Literal["development", "staging", "demo"]
LifecycleActionName = Literal["deploy", "stop", "restart"]


app = FastAPI(
    title="CloudCapsule API",
    description="Cloud module lifecycle management platform",
    version="0.5.0",
)


class ModuleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=1000)
    environment: Environment = "development"


class ModuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    environment: Environment | None = None


class LifecycleAction(BaseModel):
    action: LifecycleActionName


MODULE_COLUMNS = """
    id, name, description, environment, status, created_at
"""


@app.get("/")
def root():
    return {
        "name": "CloudCapsule",
        "message": "CloudCapsule API is running",
        "mode": "local-development",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "cloudcapsule-api",
        "mode": "local-development",
    }


@app.get("/health/database")
def database_health():
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1")

        return {
            "status": "healthy",
            "database": "postgresql",
        }
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        )


@app.post("/modules", status_code=201)
def create_module(module: ModuleCreate):
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO modules (name, description, environment)
                VALUES (%s, %s, %s)
                RETURNING id, name, description, environment, status, created_at
                """,
                (module.name, module.description, module.environment),
            ).fetchone()

        return row

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Could not save the module. Check database availability.",
        )


@app.get("/modules")
def list_modules():
    try:
        with get_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT {MODULE_COLUMNS}
                FROM modules
                ORDER BY id
                """
            ).fetchall()

        return rows

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve modules. Check database availability.",
        )


@app.get("/modules/{module_id}")
def get_module(module_id: int):
    try:
        with get_connection() as connection:
            row = connection.execute(
                f"""
                SELECT {MODULE_COLUMNS}
                FROM modules
                WHERE id = %s
                """,
                (module_id,),
            ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Module {module_id} not found",
            )

        return row

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve the module. Check database availability.",
        )


@app.patch("/modules/{module_id}")
def update_module(module_id: int, module: ModuleUpdate):
    updates = module.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update",
        )

    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=422,
            detail="Fields cannot be null. Omit fields you do not want to change.",
        )

    try:
        columns = list(updates.keys())
        assignments = ", ".join(f"{column} = %s" for column in columns)
        values = [updates[column] for column in columns]

        with get_connection() as connection:
            row = connection.execute(
                f"""
                UPDATE modules
                SET {assignments}
                WHERE id = %s
                RETURNING {MODULE_COLUMNS}
                """,
                (*values, module_id),
            ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Module {module_id} not found",
            )

        return row

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Could not update the module. Check database availability.",
        )


@app.post("/modules/{module_id}/actions")
def perform_lifecycle_action(
    module_id: int,
    request: LifecycleAction,
):
    action = request.action
    logger.info(
        "Lifecycle action requested",
        extra={"module_id": module_id, "action": action},
    )
    rejection_reason = None
    result = None

    try:
        with get_connection() as connection:
            with connection.transaction():
                module = connection.execute(
                    """
                    SELECT id, name, status
                    FROM modules
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (module_id,),
                ).fetchone()

                if module is None:
                    logger.warning(
                        "Lifecycle action rejected because module was not found",
                        extra={"module_id": module_id, "action": action},
                    )
                    raise HTTPException(
                        status_code=404,
                        detail=f"Module {module_id} not found",
                    )

                current_status = module["status"]

                allowed_actions = {
                    "registered": {"deploy"},
                    "deploying": set(),
                    "running": {"stop"},
                    "stopped": {"deploy", "restart"},
                    "failed": {"deploy"},
                }

                if action not in allowed_actions.get(current_status, set()):
                    logger.warning(
                        "Invalid lifecycle transition",
                        extra={
                            "module_id": module_id,
                            "action": action,
                            "current_status": current_status,
                        },
                )
                    rejection_reason = (
                        f"Action '{action}' is not allowed "
                        f"from status '{current_status}'"
                    )

                    connection.execute(
                        """
                        INSERT INTO module_events (
                            module_id,
                            action,
                            previous_status,
                            new_status,
                            result,
                            details
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            module_id,
                            action,
                            current_status,
                            current_status,
                            "rejected",
                            rejection_reason,
                        ),
                    )

                else:
                    logger.info(
                        "Lifecycle transition accepted",
                        extra={
                            "module_id": module_id,
                            "action": action,
                            "previous_status": current_status,
                        },
                    )
                    if action == "deploy":
                        # Record the start of the simulated deployment.
                        connection.execute(
                            """
                            UPDATE modules
                            SET status = 'deploying'
                            WHERE id = %s
                            """,
                            (module_id,),
                        )

                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id,
                                action,
                                previous_status,
                                new_status,
                                result,
                                details
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id,
                                action,
                                current_status,
                                "deploying",
                                "success",
                                "Local deployment simulation started",
                            ),
                        )

                        # Complete the simulation locally.
                        connection.execute(
                            """
                            UPDATE modules
                            SET status = 'running'
                            WHERE id = %s
                            """,
                            (module_id,),
                        )

                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id,
                                action,
                                previous_status,
                                new_status,
                                result,
                                details
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id,
                                action,
                                "deploying",
                                "running",
                                "success",
                                "Local deployment simulation completed; no AWS resources changed",
                            ),
                        )

                    elif action == "stop":
                        connection.execute(
                            """
                            UPDATE modules
                            SET status = 'stopped'
                            WHERE id = %s
                            """,
                            (module_id,),
                        )

                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id,
                                action,
                                previous_status,
                                new_status,
                                result,
                                details
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id,
                                action,
                                current_status,
                                "stopped",
                                "success",
                                "Local stop simulation; no AWS resources changed",
                            ),
                        )

                    elif action == "restart":
                        connection.execute(
                            """
                            UPDATE modules
                            SET status = 'running'
                            WHERE id = %s
                            """,
                            (module_id,),
                        )

                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id,
                                action,
                                previous_status,
                                new_status,
                                result,
                                details
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id,
                                action,
                                current_status,
                                "running",
                                "success",
                                "Local restart simulation; no AWS resources changed",
                            ),
                        )

                    updated_module = connection.execute(
                        f"""
                        SELECT {MODULE_COLUMNS}
                        FROM modules
                        WHERE id = %s
                        """,
                        (module_id,),
                    ).fetchone()

                    result = {
                        "module": updated_module,
                        "action": action,
                        "simulation": True,
                        "message": (
                            "Lifecycle action completed locally; "
                            "no AWS resources changed"
                        ),
                    }

        # Raise outside the transaction so the rejected-action event commits.
        if rejection_reason is not None:
            raise HTTPException(
                status_code=409,
                detail=rejection_reason,
            )

        return result

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Lifecycle action failed due to a database error",
        )


@app.get("/modules/{module_id}/events")
def list_module_events(module_id: int):
    try:
        with get_connection() as connection:
            module = connection.execute(
                "SELECT id FROM modules WHERE id = %s",
                (module_id,),
            ).fetchone()

            if module is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Module {module_id} not found",
                )

            events = connection.execute(
                """
                SELECT
                    id,
                    module_id,
                    action,
                    previous_status,
                    new_status,
                    result,
                    details,
                    created_at
                FROM module_events
                WHERE module_id = %s
                ORDER BY id DESC
                """,
                (module_id,),
            ).fetchall()

        return events

    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve lifecycle events.",
        )
