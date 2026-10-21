import logging
from typing import Any, Literal

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.database import get_connection
from app.aws_lifecycle import record_desired_state


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("cloudcapsule")

Environment = Literal["development", "staging", "demo"]
LifecycleActionName = Literal["deploy", "stop", "restart"]
DeploymentModel = Literal["container"]
NetworkAccess = Literal["internal", "public"]

app = FastAPI(
    title="CloudCapsule API",
    description="Cloud module lifecycle and design registry platform",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class ModuleDesignFields(BaseModel):
    """Design metadata only; these values do not provision cloud resources."""

    design_version: str = Field(default="1.0.0", min_length=1, max_length=30)
    deployment_model: DeploymentModel = "container"
    cpu_units: int = Field(default=256, ge=256, le=4096)
    memory_mb: int = Field(default=512, ge=512, le=32768)
    min_replicas: int = Field(default=1, ge=0, le=100)
    max_replicas: int = Field(default=2, ge=1, le=100)
    health_check_path: str = Field(default="/health", min_length=1, max_length=200)
    network_access: NetworkAccess = "internal"
    backup_enabled: bool = False
    design_spec: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_design(self):
        if self.min_replicas > self.max_replicas:
            raise ValueError("min_replicas cannot exceed max_replicas")
        if not self.health_check_path.startswith("/"):
            raise ValueError("health_check_path must start with '/'")
        return self


class ModuleCreate(ModuleDesignFields):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=1000)
    environment: Environment = "development"


class ModuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    environment: Environment | None = None
    design_version: str | None = Field(default=None, min_length=1, max_length=30)
    deployment_model: DeploymentModel | None = None
    cpu_units: int | None = Field(default=None, ge=256, le=4096)
    memory_mb: int | None = Field(default=None, ge=512, le=32768)
    min_replicas: int | None = Field(default=None, ge=0, le=100)
    max_replicas: int | None = Field(default=None, ge=1, le=100)
    health_check_path: str | None = Field(default=None, min_length=1, max_length=200)
    network_access: NetworkAccess | None = None
    backup_enabled: bool | None = None
    design_spec: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_design(self):
        if self.min_replicas is not None and self.max_replicas is not None:
            if self.min_replicas > self.max_replicas:
                raise ValueError("min_replicas cannot exceed max_replicas")
        if self.health_check_path is not None and not self.health_check_path.startswith("/"):
            raise ValueError("health_check_path must start with '/'")
        return self


class LifecycleAction(BaseModel):
    action: LifecycleActionName


MODULE_COLUMNS = """
    id, name, description, environment, status,
    design_version, deployment_model, cpu_units, memory_mb,
    min_replicas, max_replicas, health_check_path, network_access,
    backup_enabled, design_spec, created_at
"""

DESIGN_UPDATE_COLUMNS = {
    "name", "description", "environment", "design_version",
    "deployment_model", "cpu_units", "memory_mb", "min_replicas",
    "max_replicas", "health_check_path", "network_access",
    "backup_enabled", "design_spec",
}


@app.get("/")
def root():
    return {
        "name": "CloudCapsule",
        "message": "CloudCapsule API is running",
        "mode": "local-development",
        "aws_resources_changed": False,
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
        return {"status": "healthy", "database": "postgresql"}
    except psycopg.Error:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database is unavailable")


@app.post("/modules", status_code=201)
def create_module(module: ModuleCreate):
    data = module.model_dump()
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO modules (
                    name, description, environment,
                    design_version, deployment_model, cpu_units, memory_mb,
                    min_replicas, max_replicas, health_check_path,
                    network_access, backup_enabled, design_spec
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING
                    id, name, description, environment, status,
                    design_version, deployment_model, cpu_units, memory_mb,
                    min_replicas, max_replicas, health_check_path,
                    network_access, backup_enabled, design_spec, created_at
                """,
                (
                    data["name"], data["description"], data["environment"],
                    data["design_version"], data["deployment_model"],
                    data["cpu_units"], data["memory_mb"], data["min_replicas"],
                    data["max_replicas"], data["health_check_path"],
                    data["network_access"], data["backup_enabled"],
                    psycopg.types.json.Jsonb(data["design_spec"]),
                ),
            ).fetchone()
        return row
    except psycopg.Error:
        logger.exception("Could not create module")
        raise HTTPException(
            status_code=503,
            detail="Could not save the module. Check database availability.",
        )


@app.get("/modules")
def list_modules():
    try:
        with get_connection() as connection:
            rows = connection.execute(
                f"SELECT {MODULE_COLUMNS} FROM modules ORDER BY id"
            ).fetchall()
        return rows
    except psycopg.Error:
        logger.exception("Could not list modules")
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve modules. Check database availability.",
        )


@app.get("/modules/{module_id}")
def get_module(module_id: int):
    try:
        with get_connection() as connection:
            row = connection.execute(
                f"SELECT {MODULE_COLUMNS} FROM modules WHERE id = %s",
                (module_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Module {module_id} not found")
        return row
    except HTTPException:
        raise
    except psycopg.Error:
        logger.exception("Could not retrieve module")
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve the module. Check database availability.",
        )


@app.patch("/modules/{module_id}")
def update_module(module_id: int, module: ModuleUpdate):
    updates = module.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Provide at least one field to update")
    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=422,
            detail="Fields cannot be null. Omit fields you do not want to change.",
        )
    if not set(updates).issubset(DESIGN_UPDATE_COLUMNS):
        raise HTTPException(status_code=422, detail="Unsupported update field")

    try:
        with get_connection() as connection:
            with connection.transaction():
                current = connection.execute(
                    """
                    SELECT min_replicas, max_replicas
                    FROM modules WHERE id = %s FOR UPDATE
                    """,
                    (module_id,),
                ).fetchone()
                if current is None:
                    raise HTTPException(status_code=404, detail=f"Module {module_id} not found")

                min_replicas = updates.get("min_replicas", current["min_replicas"])
                max_replicas = updates.get("max_replicas", current["max_replicas"])
                if min_replicas > max_replicas:
                    raise HTTPException(
                        status_code=422,
                        detail="min_replicas cannot exceed max_replicas",
                    )

                columns = list(updates)
                assignments = ", ".join(f"{column} = %s" for column in columns)
                values = [
                    psycopg.types.json.Jsonb(value) if column == "design_spec" else value
                    for column, value in updates.items()
                ]
                row = connection.execute(
                    f"""
                    UPDATE modules SET {assignments}
                    WHERE id = %s
                    RETURNING {MODULE_COLUMNS}
                    """,
                    (*values, module_id),
                ).fetchone()
        return row
    except HTTPException:
        raise
    except psycopg.Error:
        logger.exception("Could not update module")
        raise HTTPException(
            status_code=503,
            detail="Could not update the module. Check database availability.",
        )


@app.post("/modules/{module_id}/actions")
def perform_lifecycle_action(module_id: int, request: LifecycleAction):
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
                    SELECT id, name, status FROM modules
                    WHERE id = %s FOR UPDATE
                    """,
                    (module_id,),
                ).fetchone()
                if module is None:
                    logger.warning(
                        "Lifecycle action rejected because module was not found",
                        extra={"module_id": module_id, "action": action},
                    )
                    raise HTTPException(status_code=404, detail=f"Module {module_id} not found")

                current_status = module["status"]
                allowed_actions = {
                    "registered": {"deploy"},
                    "deploying": set(),
                    "running": {"stop"},
                    "stopped": {"deploy", "restart"},
                    "failed": {"deploy"},
                }

                if action not in allowed_actions.get(current_status, set()):
                    rejection_reason = (
                        f"Action '{action}' is not allowed from status '{current_status}'"
                    )
                    logger.warning(
                        "Invalid lifecycle transition",
                        extra={
                            "module_id": module_id,
                            "action": action,
                            "current_status": current_status,
                        },
                    )
                    connection.execute(
                        """
                        INSERT INTO module_events (
                            module_id, action, previous_status, new_status, result, details
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            module_id, action, current_status, current_status,
                            "rejected", rejection_reason,
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
                        connection.execute(
                            "UPDATE modules SET status = 'deploying' WHERE id = %s",
                            (module_id,),
                        )
                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id, action, previous_status, new_status, result, details
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id, action, current_status, "deploying", "success",
                                "Local deployment simulation started",
                            ),
                        )
                        connection.execute(
                            "UPDATE modules SET status = 'running' WHERE id = %s",
                            (module_id,),
                        )
                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id, action, previous_status, new_status, result, details
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id, action, "deploying", "running", "success",
                                "Local deployment simulation completed; no AWS resources changed",
                            ),
                        )
                    elif action == "stop":
                        connection.execute(
                            "UPDATE modules SET status = 'stopped' WHERE id = %s",
                            (module_id,),
                        )
                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id, action, previous_status, new_status, result, details
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id, action, current_status, "stopped", "success",
                                "Local stop simulation; no AWS resources changed",
                            ),
                        )
                    elif action == "restart":
                        connection.execute(
                            "UPDATE modules SET status = 'running' WHERE id = %s",
                            (module_id,),
                        )
                        connection.execute(
                            """
                            INSERT INTO module_events (
                                module_id, action, previous_status, new_status, result, details
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                module_id, action, current_status, "running", "success",
                                "Local restart simulation; no AWS resources changed",
                            ),
                        )

                    updated_module = connection.execute(
                        f"SELECT {MODULE_COLUMNS} FROM modules WHERE id = %s",
                        (module_id,),
                    ).fetchone()
                    result = {
                        "module": updated_module,
                        "action": action,
                        "simulation": True,
                        "message": (
                            "Lifecycle action completed locally; no AWS resources changed"
                        ),
                    }

        # Raise outside the transaction so the rejected-action event commits.
        if rejection_reason is not None:
            raise HTTPException(status_code=409, detail=rejection_reason)
        return result
    except HTTPException:
        raise
    except psycopg.Error:
        logger.exception("Lifecycle action failed")
        raise HTTPException(
            status_code=503,
            detail="Lifecycle action failed due to a database error",
        )


@app.post("/modules/{module_id}/aws-sync")
def sync_module_to_aws(module_id: int):
    try:
        with get_connection() as connection:
            module = connection.execute(
                "SELECT id, name, status FROM modules WHERE id = %s",
                (module_id,),
            ).fetchone()

        if module is None:
            raise HTTPException(
                status_code=404,
                detail=f"Module {module_id} not found",
            )

        action = "stop" if module["status"] == "stopped" else "deploy"
        aws_result = record_desired_state(
            module["id"], module["name"], action
        )

        return {
            "module_id": module["id"],
            "database_status": module["status"],
            "aws_sync": aws_result,
            "simulation": False,
        }
    except HTTPException:
        raise
    except RuntimeError:
        logger.exception("AWS module sync failed")
        raise HTTPException(
            status_code=503,
            detail="Could not synchronize module with AWS",
        )
    except psycopg.Error:
        logger.exception("Database lookup for AWS sync failed")
        raise HTTPException(
            status_code=503,
            detail="Could not read module from the database",
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
                raise HTTPException(status_code=404, detail=f"Module {module_id} not found")

            events = connection.execute(
                """
                SELECT
                    id, module_id, action, previous_status, new_status,
                    result, details, created_at
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
        logger.exception("Could not retrieve module events")
        raise HTTPException(status_code=503, detail="Could not retrieve lifecycle events.")


