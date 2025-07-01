"""
Unit tests for shared utilities module.

These tests serve as executable specifications for the shared utility functionality.
Each test documents expected behavior and can be read as requirements.

Shared Utilities Requirements:
- Provide consistent delegation checking across all services
- Handle delegation errors uniformly with proper user feedback
- Support both verbose and non-verbose modes
- Return standardized delegation status information
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from modules.utils import printc, get_client
from tests.fixtures.aws_parameters import create_test_params


class TestSharedDelegationLogic:
    """
    SPECIFICATION: Shared delegation checking functionality
    
    The shared delegation logic should:
    1. Check delegation status for any AWS service uniformly
    2. Handle API errors consistently with proper user feedback
    3. Support verbose mode for detailed output
    4. Return standardized delegation status information
    5. Work across all security services with service-specific principals
    """
    
    def test_when_delegation_checker_imported_then_it_should_be_available(self):
        """
        GIVEN: The utils module provides shared delegation functionality
        WHEN: DelegationChecker is imported from utils
        THEN: It should be available for use across all service modules
        
        This test will fail until we implement the shared delegation logic.
        """
        from modules.utils import DelegationChecker
        
        assert hasattr(DelegationChecker, 'check_service_delegation'), "Should provide check_service_delegation method"
        assert hasattr(DelegationChecker, 'handle_delegation_error'), "Should provide handle_delegation_error method"
    
    @patch('modules.utils.get_client')
    def test_when_delegation_check_succeeds_then_proper_status_returned(self, mock_get_client):
        """
        GIVEN: A service is properly delegated to the security account
        WHEN: check_service_delegation is called
        THEN: Should return delegation status with proper success information
        """
        # Arrange - Create mock organizations client with proper delegation
        from unittest.mock import MagicMock
        mock_orgs_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'DelegatedAdministrators': [
                    {
                        'Id': '234567890123',
                        'Name': 'Security-Adm',
                        'Status': 'ACTIVE',
                        'JoinedTimestamp': '2024-01-01T12:00:00Z'
                    }
                ]
            }
        ]
        mock_orgs_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_orgs_client
        
        from modules.utils import DelegationChecker
        
        # Act
        result = DelegationChecker.check_service_delegation(
            service_principal='guardduty.amazonaws.com',
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['is_delegated_to_security'] is True, "Should detect delegation to security account"
        assert result['delegated_admin_account'] == '234567890123', "Should identify correct delegated admin"
        assert result['delegation_check_failed'] is False, "Should not indicate check failure on success"
        assert len(result['errors']) == 0, "Should have no errors on successful check"
    
    @patch('modules.utils.get_client')
    def test_when_delegation_api_fails_then_error_handled_consistently(self, mock_get_client):
        """
        GIVEN: Organizations API fails when checking delegation
        WHEN: check_service_delegation encounters ClientError
        THEN: Should handle error consistently with proper user feedback flags
        """
        # Arrange - Mock get_client to return None (simulating failure)
        mock_get_client.return_value = None
        
        from modules.utils import DelegationChecker
        
        # Act
        result = DelegationChecker.check_service_delegation(
            service_principal='securityhub.amazonaws.com',
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert - Should handle error consistently across all services
        assert result['is_delegated_to_security'] is False, "Should indicate delegation not confirmed"
        assert result['delegation_check_failed'] is True, "Should flag delegation check failure"
        assert len(result['errors']) > 0, "Should record the API error"
        assert 'Failed to get organizations client' in result['errors'][0], "Should include error details"
    
    @patch('modules.utils.get_client')
    def test_when_delegated_to_wrong_account_then_proper_status_returned(self, mock_get_client):
        """
        GIVEN: A service is delegated to a different account than expected
        WHEN: check_service_delegation is called
        THEN: Should return delegation status indicating wrong delegation
        """
        # Arrange - Create mock organizations client with specific delegation
        from unittest.mock import MagicMock
        mock_orgs_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                'DelegatedAdministrators': [
                    {
                        'Id': '999888777666',  # Wrong account
                        'Name': 'Other-Account',
                        'Status': 'ACTIVE',
                        'JoinedTimestamp': '2024-01-01T12:00:00Z'
                    }
                ]
            }
        ]
        mock_orgs_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_orgs_client
        
        from modules.utils import DelegationChecker
        
        # Act
        result = DelegationChecker.check_service_delegation(
            service_principal='detective.amazonaws.com',
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['is_delegated_to_security'] is False, "Should not indicate delegation to security account"
        assert result['delegated_admin_account'] == '999888777666', "Should identify actual delegated admin"
        assert len(result['delegation_details']) == 1, "Should include delegation details"
        assert result['delegation_details'][0]['Id'] == '999888777666', "Should include details about wrong delegation"
        assert result['delegation_check_failed'] is False, "Should not indicate check failure - delegation exists but wrong"
    
    @patch('modules.utils.get_client')
    def test_when_no_delegation_exists_then_proper_status_returned(self, mock_get_client):
        """
        GIVEN: No delegation exists for the service
        WHEN: check_service_delegation is called
        THEN: Should return delegation status indicating no delegation
        """
        # Arrange - Create mock organizations client with no delegations
        from unittest.mock import MagicMock
        mock_orgs_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {'DelegatedAdministrators': []}  # No delegated administrators
        ]
        mock_orgs_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_orgs_client
        
        from modules.utils import DelegationChecker
        
        # Act
        result = DelegationChecker.check_service_delegation(
            service_principal='inspector2.amazonaws.com',
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['is_delegated_to_security'] is False, "Should indicate no delegation to security account"
        assert result['delegated_admin_account'] is None, "Should have no delegated admin"
        assert result['delegation_check_failed'] is False, "Should not indicate check failure - just no delegation"
        assert len(result['errors']) == 0, "Should have no errors for successful check with no delegation"
    
    def test_when_handle_delegation_error_called_then_consistent_error_structure_returned(self):
        """
        GIVEN: A delegation check error needs to be handled
        WHEN: handle_delegation_error is called with error details
        THEN: Should return consistent error structure for integration into service status
        """
        from modules.utils import DelegationChecker
        from botocore.exceptions import ClientError
        
        # Arrange
        error = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='ListDelegatedAdministrators'
        )
        
        # Act
        result = DelegationChecker.handle_delegation_error(error, 'GuardDuty')
        
        # Assert
        assert 'error_message' in result, "Should provide formatted error message"
        assert 'needs_changes' in result, "Should indicate if this needs user attention"
        assert 'issues' in result, "Should provide human-readable issues list"
        assert 'actions' in result, "Should provide recommended actions"
        assert result['needs_changes'] is True, "Should flag delegation errors as needing attention"
        assert 'GuardDuty' in result['error_message'], "Should include service name in error message"
        assert 'Organizations API' in ' '.join(result['actions']), "Should recommend checking Organizations API permissions"


class TestAnomalousRegionDetectionEnhancements:
    """Test enhanced anomalous region detection with account-level details."""
    
    @patch('boto3.client')
    def test_get_unexpected_aws_regions_eliminates_boilerplate(self, mock_boto_client):
        """
        GIVEN: A list of expected regions
        WHEN: get_unexpected_aws_regions is called
        THEN: Should return regions that are not in the expected list
        
        This tests the shared utility that eliminates boilerplate across services.
        """
        from modules.utils import get_unexpected_aws_regions
        
        # Mock EC2 client
        mock_ec2_client = MagicMock()
        mock_boto_client.return_value = mock_ec2_client
        
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'us-west-2'},
                {'RegionName': 'eu-west-1'},
                {'RegionName': 'ap-southeast-1'},
                {'RegionName': 'ca-central-1'}
            ]
        }
        
        # Act
        unexpected_regions = get_unexpected_aws_regions(['us-east-1', 'us-west-2'])
        
        # Assert - Should return regions not in expected list
        assert 'eu-west-1' in unexpected_regions
        assert 'ap-southeast-1' in unexpected_regions
        assert 'ca-central-1' in unexpected_regions
        assert 'us-east-1' not in unexpected_regions
        assert 'us-west-2' not in unexpected_regions
        assert len(unexpected_regions) == 3
    
    @patch('modules.utils.get_client')
    def test_anomalous_region_detection_includes_account_details(self, mock_get_client, mock_aws_services):
        """
        GIVEN: Anomalous service activations exist with account-level details
        WHEN: anomalous region detection runs
        THEN: Should return account details for better security actionability
        
        This addresses the user's specific request for account-level visibility.
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mock clients
        mock_ec2_client = MagicMock()
        mock_guardduty_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'guardduty':
                return mock_guardduty_client
            return MagicMock()
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 to return regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'ap-southeast-1'}
            ]
        }
        
        # Mock GuardDuty to show detectors in unexpected region
        mock_guardduty_client.list_detectors.return_value = {
            'DetectorIds': ['detector123']
        }
        mock_guardduty_client.get_detector.return_value = {
            'Status': 'ENABLED',
            'FindingPublishingFrequency': 'FIFTEEN_MINUTES'
        }
        mock_guardduty_client.list_members.return_value = {
            'Members': [
                {
                    'AccountId': '111111111111',
                    'RelationshipStatus': 'ENABLED',
                    'InvitedAt': '2024-01-15T10:30:00.000Z'
                },
                {
                    'AccountId': '222222222222',
                    'RelationshipStatus': 'ENABLED',
                    'InvitedAt': '2024-01-15T10:30:00.000Z'
                }
            ]
        }
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='guardduty',
            expected_regions=['us-east-1'],  # ap-southeast-1 is unexpected
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert - Should find anomalous region with account details
        assert len(result) == 1
        anomaly = result[0]
        
        assert anomaly.region == 'ap-southeast-1'
        assert anomaly.resource_count == 1
        assert hasattr(anomaly, 'account_details')
        
        # Check account-level details
        account_details = anomaly.account_details
        assert len(account_details) >= 2  # Admin account + member accounts
        
        # Should include admin account
        admin_accounts = [acc for acc in account_details if acc.get('account_status') == 'ADMIN_ACCOUNT']
        assert len(admin_accounts) == 1
        assert admin_accounts[0]['account_id'] == '123456789012'
        
        # Should include member accounts with specific IDs
        member_accounts = [acc for acc in account_details if acc.get('account_id') in ['111111111111', '222222222222']]
        assert len(member_accounts) == 2
        
        # Each account should have actionable details
        for account in account_details:
            assert 'account_id' in account, "Should include account ID for action"
            assert 'account_status' in account, "Should include account status"
            assert 'detector_status' in account, "Should include detector status"
    
    @patch('modules.utils.get_client')
    def test_security_hub_anomalous_region_detection_includes_account_details(self, mock_get_client, mock_aws_services):
        """
        GIVEN: Security Hub is active in unexpected regions with member accounts
        WHEN: anomalous region detection runs for Security Hub
        THEN: Should return account details showing which accounts have Security Hub enabled
        
        TDD Red phase - this test should initially fail until we enhance Security Hub.
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mock clients
        mock_ec2_client = MagicMock()
        mock_securityhub_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'securityhub':
                return mock_securityhub_client
            return MagicMock()
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 to return regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'eu-west-3'}
            ]
        }
        
        # Mock Security Hub to show hub active in unexpected region
        mock_securityhub_client.describe_hub.return_value = {
            'HubArn': 'arn:aws:securityhub:eu-west-3:123456789012:hub/default',
            'SubscribedAt': '2024-01-15T10:30:00.000Z',
            'AutoEnableControls': True
        }
        
        # Mock Security Hub members to show account details
        mock_securityhub_client.list_members.return_value = {
            'Members': [
                {
                    'AccountId': '111111111111',
                    'MemberStatus': 'ENABLED',
                    'InvitedAt': '2024-01-15T10:30:00.000Z',
                    'UpdatedAt': '2024-01-15T11:00:00.000Z'
                },
                {
                    'AccountId': '222222222222', 
                    'MemberStatus': 'ENABLED',
                    'InvitedAt': '2024-01-15T10:30:00.000Z',
                    'UpdatedAt': '2024-01-15T11:00:00.000Z'
                }
            ]
        }
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='security_hub',
            expected_regions=['us-east-1'],  # eu-west-3 is unexpected
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert - Should find anomalous region with account details
        assert len(result) == 1
        anomaly = result[0]
        
        assert anomaly.region == 'eu-west-3'
        assert anomaly.resource_count == 1
        assert hasattr(anomaly, 'account_details')
        
        # Check account-level details
        account_details = anomaly.account_details
        assert len(account_details) >= 2  # Admin account + member accounts
        
        # Should include admin account details
        admin_accounts = [acc for acc in account_details if acc.get('account_id') == '123456789012']
        assert len(admin_accounts) == 1
        assert admin_accounts[0]['account_status'] == 'ADMIN_ACCOUNT'
        
        # Should include member accounts with specific IDs
        member_accounts = [acc for acc in account_details if acc.get('account_id') in ['111111111111', '222222222222']]
        assert len(member_accounts) == 2
        
        # Each account should have actionable details
        for account in account_details:
            assert 'account_id' in account, "Should include account ID for action"
            # Admin accounts have 'account_status', member accounts have 'member_status'
            assert 'account_status' in account or 'member_status' in account, "Should include account/member status"
            assert 'hub_status' in account, "Should include Security Hub status"
    
    @patch('modules.utils.get_client')
    def test_detective_anomalous_region_detection_includes_account_details(self, mock_get_client, mock_aws_services):
        """
        GIVEN: Detective is active in unexpected regions with investigation graphs and member accounts
        WHEN: anomalous region detection runs for Detective
        THEN: Should return account details showing which accounts are in Detective graphs
        
        TDD Red phase - this test should initially fail until we enhance Detective.
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mock clients
        mock_ec2_client = MagicMock()
        mock_detective_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'detective':
                return mock_detective_client
            return MagicMock()
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 to return regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'ca-central-1'}
            ]
        }
        
        # Mock Detective to show graphs active in unexpected region
        mock_detective_client.list_graphs.return_value = {
            'GraphList': [
                {
                    'Arn': 'arn:aws:detective:ca-central-1:123456789012:graph/123456789012',
                    'CreatedTime': '2024-01-15T10:30:00.000Z'
                }
            ]
        }
        
        # Mock Detective members to show account details
        mock_paginator = MagicMock()
        mock_detective_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'MemberDetails': [
                    {
                        'AccountId': '111111111111',
                        'Status': 'ENABLED',
                        'InvitedTime': '2024-01-15T10:30:00.000Z'
                    },
                    {
                        'AccountId': '222222222222',
                        'Status': 'ENABLED', 
                        'InvitedTime': '2024-01-15T10:30:00.000Z'
                    }
                ]
            }
        ]
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='detective',
            expected_regions=['us-east-1'],  # ca-central-1 is unexpected
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert - Should find anomalous region with account details
        assert len(result) == 1
        anomaly = result[0]
        
        assert anomaly.region == 'ca-central-1'
        assert anomaly.resource_count == 1
        assert hasattr(anomaly, 'account_details')
        
        # Check account-level details
        account_details = anomaly.account_details
        assert len(account_details) >= 2  # Admin account + member accounts
        
        # Should include admin account details
        admin_accounts = [acc for acc in account_details if acc.get('account_id') == '123456789012']
        assert len(admin_accounts) == 1
        assert admin_accounts[0]['account_status'] == 'ADMIN_ACCOUNT'
        
        # Should include member accounts with specific IDs
        member_accounts = [acc for acc in account_details if acc.get('account_id') in ['111111111111', '222222222222']]
        assert len(member_accounts) == 2
        
        # Each account should have actionable details
        for account in account_details:
            assert 'account_id' in account, "Should include account ID for action"
            # Admin accounts have 'account_status', member accounts have 'member_status'
            assert 'account_status' in account or 'member_status' in account, "Should include account/member status"
            assert 'service_status' in account or 'member_status' in account, "Should include service status"
    
    @patch('modules.utils.get_client')
    def test_access_analyzer_anomalous_region_detection_includes_account_details(self, mock_get_client, mock_aws_services):
        """
        GIVEN: Access Analyzer is active in unexpected regions with analyzers
        WHEN: anomalous region detection runs for Access Analyzer
        THEN: Should return account details showing which accounts have analyzers
        
        TDD Red phase - this test should initially fail until we enhance Access Analyzer.
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mock clients
        mock_ec2_client = MagicMock()
        mock_analyzer_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'accessanalyzer':
                return mock_analyzer_client
            return MagicMock()
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 to return regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'ap-southeast-2'}
            ]
        }
        
        # Mock Access Analyzer to show analyzers active in unexpected region
        mock_paginator = MagicMock()
        mock_analyzer_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'analyzers': [
                    {
                        'name': 'external-access-analyzer',
                        'arn': 'arn:aws:access-analyzer:ap-southeast-2:123456789012:analyzer/external-access-analyzer',
                        'type': 'ORGANIZATION',
                        'status': 'ACTIVE',
                        'createdAt': '2024-01-15T10:30:00.000Z'
                    },
                    {
                        'name': 'unused-access-analyzer',
                        'arn': 'arn:aws:access-analyzer:ap-southeast-2:123456789012:analyzer/unused-access-analyzer',
                        'type': 'ORGANIZATION_UNUSED_ACCESS',
                        'status': 'ACTIVE',
                        'createdAt': '2024-01-15T10:30:00.000Z'
                    }
                ]
            }
        ]
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='access_analyzer',
            expected_regions=['us-east-1'],  # ap-southeast-2 is unexpected
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert - Should find anomalous region with account details
        assert len(result) == 1
        anomaly = result[0]
        
        assert anomaly.region == 'ap-southeast-2'
        assert anomaly.resource_count == 2
        assert hasattr(anomaly, 'account_details')
        
        # Check account-level details
        account_details = anomaly.account_details
        assert len(account_details) >= 1  # At least admin account
        
        # Should include admin account details
        admin_accounts = [acc for acc in account_details if acc.get('account_id') == '123456789012']
        assert len(admin_accounts) == 1
        assert admin_accounts[0]['account_status'] == 'ADMIN_ACCOUNT'
        
        # Each account should have actionable details
        for account in account_details:
            assert 'account_id' in account, "Should include account ID for action"
            assert 'account_status' in account, "Should include account status"
            assert 'analyzer_status' in account, "Should include Access Analyzer status"


class TestAnomalousRegionChecker:
    """Test the shared AnomalousRegionChecker class following DelegationChecker pattern."""
    
    @patch('modules.utils.get_client')
    def test_when_anomalous_region_checker_called_then_follows_delegation_checker_pattern(self, mock_get_client):
        """
        GIVEN: AnomalousRegionChecker should follow DelegationChecker pattern exactly
        WHEN: check_service_anomalous_regions is called
        THEN: Should have same interface pattern as DelegationChecker.check_service_delegation
        """
        from modules.utils import AnomalousRegionChecker
        
        # Act - Check that method exists with expected signature
        method = getattr(AnomalousRegionChecker, 'check_service_anomalous_regions', None)
        
        # Assert
        assert method is not None, "Should provide check_service_anomalous_regions method"
        assert callable(method), "Should be a callable method"
        
        # Verify it's a static method like DelegationChecker
        import inspect
        assert inspect.isfunction(method), "Should be a static method like DelegationChecker"
    
    @patch('modules.utils.get_client')
    def test_when_guardduty_anomalous_regions_checked_then_standardized_structure_returned(self, mock_get_client):
        """
        GIVEN: GuardDuty resources exist in unexpected regions
        WHEN: check_service_anomalous_regions is called for guardduty
        THEN: Should return standardized AnomalousRegionStatus structure
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mocks
        mock_ec2_client = MagicMock()
        mock_guardduty_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'guardduty':
                return mock_guardduty_client
            return None
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'eu-west-1'}  # Unexpected region
            ]
        }
        
        # Mock GuardDuty detector in unexpected region
        mock_guardduty_client.list_detectors.return_value = {
            'DetectorIds': ['detector123']
        }
        mock_guardduty_client.get_detector.return_value = {
            'Status': 'ENABLED',
            'FindingPublishingFrequency': 'FIFTEEN_MINUTES'
        }
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='guardduty',
            expected_regions=['us-east-1'],
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert len(result) == 1
        anomaly = result[0]
        
        # Should have standardized structure
        assert hasattr(anomaly, 'region')
        assert hasattr(anomaly, 'resource_count')
        assert hasattr(anomaly, 'resource_details')
        assert hasattr(anomaly, 'account_details')
        
        assert anomaly.region == 'eu-west-1'
        assert anomaly.resource_count == 1
    
    @patch('modules.utils.get_client')
    def test_when_service_not_found_in_unexpected_regions_then_empty_list_returned(self, mock_get_client):
        """
        GIVEN: No resources exist in unexpected regions
        WHEN: check_service_anomalous_regions is called
        THEN: Should return empty list
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mocks
        mock_ec2_client = MagicMock()
        mock_guardduty_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'guardduty':
                return mock_guardduty_client
            return None
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'eu-west-1'}
            ]
        }
        
        # Mock GuardDuty with no detectors in unexpected region
        mock_guardduty_client.list_detectors.return_value = {
            'DetectorIds': []  # No detectors
        }
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='guardduty',
            expected_regions=['us-east-1'],
            admin_account='123456789012',
            security_account='234567890123',
            verbose=False
        )
        
        # Assert
        assert len(result) == 0
    
    @patch('modules.utils.get_client')
    def test_when_security_hub_anomalous_regions_checked_then_handles_exception_pattern(self, mock_get_client):
        """
        GIVEN: Security Hub uses exception-when-none pattern
        WHEN: check_service_anomalous_regions is called for security_hub
        THEN: Should handle Security Hub's unique API pattern correctly
        """
        from modules.utils import AnomalousRegionChecker
        from botocore.exceptions import ClientError
        
        # Setup mocks
        mock_ec2_client = MagicMock()
        mock_securityhub_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'securityhub':
                return mock_securityhub_client
            return None
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'ap-southeast-1'}
            ]
        }
        
        # Mock Security Hub with hub enabled in unexpected region
        mock_securityhub_client.describe_hub.return_value = {
            'HubArn': 'arn:aws:securityhub:ap-southeast-1:123456789012:hub/default',
            'SubscribedAt': '2024-01-15T10:30:00.000Z',
            'AutoEnableControls': True
        }
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='security_hub',
            expected_regions=['us-east-1'],
            admin_account='123456789012',
            security_account='234567890123',
            verbose=False
        )
        
        # Assert
        assert len(result) == 1
        anomaly = result[0]
        assert anomaly.region == 'ap-southeast-1'
        assert anomaly.resource_count == 1
        assert 'hub_arn' in anomaly.resource_details[0]
    
    @patch('modules.utils.get_client')
    def test_when_access_analyzer_anomalous_regions_checked_then_handles_paginator_pattern(self, mock_get_client):
        """
        GIVEN: Access Analyzer uses paginator pattern
        WHEN: check_service_anomalous_regions is called for access_analyzer
        THEN: Should handle Access Analyzer's paginator API pattern correctly
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mocks
        mock_ec2_client = MagicMock()
        mock_analyzer_client = MagicMock()
        mock_paginator = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'accessanalyzer':
                return mock_analyzer_client
            return None
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'ca-central-1'}
            ]
        }
        
        # Mock Access Analyzer paginator
        mock_analyzer_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'analyzers': [
                    {
                        'name': 'external-analyzer',
                        'type': 'ORGANIZATION',
                        'status': 'ACTIVE'
                    }
                ]
            }
        ]
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='access_analyzer',
            expected_regions=['us-east-1'],
            admin_account='123456789012',
            security_account='234567890123',
            verbose=False
        )
        
        # Assert
        assert len(result) == 1
        anomaly = result[0]
        assert anomaly.region == 'ca-central-1'
        assert anomaly.resource_count == 1
        assert 'analyzer_name' in anomaly.resource_details[0]
    
    @patch('modules.utils.get_client')
    def test_when_inspector_anomalous_regions_checked_then_handles_embedded_accounts_pattern(self, mock_get_client):
        """
        GIVEN: Inspector uses embedded accounts pattern
        WHEN: check_service_anomalous_regions is called for inspector
        THEN: Should handle Inspector's embedded account details correctly
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mocks
        mock_ec2_client = MagicMock()
        mock_inspector_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            elif service == 'inspector2':
                return mock_inspector_client
            return None
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'us-west-1'}
            ]
        }
        
        # Mock Inspector with enabled resources
        mock_inspector_client.batch_get_account_status.return_value = {
            'accounts': [
                {
                    'accountId': '123456789012',
                    'resourceState': {
                        'ECR': {'status': 'ENABLED'},
                        'EC2': {'status': 'ENABLED'}
                    }
                }
            ]
        }
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='inspector',
            expected_regions=['us-east-1'],
            admin_account='123456789012',
            verbose=False
        )
        
        # Assert
        assert len(result) == 1
        anomaly = result[0]
        assert anomaly.region == 'us-west-1'
        assert anomaly.resource_count == 2  # ECR + EC2
        assert len(anomaly.account_details) == 1
        assert anomaly.account_details[0]['account_id'] == '123456789012'
    
    def test_when_unknown_service_name_provided_then_raises_value_error(self):
        """
        GIVEN: Unknown service name is provided
        WHEN: check_service_anomalous_regions is called
        THEN: Should raise ValueError for unknown service
        """
        from modules.utils import AnomalousRegionChecker
        
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown service"):
            AnomalousRegionChecker.check_service_anomalous_regions(
                service_name='unknown_service',
                expected_regions=['us-east-1'],
                admin_account='123456789012'
            )
    
    @patch('modules.utils.get_client')
    def test_when_client_creation_fails_then_gracefully_continues(self, mock_get_client):
        """
        GIVEN: Client creation fails for some regions
        WHEN: check_service_anomalous_regions encounters client failures
        THEN: Should gracefully continue with other regions
        """
        from modules.utils import AnomalousRegionChecker
        
        # Setup mocks - EC2 succeeds, service client fails
        mock_ec2_client = MagicMock()
        
        def mock_client_factory(service, account_id, region, role_name):
            if service == 'ec2':
                return mock_ec2_client
            else:
                return None  # Simulate client failure
        
        mock_get_client.side_effect = mock_client_factory
        
        # Mock EC2 regions
        mock_ec2_client.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'eu-west-1'}
            ]
        }
        
        # Act
        result = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='guardduty',
            expected_regions=['us-east-1'],
            admin_account='123456789012',
            verbose=False
        )
        
        # Assert - Should handle gracefully and return empty list
        assert len(result) == 0


class TestExistingUtilities:
    """
    SPECIFICATION: Existing utility functions should continue working
    
    Regression tests to ensure existing functionality remains intact.
    """
    
    def test_when_printc_called_then_colored_output_formatted(self):
        """
        GIVEN: Need to display colored output
        WHEN: printc is called with color and message
        THEN: Should format output with color codes correctly
        """
        with patch('builtins.print') as mock_print:
            # Act
            printc("TEST_COLOR", "Test message")
            
            # Assert
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Test message" in call_args, "Should include message text"
            assert "TEST_COLOR" in call_args, "Should include color code"
            assert "\033[K" in call_args, "Should include line clearing"
            assert "\033[0m" in call_args, "Should include color reset"
    
    @patch('boto3.client')
    def test_when_get_client_called_then_cross_account_client_created(self, mock_boto_client):
        """
        GIVEN: Need to create cross-account AWS client
        WHEN: get_client is called with account and role details
        THEN: Should perform role assumption and return configured client
        """
        # Arrange
        mock_sts_client = MagicMock()
        mock_service_client = MagicMock()
        mock_boto_client.side_effect = [mock_sts_client, mock_service_client]
        
        mock_sts_client.assume_role.return_value = {
            'Credentials': {
                'AccessKeyId': 'test-key',
                'SecretAccessKey': 'test-secret',
                'SessionToken': 'test-token'
            }
        }
        
        # Act
        result = get_client('guardduty', '234567890123', 'us-east-1', 'AWSControlTowerExecution')
        
        # Assert
        assert result is not None, "Should return configured client"
        mock_sts_client.assume_role.assert_called_once()
        role_arn = mock_sts_client.assume_role.call_args[1]['RoleArn']
        assert '234567890123' in role_arn, "Should use correct account ID in role ARN"
        assert 'AWSControlTowerExecution' in role_arn, "Should use correct role name"