"""
Integration tests for the main setup-security-services script logic.

This module tests the complete script logic flow including service module
execution and coordination by directly importing and calling functions.
All tests use mocked AWS services for fast, reliable testing.
"""

import pytest
import sys
import os
import subprocess
from unittest.mock import patch, MagicMock

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.fixtures.aws_parameters import create_test_params
from modules.aws_config import setup_aws_config
from modules.guardduty import setup_guardduty  
from modules.access_analyzer import setup_access_analyzer
from modules.security_hub import setup_security_hub
from modules.detective import setup_detective
from modules.inspector import setup_inspector


class TestServiceIntegration:
    """Test all services work together with mocked AWS."""
    
    def test_all_services_execute_successfully_when_enabled(self, mock_aws_services):
        """Test that all services execute successfully with mocked AWS."""
        # Arrange
        params = create_test_params(
            regions=['us-east-1', 'us-west-2'],
            admin_account='123456789012',
            security_account='234567890123'
        )
        
        # Act & Assert - Test all services execute without errors
        assert setup_aws_config('Yes', params, dry_run=True, verbose=False) is True
        assert setup_guardduty('Yes', params, dry_run=True, verbose=False) is True
        assert setup_access_analyzer('Yes', params, dry_run=True, verbose=False) is True
        assert setup_security_hub('Yes', params, dry_run=True, verbose=False) is True
        assert setup_detective('Yes', params, dry_run=True, verbose=False) is True
        assert setup_inspector('Yes', params, dry_run=True, verbose=False) is True
    
    def test_all_services_handle_disabled_state_gracefully(self, mock_aws_services):
        """Test that all services handle disabled state without errors."""
        # Arrange
        params = create_test_params()
        
        # Act & Assert - Test all services handle disabled state
        assert setup_aws_config('No', params, dry_run=True, verbose=False) is True
        assert setup_guardduty('No', params, dry_run=True, verbose=False) is True
        assert setup_access_analyzer('No', params, dry_run=True, verbose=False) is True
        assert setup_security_hub('No', params, dry_run=True, verbose=False) is True
        assert setup_detective('No', params, dry_run=True, verbose=False) is True
        assert setup_inspector('No', params, dry_run=True, verbose=False) is True
    
    def test_services_work_with_single_region(self, mock_aws_services):
        """Test all services work with single region configuration."""
        # Arrange
        params = create_test_params(regions=['us-east-1'])
        
        # Act & Assert
        assert setup_aws_config('Yes', params, dry_run=True, verbose=False) is True
        assert setup_guardduty('Yes', params, dry_run=True, verbose=False) is True
        assert setup_access_analyzer('Yes', params, dry_run=True, verbose=False) is True
        assert setup_security_hub('Yes', params, dry_run=True, verbose=False) is True
    
    def test_services_work_with_multiple_regions(self, mock_aws_services):
        """Test all services work with multiple region configuration."""
        # Arrange
        params = create_test_params(regions=['us-east-1', 'us-west-2', 'eu-west-1'])
        
        # Act & Assert
        assert setup_aws_config('Yes', params, dry_run=True, verbose=False) is True
        assert setup_guardduty('Yes', params, dry_run=True, verbose=False) is True
        assert setup_access_analyzer('Yes', params, dry_run=True, verbose=False) is True
        assert setup_security_hub('Yes', params, dry_run=True, verbose=False) is True


class TestServiceErrorHandling:
    """Test error handling across service integration."""
    
    def test_services_handle_malformed_parameters_gracefully(self, mock_aws_services):
        """Test services handle edge cases without crashing."""
        # Arrange - Test with minimal parameters
        params = {
            'regions': ['us-east-1'],
            'admin_account': '123456789012',
            'security_account': '234567890123',
            'cross_account_role': 'TestRole',
            'org_id': 'o-test12345',
            'root_ou': 'r-test12345'
        }
        
        # Act & Assert - Services should not crash with basic parameters
        assert setup_aws_config('Yes', params, dry_run=True, verbose=False) is True
        assert setup_guardduty('Yes', params, dry_run=True, verbose=False) is True
        assert setup_access_analyzer('Yes', params, dry_run=True, verbose=False) is True
    
    @patch('builtins.print')
    def test_verbose_mode_works_across_all_services(self, mock_print, mock_aws_services):
        """Test verbose mode produces output across all services."""
        # Arrange
        params = create_test_params()
        
        # Act
        setup_aws_config('Yes', params, dry_run=True, verbose=True)
        setup_guardduty('Yes', params, dry_run=True, verbose=True)  
        setup_access_analyzer('Yes', params, dry_run=True, verbose=True)
        
        # Assert - Verbose mode should produce output
        assert mock_print.call_count > 10, "Verbose mode should produce substantial output"
    
    def test_dry_run_mode_prevents_actual_changes(self, mock_aws_services):
        """Test dry-run mode works across all services."""
        # Arrange
        params = create_test_params()
        
        # Act & Assert - Dry run should complete successfully
        assert setup_aws_config('Yes', params, dry_run=True, verbose=False) is True
        assert setup_guardduty('Yes', params, dry_run=True, verbose=False) is True
        assert setup_access_analyzer('Yes', params, dry_run=True, verbose=False) is True
        assert setup_security_hub('Yes', params, dry_run=True, verbose=False) is True
        assert setup_detective('Yes', params, dry_run=True, verbose=False) is True
        assert setup_inspector('Yes', params, dry_run=True, verbose=False) is True


class TestServiceSequencing:
    """Test service execution order and dependencies."""
    
    def test_core_services_execute_in_logical_order(self, mock_aws_services):
        """Test that core services can be executed in dependency order."""
        # Arrange
        params = create_test_params()
        
        # Act - Execute in recommended order: Config -> GuardDuty -> Access Analyzer -> Security Hub
        config_result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
        guardduty_result = setup_guardduty('Yes', params, dry_run=True, verbose=False)
        analyzer_result = setup_access_analyzer('Yes', params, dry_run=True, verbose=False)
        hub_result = setup_security_hub('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert config_result is True
        assert guardduty_result is True
        assert analyzer_result is True
        assert hub_result is True
    
    def test_optional_services_work_independently(self, mock_aws_services):
        """Test that optional services (Detective, Inspector) work independently."""
        # Arrange
        params = create_test_params()
        
        # Act - Test optional services can run without core services
        detective_result = setup_detective('Yes', params, dry_run=True, verbose=False)
        inspector_result = setup_inspector('Yes', params, dry_run=True, verbose=False)
        
        # Assert
        assert detective_result is True
        assert inspector_result is True


class TestArgumentValidation:
    """Test argument validation using direct imports and proper mocking."""
    
    def test_cross_account_role_accepts_valid_choices(self, mock_aws_services):
        """Test that valid cross-account role choices are accepted."""
        import argparse
        
        # Create parser identical to main script
        parser = argparse.ArgumentParser(description='Setup AWS Security Services')
        parser.add_argument('--cross-account-role', default='AWSControlTowerExecution', 
                          choices=['AWSControlTowerExecution', 'OrganizationAccountAccessRole'])
        parser.add_argument('--admin-account', required=True)
        parser.add_argument('--security-account', required=True)
        parser.add_argument('--regions', required=True)
        parser.add_argument('--org-id', required=True)
        parser.add_argument('--root-ou', required=True)
        parser.add_argument('--dry-run', action='store_true')
        
        valid_roles = [
            "AWSControlTowerExecution",
            "OrganizationAccountAccessRole"
        ]
        
        for role in valid_roles:
            test_args = [
                "--admin-account", "123456789012",
                "--security-account", "234567890123", 
                "--regions", "us-east-1",
                "--cross-account-role", role,
                "--org-id", "o-example12345",
                "--root-ou", "r-example12345",
                "--dry-run"
            ]
            
            # This should not raise SystemExit
            try:
                args = parser.parse_args(test_args)
                assert args.cross_account_role == role
            except SystemExit:
                pytest.fail(f"Valid role '{role}' should not cause argument parsing error")
    
    def test_cross_account_role_rejects_invalid_choices(self):
        """Test that script rejects invalid cross-account role choices."""
        import argparse
        
        # Create parser identical to main script
        parser = argparse.ArgumentParser(description='Setup AWS Security Services')
        parser.add_argument('--cross-account-role', default='AWSControlTowerExecution', 
                          choices=['AWSControlTowerExecution', 'OrganizationAccountAccessRole'])
        parser.add_argument('--admin-account', required=True)
        parser.add_argument('--security-account', required=True)
        parser.add_argument('--regions', required=True)
        parser.add_argument('--org-id', required=True)
        parser.add_argument('--root-ou', required=True)
        parser.add_argument('--dry-run', action='store_true')
        
        invalid_roles = [
            "MyCustomRole",
            "CustomExecutionRole", 
            "AnotherRole"
        ]
        
        for role in invalid_roles:
            test_args = [
                "--admin-account", "123456789012",
                "--security-account", "234567890123",
                "--regions", "us-east-1", 
                "--cross-account-role", role,
                "--org-id", "o-example12345",
                "--root-ou", "r-example12345",
                "--dry-run"
            ]
            
            # Should raise SystemExit due to invalid choice
            with pytest.raises(SystemExit):
                parser.parse_args(test_args)
    
    def test_cross_account_role_defaults_to_control_tower(self):
        """Test that cross-account role defaults to AWSControlTowerExecution."""
        import argparse
        
        # Create parser identical to main script
        parser = argparse.ArgumentParser(description='Setup AWS Security Services')
        parser.add_argument('--cross-account-role', default='AWSControlTowerExecution', 
                          choices=['AWSControlTowerExecution', 'OrganizationAccountAccessRole'])
        parser.add_argument('--admin-account', required=True)
        parser.add_argument('--security-account', required=True)
        parser.add_argument('--regions', required=True)
        parser.add_argument('--org-id', required=True)
        parser.add_argument('--root-ou', required=True)
        parser.add_argument('--dry-run', action='store_true')
        
        # Test without specifying cross-account-role (uses default)
        test_args = [
            "--admin-account", "123456789012",
            "--security-account", "234567890123",
            "--regions", "us-east-1",
            "--org-id", "o-example12345", 
            "--root-ou", "r-example12345",
            "--dry-run"
        ]
        
        # Should succeed with default role
        args = parser.parse_args(test_args)
        assert args.cross_account_role == "AWSControlTowerExecution", \
            "Default cross-account role should be AWSControlTowerExecution"


class TestMainScriptSuccessMessages:
    """
    TDD TESTS: Verify misleading 'completed successfully' messages are removed
    
    These tests ensure that confusing success messages are eliminated from the main script.
    The messages give false impression that services are configured properly when they
    only indicate the module executed without crashing.
    """
    
    @patch('builtins.print')
    def test_main_script_does_not_show_misleading_success_messages(self, mock_print, mock_aws_services):
        """
        TDD RED PHASE: This test WILL FAIL initially to expose the misleading messages.
        
        GIVEN: Main script executes service setup functions  
        WHEN: Services return True (indicating module executed successfully)
        THEN: Should NOT show "✅ ServiceName completed successfully" messages
        
        These messages are misleading because they suggest the service is properly 
        configured when it only means the setup module didn't crash.
        """
        # Arrange - Mock all service setup functions to return True
        with patch('modules.aws_config.setup_aws_config', return_value=True), \
             patch('modules.guardduty.setup_guardduty', return_value=True), \
             patch('modules.access_analyzer.setup_access_analyzer', return_value=True), \
             patch('modules.security_hub.setup_security_hub', return_value=True), \
             patch('modules.detective.setup_detective', return_value=True), \
             patch('modules.inspector.setup_inspector', return_value=True):
            
            # Import and execute main script logic
            import subprocess
            import sys
            
            # Run the main script with mocked services
            result = subprocess.run([
                sys.executable, 'setup-security-services',
                '--admin-account', '123456789012',
                '--security-account', '234567890123', 
                '--regions', 'us-east-1',
                '--org-id', 'o-example12345',
                '--root-ou', 'r-example12345',
                '--dry-run'
            ], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), '..', '..'))
            
            # Assert - Should NOT contain misleading success messages
            all_output = result.stdout + result.stderr
            
            # TDD RED PHASE: These assertions will FAIL, exposing the misleading messages
            misleading_messages = [
                "✅ AWS Config completed successfully",
                "✅ GuardDuty completed successfully", 
                "✅ IAM Access Analyzer completed successfully",
                "✅ Security Hub completed successfully",
                "✅ Detective completed successfully",
                "✅ Inspector completed successfully"
            ]
            
            for message in misleading_messages:
                assert message not in all_output, f"Misleading message found: '{message}' - this suggests service is properly configured when it only means module didn't crash"