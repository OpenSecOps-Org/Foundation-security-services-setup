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
from unittest.mock import patch, call

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
    
    def test_when_aws_config_is_enabled_then_function_returns_success(self):
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
    
    def test_when_aws_config_is_disabled_then_function_returns_success(self):
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
    
    def test_when_enabled_flag_uses_different_cases_then_all_are_accepted(self):
        """
        GIVEN: Users may type enabled flags in different cases
        WHEN: setup_aws_config is called with various case combinations
        THEN: All reasonable variations should be accepted (case-insensitive)
        
        This ensures user-friendly behavior regardless of how users type the flag.
        """
        # Arrange
        params = create_test_params()
        acceptable_yes_values = ['YES', 'yes', 'Yes', 'Y']
        acceptable_no_values = ['NO', 'no', 'No', 'N']
        
        # Act & Assert - Test enabled variations
        for enabled_value in acceptable_yes_values:
            result = setup_aws_config(enabled_value, params, dry_run=True, verbose=False)
            assert result is True, f"Should accept enabled='{enabled_value}' as a valid 'yes' value"
            
        # Act & Assert - Test disabled variations  
        for enabled_value in acceptable_no_values:
            result = setup_aws_config(enabled_value, params, dry_run=True, verbose=False)
            assert result is True, f"Should accept enabled='{enabled_value}' as a valid 'no' value"


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
    def test_when_verbose_mode_is_enabled_then_detailed_information_is_displayed(self, mock_print):
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
    
    @patch('builtins.print')
    def test_when_dry_run_mode_is_enabled_then_preview_actions_are_shown(self, mock_print):
        """
        GIVEN: User wants to preview actions without making changes
        WHEN: setup_aws_config is called with dry_run=True
        THEN: Actions should be prefixed with "DRY RUN:" to indicate no changes
        
        This allows users to safely validate their configuration before applying.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1', 'us-west-2'])
        
        # Act
        result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify dry-run messages were displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'DRY RUN:' in all_output, "Should prefix actions with DRY RUN indicator"
        assert 'Would enable AWS Config' in all_output, "Should describe what would be done"
        assert 'main region (us-east-1)' in all_output, "Should specify the main region"
    
    @patch('builtins.print')
    def test_when_aws_config_is_disabled_then_clear_skip_message_is_shown(self, mock_print):
        """
        GIVEN: User has disabled AWS Config in their configuration
        WHEN: setup_aws_config is called with enabled='No'
        THEN: A clear message should indicate the service is being skipped
        
        This prevents confusion about whether the service failed or was intentionally skipped.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_aws_config('No', params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify skip message was displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'AWS Config is disabled - skipping' in all_output, "Should clearly indicate service is being skipped"
    
    @patch('builtins.print')
    def test_when_function_runs_then_proper_banner_formatting_is_used(self, mock_print):
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
    
    @patch('builtins.print')
    def test_when_single_region_is_provided_then_it_becomes_main_region(self, mock_print):
        """
        GIVEN: User provides only one region in their configuration
        WHEN: setup_aws_config is called with a single region
        THEN: That region should be treated as the main region with IAM global events
        
        Single-region deployments still need IAM global event recording somewhere.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1'])
        
        # Act
        result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'main region (us-east-1)' in all_output, "Single region should be identified as main"
        # Should not mention other regions when there's only one
        other_regions_mentioned = 'other regions' in all_output and '[]' not in all_output
        assert not other_regions_mentioned, "Should not mention other regions for single region setup"
    
    @patch('builtins.print')
    def test_when_multiple_regions_provided_then_first_is_main_others_are_secondary(self, mock_print):
        """
        GIVEN: User provides multiple regions in their configuration
        WHEN: setup_aws_config is called with multiple regions
        THEN: First region should be main (with IAM global), others should be secondary (without IAM global)
        
        This prevents duplicate IAM global event recording across regions.
        """
        # Arrange
        params = create_test_params(regions=['eu-west-1', 'us-east-1', 'ap-southeast-1'])
        
        # Act
        result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Main region should be the first one in the list
        assert 'main region (eu-west-1)' in all_output, "First region should be identified as main"
        
        # Other regions should be mentioned
        assert 'other regions' in all_output, "Should mention other regions exist"
        assert 'us-east-1' in all_output, "Should list second region as other"
        assert 'ap-southeast-1' in all_output, "Should list third region as other"
    
    @patch('builtins.print')
    def test_when_regions_parameter_is_missing_then_graceful_handling_occurs(self, mock_print):
        """
        GIVEN: Parameters might be incomplete or malformed
        WHEN: setup_aws_config is called with missing regions parameter
        THEN: Function should handle gracefully without crashing
        
        Defensive programming for real-world usage scenarios.
        """
        # Arrange
        params = {
            'admin_account': '123456789012',
            'security_account': '234567890123',
            # Missing regions parameter
            'org_id': 'o-example12345'
        }
        
        # Act
        result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True, "Should handle missing regions parameter gracefully"
    
    @patch('builtins.print')
    def test_when_regions_parameter_is_empty_then_graceful_handling_occurs(self, mock_print):
        """
        GIVEN: User might provide empty regions list
        WHEN: setup_aws_config is called with empty regions=[]
        THEN: Function should handle gracefully without crashing
        
        Edge case handling for defensive programming.
        """
        # Arrange
        params = create_test_params(regions=[])
        
        # Act
        result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True, "Should handle empty regions list gracefully"


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
    def test_when_unexpected_exception_occurs_then_error_is_handled_gracefully(self, mock_print):
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
    
    def test_when_parameters_are_malformed_then_function_continues_safely(self):
        """
        GIVEN: Parameters might be malformed in real-world usage
        WHEN: setup_aws_config is called with various malformed parameters
        THEN: Function should handle them safely without crashing
        
        Real-world defensive programming for unexpected input.
        """
        # Arrange
        malformed_test_cases = [
            None,  # No parameters at all
            {},    # Empty parameters
            {'regions': 'not-a-list'},  # Wrong type
            {'invalid_key': 'value'},   # Unexpected keys
        ]
        
        # Act & Assert
        for malformed_params in malformed_test_cases:
            result = setup_aws_config('Yes', malformed_params, dry_run=True, verbose=False)
            assert result is True, f"Should handle malformed params gracefully: {malformed_params}"
    
    def test_when_invalid_enabled_values_provided_then_function_handles_gracefully(self):
        """
        GIVEN: Users might provide unexpected values for the enabled parameter
        WHEN: setup_aws_config is called with various invalid enabled values
        THEN: Function should handle them without crashing
        
        User input validation and defensive programming.
        """
        # Arrange
        params = create_test_params()
        invalid_enabled_values = [None, 123, [], {}, 'invalid', '']
        
        # Act & Assert
        for invalid_value in invalid_enabled_values:
            result = setup_aws_config(invalid_value, params, dry_run=True, verbose=False)
            assert result is True, f"Should handle invalid enabled value: {invalid_value}"


class TestPrintcUtilityFunction:
    """
    SPECIFICATION: Printc utility function behavior
    
    The printc helper function should:
    1. Format colored output consistently
    2. Handle additional print parameters
    3. Clear line endings properly
    """
    
    @patch('builtins.print')
    def test_when_printc_is_called_then_colored_output_is_formatted_correctly(self, mock_print):
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
    def test_when_printc_called_with_kwargs_then_they_are_passed_through(self, mock_print):
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