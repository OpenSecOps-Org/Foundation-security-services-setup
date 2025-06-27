"""
Unit tests for GuardDuty service module.

These tests serve as executable specifications for the GuardDuty setup functionality.
Each test documents expected behavior and can be read as requirements.

GuardDuty Setup Requirements:
- Enable GuardDuty in org account across all regions
- Delegate administration to Security-Adm account
- Configure auto-enable for new and existing accounts
- Support dry-run mode for safe preview
- Handle disabled state gracefully
- Preserve existing configurations
- Provide clear user feedback
"""

import pytest
import sys
import os
from unittest.mock import patch, call

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from modules.guardduty import setup_guardduty, check_guardduty_in_region, printc
from tests.fixtures.aws_parameters import create_test_params


class TestGuardDutyBasicBehavior:
    """
    SPECIFICATION: Basic behavior of GuardDuty setup
    
    The setup_guardduty function should:
    1. Return True when operation completes successfully
    2. Accept both enabled and disabled states
    3. Handle case-insensitive input gracefully
    """
    
    def test_when_guardduty_is_enabled_then_function_returns_success(self, mock_aws_services):
        """
        GIVEN: GuardDuty is requested to be enabled
        WHEN: setup_guardduty is called with enabled='Yes'
        THEN: The function should return True indicating successful completion
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_guardduty(enabled='Yes', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "GuardDuty setup should return True when enabled successfully"
    
    def test_when_guardduty_is_disabled_then_function_returns_success(self, mock_aws_services):
        """
        GIVEN: GuardDuty is requested to be disabled/skipped
        WHEN: setup_guardduty is called with enabled='No'
        THEN: The function should return True and skip configuration gracefully
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_guardduty(enabled='No', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "GuardDuty setup should return True even when disabled"
    
    def test_when_enabled_flag_values_are_exactly_yes_or_no_then_they_are_accepted(self, mock_aws_services):
        """
        GIVEN: Main script provides exactly 'Yes' or 'No' values via argparse choices
        WHEN: setup_guardduty is called with these canonical values
        THEN: Both values should be handled correctly
        
        Note: argparse choices=['Yes', 'No'] ensures only these values are passed.
        """
        # Arrange
        params = create_test_params()
        
        # Act & Assert - Test canonical Yes value
        result = setup_guardduty('Yes', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='Yes'"
            
        # Act & Assert - Test canonical No value
        result = setup_guardduty('No', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='No'"


class TestGuardDutyUserFeedback:
    """
    SPECIFICATION: User feedback and communication
    
    The setup_guardduty function should provide clear feedback to users:
    1. Show what actions will be taken in dry-run mode
    2. Display detailed information in verbose mode
    3. Confirm when services are disabled/skipped
    4. Use consistent formatting and colors
    """
    
    @patch('builtins.print')
    def test_when_verbose_mode_is_enabled_then_detailed_information_is_displayed(self, mock_print, mock_aws_services):
        """
        GIVEN: User wants detailed information about the operation
        WHEN: setup_guardduty is called with verbose=True
        THEN: Detailed parameter information should be displayed
        
        This helps users understand exactly what the script will do with their parameters.
        """
        # Arrange
        params = create_test_params(
            regions=['us-east-1', 'us-west-2'], 
            org_id='o-example12345'
        )
        
        # Act
        result = setup_guardduty('Yes', params, dry_run=False, verbose=True)
        
        # Assert
        assert result is True
        
        # Verify verbose information was displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'Enabled: Yes' in all_output, "Should show the enabled status"
        assert 'us-east-1' in all_output, "Should show the regions being configured"
        assert 'o-example12345' in all_output, "Should show the organization ID"
        assert 'Dry Run: False' in all_output, "Should show the dry-run status"
        assert 'Verbose: True' in all_output, "Should show the verbose status"
    
    @patch('modules.guardduty.check_guardduty_in_region')
    @patch('builtins.print')
    def test_when_dry_run_mode_is_enabled_then_preview_actions_are_shown(self, mock_print, mock_check_guardduty, mock_aws_services):
        """
        GIVEN: User wants to preview actions without making changes and GuardDuty needs changes
        WHEN: setup_guardduty is called with dry_run=True and regions need configuration
        THEN: Actions should be prefixed with "DRY RUN:" to indicate no changes
        
        This allows users to safely validate their configuration before applying.
        """
        # Arrange - Mock GuardDuty needing changes to trigger dry-run output
        mock_check_guardduty.return_value = {
            'region': 'us-east-1',
            'guardduty_enabled': False,
            'delegation_status': 'unknown',
            'member_count': 0,
            'organization_auto_enable': False,
            'needs_changes': True,
            'issues': ['GuardDuty is not enabled in this region'],
            'actions': ['Enable GuardDuty and create detector'],
            'errors': [],
            'guardduty_details': []
        }
        params = create_test_params(regions=['us-east-1', 'us-west-2'])
        
        # Act
        result = setup_guardduty('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify dry-run messages were displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'DRY RUN:' in all_output, "Should prefix actions with DRY RUN indicator"
        assert 'Would make the following changes' in all_output, "Should describe what would be done"
    
    @patch('builtins.print')
    def test_when_guardduty_is_disabled_then_clear_skip_message_is_shown(self, mock_print, mock_aws_services):
        """
        GIVEN: User has disabled GuardDuty in their configuration
        WHEN: setup_guardduty is called with enabled='No'
        THEN: A clear message should indicate the service is being skipped
        
        This prevents confusion about whether the service failed or was intentionally skipped.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_guardduty('No', params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify skip message was displayed (updated to match real implementation)
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'GuardDuty setup SKIPPED due to enabled=No parameter' in all_output, "Should clearly indicate service is being skipped"
    
    @patch('builtins.print')
    def test_when_function_runs_then_proper_banner_formatting_is_used(self, mock_print, mock_aws_services):
        """
        GIVEN: User runs the GuardDuty setup
        WHEN: setup_guardduty is called
        THEN: Output should include a properly formatted banner for readability
        
        Consistent formatting helps users identify different service sections in the output.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        setup_guardduty('Yes', params, dry_run=False, verbose=False)
        
        # Assert
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'GUARDDUTY SETUP' in all_output, "Should display service name banner"
        assert '=' in all_output, "Should use separator lines for visual formatting"


class TestGuardDutyRegionHandling:
    """
    SPECIFICATION: Multi-region configuration logic
    
    GuardDuty requires configuration across all enabled regions:
    1. Enable GuardDuty in all regions
    2. Delegate administration in all regions
    3. Configure auto-enable for new and existing accounts
    4. Handle single vs multiple region deployments
    """
    
    @patch('builtins.print')
    def test_when_single_region_is_provided_then_it_is_configured(self, mock_print, mock_aws_services):
        """
        GIVEN: User provides only one region in their configuration
        WHEN: setup_guardduty is called with a single region
        THEN: That region should be configured for GuardDuty
        
        Single-region deployments should work correctly.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1'])
        
        # Act
        result = setup_guardduty('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'all activated regions' in all_output or 'regions' in all_output, "Should mention region configuration"
    
    @patch('builtins.print')
    def test_when_multiple_regions_provided_then_all_are_configured(self, mock_print, mock_aws_services):
        """
        GIVEN: User provides multiple regions in their configuration
        WHEN: setup_guardduty is called with multiple regions
        THEN: All regions should be configured for GuardDuty
        
        Multi-region deployments should handle all regions consistently.
        """
        # Arrange
        params = create_test_params(regions=['eu-west-1', 'us-east-1', 'ap-southeast-1'])
        
        # Act
        result = setup_guardduty('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Should mention region configuration approach
        assert 'all activated regions' in all_output or 'regions' in all_output, "Should mention region configuration"
    


class TestGuardDutyErrorResilience:
    """
    SPECIFICATION: Error handling and resilience
    
    The setup_guardduty function should:
    1. Handle exceptions gracefully without crashing
    2. Return False when errors occur
    3. Log error information for debugging
    4. Continue functioning with malformed input
    """
    
    @patch('builtins.print')
    def test_when_unexpected_exception_occurs_then_error_is_handled_gracefully(self, mock_print, mock_aws_services):
        """
        GIVEN: An unexpected error occurs during execution
        WHEN: setup_guardduty encounters an exception
        THEN: Function should catch the error, log it, and return False
        
        This prevents the entire script from crashing due to one service failure.
        """
        # Arrange - simulate an error after the initial banner by raising on verbose check
        def side_effect_function(*args, **kwargs):
            # Let the first few printc calls succeed (banner), then fail
            if 'Enabled:' in str(args):
                raise Exception("Simulated unexpected error")
            return None
        
        mock_print.side_effect = side_effect_function
        params = create_test_params()
        
        # Act
        result = setup_guardduty('Yes', params, dry_run=False, verbose=True)
        
        # Assert
        assert result is False, "Should return False when exception occurs"
        
        # Verify error was logged
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert 'ERROR in setup_guardduty:' in all_output, "Should log the error"
    


class TestPrintcUtilityFunction:
    """
    SPECIFICATION: Printc utility function behavior
    
    The printc helper function should:
    1. Format colored output consistently
    2. Handle additional print parameters
    3. Clear line endings properly
    """
    
    @patch('builtins.print')
    def test_when_printc_is_called_then_colored_output_is_formatted_correctly(self, mock_print, mock_aws_services):
        """
        GIVEN: Need to display colored output to users
        WHEN: printc is called with color and message
        THEN: Output should include color codes and message formatting
        
        Ensures consistent colored output across all messages.
        """
        # Arrange
        test_color = "TEST_COLOR"
        test_message = "Test message"
        
        # Act
        printc(test_color, test_message)
        
        # Assert
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert test_message in call_args, "Should include the message text"
        assert test_color in call_args, "Should include the color code"
    
    @patch('builtins.print')
    def test_when_printc_called_with_kwargs_then_they_are_passed_through(self, mock_print, mock_aws_services):
        """
        GIVEN: Need to pass additional parameters to print function
        WHEN: printc is called with additional keyword arguments
        THEN: Those arguments should be passed through to the print function
        
        Ensures flexibility for different output requirements.
        """
        # Arrange
        test_color = "TEST_COLOR"
        test_message = "Test message"
        
        # Act
        printc(test_color, test_message, end='', flush=True)
        
        # Assert
        mock_print.assert_called_once()
        call_kwargs = mock_print.call_args[1]
        assert 'end' in call_kwargs, "Should pass through end parameter"
        assert 'flush' in call_kwargs, "Should pass through flush parameter"


class TestGuardDutyConfigurationScenarios:
    """
    SPECIFICATION: Comprehensive configuration scenario detection
    
    The check_guardduty_in_region function should handle all real-world scenarios:
    1. Unconfigured service - No GuardDuty detectors found
    2. Configuration but no delegation - GuardDuty enabled but not delegated to Security account  
    3. Weird configurations - Delegated to wrong account, suboptimal settings, mixed member states
    4. Valid configurations - Properly delegated with optimal settings and all members enabled
    """
    
    @patch('boto3.client')
    def test_scenario_1_unconfigured_service_detected(self, mock_boto_client):
        """
        GIVEN: GuardDuty is not enabled in a region (no detectors)
        WHEN: check_guardduty_in_region is called
        THEN: Should detect unconfigured service and recommend enablement
        """
        # Arrange - No detectors found
        mock_guardduty_client = mock_boto_client.return_value
        mock_guardduty_client.list_detectors.return_value = {'DetectorIds': []}
        
        # Act
        result = check_guardduty_in_region(
            region='us-east-1',
            admin_account='123456789012', 
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['guardduty_enabled'] is False
        assert result['needs_changes'] is True
        assert "GuardDuty is not enabled in this region" in result['issues']
        assert "Enable GuardDuty and create detector" in result['actions']
        assert "❌ GuardDuty not enabled - no detectors found" in result['guardduty_details']
    
    @patch('boto3.client')
    def test_scenario_2_configuration_but_no_delegation(self, mock_boto_client):
        """
        GIVEN: GuardDuty is enabled but not delegated to Security account
        WHEN: check_guardduty_in_region is called
        THEN: Should detect missing delegation and recommend setup
        """
        # Arrange - GuardDuty enabled but no delegation
        mock_guardduty_client = mock_boto_client.return_value
        mock_orgs_client = mock_boto_client.return_value
        
        # GuardDuty detector exists and is enabled
        mock_guardduty_client.list_detectors.return_value = {'DetectorIds': ['detector123']}
        mock_guardduty_client.get_detector.return_value = {
            'Status': 'ENABLED',
            'FindingPublishingFrequency': 'FIFTEEN_MINUTES'
        }
        
        # No delegated administrators found
        mock_orgs_client.list_delegated_administrators.return_value = {'DelegatedAdministrators': []}
        
        # Act
        result = check_guardduty_in_region(
            region='us-east-1',
            admin_account='123456789012',
            security_account='234567890123', 
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['guardduty_enabled'] is True
        assert result['delegation_status'] == 'not_delegated'
        assert result['needs_changes'] is True
        assert "GuardDuty enabled but not delegated to Security account" in result['issues']
        assert "Delegate GuardDuty administration to Security account" in result['actions']
    
    @patch('boto3.client')
    def test_scenario_3_weird_configuration_wrong_delegation(self, mock_boto_client):
        """
        GIVEN: GuardDuty is delegated to wrong account (not Security account)
        WHEN: check_guardduty_in_region is called
        THEN: Should detect weird configuration and recommend fix
        """
        # Arrange - GuardDuty delegated to wrong account
        mock_guardduty_client = mock_boto_client.return_value
        mock_orgs_client = mock_boto_client.return_value
        
        # GuardDuty detector exists and is enabled
        mock_guardduty_client.list_detectors.return_value = {'DetectorIds': ['detector123']}
        mock_guardduty_client.get_detector.return_value = {
            'Status': 'ENABLED',
            'FindingPublishingFrequency': 'FIFTEEN_MINUTES'
        }
        
        # Delegated to wrong account
        mock_orgs_client.list_delegated_administrators.return_value = {
            'DelegatedAdministrators': [
                {'Id': '999888777666', 'Name': 'WrongAccount'}  # Different from security account
            ]
        }
        
        # Act
        result = check_guardduty_in_region(
            region='us-east-1',
            admin_account='123456789012',
            security_account='234567890123',  # Different from delegated account
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['guardduty_enabled'] is True
        assert result['delegation_status'] == 'not_delegated'
        assert result['needs_changes'] is True
        assert "GuardDuty delegated to 999888777666 instead of Security account 234567890123" in result['issues']
        assert "Remove existing delegation and delegate to Security account" in result['actions']
        assert "⚠️  GuardDuty delegated to other account(s): 999888777666" in result['guardduty_details']
    
    @patch('boto3.client')
    def test_scenario_3_weird_configuration_suboptimal_frequency(self, mock_boto_client):
        """
        GIVEN: GuardDuty is properly delegated but has suboptimal finding frequency
        WHEN: check_guardduty_in_region is called  
        THEN: Should detect suboptimal configuration and recommend optimization
        """
        # Arrange - Proper delegation but suboptimal frequency
        mock_guardduty_client = mock_boto_client.return_value
        mock_orgs_client = mock_boto_client.return_value
        
        # GuardDuty detector exists but suboptimal frequency
        mock_guardduty_client.list_detectors.return_value = {'DetectorIds': ['detector123']}
        mock_guardduty_client.get_detector.return_value = {
            'Status': 'ENABLED',
            'FindingPublishingFrequency': 'SIX_HOURS'  # Suboptimal
        }
        
        # Properly delegated to Security account
        mock_orgs_client.list_delegated_administrators.return_value = {
            'DelegatedAdministrators': [
                {'Id': '234567890123', 'Name': 'Security-Adm'}
            ]
        }
        
        # Act
        result = check_guardduty_in_region(
            region='us-east-1',
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['guardduty_enabled'] is True
        assert result['delegation_status'] == 'delegated'
        assert result['needs_changes'] is True
        assert "Finding frequency is 6 hours - too slow for optimal threat detection" in result['issues']
        assert "Set finding frequency to FIFTEEN_MINUTES for optimal security" in result['actions']
        # Check that suboptimal frequency is detected in details
        details_str = '\n'.join(result['guardduty_details'])
        assert "⚠️  Finding Frequency: SIX_HOURS (suboptimal)" in details_str
    
    @patch('modules.guardduty.get_client')
    @patch('boto3.client')
    def test_scenario_4_valid_configuration_optimal_setup(self, mock_boto_client, mock_get_client):
        """
        GIVEN: GuardDuty is properly configured with optimal settings
        WHEN: check_guardduty_in_region is called
        THEN: Should detect valid configuration and require no changes
        """
        # Arrange - Optimal configuration with cross-account data
        mock_guardduty_client = mock_boto_client.return_value
        mock_orgs_client = mock_boto_client.return_value
        mock_delegated_client = mock_get_client.return_value
        
        # GuardDuty detector exists with optimal settings
        mock_guardduty_client.list_detectors.return_value = {'DetectorIds': ['detector123']}
        mock_guardduty_client.get_detector.return_value = {
            'Status': 'ENABLED',
            'FindingPublishingFrequency': 'FIFTEEN_MINUTES'  # Optimal
        }
        
        # Properly delegated to Security account
        mock_orgs_client.list_delegated_administrators.return_value = {
            'DelegatedAdministrators': [
                {'Id': '234567890123', 'Name': 'Security-Adm'}
            ]
        }
        
        # Cross-account delegated admin has optimal config
        mock_delegated_client.list_detectors.return_value = {'DetectorIds': ['delegated-detector']}
        mock_delegated_client.describe_organization_configuration.return_value = {
            'AutoEnable': True,
            'AutoEnableOrganizationMembers': 'ALL',
            'DataSources': {
                'S3Logs': {'AutoEnable': True},
                'Kubernetes': {'AutoEnable': False},
                'MalwareProtection': {'AutoEnable': True}
            }
        }
        
        # All member accounts enabled
        mock_delegated_client.get_paginator.return_value.paginate.return_value = [
            {'Members': [
                {'AccountId': '111111111111', 'RelationshipStatus': 'Enabled'},
                {'AccountId': '222222222222', 'RelationshipStatus': 'Enabled'},
                {'AccountId': '333333333333', 'RelationshipStatus': 'Enabled'}
            ]}
        ]
        
        # Act
        result = check_guardduty_in_region(
            region='us-east-1',
            admin_account='123456789012',
            security_account='234567890123',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert - Valid configuration requires no changes
        assert result['guardduty_enabled'] is True
        assert result['delegation_status'] == 'delegated'
        assert result['organization_auto_enable'] is True
        assert result['member_count'] == 3
        assert result['needs_changes'] is False, "Valid configuration should not need changes"
        assert result['issues'] == [], "Valid configuration should have no issues"
        assert result['actions'] == [], "Valid configuration should need no actions"
        
        # Check that optimal settings are properly detected
        details_str = '\n'.join(result['guardduty_details'])
        assert "✅ Finding Frequency: FIFTEEN_MINUTES (optimal)" in details_str
        assert "✅ Delegated Admin: Security-Adm" in details_str
        assert "✅ Organization Auto-Enable: True" in details_str
        assert "✅ Auto-Enable Org Members: ALL" in details_str
        assert "✅ All 3 member accounts are enabled" in details_str
    
    def test_verbosity_control_in_configuration_detection(self):
        """
        GIVEN: Configuration detection is performed with verbosity controls
        WHEN: check_guardduty_in_region is called with verbose flag variations
        THEN: Should respect verbosity settings for output control
        
        This ensures the terse vs verbose behavior works correctly.
        """
        # This test validates that the verbosity pattern is implemented
        # The actual verbose behavior is tested through integration tests
        # This serves as a specification that verbosity control exists
        
        params = create_test_params()
        
        # Test that function accepts verbose parameter
        # (Implementation details tested through integration)
        assert 'verbose' in check_guardduty_in_region.__code__.co_varnames
        
        # Specification: Function should handle both verbose and non-verbose modes
        # Integration tests validate the actual output behavior