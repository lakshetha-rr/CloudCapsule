import json

import pytest

from app import aws_lifecycle


def test_record_desired_state_writes_parameter_store(monkeypatch):
    calls = {}

    class FakeSSM:
        def put_parameter(self, **kwargs):
            calls.update(kwargs)
            return {"Version": 1}

    monkeypatch.setenv("CLOUDCAPSULE_AWS_LIFECYCLE_ENABLED", "true")
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.setattr(
        aws_lifecycle.boto3,
        "client",
        lambda service, region_name: FakeSSM(),
    )

    result = aws_lifecycle.record_desired_state(123, "Test Module", "deploy")

    assert result["provider"] == "aws-ssm-parameter-store"
    assert result["parameter_name"] == "/cloudcapsule/modules/123"
    assert result["desired_status"] == "running"
    assert calls["Name"] == "/cloudcapsule/modules/123"
    assert calls["Overwrite"] is True
    assert json.loads(calls["Value"])["name"] == "Test Module"


def test_record_desired_state_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("CLOUDCAPSULE_AWS_LIFECYCLE_ENABLED", raising=False)

    with pytest.raises(RuntimeError, match="not enabled"):
        aws_lifecycle.record_desired_state(123, "Test Module", "deploy")
