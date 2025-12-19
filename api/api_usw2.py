from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as _api,
    aws_apigatewayv2_integrations as _integrations,
    aws_certificatemanager as _acm,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_logs as _logs,
    aws_route53 as _route53,
    aws_route53_targets as _r53targets,
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

    ### ACM CERTIFICATE ###

        acm = _acm.Certificate(
            self, 'acm',
            domain_name = 'usw2.api.lukach.io',
            subject_alternative_names = [
                'api.lukach.io'
            ],
            validation = _acm.CertificateValidation.from_dns(hostzone)
        )

    ### DOMAIN NAME ###

        domain = _api.DomainName(
            self, 'domain',
            domain_name = 'usw2.api.lukach.io',
            certificate = acm,
            endpoint_type = _api.EndpointType.REGIONAL,
            ip_address_type = _api.IpAddressType.DUAL_STACK
        )

    ### API LOG ROLE ###

        apirole = _iam.Role(
            self, 'apirole', 
            assumed_by = _iam.ServicePrincipal(
                'apigateway.amazonaws.com'
            )
        )

        apirole.add_managed_policy(
            _iam.ManagedPolicy.from_aws_managed_policy_name(
                'service-role/AmazonAPIGatewayPushToCloudWatchLogs'
            )
        )

        apilogs = _logs.LogGroup(
            self, 'apilogs',
            log_group_name = '/aws/apigateway/apilukachio',
            retention = _logs.RetentionDays.THIRTEEN_MONTHS,
            removal_policy = RemovalPolicy.DESTROY
        )

    ### API GATEWAY ###

        api = _api.HttpApi(
            self, 'api',
            api_name = 'api.lukach.io',
            description = 'usw2.api.lukach.io',
            default_domain_mapping = _api.DomainMappingOptions(
                domain_name = domain
            ),
            ip_address_type = _api.IpAddressType.DUAL_STACK
        )

    ### GEOLITE FUNCTION ###

        geoliteaccount = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'geoliteaccount',
            parameter_name = '/account/geolite'
        )

        geolite = _lambda.Function.from_function_attributes(
            self, 'geolite',
            function_arn = 'arn:aws:lambda:us-west-2:'+geoliteaccount.string_value+':function:search',
            same_environment = False,
            skip_permissions = True
        )

        geoliteintegration = _integrations.HttpLambdaIntegration(
            'geoliteintegration', geolite
        )

        api.add_routes(
            path = '/geo/geolite2',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = geoliteintegration
        )

    ### HEALTH FUNCTION ###

        healthrole = _iam.Role(
            self, 'healthrole',
            assumed_by = _iam.ServicePrincipal(
                'lambda.amazonaws.com'
            )
        )

        healthrole.add_managed_policy(
            _iam.ManagedPolicy.from_aws_managed_policy_name(
                'service-role/AWSLambdaBasicExecutionRole'
            )
        )

        healthrole.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'apigateway:GET'
                ],
                resources = [
                    '*'
                ]
            )
        )

        health = _lambda.Function(
            self, 'health',
            function_name = 'health',
            runtime = _lambda.Runtime.PYTHON_3_13,
            architecture = _lambda.Architecture.ARM_64,
            code = _lambda.Code.from_asset('health'),
            handler = 'health.handler',
            timeout = Duration.seconds(3),
            memory_size = 128,
            role = healthrole
        )

        healthlogs = _logs.LogGroup(
            self, 'healthlogs',
            log_group_name = '/aws/lambda/'+health.function_name,
            retention = _logs.RetentionDays.ONE_WEEK,
            removal_policy = RemovalPolicy.DESTROY
        )

        healthintegration = _integrations.HttpLambdaIntegration(
            'healthintegration', health
        )

        api.add_routes(
            path = '/health',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = healthintegration
        )

    ### DNS RECORDS

        ipv4dns = _route53.ARecord(
            self, 'ipv4dns',
            zone = hostzone,
            record_name = 'usw2.api.lukach.io',
            target = _route53.RecordTarget.from_alias(
                _r53targets.ApiGatewayv2DomainProperties(
                    domain.regional_domain_name,
                    domain.regional_hosted_zone_id
                )
            )
        )

        ipv6dns = _route53.AaaaRecord(
            self, 'ipv6dns',
            zone = hostzone,
            record_name = 'usw2.api.lukach.io',
            target = _route53.RecordTarget.from_alias(
                _r53targets.ApiGatewayv2DomainProperties(
                    domain.regional_domain_name,
                    domain.regional_hosted_zone_id
                )
            )
        )
