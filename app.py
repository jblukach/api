#!/usr/bin/env python3
import os

import aws_cdk as cdk

from api.api_stack import ApiStack
from api.api_use1 import ApiUse1
from api.api_use2 import ApiUse2

app = cdk.App()


def resolve_account() -> str:
    account = (
        os.getenv('CDK_DEFAULT_ACCOUNT')
        or os.getenv('CDK_DEPLOY_ACCOUNT')
        or os.getenv('AWS_ACCOUNT_ID')
        or app.node.try_get_context('account')
    )
    if account:
        return account

    raise RuntimeError(
        'Unable to resolve AWS account. Set CDK_DEFAULT_ACCOUNT/AWS_ACCOUNT_ID, '
        'or pass context with -c account=<aws-account-id>. '
        'If using a profile, ensure it is configured and authenticated before running CDK.'
    )


account = resolve_account()

ApiStack(
    app, "ApiStack",
    env = cdk.Environment(
        account = account,
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

ApiUse1(
    app, "ApiUse1",
    env = cdk.Environment(
        account = account,
        region = 'us-east-1'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

ApiUse2(
    app, "ApiUse2",
    env = cdk.Environment(
        account = account,
        region = 'us-east-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

cdk.Tags.of(app).add('Alias','api')
cdk.Tags.of(app).add('GitHub','https://github.com/jblukach/api')
cdk.Tags.of(app).add('Org','lukach.io')

app.synth()