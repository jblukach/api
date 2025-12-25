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
            domain_name = 'api.lukach.io',
            subject_alternative_names = [
                'usw2.api.lukach.io'
            ],
            validation = _acm.CertificateValidation.from_dns(hostzone)
        )

    ### DOMAIN NAME ###

        domain = _api.DomainName(
            self, 'domain',
            domain_name = 'api.lukach.io',
            certificate = acm,
            endpoint_type = _api.EndpointType.REGIONAL,
            ip_address_type = _api.IpAddressType.DUAL_STACK
        )

        regional = _api.DomainName(
            self, 'regional',
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

        regionmap = _api.ApiMapping(
            self, 'regionmap',
            api = api,
            domain_name = regional
        )

    ### CARETAKER ACCOUNT ###

        caretakeraccount = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'caretakeraccount',
            parameter_name = '/account/caretaker'
        )

    ### CARETAKER ASN FUNCTION ###

        caretakerasn = _lambda.Function.from_function_attributes(
            self, 'caretakerasn',
            function_arn = 'arn:aws:lambda:us-west-2:'+caretakeraccount.string_value+':function:asn',
            same_environment = False,
            skip_permissions = True
        )

        caretakerasnintegration = _integrations.HttpLambdaIntegration(
            'caretakerasnintegration', caretakerasn
        )

        api.add_routes(
            path = '/osint/asn',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = caretakerasnintegration
        )

    ### CARETAKER CO FUNCTION ###

        caretakerco = _lambda.Function.from_function_attributes(
            self, 'caretakerco',
            function_arn = 'arn:aws:lambda:us-west-2:'+caretakeraccount.string_value+':function:co',
            same_environment = False,
            skip_permissions = True
        )

        caretakercointegration = _integrations.HttpLambdaIntegration(
            'caretakercointegration', caretakerco
        )

        api.add_routes(
            path = '/osint/co',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = caretakercointegration
        )

    ### CARETAKER DNS FUNCTION ###

        caretakerdns = _lambda.Function.from_function_attributes(
            self, 'caretakerdns',
            function_arn = 'arn:aws:lambda:us-west-2:'+caretakeraccount.string_value+':function:dns',
            same_environment = False,
            skip_permissions = True
        )

        caretakerdnsintegration = _integrations.HttpLambdaIntegration(
            'caretakerdnsintegration', caretakerdns
        )

        api.add_routes(
            path = '/osint/dns',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = caretakerdnsintegration
        )

    ### CARETAKER IP FUNCTION ###

        caretakerip = _lambda.Function.from_function_attributes(
            self, 'caretakerip',
            function_arn = 'arn:aws:lambda:us-west-2:'+caretakeraccount.string_value+':function:ip',
            same_environment = False,
            skip_permissions = True
        )

        caretakeripintegration = _integrations.HttpLambdaIntegration(
            'caretakeripintegration', caretakerip
        )

        api.add_routes(
            path = '/osint/ip',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = caretakeripintegration
        )

    ### CARETAKER ST FUNCTION ###

        caretakerst = _lambda.Function.from_function_attributes(
            self, 'caretakerst',
            function_arn = 'arn:aws:lambda:us-west-2:'+caretakeraccount.string_value+':function:st',
            same_environment = False,
            skip_permissions = True
        )

        caretakerstintegration = _integrations.HttpLambdaIntegration(
            'caretakerstintegration', caretakerst
        )

        api.add_routes(
            path = '/osint/st',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = caretakerstintegration
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
                    regional.regional_domain_name,
                    regional.regional_hosted_zone_id
                )
            )
        )

        ipv6dns = _route53.AaaaRecord(
            self, 'ipv6dns',
            zone = hostzone,
            record_name = 'usw2.api.lukach.io',
            target = _route53.RecordTarget.from_alias(
                _r53targets.ApiGatewayv2DomainProperties(
                    regional.regional_domain_name,
                    regional.regional_hosted_zone_id
                )
            )
        )

    #### HEALTH CHECK ###

        healthcheck = _route53.HealthCheck(
            self, 'healthcheck',
            type = _route53.HealthCheckType.HTTPS,
            fqdn = 'usw2.api.lukach.io',
            port = 443,
            resource_path = '/health',
            failure_threshold = 3,
            request_interval = Duration.seconds(30),
            enable_sni = True,
            regions = [
                'us-east-1',
                'us-west-2',
                'eu-west-1',
                'ap-southeast-2'
            ]
        )
