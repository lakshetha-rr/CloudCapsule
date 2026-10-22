# CloudCapsule Deployment Verification

## Deployment Environment
- Cloud provider: AWS
- Region: ap-south-1
- Compute: Existing EC2 instance
- Application: FastAPI
- Database: PostgreSQL 16
- Container orchestration: Docker Compose
- Lifecycle registry: AWS Systems Manager Parameter Store

## Verified Results

| Check | Result |
|---|---|
| Public API health endpoint | HTTP 200; healthy |
| Module listing endpoint | Successful |
| Backend container | Running |
| PostgreSQL container | Running; healthy |
| Backend regression tests | 27 passed |
| AWS lifecycle sync endpoint | HTTP 200 |
| Parameter Store record | Verified |
| Parameter version | 1 |
| Recorded desired state | running |

## AWS Lifecycle Integration

The endpoint `POST /modules/1/aws-sync` successfully recorded the desired state of module 1 in:

`/cloudcapsule/modules/1`

The stored record includes the module ID, name, requested action, desired status, and update timestamp. The Parameter Store record was independently retrieved using the AWS CLI.

The EC2 instance role was granted `ssm:PutParameter` permission scoped to the CloudCapsule module parameter path.

## Testing

The backend test suite was executed inside the deployed backend container.

Result: **27 passed, 1 warning**.

The warning concerns a Starlette/httpx deprecation and did not cause a test failure.

## Important Limitations

- The lifecycle integration records desired state in Parameter Store. It does not itself launch, stop, or scale application containers.
- The API health response reports `local-development` mode.
- This verification does not establish that ECS orchestration, an Application Load Balancer, automated backups, or disaster recovery have been implemented.
- The existing EC2/Docker Compose deployment was preserved; no Terraform apply was performed as part of this verification.

## Evidence Commands

Check API health:

`Invoke-RestMethod -Uri "http://13.201.55.120:8000/health"`

Retrieve the module lifecycle record:

`aws ssm get-parameter --region ap-south-1 --name "/cloudcapsule/modules/1"`

Run backend tests:

`docker compose exec -T backend python -m pytest tests -q`

## Latest Deployment Verification — 23 October 2026

### Verified Results
- EC2 instance `i-02f71a810e54296d5` is running in `ap-south-1`.
- EC2 system and instance status checks both returned `ok`.
- Backend and PostgreSQL Docker containers are running; PostgreSQL reports healthy.
- Local API health check returned `healthy` for `cloudcapsule-api`.
- Regression tests passed: **27 passed, 1 deprecation warning**, using `python -m pytest -q` inside the backend container.
- AWS Systems Manager Parameter Store contains `/cloudcapsule/modules/1`, with desired status `running`.
- The EC2 security group restricts inbound port 8000 to `122.187.117.179/32`.

### Deployment Limitations
- No ECS cluster or ECR repository was found in `ap-south-1` during the read-only checks.
- The API reports `mode: local-development`.
- The Parameter Store entry records desired state; it does not demonstrate automatic module orchestration.
- The Terraform RDS and network configuration remains undeployed.
- No Terraform apply or AWS resource creation was performed during this verification.

### Test Note
Use `python -m pytest -q` inside the backend container. Running `pytest -q` directly produced import errors, while the Python module invocation passed all 27 tests.
