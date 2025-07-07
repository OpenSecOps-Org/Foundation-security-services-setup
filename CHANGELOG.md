# Change Log

## v0.1.19
    * Fixed Security Hub field name mismatch bug causing false "not enabled in all regions" warnings when hubs were properly configured
    * Removed misleading "completed successfully" messages that suggested services were configured when they only indicated module execution without crashes

## v0.1.18
    * Completed Dataclass Direct Usage refactoring - eliminated dictionary conversion layers throughout codebase
    * Achieved full type safety with dataclass objects used directly in all service modules and anomalous region detection
    * Removed obsolete from_dict() method and related test scaffolding for clean production code
    * Validated real-world deployment success across multi-region AWS environment with 6 security services
    * Maintained 100% test success rate (219 tests passing in 2.56 seconds)

## v0.1.17
    * Improved IAM Access Analyzer output messaging - eliminated confusing "No analyzers found" messages when delegation provides complete data
    * Fixed ValidationException for Unused Access analyzers by using correct ListFindingsV2 API instead of ListFindings API
    * Added 3 comprehensive TDD tests to specify improved messaging and API usage behavior (192 tests passing)
    * Enhanced verbose output clarity and eliminated contradictory status messages

## v0.1.16
    * Fixed IAM Access Analyzer KeyError crash in eu-west-1 and other regions during verbose configuration display
    * Corrected 'analyzer_enabled' key mismatch - now properly uses 'has_analyzers' key returned by check function
    * Maintains 100% test success rate (189 tests passing) and resolves regional processing failures

## v0.1.15
    * Completed emoji cleanup across all Python modules and documentation examples, maintaining only essential status indicators (✅, ❌, ⚠️)
    * Enhanced GuardDuty monitoring with comprehensive data sources status reporting (S3 Data Events, Kubernetes Audit Logs, Malware Protection, RDS Protection, Lambda Network Activity, EKS Runtime Monitoring, EBS Malware Protection)
    * Improved professional output formatting for enterprise environments
    * Maintained 100% test success rate (189 tests passing)

## v0.1.14
    * Updated README documentation for improved clarity and accuracy

## v0.1.13
    * Removed unnecessary emojis from output strings, keeping only essential status indicators (checkmarks, warning triangles, red crosses)
    * Removed preaching about security posture choices - now reports facts without recommendations on S3 data events and malware protection
    * Fixed IAM Global Resources display to correctly show excluded status as valid configuration for non-main regions
    * Updated corresponding tests to maintain 100% test success rate (185 tests passing)
    * Improved output professionalism while preserving all technical recommendations and security information

## v0.1.12
    * Added comprehensive spurious region detection for all 6 security services (GuardDuty, Security Hub, AWS Config, Detective, Inspector, Access Analyzer)
    * Enhanced all services to check for unexpected activations outside configured regions when disabled, preventing cost surprises
    * Improved error handling to gracefully suppress service unavailability errors in unsupported regions
    * Added 6 new tests covering anomalous region detection scenarios (125 total tests, all passing)
    * Ensured consistent behavior across all modules for configuration drift detection and cost control

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
