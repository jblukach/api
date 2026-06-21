from aws_cdk import (
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

class ApiUse2(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = Stack.of(self).account
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
            description = 'api.lukach.io',
            default_domain_mapping = _api.DomainMappingOptions(
                domain_name = domain
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

    ### GEOLITE FUNCTION ###

        geoaccount = _ssm.StringParameter.from_string_parameter_attributes(
            self, 'geoaccount',
            parameter_name = '/account/geo'
        )

        geo = _lambda.Function.from_function_attributes(
            self, 'geo',
            function_arn = 'arn:aws:lambda:us-east-2:'+geoaccount.string_value+':function:geo-search',
            same_environment = False,
            skip_permissions = True
        )

        geointegration = _integrations.HttpLambdaIntegration(
            'geointegration', geo
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
            function_arn = 'arn:aws:lambda:us-east-2:'+mcpaccount.string_value+':function:mcp-service',
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

    ### DNS RECORDS

        ipv4dns = _route53.ARecord(
            self, 'ipv4dns',
            zone = hostzone,
            record_name = 'api.lukach.io',
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
            record_name = 'api.lukach.io',
            target = _route53.RecordTarget.from_alias(
                _r53targets.ApiGatewayv2DomainProperties(
                    domain.regional_domain_name,
                    domain.regional_hosted_zone_id
                )
            )
        )
