# API Ingress on AWS CDK

This repository deploys the public API Gateway ingress for [`jblukach/geo`](https://github.com/jblukach/geo) and [`jblukach/mcp`](https://github.com/jblukach/mcp). It publishes `api.lukach.io` with AWS CDK across three regions. The apex name uses Route 53 health-check-based failover between API Gateway regional endpoints in us-east-1 and us-west-2; us-east-2 provides an additional regional endpoint.

The stacks are:

- `ApiStack` (us-east-2): GitHub OIDC provider and deployment IAM role.
- `ApiUse1` (us-east-1): Route 53 hosted zone, primary API, and hosted-zone ID SSM parameter.
- `ApiUse2` (us-east-2): Regional API endpoint and DNS records.
- `ApiUsw2` (us-west-2): Route 53 secondary API and failover endpoint.

## Architecture

### Region Mapping

- `ApiStack`: us-east-2
- `ApiUse1`: us-east-1
- `ApiUse2`: us-east-2
- `ApiUsw2`: us-west-2

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
- HTTP API with custom domain `use2.api.lukach.io`
- ACM DNS-validated certificate and dual-stack DNS records (`A` and `AAAA`)
- Routes integrated to regional `search` and `mcp-service` Lambda functions
- CORS preflight support for browser clients of the public geo and MCP endpoints
- CloudFormation outputs for API ID, API endpoint, and scoped Lambda invoke source ARN patterns

`ApiUsw2`:
- HTTP API with custom domains `api.lukach.io` and `usw2.api.lukach.io`
- ACM DNS-validated certificate and dual-stack DNS records (`A` and `AAAA`)
- Secondary apex records for Route 53 failover
- Routes integrated to regional `search` and `mcp-service` Lambda functions
- CORS preflight support for browser clients of the public geo and MCP endpoints
- CloudFormation outputs for API ID, API endpoint, and scoped Lambda invoke source ARN patterns

`ApiUse1` also creates the primary `api.lukach.io` endpoint, an HTTPS `/health` route, CORS preflight support, and CloudFormation outputs for the API ID, API endpoint, and scoped Lambda invoke source ARN patterns. Route 53 checks `https://use1.api.lukach.io/health`; when it fails, traffic moves to the us-west-2 secondary records. API Gateway aliases have target-health evaluation disabled because the explicit Route 53 health check controls failover.

## API Routes

Failover base URL: `https://api.lukach.io`

Regional base URLs:

- `https://use1.api.lukach.io`
- `https://use2.api.lukach.io`
- `https://usw2.api.lukach.io`

Geo routes for [`jblukach/geo`](https://github.com/jblukach/geo):

- `GET /geo`
- `POST /geo`
- `GET /geo/{ip}`

The `geo` integration uses HTTP API payload format 2.0 so the `search` Lambda receives the v2 request context it uses for source-IP lookup.

Geo examples:

```bash
curl https://api.lukach.io/geo

curl "https://api.lukach.io/geo?ip=192.0.2.1&ip=198.51.100.111&ip=2001%3Adb8%3A%3A1"

curl -X POST https://api.lukach.io/geo \
  -H "Content-Type: application/json" \
  -d '{"ips":["192.0.2.1","192.0.2.2"]}'

curl https://api.lukach.io/geo/198.51.100.111

curl "https://api.lukach.io/geo/2001%3Adb8%3A%3A1"
```

For IPv6 path input, URL-encode colons (`:`). Query values for `ip` may be repeated or comma-separated. For POST input, send `Content-Type: application/json` with either an `ip` string or an `ips` array. `GET /geo` without an IP looks up the request source address.

MCP routes for [`jblukach/mcp`](https://github.com/jblukach/mcp):

- `ANY /mcp`
- `ANY /mcp/{proxy+}`

The `mcp` integration uses HTTP API payload format 2.0 for the FastMCP/Mangum Lambda handler.

MCP discovery examples:

```bash
curl https://api.lukach.io/mcp

curl "https://api.lukach.io/mcp?endpoint=geo"
```

MCP JSON-RPC clients must send an `Accept` header that includes both JSON and server-sent events:

```bash
curl -X POST "https://api.lukach.io/mcp" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl-probe","version":"1.0.0"}}}'
```

The `endpoint` query parameter applies to plain `GET /mcp` discovery only; MCP JSON-RPC clients post to `/mcp` without it.

API Gateway handles CORS preflight for browser clients. Allowed request headers include `accept`, `content-type`, `mcp-protocol-version`, and `mcp-session-id`; exposed response headers include `cache-control`, `content-type`, `mcp-protocol-version`, and `mcp-session-id`. Allowed methods are `DELETE`, `GET`, `POST`, and `OPTIONS`.

## Prerequisites

- Python 3.12+
- AWS CDK v2 CLI (`cdk --version`)
- AWS credentials/profile with permissions to deploy all four stacks
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

## Required External Dependencies

Before deploying the three regional API stacks, create these SSM parameters in each corresponding region:

- `/account/geo`: AWS account ID containing `search`
- `/account/mcp`: AWS account ID containing `mcp-service`

The stacks construct regional ARNs, so the functions must exist in the same region as the API:

| Stack | Region | Required functions |
| --- | --- | --- |
| `ApiUse1` | us-east-1 | `search`, `mcp-service` |
| `ApiUse2` | us-east-2 | `search`, `mcp-service` |
| `ApiUsw2` | us-west-2 | `search`, `mcp-service` |

Because these functions are imported with `skip_permissions=True`, each function-owning account must grant `apigateway.amazonaws.com` permission to invoke the functions. Use a source ARN scoped to the deployment account and the API region, for example:

```bash
aws lambda add-permission \
  --region us-east-1 \
  --function-name search \
  --statement-id api-use1-geo \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn 'arn:aws:execute-api:us-east-1:<api-account-id>:<api-id>/*/*/geo*'
```

Repeat this for `mcp-service` with the `/mcp*` source ARN pattern and for the us-east-2 and us-west-2 API regions, using unique statement IDs. Run the commands as an administrator of the account that owns each Lambda function.

Each regional API stack outputs the values needed to create those permissions:

| Output | Purpose |
| --- | --- |
| `apiendpoint` | Regional default execute-api endpoint |
| `apiid` | HTTP API ID used in source ARNs |
| `geosourcearn` | Source ARN pattern for the regional `search` Lambda permission |
| `mcpsourcearn` | Source ARN pattern for the regional `mcp-service` Lambda permission |

Retrieve them after deployment with:

```bash
aws cloudformation describe-stacks \
  --stack-name ApiUse1 \
  --query "Stacks[0].Outputs" \
  --output table \
  --profile <your-profile>
```

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
cdk diff ApiStack ApiUse1 ApiUse2 ApiUsw2 --profile <your-profile> -c account=<aws-account-id>
```

5. Deploy in order. `ApiUse2` and `ApiUsw2` read the hosted-zone ID from the SSM parameter created by `ApiUse1`, so deploy them only after `ApiUse1` completes.

```bash
cdk deploy ApiStack --require-approval never --profile <your-profile> -c account=<aws-account-id>
cdk deploy ApiUse1 --require-approval never --profile <your-profile> -c account=<aws-account-id>
cdk deploy ApiUse2 --require-approval never --profile <your-profile> -c account=<aws-account-id>
cdk deploy ApiUsw2 --require-approval never --profile <your-profile> -c account=<aws-account-id>
```

`cdk deploy --all` is not recommended for a first deployment because the regional stacks perform a runtime SSM lookup of the hosted-zone parameter.

The GitHub Actions role is created by `ApiStack`. Retrieve its ARN after deployment with:

```bash
aws cloudformation describe-stack-resources \
  --stack-name ApiStack \
  --query "StackResources[?ResourceType=='AWS::IAM::Role'].PhysicalResourceId" \
  --output text \
  --profile <your-profile>
```

Configure that role ARN as the GitHub Actions OIDC role used by workflows in `jblukach/api`. The trust policy currently permits subjects matching `repo:jblukach/api:*`.

## Troubleshooting

Unable to resolve AWS account:

```bash
cdk synth --profile <your-profile> -c account=<aws-account-id>
```

Missing hosted zone parameter:
- Ensure `ApiUse1` has been deployed and `/route53/apilukachio` exists in us-east-1.

Missing geo account parameter:
- Ensure `/account/geo` exists in the API region and points to the account that owns the regional Lambda `search`.

Missing mcp account parameter:
- Ensure `/account/mcp` exists in the API region and points to the account that owns the regional Lambda `mcp-service`.

Lambda integration returns 403 or 500:
- Confirm the target function exists in the API region and that its resource policy grants `apigateway.amazonaws.com` permission with a matching `execute-api` source ARN.
- Use the stack outputs `geosourcearn` and `mcpsourcearn` as the source ARN values for the target Lambda permissions.

Geo source-IP lookup returns the wrong address or fails unexpectedly:
- Confirm the regional `geointegration` uses HTTP API payload format 2.0 so the `search` Lambda receives `requestContext.http.sourceIp`.

MCP JSON-RPC returns `406 Not Acceptable`:
- Include `Accept: application/json, text/event-stream` on MCP JSON-RPC requests.

Browser clients fail CORS preflight:
- Confirm the deployed HTTP API includes CORS preflight for `DELETE`, `GET`, `POST`, and `OPTIONS`, and allows `accept`, `content-type`, `mcp-protocol-version`, and `mcp-session-id` request headers.

Dual-stack validation:
- Confirm API domain is `DUAL_STACK` and Route53 has both `A` and `AAAA` alias records.

## Smoke Tests

After deployment, test the failover endpoint and each regional endpoint:

```bash
for base in \
  https://api.lukach.io \
  https://use1.api.lukach.io \
  https://use2.api.lukach.io \
  https://usw2.api.lukach.io; do
  curl "$base/geo"
  curl "$base/geo?ip=1.1.1.1&ip=8.8.8.8"
  curl "$base/geo/2001%3A4860%3A4860%3A%3A8888"
  curl -X POST "$base/geo" \
    -H "Content-Type: application/json" \
    -d '{"ips":["1.1.1.1","8.8.8.8"]}'
  curl "$base/mcp"
  curl "$base/mcp?endpoint=geo"
  curl -X OPTIONS "$base/mcp" \
    -H "Origin: https://example.com" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: accept,content-type,mcp-protocol-version,mcp-session-id"
done
```

## Tests

The suite synthesizes each stack and asserts the CloudFormation template, so it needs no AWS credentials.

```bash
python -m unittest discover -s tests -v
```

It covers the geo and MCP route keys, payload format 2.0 integrations, CORS headers and methods, stage throttling and access logging, dual-stack domains, the Route 53 primary/secondary failover records and health check, the Lambda permission source-ARN outputs, and the GitHub OIDC role trust scope.

## Project Structure

```text
.
├── api/
│   ├── __init__.py
│   ├── api_stack.py
│   ├── api_use1.py
│   ├── api_use2.py
│   └── api_usw2.py
├── tests/
│   └── test_stacks.py
├── app.py
├── cdk.json
├── LICENSE
├── README.md
└── requirements.txt
```
