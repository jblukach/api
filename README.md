# API Ingress on AWS CDK

This repository deploys `api.lukach.io` with AWS CDK using a multi-stack layout:

- `ApiStack` (us-east-2): GitHub OIDC provider and deployment IAM role.
- `ApiUse1` (us-east-1): Route53 hosted zone and SSM parameter export for hosted zone ID.
- `ApiUse2` (us-east-2): API Gateway HTTP API, ACM certificate, custom domain, and dual-stack DNS.

The API data plane is in us-east-2. Cross-region lookup from us-east-2 to us-east-1 is used only to read the hosted zone ID parameter.

## Architecture

### Region Mapping

- `ApiStack`: us-east-2
- `ApiUse1`: us-east-1
- `ApiUse2`: us-east-2

### What Gets Created

`ApiStack`:
- GitHub Actions OIDC identity provider (`token.actions.githubusercontent.com`)
- IAM role trusted by `repo:jblukach/api:*`
- CDK deployment permissions for CloudFormation, S3, KMS, IAM pass role, and SSM bootstrap version checks

`ApiUse1`:
- Public hosted zone: `api.lukach.io`
- Route53 query log group: `/aws/route53/apilukachio`
- SSM parameter: `/route53/apilukachio` (hosted zone ID)

`ApiUse2`:
- HTTP API with custom domain `api.lukach.io`
- ACM DNS-validated certificate for `api.lukach.io`
- Dual-stack API domain + dual-stack DNS records (`A` and `AAAA`)
- Routes integrated to Lambda function `geo-search` in us-east-2
- Routes integrated to Lambda function `mcp-service` in us-east-2

## API Routes

Base URL: `https://api.lukach.io`

- `GET /geo`
- `POST /geo`
- `GET /geo/{ip}`
- `ANY /mcp`
- `ANY /mcp/{proxy+}`

Examples:

```bash
curl https://api.lukach.io/geo

curl "https://api.lukach.io/geo?ip=192.0.2.1&ip=198.51.100.111&ip=2001%3Adb8%3A%3A1"

curl -X POST https://api.lukach.io/geo \
  -H "Content-Type: application/json" \
  -d '{"ips":["192.0.2.1","192.0.2.2"]}'

curl https://api.lukach.io/geo/198.51.100.111

curl "https://api.lukach.io/geo/2001%3Adb8%3A%3A1"
```

For IPv6 path input, URL-encode colons (`:`).

## Prerequisites

- Python 3.12+
- AWS CDK v2 CLI (`cdk --version`)
- AWS credentials/profile with permissions to deploy all three stacks
- CDK bootstrap with qualifier `lukach` in each deployed region

The code references bootstrap execution roles with qualifier `lukach` in:

- us-east-1
- us-east-2
- us-west-2

Bootstrap example:

```bash
cdk bootstrap aws://<aws-account-id>/us-east-1 --qualifier lukach --profile <your-profile>
cdk bootstrap aws://<aws-account-id>/us-east-2 --qualifier lukach --profile <your-profile>
cdk bootstrap aws://<aws-account-id>/us-west-2 --qualifier lukach --profile <your-profile>
```

## Required External Dependency

`ApiUse2` imports the target Lambda account ID from SSM parameter:

- `/account/geo`
- `/account/mcp`

Expected Lambda ARN shape:

- `arn:aws:lambda:us-east-2:<value-of-/account/geo>:function:geo-search`
- `arn:aws:lambda:us-east-2:<value-of-/account/mcp>:function:mcp-service`

Create this parameter before deploying `ApiUse2`.

## Deploy

`app.py` resolves account in this order:

- `CDK_DEFAULT_ACCOUNT`
- `CDK_DEPLOY_ACCOUNT`
- `AWS_ACCOUNT_ID`
- CDK context value `account` (`-c account=<aws-account-id>`)

If none are set, synth/deploy fails with an explicit error.

1. Install dependencies.

```bash
pip install -r requirements.txt
```

2. Authenticate.

```bash
aws sso login --profile <your-profile>
```

3. Synthesize.

```bash
cdk synth --profile <your-profile> -c account=<aws-account-id>
```

4. Review changes.

```bash
cdk diff ApiStack ApiUse1 ApiUse2 --profile <your-profile> -c account=<aws-account-id>
```

5. Deploy all stacks.

```bash
cdk deploy --all --require-approval never --profile <your-profile> -c account=<aws-account-id>
```

Recommended first-time order (if deploying individually):

1. `ApiStack`
2. `ApiUse1`
3. `ApiUse2`

## Troubleshooting

Unable to resolve AWS account:

```bash
cdk synth --profile <your-profile> -c account=<aws-account-id>
```

Missing hosted zone parameter:
- Ensure `ApiUse1` has been deployed and `/route53/apilukachio` exists in us-east-1.

Missing geo account parameter:
- Ensure `/account/geo` exists and points to the account that owns Lambda `geo-search`.

Missing mcp account parameter:
- Ensure `/account/mcp` exists and points to the account that owns Lambda `mcp-service`.

Dual-stack validation:
- Confirm API domain is `DUAL_STACK` and Route53 has both `A` and `AAAA` alias records.

## Project Structure

```text
.
├── api/
│   ├── __init__.py
│   ├── api_stack.py
│   ├── api_use1.py
│   └── api_use2.py
├── app.py
├── cdk.json
├── LICENSE
├── README.md
└── requirements.txt
```
