"""
Shared utilities for Foundation Security Services Setup.
Contains common functions, constants, and data structures used across all modules.
"""

import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# ANSI Color codes (matching Foundation-AWS-Core-SSO-Configuration)
YELLOW = "\033[93m"
LIGHT_BLUE = "\033[94m" 
GREEN = "\033[92m"
RED = "\033[91m"
GRAY = "\033[90m"
END = "\033[0m"
BOLD = "\033[1m"

def printc(color, string, **kwargs):
    """Print colored output with proper line clearing"""
    print(f"{color}{string}\033[K{END}", **kwargs)

def get_client(service: str, account_id: str, region: str, role_name: str):
    """
    Create a cross-account AWS client using role assumption.
    This matches the pattern used in SOAR and other Foundation components.
    """
    try:
        sts_client = boto3.client('sts')
        
        # Assume role in the target account
        response = sts_client.assume_role(
            RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
            RoleSessionName=f"foundation_security_services_{account_id}"
        )
        
        credentials = response['Credentials']
        
        # Return configured client
        return boto3.client(
            service,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=region
        )
    except Exception as e:
        printc(RED, f"    ❌ Failed to assume role in account {account_id}: {str(e)}")
        return None

class DelegationChecker:
    """Shared delegation checking logic for AWS services"""
    
    @staticmethod
    def check_service_delegation(service_principal: str, admin_account: str, security_account: str, regions=None, cross_account_role: str = 'AWSControlTowerExecution', verbose=False):
        """Check delegation status for the service"""
        result = {
            'is_delegated_to_security': False,
            'delegated_admin_account': None,
            'delegation_check_failed': False,
            'delegation_details': [],
            'errors': []
        }
        
        try:
            orgs_client = get_client('organizations', admin_account, 'us-east-1', cross_account_role)
            if not orgs_client:
                result['delegation_check_failed'] = True
                result['errors'].append('Failed to get organizations client')
                return result
            
            all_delegated_admins = []
            paginator = orgs_client.get_paginator('list_delegated_administrators')
            for page in paginator.paginate(ServicePrincipal=service_principal):
                all_delegated_admins.extend(page.get('DelegatedAdministrators', []))
            
            # Store delegation details for inspection
            result['delegation_details'] = all_delegated_admins
            
            # Check if delegated to our security account
            for admin in all_delegated_admins:
                if admin.get('Id') == security_account:
                    result['is_delegated_to_security'] = True
                    result['delegated_admin_account'] = security_account
                    return result
            
            # Check if delegated to other accounts
            if all_delegated_admins:
                result['delegated_admin_account'] = all_delegated_admins[0].get('Id')
            
            return result
            
        except ClientError as e:
            if verbose:
                printc(RED, f"    ❌ Delegation check failed: {str(e)}")
            result['delegation_check_failed'] = True
            result['errors'].append(str(e))
            return result
    
    @staticmethod
    def handle_delegation_error(error, service_name=None):
        """Handle delegation errors consistently"""
        service_desc = f" for {service_name}" if service_name else ""
        return {
            'status': 'check_failed',
            'error': str(error),
            'error_message': f"Delegation check failed{service_desc}: {str(error)}",
            'needs_changes': True,
            'issues': [f"Could not verify delegation status{service_desc}"],
            'actions': [f"Verify Organizations API permissions and try again{service_desc}"]
        }

def get_unexpected_aws_regions(expected_regions):
    """Get list of AWS regions not in the expected list"""
    try:
        # For testing purposes, this should be mocked
        ec2_client = boto3.client('ec2', region_name=expected_regions[0] if expected_regions else 'us-east-1')
        
        regions_response = ec2_client.describe_regions()
        all_regions = [region['RegionName'] for region in regions_response['Regions']]
        
        # Return regions that are NOT in our expected list
        return [region for region in all_regions if region not in expected_regions]
        
    except Exception as e:
        printc(RED, f"  ❌ Error getting AWS regions: {str(e)}")
        return []


# ============================================================================
# Standardized Status Data Structures
# ============================================================================

@dataclass
class ServiceRegionStatus:
    """
    Standardized status structure for all AWS security services in a region.
    
    This replaces the inconsistent service-specific dictionaries like:
    - 'guardduty_enabled' -> 'service_enabled'
    - 'config_enabled' -> 'service_enabled'  
    - 'guardduty_details' -> 'service_details'
    - etc.
    
    Key principles:
    - No service names in field keys (composability)
    - Consistent field names across all services
    - Type safety with dataclass validation
    """
    region: str
    service_enabled: bool = False
    delegation_status: Optional[str] = None  # 'delegated', 'not_delegated', 'check_failed', etc.
    member_count: int = 0
    needs_changes: bool = False
    issues: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    service_details: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'region': self.region,
            'service_enabled': self.service_enabled,
            'delegation_status': self.delegation_status,
            'member_count': self.member_count,
            'needs_changes': self.needs_changes,
            'issues': self.issues.copy(),
            'actions': self.actions.copy(),
            'errors': self.errors.copy(),
            'service_details': self.service_details.copy()
        }
    


@dataclass
class AnomalousRegionStatus:
    """
    Standardized structure for anomalous/spurious resource detection.
    
    This replaces inconsistent naming like:
    - 'detector_count' -> 'resource_count'
    - 'recorder_count' -> 'resource_count'
    - 'detector_details' -> 'resource_details'
    - etc.
    """
    region: str
    resource_count: int
    resource_details: List[Dict[str, Any]] = field(default_factory=list)
    account_details: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'region': self.region,
            'resource_count': self.resource_count,
            'resource_details': self.resource_details.copy(),
            'account_details': self.account_details.copy()
        }


# Service-specific extensions for unique requirements
@dataclass
class GuardDutyRegionStatus(ServiceRegionStatus):
    """GuardDuty-specific fields that don't fit the common pattern."""
    organization_auto_enable: bool = False


@dataclass  
class SecurityHubRegionStatus(ServiceRegionStatus):
    """Security Hub-specific fields for complex policy management."""
    hub_arn: Optional[str] = None
    consolidated_controls_enabled: bool = False
    auto_enable_controls: Optional[bool] = None
    finding_aggregation_status: Optional[str] = None
    standards_subscriptions: List[Dict[str, Any]] = field(default_factory=list)
    findings_transfer_configured: bool = False
    main_region_aggregation: Optional[bool] = None


@dataclass
class ConfigRegionStatus(ServiceRegionStatus):
    """AWS Config-specific fields (no delegation support)."""
    records_global_iam: bool = False


@dataclass
class AccessAnalyzerRegionStatus(ServiceRegionStatus):
    """Access Analyzer-specific fields for different analyzer types."""
    external_analyzer_count: int = 0
    unused_analyzer_count: int = 0


@dataclass
class DetectiveRegionStatus(ServiceRegionStatus):
    """Detective-specific fields for investigation graphs."""
    graph_arn: Optional[str] = None


@dataclass
class InspectorRegionStatus(ServiceRegionStatus):
    """Inspector-specific fields for vulnerability scanning."""
    scan_types_enabled: int = 0


# Factory functions for creating standardized status objects
def create_service_status(service_name: str, region: str) -> ServiceRegionStatus:
    """
    Factory function to create appropriate status object for service.
    
    Args:
        service_name: Name of the service ('guardduty', 'security_hub', etc.)
        region: AWS region name
        
    Returns:
        Appropriate status object for the service
    """
    service_classes = {
        'guardduty': GuardDutyRegionStatus,
        'security_hub': SecurityHubRegionStatus,
        'aws_config': ConfigRegionStatus,
        'access_analyzer': AccessAnalyzerRegionStatus,
        'detective': DetectiveRegionStatus,
        'inspector': InspectorRegionStatus
    }
    
    status_class = service_classes.get(service_name, ServiceRegionStatus)
    return status_class(region=region)


def create_anomalous_status(region: str, resource_count: int = 0) -> AnomalousRegionStatus:
    """
    Factory function to create standardized anomalous region status.
    
    Args:
        region: AWS region name
        resource_count: Number of resources found in unexpected region
        
    Returns:
        Standardized anomalous region status object
    """
    return AnomalousRegionStatus(
        region=region,
        resource_count=resource_count
    )


class AnomalousRegionChecker:
    """Shared anomalous region detection logic for AWS services following DelegationChecker pattern."""
    
    @staticmethod
    def check_service_anomalous_regions(
        service_name: str,
        expected_regions: List[str],
        admin_account: str,
        security_account: str = None,
        cross_account_role: str = 'AWSControlTowerExecution',
        verbose: bool = False
    ) -> List[AnomalousRegionStatus]:
        """
        Check for service resources active in regions outside the expected list.
        
        Args:
            service_name: AWS service to check ('guardduty', 'detective', 'inspector', etc.)
            expected_regions: List of regions that should have the service
            admin_account: Organization management account ID
            security_account: Security account ID (for cross-account services)
            cross_account_role: IAM role name for cross-account access
            verbose: Enable verbose logging
            
        Returns:
            List of AnomalousRegionStatus objects with standardized structure
        """
        from botocore.exceptions import ClientError
        import boto3
        
        anomalous_regions = []
        
        # Get service configuration first to validate service name (this can raise ValueError)
        service_config = AnomalousRegionChecker._get_service_config(service_name)
        
        try:
            # Get all AWS regions to check for anomalous resources
            ec2_client = get_client('ec2', admin_account, expected_regions[0] if expected_regions else 'us-east-1', cross_account_role)
            regions_response = ec2_client.describe_regions()
            all_regions = [region['RegionName'] for region in regions_response['Regions']]
            
            # Check regions that are NOT in our expected list
            unexpected_regions = [region for region in all_regions if region not in expected_regions]
            
            if verbose:
                printc(GRAY, f"    Checking {len(unexpected_regions)} regions outside configuration...")
            
            for region in unexpected_regions:
                try:
                    # Get appropriate client (cross-account vs direct)
                    if service_config['supports_cross_account'] and security_account:
                        service_client = get_client(service_config['aws_service'], security_account, region, cross_account_role)
                        if not service_client:
                            service_client = get_client(service_config['aws_service'], admin_account, region, cross_account_role)
                    else:
                        service_client = get_client(service_config['aws_service'], admin_account, region, cross_account_role)
                    
                    if not service_client:
                        continue
                    
                    # Check for active resources using service-specific logic
                    resources, account_details = AnomalousRegionChecker._check_service_resources(
                        service_client, service_config, admin_account, region, verbose
                    )
                    
                    if resources:
                        # Create standardized anomalous status
                        anomalous_status = create_anomalous_status(region, len(resources))
                        anomalous_status.resource_details = resources
                        anomalous_status.account_details = account_details
                        anomalous_regions.append(anomalous_status)
                        
                        if verbose:
                            printc(YELLOW, f"    ⚠️  Anomalous {service_name} in {region}: {len(resources)} resources")
                            
                except ClientError as e:
                    # Don't show common "service not available" errors
                    if 'Could not connect to the endpoint URL' not in str(e) and 'UnsupportedOperation' not in str(e):
                        if verbose:
                            printc(GRAY, f"    (Skipping {region}: {str(e)})")
                    continue
                except Exception as e:
                    # Don't show common connectivity errors
                    if 'Could not connect to the endpoint URL' not in str(e):
                        if verbose:
                            printc(GRAY, f"    (Error checking {region}: {str(e)})")
                    continue
            
            return anomalous_regions
            
        except Exception as e:
            if verbose:
                printc(GRAY, f"    ⚠️  Anomaly check failed: {str(e)}")
            return []
    
    @staticmethod
    def _get_service_config(service_name: str) -> Dict[str, Any]:
        """Get service-specific configuration for anomalous detection."""
        configs = {
            'guardduty': {
                'aws_service': 'guardduty',
                'list_method': 'list_detectors',
                'resource_field': 'DetectorIds',
                'supports_cross_account': True,
                'detail_method': 'get_detector',
                'detail_param': 'DetectorId',
                'member_method': 'list_members'
            },
            'security_hub': {
                'aws_service': 'securityhub',
                'list_method': 'describe_hub',
                'resource_field': None,  # Single hub per region
                'supports_cross_account': True,
                'exception_when_none': True,
                'member_method': 'list_members'
            },
            'detective': {
                'aws_service': 'detective',
                'list_method': 'list_graphs',
                'resource_field': 'GraphList',
                'supports_cross_account': True,
                'member_method': 'list_members'
            },
            'inspector': {
                'aws_service': 'inspector2',
                'list_method': 'batch_get_account_status',
                'resource_field': 'accounts',
                'supports_cross_account': False,
                'embedded_accounts': True
            },
            'aws_config': {
                'aws_service': 'config',
                'list_method': 'describe_configuration_recorders',
                'resource_field': 'ConfigurationRecorders',
                'supports_cross_account': False
            },
            'access_analyzer': {
                'aws_service': 'accessanalyzer',
                'list_method': 'list_analyzers',
                'resource_field': None,  # Uses paginator
                'supports_cross_account': True,
                'uses_paginator': True
            }
        }
        
        if service_name not in configs:
            raise ValueError(f"Unknown service: {service_name}")
        
        return configs[service_name]
    
    @staticmethod
    def _check_service_resources(service_client, config: Dict[str, Any], admin_account: str, region: str, verbose: bool):
        """Check for active resources using service-specific logic."""
        from botocore.exceptions import ClientError
        
        resources = []
        account_details = []
        
        try:
            # Handle different API patterns
            if config.get('exception_when_none'):
                # Security Hub pattern - throws exception when no hub
                try:
                    response = getattr(service_client, config['list_method'])()
                    if response:
                        resources.append({
                            'hub_arn': response.get('HubArn'),
                            'subscribed_at': str(response.get('SubscribedAt', '')),
                            'auto_enable_controls': response.get('AutoEnableControls', False)
                        })
                        account_details.append({
                            'account_id': admin_account,
                            'account_status': 'ADMIN_ACCOUNT',
                            'hub_status': 'ENABLED'
                        })
                        
                        # Get Security Hub member details
                        if config.get('member_method'):
                            try:
                                members_response = getattr(service_client, config['member_method'])()
                                for member in members_response.get('Members', []):
                                    account_details.append({
                                        'account_id': member.get('AccountId'),
                                        'account_status': 'MEMBER_ACCOUNT',
                                        'member_status': member.get('MemberStatus', 'Unknown'),
                                        'hub_status': 'ENABLED'
                                    })
                            except Exception:
                                pass  # Member details are optional
                                
                except ClientError:
                    # No hub found (expected for most regions)
                    pass
                    
            elif config.get('uses_paginator'):
                # Access Analyzer pattern - uses paginator
                paginator = service_client.get_paginator(config['list_method'])
                for page in paginator.paginate():
                    analyzers = page.get('analyzers', [])
                    for analyzer in analyzers:
                        resources.append({
                            'analyzer_name': analyzer.get('name'),
                            'analyzer_type': analyzer.get('type'),
                            'status': analyzer.get('status')
                        })
                    
                if resources:
                    account_details.append({
                        'account_id': admin_account,
                        'account_status': 'ADMIN_ACCOUNT',
                        'analyzer_status': 'ENABLED'
                    })
                    
            elif config.get('embedded_accounts'):
                # Inspector pattern - account details embedded in response
                response = getattr(service_client, config['list_method'])()
                accounts = response.get(config['resource_field'], [])
                
                for account in accounts:
                    resource_state = account.get('resourceState', {})
                    enabled_resources = []
                    for resource_type, state_info in resource_state.items():
                        if state_info.get('status') == 'ENABLED':
                            enabled_resources.append(resource_type)
                    
                    if enabled_resources:
                        resources.extend(enabled_resources)
                        account_details.append({
                            'account_id': account.get('accountId'),
                            'scanning_status': 'ENABLED',
                            'enabled_scan_types': enabled_resources
                        })
                        
            else:
                # Standard pattern (GuardDuty, Detective, Config)
                response = getattr(service_client, config['list_method'])()
                
                if config['resource_field']:
                    resource_list = response.get(config['resource_field'], [])
                else:
                    resource_list = [response] if response else []
                
                for resource in resource_list:
                    if config.get('detail_method'):
                        # Get detailed info (GuardDuty pattern)
                        detail_response = getattr(service_client, config['detail_method'])(
                            **{config['detail_param']: resource}
                        )
                        resources.append({
                            'resource_id': resource,
                            'status': detail_response.get('Status', 'Unknown'),
                            'details': detail_response
                        })
                    else:
                        # Use resource directly (Detective, Config pattern)
                        resources.append(resource)
                
                # Add admin account details for non-embedded account patterns
                if resources and not config.get('embedded_accounts'):
                    admin_detail = {
                        'account_id': admin_account,
                        'account_status': 'ADMIN_ACCOUNT',
                        'service_status': 'ENABLED'
                    }
                    
                    # Add service-specific status information
                    if config['aws_service'] == 'guardduty':
                        admin_detail['detector_status'] = 'ENABLED'
                    elif config['aws_service'] == 'securityhub':
                        admin_detail['hub_status'] = 'ENABLED'
                    elif config['aws_service'] == 'detective':
                        admin_detail['graph_status'] = 'ENABLED'
                    
                    account_details.append(admin_detail)
                    
                    # Get member details for services that support it
                    if config.get('member_method'):
                        try:
                            if config['aws_service'] == 'detective':
                                # Detective uses GraphArn parameter
                                for resource in resources:
                                    if isinstance(resource, dict) and 'Arn' in resource:
                                        members_paginator = service_client.get_paginator(config['member_method'])
                                        for page in members_paginator.paginate(GraphArn=resource['Arn']):
                                            for member in page.get('MemberDetails', []):
                                                account_details.append({
                                                    'account_id': member.get('AccountId'),
                                                    'account_status': 'MEMBER_ACCOUNT',
                                                    'member_status': member.get('Status', 'Unknown')
                                                })
                            elif config['aws_service'] == 'guardduty':
                                # GuardDuty uses simpler list_members call
                                members_response = getattr(service_client, config['member_method'])()
                                for member in members_response.get('Members', []):
                                    account_details.append({
                                        'account_id': member.get('AccountId'),
                                        'account_status': 'MEMBER_ACCOUNT',
                                        'member_status': member.get('RelationshipStatus', 'Unknown'),
                                        'detector_status': 'ENABLED'  # If they're members, detector is enabled
                                    })
                        except Exception:
                            pass  # Member details are optional
                            
        except Exception as e:
            if verbose:
                printc(GRAY, f"    (Error checking resources in {region}: {str(e)})")
        
        return resources, account_details


