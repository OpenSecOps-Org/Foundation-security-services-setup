"""
AWS Config setup module

Automates the manual steps:
1. In the Org account, enable AWS Config in your main region. Remove the 
   filter: in this region, you want to record IAM global events.
2. Enable AWS Config in your other enabled regions. Do not remove the IAM 
   global filter in these regions.
"""

from .utils import printc, YELLOW, LIGHT_BLUE, GREEN, RED, GRAY, END, BOLD

def setup_aws_config(enabled, params, dry_run, verbose):
    """Setup AWS Config in org account with proper IAM global event recording."""
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "AWS CONFIG SETUP")
        printc(LIGHT_BLUE, "="*60)
        
        if verbose:
            printc(GRAY, f"Enabled: {enabled}")
            printc(GRAY, f"Regions: {params['regions']}")
            printc(GRAY, f"Organization ID: {params['org_id']}")
            printc(GRAY, f"Dry Run: {dry_run}")
            printc(GRAY, f"Verbose: {verbose}")
        
        if enabled == 'No':
            # HUGE WARNING when someone tries to disable Config
            printc(RED, "\n" + "🚨" * 20)
            printc(RED, "🚨 CRITICAL WARNING: AWS Config Disable Requested! 🚨")
            printc(RED, "🚨" * 20)
            printc(RED, "")
            printc(RED, "AWS Config is a CRITICAL security service that:")
            printc(RED, "• Provides configuration compliance monitoring")
            printc(RED, "• Enables Security Hub controls and findings")
            printc(RED, "• Records resource configuration changes")
            printc(RED, "• Required for many security compliance frameworks")
            printc(RED, "")
            printc(RED, "⛔ DISABLING CONFIG WILL BREAK SECURITY MONITORING!")
            printc(RED, "⛔ This action is STRONGLY DISCOURAGED!")
            printc(RED, "")
            printc(RED, "Config setup SKIPPED due to enabled=No parameter.")
            printc(RED, "🚨" * 20)
            
            # Check for spurious AWS Config activations in ALL regions (since service is disabled)
            regions = params['regions']
            admin_account = params['admin_account']
            security_account = params['security_account']
            
            if verbose:
                printc(GRAY, f"\n🔍 Checking all AWS regions for spurious AWS Config activation...")
            
            # Pass empty list as expected_regions so ALL regions are checked
            anomalous_regions = check_anomalous_config_regions([], admin_account, security_account, verbose)
            
            if anomalous_regions:
                printc(YELLOW, f"\n⚠️  SPURIOUS AWS CONFIG ACTIVATION DETECTED:")
                printc(YELLOW, f"AWS Config recorders found in unexpected regions:")
                total_recorders = sum(anomaly['recorder_count'] for anomaly in anomalous_regions)
                printc(YELLOW, f"")
                printc(YELLOW, f"Current spurious AWS Config resources:")
                printc(YELLOW, f"  • {total_recorders} recorder(s) across {len(anomalous_regions)} unexpected region(s)")
                for anomaly in anomalous_regions:
                    region = anomaly['region']
                    recorder_count = anomaly['recorder_count']
                    printc(YELLOW, f"    📍 {region}: {recorder_count} recorder(s) active")
                    for recorder_detail in anomaly['recorder_details']:
                        recorder_name = recorder_detail['recorder_name']
                        recording_enabled = "enabled" if recorder_detail['recording_enabled'] else "disabled"
                        global_resources = "with global" if recorder_detail['include_global_resources'] else "local only"
                        printc(YELLOW, f"      📝 Recorder {recorder_name}: {recording_enabled} ({global_resources})")
                printc(YELLOW, f"")
                printc(YELLOW, f"📋 SPURIOUS ACTIVATION RECOMMENDATIONS:")
                printc(YELLOW, f"  • Review: These recorders may be configuration drift or forgotten resources")
                printc(YELLOW, f"  • Recommended: Disable AWS Config recorders in these regions to control costs")
                printc(YELLOW, f"  • Note: AWS Config generates storage costs per region and per rule evaluation")
            else:
                if verbose:
                    printc(GRAY, f"   ✅ AWS Config is not active in any region - no cleanup needed")
            
            return True
        
        # enabled == 'Yes' - proceed with Config setup/verification
        regions = params['regions']
        admin_account = params['admin_account']
        security_account = params['security_account']
        main_region = regions[0]
        other_regions = regions[1:] if len(regions) > 1 else []
        
        printc(YELLOW, f"Checking AWS Config setup in {len(regions)} regions...")
        if verbose:
            printc(GRAY, f"Main region: {main_region} (should record IAM global events)")
            if other_regions:
                printc(GRAY, f"Other regions: {other_regions} (should exclude IAM global events)")
        
        # Check current Config state in all regions
        config_status = {}
        any_changes_needed = False
        
        for region in regions:
            if verbose:
                printc(GRAY, f"\n🔍 Checking Config in region {region}...")
            
            region_status = check_config_in_region(region, main_region == region, verbose)
            config_status[region] = region_status
            
            if not region_status['needs_changes']:
                if verbose:
                    printc(GREEN, f"  ✅ Config properly configured in {region}")
            else:
                any_changes_needed = True
                if verbose:
                    printc(YELLOW, f"  ⚠️  Config needs changes in {region}")
        
        # Step 2: Check for anomalous AWS Config recorders in unexpected regions
        if verbose:
            printc(GRAY, f"\n🔍 Checking for AWS Config recorders in unexpected regions...")
        
        anomalous_regions = check_anomalous_config_regions(regions, admin_account, security_account, verbose)
        
        if anomalous_regions:
            any_changes_needed = True  # Anomalous regions require attention
            printc(YELLOW, f"\n⚠️  ANOMALOUS AWS CONFIG RECORDERS DETECTED:")
            printc(YELLOW, f"AWS Config recorders are active in regions outside your configuration:")
            for anomaly in anomalous_regions:
                region = anomaly['region']
                recorder_count = anomaly['recorder_count']
                printc(YELLOW, f"  • {region}: {recorder_count} recorder(s) active (not in your regions list)")
            printc(YELLOW, f"")
            printc(YELLOW, f"📋 ANOMALY RECOMMENDATIONS:")
            printc(YELLOW, f"  • Review: Determine if these recorders are intentional or configuration drift")
            printc(YELLOW, f"  • Recommended: Disable AWS Config recorders in these regions to control costs")
            printc(YELLOW, f"  • Note: Adding regions to OpenSecOps requires full system redeployment")
            printc(YELLOW, f"  💰 Cost Impact: AWS Config generates storage costs per region and per rule evaluation")
        
        # Report findings and take action
        if not any_changes_needed:
            printc(GREEN, "✅ AWS Config is already properly configured in all regions!")
            printc(GREEN, "   No changes needed - existing setup meets stringent security standards.")
            
            # Show detailed configuration for each region ONLY when verbose
            if verbose:
                printc(LIGHT_BLUE, "\n📋 Current AWS Config Configuration:")
                for region, status in config_status.items():
                    printc(LIGHT_BLUE, f"\n🌍 Region: {region}")
                    if status['config_enabled']:
                        for detail in status['config_details']:
                            printc(GRAY, f"  {detail}")
                    else:
                        printc(GRAY, "  Config not enabled in this region")
            
            return True
        
        # Some changes needed
        printc(YELLOW, "⚠️  AWS Config needs configuration in some regions:")
        
        for region, status in config_status.items():
            if status['needs_changes']:
                for issue in status['issues']:
                    printc(YELLOW, f"  • {region}: {issue}")
        
        if dry_run:
            printc(YELLOW, "\n🔍 DRY RUN: Would make the following changes:")
            for region, status in config_status.items():
                if status['needs_changes']:
                    for action in status['actions']:
                        printc(YELLOW, f"  • {region}: {action}")
        else:
            printc(YELLOW, "\n🔧 Making Config changes...")
            # TODO: Implement actual Config changes
            for region, status in config_status.items():
                if status['needs_changes']:
                    printc(YELLOW, f"  TODO: Implement changes for {region}")
        
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_aws_config: {e}")
        return False

def check_config_in_region(region, is_main_region, verbose=False):
    """
    Check AWS Config status in a specific region.
    Returns status and needed changes.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    status = {
        'region': region,
        'config_enabled': False,
        'records_global_iam': False,
        'needs_changes': False,
        'issues': [],
        'actions': [],
        'errors': [],
        'config_details': []
    }
    
    try:
        config_client = boto3.client('config', region_name=region)
        
        # Check configuration recorders
        try:
            recorders_response = config_client.describe_configuration_recorders()
            recorders = recorders_response.get('ConfigurationRecorders', [])
            
            if not recorders:
                status['needs_changes'] = True
                status['issues'].append("No configuration recorders found")
                status['actions'].append("Create configuration recorder")
                status['config_details'].append("❌ No configuration recorders found")
                return status
            
            status['config_enabled'] = True
            status['config_details'].append(f"✅ Configuration Recorders: {len(recorders)} found")
            
            # Analyze each recorder in detail
            for i, recorder in enumerate(recorders):
                recorder_name = recorder.get('name', f'recorder-{i}')
                role_arn = recorder.get('roleARN', 'Unknown')
                
                status['config_details'].append(f"   📝 Recorder '{recorder_name}':")
                status['config_details'].append(f"      IAM Role: {role_arn}")
                
                # Analyze recording group settings
                recording_group = recorder.get('recordingGroup', {})
                include_global = recording_group.get('includeGlobalResourceTypes', False)
                all_supported = recording_group.get('allSupported', False)
                recording_strategy = recording_group.get('recordingStrategy', {}).get('useOnly', 'Unknown')
                
                if all_supported:
                    status['config_details'].append("      📊 Recording: All supported resources")
                    status['records_global_iam'] = True
                else:
                    resource_types = recording_group.get('resourceTypes', [])
                    exclusions = recording_group.get('exclusionByResourceTypes', {}).get('resourceTypes', [])
                    
                    if exclusions:
                        status['config_details'].append(f"      📊 Recording: All resources except {len(exclusions)} excluded types")
                        status['config_details'].append(f"      🚫 Excluded: {', '.join(exclusions[:3])}{'...' if len(exclusions) > 3 else ''}")
                    elif resource_types:
                        status['config_details'].append(f"      📊 Recording: {len(resource_types)} specific resource types")
                    else:
                        status['config_details'].append("      📊 Recording: Configuration unclear")
                
                # IAM global resource recording
                if include_global:
                    status['config_details'].append("      🌍 IAM Global Resources: ✅ Included")
                    status['records_global_iam'] = True
                elif all_supported:
                    status['config_details'].append("      🌍 IAM Global Resources: ✅ Included (via all supported)")
                else:
                    status['config_details'].append("      🌍 IAM Global Resources: ❌ Excluded")
                
                # Recording frequency
                recording_mode = recorder.get('recordingMode', {})
                frequency = recording_mode.get('recordingFrequency', 'Unknown')
                status['config_details'].append(f"      ⏱️  Recording Frequency: {frequency}")
            
            # Validate IAM global recording matches region role
            if is_main_region and not status['records_global_iam']:
                status['needs_changes'] = True
                status['issues'].append("Main region should record IAM global events but doesn't")
                status['actions'].append("Enable IAM global resource recording")
            elif not is_main_region and status['records_global_iam']:
                status['needs_changes'] = True
                status['issues'].append("Non-main region should NOT record IAM global events")
                status['actions'].append("Disable IAM global resource recording")
            
        except ClientError as e:
            error_msg = f"Configuration recorders check failed: {str(e)}"
            status['errors'].append(error_msg)
            if verbose:
                printc(RED, f"    ❌ {error_msg}")
        
        # Check delivery channels
        try:
            channels_response = config_client.describe_delivery_channels()
            channels = channels_response.get('DeliveryChannels', [])
            
            if not channels and status['config_enabled']:
                status['needs_changes'] = True
                status['issues'].append("No delivery channels found")
                status['actions'].append("Create delivery channel")
                status['config_details'].append("❌ No delivery channels found")
            elif channels:
                status['config_details'].append(f"✅ Delivery Channels: {len(channels)} found")
                
                for i, channel in enumerate(channels):
                    channel_name = channel.get('name', f'channel-{i}')
                    s3_bucket = channel.get('s3BucketName', 'Unknown')
                    s3_key_prefix = channel.get('s3KeyPrefix', 'None')
                    sns_topic = channel.get('snsTopicARN', 'None')
                    
                    status['config_details'].append(f"   📦 Channel '{channel_name}':")
                    status['config_details'].append(f"      S3 Bucket: {s3_bucket}")
                    if s3_key_prefix != 'None':
                        status['config_details'].append(f"      S3 Key Prefix: {s3_key_prefix}")
                    if sns_topic != 'None':
                        status['config_details'].append(f"      SNS Topic: {sns_topic}")
                    
                    # Check delivery properties
                    delivery_properties = channel.get('deliveryProperties', {})
                    if delivery_properties:
                        max_file_size = delivery_properties.get('deliveryFrequency', 'Unknown')
                        status['config_details'].append(f"      Delivery Frequency: {max_file_size}")
                
        except ClientError as e:
            error_msg = f"Delivery channels check failed: {str(e)}"
            status['errors'].append(error_msg)
            status['config_details'].append(f"❌ Delivery channels check failed: {str(e)}")
            if verbose:
                printc(RED, f"    ❌ {error_msg}")
        
        # Check Config rules count with pagination
        try:
            all_rules = []
            paginator = config_client.get_paginator('describe_config_rules')
            
            for page in paginator.paginate():
                rules = page.get('ConfigRules', [])
                all_rules.extend(rules)
            
            rules_count = len(all_rules)
            status['config_details'].append(f"✅ Config Rules: {rules_count} active rules")
            
            if rules_count > 0:
                # Categorize rules by source
                aws_managed = sum(1 for rule in all_rules if rule.get('Source', {}).get('Owner') == 'AWS')
                custom = rules_count - aws_managed
                
                if aws_managed > 0:
                    status['config_details'].append(f"   📋 AWS Managed Rules: {aws_managed}")
                if custom > 0:
                    status['config_details'].append(f"   📋 Custom Rules: {custom}")
            
        except ClientError as e:
            error_msg = f"Config rules check failed: {str(e)}"
            status['errors'].append(error_msg)
            status['config_details'].append(f"❌ Config rules check failed: {str(e)}")
            if verbose:
                printc(RED, f"    ❌ {error_msg}")
                
    except Exception as e:
        error_msg = f"General error checking region {region}: {str(e)}"
        status['errors'].append(error_msg)
        if verbose:
            printc(RED, f"    ❌ {error_msg}")
    
    return status

def check_anomalous_config_regions(expected_regions, admin_account, security_account, verbose=False):
    """
    Check for AWS Config configuration recorders active in regions outside the expected list.
    
    This detects configuration drift where AWS Config was enabled in regions
    not included in the current setup, which could generate unexpected costs.
    
    Returns list of anomalous regions with configuration recorder details.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    anomalous_regions = []
    
    try:
        # Get all AWS regions to check for anomalous configuration recorders
        ec2_client = boto3.client('ec2', region_name=expected_regions[0] if expected_regions else 'us-east-1')
        regions_response = ec2_client.describe_regions()
        all_regions = [region['RegionName'] for region in regions_response['Regions']]
        
        # Check regions that are NOT in our expected list
        unexpected_regions = [region for region in all_regions if region not in expected_regions]
        
        if verbose:
            printc(GRAY, f"    Checking {len(unexpected_regions)} regions outside configuration...")
        
        for region in unexpected_regions:
            try:
                config_client = boto3.client('config', region_name=region)
                
                # Check if there are any configuration recorders in this region
                recorders_response = config_client.describe_configuration_recorders()
                recorders = recorders_response.get('ConfigurationRecorders', [])
                
                recorder_details = []
                for recorder in recorders:
                    try:
                        # Get recording status for this recorder
                        status_response = config_client.describe_configuration_recorder_status(
                            ConfigurationRecorderNames=[recorder['name']]
                        )
                        recorder_status = status_response.get('ConfigurationRecordersStatus', [])
                        recording_enabled = False
                        if recorder_status:
                            recording_enabled = recorder_status[0].get('recording', False)
                        
                        recorder_details.append({
                            'recorder_name': recorder['name'],
                            'recording_enabled': recording_enabled,
                            'recording_mode': recorder.get('recordingMode', {}).get('recordingModeOverrides', []),
                            'include_global_resources': recorder.get('recordingGroup', {}).get('includeGlobalResourceTypes', False)
                        })
                    except ClientError as e:
                        if verbose:
                            printc(GRAY, f"    (Could not get status for recorder {recorder['name']}: {str(e)})")
                        recorder_details.append({
                            'recorder_name': recorder['name'],
                            'recording_enabled': False,
                            'recording_mode': 'Unknown',
                            'include_global_resources': False
                        })
                
                if recorder_details:
                    anomalous_regions.append({
                        'region': region,
                        'recorder_count': len(recorder_details),
                        'recorder_details': recorder_details
                    })
                    
                    if verbose:
                        printc(YELLOW, f"    ⚠️  Anomalous Config in {region}: {len(recorder_details)} recorder(s)")
                        for detail in recorder_details:
                            status = "enabled" if detail['recording_enabled'] else "disabled"
                            global_resources = "with global" if detail['include_global_resources'] else "local only"
                            printc(YELLOW, f"       Recorder {detail['recorder_name']}: {status} ({global_resources})")
                            
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