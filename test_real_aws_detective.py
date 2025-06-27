#!/usr/bin/env python3
"""
Real AWS Detective Discovery Script

IMPORTANT: This script is for development understanding only.
- Gathers real AWS Detective configuration data
- Helps understand API structure and pagination patterns
- Data collected here informs implementation design
- NO real data should be used in tests or production code

This script discovers:
1. Detective delegation status across regions
2. Detective graphs and their configuration
3. Member account structure and status
4. GuardDuty prerequisite configuration
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

def discover_detective_configuration():
    """Discover current Detective configuration across all regions."""
    
    try:
        # Get list of all AWS regions
        print("🔍 Discovering AWS Detective configuration...")
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        regions_response = ec2_client.describe_regions()
        all_regions = [region['RegionName'] for region in regions_response['Regions']]
        
        discovery_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'regions_checked': len(all_regions),
            'detective_delegation': {},
            'detective_graphs': {},
            'guardduty_prerequisite': {},
            'summary': {
                'regions_with_delegation': 0,
                'regions_with_graphs': 0,
                'total_graphs_found': 0,
                'total_members_found': 0
            }
        }
        
        print(f"📊 Checking {len(all_regions)} AWS regions for Detective configuration...")
        
        # Check each region for Detective delegation and configuration
        for region in all_regions:
            print(f"\n🌍 Checking region: {region}")
            
            try:
                # Check Detective delegation
                print(f"  🔍 Checking Detective delegation...")
                orgs_client = boto3.client('organizations', region_name=region)
                
                try:
                    detective_admins = []
                    paginator = orgs_client.get_paginator('list_delegated_administrators')
                    for page in paginator.paginate(ServicePrincipal='detective.amazonaws.com'):
                        detective_admins.extend(page.get('DelegatedAdministrators', []))
                    
                    discovery_data['detective_delegation'][region] = safe_convert_datetime(detective_admins)
                    
                    if detective_admins:
                        discovery_data['summary']['regions_with_delegation'] += 1
                        admin_ids = [admin.get('Id') for admin in detective_admins]
                        print(f"    ✅ Detective delegated to: {', '.join(admin_ids)}")
                    else:
                        print(f"    ❌ No Detective delegation found")
                        
                except ClientError as e:
                    print(f"    ⚠️  Delegation check failed: {str(e)}")
                    discovery_data['detective_delegation'][region] = {'error': str(e)}
                
                # Check Detective graphs
                print(f"  🔍 Checking Detective graphs...")
                detective_client = boto3.client('detective', region_name=region)
                
                try:
                    # Detective list_graphs is NOT paginated - use direct call
                    response = detective_client.list_graphs()
                    all_graphs = response.get('GraphList', [])
                    
                    region_graph_data = {
                        'graphs': safe_convert_datetime(all_graphs),
                        'graph_count': len(all_graphs),
                        'members_per_graph': {}
                    }
                    
                    if all_graphs:
                        discovery_data['summary']['regions_with_graphs'] += 1
                        discovery_data['summary']['total_graphs_found'] += len(all_graphs)
                        print(f"    ✅ Found {len(all_graphs)} Detective graph(s)")
                        
                        # Get member details for each graph
                        for graph in all_graphs:
                            graph_arn = graph.get('Arn')
                            print(f"      📊 Checking members for graph: {graph_arn}")
                            
                            try:
                                # Detective list_members IS paginated
                                all_members = []
                                members_paginator = detective_client.get_paginator('list_members')
                                for page in members_paginator.paginate(GraphArn=graph_arn):
                                    all_members.extend(page.get('MemberDetails', []))
                                
                                region_graph_data['members_per_graph'][graph_arn] = {
                                    'members': safe_convert_datetime(all_members),
                                    'member_count': len(all_members)
                                }
                                
                                discovery_data['summary']['total_members_found'] += len(all_members)
                                
                                if all_members:
                                    enabled_count = sum(1 for m in all_members if m.get('Status') == 'ENABLED')
                                    invited_count = sum(1 for m in all_members if m.get('Status') == 'INVITED')
                                    print(f"        ✅ Members: {len(all_members)} total, {enabled_count} enabled, {invited_count} invited")
                                else:
                                    print(f"        ❌ No members found")
                                    
                            except ClientError as e:
                                print(f"        ⚠️  Member check failed: {str(e)}")
                                region_graph_data['members_per_graph'][graph_arn] = {'error': str(e)}
                    else:
                        print(f"    ❌ No Detective graphs found")
                    
                    discovery_data['detective_graphs'][region] = region_graph_data
                    
                except ClientError as e:
                    print(f"    ⚠️  Graph check failed: {str(e)}")
                    discovery_data['detective_graphs'][region] = {'error': str(e)}
                
                # Quick GuardDuty prerequisite check
                print(f"  🔍 Checking GuardDuty prerequisite...")
                try:
                    guardduty_client = boto3.client('guardduty', region_name=region)
                    detectors = guardduty_client.list_detectors()
                    
                    guardduty_data = {
                        'detectors': detectors.get('DetectorIds', []),
                        'detector_count': len(detectors.get('DetectorIds', []))
                    }
                    
                    if detectors.get('DetectorIds'):
                        print(f"    ✅ GuardDuty detectors found: {len(detectors['DetectorIds'])}")
                    else:
                        print(f"    ❌ No GuardDuty detectors found")
                    
                    discovery_data['guardduty_prerequisite'][region] = guardduty_data
                    
                except ClientError as e:
                    print(f"    ⚠️  GuardDuty check failed: {str(e)}")
                    discovery_data['guardduty_prerequisite'][region] = {'error': str(e)}
                
            except Exception as e:
                print(f"  ❌ General error in region {region}: {str(e)}")
                discovery_data['detective_delegation'][region] = {'error': f"General error: {str(e)}"}
                discovery_data['detective_graphs'][region] = {'error': f"General error: {str(e)}"}
                discovery_data['guardduty_prerequisite'][region] = {'error': f"General error: {str(e)}"}
        
        # Save discovery data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detective_discovery_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(discovery_data, f, indent=2, default=str)
        
        print(f"\n📋 Detective Discovery Summary:")
        print(f"  • Regions checked: {discovery_data['regions_checked']}")
        print(f"  • Regions with Detective delegation: {discovery_data['summary']['regions_with_delegation']}")
        print(f"  • Regions with Detective graphs: {discovery_data['summary']['regions_with_graphs']}")
        print(f"  • Total graphs found: {discovery_data['summary']['total_graphs_found']}")
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
    print("🚀 Starting AWS Detective Discovery...")
    print("⚠️  This script is for development understanding only.")
    print("⚠️  No real data will be used in tests or production code.")
    print()
    
    result = discover_detective_configuration()
    
    if result:
        print("\n✅ Detective discovery completed successfully!")
        print("\n🧠 Key insights for implementation:")
        print("  • Use pagination for list_graphs and list_members calls")
        print("  • Detective delegation is per-region (unlike Access Analyzer)")
        print("  • Member status can be 'ENABLED', 'INVITED', or other states")
        print("  • GuardDuty prerequisite check should verify detectors exist")
        print("  • Graph ARN is needed for member management operations")
    else:
        print("\n❌ Detective discovery failed!")
        sys.exit(1)