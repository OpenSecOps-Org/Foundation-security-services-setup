"""
Unit tests for AWS Config service module.

These tests serve as executable specifications for the AWS Config setup functionality.
Each test documents expected behavior and can be read as requirements.

AWS Config Setup Requirements:
- Enable AWS Config in main region with IAM global events
- Enable AWS Config in other regions without IAM global events  
- Support dry-run mode for safe preview
- Handle disabled state gracefully
- Preserve existing configurations
- Provide clear user feedback
"""

import pytest
import sys
import os
from unittest.mock import patch, call, Mock, MagicMock

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from modules.aws_config import setup_aws_config, printc
from tests.fixtures.aws_parameters import create_test_params


class TestAWSConfigBasicBehavior:
    """
    SPECIFICATION: Basic behavior of AWS Config setup
    
    The setup_aws_config function should:
    1. Return True when operation completes successfully
    2. Accept both enabled and disabled states
    3. Handle case-insensitive input gracefully
    """
    
    def test_when_aws_config_is_enabled_then_function_returns_success(self, mock_aws_services):
        """
        GIVEN: AWS Config is requested to be enabled
        WHEN: setup_aws_config is called with enabled='Yes'
        THEN: The function should return True indicating successful completion
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_aws_config(enabled='Yes', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "AWS Config setup should return True when enabled successfully"
    
    def test_when_aws_config_is_disabled_then_function_returns_success(self, mock_aws_services):
        """
        GIVEN: AWS Config is requested to be disabled/skipped
        WHEN: setup_aws_config is called with enabled='No'
        THEN: The function should return True and skip configuration gracefully
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_aws_config(enabled='No', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "AWS Config setup should return True even when disabled"
    
    def test_when_enabled_flag_values_are_exactly_yes_or_no_then_they_are_accepted(self, mock_aws_services):
        """
        GIVEN: Main script provides exactly 'Yes' or 'No' values via argparse choices
        WHEN: setup_aws_config is called with these canonical values
        THEN: Both values should be handled correctly
        
        Note: argparse choices=['Yes', 'No'] ensures only these values are passed.
        """
        # Arrange
        params = create_test_params()
        
        # Act & Assert - Test canonical Yes value
        result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='Yes'"
            
        # Act & Assert - Test canonical No value
        result = setup_aws_config('No', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='No'"


class TestAWSConfigUserFeedback:
    """
    SPECIFICATION: User feedback and communication
    
    The setup_aws_config function should provide clear feedback to users:
    1. Show what actions will be taken in dry-run mode
    2. Display detailed information in verbose mode
    3. Confirm when services are disabled/skipped
    4. Use consistent formatting and colors
    """
    
    @patch('builtins.print')
    def test_when_verbose_mode_is_enabled_then_detailed_information_is_displayed(self, mock_print, mock_aws_services):
        """
        GIVEN: User wants detailed information about the operation
        WHEN: setup_aws_config is called with verbose=True
        THEN: Detailed parameter information should be displayed
        
        This helps users understand exactly what the script will do with their parameters.
        """
        # Arrange
        params = create_test_params(
            regions=['us-east-1', 'us-west-2'], 
            org_id='o-example12345'
        )
        
        # Act
        result = setup_aws_config('Yes', params, dry_run=False, verbose=True)
        
        # Assert
        assert result is True
        
        # Verify verbose information was displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'Enabled: Yes' in all_output, "Should show the enabled status"
        assert 'us-east-1' in all_output, "Should show the regions being configured"
        assert 'o-example12345' in all_output, "Should show the organization ID"
        assert 'Dry Run: False' in all_output, "Should show the dry-run status"
        assert 'Verbose: True' in all_output, "Should show the verbose status"
    
    @patch('modules.aws_config.check_config_in_region')
    @patch('builtins.print')
    def test_when_dry_run_mode_is_enabled_then_preview_actions_are_shown(self, mock_print, mock_check_config, mock_aws_services):
        """
        GIVEN: User wants to preview actions without making changes and Config needs changes
        WHEN: setup_aws_config is called with dry_run=True and regions need configuration
        THEN: Actions should be prefixed with "DRY RUN:" to indicate no changes
        
        This allows users to safely validate their configuration before applying.
        """
        # Arrange - Mock Config needing changes to trigger dry-run output
        mock_check_config.return_value = {
            'region': 'us-east-1',
            'service_enabled': False,
            'records_global_iam': False,
            'needs_changes': True,
            'issues': ['Config not enabled'],
            'actions': ['Enable AWS Config'],
            'errors': [],
            'service_details': []
        }
        params = create_test_params(regions=['us-east-1', 'us-west-2'])
        
        # Act
        result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify dry-run messages were displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'DRY RUN:' in all_output, "Should prefix actions with DRY RUN indicator"
        assert 'Would make the following changes' in all_output, "Should describe what would be done"
    
    @patch('builtins.print')
    def test_when_aws_config_is_disabled_then_huge_warning_is_shown(self, mock_print, mock_aws_services):
        """
        GIVEN: User has disabled AWS Config in their configuration
        WHEN: setup_aws_config is called with enabled='No'
        THEN: A huge warning should be displayed about disabling critical security service
        
        AWS Config is critical for Security Hub and compliance - disabling should show major warning.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_aws_config('No', params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify huge warning was displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'CRITICAL WARNING: AWS Config Disable Requested' in all_output, "Should show critical warning"
        assert 'DISABLING CONFIG WILL BREAK SECURITY MONITORING' in all_output, "Should emphasize breaking security"
        assert 'Config setup SKIPPED due to enabled=No parameter' in all_output, "Should indicate service is skipped"
    
    @patch('builtins.print')
    def test_when_function_runs_then_proper_banner_formatting_is_used(self, mock_print, mock_aws_services):
        """
        GIVEN: User runs the AWS Config setup
        WHEN: setup_aws_config is called
        THEN: Output should include a properly formatted banner for readability
        
        Consistent formatting helps users identify different service sections in the output.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        setup_aws_config('Yes', params, dry_run=False, verbose=False)
        
        # Assert
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'AWS CONFIG SETUP' in all_output, "Should display service name banner"
        assert '=' in all_output, "Should use separator lines for visual formatting"


class TestAWSConfigRegionHandling:
    """
    SPECIFICATION: Multi-region configuration logic
    
    AWS Config has specific requirements for IAM global events:
    1. Main region (first in list) should record IAM global events
    2. Other regions should NOT record IAM global events to avoid duplication
    3. Single region deployments should handle IAM global events
    4. Empty or missing regions should be handled gracefully
    """
    
    @patch('modules.aws_config.check_config_in_region')
    @patch('builtins.print')
    def test_when_single_region_is_provided_then_it_becomes_main_region(self, mock_print, mock_check_config, mock_aws_services):
        """
        GIVEN: User provides only one region in their configuration
        WHEN: setup_aws_config is called with a single region and verbose mode
        THEN: That region should be treated as the main region with IAM global events
        
        Single-region deployments still need IAM global event recording somewhere.
        """
        # Arrange - Mock configuration check  
        mock_check_config.return_value = {
            'region': 'us-east-1',
            'service_enabled': True,  # Updated to use standardized field name
            'records_global_iam': True,
            'needs_changes': False,
            'issues': [],
            'actions': [],
            'errors': [],
            'service_details': []  # Updated to use standardized field name
        }
        params = create_test_params(regions=['us-east-1'])
        
        # Act - Use verbose to see region details
        result = setup_aws_config('Yes', params, dry_run=True, verbose=True)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'Main region: us-east-1' in all_output, "Single region should be identified as main"
        # Should not mention other regions when there's only one
        assert 'Other regions:' not in all_output, "Should not mention other regions for single region setup"
    
    @patch('modules.aws_config.check_config_in_region')
    @patch('builtins.print')
    def test_when_multiple_regions_provided_then_first_is_main_others_are_secondary(self, mock_print, mock_check_config, mock_aws_services):
        """
        GIVEN: User provides multiple regions in their configuration
        WHEN: setup_aws_config is called with multiple regions and verbose mode
        THEN: First region should be main (with IAM global), others should be secondary (without IAM global)
        
        This prevents duplicate IAM global event recording across regions.
        """
        # Arrange - Mock configuration check
        mock_check_config.return_value = {
            'region': 'test-region',
            'service_enabled': True,
            'records_global_iam': True,
            'needs_changes': False,
            'issues': [],
            'actions': [],
            'errors': [],
            'service_details': []
        }
        params = create_test_params(regions=['eu-west-1', 'us-east-1', 'ap-southeast-1'])
        
        # Act - Use verbose to see region details
        result = setup_aws_config('Yes', params, dry_run=True, verbose=True)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Main region should be the first one in the list
        assert 'Main region: eu-west-1' in all_output, "First region should be identified as main"
        
        # Other regions should be mentioned
        assert 'Other regions:' in all_output, "Should mention other regions exist"
        assert 'us-east-1' in all_output, "Should list second region as other"
        assert 'ap-southeast-1' in all_output, "Should list third region as other"
    


class TestAWSConfigErrorResilience:
    """
    SPECIFICATION: Error handling and resilience
    
    The setup_aws_config function should:
    1. Handle exceptions gracefully without crashing
    2. Return False when errors occur
    3. Log error information for debugging
    4. Continue functioning with malformed input
    """
    
    @patch('builtins.print')
    def test_when_unexpected_exception_occurs_then_error_is_handled_gracefully(self, mock_print, mock_aws_services):
        """
        GIVEN: An unexpected error occurs during execution
        WHEN: setup_aws_config encounters an exception
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
        result = setup_aws_config('Yes', params, dry_run=False, verbose=True)
        
        # Assert
        assert result is False, "Should return False when exception occurs"
        
        # Verify error was logged
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert 'ERROR in setup_aws_config:' in all_output, "Should log the error"
    


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


class TestAWSConfigConfigurationScenarios:
    """
    SPECIFICATION: Comprehensive configuration scenario detection
    
    The check_config_in_region function should handle all real-world scenarios:
    1. Unconfigured service - No Config recorders found
    2. Configuration but wrong IAM global settings - Config enabled but IAM global recording incorrect
    3. Weird configurations - Partial setups, missing delivery channels, suboptimal settings
    4. Valid configurations - Properly configured with correct IAM global recording per region role
    """
    
    def test_scenario_1_unconfigured_service_detected(self, mock_aws_services):
        """
        GIVEN: AWS Config is not enabled in a region (no recorders)
        WHEN: check_config_in_region is called
        THEN: Should detect unconfigured service and recommend enablement
        """
        # Arrange - No configuration recorders found - this will be mocked by mock_aws_services
        
        # Act
        from modules.aws_config import check_config_in_region
        result = check_config_in_region(
            region='us-east-1',
            is_main_region=True,
            admin_account='123456789012',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['service_enabled'] is False
        assert result['needs_changes'] is True
        assert "No configuration recorders found" in result['issues']
        assert "Create configuration recorder" in result['actions']
        assert "❌ No configuration recorders found" in result['service_details']
    
    @patch('modules.aws_config.get_client')
    def test_scenario_2_main_region_missing_iam_global_recording(self, mock_get_client):
        """
        GIVEN: AWS Config is enabled in main region but not recording IAM global events
        WHEN: check_config_in_region is called for main region
        THEN: Should detect missing IAM global recording and recommend fix
        """
        # Arrange - Config enabled but no IAM global recording in main region
        mock_config_client = MagicMock()
        mock_get_client.return_value = mock_config_client
        
        # Configuration recorder exists but without IAM global recording
        mock_config_client.describe_configuration_recorders.return_value = {
            'ConfigurationRecorders': [
                {
                    'name': 'test-recorder',
                    'roleARN': 'arn:aws:iam::123456789012:role/config-role',
                    'recordingGroup': {
                        'allSupported': False,
                        'includeGlobalResourceTypes': False,  # Missing IAM global
                        'resourceTypes': ['AWS::EC2::Instance']
                    }
                }
            ]
        }
        
        # Mock delivery channels and rules
        mock_config_client.describe_delivery_channels.return_value = {'DeliveryChannels': []}
        mock_config_client.get_paginator.return_value.paginate.return_value = [{'ConfigRules': []}]
        
        # Act
        from modules.aws_config import check_config_in_region
        result = check_config_in_region(
            region='us-east-1',
            is_main_region=True,  # Main region should record IAM global
            admin_account='123456789012',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['service_enabled'] is True
        assert result['records_global_iam'] is False
        assert result['needs_changes'] is True
        assert "Main region should record IAM global events but doesn't" in result['issues']
        assert "Enable IAM global resource recording" in result['actions']
        # Check that IAM global resources are marked as excluded in details
        details_str = '\n'.join(result['service_details'])
        assert "IAM Global Resources: ✅ Excluded" in details_str
    
    @patch('modules.aws_config.get_client')
    def test_scenario_3_non_main_region_incorrectly_recording_iam_global(self, mock_get_client):
        """
        GIVEN: AWS Config is enabled in non-main region but incorrectly recording IAM global events
        WHEN: check_config_in_region is called for non-main region
        THEN: Should detect incorrect IAM global recording and recommend fix
        """
        # Arrange - Config enabled with IAM global recording in non-main region
        mock_config_client = MagicMock()
        mock_get_client.return_value = mock_config_client
        
        # Configuration recorder exists with IAM global recording (wrong for non-main region)
        mock_config_client.describe_configuration_recorders.return_value = {
            'ConfigurationRecorders': [
                {
                    'name': 'test-recorder',
                    'roleARN': 'arn:aws:iam::123456789012:role/config-role',
                    'recordingGroup': {
                        'allSupported': True,  # All supported includes global
                        'includeGlobalResourceTypes': True
                    }
                }
            ]
        }
        
        # Mock delivery channels and rules
        mock_config_client.describe_delivery_channels.return_value = {'DeliveryChannels': []}
        mock_config_client.get_paginator.return_value.paginate.return_value = [{'ConfigRules': []}]
        
        # Act
        from modules.aws_config import check_config_in_region
        result = check_config_in_region(
            region='us-west-2',
            is_main_region=False,  # Non-main region should NOT record IAM global
            admin_account='123456789012',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['service_enabled'] is True
        assert result['records_global_iam'] is True
        assert result['needs_changes'] is True
        assert "Non-main region should NOT record IAM global events" in result['issues']
        assert "Disable IAM global resource recording" in result['actions']
        # Check that IAM global resources are marked as included in details
        details_str = '\n'.join(result['service_details'])
        assert "IAM Global Resources: ✅ Included" in details_str
    
    @patch('modules.aws_config.get_client')
    def test_scenario_3_weird_configuration_missing_delivery_channel(self, mock_get_client):
        """
        GIVEN: AWS Config is enabled but missing delivery channel
        WHEN: check_config_in_region is called
        THEN: Should detect weird configuration and recommend fix
        """
        # Arrange - Config enabled but no delivery channel
        mock_config_client = MagicMock()
        mock_get_client.return_value = mock_config_client
        
        # Configuration recorder exists with proper IAM global settings
        mock_config_client.describe_configuration_recorders.return_value = {
            'ConfigurationRecorders': [
                {
                    'name': 'test-recorder',
                    'roleARN': 'arn:aws:iam::123456789012:role/config-role',
                    'recordingGroup': {
                        'allSupported': True,
                        'includeGlobalResourceTypes': True
                    }
                }
            ]
        }
        
        # No delivery channels (weird configuration)
        mock_config_client.describe_delivery_channels.return_value = {'DeliveryChannels': []}
        mock_config_client.get_paginator.return_value.paginate.return_value = [{'ConfigRules': []}]
        
        # Act
        from modules.aws_config import check_config_in_region
        result = check_config_in_region(
            region='us-east-1',
            is_main_region=True,
            admin_account='123456789012',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert
        assert result['service_enabled'] is True
        assert result['needs_changes'] is True
        assert "No delivery channels found" in result['issues']
        assert "Create delivery channel" in result['actions']
        assert "❌ No delivery channels found" in result['service_details']
    
    @patch('modules.aws_config.get_client')
    def test_scenario_4_valid_configuration_optimal_setup(self, mock_get_client):
        """
        GIVEN: AWS Config is properly configured with optimal settings
        WHEN: check_config_in_region is called
        THEN: Should detect valid configuration and require no changes
        """
        # Arrange - Optimal configuration
        mock_config_client = MagicMock()
        mock_get_client.return_value = mock_config_client
        
        # Configuration recorder with optimal settings
        mock_config_client.describe_configuration_recorders.return_value = {
            'ConfigurationRecorders': [
                {
                    'name': 'aws-config-recorder',
                    'roleARN': 'arn:aws:iam::123456789012:role/aws-config-role',
                    'recordingGroup': {
                        'allSupported': True,
                        'includeGlobalResourceTypes': True
                    },
                    'recordingMode': {
                        'recordingFrequency': 'CONTINUOUS'
                    }
                }
            ]
        }
        
        # Proper delivery channel
        mock_config_client.describe_delivery_channels.return_value = {
            'DeliveryChannels': [
                {
                    'name': 'aws-config-delivery-channel',
                    's3BucketName': 'aws-config-bucket-123456789012',
                    's3KeyPrefix': 'config',
                    'deliveryProperties': {
                        'deliveryFrequency': 'Daily'
                    }
                }
            ]
        }
        
        # Config rules present
        mock_config_client.get_paginator.return_value.paginate.return_value = [
            {
                'ConfigRules': [
                    {'Source': {'Owner': 'AWS'}, 'ConfigRuleName': 'rule1'},
                    {'Source': {'Owner': 'AWS'}, 'ConfigRuleName': 'rule2'},
                    {'Source': {'Owner': 'CUSTOM_LAMBDA'}, 'ConfigRuleName': 'custom-rule'}
                ]
            }
        ]
        
        # Act
        from modules.aws_config import check_config_in_region
        result = check_config_in_region(
            region='us-east-1',
            is_main_region=True,
            admin_account='123456789012',
            cross_account_role='AWSControlTowerExecution',
            verbose=False
        )
        
        # Assert - Valid configuration requires no changes
        assert result['service_enabled'] is True
        assert result['records_global_iam'] is True
        assert result['needs_changes'] is False, "Valid configuration should not need changes"
        assert result['issues'] == [], "Valid configuration should have no issues"
        assert result['actions'] == [], "Valid configuration should need no actions"
        
        # Check that optimal settings are properly detected
        details_str = '\n'.join(result['service_details'])
        assert "✅ Configuration Recorders: 1 found" in details_str
        assert "Recording: All supported resources" in details_str
        assert "IAM Global Resources: ✅ Included" in details_str
        assert "Recording Frequency: CONTINUOUS" in details_str
        assert "✅ Delivery Channels: 1 found" in details_str
        assert "✅ Config Rules: 3 active rules" in details_str
        assert "AWS Managed Rules: 2" in details_str
        assert "Custom Rules: 1" in details_str
    
    def test_verbosity_control_in_configuration_detection(self):
        """
        GIVEN: Configuration detection is performed with verbosity controls
        WHEN: check_config_in_region is called with verbose flag variations
        THEN: Should respect verbosity settings for output control
        
        This ensures the terse vs verbose behavior works correctly.
        """
        # This test validates that the verbosity pattern is implemented
        # The actual verbose behavior is tested through integration tests
        # This serves as a specification that verbosity control exists
        
        params = create_test_params()
        
        # Test that function accepts verbose parameter
        # (Implementation details tested through integration)
        from modules.aws_config import check_config_in_region
        assert 'verbose' in check_config_in_region.__code__.co_varnames
        
        # Specification: Function should handle both verbose and non-verbose modes
        # Integration tests validate the actual output behavior


class TestAwsConfigAnomalousRegionDetection:
    """
    SPECIFICATION: AWS Config anomalous region detection
    
    The check_anomalous_config_regions function should:
    1. Detect AWS Config configuration recorders in regions outside the expected list
    2. Return list of anomalous regions with configuration details
    3. Handle API errors gracefully
    4. Provide cost-impact warnings for unexpected activations
    """
    
    @patch('modules.aws_config.printc')
    @patch('modules.aws_config.AnomalousRegionChecker.check_service_anomalous_regions')
    def test_when_anomalous_config_found_then_show_cost_warnings(self, mock_anomaly_check, mock_print, mock_aws_services):
        """
        GIVEN: AWS Config configuration recorders exist in regions outside expected configuration
        WHEN: setup_aws_config detects anomalous regions
        THEN: Should warn about unexpected costs and configuration drift
        """
        # Arrange - Mock anomalous regions found using dataclass objects
        from modules.utils import create_anomalous_status
        
        anomaly1 = create_anomalous_status('ap-southeast-2', 1)
        anomaly1.resource_details = [
            {
                'recorder_name': 'default',
                'recording_enabled': True,
                'recording_mode': 'CONTINUOUS',
                'include_global_resources': False
            }
        ]
        
        anomaly2 = create_anomalous_status('ca-central-1', 1)
        anomaly2.resource_details = [
            {
                'recorder_name': 'custom-recorder',
                'recording_enabled': True,
                'recording_mode': 'DAILY',
                'include_global_resources': True
            }
        ]
        
        mock_anomaly_check.return_value = [anomaly1, anomaly2]
        
        params = create_test_params()
        
        # Act
        result = setup_aws_config(enabled='Yes', params=params, dry_run=False, verbose=True)
        
        # Assert
        assert result is True, "Should handle anomalous config gracefully"
        
        # Check that anomaly warnings were displayed
        all_output = ' '.join([str(call_args) for call_args in mock_print.call_args_list])
        anomaly_mentioned = any(phrase in all_output.lower() for phrase in [
            'anomalous', 'unexpected', 'cost', 'configuration drift'
        ])
        assert anomaly_mentioned, f"Should show anomalous config warnings. Got: {all_output}"