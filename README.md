# Foundation Security Services Setup

**Automated AWS security service configuration for infrastructure engineers**

> **⚠️ PRE-RELEASE VERSION (v0.1.0)**: This version provides comprehensive read-only analysis and discovery of AWS security services. It does not yet mutate AWS resources. Full automation capabilities coming in v1.0.0.

## The Problem

Setting up AWS security services across an organization is time-consuming, repetitive, and error-prone. Infrastructure engineers typically spend hours or days manually:

- **Time-consuming setup**: Each service requires multiple console clicks across regions and accounts
- **Repetitive delegation**: Every service needs manual delegation from org account to security account  
- **Inconsistent procedures**: Each service has subtly different configuration steps and requirements
- **Error-prone process**: Manual steps lead to misconfigurations and security gaps

### Before vs After

**Before** (Manual Process):
1. Log into org management account console
2. Navigate to GuardDuty → Enable in us-east-1 → Delegate to security account
3. Repeat step 2 for us-west-2, eu-west-1...
4. Log into security account → Accept delegations in each region
5. Configure auto-enable for new accounts in each region
6. Navigate to Security Hub → Enable → Delegate...
7. Repeat for Detective, Inspector, Access Analyzer, Config...
   [Hours of repetitive console clicking]

**After** (Automated):
```bash
./deploy
# ✅ All services configured in minutes
```

## The Solution

This Foundation component automates AWS security service configuration, supporting both OpenSecOps integrated deployments and standalone usage. It configures the following services:

* **AWS Config** - Enables configuration recording with proper IAM global event settings
* **GuardDuty** - Sets up delegation to Security-Adm account with auto-enable for new accounts
* **Security Hub** - Configures central security findings with control policies for PROD/DEV environments
* **IAM Access Analyzer** - Creates organization-wide analyzers for external and unused access
* **Detective** - Configures threat investigation capabilities (optional)
* **Inspector** - Sets up vulnerability assessment with auto-activation (optional)

All services are properly delegated from the organization management account to the designated security administration account.

## Key Benefits

✅ **Time Savings**: What used to take hours or days now takes minutes  
✅ **Consistency**: Eliminates configuration drift and human error across environments  
✅ **Flexibility**: Enable exactly the services you need with simple Yes/No configuration  
✅ **Safety**: Non-destructive operation with dry-run mode and comprehensive testing  
✅ **Peace of Mind**: Never overwrites existing configurations - completely safe to run  
✅ **Scalability**: Handle complex multi-region, multi-account scenarios effortlessly

## Prerequisites

* AWS CLI configured with SystemAdministrator access to the organization management account
* Active AWS SSO login session

## Usage

### OpenSecOps Installer Integration

When running as part of the OpenSecOps Installer, services are enabled/disabled via parameters in `Installer/apps/foundation/parameters.toml`:

```toml
# --------------------------------------------------------------
# Foundation-security-services-setup
# --------------------------------------------------------------

[Foundation-security-services-setup.setup-security-services]

AWSConfigEnabled = 'Yes'
GuardDutyEnabled = 'Yes'
SecurityHubEnabled = 'Yes'
IAMAccessAnalyzerEnabled = 'Yes'
DetectiveEnabled = 'No'
InspectorEnabled = 'No'

admin-account = '{admin-account}'
security-account = '{security-account}'
main-region = '{main-region}'
other-regions = '{other-regions}'
all-regions = '{all-regions}'
cross-account-role = '{cross-account-role}'
org-id = '{org-id}'
root-ou = '{root-ou}'
```

**repos.toml configuration** (required for existing installations):
```toml
[[repos]]
name = "Foundation-security-services-setup"
```
Add this entry under `Foundation-AWS-Core-SSO-Configuration` in `Installer/apps/foundation/repos.toml`, or copy `Installer/apps.example/foundation/repos.toml` to `Installer/apps/foundation/repos.toml`.

**Getting Started**: 
- **New installation**: No action needed
- **Existing installation**: Copy the complete `Foundation-security-services-setup` section from `Installer/apps.example/foundation/parameters.toml` and add to your existing parameters file

Deploy with:
```console
aws sso login
./deploy
```

### Standalone Usage

You can run the setup script directly without the OpenSecOps Installer:

**Basic usage:**
```console
./setup-security-services \
  --admin-account 111111111111 \
  --security-account 222222222222 \
  --regions us-east-1,us-west-2,eu-west-1 \
  --cross-account-role AWSControlTowerExecution \
  --org-id o-example12345 \
  --root-ou r-example12345
```

**With service customization:**
```console
./setup-security-services \
  --admin-account 111111111111 \
  --security-account 222222222222 \
  --regions us-east-1,us-west-2,eu-west-1 \
  --cross-account-role AWSControlTowerExecution \
  --org-id o-example12345 \
  --root-ou r-example12345 \
  --security-hub No \
  --detective Yes \
  --inspector Yes
```

**Parameters:**
- **Required**: `--admin-account`, `--security-account`, `--regions`, `--cross-account-role`, `--org-id`, `--root-ou`
- **Core Services** (default: Yes): `--aws-config`, `--guardduty`, `--security-hub`, `--access-analyzer`
- **Optional Services** (default: No): `--detective`, `--inspector`
- **Flags**: `--dry-run` (preview changes), `--verbose` (detailed output)

## Safety & Non-Destructive Operation

This utility is designed to be **completely safe** when run against existing AWS environments:

### Configuration Detection & Preservation
- **Detects existing setups**: Automatically identifies services that are already configured
- **Backs off gracefully**: Never overwrites or modifies existing custom configurations
- **Reports current state**: Shows you what's already configured and how
- **Preserves custom settings**: Maintains existing policies, settings, and delegations

### What Happens with Already Configured Services
✅ **Security Hub with existing policies** → Skips policy creation, reports existing PROD/DEV policies  
✅ **GuardDuty already delegated** → Skips delegation, reports current delegation (with warning if different)  
✅ **Detective with existing configuration** → Preserves settings, reports current region configuration  
✅ **Inspector with custom schedules** → Maintains custom assessment schedules  
✅ **Access Analyzer with different scopes** → Skips creation, reports existing configurations  
✅ **AWS Config with different delivery channels** → Preserves existing channels and recorders  

## Output Examples

### ✅ When Services Meet Standards
```console
✅ GuardDuty is already properly configured in all regions!
   No changes needed - existing setup meets stringent security standards.
```

### ⚠️ When Services Need Configuration
```console
⚠️  GuardDuty needs configuration in some regions:
  • us-east-1: GuardDuty is not enabled in this region
  • us-west-2: Finding frequency is 6 hours - too slow for optimal threat detection
  • eu-west-1: GuardDuty delegated to 999888777666 instead of Security account 234567890123

🔧 Making GuardDuty changes...
  • us-east-1: Enable GuardDuty and create detector
  • us-west-2: Set finding frequency to FIFTEEN_MINUTES for optimal security
  • eu-west-1: Remove existing delegation and delegate to Security account
```

### 📊 Verbose Mode (--verbose)
```console
🔍 Checking GuardDuty in region us-east-1...
✅ GuardDuty properly configured in us-east-1

📋 Current GuardDuty Configuration:
🌍 Region: us-east-1
✅ GuardDuty Detector: abcd1234efgh5678
   ✅ Status: ENABLED
   ✅ Finding Frequency: FIFTEEN_MINUTES (optimal)
✅ Delegated Admin: Security-Administration-Account
✅ Organization Auto-Enable: True
✅ Member Accounts: 12 found
   ✅ All 12 member accounts are enabled
```

### 🔍 Dry-Run Mode (--dry-run)
```console
🔍 DRY RUN: Would make the following changes:
  • us-east-1: Enable GuardDuty and create detector
  • us-west-2: Set finding frequency to FIFTEEN_MINUTES for optimal security
  • eu-west-1: Delegate GuardDuty administration to Security account
```

### 🚨 Service Disable Warnings
```console
🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
🚨 CRITICAL WARNING: AWS Config Disable Requested! 🚨
🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨

AWS Config is a CRITICAL security service that:
• Provides configuration compliance monitoring
• Enables Security Hub controls and findings
• Records resource configuration changes

⛔ DISABLING CONFIG WILL BREAK SECURITY MONITORING!
Config setup SKIPPED due to enabled=No parameter.
```

## Testing

This component includes comprehensive test coverage with pytest and AWS mocking.

**Install dependencies:**
```console
pip install pytest pytest-cov "moto[all]" boto3
```

**Run tests:**
```console
pytest tests/                              # All tests
pytest tests/unit/                         # Unit tests only
pytest tests/integration/                  # Integration tests only
pytest tests/ --cov=modules --cov-report=term-missing  # With coverage
```

All tests use AWS mocking (moto) for safe testing without real AWS resources.

## Example Output

```console
============================================================
  Foundation Security Services Setup
------------------------------------------------------------

============================================================
AWS CONFIG SETUP
============================================================
Checking AWS Config setup in 2 regions...
✅ AWS Config is already properly configured in all regions!
   No changes needed - existing setup meets stringent security standards.
✅ AWS Config completed successfully

============================================================
GUARDDUTY SETUP
============================================================
Checking GuardDuty setup in 2 regions...
✅ GuardDuty is already properly configured in all regions!
   No changes needed - existing setup meets stringent security standards.
✅ GuardDuty completed successfully

============================================================
SECURITY HUB SETUP
============================================================
✅ Security Hub is optimally configured for consolidated controls
✅ Consolidated controls enabled in all 2 regions
✅ Auto-enable controls correctly disabled (manual control selection)
✅ Finding aggregation configured to main region (eu-north-1)
✅ 2 control policies with 28 organizational assignments
✅ PROD and DEV control policies identified
✅ Security Hub completed successfully

============================================================
FINAL SUMMARY
============================================================
AWS Config: ✅ SUCCESS
GuardDuty: ✅ SUCCESS
IAM Access Analyzer: ✅ SUCCESS
Security Hub: ✅ SUCCESS
Detective: ✅ SUCCESS
Inspector: ✅ SUCCESS

✅ All services processed successfully!
```