"""
Shared pytest configuration and fixtures for Foundation Security Services Setup tests.

This module provides common test configuration, fixtures, and setup/teardown
functionality following the proven patterns from SOAR testing infrastructure.
"""

import os
import pytest
import boto3
from moto import mock_aws

# Load environment variables from .env.test if available
try:
    from dotenv import load_dotenv
    load_dotenv('.env.test')
except ImportError:
    # python-dotenv not installed, environment should be loaded manually
    pass

# Test configuration from environment variables
TEST_ADMIN_ACCOUNT = os.getenv('TEST_ADMIN_ACCOUNT', '123456789012')
TEST_SECURITY_ACCOUNT = os.getenv('TEST_SECURITY_ACCOUNT', '234567890123')
TEST_ORG_ID = os.getenv('TEST_ORG_ID', 'o-example12345')
TEST_ROOT_OU = os.getenv('TEST_ROOT_OU', 'r-example12345')
TEST_CROSS_ACCOUNT_ROLE = os.getenv('TEST_CROSS_ACCOUNT_ROLE', 'AWSControlTowerExecution')
TEST_REGIONS = os.getenv('TEST_REGIONS', 'us-east-1,us-west-2,eu-west-1').split(',')

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def test_parameters():
    """Standard test parameters for security services setup."""
    return {
        'admin_account': TEST_ADMIN_ACCOUNT,
        'security_account': TEST_SECURITY_ACCOUNT,
        'regions': TEST_REGIONS,
        'cross_account_role': TEST_CROSS_ACCOUNT_ROLE,
        'org_id': TEST_ORG_ID,
        'root_ou': TEST_ROOT_OU
    }

@pytest.fixture
def test_service_flags():
    """Standard service enable/disable flags for testing."""
    return {
        'aws_config': os.getenv('TEST_AWS_CONFIG_ENABLED', 'Yes'),
        'guardduty': os.getenv('TEST_GUARDDUTY_ENABLED', 'Yes'),
        'security_hub': os.getenv('TEST_SECURITY_HUB_ENABLED', 'Yes'),
        'access_analyzer': os.getenv('TEST_ACCESS_ANALYZER_ENABLED', 'Yes'),
        'detective': os.getenv('TEST_DETECTIVE_ENABLED', 'No'),
        'inspector': os.getenv('TEST_INSPECTOR_ENABLED', 'No')
    }

@pytest.fixture(autouse=True)
def mock_aws_services():
    """Mock all AWS services using moto. Auto-applied to ALL tests."""
    with mock_aws():
        # Mock get_client to return moto clients instead of doing real cross-account calls
        from unittest.mock import patch
        import boto3
        
        # Data-driven service configuration - clean and maintainable
        SERVICE_MOCK_CONFIGS = {
            'organizations': {
                'list_delegated_administrators': {'DelegatedAdministrators': []},
                'get_paginator': [{'DelegatedAdministrators': []}]
            },
            'guardduty': {
                'list_detectors': {'DetectorIds': []},
                'get_detector': {'Status': 'ENABLED', 'FindingPublishingFrequency': 'FIFTEEN_MINUTES'},
                'list_members': {'Members': []},
                'get_paginator': []
            },
            'detective': {
                'list_graphs': {'GraphList': []},
                'get_paginator': []
            },
            'securityhub': {
                'describe_hub': Exception('Hub not enabled'),
                'list_members': {'Members': []},
                'get_enabled_standards': {'StandardsSubscriptions': []},
                'list_finding_aggregators': {'FindingAggregators': []},
                'get_paginator': []
            },
            'inspector2': {
                'list_account_permissions': {'permissions': []},
                'batch_get_account_status': {'accounts': []},
                'get_paginator': []
            },
            'accessanalyzer': {
                'get_paginator': []
            },
            'config': {
                'describe_configuration_recorders': {'ConfigurationRecorders': []},
                'describe_delivery_channels': {'DeliveryChannels': []},
                'get_paginator': [{'ConfigRules': []}]
            },
            'ec2': {
                'describe_regions': {
                    'Regions': [
                        {'RegionName': 'us-east-1'},
                        {'RegionName': 'us-west-2'},
                        {'RegionName': 'eu-west-1'}
                    ]
                }
            }
        }
        
        def mock_get_client(service, account_id, region, role_name):
            """Return a pure mock client configured from data."""
            from unittest.mock import MagicMock
            
            client = MagicMock()
            config = SERVICE_MOCK_CONFIGS.get(service, {})
            
            for method_name, response in config.items():
                if method_name == 'get_paginator':
                    # Special handling for paginator
                    paginator = MagicMock()
                    paginator.paginate = MagicMock(return_value=response)
                    client.get_paginator = MagicMock(return_value=paginator)
                elif isinstance(response, Exception):
                    # Handle methods that should raise exceptions
                    setattr(client, method_name, MagicMock(side_effect=response))
                else:
                    # Normal method with return value
                    setattr(client, method_name, MagicMock(return_value=response))
            
            # Make the client more flexible for tests that want to override specific methods
            client._service_name = service
            client._account_id = account_id
            client._region = region
            
            return client
        
        # Patch all the get_client functions across modules
        patches = [
            patch('modules.utils.get_client', side_effect=mock_get_client),
            patch('modules.aws_config.get_client', side_effect=mock_get_client),
            patch('modules.guardduty.get_client', side_effect=mock_get_client),
            patch('modules.security_hub.get_client', side_effect=mock_get_client),
            patch('modules.detective.get_client', side_effect=mock_get_client),
            patch('modules.inspector.get_client', side_effect=mock_get_client),
            patch('modules.access_analyzer.get_client', side_effect=mock_get_client),
        ]
        
        for p in patches:
            p.start()
        
        try:
            yield
        finally:
            for p in patches:
                p.stop()

@pytest.fixture
def sts_client(aws_credentials, mock_aws_services):
    """Mocked STS client for testing cross-account operations."""
    return boto3.client('sts', region_name='us-east-1')

@pytest.fixture
def guardduty_client(aws_credentials, mock_aws_services):
    """Mocked GuardDuty client for testing."""
    return boto3.client('guardduty', region_name='us-east-1')

@pytest.fixture
def security_hub_client(aws_credentials, mock_aws_services):
    """Mocked Security Hub client for testing."""
    return boto3.client('securityhub', region_name='us-east-1')

@pytest.fixture
def detective_client(aws_credentials, mock_aws_services):
    """Mocked Detective client for testing."""
    return boto3.client('detective', region_name='us-east-1')

@pytest.fixture
def inspector_client(aws_credentials, mock_aws_services):
    """Mocked Inspector client for testing."""
    return boto3.client('inspector2', region_name='us-east-1')

@pytest.fixture
def access_analyzer_client(aws_credentials, mock_aws_services):
    """Mocked Access Analyzer client for testing."""
    return boto3.client('accessanalyzer', region_name='us-east-1')

@pytest.fixture
def config_client(aws_credentials, mock_aws_services):
    """Mocked Config client for testing."""
    return boto3.client('config', region_name='us-east-1')

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically set up test environment for all tests."""
    # Ensure clean environment for each test
    original_env = os.environ.copy()
    yield
    # Restore original environment after test
    os.environ.clear()
    os.environ.update(original_env)

# Test markers for different test categories
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests that can be skipped during development")
    config.addinivalue_line("markers", "security: Security-focused tests")