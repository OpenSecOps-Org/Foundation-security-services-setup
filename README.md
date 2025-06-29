# Foundation Security Services Setup

**Automated AWS security service configuration for infrastructure engineers**

> **⚠️ PRE-RELEASE VERSION**: This version provides comprehensive read-only analysis and discovery of AWS security services. It does not yet mutate AWS resources. Full automation capabilities coming in v1.0.0.

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
- **Existing installation**: Copy the `Foundation-security-services-setup` section from `Installer/apps.example/foundation/parameters.toml` and add to your existing parameters file

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
  --org-id o-example12345 \
  --root-ou r-example12345
```

**With service customization:**
```console
./setup-security-services \
  --admin-account 111111111111 \
  --security-account 222222222222 \
  --regions us-east-1,us-west-2,eu-west-1 \
  --cross-account-role OrganizationAccountAccessRole \  # For Organizations without Control Tower
  --org-id o-example12345 \
  --root-ou r-example12345 \
  --security-hub No \
  --detective Yes \
  --inspector Yes
```

**Parameters:**
- **Required**: `--admin-account`, `--security-account`, `--regions`, `--org-id`, `--root-ou`
- **Cross-Account Access**: `--cross-account-role` (default: `AWSControlTowerExecution`)
  - `AWSControlTowerExecution` - For environments with AWS Control Tower (default)
  - `OrganizationAccountAccessRole` - For AWS Organizations without Control Tower
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

## Example Output

## Normal verbosity

```console
./deploy

============================================================
  Foundation Security Services Setup
------------------------------------------------------------

============================================================
AWS CONFIG SETUP
============================================================
Checking AWS Config setup in 2 regions...
✅ AWS Config is already properly configured in all regions
   No changes needed - existing setup meets stringent security standards
✅ AWS Config completed successfully

============================================================
GUARDDUTY SETUP
============================================================
Checking GuardDuty setup in 2 regions...
✅ GuardDuty is already properly configured in all regions
   No changes needed - existing setup meets stringent security standards
✅ GuardDuty completed successfully

============================================================
IAM ACCESS ANALYZER SETUP
============================================================
Checking IAM Access Analyzer setup...
  ⚠️  Access Analyzer needs changes in eu-north-1
    • Main region missing unused access analyzer
⚠️  IAM Access Analyzer needs configuration:

📋 MISSING ANALYZERS:

  🌍 Region: eu-north-1
    • Missing: Unused Access Analyzer (main region only)
      Recommend: Create ORGANIZATION analyzer for unused access detection

🔧 Making Access Analyzer changes...
  TODO: Create required analyzers in eu-north-1
✅ IAM Access Analyzer completed successfully

============================================================
SECURITY HUB SETUP
============================================================

⚠️  ANOMALOUS SECURITY HUB HUBS DETECTED:
Security Hub hubs are active in regions outside your configuration:
  • eu-central-1: Hub is active (not in your regions list)

ANOMALY RECOMMENDATIONS:
  • Review: Determine if these hubs are intentional or configuration drift
  • Recommended: Disable Security Hub in these regions to control costs
  • Note: Adding regions to OpenSecOps requires full system redeployment
  Cost Impact: Security Hub generates charges per region and per finding
⚠️  Security Hub configuration needs optimization:
  • Review anomalous hubs in 1 unexpected region(s)
    (Hubs outside configured regions may generate unexpected costs)
✅ Security Hub completed successfully

============================================================
DETECTIVE SETUP
============================================================
Detective is disabled - checking for active resources to deactivate
✅ Detective completed successfully

============================================================
INSPECTOR SETUP
============================================================
Inspector is disabled - checking for active resources to deactivate
✅ Inspector completed successfully

============================================================
FINAL SUMMARY
============================================================
AWS Config: ✅ SUCCESS
GuardDuty: ✅ SUCCESS
IAM Access Analyzer: ✅ SUCCESS
Security Hub: ✅ SUCCESS
Detective: ✅ SUCCESS
Inspector: ✅ SUCCESS

✅ All services processed successfully
```

## Verbose

```console
./deploy --verbose

============================================================
  Foundation Security Services Setup
------------------------------------------------------------
VERBOSE MODE: Additional debugging output enabled

Service flags:
  --aws-config: Yes
  --guardduty: Yes
  --access-analyzer: Yes
  --security-hub: Yes
  --detective: No
  --inspector: No

AWS parameters:
  --admin-account: 111111111111
  --security-account: 222222222222
  --regions: eu-north-1,us-east-1
  --cross-account-role: AWSControlTowerExecution
  --org-id: 0-xxxxxxxxxx
  --root-ou: r-yyyy

Other arguments:
  --dry-run: False
  --verbose: True

============================================================
AWS CONFIG SETUP
============================================================
Enabled: Yes
Regions: ['eu-north-1', 'us-east-1']
Organization ID: 0-xxxxxxxxxx
Dry Run: False
Verbose: True
Checking AWS Config setup in 2 regions...
Main region: eu-north-1 (should record IAM global events)
Other regions: ['us-east-1'] (should exclude IAM global events)

Checking Config in region eu-north-1...
  ✅ Config properly configured in eu-north-1

Checking Config in region us-east-1...
  ✅ Config properly configured in us-east-1

Checking for AWS Config recorders in unexpected regions...
    Checking 15 regions outside configuration...
✅ AWS Config is already properly configured in all regions
   No changes needed - existing setup meets stringent security standards

Current AWS Config Configuration:

Region: eu-north-1
  ✅ Configuration Recorders: 1 found
     Recorder 'default':
        IAM Role: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
        Recording: All supported resources
        IAM Global Resources: ✅ Included
        Recording Frequency: CONTINUOUS
  ✅ Delivery Channels: 1 found
     Channel 'default':
        S3 Bucket: config-bucket-111111111111
  ✅ Config Rules: 242 active rules
     AWS Managed Rules: 225
     Custom Rules: 17

Region: us-east-1
  ✅ Configuration Recorders: 1 found
     Recorder 'default':
        IAM Role: arn:aws:iam::111111111111:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig
        Recording: All resources except 4 excluded types
        Excluded: AWS::IAM::Policy, AWS::IAM::User, AWS::IAM::Role...
        IAM Global Resources: ✅ Excluded
        Recording Frequency: CONTINUOUS
  ✅ Delivery Channels: 1 found
     Channel 'default':
        S3 Bucket: config-bucket-111111111111
  ✅ Config Rules: 251 active rules
     AWS Managed Rules: 234
     Custom Rules: 17
✅ AWS Config completed successfully

============================================================
GUARDDUTY SETUP
============================================================
Enabled: Yes
Regions: ['eu-north-1', 'us-east-1']
Admin Account: 111111111111
Security Account: 222222222222
Organization ID: 0-xxxxxxxxxx
Dry Run: False
Verbose: True
Checking GuardDuty setup in 2 regions...
Admin account (111111111111): Should enable GuardDuty and delegate to Security account
Security account (222222222222): Should be delegated admin for organization

🔍 Checking GuardDuty in region eu-north-1...
    🔄 Switching to delegated admin account for complete data...
  ✅ GuardDuty properly configured in eu-north-1

🔍 Checking GuardDuty in region us-east-1...
    🔄 Switching to delegated admin account for complete data...
  ✅ GuardDuty properly configured in us-east-1

🔍 Checking for GuardDuty detectors in unexpected regions...
    Checking 15 regions outside configuration...
✅ GuardDuty is already properly configured in all regions
   No changes needed - existing setup meets stringent security standards

📋 Current GuardDuty Configuration:

🌍 Region: eu-north-1
  ✅ GuardDuty Detector: 56c909d6a827d835be29e1d8xxxxxxxx
     ✅ Status: ENABLED
     ✅ Finding Frequency: FIFTEEN_MINUTES (optimal)
  ✅ Delegated to Security account: 222222222222
  ✅ Organization Auto-Enable: True
  ✅ Auto-Enable Org Members: ALL
     S3 Data Events: False
     Kubernetes Audit Logs: False
     Malware Protection: False
  ✅ Member Accounts: 142 found
     ✅ All 142 member accounts are enabled

🌍 Region: us-east-1
  ✅ GuardDuty Detector: 0ec909d8a800bb5dff4c83ecyyyyyyyy
     ✅ Status: ENABLED
     ✅ Finding Frequency: FIFTEEN_MINUTES (optimal)
  ✅ Delegated to Security account: 222222222222
  ✅ Organization Auto-Enable: True
  ✅ Auto-Enable Org Members: ALL
     S3 Data Events: False
     Kubernetes Audit Logs: False
     Malware Protection: False
  ✅ Member Accounts: 142 found
     ✅ All 142 member accounts are enabled
✅ GuardDuty completed successfully

============================================================
IAM ACCESS ANALYZER SETUP
============================================================
Enabled: Yes
Regions: ['eu-north-1', 'us-east-1']
Admin Account: 111111111111
Security Account: 222222222222
Organization ID: 0-xxxxxxxxxx
Dry Run: False
Verbose: True
Checking IAM Access Analyzer setup...
Expected regions: eu-north-1, us-east-1
Admin account (111111111111): Should delegate to Security account
Security account (222222222222): Should be delegated admin for organization
Main region (eu-north-1): Should have both external and unused access analyzers
Other regions: Should have external access analyzers only

🔍 Checking Access Analyzer delegation (organization-wide)...
    ✅ Delegated to Security account: 222222222222
✅ Access Analyzer properly delegated to Security account
🔍 Scanning 17 AWS regions for analyzers in unexpected regions...
  ✅ No analyzers found in unexpected regions

🔍 Checking analyzers in region eu-north-1...
    🔄 Checking from delegated admin perspective...
  ⚠️  Access Analyzer needs changes in eu-north-1

🔍 Checking analyzers in region us-east-1...
    🔄 Checking from delegated admin perspective...
  ✅ Access Analyzer properly configured in us-east-1
⚠️  IAM Access Analyzer needs configuration:

📋 MISSING ANALYZERS:

  🌍 Region: eu-north-1
    • Missing: Unused Access Analyzer (main region only)
      Recommend: Create ORGANIZATION analyzer for unused access detection

🔧 Making Access Analyzer changes...
  TODO: Create required analyzers in eu-north-1
✅ IAM Access Analyzer completed successfully

============================================================
SECURITY HUB SETUP
============================================================
Enabled: Yes
Regions: ['eu-north-1', 'us-east-1']
Admin Account: 111111111111
Security Account: 222222222222
Organization ID: 0-xxxxxxxxxx
Dry Run: False
Verbose: True
🔍 Analyzing current Security Hub configuration...
🔍 Checking Security Hub delegation status...
🌍 Checking Security Hub in region: eu-north-1
    🌍 Analyzing Security Hub in region: eu-north-1
      Consolidated Controls: ✅ ENABLED
      Auto Enable Controls: ✅ DISABLED (correct)
      Standards enabled: 4
        - AWS Foundational Security Standard: READY
        - CIS AWS Foundations Benchmark: READY
        - NIST SP 800-53: READY
        - PCI DSS: READY
      Member accounts: 142
      🔄 Finding Aggregation: Unknown (0 regions)
🌍 Checking Security Hub in region: us-east-1
    🌍 Analyzing Security Hub in region: us-east-1
      Consolidated Controls: ✅ ENABLED
      Auto Enable Controls: ✅ DISABLED (correct)
      Standards enabled: 4
        - AWS Foundational Security Standard: READY
        - CIS AWS Foundations Benchmark: READY
        - NIST SP 800-53: READY
        - PCI DSS: READY
      Member accounts: 142
      🔄 Finding Aggregation: Unknown (0 regions)
📋 Analyzing control policies...
📋 Analyzing control policies and organizational assignments...
    🔗 Policy associations found: 28
    📋 Found policy: DEV (07922ea1-3aeb-48fa-b910-c28fxxxxxxxx)
    📋 Found policy: PROD (c501c960-3009-4b1a-a698-db69yyyyyyyy)
    🧪 DEV policy identified: DEV
    🏭 PROD policy identified: PROD
    🔗 Analyzing 28 policy associations...

🔍 Checking for Security Hub hubs in unexpected regions...
    Checking 15 regions outside configuration...
    ⚠️  Anomalous Security Hub in eu-central-1: Hub is active
       Hub ARN: arn:aws:securityhub:eu-central-1:111111111111:hub/default
       Auto-enable controls: False

⚠️  ANOMALOUS SECURITY HUB HUBS DETECTED:
Security Hub hubs are active in regions outside your configuration:
  • eu-central-1: Hub is active (not in your regions list)

ANOMALY RECOMMENDATIONS:
  • Review: Determine if these hubs are intentional or configuration drift
  • Recommended: Disable Security Hub in these regions to control costs
  • Note: Adding regions to OpenSecOps requires full system redeployment
  Cost Impact: Security Hub generates charges per region and per finding
⚠️  Security Hub configuration needs optimization:
  • Review anomalous hubs in 1 unexpected region(s)
    (Hubs outside configured regions may generate unexpected costs)
✅ Security Hub completed successfully

============================================================
DETECTIVE SETUP
============================================================
Enabled: No
Regions: ['eu-north-1', 'us-east-1']
Admin Account: 111111111111
Security Account: 222222222222
Organization ID: 0-xxxxxxxxxx
Dry Run: False
Verbose: True
Detective is disabled - checking for active resources to deactivate
   🔍 Checking all AWS regions for spurious Detective activation...
    Checking 17 regions outside configuration...
   ✅ Detective is not delegated or active - no cleanup needed
✅ Detective completed successfully

============================================================
INSPECTOR SETUP
============================================================
Enabled: No
Regions: ['eu-north-1', 'us-east-1']
Admin Account: 111111111111
Security Account: 222222222222
Organization ID: 0-xxxxxxxxxx
Dry Run: False
Verbose: True
Inspector is disabled - checking for active resources to deactivate
   🔍 Checking all 17 AWS regions for spurious Inspector activation...
   ✅ Inspector is not delegated or active - no cleanup needed
✅ Inspector completed successfully

============================================================
FINAL SUMMARY
============================================================
AWS Config: ✅ SUCCESS
GuardDuty: ✅ SUCCESS
IAM Access Analyzer: ✅ SUCCESS
Security Hub: ✅ SUCCESS
Detective: ✅ SUCCESS
Inspector: ✅ SUCCESS

✅ All services processed successfully
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
