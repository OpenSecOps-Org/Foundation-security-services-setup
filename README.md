# Foundation Security Services Setup

**Automated AWS security service configuration for infrastructure engineers**

## The Problem

Setting up AWS security services across an organization is **time-consuming, repetitive, and error-prone**. Infrastructure engineers face several challenges:

### Manual Configuration Pain Points
- **Time-consuming setup**: Each service requires multiple console clicks across regions and accounts
- **Repetitive delegation**: Every service needs manual delegation from org account to security account  
- **Inconsistent procedures**: Each service has subtly different configuration steps and requirements
- **Error-prone process**: Manual steps lead to misconfigurations and security gaps
- **Difficult to disable**: Reversing the setup is equally laborious with different procedures per service

### The Current Reality
Infrastructure engineers typically spend **hours or days** manually:
- Enabling GuardDuty in each region and delegating to security account
- Configuring Detective with proper region selection
- Setting up Inspector with auto-activation for existing and new accounts
- Creating IAM Access Analyzer with organization-wide scope
- Configuring Security Hub with PROD/DEV control policies
- Enabling AWS Config with correct IAM global event recording

## The Solution

**This Foundation component solves the configuration complexity** by providing a single, automated interface. Infrastructure engineers can now:

✅ **Specify what they want**: Simple Yes/No flags for each service  
✅ **Let automation handle the rest**: All configuration complexity handled automatically  
✅ **Work consistently**: Same interface whether running standalone or with OpenSecOps  
✅ **Preview changes safely**: Dry-run mode shows exactly what will be configured  
✅ **Scale effortlessly**: Configure across multiple regions and accounts simultaneously  

### Before vs After

**Before** (Manual Process):
```
1. Log into org management account console
2. Navigate to GuardDuty → Enable in us-east-1 → Delegate to security account
3. Repeat step 2 for us-west-2, eu-west-1...
4. Log into security account → Accept delegations in each region
5. Configure auto-enable for new accounts in each region
6. Navigate to Security Hub → Enable → Delegate...
7. Repeat for Detective, Inspector, Access Analyzer, Config...
   [Hours of repetitive console clicking]
```

**After** (Automated):
```bash
./setup-security-services \
  --admin-account 123456789012 \
  --security-account 234567890123 \
  --regions us-east-1,us-west-2,eu-west-1 \
  --cross-account-role AWSControlTowerExecution \
  --org-id o-example12345 \
  --root-ou r-example12345 \
  --dry-run

# ✅ All services configured in minutes
```

## Overview

This Foundation component automates AWS security service configuration, supporting both OpenSecOps integrated deployments and standalone usage. It configures the following services:

* **AWS Config** - Enables configuration recording with proper IAM global event settings
* **GuardDuty** - Sets up delegation to Security-Adm account with auto-enable for new accounts
* **Security Hub** - Configures central security findings with control policies for PROD/DEV environments
* **IAM Access Analyzer** - Creates organization-wide analyzers for external and unused access
* **Detective** - Configures threat investigation capabilities (optional)
* **Inspector** - Sets up vulnerability assessment with auto-activation (optional)

All services are properly delegated from the organization management account to the designated security administration account.

## Prerequisites

* AWS CLI configured with SystemAdministrator access to the organization management account
* Active AWS SSO login session

## Configuration (OpenSecOps Installer Only)

When running as part of the OpenSecOps Installer, services can be enabled/disabled via parameters in `Installer/apps/foundation/parameters.toml`:

```toml
[Foundation-security-services-setup.setup-security-services]
AWSConfigEnabled = 'Yes'
GuardDutyEnabled = 'Yes'
SecurityHubEnabled = 'Yes'
IAMAccessAnalyzerEnabled = 'Yes'
DetectiveEnabled = 'No'
InspectorEnabled = 'No'
```

**Note**: This configuration method only applies when using the OpenSecOps Installer. For standalone usage, all parameters are passed via command-line arguments as shown in the usage examples below.

## Deployment

### Using OpenSecOps Installer

Ensure you're authenticated to your organization management account:

```console
aws sso login
```

Deploy the security services setup:

```console
./deploy
```

The script will:
1. Read account information from the Installer configuration
2. Configure enabled services in the organization management account
3. Delegate administration to the security account
4. Set up service-specific configurations and policies

### Standalone Usage

You can also run the setup script directly without the OpenSecOps Installer:

```console
./setup-security-services \
  --admin-account 123456789012 \
  --security-account 234567890123 \
  --regions us-east-1,us-west-2,eu-west-1 \
  --cross-account-role AWSControlTowerExecution \
  --org-id o-example12345 \
  --root-ou r-example12345 \
  --dry-run
```

To disable specific services or enable optional ones:

```console
./setup-security-services \
  --admin-account 123456789012 \
  --security-account 234567890123 \
  --regions us-east-1,us-west-2,eu-west-1 \
  --cross-account-role AWSControlTowerExecution \
  --org-id o-example12345 \
  --root-ou r-example12345 \
  --security-hub No \
  --detective Yes \
  --inspector Yes \
  --dry-run
```

**Required Parameters:**
- `--admin-account`: Organization management account ID
- `--security-account`: Security administration account ID  
- `--regions`: Comma-separated list of regions (main region first)
- `--cross-account-role`: Role name for cross-account access
- `--org-id`: AWS Organization ID
- `--root-ou`: Root organizational unit ID

**Optional Parameters:**
- `--aws-config`, `--guardduty`, `--security-hub`, `--access-analyzer`: Enable/disable core services (Yes/No, default: Yes)
- `--detective`, `--inspector`: Enable/disable optional services (Yes/No, default: No)
- `--dry-run`: Preview changes without making modifications
- `--verbose`: Additional debugging output

## Key Features

* **Non-destructive operation** - Never overwrites existing configurations, backs off safely when services are already configured
* **Idempotent operation** - Safe to run multiple times with consistent results
* **Configuration detection** - Identifies existing setups and reports what's already configured
* **Dry-run support** - Preview changes without making modifications
* **Selective service enablement** - Enable only the services you need
* **Automated cross-account setup** - Handles delegation and role assumptions
* **Organization-wide coverage** - Configures services across all accounts
* **Comprehensive validation** - Robust parameter validation and error handling
* **Standalone or integrated** - Works with OpenSecOps or as independent utility

## Value Proposition

**Time Savings**: What used to take hours or days of manual configuration now takes minutes  
**Consistency**: Eliminates configuration drift and human error across environments  
**Flexibility**: Enable exactly the services you need with simple Yes/No configuration  
**Safety**: Non-destructive operation, dry-run mode, and comprehensive testing ensure reliable operations  
**Peace of Mind**: Never overwrites existing configurations - completely safe to run in any environment  
**Scalability**: Handle complex multi-region, multi-account scenarios effortlessly

## Safety & Non-Destructive Operation

This utility is designed to be **completely safe** when run against existing AWS environments:

### Configuration Detection & Preservation
- **Detects existing setups**: Automatically identifies services that are already configured
- **Backs off gracefully**: Never overwrites or modifies existing custom configurations
- **Reports current state**: Shows you what's already configured and how
- **Preserves custom settings**: Maintains existing policies, settings, and delegations

### What Happens with Already Configured Services
When the utility encounters services that are already set up:

✅ **Security Hub with existing policies** → Skips policy creation, reports existing PROD/DEV policies  
✅ **GuardDuty already delegated** → Skips delegation, reports current delegation to different account (with warning)  
✅ **Detective with existing configuration** → Preserves settings, reports current region configuration  
✅ **Inspector with custom schedules** → Maintains custom assessment schedules, reports existing setup  
✅ **Access Analyzer with different scopes** → Skips creation, reports existing analyzer configurations  
✅ **AWS Config with different delivery channels** → Preserves existing channels and configuration recorders  

### Safety Guarantees
- **No configuration loss**: Existing setups are never overwritten or deleted
- **Clear status reporting**: Always tells you what was skipped and why
- **Warning system**: Alerts when existing configurations differ from expected setup
- **Rollback unnecessary**: Since nothing destructive happens, no rollback mechanism needed

This makes the utility safe to run in any environment, whether services are already configured or not.

## What Gets Configured

* **AWS Config**: Enabled with proper IAM global event recording settings
* **GuardDuty**: Delegated with auto-enable for new members and existing accounts
* **Security Hub**: Central configuration with PROD/DEV control policies
* **Access Analyzer**: Organization-wide analyzers for external and unused access detection
* **Detective**: Investigation capabilities across the organization (if enabled)
* **Inspector**: Vulnerability assessments with auto-activation (if enabled)

## Testing

This component includes comprehensive test coverage following TDD methodology with pytest and AWS mocking.

### Running Tests

**Install test dependencies:**
```console
pip install pytest pytest-cov "moto[all]" boto3
```

**Run all tests:**
```console
pytest tests/
```

**Run specific test categories:**
```console
pytest tests/unit/                     # Unit tests only
pytest tests/integration/              # Integration tests only
pytest tests/unit/modules/             # Service module tests
```

**Run with coverage:**
```console
pytest tests/ --cov=modules --cov-report=term-missing
```

**Run tests for specific service:**
```console
pytest tests/unit/modules/test_aws_config.py -v
```

### Test Categories

* **Unit Tests**: Test individual service modules and parameter validation
  - AWS Config module: comprehensive tests covering all functionality
  - Parameter validation: tests for security and input validation
* **Integration Tests**: Test main script execution and service coordination
  - Script execution flow, parameter parsing, error handling
  - Service module integration through main script interface

All tests use AWS mocking (moto) for safe testing without real AWS resources. Tests work in complete isolation with no external dependencies.