"""
Integration tests for the main setup-security-services script logic.

This module tests the complete script logic flow including service module
execution and coordination by directly importing and calling functions.
All tests use mocked AWS services for fast, reliable testing.
"""

import pytest
import sys
import os
from unittest.mock import patch

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