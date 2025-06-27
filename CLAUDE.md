# Foundation Security Services Setup

## 🚨🚨🚨 CRITICAL TESTING RULES - READ FIRST 🚨🚨🚨

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

## Current Status Summary (for New Sessions)

**🎯 PHASE 2: REAL AWS IMPLEMENTATION 83% COMPLETE**: Foundation component with 5 of 6 security services fully implemented with real AWS discovery and comprehensive recommendations.

**✅ Complete AWS Implementation**:
- ✅ **AWS Config**: Full discovery, 4-scenario detection, IAM global recording logic
- ✅ **GuardDuty**: Complete delegation patterns, finding frequency optimization, cross-account discovery
- ✅ **Detective**: Comprehensive investigation graph discovery, GuardDuty dependency validation
- ✅ **Inspector**: Cost-conscious vulnerability scanning with account-specific cost detection  
- ✅ **Access Analyzer**: Global delegation discovery, external/unused access analyzer configuration

**🚧 Remaining Service (Stub → Real AWS Implementation)**:
- 🔸 **Security Hub** (MOST COMPLEX): Control policies, PROD/DEV environments, consolidated findings, organization-wide configuration, standards subscription management

**Implementation Infrastructure**:
- ✅ **Test Architecture**: 147 passing tests with proper AWS mocking (<35 seconds execution)
- ✅ **TDD Methodology**: Proven pattern for service logic fixes and feature additions
- ✅ **Cross-Account Patterns**: Established delegation and role assumption patterns
- ✅ **User Experience**: Clear recommendations and actionable guidance for missing configurations
- ✅ **Service-Specific Logic**: Correct handling of unique service characteristics (e.g., IAM global delegation)

**Next Priority: Security Hub Implementation** (Most complex service requiring organization-wide control policies and PROD/DEV environment differentiation)

### Security Hub Implementation Complexity

**Why Security Hub is Most Complex**:
1. **Organization-wide control policies** - Must create and manage PROD/DEV policy differentiation
2. **Organizational unit assignment** - Different policies for production vs development OUs
3. **Control policy content** - Specific security controls must be enabled/disabled per environment
4. **Consolidated findings** - Central configuration across all regions and accounts
5. **Policy creation order** - Policies must exist before assignment to OUs
6. **Multi-step delegation** - Enable → Delegate → Configure → Create Policies → Assign Policies → Enable Controls

**Key Implementation Challenges**:
- **Policy Management**: PROD policies (strict controls) vs DEV policies (developer-friendly)
- **OU Discovery**: Must identify production vs development organizational units
- **Control Granularity**: Different security controls for different environment types
- **Finding Suppression**: Reset findings after policy changes for clean baseline
- **Cross-Region Coordination**: Ensure consistent policy application across all regions

**Key Files**:
- `setup-security-services` - Main orchestration script with shared `get_client()` function
- `modules/aws_config.py` - Complete AWS Config discovery and reporting (production-ready read-only)
- `modules/guardduty.py` - Complete GuardDuty discovery with cross-account delegation patterns (production-ready read-only)
- `modules/` - Four other service modules with consistent interfaces (stubs ready for AWS implementation)
- `tests/` - Comprehensive test suite ensuring interface stability
- `README.md` - Standalone usage instructions
- `test_real_aws_guardduty.py` - GuardDuty discovery script demonstrating cross-account patterns
- `guardduty_discovery_*.json` - Real AWS GuardDuty data showing delegation and member accounts

**Latest Changes**: Completed IAM Access Analyzer implementation with correct global delegation logic, regional analyzer detection, anomalous region detection, and comprehensive actionable recommendations using TDD methodology.

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
- `--cross-account-role` - Cross-account role name (typically "AWSControlTowerExecution")
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

See the main [CLAUDE.md](../CLAUDE.md#git-workflow--publishing) for complete documentation of the OpenSecOps git workflow, development process, and publishing system.


## Implementation Status

### ✅ Completed - Descriptive Implementation Phase
- [x] Component structure created via `refresh --dev`
- [x] Architecture documented and finalized
- [x] Git repository initialized with proper remotes
- [x] Central orchestration script (`setup-security-services`) implemented
- [x] **5 out of 6 service modules completed with comprehensive real AWS integration**:
  - [x] AWS Config setup module (`modules/aws_config.py`) - **COMPLETE** Real AWS implementation
  - [x] GuardDuty setup module (`modules/guardduty.py`) - **COMPLETE** Real AWS implementation  
  - [x] Detective setup module (`modules/detective.py`) - **COMPLETE** Real AWS implementation with comprehensive discovery
  - [x] Inspector setup module (`modules/inspector.py`) - **COMPLETE** Real AWS implementation with cost-conscious approach & account-specific scanning details
  - [x] Access Analyzer setup module (`modules/access_analyzer.py`) - **COMPLETE** Real AWS implementation
  - [ ] Security Hub setup module (`modules/security_hub.py`) - **PENDING** (stub implementation, most complex service remaining)
- [x] Comprehensive test infrastructure (147 tests, 94% coverage)
- [x] Parameter validation and argparse integration
- [x] Standalone usage capability (independent of OpenSecOps Installer)
- [x] README.md with detailed usage instructions
- [x] Complete TDD implementation with BDD-style specifications
- [x] **Detective Implementation Completed**: Comprehensive real AWS logic with discovery, deactivation detection, and detailed configuration recommendations
- [x] **Inspector Implementation Completed**: Cost-conscious minimal scanning approach with comprehensive account-specific deactivation guidance

### 🚧 Next Phase - Security Hub Implementation
**REMAINING WORK**: Only Security Hub requires real AWS implementation to complete the descriptive implementation phase.

- [ ] **Security Hub real AWS implementation** - Most complex service with:
  - [ ] Multi-region delegation and configuration
  - [ ] PROD and DEV control policy management
  - [ ] Organization-wide finding aggregation setup
  - [ ] Standards subscription management (AWS Foundational, CIS, PCI DSS)
  - [ ] Custom control configuration and exceptions
  - [ ] Finding suppression and policy assignment

### 🔄 Future Phases (After Security Hub)
- [ ] **Mutation Implementation**: Replace TODO placeholders with actual AWS resource creation/modification
- [ ] config-deploy.toml configuration for Installer integration
- [ ] Cross-account role assumption implementation  
- [ ] Idempotency and existing configuration detection
- [ ] End-to-end testing with real AWS environments

### 📋 Future Enhancements
- [ ] Service-specific parameter extensions (e.g., custom Security Hub policies)
- [ ] Advanced safety rules and configuration preservation
- [ ] Performance optimization for large multi-account environments
- [ ] Integration with AWS Organizations APIs for automated account discovery



## Security Hub Implementation Guidance (Next Service - Most Complex)

**READY FOR IMPLEMENTATION**: Complete guidance for implementing Security Hub as the final service in the descriptive implementation phase.

### Why Security Hub is Most Complex

**Organization-Wide Control Policy Management**:
- **Multi-environment policies**: Separate PROD and DEV control policies with different requirements
- **Organizational Unit assignment**: Different policies for production vs development OUs
- **Control-level granularity**: Specific security controls enabled/disabled per environment type
- **Policy creation dependencies**: Policies must exist before assignment to OUs

**AWS Service Dependencies**:
- **Findings aggregation**: Security Hub aggregates findings from GuardDuty, Config, Inspector, Access Analyzer
- **Standards management**: AWS Foundational Security Standard, CIS, PCI DSS subscriptions
- **Cross-service integration**: Requires other security services to be properly configured first

### Security Hub Manual Steps to Automate

**From modules/security_hub.py documentation:**

1. **Org Account (Admin)**: Delegate administration to Security-Adm in all enabled regions
2. **Security-Adm Account**: Set up central configuration and consolidated findings in all regions
3. **Security-Adm Account**: Create PROD and DEV control policies:
   - **PROD Policy**: Multi-zone deployment, backup plans, deletion protection, strict controls
   - **DEV Policy**: Relaxed controls for development ease (allow KMS key deletion, etc.)
   - **Auto-enable new controls**: DISABLED (manual control selection only)
   - **Control selection**: Exact controls needed, one by one selection
4. **Policy Assignment**:
   - **PROD policy → Organization root** (production accounts inherit)
   - **DEV policy → Development OUs** (IndividualBusinessUsers, Sandbox, SDLC OUs)
5. **Finding Reset**: Suppress all findings to reset with new settings (24-hour regeneration)

### Security Hub API Structure and Patterns

**Service Principal**: `securityhub.amazonaws.com`

**Key APIs for Discovery**:
```python
# Delegation Discovery
organizations.list_delegated_administrators(ServicePrincipal='securityhub.amazonaws.com')

# Security Hub Configuration  
securityhub.describe_hub()                    # Hub status per region
securityhub.get_enabled_standards()           # Standards subscriptions (CIS, AWS Foundational, etc.)
securityhub.list_members()                    # Organization member accounts (paginated)
securityhub.get_configuration_policy()        # Control policies (PROD/DEV)
securityhub.list_configuration_policies()     # All policies (paginated)
securityhub.get_configuration_policy_association()  # OU/account policy assignments

# Findings and Controls
securityhub.get_findings()                    # All findings (heavily paginated)
securityhub.describe_standards_controls()     # Available controls per standard
```

**Critical Pagination Requirements**:
- **list_members**: Organization accounts (potentially 100s)
- **get_findings**: Thousands of findings across organization  
- **list_configuration_policies**: Multiple PROD/DEV policies
- **describe_standards_controls**: Hundreds of controls per standard

### Security Hub Implementation Approach

**Follow Established TDD Pattern**:

1. **Create Discovery Script**: `test_real_aws_security_hub.py`
   ```python
   # Based on proven pattern from other services
   # Discover current Security Hub state across all regions
   # Document delegation status, hub configuration, policies, standards
   # Save findings to security_hub_discovery_YYYYMMDD_HHMMSS.json
   ```

2. **Analyze Current State**: 
   - Check if Security Hub already delegated
   - Identify existing configuration policies
   - Document current standards subscriptions  
   - Map current OU policy assignments

3. **Implement Descriptive Logic**:
   ```python
   def setup_security_hub(enabled, params, dry_run, verbose):
       # Phase 1: Delegation discovery (like other services)
       # Phase 2: Hub configuration analysis per region
       # Phase 3: Control policy discovery and OU mapping
       # Phase 4: Standards subscription analysis
       # Phase 5: Comprehensive recommendations for missing setup
   ```

4. **Key Implementation Functions**:
   ```python
   def check_security_hub_delegation(admin_account, security_account, regions, verbose)
   def check_security_hub_in_region(region, admin_account, security_account, cross_account_role, verbose)
   def check_security_hub_policies(regions, admin_account, security_account, cross_account_role, verbose)
   def check_security_hub_standards(regions, admin_account, security_account, cross_account_role, verbose)
   def check_security_hub_ou_assignments(org_id, root_ou, policies, verbose)
   ```

### Security Hub Specific Complexity Factors

**Multi-Environment Policy Logic**:
```yaml
PROD Policy Requirements:
  - Multi-AZ deployment controls: ENABLED
  - Backup plan controls: ENABLED  
  - Deletion protection: ENABLED
  - KMS key deletion: DISABLED
  - Auto-enable new controls: DISABLED

DEV Policy Requirements:
  - Multi-AZ deployment controls: DISABLED
  - Backup plan controls: DISABLED
  - Deletion protection: DISABLED
  - KMS key deletion: ENABLED  
  - Auto-enable new controls: DISABLED
```

**Organizational Unit Mapping**:
```yaml
PROD Policy Assignment:
  - Target: Organization Root (r-example12345)
  - Scope: All accounts inherit unless overridden

DEV Policy Assignment:
  - Targets: 
    - IndividualBusinessUsers OU
    - Sandbox OU  
    - SDLC OU
  - Scope: Development accounts only
```

**Standards Management Complexity**:
```yaml
AWS Foundational Security Standard:
  - Default subscription: REQUIRED
  - Control customization: Per environment
  - Finding suppression: After policy assignment

CIS AWS Foundations Benchmark:
  - Optional subscription: Organization choice
  - Control overlap: With AWS Foundational
  - Environment differences: PROD vs DEV

PCI DSS Standard:
  - Conditional subscription: If PCI compliance needed
  - Control requirements: Strict for payment processing
```

### Security Hub Error Handling Patterns

**Configuration Preservation Priority**:
- **Existing policies**: Never overwrite custom PROD/DEV policies
- **OU assignments**: Preserve existing policy assignments
- **Standards subscriptions**: Don't modify existing standard selections
- **Finding suppressions**: Respect existing suppression rules

**Safety Rules Implementation**:
```python
if existing_prod_policy or existing_dev_policy:
    print("⚠️  Custom Security Hub policies detected - preserving existing configuration")
    print("🔍 Manual review recommended for policy compliance with OpenSecOps standards")
    return True  # Skip policy creation to avoid conflicts

if existing_ou_assignments:
    print("⚠️  Custom OU policy assignments detected - preserving existing assignments")
    print("📋 Review current assignments against OpenSecOps PROD/DEV requirements")
```

### Security Hub Testing Strategy

**Test Implementation Requirements**:
- **14 existing Security Hub tests** (stub implementation coverage)
- **Add 6+ new tests** for real AWS functionality:
  - Delegation discovery and cross-account access
  - Multi-region hub configuration analysis
  - PROD/DEV policy detection and recommendation
  - Standards subscription discovery
  - OU assignment validation
  - Finding suppression guidance

**Complex Mocking Requirements**:
```python
# Mock multi-region Security Hub configuration
def mock_describe_hub_per_region():
    return {'HubArn': 'arn:aws:securityhub:region:account:hub/default'}

# Mock configuration policies (PROD/DEV)
def mock_list_configuration_policies():
    return {'ConfigurationPolicySummaryList': [
        {'Id': 'prod-policy-123', 'Name': 'OpenSecOps-PROD'},
        {'Id': 'dev-policy-456', 'Name': 'OpenSecOps-DEV'}
    ]}
```

### Expected Implementation Output

**When Security Hub Disabled**:
```yaml
Security Hub Deactivation Analysis:
  • Delegation Status: Delegated to Security-Adm (account 234567890123)
  • Hub Configuration: Active in 2 regions (eu-north-1, us-east-1)
  • Control Policies: 2 custom policies detected (PROD, DEV)
  • Policy Assignments: 
    - PROD → Organization Root
    - DEV → 3 development OUs
  • Standards: AWS Foundational (enabled), CIS (enabled)
  • Findings: 1,247 active findings across organization

Recommended Deactivation Steps:
  1. Document current policy configurations for future reference
  2. Remove policy assignments from organizational units
  3. Delete custom PROD/DEV configuration policies
  4. Unsubscribe from security standards per region
  5. Remove member accounts from Security Hub organization  
  6. Disable Security Hub in all regions
  7. Remove Security Hub delegation from Security-Adm account
```

**When Security Hub Enabled but Needs Configuration**:
```yaml
Security Hub Configuration Requirements:
  🌍 Region: eu-north-1
    • Missing: PROD control policy for production accounts
    • Missing: DEV control policy for development accounts  
    • Missing: Policy assignment to organization root (PROD)
    • Missing: Policy assignment to development OUs (DEV)
    • Recommend: Subscribe to AWS Foundational Security Standard
    • Recommend: Configure control customization per environment

  📋 PROD Policy Requirements:
    • Multi-AZ deployment controls: Must be enabled
    • Backup plan inclusion controls: Must be enabled
    • Resource deletion protection: Must be enabled
    • KMS key deletion prevention: Must be enabled
    • Auto-enable new controls: Must be disabled (manual selection)

  📋 DEV Policy Requirements:  
    • Multi-AZ deployment controls: Should be disabled
    • Backup plan inclusion controls: Should be disabled
    • Resource deletion protection: Should be disabled
    • KMS key deletion: Should be allowed for development
    • Auto-enable new controls: Must be disabled (manual selection)
```

**Implementation Priority**: Security Hub is the final service needed to complete the descriptive implementation phase. Its complexity requires the established TDD pattern with real AWS discovery first, followed by comprehensive descriptive logic that provides exact specifications for future mutation implementation.

## Testing

**ALL CRITICAL TESTING RULES ARE AT THE TOP OF THIS DOCUMENT**

This component follows the comprehensive testing methodology established for SOAR, documented at [SOAR/tests/README.md](../SOAR/tests/README.md). The testing strategy uses pytest + moto for AWS service mocking with proven patterns for security-critical components.

**Test Execution:**
```bash
pytest tests/                          # Run all tests  
pytest tests/unit/modules/             # Service module tests
pytest tests/ --cov=. --cov-report=html # With coverage
```

**Key Patterns (based on SOAR methodology):**
- All tests use moto mocking (no real AWS calls)
- Cross-account discovery patterns for delegated admin services
- Pagination required for all AWS list operations
- BDD-style test specifications with GIVEN/WHEN/THEN structure
- Centralized fixture management for consistent test data

## Critical Implementation Learnings

### **Cross-Account Discovery Patterns (MANDATORY)**

**Problem**: Admin accounts have severely limited visibility into delegated security services.
- Admin account shows 0 member accounts, cannot access organization configuration
- Only delegated admin accounts have complete organization visibility
- This affects ALL major AWS security services with delegation

**Solution Pattern (Required for all security services)**:
```python
# 1. Always check delegation status FIRST
orgs_client = boto3.client('organizations', region_name=region)
delegated_admins = orgs_client.list_delegated_administrators(ServicePrincipal='servicename.amazonaws.com')

is_delegated_to_security = False
for admin in delegated_admins.get('DelegatedAdministrators', []):
    if admin.get('Id') == security_account:
        is_delegated_to_security = True
        break

# 2. IF delegated, switch to delegated admin for complete data
if (is_delegated_to_security and cross_account_role and security_account != admin_account):
    delegated_client = get_client('servicename', security_account, region, cross_account_role)
    # Now access real organization configuration and member data
```

**Services Requiring This Pattern**: GuardDuty ✅, Security Hub, Access Analyzer, Detective, Inspector


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