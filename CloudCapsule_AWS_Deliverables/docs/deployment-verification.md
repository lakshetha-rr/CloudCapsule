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
