# Foundation Security Services Setup

## 🚨🚨🚨 CRITICAL TESTING RULES - READ FIRST 🚨🚨🚨

### ABSOLUTE RULE #0: ALWAYS USE TDD (TEST-DRIVEN DEVELOPMENT)
**VIOLATION = UNACCEPTABLE REGRESSION RISK**

- ✅ **ALWAYS**: Write tests FIRST, then implement code to pass them
- ✅ **ALWAYS**: Run tests after every change to catch regressions immediately
- ✅ **ALWAYS**: Use Red-Green-Refactor cycle (failing test → passing code → cleanup)
- ❌ **NEVER**: Write code without tests first
- ❌ **NEVER**: Make changes without running tests to verify no regressions

**TDD WORKFLOW REQUIRED:**
1. Write failing test that defines expected behavior
2. Run test to confirm it fails (Red)
3. Write minimal code to make test pass (Green)  
4. Run test to confirm it passes
5. Refactor code while keeping tests green
6. Run all related tests to ensure no regressions

### ABSOLUTE RULE #1: NO REAL AWS API CALLS IN TESTS
**VIOLATION = CRITICAL FAILURE**

- ❌ **NEVER**: Allow tests to make real AWS API calls
- ❌ **NEVER**: Skip `mock_aws_services` fixture in any test
- ✅ **ALWAYS**: Every test method calling AWS services MUST have `mock_aws_services` parameter
- ✅ **ALWAYS**: Use moto mocking for all AWS interactions in tests

**CORRECT TEST SIGNATURE:**
```python
def test_any_aws_function(self, mock_aws_services):
    # All AWS calls will be mocked
```

### ABSOLUTE RULE #2: NO REAL DATA IN TESTS  
**VIOLATION = SECURITY ISSUE**

- ❌ **NEVER**: Real account numbers (use example: 111111111111, 222222222222)
- ❌ **NEVER**: Real org IDs (use example: o-example12345) or OUs (use example: r-example12345)
- ✅ **ALWAYS**: Example data (111111111111, 222222222222, o-example12345)

### WHERE REAL AWS CALLS ARE PERMITTED:
1. **Discovery scripts only**: `test_real_aws_*.py` files (for understanding real AWS state)
2. **Module implementation**: The actual service modules when called by main script (production usage)
3. **NEVER in tests**: Tests must ALWAYS use mocks

### PURPOSE OF REAL DATA:
- **Real data is ONLY for creating logic in modules**: Understanding actual AWS configurations to build proper detection
- **Discovery scripts exist to inform implementation**: Not for production use, just for development understanding
- **Tests simulate behavior without real calls**: Must use mocks to test the logic without AWS dependencies

### TESTING FAILURE SYMPTOMS:
- Tests taking 2+ minutes (instead of seconds)
- Tests timing out  
- "AuthFailure" or credential errors
- Hundreds of AWS API calls during test run

**IF YOU SEE THESE SYMPTOMS: STOP IMMEDIATELY AND FIX THE MOCKING**

### INTEGRATION TEST REQUIREMENT:
Integration tests use subprocess.run() to call the actual script. Since subprocess doesn't inherit mocking, integration tests must set up proper mock environment variables for the subprocess.

**NEVER modify production code for testing!** Production code stays clean.

### 🎯 PROVEN MOCKING ARCHITECTURE (185/185 TESTS PASSING)

**BREAKTHROUGH ACHIEVEMENT**: We have developed a proven testing architecture that achieves:
- ✅ **100% test success rate** (185/185 tests passing)
- ✅ **98% performance improvement** (77+ seconds → <3 seconds)
- ✅ **99.7% warning reduction** (4661+ warnings → 13 warnings)
- ✅ **Zero AWS costs** (no real API calls during testing)
- ✅ **Zero security risk** (no real credentials or data exposure)

#### Data-Driven Mock Configuration

**CRITICAL INSIGHT**: Use data-driven configuration instead of ugly case structures:

```python
# tests/conftest.py - PROVEN PATTERN
SERVICE_MOCK_CONFIGS = {
    'organizations': {
        'list_delegated_administrators': {'DelegatedAdministrators': []},
        'get_paginator': [{'DelegatedAdministrators': []}]
    },
    'guardduty': {
        'list_detectors': {'DetectorIds': []},
        'get_detector': {'Status': 'ENABLED', 'FindingPublishingFrequency': 'FIFTEEN_MINUTES'},
        'list_members': {'Members': []},
        'get_paginator': []
    }
    # Clean, maintainable, no ugly if/elif chains
}

def mock_get_client(service, account_id, region, role_name):
    """Return a pure mock client configured from data."""
    client = MagicMock()
    config = SERVICE_MOCK_CONFIGS.get(service, {})
    
    for method_name, response in config.items():
        if isinstance(response, Exception):
            setattr(client, method_name, MagicMock(side_effect=response))
        else:
            setattr(client, method_name, MagicMock(return_value=response))
    
    return client
```

#### Global Mock Patching Strategy

**CRITICAL SUCCESS FACTOR**: Global `get_client()` patching prevents ALL real AWS calls:

```python
# Patch ALL modules' get_client functions globally
patches = [
    patch('modules.utils.get_client', side_effect=mock_get_client),
    patch('modules.aws_config.get_client', side_effect=mock_get_client),
    patch('modules.guardduty.get_client', side_effect=mock_get_client),
    patch('modules.security_hub.get_client', side_effect=mock_get_client),
    patch('modules.detective.get_client', side_effect=mock_get_client),
    patch('modules.inspector.get_client', side_effect=mock_get_client),
    patch('modules.access_analyzer.get_client', side_effect=mock_get_client),
]
```

#### Performance Optimization Lessons

1. **Pure MagicMock objects** are 98% faster than real boto3 clients under moto
2. **Global patching** eliminates AWS API call leakage that causes performance regression
3. **Data-driven configuration** is cleaner and more maintainable than case structures
4. **Exception mocking** allows testing both success and failure scenarios

#### Testing Pattern Evolution

```python
# ❌ OLD PATTERN (Problematic)
@patch('boto3.client')
def test_function(self, mock_client):
    # Could leak to real AWS calls
    # Complex setup required

# ✅ NEW PATTERN (Proven)
def test_function(self, mock_aws_services):
    # Global mocking prevents all AWS calls
    # Clean test logic, minimal setup
```

#### Advanced Mock Capabilities

**Account Details Testing** for anomalous region detection:
```python
def test_anomalous_detection_with_account_details(self, mock_get_client):
    result = check_anomalous_regions(expected_regions=['us-east-1'])
    
    # Verify account-level details for security actionability
    assert 'account_details' in result[0]
    account_details = result[0]['account_details']
    
    # Check admin and member account details
    admin_accounts = [acc for acc in account_details 
                     if acc.get('account_status') == 'ADMIN_ACCOUNT']
    assert len(admin_accounts) == 1
```

#### Critical Mocking Rules (LEARNED THE HARD WAY)

1. **NEVER create real boto3 clients** even under moto context - use pure MagicMock
2. **ALWAYS use global patching** for `get_client()` across all modules
3. **NEVER use `@patch('boto3.client')`** in individual tests - conflicts with global mocking
4. **ALWAYS configure exception scenarios** for comprehensive error testing
5. **ALWAYS run full test suite** after ANY mocking changes to prevent regressions

## Current Status Summary (for New Sessions)

**🎯 PHASE 2: REAL AWS IMPLEMENTATION 100% COMPLETE**: Foundation component with all 6 security services fully implemented with real AWS discovery and comprehensive recommendations.

**✅ Complete AWS Implementation**:
- ✅ **AWS Config**: Full discovery, 4-scenario detection, IAM global recording logic
- ✅ **GuardDuty**: Complete delegation patterns, finding frequency optimization, cross-account discovery
- ✅ **Detective**: Comprehensive investigation graph discovery, GuardDuty dependency validation
- ✅ **Inspector**: Cost-conscious vulnerability scanning with account-specific cost detection  
- ✅ **Access Analyzer**: Global delegation discovery, external/unused access analyzer configuration
- ✅ **Security Hub**: Consolidated controls validation, auto-enable controls checking, finding aggregation, multi-region delegation

**Implementation Infrastructure**:
- ✅ **Test Architecture**: 185 passing tests with advanced mocking (<3 seconds execution)
- ✅ **TDD Methodology**: Proven pattern for service logic fixes and feature additions
- ✅ **Cross-Account Patterns**: Established delegation and role assumption patterns
- ✅ **User Experience**: Clear recommendations and actionable guidance for missing configurations
- ✅ **Service-Specific Logic**: Correct handling of unique service characteristics (e.g., IAM global delegation)
- ✅ **Advanced Mocking**: Data-driven mock configuration with 98% performance improvement
- ✅ **Security Testing**: Zero AWS costs and zero real API calls during testing
- ✅ **Account Details Enhancement**: Anomalous region detection with actionable account-level details

**Descriptive Implementation Phase Complete**: All security services now have comprehensive real AWS discovery and analysis capabilities.

### Key Files
- `setup-security-services` - Main orchestration script with shared `get_client()` function
- `modules/aws_config.py` - Complete AWS Config discovery and reporting (production-ready read-only)
- `modules/guardduty.py` - Complete GuardDuty discovery with cross-account delegation patterns (production-ready read-only)
- `modules/security_hub.py` - Complete Security Hub discovery with consolidated controls validation (production-ready read-only)
- `modules/detective.py` - Complete Detective discovery with comprehensive graph analysis (production-ready read-only)
- `modules/inspector.py` - Complete Inspector discovery with cost-conscious vulnerability scanning (production-ready read-only)
- `modules/access_analyzer.py` - Complete Access Analyzer discovery with global delegation patterns (production-ready read-only)
- `tests/` - Comprehensive test suite ensuring interface stability (147 passing tests)
- `README.md` - Standalone usage instructions

### Security Hub Implementation Features

**Critical Security Controls Validation**:
- ✅ **Consolidated Controls Detection**: Validates `ControlFindingGenerator: SECURITY_CONTROL` is enabled
- ✅ **Auto-Enable Controls Checking**: Ensures auto-enable is DISABLED (critical for security posture control)
- ✅ **Finding Aggregation**: Verifies cross-region finding aggregation to main region
- ✅ **Standards Subscription Analysis**: Comprehensive analysis of AWS Foundational, CIS, NIST, PCI DSS standards
- ✅ **Multi-Region Delegation**: Proper delegation validation across all configured regions
- ✅ **Member Account Management**: Organization-wide Security Hub membership analysis

## Overview

This Foundation component automates the manual security service configuration steps required to enable and configure AWS security services across the organization. It eliminates the tedious console-clicking required for proper security service delegation and setup.

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
4. Handles cross-account role assumptions (`AWSControlTowerExecution` for Control Tower, `OrganizationAccountAccessRole` for Organizations-only)
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
- Support parameter templating (e.g., `{regions}`, `{security-account}`)
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
- `--admin-account` - Organization management account ID (where delegations are performed)
- `--security-account` - Security administration account ID (where services are configured)
- `--regions` - Comma-separated list of regions (main region first, e.g., "us-east-1,us-west-2,eu-west-1")
- `--cross-account-role` - Cross-account role name (default: "AWSControlTowerExecution", choices: "AWSControlTowerExecution" or "OrganizationAccountAccessRole")
- `--org-id` - AWS Organization ID (e.g., "o-example12345")
- `--root-ou` - Root organizational unit ID (e.g., "r-example12345")

**Service Control Flags** (all with choices=['Yes', 'No']):
- `--aws-config` - Enable AWS Config (default: Yes)
- `--guardduty` - Enable GuardDuty (default: Yes)  
- `--security-hub` - Enable Security Hub (default: Yes)
- `--access-analyzer` - Enable IAM Access Analyzer (default: Yes)
- `--detective` - Enable Detective (default: No, optional service)
- `--inspector` - Enable Inspector (default: No, optional service)

**Standard Flags**:
- `--dry-run` - Preview mode, shows what would be done without making changes
- `--verbose` - Detailed output for debugging and verification

### Deployment Sequence
This component deploys after Foundation core components but before manual SSO configuration:
1. **Manual**: AFT setup and account creation
2. **Automated**: Foundation core components (`./deploy-all`)
3. **Automated**: Security services setup (this component)
4. **Manual**: SSO group assignments and verification

## Git Workflow & Publishing

**IMPORTANT**: This component follows the standard OpenSecOps release process documented in the main [CLAUDE.md](../CLAUDE.md#git-workflow--publishing).

Key points for this component:
- Use the complete release process steps from main CLAUDE.md
- All tests must pass before publishing (`pytest` - currently 185 tests with <3 second execution)
- Follow exact commit message format: `vX.Y.Z`
- Use `./publish` script for clean releases


## Implementation Status

### ✅ Completed - Descriptive Implementation Phase (100% Complete)
- [x] Component structure created via `refresh --dev`
- [x] Architecture documented and finalized
- [x] Git repository initialized with proper remotes
- [x] Central orchestration script (`setup-security-services`) implemented
- [x] **All 6 service modules completed with comprehensive real AWS integration**:
  - [x] AWS Config setup module (`modules/aws_config.py`) - **COMPLETE** Real AWS implementation
  - [x] GuardDuty setup module (`modules/guardduty.py`) - **COMPLETE** Real AWS implementation  
  - [x] Detective setup module (`modules/detective.py`) - **COMPLETE** Real AWS implementation with comprehensive discovery
  - [x] Inspector setup module (`modules/inspector.py`) - **COMPLETE** Real AWS implementation with cost-conscious approach & account-specific scanning details
  - [x] Access Analyzer setup module (`modules/access_analyzer.py`) - **COMPLETE** Real AWS implementation
  - [x] Security Hub setup module (`modules/security_hub.py`) - **COMPLETE** Real AWS implementation with PROD/DEV policy discovery
- [x] Comprehensive test infrastructure (185 tests passing, 100% success rate with advanced mocking)
- [x] Parameter validation and argparse integration
- [x] Standalone usage capability (independent of OpenSecOps Installer)
- [x] README.md with detailed usage instructions
- [x] Complete TDD implementation with BDD-style specifications
- [x] **Security Hub Implementation Completed**: PROD/DEV policy discovery, consolidated controls validation, standards analysis with readable names
- [x] **Repository cleanup**: Removed 21 obsolete discovery files and scripts

### 🔄 Next Phase - Mutation Implementation
**READY TO START**: All descriptive implementations complete, comprehensive recommendations available for mutation logic.

**Mutation Implementation Priority**:
- [ ] **AWS Config Mutation**: Enable Config in regions with proper IAM global event recording
- [ ] **GuardDuty Mutation**: Delegate administration and configure auto-enable for organization
- [ ] **Security Hub Mutation**: Delegate administration, enable consolidated controls, configure finding aggregation
- [ ] **Access Analyzer Mutation**: Create organization-wide analyzers for external and unused access detection
- [ ] **Detective Mutation**: Enable investigation graphs with GuardDuty dependency validation
- [ ] **Inspector Mutation**: Configure vulnerability scanning with cost-conscious minimal approach

**Each Mutation Module Should**:
- Replace current TODO placeholders with actual AWS resource creation/modification
- Implement the exact recommendations shown in dry-run mode
- Maintain idempotency (safe to run multiple times)
- Preserve existing configurations where appropriate
- Use established cross-account patterns with `get_client()` function

### 📋 Implementation Integration (After Mutation)
- [ ] config-deploy.toml configuration for Installer integration
- [ ] Enhanced cross-account role assumption patterns
- [ ] Production deployment testing and validation

### 📋 Future Enhancements
- [ ] Service-specific parameter extensions (e.g., custom Security Hub policies)
- [ ] Advanced safety rules and configuration preservation
- [ ] Performance optimization for large multi-account environments
- [ ] Integration with AWS Organizations APIs for automated account discovery




