import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def record_desired_state(module_id: int, name: str, action: str) -> dict:
    """Record desired lifecycle state in AWS Systems Manager Parameter Store."""
    if os.getenv("CLOUDCAPSULE_AWS_LIFECYCLE_ENABLED", "false").lower() != "true":
        raise RuntimeError("AWS lifecycle integration is not enabled")

    desired_status = "stopped" if action == "stop" else "running"
    region = os.getenv("AWS_REGION", "ap-south-1")
    parameter_name = f"/cloudcapsule/modules/{module_id}"

    payload = {
        "module_id": module_id,
        "name": name,
        "action": action,
        "desired_status": desired_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    client = boto3.client("ssm", region_name=region)
    try:
        client.put_parameter(
            Name=parameter_name,
            Description="CloudCapsule desired module lifecycle state",
            Value=json.dumps(payload),
            Type="String",
            Overwrite=True,
        )
    except (BotoCoreError, ClientError):
        raise RuntimeError("Could not record lifecycle state in AWS Parameter Store") from None

    return {
        "provider": "aws-ssm-parameter-store",
        "parameter_name": parameter_name,
        "desired_status": desired_status,
    }
