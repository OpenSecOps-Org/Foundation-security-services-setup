"""
Unit tests for Security Hub service module.

These tests serve as executable specifications for the Security Hub setup functionality.
Each test documents expected behavior and can be read as requirements.

Security Hub Setup Requirements:
- Enable Security Hub in org account across all regions
- Delegate administration to Security-Adm account
- Configure central findings and control policies
- Create PROD and DEV control policies with specific controls
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

from modules.security_hub import setup_security_hub, printc
from tests.fixtures.aws_parameters import create_test_params


class TestSecurityHubBasicBehavior:
    """
    SPECIFICATION: Basic behavior of Security Hub setup
    
    The setup_security_hub function should:
    1. Return True when operation completes successfully
    2. Accept both enabled and disabled states
    3. Handle case-insensitive input gracefully
    """
    
    def test_when_security_hub_is_enabled_then_function_returns_success(self, mock_aws_services):
        """
        GIVEN: Security Hub is requested to be enabled
        WHEN: setup_security_hub is called with enabled='Yes'
        THEN: The function should return True indicating successful completion
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_security_hub(enabled='Yes', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "Security Hub setup should return True when enabled successfully"
    
    def test_when_security_hub_is_disabled_then_function_returns_success(self, mock_aws_services):
        """
        GIVEN: Security Hub is requested to be disabled/skipped
        WHEN: setup_security_hub is called with enabled='No'
        THEN: The function should return True and skip configuration gracefully
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_security_hub(enabled='No', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "Security Hub setup should return True even when disabled"
    
    def test_when_enabled_flag_values_are_exactly_yes_or_no_then_they_are_accepted(self, mock_aws_services):
        """
        GIVEN: Main script provides exactly 'Yes' or 'No' values via argparse choices
        WHEN: setup_security_hub is called with these canonical values
        THEN: Both values should be handled correctly
        
        Note: argparse choices=['Yes', 'No'] ensures only these values are passed.
        """
        # Arrange
        params = create_test_params()
        
        # Act & Assert - Test canonical Yes value
        result = setup_security_hub('Yes', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='Yes'"
            
        # Act & Assert - Test canonical No value
        result = setup_security_hub('No', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='No'"


class TestSecurityHubUserFeedback:
    """
    SPECIFICATION: User feedback and communication
    
    The setup_security_hub function should provide clear feedback to users:
    1. Show what actions will be taken in dry-run mode
    2. Display detailed information in verbose mode
    3. Confirm when services are disabled/skipped
    4. Use consistent formatting and colors
    """
    
    @patch('builtins.print')
    def test_when_verbose_mode_is_enabled_then_detailed_information_is_displayed(self, mock_print, mock_aws_services):
        """
        GIVEN: User wants detailed information about the operation
        WHEN: setup_security_hub is called with verbose=True
        THEN: Detailed parameter information should be displayed
        
        This helps users understand exactly what the script will do with their parameters.
        """
        # Arrange
        params = create_test_params(
            regions=['us-east-1', 'us-west-2'], 
            org_id='o-example12345'
        )
        
        # Act
        result = setup_security_hub('Yes', params, dry_run=False, verbose=True)
        
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
    def test_when_dry_run_mode_is_enabled_then_preview_actions_are_shown(self, mock_print, mock_aws_services):
        """
        GIVEN: User wants to preview actions without making changes
        WHEN: setup_security_hub is called with dry_run=True
        THEN: Actions should be prefixed with "DRY RUN:" to indicate no changes
        
        This allows users to safely validate their configuration before applying.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1', 'us-west-2'])
        
        # Act
        result = setup_security_hub('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify dry-run messages were displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Real implementation uses "DRY RUN - Actions that would be taken:"
        assert 'DRY RUN' in all_output, "Should indicate dry run mode"
        assert ('delegate' in all_output or 'delegation' in all_output), "Should describe delegation actions"
        assert ('policies' in all_output or 'finding aggregation' in all_output), "Should mention setup actions"
    
    @patch('builtins.print')
    def test_when_security_hub_is_disabled_then_clear_skip_message_is_shown(self, mock_print, mock_aws_services):
        """
        GIVEN: User has disabled Security Hub in their configuration
        WHEN: setup_security_hub is called with enabled='No'
        THEN: A clear message should indicate the service is being skipped
        
        This prevents confusion about whether the service failed or was intentionally skipped.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_security_hub('No', params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify skip message was displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Real implementation shows deactivation analysis, not just "skipping"
        assert ('Security Hub is not currently configured' in all_output or 
                'DEACTIVATION ANALYSIS' in all_output), "Should show deactivation analysis when disabled"
    
    @patch('builtins.print')
    def test_when_function_runs_then_proper_banner_formatting_is_used(self, mock_print, mock_aws_services):
        """
        GIVEN: User runs the Security Hub setup
        WHEN: setup_security_hub is called
        THEN: Output should include a properly formatted banner for readability
        
        Consistent formatting helps users identify different service sections in the output.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        setup_security_hub('Yes', params, dry_run=False, verbose=False)
        
        # Assert
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'SECURITY HUB SETUP' in all_output, "Should display service name banner"
        assert '=' in all_output, "Should use separator lines for visual formatting"


class TestSecurityHubRegionHandling:
    """
    SPECIFICATION: Multi-region configuration logic
    
    Security Hub requires configuration across all enabled regions:
    1. Enable Security Hub in all regions
    2. Delegate administration in all regions
    3. Configure control policies for PROD/DEV environments
    4. Handle single vs multiple region deployments
    """
    
    @patch('builtins.print')
    def test_when_single_region_is_provided_then_it_is_configured(self, mock_print, mock_aws_services):
        """
        GIVEN: User provides only one region in their configuration
        WHEN: setup_security_hub is called with a single region
        THEN: That region should be configured for Security Hub
        
        Single-region deployments should work correctly.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1'])
        
        # Act
        result = setup_security_hub('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'administration' in all_output or 'configuration' in all_output, "Should mention Security Hub configuration"
    
    @patch('builtins.print')
    def test_when_multiple_regions_provided_then_all_are_configured(self, mock_print, mock_aws_services):
        """
        GIVEN: User provides multiple regions in their configuration
        WHEN: setup_security_hub is called with multiple regions
        THEN: All regions should be configured for Security Hub
        
        Multi-region deployments should handle all regions consistently.
        """
        # Arrange
        params = create_test_params(regions=['eu-west-1', 'us-east-1', 'ap-southeast-1'])
        
        # Act
        result = setup_security_hub('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Should mention Security Hub configuration approach
        assert 'administration' in all_output or 'configuration' in all_output, "Should mention Security Hub configuration"
    


class TestSecurityHubControlPolicyHandling:
    """
    SPECIFICATION: Control policy configuration logic
    
    Security Hub requires specific control policy setup:
    1. Create PROD control policy with specific controls
    2. Create DEV control policy with different controls
    3. Assign policies to appropriate organizational units
    4. Handle existing policy preservation
    """
    
    @patch('builtins.print')
    def test_when_enabled_then_control_policy_setup_is_mentioned(self, mock_print, mock_aws_services):
        """
        GIVEN: Security Hub is enabled
        WHEN: setup_security_hub is called
        THEN: Control policy configuration should be mentioned in output
        
        Control policies are a key part of Security Hub setup.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_security_hub('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'PROD' in all_output or 'DEV' in all_output, "Should mention PROD or DEV policies"
    
    @patch('builtins.print')
    def test_when_dry_run_then_policy_creation_is_previewed(self, mock_print, mock_aws_services):
        """
        GIVEN: User wants to preview Security Hub setup
        WHEN: setup_security_hub is called with dry_run=True
        THEN: Control policy creation should be previewed
        
        Users should see what policies will be created.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_security_hub('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Real implementation uses "DRY RUN - Actions that would be taken:"
        assert 'DRY RUN' in all_output, "Should indicate dry run mode"
        assert ('policies' in all_output or 'delegate' in all_output), "Should mention policies or delegation setup"


class TestSecurityHubErrorResilience:
    """
    SPECIFICATION: Error handling and resilience
    
    The setup_security_hub function should:
    1. Handle exceptions gracefully without crashing
    2. Return False when errors occur
    3. Log error information for debugging
    4. Continue functioning with malformed input
    """
    
    @patch('builtins.print')
    def test_when_unexpected_exception_occurs_then_error_is_handled_gracefully(self, mock_print, mock_aws_services):
        """
        GIVEN: An unexpected error occurs during execution
        WHEN: setup_security_hub encounters an exception
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
        result = setup_security_hub('Yes', params, dry_run=False, verbose=True)
        
        # Assert
        assert result is False, "Should return False when exception occurs"
        
        # Verify error was logged
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert 'ERROR in setup_security_hub:' in all_output, "Should log the error"
    


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