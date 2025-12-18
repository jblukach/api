from aws_cdk import (
    Duration,
    RemovalPolicy,
    Size,
    Stack,
    aws_apigatewayv2 as _api,
    aws_apigatewayv2_integrations as _integrations,
    aws_certificatemanager as _acm,
    aws_events as _events,
    aws_events_targets as _targets,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_logs as _logs,
    aws_route53 as _route53,
    aws_route53_targets as _r53targets,
    aws_s3 as _s3,
    aws_s3_deployment as _deployment,
    aws_ssm as _ssm
)

from constructs import Construct

class ApiUsw2(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    ### HOSTZONE ###

        hostzone = _route53.HostedZone.from_lookup(
            self, 'hostzone',
            domain_name = 'api.lukach.io'
        )

    ### PARAMETER ###

        parameter = _ssm.StringParameter(
            self, 'parameter',
            description = 'api.lukach.io',
            parameter_name = '/route53/apilukachio',
            string_value = hostzone.hosted_zone_id,
            tier = _ssm.ParameterTier.STANDARD
        )
