import unittest

import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from api.api_stack import ApiStack
from api.api_use1 import ApiUse1
from api.api_use2 import ApiUse2
from api.api_usw2 import ApiUsw2


ACCOUNT = '123456789012'

CORS_ALLOW_HEADERS = ['accept', 'content-type', 'mcp-protocol-version', 'mcp-session-id']
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'POST', 'OPTIONS']
CORS_EXPOSE_HEADERS = ['cache-control', 'content-type', 'mcp-protocol-version', 'mcp-session-id']

REGIONAL_STACKS = (
    ('ApiUse1', ApiUse1, 'us-east-1'),
    ('ApiUse2', ApiUse2, 'us-east-2'),
    ('ApiUsw2', ApiUsw2, 'us-west-2'),
)


def _template(stack_class, name, region):
    app = cdk.App()
    stack = stack_class(
        app, name,
        env = cdk.Environment(account = ACCOUNT, region = region),
        synthesizer = cdk.DefaultStackSynthesizer(qualifier = 'lukach')
    )
    return Template.from_stack(stack)


def _route_keys(template):
    return [
        route['Properties']['RouteKey']
        for route in template.find_resources('AWS::ApiGatewayV2::Route').values()
    ]


class RegionalApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.templates = {
            name: _template(stack_class, name, region)
            for name, stack_class, region in REGIONAL_STACKS
        }

    def test_cors_allows_mcp_headers_and_methods(self):
        for name, template in self.templates.items():
            with self.subTest(stack = name):
                template.has_resource_properties('AWS::ApiGatewayV2::Api', {
                    'CorsConfiguration': {
                        'AllowHeaders': CORS_ALLOW_HEADERS,
                        'AllowMethods': CORS_ALLOW_METHODS,
                        'ExposeHeaders': CORS_EXPOSE_HEADERS
                    }
                })

    def test_geo_and_mcp_routes_exist(self):
        for name, template in self.templates.items():
            with self.subTest(stack = name):
                routes = _route_keys(template)
                for route_key in (
                    'GET /geo',
                    'POST /geo',
                    'GET /geo/{ip}',
                    'ANY /mcp',
                    'ANY /mcp/{proxy+}'
                ):
                    self.assertIn(route_key, routes)

    def test_lambda_integrations_use_payload_format_two(self):
        # geo needs the v2 request context for source-IP lookup; mcp needs it for Mangum.
        for name, template in self.templates.items():
            with self.subTest(stack = name):
                integrations = template.find_resources('AWS::ApiGatewayV2::Integration')
                self.assertTrue(integrations)
                for integration in integrations.values():
                    self.assertEqual(integration['Properties']['IntegrationType'], 'AWS_PROXY')
                    self.assertEqual(integration['Properties']['PayloadFormatVersion'], '2.0')

    def test_outputs_expose_lambda_permission_source_arns(self):
        for name, template in self.templates.items():
            with self.subTest(stack = name):
                outputs = template.find_outputs('*')
                for output in ('apiid', 'apiendpoint', 'geosourcearn', 'mcpsourcearn'):
                    self.assertIn(output, outputs)

    def test_stages_are_throttled_and_logged(self):
        for name, template in self.templates.items():
            with self.subTest(stack = name):
                template.has_resource_properties('AWS::ApiGatewayV2::Stage', {
                    'AccessLogSettings': Match.any_value(),
                    'DefaultRouteSettings': {
                        'ThrottlingBurstLimit': 5,
                        'ThrottlingRateLimit': 2
                    }
                })

    def test_domains_are_dual_stack(self):
        for name, template in self.templates.items():
            with self.subTest(stack = name):
                template.all_resources_properties('AWS::ApiGatewayV2::DomainName', {
                    'DomainNameConfigurations': Match.array_with([
                        Match.object_like({
                            'EndpointType': 'REGIONAL',
                            'IpAddressType': 'dualstack'
                        })
                    ])
                })


class ApiUse1Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.template = _template(ApiUse1, 'ApiUse1', 'us-east-1')

    def test_publishes_hosted_zone_id_parameter(self):
        self.template.has_resource_properties('AWS::SSM::Parameter', {
            'Name': '/route53/apilukachio'
        })

    def test_health_route_backs_the_failover_health_check(self):
        self.assertIn('GET /health', _route_keys(self.template))
        self.template.has_resource_properties('AWS::Route53::HealthCheck', {
            'HealthCheckConfig': {
                'Type': 'HTTPS',
                'FullyQualifiedDomainName': 'use1.api.lukach.io',
                'ResourcePath': '/health',
                'Port': 443
            }
        })

    def test_apex_records_are_primary_with_health_check(self):
        records = self.template.find_resources('AWS::Route53::RecordSet', {
            'Properties': {'Failover': 'PRIMARY'}
        })
        self.assertEqual(
            sorted(record['Properties']['Type'] for record in records.values()),
            ['A', 'AAAA']
        )
        for record in records.values():
            self.assertIn('HealthCheckId', record['Properties'])
            self.assertFalse(record['Properties']['AliasTarget']['EvaluateTargetHealth'])


class ApiUsw2Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.template = _template(ApiUsw2, 'ApiUsw2', 'us-west-2')

    def test_apex_records_are_secondary(self):
        records = self.template.find_resources('AWS::Route53::RecordSet', {
            'Properties': {'Failover': 'SECONDARY'}
        })
        self.assertEqual(
            sorted(record['Properties']['Type'] for record in records.values()),
            ['A', 'AAAA']
        )


class ApiStackTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.template = _template(ApiStack, 'ApiStack', 'us-east-2')

    def test_github_oidc_role_is_scoped_to_this_repository(self):
        self.template.has_resource_properties('AWS::IAM::Role', {
            'AssumeRolePolicyDocument': {
                'Statement': Match.array_with([
                    Match.object_like({
                        'Condition': {
                            'StringLike': {
                                'token.actions.githubusercontent.com:sub': 'repo:jblukach/api:*'
                            }
                        }
                    })
                ])
            }
        })


if __name__ == '__main__':
    unittest.main()
