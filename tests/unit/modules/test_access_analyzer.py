"""
Unit tests for IAM Access Analyzer service module.

These tests serve as executable specifications for the Access Analyzer setup functionality.
Each test documents expected behavior and can be read as requirements.

Access Analyzer Setup Requirements:
- Delegate administration to Security-Adm account
- Set up organization-wide analyzer for external access (all regions)
- Set up organization-wide analyzer for unused access (main region only)
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

from modules.access_analyzer import setup_access_analyzer, printc
from tests.fixtures.aws_parameters import create_test_params


class TestAccessAnalyzerBasicBehavior:
    """
    SPECIFICATION: Basic behavior of Access Analyzer setup
    
    The setup_access_analyzer function should:
    1. Return True when operation completes successfully
    2. Accept both enabled and disabled states
    3. Handle case-insensitive input gracefully
    """
    
    def test_when_access_analyzer_is_enabled_then_function_returns_success(self):
        """
        GIVEN: Access Analyzer is requested to be enabled
        WHEN: setup_access_analyzer is called with enabled='Yes'
        THEN: The function should return True indicating successful completion
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_access_analyzer(enabled='Yes', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "Access Analyzer setup should return True when enabled successfully"
    
    def test_when_access_analyzer_is_disabled_then_function_returns_success(self):
        """
        GIVEN: Access Analyzer is requested to be disabled/skipped
        WHEN: setup_access_analyzer is called with enabled='No'
        THEN: The function should return True and skip configuration gracefully
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_access_analyzer(enabled='No', params=params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True, "Access Analyzer setup should return True even when disabled"
    
    def test_when_enabled_flag_values_are_exactly_yes_or_no_then_they_are_accepted(self):
        """
        GIVEN: Main script provides exactly 'Yes' or 'No' values via argparse choices
        WHEN: setup_access_analyzer is called with these canonical values
        THEN: Both values should be handled correctly
        
        Note: argparse choices=['Yes', 'No'] ensures only these values are passed.
        """
        # Arrange
        params = create_test_params()
        
        # Act & Assert - Test canonical Yes value
        result = setup_access_analyzer('Yes', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='Yes'"
            
        # Act & Assert - Test canonical No value
        result = setup_access_analyzer('No', params, dry_run=True, verbose=False)
        assert result is True, "Should accept enabled='No'"


class TestAccessAnalyzerUserFeedback:
    """
    SPECIFICATION: User feedback and communication
    
    The setup_access_analyzer function should provide clear feedback to users:
    1. Show what actions will be taken in dry-run mode
    2. Display detailed information in verbose mode
    3. Confirm when services are disabled/skipped
    4. Use consistent formatting and colors
    """
    
    @patch('builtins.print')
    def test_when_verbose_mode_is_enabled_then_detailed_information_is_displayed(self, mock_print):
        """
        GIVEN: User wants detailed information about the operation
        WHEN: setup_access_analyzer is called with verbose=True
        THEN: Detailed parameter information should be displayed
        
        This helps users understand exactly what the script will do with their parameters.
        """
        # Arrange
        params = create_test_params(
            regions=['us-east-1', 'us-west-2'], 
            org_id='o-example12345'
        )
        
        # Act
        result = setup_access_analyzer('Yes', params, dry_run=False, verbose=True)
        
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
        WHEN: setup_access_analyzer is called with dry_run=True
        THEN: Actions should be prefixed with "DRY RUN:" to indicate no changes
        
        This allows users to safely validate their configuration before applying.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1', 'us-west-2'])
        
        # Act
        result = setup_access_analyzer('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify dry-run messages were displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'DRY RUN:' in all_output, "Should prefix actions with DRY RUN indicator"
        assert 'Would delegate administration' in all_output, "Should describe what would be done"
        assert 'analyzer' in all_output, "Should mention analyzer setup"
    
    @patch('builtins.print')
    def test_when_access_analyzer_is_disabled_then_clear_skip_message_is_shown(self, mock_print):
        """
        GIVEN: User has disabled Access Analyzer in their configuration
        WHEN: setup_access_analyzer is called with enabled='No'
        THEN: A clear message should indicate the service is being skipped
        
        This prevents confusion about whether the service failed or was intentionally skipped.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_access_analyzer('No', params, dry_run=False, verbose=False)
        
        # Assert
        assert result is True
        
        # Verify skip message was displayed
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'Access Analyzer is disabled - skipping' in all_output, "Should clearly indicate service is being skipped"
    
    @patch('builtins.print')
    def test_when_function_runs_then_proper_banner_formatting_is_used(self, mock_print):
        """
        GIVEN: User runs the Access Analyzer setup
        WHEN: setup_access_analyzer is called
        THEN: Output should include a properly formatted banner for readability
        
        Consistent formatting helps users identify different service sections in the output.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        setup_access_analyzer('Yes', params, dry_run=False, verbose=False)
        
        # Assert
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'ACCESS ANALYZER SETUP' in all_output, "Should display service name banner"
        assert '=' in all_output, "Should use separator lines for visual formatting"


class TestAccessAnalyzerRegionHandling:
    """
    SPECIFICATION: Multi-region configuration logic
    
    Access Analyzer has specific region requirements:
    1. External access analyzer in all regions
    2. Unused access analyzer in main region only
    3. Delegation required in all regions
    4. Handle single vs multiple region deployments
    """
    
    @patch('builtins.print')
    def test_when_single_region_is_provided_then_it_is_configured(self, mock_print):
        """
        GIVEN: User provides only one region in their configuration
        WHEN: setup_access_analyzer is called with a single region
        THEN: That region should be configured for Access Analyzer
        
        Single-region deployments should work correctly.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1'])
        
        # Act
        result = setup_access_analyzer('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        assert 'all regions' in all_output or 'main region' in all_output, "Should mention region configuration"
    
    @patch('builtins.print')
    def test_when_multiple_regions_provided_then_all_are_configured(self, mock_print):
        """
        GIVEN: User provides multiple regions in their configuration
        WHEN: setup_access_analyzer is called with multiple regions
        THEN: All regions should be configured for Access Analyzer
        
        Multi-region deployments should handle all regions consistently.
        """
        # Arrange
        params = create_test_params(regions=['eu-west-1', 'us-east-1', 'ap-southeast-1'])
        
        # Act
        result = setup_access_analyzer('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Should mention region configuration approach
        assert 'all regions' in all_output, "Should mention all regions configuration"
        assert 'main region' in all_output, "Should mention main region specific configuration"
    


class TestAccessAnalyzerTypeHandling:
    """
    SPECIFICATION: Analyzer type configuration logic
    
    Access Analyzer requires different analyzer types:
    1. External access analyzer (all regions)
    2. Unused access analyzer (main region only)
    3. Proper delegation and organization-wide scope
    4. Future extensibility for additional analyzer types
    """
    
    @patch('builtins.print')
    def test_when_enabled_then_analyzer_types_are_mentioned(self, mock_print):
        """
        GIVEN: Access Analyzer is enabled
        WHEN: setup_access_analyzer is called
        THEN: Different analyzer types should be mentioned in output
        
        Users should understand what types of analyzers are being configured.
        """
        # Arrange
        params = create_test_params()
        
        # Act
        result = setup_access_analyzer('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Should mention analyzer types or configuration
        analyzer_mentioned = any(term in all_output for term in [
            'external access', 'unused access', 'analyzers', 'organization-wide'
        ])
        assert analyzer_mentioned, "Should mention analyzer types or configuration"
    
    @patch('builtins.print')
    def test_when_main_region_specified_then_unused_access_setup_mentioned(self, mock_print):
        """
        GIVEN: Access Analyzer is enabled with main region
        WHEN: setup_access_analyzer is called
        THEN: Unused access analyzer setup should be mentioned for main region
        
        Unused access analyzers are only configured in the main region.
        """
        # Arrange
        params = create_test_params(regions=['us-east-1', 'us-west-2'])
        
        # Act
        result = setup_access_analyzer('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert result is True
        
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        
        # Should mention main region context or unused access
        main_region_mentioned = 'main region' in all_output
        assert main_region_mentioned, "Should reference main region configuration"


class TestAccessAnalyzerErrorResilience:
    """
    SPECIFICATION: Error handling and resilience
    
    The setup_access_analyzer function should:
    1. Handle exceptions gracefully without crashing
    2. Return False when errors occur
    3. Log error information for debugging
    4. Continue functioning with malformed input
    """
    
    @patch('builtins.print')
    def test_when_unexpected_exception_occurs_then_error_is_handled_gracefully(self, mock_print):
        """
        GIVEN: An unexpected error occurs during execution
        WHEN: setup_access_analyzer encounters an exception
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
        result = setup_access_analyzer('Yes', params, dry_run=False, verbose=True)
        
        # Assert
        assert result is False, "Should return False when exception occurs"
        
        # Verify error was logged
        all_output = ' '.join(str(call) for call in mock_print.call_args_list)
        assert 'ERROR in setup_access_analyzer:' in all_output, "Should log the error"
    


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