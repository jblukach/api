# API Ingress on AWS CDK

This repository deploys a single-region API ingress in us-east-2 using Amazon API Gateway HTTP API with a custom domain and dual-stack DNS.

## Current Architecture

The active data-plane region is us-east-2.

Stack to region mapping in code:

- ApiStack: us-east-2
- ApiUse1: us-east-1
- ApiUse2: us-east-2

- ApiStack in us-east-2
   - Creates GitHub OIDC/IAM deployment role and related permissions.
- ApiUse2 in us-east-2
   - Creates API Gateway HTTP API, ACM certificate, domain mapping, and Route53 A and AAAA alias records for api.lukach.io.
   - Integrates route /geo with Lambda function geo-search in us-east-2.
- ApiUse1 in us-east-1
   - Supporting stack only: creates public hosted zone and stores hosted zone ID in SSM parameter /route53/apilukachio.
   - ApiUse2 reads that parameter cross-region from us-east-1.

This means request serving is single region us-east-2, while DNS source data is provisioned in us-east-1.

## API Endpoint

- Base domain: api.lukach.io
- Routes:
   - GET /geo
   - POST /geo
   - GET /geo/{ip}

`/geo` supports query-string lookups (for example `?ip=1.1.1.1`). `/geo/{ip}` is a GET path-parameter lookup.

Example:

      curl https://api.lukach.io/geo

      curl "https://api.lukach.io/geo?ip=1.1.1.1"

      curl https://api.lukach.io/geo/1.1.1.1

      curl "https://api.lukach.io/geo/2001%3Adb8%3A%3A1"

## IPv4 and IPv6

The code configures dual-stack end to end:

- API Gateway domain uses DUAL_STACK IP address type.
- Route53 publishes both A and AAAA alias records for api.lukach.io.
- Both route forms work for IPv4 and IPv6. For path-style IPv6, URL-encode colons (`:`).

## Prerequisites

- AWS account with permissions to deploy CDK stacks.
- Python 3.12 or newer.
- AWS CDK CLI.
- Authenticated AWS profile for deployment.

## Deploy

Account resolution behavior (from app.py):

- CDK_DEFAULT_ACCOUNT
- CDK_DEPLOY_ACCOUNT
- AWS_ACCOUNT_ID
- CDK context account (use -c account=<aws-account-id>)

If none of these are set, synth/deploy fails fast with an explicit error.

1. Install dependencies.

          pip install -r requirements.txt

2. Authenticate profile.

          aws sso login --profile <your-profile>

3. Synthesize.

          cdk synth -c account=<aws-account-id>

4. Review changes.

          cdk diff ApiStack ApiUse1 ApiUse2 --profile <your-profile> -c account=<aws-account-id>

5. Deploy.

          cdk deploy --all --require-approval never --profile <your-profile> -c account=<aws-account-id>

## Troubleshooting

- Unable to resolve AWS account to use
   - Pass account context explicitly and use a valid profile:

            cdk synth --profile <your-profile> -c account=<aws-account-id>

- Hosted zone parameter region mismatch
   - Parameter /route53/apilukachio is intentionally read from us-east-1 by ApiUse2.

- Dual-stack check
   - Confirm API Gateway domain is DUAL_STACK and Route53 has both A and AAAA alias records.

## Project Structure

      api/
      ├── api/
      │   ├── api_stack.py
      │   ├── api_use1.py
      │   └── api_use2.py
      ├── .github/workflows/
      │   └── api.yaml
      ├── app.py
      ├── cdk.json
      └── requirements.txt
