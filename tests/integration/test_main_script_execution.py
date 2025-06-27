"""
Integration tests for the main setup-security-services script execution.

This module tests the complete script execution flow including parameter
parsing, service module execution, and overall coordination through the
actual main script interface.
"""

import pytest
import subprocess
import sys
import os
from unittest.mock import patch

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.fixtures.aws_parameters import create_test_params, create_service_flags
from tests.helpers.test_helpers import create_test_argv


class TestMainScriptExecution:
    """Test complete main script execution through subprocess calls."""
    
    def test_help_display(self):
        """Test that help is displayed correctly."""
        result = subprocess.run(
            [sys.executable, './setup-security-services', '--help'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        
        assert result.returncode == 0
        assert 'Setup AWS Security Services' in result.stdout
        assert '--admin-account' in result.stdout
        assert '--regions' in result.stdout
        assert '--dry-run' in result.stdout
    
    def test_missing_required_parameters(self):
        """Test that missing required parameters cause proper error."""
        result = subprocess.run(
            [sys.executable, './setup-security-services', '--admin-account', '123456789012'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        
        assert result.returncode == 2  # argparse error exit code
        assert 'required' in result.stderr.lower()
    
    def test_dry_run_execution_success(self):
        """Test successful dry-run execution with all required parameters."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123', 
            '--regions', 'us-east-1,us-west-2',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        assert 'DRY RUN MODE' in result.stdout
        assert 'Foundation Security Services Setup' in result.stdout
        assert 'FINAL SUMMARY' in result.stdout
    
    def test_verbose_output(self):
        """Test verbose mode displays parameter information."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1,us-west-2',
            '--cross-account-role', 'AWSControlTowerExecution', 
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run', '--verbose'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        assert 'VERBOSE MODE' in result.stdout
        assert '123456789012' in result.stdout  # admin account displayed
        assert 'us-east-1,us-west-2' in result.stdout  # regions displayed
    
    def test_service_flag_defaults(self):
        """Test that default service flags work correctly."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345', 
            '--root-ou', 'r-example12345',
            '--dry-run', '--verbose'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        # Verify default values are shown in verbose output
        assert '--aws-config: Yes' in result.stdout
        assert '--guardduty: Yes' in result.stdout
        assert '--security-hub: Yes' in result.stdout
        assert '--access-analyzer: Yes' in result.stdout
        assert '--detective: No' in result.stdout
        assert '--inspector: No' in result.stdout
    
    def test_custom_service_flags(self):
        """Test execution with custom service flags."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--aws-config', 'No',
            '--guardduty', 'Yes',
            '--security-hub', 'No', 
            '--access-analyzer', 'Yes',
            '--detective', 'Yes',
            '--inspector', 'No',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run', '--verbose'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        # Verify custom values are reflected
        assert '--aws-config: No' in result.stdout
        assert '--detective: Yes' in result.stdout
    
    def test_multiple_regions_parsing(self):
        """Test that multiple regions are parsed and handled correctly."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1,us-west-2,eu-west-1,ap-southeast-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run', '--verbose'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        # Verify regions are parsed correctly (shown in AWS Config output)
        assert 'main region (us-east-1)' in result.stdout
        assert "other regions (['us-west-2', 'eu-west-1', 'ap-southeast-1'])" in result.stdout
    
    def test_all_services_processing(self):
        """Test that all services are processed in the correct order."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123', 
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        
        # Verify all services are processed in expected order
        output = result.stdout
        
        # Check service processing messages appear
        assert '🔧 Processing AWS Config...' in output
        assert '🔧 Processing GuardDuty...' in output 
        assert '🔧 Processing Security Hub...' in output
        assert '🔧 Processing IAM Access Analyzer...' in output
        assert '🔧 Processing Detective...' in output
        assert '🔧 Processing Inspector...' in output
        
        # Check success messages
        assert '✅ AWS Config completed successfully' in output
        assert '✅ GuardDuty completed successfully' in output
        assert '✅ Security Hub completed successfully' in output
        
        # Check final summary
        assert 'FINAL SUMMARY' in output
        assert 'All services processed successfully!' in output


class TestServiceModuleIntegration:
    """Test individual service modules through main script execution."""
    
    def test_aws_config_enabled(self):
        """Test AWS Config service when enabled."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--aws-config', 'Yes',
            '--guardduty', 'No',
            '--security-hub', 'No',
            '--access-analyzer', 'No', 
            '--detective', 'No',
            '--inspector', 'No',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1,us-west-2',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        assert 'AWS CONFIG SETUP' in result.stdout
        assert 'Would enable AWS Config in main region (us-east-1)' in result.stdout
        assert 'Would enable AWS Config in other regions' in result.stdout
    
    def test_aws_config_disabled(self):
        """Test AWS Config service when disabled."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--aws-config', 'No',
            '--guardduty', 'No',
            '--security-hub', 'No',
            '--access-analyzer', 'No',
            '--detective', 'No', 
            '--inspector', 'No',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        assert 'AWS CONFIG SETUP' in result.stdout
        assert 'AWS Config is disabled - skipping' in result.stdout
    
    def test_guardduty_enabled(self):
        """Test GuardDuty service when enabled."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--aws-config', 'No',
            '--guardduty', 'Yes',
            '--security-hub', 'No',
            '--access-analyzer', 'No',
            '--detective', 'No',
            '--inspector', 'No',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        assert 'GUARDDUTY SETUP' in result.stdout
        assert 'Would enable GuardDuty in all activated regions' in result.stdout
        assert 'Would delegate administration to Security-Adm account' in result.stdout
    
    def test_security_hub_enabled(self):
        """Test Security Hub service when enabled."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--aws-config', 'No',
            '--guardduty', 'No', 
            '--security-hub', 'Yes',
            '--access-analyzer', 'No',
            '--detective', 'No',
            '--inspector', 'No',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        assert 'SECURITY HUB SETUP' in result.stdout
        assert 'Would delegate administration to Security-Adm account' in result.stdout
        assert 'Would create PROD and DEV control policies' in result.stdout
    
    def test_detective_optional_service(self):
        """Test Detective as optional service (disabled by default)."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--aws-config', 'No',
            '--guardduty', 'No',
            '--security-hub', 'No',
            '--access-analyzer', 'No',
            '--detective', 'No',  # Explicitly disabled
            '--inspector', 'No',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        assert result.returncode == 0
        assert 'DETECTIVE SETUP' in result.stdout
        assert 'Detective is disabled - skipping' in result.stdout


class TestErrorHandlingIntegration:
    """Test error handling through main script execution."""
    
    def test_invalid_account_id_format(self):
        """Test handling of invalid account ID format."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', 'invalid-account',  # Invalid format
            '--security-account', '234567890123',
            '--regions', 'us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Script should handle this gracefully (validation depends on implementation)
        # For now, just verify it doesn't crash
        assert result.returncode == 0
    
    def test_invalid_region_format(self):
        """Test handling of invalid region format.""" 
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', 'invalid-region,us-east-1',
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Script should handle this gracefully 
        assert result.returncode == 0
    
    def test_empty_regions_parameter(self):
        """Test handling of empty regions parameter."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', '',  # Empty regions
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Script should exit with error code 1 for empty regions
        assert result.returncode == 1, f"Expected exit code 1, got {result.returncode}"
        # Error messages go to stdout, not stderr in our implementation
        assert "ERROR: At least one region must be specified" in result.stdout
        assert "cannot be empty or contain only whitespace" in result.stdout
    
    def test_whitespace_only_regions_parameter(self):
        """Test handling of whitespace-only regions parameter."""
        result = subprocess.run([
            sys.executable, './setup-security-services',
            '--admin-account', '123456789012',
            '--security-account', '234567890123',
            '--regions', '   ',  # Whitespace-only regions
            '--cross-account-role', 'AWSControlTowerExecution',
            '--org-id', 'o-example12345',
            '--root-ou', 'r-example12345',
            '--dry-run'
        ], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Script should exit with error code 1 for whitespace-only regions
        assert result.returncode == 1, f"Expected exit code 1, got {result.returncode}"
        # Error messages go to stdout, not stderr in our implementation
        assert "ERROR: At least one region must be specified" in result.stdout
        assert "cannot be empty or contain only whitespace" in result.stdout