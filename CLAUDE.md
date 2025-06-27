# Foundation Security Services Setup

## Overview

This Foundation component automates the manual security service configuration steps outlined in the OpenSecOps Foundation Installation Manual section "Activations & delegations" (pages 32-33). It eliminates the tedious console-clicking required to enable and configure AWS security services across the organization.

## Problem Statement

The current installation process requires extensive manual configuration through the AWS console:
- GuardDuty delegation and auto-enable setup
- Detective delegation and configuration  
- Inspector delegation and assessment scheduling
- IAM Access Analyzer delegation and organisation-wide setup
- Security Hub delegation and control policy configuration
- AWS Config enablement with proper IAM global event recording

This manual process is error-prone, time-consuming, and inconsistent with OpenSecOps' automation-first philosophy.

## Architecture

### Approach
Following the **Foundation-AWS-Core-SSO-Configuration** pattern, this component uses executable scripts rather than Lambda functions or CloudFormation custom resources. This avoids overengineering while maintaining simplicity and debuggability.

### Component Structure
```
Foundation-security-services-setup/
├── CLAUDE.md                    # This documentation
├── CHANGELOG.md                 # Version history
├── config-deploy.toml           # Deployment configuration with single Script section
├── deploy                       # Main deployment script
├── setup                        # Git setup script
├── publish                      # Publishing script
├── scripts/                     # Standard Foundation scripts (managed by refresh)
│   ├── deploy.py               # Core deployment logic
│   ├── setup.zsh               # Git setup
│   └── publish.zsh             # Publishing workflow
├── setup-security-services     # Central orchestration script with shared utilities
└── modules/                     # Service-specific implementation modules
    ├── __init__.py             # Python package marker
    ├── aws_config.py           # AWS Config setup functions
    ├── guardduty.py            # GuardDuty setup functions
    ├── detective.py            # Detective setup functions
    ├── inspector.py            # Inspector setup functions
    ├── access_analyzer.py      # IAM Access Analyzer setup functions
    └── security_hub.py         # Security Hub setup functions
```

### Script-Based Architecture
**Central Orchestration Approach:**
- Single `setup-security-services` script orchestrates all security service configuration
- Individual service modules in `modules/` directory contain service-specific logic
- Shared utility code (cross-account operations, AWS utilities, validation) lives in the main script
- Services can be selectively enabled/disabled via parameters
- Unified dry-run, idempotency, and error handling across all services

**Important:** The `scripts/` directory is managed by the refresh script and should NOT be used for custom code. It gets deleted and recreated during updates. All custom shared code must go in the main `setup-security-services` script or service modules.

**Each service module:**
1. Can be implemented as **zsh scripts** (using AWS CLI commands) or **Python scripts** (using boto3)
2. Assumes authenticated session via `aws sso login` to admin account with SystemAdministrator access
3. Uses account names/IDs from `Installer/apps/accounts.toml` for cross-account operations
4. Handles cross-account role assumptions (typically to `AWSControlTowerExecution` role)
5. Implements the specific manual steps for that service
6. **Provides idempotent operation** - can be run multiple times safely without side effects
7. **Supports --dry-run mode** - shows what would be done without making changes
8. Includes proper error handling and logging

### Idempotency Requirements
All scripts MUST be idempotent, meaning:
- Check current state before making changes
- Skip operations that are already completed
- Handle partial completion gracefully
- Allow safe re-execution after failures
- Detect and preserve existing configurations

### Safety and Configuration Preservation
**CRITICAL**: Scripts must respect existing configurations and back off when appropriate:
- **Never overwrite existing custom configurations** - only enable services that are completely unconfigured
- **Detect existing setups** and skip configuration if resources already exist in a different configuration
- **Service-specific safety rules** must be implemented per service:
  - Security Hub: If PROD/DEV policies already exist, skip policy creation entirely
  - GuardDuty: If already delegated to a different account, warn and skip
  - Detective: If existing configuration detected, preserve settings
  - Inspector: If custom assessment schedules exist, preserve them
  - Access Analyzer: If analyzers already exist with different scopes, skip creation
  - AWS Config: If delivery channels/configuration recorders exist with different settings, preserve them
- **Always warn the user** when skipping operations due to existing configurations
- **Provide clear status reporting** on what was skipped vs. what was configured

### Dry-Run Support
All scripts MUST support `--dry-run` mode:
- Accept `--dry-run` as a command-line parameter
- Show exactly what operations would be performed
- Make no actual changes to AWS resources
- Validate current state and report differences
- Enable safe testing and validation before execution

### Configuration Integration
**parameters.toml Configuration:**
```toml
# --------------------------------------------------------------
# Foundation-security-services-setup
# --------------------------------------------------------------

[Foundation-security-services-setup]
AWSConfigEnabled = 'Yes'
GuardDutyEnabled = 'Yes'
DetectiveEnabled = 'Yes'
InspectorEnabled = 'Yes'
IAMAccessAnalyzerEnabled = 'Yes'
SecurityHubEnabled = 'Yes'
```

**config-deploy.toml Configuration:**
Single `[[Script]]` section references the central orchestration script:
- References parameters from `Installer/apps/foundation/parameters.toml`
- Support parameter templating (e.g., `{main-region}`, `{security-adm-account}`)
- Service enable/disable flags control which services are configured
- Unified parameter passing to central script

## Manual Steps to Automate

### AWS Config
1. **Org account**: Enable AWS Config in main region, remove IAM global filter
2. **Org account**: Enable AWS Config in other regions, keep IAM global filter

### GuardDuty  
1. **Org account**: Enable GuardDuty in all activated regions
2. **Org account**: Delegate administration to Security-Adm account in all regions
3. **Security-Adm**: Enable and configure auto-enable in all regions

### IAM Access Analyzer
1. **Org account**: Delegate administration to Security-Adm account
2. **Security-Adm**: Set up organisation-wide analyzer for external access (all regions)
3. **Security-Adm**: Set up organisation-wide analyzer for unused access (main region only)

### Amazon Detective
1. **Org account**: Delegate Detective to Security-Adm in all regions
2. **Security-Adm**: Configure Detective in all selected regions

### Amazon Inspector
1. **Org account**: Delegate administration to Security-Adm in all regions
2. **Security-Adm**: Configure Inspector, activate existing accounts, enable auto-activation

### AWS Security Hub
1. **Org account**: Delegate administration to Security-Adm in all regions
2. **Security-Adm**: Set up central configuration and consolidated findings
3. **Security-Adm**: Create PROD and DEV control policies with specific controls
4. **Security-Adm**: Assign PROD policy to org root, DEV policy to development OUs
5. **Security-Adm**: Suppress all findings to reset with new settings

## Standalone Usage

This repository can be used independently of the OpenSecOps Installer for organizations that want to use just the security services setup automation. The `setup-security-services` script accepts all required parameters via command line arguments, making it suitable for integration into other deployment pipelines or manual execution.

See the README.md for detailed standalone usage instructions and parameter examples.

## Deployment Integration

### Authentication & Account Access
**Authentication:**
- Scripts assume `aws sso login` authentication to admin account with SystemAdministrator access
- No additional credential configuration required

**Account Information:**
- Account names and IDs are read from `Installer/apps/accounts.toml`
- Key accounts for security services:
  - **admin-account** (org management account) - where delegations are performed
  - **security-account** (security administration account) - where services are configured
- Account IDs and SSO profiles are dynamically read from accounts.toml
- Cross-account access via SSO profile switching or role assumption

### Parameters Required
- `{security-account}` - Security administration account ID (from accounts.toml)
- `{main-region}` - Primary AWS region
- `{other-regions}` - Additional enabled regions  
- `{all-regions}` - Combined list of main-region + other-regions (auto-generated)
- `{org-id}` - Organization ID
- `{root-ou}` - Root organizational unit ID
- `{cross-account-role}` - Role for cross-account access

### Deployment Sequence
This component deploys after Foundation core components but before manual SSO configuration:
1. **Manual**: AFT setup and account creation
2. **Automated**: Foundation core components (`./deploy-all`)
3. **Automated**: Security services setup (this component)
4. **Manual**: SSO group assignments and verification

## Git Workflow & Publishing

See the main [CLAUDE.md](../CLAUDE.md#git-workflow--publishing) for complete documentation of the OpenSecOps git workflow, development process, and publishing system.

## Implementation Status

- [x] Component structure created via `refresh --dev`
- [x] Architecture documented
- [x] Git repository initialized with proper remotes
- [ ] AWS Config setup script
- [ ] GuardDuty setup script
- [ ] Detective setup script  
- [ ] Inspector setup script
- [ ] Access Analyzer setup script
- [ ] Security Hub setup script
- [ ] config-deploy.toml configuration
- [ ] Parameter integration testing
- [ ] End-to-end testing

## Testing Strategy

### Overview

This Foundation component implements comprehensive test coverage following the proven patterns established in the SOAR testing infrastructure. Given the critical security role and privileged access across AWS accounts, extensive testing is essential for reliability and security validation.

### Strategic Importance

**Critical Security Component**: Foundation Security Services Setup represents a high-risk component due to:
- Organization-wide security service configuration
- Cross-account delegation and role assumptions
- Automated AWS security service setup
- Direct impact on security posture across all accounts

**Testing Priority**: Following SOAR's successful testing model with 428 comprehensive tests achieving 100% auto-remediation coverage.

### Test Infrastructure Strategy

**Chosen Approach: Pure Mocking (pytest + moto)**

**Decision Rationale**:
- ✅ **Proven Success**: Based on SOAR's comprehensive testing infrastructure
- ✅ **Lightweight**: Fast execution without real AWS resources
- ✅ **Zero AWS Costs**: No real AWS resources needed
- ✅ **Easy Setup**: Simple pip install requirements
- ✅ **Offline Development**: Works without internet/AWS credentials
- ✅ **Deterministic**: Consistent results, no flaky tests

### Test Organization

```
tests/
├── conftest.py                    # Shared pytest configuration and fixtures
├── fixtures/                     # Centralized test data management
│   ├── __init__.py
│   ├── aws_parameters.py         # AWS account/region test data
│   └── service_configs.py        # Service-specific configuration data
├── helpers/
│   └── test_helpers.py           # Common testing utilities
├── integration/                  # End-to-end testing with moto
│   ├── test_full_deployment.py   # Complete script execution tests
│   └── test_aws_service_mocking.py # AWS service integration tests
└── unit/                         # Unit tests for individual components
    ├── test_main_script.py       # setup-security-services script
    ├── modules/                  # Service module tests
    │   ├── test_aws_config.py
    │   ├── test_guardduty.py
    │   ├── test_security_hub.py
    │   ├── test_access_analyzer.py
    │   ├── test_detective.py
    │   └── test_inspector.py
    └── test_parameter_validation.py # Argument parsing and validation
```

### Critical Testing Areas

**1. Parameter Validation & Security**
- Required parameter enforcement
- Input sanitization (account IDs, regions, role names)
- Malicious input rejection
- Default value behavior validation

**2. AWS Service Module Safety**
- **Configuration preservation** (existing setups detection)
- **Idempotency validation** (safe re-execution)
- **Dry-run accuracy** (preview vs actual behavior)
- **Error handling** (AWS API failures, permissions)
- **Cross-account operations** (role assumption testing)

**3. Service-Specific Safety Rules**
- **Security Hub**: Existing policy detection and preservation
- **GuardDuty**: Delegation conflict detection and warning
- **Detective**: Existing configuration preservation
- **Inspector**: Custom assessment schedule preservation
- **Access Analyzer**: Existing analyzer scope preservation
- **AWS Config**: Delivery channel/recorder preservation

**4. Integration Testing**
- **Complete workflow execution** (all services enabled/disabled)
- **AWS service mocking** with comprehensive moto coverage
- **Cross-account scenarios** with proper role assumption
- **Failure recovery** and partial completion handling

### Testing Methodology

**1. Documentation-First Analysis** ✅
- Comprehensive function structure analysis before testing
- Complete understanding of all execution paths
- Error handling pattern identification
- AWS API interaction mapping

**2. Security-First Testing**
- Permission validation and role assumption testing
- Input sanitization and validation
- Error handling and graceful degradation
- Cross-account access controls
- Configuration preservation validation

**3. Comprehensive Coverage Requirements**
- **Positive scenarios**: Successful service configuration
- **Negative scenarios**: API failures, permission errors
- **Edge cases**: Missing resources, partial configurations
- **Safety scenarios**: Existing configuration detection
- **Cross-account scenarios**: Multi-account operations

### Running Tests

**Environment Setup:**
```bash
# Install test dependencies
pip install pytest pytest-cov "moto[all]" boto3 python-dotenv

# Copy and configure test environment
cp .env.test.example .env.test
```

**Test Execution:**
```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests
pytest tests/unit/modules/            # Service module tests

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run in parallel for faster execution
pytest tests/ -n auto
```

### Key Testing Learnings and Patterns

**1. AWS Mocking with moto**
- Use `@mock_aws` decorator for comprehensive AWS service mocking
- Handles all AWS services in one decorator (vs individual service decorators)
- Provides realistic AWS API responses without actual AWS calls
- Essential for testing cross-account operations safely

**2. Module Testing Through Main Script Interface**
- Test service modules by importing them directly (not through subprocess)
- Service modules are designed to be imported and called as functions
- This approach allows unit testing while preserving the calling convention
- Tests validate the actual function interfaces used by the main script

**3. Standalone Testing Context**
- Tests work independently of parameter parsing/command-line arguments  
- Tests create parameter dictionaries directly and pass to functions
- Focus on testing function behavior, not argument parsing mechanics
- Enables testing in isolation without dependency on main script argument handling

**4. BDD-Style Specifications**
- All tests follow GIVEN/WHEN/THEN format for readability
- Tests serve as executable specifications and documentation
- Clear descriptions of expected behavior in various scenarios
- Human-readable test names that describe functionality

**5. Defensive Programming Validation**
- Unit tests reveal real bugs in parameter handling (None values, etc.)
- Tests ensure graceful handling of malformed/missing parameters
- Exception handling validation prevents script crashes
- Input sanitization and validation testing

**6. Testing Pyramid Implementation**
- Many unit tests (16 per service module) for detailed behavior validation
- Fewer integration tests (16 total) for main script interface testing  
- Minimal end-to-end tests for complete workflow validation
- Focus on unit testing first, integration testing second

### Test Development Standards

**1. Service Module Testing Pattern**
```python
import pytest
import sys
import os
from unittest.mock import patch

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from modules.aws_config import setup_aws_config
from tests.fixtures.aws_parameters import create_test_params

# Test through direct function import (main script calling convention)
class TestServiceModuleBehavior:
    def test_when_service_enabled_then_returns_success(self):
        """
        GIVEN: Service is enabled in configuration
        WHEN: Service setup function is called
        THEN: Function returns True and performs expected operations
        """
        # Arrange - create test parameters in isolation
        params = create_test_params(
            regions=['us-east-1', 'us-west-2'],
            admin_account='123456789012',
            security_account='234567890123'
        )
        
        # Act - call service function directly
        result = setup_aws_config(
            enabled='Yes', 
            params=params, 
            dry_run=False, 
            verbose=False
        )
        
        # Assert - validate expected behavior
        assert result is True
```

**2. Standalone Parameter Testing**
```python
def test_function_behavior_with_direct_parameters():
    """Test function behavior by passing parameters directly."""
    # Create parameters dictionary without command-line parsing
    params = {
        'regions': ['us-east-1', 'us-west-2'],
        'admin_account': '123456789012',
        'security_account': '234567890123',
        'org_id': 'o-example12345',
        'root_ou': 'r-example12345',
        'cross_account_role': 'AWSControlTowerExecution'
    }
    
    # Test function directly with prepared parameters
    result = service_function(enabled='Yes', params=params, dry_run=True, verbose=False)
    assert result is True
```

**3. AWS Service Mocking Pattern**
```python
from moto import mock_aws
import boto3

@mock_aws
def test_aws_service_interaction():
    """Test AWS service calls with moto mocking."""
    # moto automatically mocks all AWS services
    # No real AWS calls made, no credentials needed
    
    # Create mock AWS resources
    client = boto3.client('guardduty', region_name='us-east-1')
    
    # Mock returns predictable responses
    response = client.list_detectors()
    assert 'DetectorIds' in response
```

**4. Integration Testing Through Main Script**
```python
# Test the actual main script interface used in production
def test_main_script_interface():
    """Test main script by calling functions it imports."""
    # Import the same way main script does
    from modules.aws_config import setup_aws_config
    
    # Call with same parameters main script would use
    params = create_test_params()
    result = setup_aws_config('Yes', params, dry_run=True, verbose=False)
    
    # Validate same interface main script expects
    assert result is True
```

**5. Error Handling and Defensive Testing**
```python
def test_defensive_programming_with_malformed_input():
    """Test graceful handling of edge cases."""
    # Test with None parameters
    result = setup_service(enabled=None, params=None, dry_run=False, verbose=False)
    assert result is True  # Should handle gracefully
    
    # Test with empty parameters
    result = setup_service(enabled='Yes', params={}, dry_run=False, verbose=False)  
    assert result is True  # Should handle missing keys gracefully
```

### Critical Testing Practices

**1. Import Testing (Not Subprocess)**
- Import service modules directly in tests
- Test the actual function interfaces used by main script
- Avoid subprocess calls in unit tests (use integration tests for that)
- Enable proper mocking and assertion validation

**2. Parameter Isolation**
- Create parameter dictionaries directly in tests
- Don't test command-line argument parsing in unit tests
- Focus on function behavior given specific parameters
- Separate argument parsing tests from function behavior tests

**3. Mock AWS Comprehensively**
- Use `@mock_aws` for all AWS service testing
- Mock cross-account role assumptions
- Create predictable AWS resource states for testing
- Test both success and failure scenarios

**4. Test Safety and Idempotency**
- Verify existing resource detection and preservation
- Test multiple execution safety (idempotency)
- Validate dry-run accuracy vs real execution
- Test error recovery and partial completion scenarios

### Test Execution in Standalone Context

Tests are designed to run completely independently:

```bash
# Run tests without any external dependencies
pytest tests/unit/modules/test_aws_config.py -v

# Run with coverage for validation
pytest tests/ --cov=modules --cov-report=term-missing

# Run specific test categories
pytest tests/unit/ -v                    # Pure unit tests
pytest tests/integration/ -v            # Integration tests
```

**IMPORTANT**: Always use `pytest` directly, NOT `python -m pytest`. The Claude permissions system supports wildcards for direct `pytest` commands but not for `python -m pytest` commands due to how it handles multi-word base commands.

All tests work in complete isolation - no external dependencies, AWS credentials, or command-line argument parsing required.

### Security Testing Requirements

For this security-critical component, all tests must validate:
- **Input Validation**: Proper sanitization of all parameters
- **Permission Handling**: Correct IAM role assumptions
- **Error Boundaries**: Graceful handling of all failure modes
- **Configuration Safety**: Preservation of existing setups
- **Audit Trail**: Proper logging of all actions taken

### TDD Development Process

**Phase 1: Test Infrastructure**
1. Create test directory structure and fixtures
2. Set up comprehensive AWS service mocking
3. Establish test data management patterns
4. Validate test runner and coverage tools

**Phase 2: Core Component Testing**
1. Main script parameter parsing and validation
2. Service module interface and error handling
3. Cross-account operation patterns
4. Configuration preservation logic

**Phase 3: Service-Specific Testing**
1. Individual AWS service module testing
2. Service-specific safety rule validation
3. API failure and edge case handling
4. Integration between services

**Phase 4: End-to-End Validation**
1. Complete workflow execution testing
2. Multi-service interaction validation
3. Performance and reliability testing
4. Real-world scenario simulation

### Continuous Integration

Tests are integrated into the development workflow:
- All tests must pass before commits
- Coverage reporting and regression prevention
- Automated test execution on every change
- Performance regression detection

## Design Principles

1. **Idempotent**: Scripts can be run multiple times safely with no side effects
   - Always check current state before attempting operations
   - Handle "already exists" conditions gracefully
   - Support resuming from partial failures
2. **Configurable**: All settings parameterized via `parameters.toml`
3. **Simple**: Script-based approach, no complex infrastructure
4. **Consistent**: Follows established Foundation component patterns
5. **Robust**: Proper error handling and rollback capabilities
6. **Auditable**: Clear logging of all actions taken
7. **Well-Tested**: Comprehensive test coverage ensuring reliability and security