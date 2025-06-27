#!/usr/bin/env python3

"""
Real AWS IAM Access Analyzer Discovery Script

This script discovers the current IAM Access Analyzer configuration across regions and accounts.
Used to understand real-world configurations and build the implementation accordingly.

Manual steps to automate:
1. Org account: Delegate administration to Security-Adm account
2. Security-Adm: Set up organisation-wide analyzer for external access (all regions)
3. Security-Adm: Set up organisation-wide analyzer for unused access (main region only)
"""

import boto3
import json
import sys
from datetime import datetime
from botocore.exceptions import ClientError

def discover_access_analyzer_in_region(region, admin_account, security_account, cross_account_role):
    """Discover Access Analyzer configuration in a specific region."""
    
    print(f"\n🔍 Discovering Access Analyzer in region {region}...")
    
    discovery = {
        'region': region,
        'timestamp': datetime.now().isoformat(),
        'admin_account_view': {},
        'security_account_view': {},
        'delegation_status': 'unknown',
        'errors': []
    }
    
    try:
        # Check from admin account perspective
        print(f"  📊 Checking from admin account perspective...")
        
        # Check delegation status (with pagination)
        orgs_client = boto3.client('organizations', region_name=region)
        try:
            all_delegated_admins = []
            paginator = orgs_client.get_paginator('list_delegated_administrators')
            for page in paginator.paginate(ServicePrincipal='access-analyzer.amazonaws.com'):
                all_delegated_admins.extend(page.get('DelegatedAdministrators', []))
            
            discovery['admin_account_view']['delegated_administrators'] = all_delegated_admins
            
            # Check if delegated to security account
            is_delegated_to_security = False
            for admin in all_delegated_admins:
                if admin.get('Id') == security_account:
                    discovery['delegation_status'] = 'delegated_to_security'
                    is_delegated_to_security = True
                    print(f"    ✅ Delegated to Security account: {admin.get('Name', admin.get('Id'))}")
                    break
            else:
                if all_delegated_admins:
                    discovery['delegation_status'] = 'delegated_to_other'
                    other_admins = [admin.get('Id') for admin in all_delegated_admins]
                    print(f"    ⚠️  Delegated to other account(s): {', '.join(other_admins)}")
                else:
                    discovery['delegation_status'] = 'not_delegated'
                    print(f"    ❌ No delegation found")
                    
        except ClientError as e:
            error_msg = f"Delegation check failed: {str(e)}"
            discovery['errors'].append(error_msg)
            print(f"    ❌ {error_msg}")
        
        # Check analyzers from admin account (with pagination)
        access_analyzer_client = boto3.client('accessanalyzer', region_name=region)
        try:
            all_analyzers = []
            paginator = access_analyzer_client.get_paginator('list_analyzers')
            for page in paginator.paginate():
                all_analyzers.extend(page.get('analyzers', []))
            
            discovery['admin_account_view']['analyzers'] = all_analyzers
            
            print(f"    📋 Found {len(discovery['admin_account_view']['analyzers'])} analyzers from admin account")
            for analyzer in discovery['admin_account_view']['analyzers']:
                print(f"      - {analyzer.get('name')} (Type: {analyzer.get('type')}, Status: {analyzer.get('status')})")
                
        except ClientError as e:
            error_msg = f"List analyzers failed: {str(e)}"
            discovery['errors'].append(error_msg)
            print(f"    ❌ {error_msg}")
        
        # If delegated to security account, check from security account perspective
        if is_delegated_to_security and cross_account_role and security_account != admin_account:
            print(f"  🔄 Switching to delegated admin account for complete data...")
            
            try:
                # Assume role in security account
                sts_client = boto3.client('sts')
                response = sts_client.assume_role(
                    RoleArn=f"arn:aws:iam::{security_account}:role/{cross_account_role}",
                    RoleSessionName=f"access_analyzer_discovery_{security_account}"
                )
                
                credentials = response['Credentials']
                
                # Create Access Analyzer client with assumed role
                delegated_analyzer_client = boto3.client(
                    'accessanalyzer',
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=region
                )
                
                # Get analyzers from delegated admin perspective (with pagination)
                all_delegated_analyzers = []
                delegated_paginator = delegated_analyzer_client.get_paginator('list_analyzers')
                for page in delegated_paginator.paginate():
                    all_delegated_analyzers.extend(page.get('analyzers', []))
                
                discovery['security_account_view']['analyzers'] = all_delegated_analyzers
                
                print(f"    📋 Found {len(discovery['security_account_view']['analyzers'])} analyzers from security account")
                
                for analyzer in discovery['security_account_view']['analyzers']:
                    analyzer_name = analyzer.get('name')
                    analyzer_type = analyzer.get('type')
                    analyzer_status = analyzer.get('status')
                    
                    print(f"      - {analyzer_name} (Type: {analyzer_type}, Status: {analyzer_status})")
                    
                    # Get detailed analyzer configuration
                    try:
                        analyzer_details = delegated_analyzer_client.get_analyzer(analyzerName=analyzer_name)
                        analyzer['details'] = analyzer_details.get('analyzer', {})
                        
                        # Check for findings (with pagination)
                        findings_count = 0
                        try:
                            paginator = delegated_analyzer_client.get_paginator('list_findings')
                            for page in paginator.paginate(analyzerArn=analyzer.get('arn')):
                                findings_count += len(page.get('findings', []))
                            
                            analyzer['findings_count'] = findings_count
                            print(f"        📊 Active findings: {findings_count}")
                            
                        except ClientError as e:
                            error_msg = f"List findings failed for {analyzer_name}: {str(e)}"
                            discovery['errors'].append(error_msg)
                            print(f"        ❌ {error_msg}")
                            
                    except ClientError as e:
                        error_msg = f"Get analyzer details failed for {analyzer_name}: {str(e)}"
                        discovery['errors'].append(error_msg)
                        print(f"        ❌ {error_msg}")
                
            except ClientError as e:
                error_msg = f"Cross-account access failed: {str(e)}"
                discovery['errors'].append(error_msg)
                print(f"    ❌ {error_msg}")
        
    except Exception as e:
        error_msg = f"General error in region {region}: {str(e)}"
        discovery['errors'].append(error_msg)
        print(f"  ❌ {error_msg}")
    
    return discovery

def main():
    """Main discovery function."""
    print("🔍 IAM Access Analyzer Real AWS Discovery")
    print("=" * 50)
    
    # Configuration (update these for your environment)
    admin_account = "123456789012"  # Your org management account
    security_account = "234567890123"  # Your security account
    regions = ['us-east-1', 'us-west-2', 'eu-west-1']  # Your enabled regions
    cross_account_role = "AWSControlTowerExecution"  # Your cross-account role
    
    print(f"Admin Account: {admin_account}")
    print(f"Security Account: {security_account}")
    print(f"Regions: {regions}")
    print(f"Cross-Account Role: {cross_account_role}")
    
    all_discoveries = {}
    
    for region in regions:
        discovery = discover_access_analyzer_in_region(region, admin_account, security_account, cross_account_role)
        all_discoveries[region] = discovery
    
    # Save discovery results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'access_analyzer_discovery_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(all_discoveries, f, indent=2, default=str)
    
    print(f"\n💾 Discovery results saved to: {filename}")
    
    # Summary
    print(f"\n📊 DISCOVERY SUMMARY")
    print(f"=" * 30)
    
    for region, discovery in all_discoveries.items():
        admin_analyzers = len(discovery.get('admin_account_view', {}).get('analyzers', []))
        security_analyzers = len(discovery.get('security_account_view', {}).get('analyzers', []))
        delegation_status = discovery.get('delegation_status', 'unknown')
        errors = len(discovery.get('errors', []))
        
        print(f"\n🌍 {region}:")
        print(f"  Delegation: {delegation_status}")
        print(f"  Admin view analyzers: {admin_analyzers}")
        print(f"  Security view analyzers: {security_analyzers}")
        if errors > 0:
            print(f"  Errors: {errors}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Discovery interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Discovery failed: {e}")
        sys.exit(1)