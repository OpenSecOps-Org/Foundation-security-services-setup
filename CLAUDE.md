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
├── setup-security-services*    # Central orchestration script
├── modules/                     # Service-specific implementation modules
│   ├── aws_config.py*          # AWS Config setup functions
│   ├── guardduty.py*           # GuardDuty setup functions
│   ├── detective.py*           # Detective setup functions
│   ├── inspector.py*           # Inspector setup functions
│   ├── access_analyzer.py*     # IAM Access Analyzer setup functions
│   └── security_hub.py*        # Security Hub setup functions
└── lib/                         # Shared utility code (if needed)
    ├── __init__.py*            # Python package marker
    ├── aws_utils.py*           # Common AWS operations
    ├── cross_account.py*       # Cross-account role assumption
    └── validation.py*          # Common validation functions

* = To be implemented
```

### Script-Based Architecture
**Central Orchestration Approach:**
- Single `setup-security-services` script orchestrates all security service configuration
- Individual service modules in `modules/` directory contain service-specific logic
- Shared utility code in `lib/` directory (cross-account operations, AWS utilities, validation)
- Services can be selectively enabled/disabled via parameters
- Unified dry-run, idempotency, and error handling across all services

**Important:** The `scripts/` directory is managed by the refresh script and should NOT be used for custom code. It gets deleted and recreated during updates. All custom shared code must go in the `lib/` directory.

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
- `{security-adm-account}` - Security administration account ID (from accounts.toml)
- `{main-region}` - Primary AWS region
- `{other-regions}` - Additional enabled regions
- `{org-id}` - Organization ID
- `{cross-account-role}` - Role for cross-account access

### Deployment Sequence
This component deploys after Foundation core components but before manual SSO configuration:
1. **Manual**: AFT setup and account creation
2. **Automated**: Foundation core components (`./deploy-all`)
3. **Automated**: Security services setup (this component)
4. **Manual**: SSO group assignments and verification

## Git Workflow & Publishing

See the main [CLAUDE.md](../CLAUDE.md#git-workflow--publishing) for complete documentation of the OpenSecOps git workflow, development process, and publishing system.

### CRITICAL WARNING: Never Push Directly to OpenSecOps Repositories

**NEVER** push directly to OpenSecOps organization repositories (e.g., `https://github.com/OpenSecOps-Org/Foundation-security-services-setup.git`). This will:

- Pollute the clean release history with messy development commits
- Break the established dual-repository workflow 
- Require deletion and recreation of the entire OpenSecOps repository
- Destroy the professional appearance of published repositories

**Always use the `./publish` script** which:
- Collapses all development commits into clean release commits
- Manages the dual repository structure properly  
- Maintains professional public history in OpenSecOps repositories
- Preserves full development history in personal DEV repositories

**Development workflow**: Commit freely to the development repository (`origin`), then use `./publish` for clean releases to OpenSecOps.

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