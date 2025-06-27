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

@pytest.fixture
def mock_aws_services():
    """Mock all AWS services used by the security services setup."""
    with mock_aws():
        yield

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