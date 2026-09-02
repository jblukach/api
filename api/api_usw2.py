from aws_cdk import (
    CfnOutput,
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
    aws_ssm as _ssm,
    custom_resources as _cr
)

from constructs import Construct

class ApiUsw2(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = Stack.of(self).account
        region = Stack.of(self).region
        hostzone_parameter_arn = Stack.of(self).format_arn(
            service = 'ssm',
            region = 'us-east-1',
            account = account,
            resource = 'parameter',
            resource_name = 'route53/apilukachio'
        )

    ### HOSTZONE ###

        hostzone_id_lookup = _cr.AwsCustomResource(
            self,
            'hostzoneidlookup',
            on_create = _cr.AwsSdkCall(
                service = 'SSM',
                action = 'getParameter',
                region = 'us-east-1',
                parameters = {
                    'Name': '/route53/apilukachio'
                },
                physical_resource_id = _cr.PhysicalResourceId.of('route53-apilukachio-hostzone-id')
            ),
            on_update = _cr.AwsSdkCall(
                service = 'SSM',
                action = 'getParameter',
                region = 'us-east-1',
                parameters = {
                    'Name': '/route53/apilukachio'
                },
                physical_resource_id = _cr.PhysicalResourceId.of('route53-apilukachio-hostzone-id')
            ),
            policy = _cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources = [
                    hostzone_parameter_arn
                ]
            )
        )

        hostzone_id = hostzone_id_lookup.get_response_field('Parameter.Value')

        hostzone = _route53.HostedZone.from_hosted_zone_attributes(
            self,
            'hostzone',
            hosted_zone_id = hostzone_id,
            zone_name = 'api.lukach.io'
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
            api_name = 'usw2.api.lukach.io',
            description = 'usw2.api.lukach.io',
            default_domain_mapping = _api.DomainMappingOptions(
                domain_name = regional
            ),
            cors_preflight = _api.CorsPreflightOptions(
                allow_headers = [
                    'accept',
                    'content-type',
                    'mcp-session-id'
                ],
                allow_methods = [
                    _api.CorsHttpMethod.GET,
                    _api.CorsHttpMethod.POST,
                    _api.CorsHttpMethod.OPTIONS
                ],
                allow_origins = [
                    '*'
                ],
                expose_headers = [
                    'cache-control',
                    'content-type',
                    'mcp-session-id'
                ]
            ),
            ip_address_type = _api.IpAddressType.DUAL_STACK
        )

        api.default_stage.node.default_child.default_route_settings = _api.CfnStage.RouteSettingsProperty(
            throttling_rate_limit = 2,
            throttling_burst_limit = 5
        )

        api.default_stage.node.default_child.access_log_settings = _api.CfnStage.AccessLogSettingsProperty(
            destination_arn = apilogs.log_group_arn,
            format = '{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength"}'
        )

    ### APEX DOMAIN MAPPING ###

        _api.ApiMapping(
            self, 'apexmapping',
            api = api,
            domain_name = domain,
            stage = api.default_stage
        )

    ### HEALTH FUNCTION ###

        health = _lambda.Function(
            self, 'health',
            runtime = _lambda.Runtime.PYTHON_3_12,
            handler = 'index.handler',
            code = _lambda.Code.from_inline(
                "import json\n"
                "import os\n"
                "\n"
                "def handler(event, context):\n"
                "    return {\n"
                "        'statusCode': 200,\n"
                "        'body': json.dumps(os.environ['AWS_REGION'])\n"
                "    }\n"
            ),
            reserved_concurrent_executions = 5
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

    ### GEOLITE FUNCTION ###

        geoaccount = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'geoaccount',
            parameter_name = '/account/geo'
        )

        geo = _lambda.Function.from_function_attributes(
            self, 'geo',
            function_arn = 'arn:aws:lambda:'+region+':'+geoaccount.string_value+':function:search',
            same_environment = False,
            skip_permissions = True
        )

        geointegration = _integrations.HttpLambdaIntegration(
            'geointegration', geo,
            payload_format_version = _api.PayloadFormatVersion.VERSION_2_0
        )

        api.add_routes(
            path = '/geo',
            methods = [
                _api.HttpMethod.GET,
                _api.HttpMethod.POST
            ],
            integration = geointegration
        )

        api.add_routes(
            path = '/geo/{ip}',
            methods = [
                _api.HttpMethod.GET
            ],
            integration = geointegration
        )

    ### MCP SERVICE FUNCTION ###

        mcpaccount = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'mcpaccount',
            parameter_name = '/account/mcp'
        )

        mcp = _lambda.Function.from_function_attributes(
            self, 'mcp',
            function_arn = 'arn:aws:lambda:'+region+':'+mcpaccount.string_value+':function:mcp-service',
            same_environment = False,
            skip_permissions = True
        )

        mcpintegration = _integrations.HttpLambdaIntegration(
            'mcpintegration', mcp,
            payload_format_version = _api.PayloadFormatVersion.VERSION_2_0
        )

        api.add_routes(
            path = '/mcp',
            methods = [
                _api.HttpMethod.ANY
            ],
            integration = mcpintegration
        )

        api.add_routes(
            path = '/mcp/{proxy+}',
            methods = [
                _api.HttpMethod.ANY
            ],
            integration = mcpintegration
        )

    ### OUTPUTS ###

        CfnOutput(
            self, 'apiendpoint',
            description = 'Regional HTTP API endpoint',
            value = api.api_endpoint
        )

        CfnOutput(
            self, 'apiid',
            description = 'HTTP API ID used in execute-api source ARNs',
            value = api.api_id
        )

        CfnOutput(
            self, 'geosourcearn',
            description = 'Source ARN pattern for API Gateway invoking the regional geo search Lambda',
            value = 'arn:aws:execute-api:'+region+':'+account+':'+api.api_id+'/*/*/geo*'
        )

        CfnOutput(
            self, 'mcpsourcearn',
            description = 'Source ARN pattern for API Gateway invoking the regional MCP service Lambda',
            value = 'arn:aws:execute-api:'+region+':'+account+':'+api.api_id+'/*/*/mcp*'
        )

    ### DNS RECORDS ###

        _route53.ARecord(
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

        _route53.AaaaRecord(
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

    ### APEX FAILOVER DNS (SECONDARY) ###

        _route53.CfnRecordSet(
            self, 'apexipv4dns',
            hosted_zone_id = hostzone_id,
            name = 'api.lukach.io',
            type = 'A',
            failover = 'SECONDARY',
            set_identifier = 'usw2',
            alias_target = _route53.CfnRecordSet.AliasTargetProperty(
                dns_name = domain.regional_domain_name,
                hosted_zone_id = domain.regional_hosted_zone_id,
                evaluate_target_health = False
            )
        )

        _route53.CfnRecordSet(
            self, 'apexipv6dns',
            hosted_zone_id = hostzone_id,
            name = 'api.lukach.io',
            type = 'AAAA',
            failover = 'SECONDARY',
            set_identifier = 'usw2',
            alias_target = _route53.CfnRecordSet.AliasTargetProperty(
                dns_name = domain.regional_domain_name,
                hosted_zone_id = domain.regional_hosted_zone_id,
                evaluate_target_health = False
            )
        )
