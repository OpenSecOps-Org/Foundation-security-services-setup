# Foundation Security Services Setup

Automates the configuration of AWS security services across your organization, eliminating the manual console-clicking required for proper security service delegation and setup.

## Overview

This Foundation component automates the "Activations & delegations" section from the OpenSecOps Foundation Installation Manual, configuring the following AWS security services:

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
* Accounts defined in `Installer/apps/accounts.toml`

## Configuration

Services can be enabled/disabled via parameters in `Installer/apps/foundation/parameters.toml`:

```toml
[Foundation-security-services-setup.setup-security-services]
AWSConfigEnabled = 'Yes'
GuardDutyEnabled = 'Yes'
SecurityHubEnabled = 'Yes'
IAMAccessAnalyzerEnabled = 'Yes'
DetectiveEnabled = 'No'
InspectorEnabled = 'No'
```

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

## Features

* **Idempotent operation** - Safe to run multiple times
* **Dry-run support** - Preview changes without making modifications
* **Selective service enablement** - Enable only the services you need
* **Automated cross-account setup** - Handles delegation and role assumptions
* **Organization-wide coverage** - Configures services across all accounts

## What Gets Configured

* **AWS Config**: Enabled with proper IAM global event recording settings
* **GuardDuty**: Delegated with auto-enable for new members and existing accounts
* **Security Hub**: Central configuration with PROD/DEV control policies
* **Access Analyzer**: Organization-wide analyzers for external and unused access detection
* **Detective**: Investigation capabilities across the organization (if enabled)
* **Inspector**: Vulnerability assessments with auto-activation (if enabled)