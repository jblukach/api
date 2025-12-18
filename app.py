#!/usr/bin/env python3
import os

import aws_cdk as cdk

from api.api_stack import ApiStack
from api.api_use1 import ApiUse1
from api.api_usw2 import ApiUsw2

app = cdk.App()

ApiStack(
    app, "ApiStack",
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-1'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

ApiUse1(
    app, "ApiUse1",
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-east-1'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

ApiUsw2(
    app, "ApiUsw2",
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = 'us-west-2'
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = 'lukach'
    )
)

cdk.Tags.of(app).add('Alias','api')
cdk.Tags.of(app).add('GitHub','https://github.com/jblukach/api')
cdk.Tags.of(app).add('Org','lukach.io')

app.synth()