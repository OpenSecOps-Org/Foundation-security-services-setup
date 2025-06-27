"""
Common testing utilities for Foundation Security Services Setup tests.

This module provides helper functions and utilities used across multiple
test suites following SOAR testing patterns.
"""

import json
import boto3
from unittest.mock import patch, MagicMock
from moto import mock_aws


def mock_cross_account_session(account_id, role_name, region='us-east-1'):
    """
    Create a mocked cross-account AWS session for testing.
    
    Args:
        account_id (str): Target account ID
        role_name (str): Role name to assume
        region (str): AWS region
        
    Returns:
        MagicMock: Mocked boto3 session
    """
    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()
    return mock_session


def setup_sts_assume_role_mock(sts_client, account_id, role_name):
    """
    Set up STS assume role mock for cross-account testing.
    
    Args:
        sts_client: Mocked STS client
        account_id (str): Account ID to assume role in
        role_name (str): Role name to assume
    """
    assumed_role_credentials = {
        'Credentials': {
            'AccessKeyId': 'ASSUMED_ACCESS_KEY',
            'SecretAccessKey': 'ASSUMED_SECRET_KEY',
            'SessionToken': 'ASSUMED_SESSION_TOKEN',
            'Expiration': '2023-12-31T23:59:59Z'
        },
        'AssumedRoleUser': {
            'AssumedRoleId': f'AROATEST123456789012345:{role_name}',
            'Arn': f'arn:aws:sts::{account_id}:assumed-role/{role_name}/test-session'
        }
    }
    
    sts_client.assume_role.return_value = assumed_role_credentials
    return assumed_role_credentials


def create_mock_service_client(service_name, responses=None):
    """
    Create a mock AWS service client with predefined responses.
    
    Args:
        service_name (str): AWS service name
        responses (dict): Custom responses for service methods
        
    Returns:
        MagicMock: Mocked service client
    """
    mock_client = MagicMock()
    
    if responses:
        for method, response in responses.items():
            getattr(mock_client, method).return_value = response
    
    return mock_client


def assert_log_message_contains(caplog, level, message_substring):
    """
    Assert that a log message contains a specific substring.
    
    Args:
        caplog: pytest caplog fixture
        level (str): Log level (INFO, WARNING, ERROR, etc.)
        message_substring (str): Substring to search for in log messages
    """
    found = False
    for record in caplog.records:
        if record.levelname == level and message_substring in record.message:
            found = True
            break
    
    assert found, f"Log message containing '{message_substring}' not found at {level} level"


def assert_service_enabled_correctly(result, service_name):
    """
    Assert that a service was enabled correctly based on standard result format.
    
    Args:
        result: Service setup function result
        service_name (str): Name of the service for error messages
    """
    assert result is True, f"{service_name} setup should return True on success"


def assert_service_skipped_correctly(result, service_name):
    """
    Assert that a service was skipped correctly (disabled or existing config).
    
    Args:
        result: Service setup function result
        service_name (str): Name of the service for error messages
    """
    assert result is True, f"{service_name} should return True even when skipped"


def create_test_argv(params, service_flags, dry_run=False, verbose=False):
    """
    Create sys.argv list for testing main script argument parsing.
    
    Args:
        params (dict): AWS parameters dictionary
        service_flags (dict): Service enable/disable flags
        dry_run (bool): Enable dry run mode
        verbose (bool): Enable verbose mode
        
    Returns:
        list: sys.argv formatted argument list
    """
    argv = ['setup-security-services']
    
    # Add service flags
    for service, enabled in service_flags.items():
        argv.extend([f'--{service.replace("_", "-")}', enabled])
    
    # Add AWS parameters
    argv.extend(['--admin-account', params['admin_account']])
    argv.extend(['--security-account', params['security_account']])
    argv.extend(['--regions', ','.join(params['regions'])])
    argv.extend(['--cross-account-role', params['cross_account_role']])
    argv.extend(['--org-id', params['org_id']])
    argv.extend(['--root-ou', params['root_ou']])
    
    # Add optional flags
    if dry_run:
        argv.append('--dry-run')
    if verbose:
        argv.append('--verbose')
    
    return argv


def mock_existing_aws_resources(service_name, client_mock, exists=True):
    """
    Mock existing AWS resources for testing configuration preservation.
    
    Args:
        service_name (str): AWS service name
        client_mock: Mocked AWS service client
        exists (bool): Whether resources should exist
    """
    if service_name == 'guardduty':
        if exists:
            client_mock.list_detectors.return_value = {'DetectorIds': ['test-detector-123']}
            client_mock.get_administrator_account.return_value = {
                'Administrator': {'AccountId': '123456789012'}
            }
        else:
            client_mock.list_detectors.return_value = {'DetectorIds': []}
            from botocore.exceptions import ClientError
            client_mock.get_administrator_account.side_effect = ClientError(
                {'Error': {'Code': 'BadRequestException'}}, 'GetAdministratorAccount'
            )
    
    elif service_name == 'security_hub':
        if exists:
            client_mock.describe_hub.return_value = {'HubArn': 'test-hub-arn'}
            client_mock.list_configuration_policies.return_value = {
                'ConfigurationPolicySummaryList': [
                    {'Id': 'test-policy-1', 'Name': 'PROD-Policy'},
                    {'Id': 'test-policy-2', 'Name': 'DEV-Policy'}
                ]
            }
        else:
            from botocore.exceptions import ClientError
            client_mock.describe_hub.side_effect = ClientError(
                {'Error': {'Code': 'InvalidAccessException'}}, 'DescribeHub'
            )
            client_mock.list_configuration_policies.return_value = {
                'ConfigurationPolicySummaryList': []
            }
    
    # Add more service mocking as needed


class OutputCapture:
    """Helper class to capture and validate script output."""
    
    def __init__(self):
        self.stdout_lines = []
        self.stderr_lines = []
    
    def capture_stdout(self, line):
        """Capture stdout line."""
        self.stdout_lines.append(line)
    
    def capture_stderr(self, line):
        """Capture stderr line.""" 
        self.stderr_lines.append(line)
    
    def assert_contains(self, text, in_stdout=True):
        """Assert that output contains specific text."""
        lines = self.stdout_lines if in_stdout else self.stderr_lines
        found = any(text in line for line in lines)
        output_type = "stdout" if in_stdout else "stderr"
        assert found, f"Text '{text}' not found in {output_type}"
    
    def assert_not_contains(self, text, in_stdout=True):
        """Assert that output does not contain specific text."""
        lines = self.stdout_lines if in_stdout else self.stderr_lines
        found = any(text in line for line in lines)
        output_type = "stdout" if in_stdout else "stderr"
        assert not found, f"Text '{text}' unexpectedly found in {output_type}"