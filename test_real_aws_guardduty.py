#!/usr/bin/env python3
"""
Real AWS GuardDuty Discovery Script

This script discovers your current AWS GuardDuty setup using the exact same
calling patterns that will be used in the actual modules/guardduty.py.

The goal is to gather real AWS data to inform the TDD implementation.
"""

import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, List, Any
from datetime import datetime

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
            RoleSessionName=f"guardduty_discovery_{account_id}"
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
        print(f"    ❌ Failed to assume role in account {account_id}: {str(e)}")
        return None

def discover_current_guardduty_state(params: Dict[str, Any], verbose=False) -> Dict[str, Any]:
    """
    Discover current AWS GuardDuty state using the same parameter structure
    that the real setup_guardduty function will receive.
    
    This function mirrors what setup_guardduty will do:
    1. Connect to AWS (using default session - assumes aws sso login completed)
    2. Check GuardDuty in all regions
    3. Check delegation to security account
    4. Report current state vs desired state
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'params_used': params,
        'regions_checked': [],
        'guardduty_state': {},
        'recommendations': [],
        'warnings': [],
        'errors': []
    }
    
    print("\n" + "="*60)
    print("AWS GUARDDUTY DISCOVERY")
    print("="*60)
    
    if verbose:
        print(f"Regions: {params['regions']}")
        print(f"Admin Account: {params['admin_account']}")
        print(f"Security Account: {params['security_account']}")
        print(f"Organization ID: {params['org_id']}")
    
    regions = params['regions']
    admin_account = params['admin_account']
    security_account = params['security_account']
    
    print(f"\nExpected setup:")
    print(f"- Admin account ({admin_account}): Should enable GuardDuty and delegate to Security account")
    print(f"- Security account ({security_account}): Should be delegated admin for organization")
    
    # Check each region's current GuardDuty state
    for region in regions:
        print(f"\n🔍 Checking GuardDuty in region {region}...")
        region_state = check_guardduty_in_region(region, admin_account, security_account, params.get('cross_account_role'), verbose)
        results['guardduty_state'][region] = region_state
        results['regions_checked'].append(region)
        
        # Analyze findings
        if region_state['guardduty_enabled']:
            print(f"  ✅ GuardDuty is ENABLED in {region}")
            
            # Check delegation status
            delegation_status = region_state.get('delegation_status', 'unknown')
            if delegation_status == 'delegated':
                print(f"  ✅ Delegation is properly configured")
            elif delegation_status == 'not_delegated':
                print(f"  ⚠️  No delegation found - should delegate to Security account")
                results['warnings'].append(f"Region {region} needs delegation to Security account")
            else:
                print(f"  ❓ Delegation status unclear: {delegation_status}")
                
            # Check member accounts
            member_count = region_state.get('member_count', 0)
            if member_count > 0:
                print(f"  📊 {member_count} member accounts found")
            else:
                print(f"  ⚠️  No member accounts - organization setup may be incomplete")
                
        else:
            print(f"  ❌ GuardDuty is DISABLED in {region}")
            results['recommendations'].append(f"Enable GuardDuty in region {region}")
    
    return results

def check_guardduty_in_region(region: str, admin_account: str, security_account: str, cross_account_role: str = None, verbose=False) -> Dict[str, Any]:
    """
    Check AWS GuardDuty status in a specific region.
    Uses default boto3 session (assumes aws sso login completed).
    
    This exactly mirrors what the real modules/guardduty.py will do.
    """
    region_data = {
        'region': region,
        'guardduty_enabled': False,
        'detector_id': None,
        'detector_status': None,
        'delegated_admin': None,
        'delegation_status': 'unknown',
        'members': [],
        'member_count': 0,
        'organization_config': {},
        'errors': []
    }
    
    try:
        # Use default session - this matches what the real module will do
        # Foundation components assume aws sso login has been completed
        guardduty_client = boto3.client('guardduty', region_name=region)
        
        # Check GuardDuty detectors
        try:
            detectors_response = guardduty_client.list_detectors()
            detector_ids = detectors_response.get('DetectorIds', [])
            
            if detector_ids:
                region_data['guardduty_enabled'] = True
                region_data['detector_id'] = detector_ids[0]  # Usually only one detector per region
                
                if verbose:
                    print(f"    Found {len(detector_ids)} GuardDuty detectors")
                
                # Get detector details
                try:
                    detector_response = guardduty_client.get_detector(DetectorId=detector_ids[0])
                    region_data['detector_status'] = detector_response.get('Status', 'Unknown')
                    
                    if verbose:
                        print(f"    Detector status: {region_data['detector_status']}")
                        
                except ClientError as e:
                    error_msg = f"Get detector details failed: {str(e)}"
                    region_data['errors'].append(error_msg)
                    if verbose:
                        print(f"    ❌ {error_msg}")
                
            else:
                if verbose:
                    print(f"    No GuardDuty detectors found")
                
        except ClientError as e:
            error_msg = f"List detectors failed: {str(e)}"
            region_data['errors'].append(error_msg)
            if verbose:
                print(f"    ❌ {error_msg}")
        
        # Check delegated administrator first to determine access pattern
        try:
            orgs_client = boto3.client('organizations', region_name=region)
            delegated_admins = orgs_client.list_delegated_administrators(ServicePrincipal='guardduty.amazonaws.com')
            
            is_delegated_to_security = False
            for admin in delegated_admins.get('DelegatedAdministrators', []):
                if admin.get('Id') == security_account:
                    region_data['delegated_admin'] = admin
                    region_data['delegation_status'] = 'delegated'
                    is_delegated_to_security = True
                    if verbose:
                        print(f"    ✅ Security account is delegated administrator")
                    break
            else:
                if region_data['guardduty_enabled']:
                    region_data['delegation_status'] = 'not_delegated'
                    if verbose:
                        print(f"    ⚠️  Security account not found as delegated administrator")
                        
        except ClientError as e:
            error_msg = f"Check delegated administrators failed: {str(e)}"
            region_data['errors'].append(error_msg)
            if verbose:
                print(f"    ❌ {error_msg}")
            is_delegated_to_security = False
        
        # Check organization configuration and member accounts 
        # If delegation is detected, switch to delegated admin account for complete data
        if (is_delegated_to_security and 
            cross_account_role and 
            security_account != admin_account):
            
            if verbose:
                print(f"    🔄 Switching to delegated admin account ({security_account}) for complete data...")
            
            # Create cross-account client to security account
            delegated_client = get_client('guardduty', security_account, region, cross_account_role)
            
            if delegated_client:
                # Get detector ID in the delegated admin account
                try:
                    delegated_detectors = delegated_client.list_detectors()
                    delegated_detector_ids = delegated_detectors.get('DetectorIds', [])
                    
                    if delegated_detector_ids:
                        delegated_detector_id = delegated_detector_ids[0]
                        if verbose:
                            print(f"    Found delegated admin detector: {delegated_detector_id}")
                        
                        # Get organization configuration from delegated admin
                        try:
                            org_config_response = delegated_client.describe_organization_configuration(
                                DetectorId=delegated_detector_id
                            )
                            
                            region_data['organization_config'] = org_config_response
                            auto_enable = org_config_response.get('AutoEnable', False)
                            auto_enable_orgs = org_config_response.get('AutoEnableOrganizationMembers', 'Unknown')
                            
                            if verbose:
                                print(f"    ✅ Organization auto-enable: {auto_enable}")
                                print(f"    ✅ Auto-enable org members: {auto_enable_orgs}")
                                
                        except ClientError as e:
                            error_msg = f"Delegated admin org configuration failed: {str(e)}"
                            region_data['errors'].append(error_msg)
                            if verbose:
                                print(f"    ❌ {error_msg}")
                        
                        # Get member accounts from delegated admin with pagination
                        try:
                            all_members = []
                            paginator = delegated_client.get_paginator('list_members')
                            
                            for page in paginator.paginate(DetectorId=delegated_detector_id):
                                members = page.get('Members', [])
                                all_members.extend(members)
                            
                            region_data['members'] = all_members
                            region_data['member_count'] = len(all_members)
                            
                            if verbose:
                                print(f"    ✅ Found {region_data['member_count']} member accounts via delegated admin")
                                if region_data['member_count'] > 0:
                                    for member in all_members[:3]:  # Show first 3
                                        status = member.get('RelationshipStatus', 'Unknown')
                                        account_id = member.get('AccountId', 'Unknown')
                                        email = member.get('Email', 'Unknown')
                                        print(f"      Member {account_id} ({email}): {status}")
                                    if len(all_members) > 3:
                                        print(f"      ... and {len(all_members) - 3} more")
                                        
                        except ClientError as e:
                            error_msg = f"Delegated admin list members failed: {str(e)}"
                            region_data['errors'].append(error_msg)
                            if verbose:
                                print(f"    ❌ {error_msg}")
                    else:
                        if verbose:
                            print(f"    ⚠️  No detectors found in delegated admin account")
                            
                except ClientError as e:
                    error_msg = f"Delegated admin detector check failed: {str(e)}"
                    region_data['errors'].append(error_msg)
                    if verbose:
                        print(f"    ❌ {error_msg}")
            else:
                if verbose:
                    print(f"    ❌ Failed to create cross-account client to security account")
        
        else:
            # Fallback: Try to get organization config from current account (limited data)
            try:
                org_config_response = guardduty_client.describe_organization_configuration(
                    DetectorId=region_data['detector_id']
                ) if region_data['detector_id'] else None
                
                if org_config_response:
                    region_data['organization_config'] = org_config_response
                    auto_enable = org_config_response.get('AutoEnable', False)
                    
                    if verbose:
                        print(f"    Organization auto-enable: {auto_enable}")
                        
            except ClientError as e:
                if "is not the GuardDuty administrator" in str(e):
                    region_data['delegation_status'] = 'not_admin'
                    if verbose:
                        print(f"    ℹ️  Not the GuardDuty administrator for organization")
                else:
                    error_msg = f"Organization configuration check failed: {str(e)}"
                    region_data['errors'].append(error_msg)
                    if verbose:
                        print(f"    ❌ {error_msg}")
            
            # Try to get member accounts from current account (limited data)
            try:
                if region_data['detector_id']:
                    all_members = []
                    paginator = guardduty_client.get_paginator('list_members')
                    
                    for page in paginator.paginate(DetectorId=region_data['detector_id']):
                        members = page.get('Members', [])
                        all_members.extend(members)
                    
                    region_data['members'] = all_members
                    region_data['member_count'] = len(all_members)
                    
                    if verbose and region_data['member_count'] > 0:
                        print(f"    Found {region_data['member_count']} member accounts")
                        for member in all_members[:3]:  # Show first 3
                            status = member.get('RelationshipStatus', 'Unknown')
                            account_id = member.get('AccountId', 'Unknown')
                            print(f"      Member {account_id}: {status}")
                        if len(all_members) > 3:
                            print(f"      ... and {len(all_members) - 3} more")
                            
            except ClientError as e:
                error_msg = f"List members failed: {str(e)}"
                region_data['errors'].append(error_msg)
                if verbose:
                    print(f"    ❌ {error_msg}")
                
    except Exception as e:
        error_msg = f"General error checking GuardDuty in region {region}: {str(e)}"
        region_data['errors'].append(error_msg)
        print(f"    ❌ {error_msg}")
    
    return region_data

def save_discovery_results(results: Dict[str, Any], filename: str = None):
    """Save discovery results to JSON file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"guardduty_discovery_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filename}")

def main():
    """Main function - simulates exactly how setup_guardduty will be called."""
    print("🔍 AWS GuardDuty Real Discovery (TDD Pattern)")
    print("This uses the exact calling pattern of the real setup_guardduty function")
    print("-" * 70)
    
    # Create params dict exactly as main script does
    params = {
        'admin_account': '123456789012',      # Example admin account
        'security_account': '234567890123',   # Example security account  
        'regions': ['eu-north-1', 'us-east-1'],  # Stockholm and West Virginia
        'cross_account_role': 'AWSControlTowerExecution',
        'org_id': 'o-example12345',
        'root_ou': 'r-example12345'
    }
    
    # Run discovery with same parameters that setup_guardduty will receive
    results = discover_current_guardduty_state(params, verbose=True)
    
    # Save results for analysis
    save_discovery_results(results)
    
    # Summary
    print("\n" + "="*60)
    print("DISCOVERY SUMMARY")
    print("="*60)
    
    enabled_regions = [r for r, data in results['guardduty_state'].items() if data['guardduty_enabled']]
    disabled_regions = [r for r, data in results['guardduty_state'].items() if not data['guardduty_enabled']]
    
    print(f"GuardDuty enabled in: {enabled_regions if enabled_regions else 'None'}")
    print(f"GuardDuty disabled in: {disabled_regions if disabled_regions else 'None'}")
    
    # Check delegation status summary
    delegation_summary = {}
    for region, data in results['guardduty_state'].items():
        status = data.get('delegation_status', 'unknown')
        delegation_summary[region] = status
    
    print(f"Delegation status by region: {delegation_summary}")
    
    if results['warnings']:
        print(f"\n⚠️  {len(results['warnings'])} warnings:")
        for warning in results['warnings']:
            print(f"  - {warning}")
    
    if results['recommendations']:
        print(f"\n💡 {len(results['recommendations'])} recommendations:")
        for rec in results['recommendations']:
            print(f"  - {rec}")
    
    if results['errors']:
        print(f"\n❌ {len(results['errors'])} errors encountered")

if __name__ == "__main__":
    main()