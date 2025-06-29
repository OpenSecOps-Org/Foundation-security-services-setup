# Change Log

## v0.1.11
    * --cross-account-role parameter now defaults to AWSControlTowerExecution and can be omitted for standalone usage convenience
    * Cross-account role restricted to two valid choices: AWSControlTowerExecution (default) and OrganizationAccountAccessRole
    * Common utilities (colors, printc, get_client) centralized in shared modules/utils.py for improved maintainability

## v0.1.10
    * Added missing .python-version file.

## v0.1.9
    * README updated.

## v0.1.8
    * README updated.

## v0.1.7
    * Deployment script fixed.
    * Updated the README.

## v0.1.6
    * Updated the README.

## v0.1.5
    * README consolidated.

## v0.1.4
    * Further README updates.

## v0.1.3
    * Further README updates.

## v0.1.2
    * Updated the README.

## v0.1.1
    * Improved output formatting for better readability and professional appearance.
    * Removed redundant processing messages that duplicated service banner information.
    * Enhanced README with comprehensive example output showing all 6 security services.
    * Added configuration guidance for both new and existing OpenSecOps installations.

## v0.1.0
    * Initial pre-release with read-only AWS security services discovery and analysis.
    * Comprehensive discovery for AWS Config, GuardDuty, Detective, Inspector, Access Analyzer, and Security Hub.
    * Detailed recommendations and configuration validation across all regions.
    * 147 passing tests with complete AWS service mocking.
    * Note: This is a descriptive implementation only - no AWS resource creation/modification capabilities yet.
