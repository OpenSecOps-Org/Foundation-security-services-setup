#!/usr/bin/env python3
"""
Real AWS Config Discovery Script - Simple Version

This script discovers your current AWS Config setup using the exact same
calling patterns that will be used in the actual modules/aws_config.py.

The goal is to gather real AWS data to inform the TDD implementation.
"""

import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, List, Any
from datetime import datetime

def discover_current_config_state(params: Dict[str, Any], verbose=False) -> Dict[str, Any]:
    """
    Discover current AWS Config state using the same parameter structure
    that the real setup_aws_config function will receive.
    
    This function mirrors what setup_aws_config will do:
    1. Connect to AWS (using default session - assumes aws sso login completed)
    2. Check Config in all regions
    3. Report current state vs desired state
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'params_used': params,
        'regions_checked': [],
        'config_state': {},
        'recommendations': [],
        'warnings': [],
        'errors': []
    }
    
    print("\n" + "="*60)
    print("AWS CONFIG DISCOVERY")
    print("="*60)
    
    if verbose:
        print(f"Regions: {params['regions']}")
        print(f"Admin Account: {params['admin_account']}")
        print(f"Security Account: {params['security_account']}")
        print(f"Organization ID: {params['org_id']}")
    
    regions = params['regions']
    main_region = regions[0]
    other_regions = regions[1:] if len(regions) > 1 else []
    
    print(f"\nMain region: {main_region} (should record IAM global events)")
    if other_regions:
        print(f"Other regions: {other_regions} (should NOT record IAM global events)")
    
    # Check each region's current Config state
    for region in regions:
        print(f"\n🔍 Checking Config in region {region}...")
        region_state = check_config_in_region(region, verbose)
        results['config_state'][region] = region_state
        results['regions_checked'].append(region)
        
        # Analyze findings
        if region_state['config_enabled']:
            print(f"  ✅ Config is ENABLED in {region}")
            
            # Check IAM global recording setting
            global_recording = region_state.get('records_global_iam', 'unknown')
            if region == main_region:
                if global_recording:
                    print(f"  ✅ Main region correctly records IAM global events")
                else:
                    print(f"  ⚠️  Main region should record IAM global events but doesn't")
                    results['warnings'].append(f"Main region {region} not recording IAM global events")
            else:
                if not global_recording:
                    print(f"  ✅ Non-main region correctly excludes IAM global events")
                else:
                    print(f"  ⚠️  Non-main region should NOT record IAM global events")
                    results['warnings'].append(f"Non-main region {region} recording IAM global events")
        else:
            print(f"  ❌ Config is DISABLED in {region}")
            results['recommendations'].append(f"Enable Config in region {region}")
    
    return results

def check_config_in_region(region: str, verbose=False) -> Dict[str, Any]:
    """
    Check AWS Config status in a specific region.
    Uses default boto3 session (assumes aws sso login completed).
    
    This exactly mirrors what the real modules/aws_config.py will do.
    """
    region_data = {
        'region': region,
        'config_enabled': False,
        'configuration_recorders': [],
        'delivery_channels': [],
        'records_global_iam': False,
        'config_rules_count': 0,
        'errors': []
    }
    
    try:
        # Use default session - this matches what the real module will do
        # Foundation components assume aws sso login has been completed
        config_client = boto3.client('config', region_name=region)
        
        # Check configuration recorders
        try:
            recorders_response = config_client.describe_configuration_recorders()
            recorders = recorders_response.get('ConfigurationRecorders', [])
            region_data['configuration_recorders'] = recorders
            region_data['config_enabled'] = len(recorders) > 0
            
            if verbose:
                print(f"    Found {len(recorders)} configuration recorders")
            
            # Check if any recorder includes global IAM resources
            for recorder in recorders:
                recording_group = recorder.get('recordingGroup', {})
                include_global = recording_group.get('includeGlobalResourceTypes', False)
                all_supported = recording_group.get('allSupported', False)
                
                if include_global or all_supported:
                    region_data['records_global_iam'] = True
                    if verbose:
                        print(f"    Recorder '{recorder.get('name', 'unnamed')}' records global IAM resources")
                
        except ClientError as e:
            error_msg = f"Configuration recorders check failed: {str(e)}"
            region_data['errors'].append(error_msg)
            if verbose:
                print(f"    ❌ {error_msg}")
        
        # Check delivery channels
        try:
            channels_response = config_client.describe_delivery_channels()
            channels = channels_response.get('DeliveryChannels', [])
            region_data['delivery_channels'] = channels
            
            if verbose:
                print(f"    Found {len(channels)} delivery channels")
                
        except ClientError as e:
            error_msg = f"Delivery channels check failed: {str(e)}"
            region_data['errors'].append(error_msg)
            if verbose:
                print(f"    ❌ {error_msg}")
        
        # Check Config rules count
        try:
            rules_response = config_client.describe_config_rules()
            rules = rules_response.get('ConfigRules', [])
            region_data['config_rules_count'] = len(rules)
            
            if verbose:
                print(f"    Found {len(rules)} Config rules")
                
        except ClientError as e:
            error_msg = f"Config rules check failed: {str(e)}"
            region_data['errors'].append(error_msg)
            if verbose:
                print(f"    ❌ {error_msg}")
                
    except Exception as e:
        error_msg = f"General error checking region {region}: {str(e)}"
        region_data['errors'].append(error_msg)
        print(f"    ❌ {error_msg}")
    
    return region_data

def save_discovery_results(results: Dict[str, Any], filename: str = None):
    """Save discovery results to JSON file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"config_discovery_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filename}")

def main():
    """Main function - simulates exactly how setup_aws_config will be called."""
    print("🔍 AWS Config Real Discovery (TDD Pattern)")
    print("This uses the exact calling pattern of the real setup_aws_config function")
    print("-" * 70)
    
    # Create params dict exactly as main script does
    params = {
        'admin_account': '515966493378',      # From your accounts.toml
        'security_account': '650251698273',   # From your accounts.toml  
        'regions': ['eu-north-1', 'us-east-1'],  # From your parameters.toml
        'cross_account_role': 'AWSControlTowerExecution',
        'org_id': 'o-d09svdge39',
        'root_ou': 'r-jyql'
    }
    
    # Run discovery with same parameters that setup_aws_config will receive
    results = discover_current_config_state(params, verbose=True)
    
    # Save results for analysis
    save_discovery_results(results)
    
    # Summary
    print("\n" + "="*60)
    print("DISCOVERY SUMMARY")
    print("="*60)
    
    enabled_regions = [r for r, data in results['config_state'].items() if data['config_enabled']]
    disabled_regions = [r for r, data in results['config_state'].items() if not data['config_enabled']]
    
    print(f"Config enabled in: {enabled_regions if enabled_regions else 'None'}")
    print(f"Config disabled in: {disabled_regions if disabled_regions else 'None'}")
    
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