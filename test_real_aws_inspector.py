#!/usr/bin/env python3
"""
Real AWS Inspector Discovery Script

IMPORTANT: This script is for development understanding only.
- Gathers real AWS Inspector configuration data
- Helps understand API structure and pagination patterns
- Data collected here informs implementation design
- NO real data should be used in tests or production code

This script discovers:
1. Inspector delegation status across regions
2. Inspector scanning configurations (ECR, EC2, Lambda)
3. Member account structure and scanning status
4. Cost-related scanning settings and usage patterns
"""

import boto3
import json
import sys
from datetime import datetime, timezone
from botocore.exceptions import ClientError, NoCredentialsError

def safe_convert_datetime(obj):
    """Convert datetime objects to strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: safe_convert_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [safe_convert_datetime(item) for item in obj]
    else:
        return obj

def discover_inspector_configuration():
    """Discover current Inspector configuration across all regions."""
    
    try:
        # Get list of all AWS regions
        print("🔍 Discovering AWS Inspector configuration...")
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        regions_response = ec2_client.describe_regions()
        all_regions = [region['RegionName'] for region in regions_response['Regions']]
        
        discovery_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'regions_checked': len(all_regions),
            'inspector_delegation': {},
            'inspector_scanning_status': {},
            'inspector_members': {},
            'inspector_usage_data': {},
            'summary': {
                'regions_with_delegation': 0,
                'regions_with_scanning': 0,
                'total_scan_types_enabled': 0,
                'total_members_found': 0
            }
        }
        
        print(f"📊 Checking {len(all_regions)} AWS regions for Inspector configuration...")
        
        # Check each region for Inspector delegation and configuration
        for region in all_regions:
            print(f"\n🌍 Checking region: {region}")
            
            try:
                # Check Inspector delegation
                print(f"  🔍 Checking Inspector delegation...")
                orgs_client = boto3.client('organizations', region_name=region)
                
                try:
                    inspector_admins = []
                    paginator = orgs_client.get_paginator('list_delegated_administrators')
                    for page in paginator.paginate(ServicePrincipal='inspector2.amazonaws.com'):
                        inspector_admins.extend(page.get('DelegatedAdministrators', []))
                    
                    discovery_data['inspector_delegation'][region] = safe_convert_datetime(inspector_admins)
                    
                    if inspector_admins:
                        discovery_data['summary']['regions_with_delegation'] += 1
                        admin_ids = [admin.get('Id') for admin in inspector_admins]
                        print(f"    ✅ Inspector delegated to: {', '.join(admin_ids)}")
                    else:
                        print(f"    ❌ No Inspector delegation found")
                        
                except ClientError as e:
                    print(f"    ⚠️  Delegation check failed: {str(e)}")
                    discovery_data['inspector_delegation'][region] = {'error': str(e)}
                
                # Check Inspector scanning status
                print(f"  🔍 Checking Inspector scanning configuration...")
                inspector_client = boto3.client('inspector2', region_name=region)
                
                try:
                    # Get account scanning status
                    scanning_status = inspector_client.batch_get_account_status()
                    
                    region_scanning_data = {
                        'accounts': safe_convert_datetime(scanning_status.get('accounts', [])),
                        'failed_accounts': safe_convert_datetime(scanning_status.get('failedAccounts', [])),
                        'scanning_enabled': False,
                        'scan_types': {},
                        'resource_counts': {}
                    }
                    
                    # Analyze scanning configuration
                    for account in scanning_status.get('accounts', []):
                        account_id = account.get('accountId')
                        resource_state = account.get('resourceState', {})
                        
                        print(f"    📊 Account {account_id} scanning status:")
                        
                        # Check each resource type
                        for resource_type, state_info in resource_state.items():
                            status = state_info.get('status')
                            if status == 'ENABLED':
                                region_scanning_data['scanning_enabled'] = True
                                region_scanning_data['scan_types'][resource_type] = 'ENABLED'
                                discovery_data['summary']['total_scan_types_enabled'] += 1
                                print(f"      ✅ {resource_type}: {status}")
                            else:
                                region_scanning_data['scan_types'][resource_type] = status
                                print(f"      ❌ {resource_type}: {status}")
                    
                    if region_scanning_data['scanning_enabled']:
                        discovery_data['summary']['regions_with_scanning'] += 1
                    
                    discovery_data['inspector_scanning_status'][region] = region_scanning_data
                    
                except ClientError as e:
                    print(f"    ⚠️  Scanning status check failed: {str(e)}")
                    discovery_data['inspector_scanning_status'][region] = {'error': str(e)}
                
                # Check Inspector members (if delegated)
                if inspector_admins:
                    print(f"  🔍 Checking Inspector member accounts...")
                    try:
                        # Get member account information
                        members_paginator = inspector_client.get_paginator('list_members')
                        all_members = []
                        for page in members_paginator.paginate():
                            all_members.extend(page.get('members', []))
                        
                        discovery_data['inspector_members'][region] = {
                            'members': safe_convert_datetime(all_members),
                            'member_count': len(all_members)
                        }
                        
                        discovery_data['summary']['total_members_found'] += len(all_members)
                        
                        if all_members:
                            print(f"    ✅ Inspector members: {len(all_members)} accounts")
                            
                            # Show member status breakdown
                            status_counts = {}
                            for member in all_members:
                                status = member.get('relationshipStatus', 'UNKNOWN')
                                status_counts[status] = status_counts.get(status, 0) + 1
                            
                            for status, count in status_counts.items():
                                print(f"      📊 {status}: {count} members")
                        else:
                            print(f"    ❌ No Inspector members found")
                            
                    except ClientError as e:
                        print(f"    ⚠️  Member check failed: {str(e)}")
                        discovery_data['inspector_members'][region] = {'error': str(e)}
                
                # Check Inspector usage/cost data
                print(f"  🔍 Checking Inspector usage data...")
                try:
                    # Get usage totals for cost awareness
                    usage_totals = inspector_client.get_usage_totals()
                    
                    discovery_data['inspector_usage_data'][region] = {
                        'usage_totals': safe_convert_datetime(usage_totals.get('totals', [])),
                        'total_usage': usage_totals.get('total', {})
                    }
                    
                    for total in usage_totals.get('totals', []):
                        account_id = total.get('accountId')
                        usage = total.get('usage', [])
                        if usage:
                            print(f"    💰 Account {account_id}: {len(usage)} usage entries")
                    
                except ClientError as e:
                    print(f"    ⚠️  Usage data check failed: {str(e)}")
                    discovery_data['inspector_usage_data'][region] = {'error': str(e)}
                
            except Exception as e:
                print(f"  ❌ General error in region {region}: {str(e)}")
                discovery_data['inspector_delegation'][region] = {'error': f"General error: {str(e)}"}
                discovery_data['inspector_scanning_status'][region] = {'error': f"General error: {str(e)}"}
                discovery_data['inspector_members'][region] = {'error': f"General error: {str(e)}"}
                discovery_data['inspector_usage_data'][region] = {'error': f"General error: {str(e)}"}
        
        # Save discovery data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inspector_discovery_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(discovery_data, f, indent=2, default=str)
        
        print(f"\n📋 Inspector Discovery Summary:")
        print(f"  • Regions checked: {discovery_data['regions_checked']}")
        print(f"  • Regions with Inspector delegation: {discovery_data['summary']['regions_with_delegation']}")
        print(f"  • Regions with active scanning: {discovery_data['summary']['regions_with_scanning']}")
        print(f"  • Total scan types enabled: {discovery_data['summary']['total_scan_types_enabled']}")
        print(f"  • Total members found: {discovery_data['summary']['total_members_found']}")
        print(f"\n💾 Discovery data saved to: {filename}")
        
        return discovery_data
        
    except NoCredentialsError:
        print("❌ AWS credentials not found. Please run 'aws sso login' first.")
        return None
    except Exception as e:
        print(f"❌ Discovery failed: {str(e)}")
        return None

if __name__ == "__main__":
    print("🚀 Starting AWS Inspector Discovery...")
    print("⚠️  This script is for development understanding only.")
    print("⚠️  No real data will be used in tests or production code.")
    print()
    
    result = discover_inspector_configuration()
    
    if result:
        print("\n✅ Inspector discovery completed successfully!")
        print("\n🧠 Key insights for implementation:")
        print("  • Inspector uses 'inspector2.amazonaws.com' service principal for delegation")
        print("  • batch_get_account_status() shows scanning configuration per account")
        print("  • list_members is paginated for member account management")
        print("  • get_usage_totals() provides cost awareness data")
        print("  • Resource types: ECR, EC2, Lambda scanning can be enabled independently")
        print("  • Minimal setup should focus on delegation without enabling expensive scanning")
    else:
        print("\n❌ Inspector discovery failed!")
        sys.exit(1)