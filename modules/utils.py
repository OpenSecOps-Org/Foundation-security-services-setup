"""
Shared utilities for Foundation Security Services Setup.
Contains common functions and constants used across all modules.
"""

import boto3
from botocore.exceptions import ClientError

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