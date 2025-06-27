"""
GuardDuty setup module

Automates the manual steps:
1. In the Org account, enable GuardDuty in all activated regions
2. Delegate administration to Security-Adm account in all regions
3. In the Security-Adm account, enable and configure GuardDuty auto-enable in all regions
"""

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
    import boto3
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

def setup_guardduty(enabled, params, dry_run, verbose):
    """Setup AWS GuardDuty with proper organization delegation."""
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "GUARDDUTY SETUP")
        printc(LIGHT_BLUE, "="*60)
        
        if verbose:
            printc(GRAY, f"Enabled: {enabled}")
            printc(GRAY, f"Regions: {params['regions']}")
            printc(GRAY, f"Admin Account: {params['admin_account']}")
            printc(GRAY, f"Security Account: {params['security_account']}")
            printc(GRAY, f"Organization ID: {params['org_id']}")
            printc(GRAY, f"Dry Run: {dry_run}")
            printc(GRAY, f"Verbose: {verbose}")
        
        if enabled == 'No':
            # WARNING when someone tries to disable GuardDuty
            printc(RED, "\n" + "🚨" * 15)
            printc(RED, "🚨 WARNING: GuardDuty Disable Requested! 🚨")
            printc(RED, "🚨" * 15)
            printc(RED, "")
            printc(RED, "GuardDuty is a CRITICAL security service that:")
            printc(RED, "• Provides threat detection and monitoring")
            printc(RED, "• Detects malicious activity and compromises")
            printc(RED, "• Required for compliance and security frameworks")
            printc(RED, "")
            printc(RED, "⛔ DISABLING GUARDDUTY REDUCES SECURITY POSTURE!")
            printc(RED, "")
            printc(RED, "GuardDuty setup SKIPPED due to enabled=No parameter.")
            printc(RED, "🚨" * 15)
            return True
        
        # enabled == 'Yes' - proceed with GuardDuty setup/verification
        regions = params['regions']
        admin_account = params['admin_account']
        security_account = params['security_account']
        cross_account_role = params['cross_account_role']
        
        printc(YELLOW, f"Checking GuardDuty setup in {len(regions)} regions...")
        if verbose:
            printc(GRAY, f"Admin account ({admin_account}): Should enable GuardDuty and delegate to Security account")
            printc(GRAY, f"Security account ({security_account}): Should be delegated admin for organization")
        
        # Check current GuardDuty state in all regions
        guardduty_status = {}
        any_changes_needed = False
        
        for region in regions:
            if verbose:
                printc(GRAY, f"\n🔍 Checking GuardDuty in region {region}...")
            
            region_status = check_guardduty_in_region(region, admin_account, security_account, cross_account_role, verbose)
            guardduty_status[region] = region_status
            
            if not region_status['needs_changes']:
                if verbose:
                    printc(GREEN, f"  ✅ GuardDuty properly configured in {region}")
            else:
                any_changes_needed = True
                # Always show issues when changes are needed, even without verbose
                printc(YELLOW, f"  ⚠️  GuardDuty needs changes in {region}")
                # Show basic issues without verbose
                if not verbose:
                    for issue in region_status['issues'][:2]:  # Show first 2 issues
                        printc(YELLOW, f"    • {issue}")
                    if len(region_status['issues']) > 2:
                        printc(YELLOW, f"    • ... and {len(region_status['issues']) - 2} more (use --verbose for details)")
        
        # Report findings and take action
        if not any_changes_needed:
            printc(GREEN, "✅ GuardDuty is already properly configured in all regions!")
            printc(GREEN, "   No changes needed - existing setup meets stringent security standards.")
            
            # Show detailed configuration for each region ONLY when verbose
            if verbose:
                printc(LIGHT_BLUE, "\n📋 Current GuardDuty Configuration:")
                for region, status in guardduty_status.items():
                    printc(LIGHT_BLUE, f"\n🌍 Region: {region}")
                    if status['guardduty_enabled']:
                        for detail in status['guardduty_details']:
                            printc(GRAY, f"  {detail}")
                    else:
                        printc(GRAY, "  GuardDuty not enabled in this region")
            
            return True
        
        # Some changes needed
        printc(YELLOW, "⚠️  GuardDuty needs configuration in some regions:")
        
        for region, status in guardduty_status.items():
            if status['needs_changes']:
                for issue in status['issues']:
                    printc(YELLOW, f"  • {region}: {issue}")
        
        if dry_run:
            printc(YELLOW, "\n🔍 DRY RUN: Would make the following changes:")
            for region, status in guardduty_status.items():
                if status['needs_changes']:
                    for action in status['actions']:
                        printc(YELLOW, f"  • {region}: {action}")
        else:
            printc(YELLOW, "\n🔧 Making GuardDuty changes...")
            # TODO: Implement actual GuardDuty changes
            for region, status in guardduty_status.items():
                if status['needs_changes']:
                    printc(YELLOW, f"  TODO: Implement changes for {region}")
        
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_guardduty: {e}")
        return False

def check_guardduty_in_region(region, admin_account, security_account, cross_account_role, verbose=False):
    """
    Check AWS GuardDuty status in a specific region.
    
    Handles all configuration scenarios:
    1. Unconfigured service - No GuardDuty detectors found
    2. Configuration but no delegation - GuardDuty enabled but not delegated to Security account
    3. Weird configurations - Delegated to wrong account, suboptimal settings, mixed member states
    4. Valid configurations - Properly delegated with optimal settings and all members enabled
    
    Returns status dictionary with needed changes and detailed findings.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    status = {
        'region': region,
        'guardduty_enabled': False,
        'delegation_status': 'unknown',
        'member_count': 0,
        'organization_auto_enable': False,
        'needs_changes': False,
        'issues': [],
        'actions': [],
        'errors': [],
        'guardduty_details': []
    }
    
    try:
        guardduty_client = boto3.client('guardduty', region_name=region)
        
        # Check GuardDuty detectors
        try:
            detectors_response = guardduty_client.list_detectors()
            detector_ids = detectors_response.get('DetectorIds', [])
            
            if not detector_ids:
                # Case 1: Unconfigured service
                status['needs_changes'] = True
                status['issues'].append("GuardDuty is not enabled in this region")
                status['actions'].append("Enable GuardDuty and create detector")
                status['guardduty_details'].append("❌ GuardDuty not enabled - no detectors found")
                return status
            
            status['guardduty_enabled'] = True
            detector_id = detector_ids[0]  # Usually only one detector per region
            status['guardduty_details'].append(f"✅ GuardDuty Detector: {detector_id}")
            
            # Get detector details
            try:
                detector_response = guardduty_client.get_detector(DetectorId=detector_id)
                detector_status = detector_response.get('Status', 'Unknown')
                finding_publishing_frequency = detector_response.get('FindingPublishingFrequency', 'Unknown')
                
                # Case 4: Valid configuration vs Case 3: Weird configuration assessment
                if detector_status == 'ENABLED':
                    status['guardduty_details'].append(f"   ✅ Status: {detector_status}")
                else:
                    # Case 3: Weird configuration - detector exists but not enabled
                    status['guardduty_details'].append(f"   ⚠️  Status: {detector_status}")
                    status['needs_changes'] = True
                    status['issues'].append(f"Detector status is {detector_status}, should be ENABLED")
                    status['actions'].append("Enable GuardDuty detector")
                
                # Check finding frequency - FIFTEEN_MINUTES is the optimal standard
                if finding_publishing_frequency == 'FIFTEEN_MINUTES':
                    status['guardduty_details'].append(f"   ✅ Finding Frequency: {finding_publishing_frequency} (optimal)")
                elif finding_publishing_frequency == 'ONE_HOUR':
                    status['guardduty_details'].append(f"   📊 Finding Frequency: {finding_publishing_frequency} (acceptable)")
                    status['guardduty_details'].append("   💡 Consider setting to FIFTEEN_MINUTES for optimal threat detection")
                elif finding_publishing_frequency == 'SIX_HOURS':
                    status['guardduty_details'].append(f"   ⚠️  Finding Frequency: {finding_publishing_frequency} (suboptimal)")
                    status['needs_changes'] = True
                    status['issues'].append("Finding frequency is 6 hours - too slow for optimal threat detection")
                    status['actions'].append("Set finding frequency to FIFTEEN_MINUTES for optimal security")
                else:
                    status['guardduty_details'].append(f"   ⚠️  Finding Frequency: {finding_publishing_frequency}")
                    status['needs_changes'] = True
                    status['issues'].append(f"Finding frequency is {finding_publishing_frequency} - should be FIFTEEN_MINUTES")
                    status['actions'].append("Set finding frequency to FIFTEEN_MINUTES for optimal threat detection")
                    
            except ClientError as e:
                error_msg = f"Get detector details failed: {str(e)}"
                status['errors'].append(error_msg)
                status['guardduty_details'].append(f"❌ {error_msg}")
                
        except ClientError as e:
            error_msg = f"List detectors failed: {str(e)}"
            status['errors'].append(error_msg)
            if verbose:
                printc(RED, f"    ❌ {error_msg}")
                
        # Check delegated administrator first to determine access pattern
        try:
            orgs_client = boto3.client('organizations', region_name=region)
            delegated_admins = orgs_client.list_delegated_administrators(ServicePrincipal='guardduty.amazonaws.com')
            
            is_delegated_to_security = False
            for admin in delegated_admins.get('DelegatedAdministrators', []):
                if admin.get('Id') == security_account:
                    status['delegation_status'] = 'delegated'
                    is_delegated_to_security = True
                    status['guardduty_details'].append(f"✅ Delegated Admin: {admin.get('Name', admin.get('Id'))}")
                    break
            else:
                if status['guardduty_enabled']:
                    # Case 2: GuardDuty enabled but no delegation to Security account
                    status['delegation_status'] = 'not_delegated'
                    
                    # Check if delegated to a different account (weird configuration)
                    other_delegated_admins = delegated_admins.get('DelegatedAdministrators', [])
                    if other_delegated_admins:
                        other_admin_ids = [admin.get('Id') for admin in other_delegated_admins]
                        status['guardduty_details'].append(f"⚠️  GuardDuty delegated to other account(s): {', '.join(other_admin_ids)}")
                        status['guardduty_details'].append(f"⚠️  Expected delegation to Security account: {security_account}")
                        status['issues'].append(f"GuardDuty delegated to {', '.join(other_admin_ids)} instead of Security account {security_account}")
                        status['actions'].append("Remove existing delegation and delegate to Security account")
                        status['needs_changes'] = True
                    else:
                        # Case 2: Configuration but no delegation at all
                        status['needs_changes'] = True
                        status['issues'].append("GuardDuty enabled but not delegated to Security account")
                        status['actions'].append("Delegate GuardDuty administration to Security account")
                        status['guardduty_details'].append("❌ No delegation found - should delegate to Security account")
                        
        except ClientError as e:
            error_msg = f"Check delegated administrators failed: {str(e)}"
            status['errors'].append(error_msg)
            status['guardduty_details'].append(f"❌ Delegation check failed: {str(e)}")
            
        # Get organization configuration and member accounts 
        # If delegation is detected, switch to delegated admin account for complete data
        if (is_delegated_to_security and 
            cross_account_role and 
            security_account != admin_account):
            
            if verbose:
                printc(GRAY, f"    🔄 Switching to delegated admin account for complete data...")
            
            # Create cross-account client to security account
            delegated_client = get_client('guardduty', security_account, region, cross_account_role)
            
            if delegated_client:
                # Get detector ID in the delegated admin account
                try:
                    delegated_detectors = delegated_client.list_detectors()
                    delegated_detector_ids = delegated_detectors.get('DetectorIds', [])
                    
                    if delegated_detector_ids:
                        delegated_detector_id = delegated_detector_ids[0]
                        
                        # Get organization configuration from delegated admin
                        try:
                            org_config_response = delegated_client.describe_organization_configuration(
                                DetectorId=delegated_detector_id
                            )
                            
                            auto_enable = org_config_response.get('AutoEnable', False)
                            auto_enable_orgs = org_config_response.get('AutoEnableOrganizationMembers', 'Unknown')
                            datasources = org_config_response.get('DataSources', {})
                            
                            status['organization_auto_enable'] = auto_enable
                            
                            # Case 4: Valid configuration vs weird configuration assessment
                            if auto_enable and auto_enable_orgs == 'ALL':
                                status['guardduty_details'].append(f"✅ Organization Auto-Enable: {auto_enable}")
                                status['guardduty_details'].append(f"✅ Auto-Enable Org Members: {auto_enable_orgs}")
                            else:
                                # Case 3: Weird configuration - delegated but suboptimal settings
                                status['guardduty_details'].append(f"⚠️  Organization Auto-Enable: {auto_enable}")
                                status['guardduty_details'].append(f"⚠️  Auto-Enable Org Members: {auto_enable_orgs}")
                                
                                if not auto_enable:
                                    status['needs_changes'] = True
                                    status['issues'].append("Organization auto-enable is disabled")
                                    status['actions'].append("Enable organization auto-enable")
                                
                                if auto_enable_orgs != 'ALL':
                                    status['needs_changes'] = True
                                    status['issues'].append(f"Auto-enable org members is '{auto_enable_orgs}', should be 'ALL'")
                                    status['actions'].append("Set auto-enable organization members to 'ALL'")
                            
                            # Check data sources configuration  
                            if datasources:
                                s3_logs = datasources.get('S3Logs', {}).get('AutoEnable', False)
                                kubernetes = datasources.get('Kubernetes', {}).get('AutoEnable', False) 
                                malware = datasources.get('MalwareProtection', {}).get('AutoEnable', False)
                                
                                status['guardduty_details'].append(f"   📊 S3 Data Events: {s3_logs}")
                                status['guardduty_details'].append(f"   📊 Kubernetes Audit Logs: {kubernetes}")
                                status['guardduty_details'].append(f"   📊 Malware Protection: {malware}")
                                
                                # Optionally flag if important data sources are disabled
                                if not s3_logs:
                                    status['guardduty_details'].append("   ⚠️  S3 data events disabled - consider enabling for enhanced monitoring")
                                if not malware:
                                    status['guardduty_details'].append("   ⚠️  Malware protection disabled - consider enabling for enhanced security")
                                
                        except ClientError as e:
                            error_msg = f"Organization configuration check failed: {str(e)}"
                            status['errors'].append(error_msg)
                            status['guardduty_details'].append(f"❌ Org config failed: {str(e)}")
                        
                        # Get member accounts from delegated admin with pagination
                        try:
                            all_members = []
                            paginator = delegated_client.get_paginator('list_members')
                            
                            for page in paginator.paginate(DetectorId=delegated_detector_id):
                                members = page.get('Members', [])
                                all_members.extend(members)
                            
                            status['member_count'] = len(all_members)
                            status['guardduty_details'].append(f"✅ Member Accounts: {status['member_count']} found")
                            
                            # Analyze member statuses - detect weird configurations
                            if status['member_count'] > 0:
                                enabled_members = sum(1 for member in all_members if member.get('RelationshipStatus') == 'Enabled')
                                invited_members = sum(1 for member in all_members if member.get('RelationshipStatus') == 'Invited')
                                disabled_members = sum(1 for member in all_members if member.get('RelationshipStatus') == 'Disabled')
                                paused_members = sum(1 for member in all_members if member.get('RelationshipStatus') == 'Paused')
                                removed_members = sum(1 for member in all_members if member.get('RelationshipStatus') == 'Removed')
                                
                                # Case 4: Valid configuration - all members enabled
                                if enabled_members == status['member_count']:
                                    status['guardduty_details'].append(f"   ✅ All {enabled_members} member accounts are enabled")
                                else:
                                    # Case 3: Weird configurations - mixed member states
                                    if enabled_members > 0:
                                        status['guardduty_details'].append(f"   📊 Enabled Members: {enabled_members}")
                                    
                                    if invited_members > 0:
                                        status['guardduty_details'].append(f"   ⚠️  Invited Members: {invited_members}")
                                        status['needs_changes'] = True
                                        status['issues'].append(f"{invited_members} member accounts are still in 'Invited' status")
                                        status['actions'].append("Follow up on pending member invitations")
                                    
                                    if disabled_members > 0:
                                        status['guardduty_details'].append(f"   ❌ Disabled Members: {disabled_members}")
                                        status['needs_changes'] = True
                                        status['issues'].append(f"{disabled_members} member accounts are disabled")
                                        status['actions'].append("Enable disabled member accounts")
                                    
                                    if paused_members > 0:
                                        status['guardduty_details'].append(f"   ⏸️  Paused Members: {paused_members}")
                                        status['needs_changes'] = True
                                        status['issues'].append(f"{paused_members} member accounts are paused")
                                        status['actions'].append("Resume paused member accounts")
                                    
                                    if removed_members > 0:
                                        status['guardduty_details'].append(f"   🗑️  Removed Members: {removed_members}")
                                        status['issues'].append(f"{removed_members} member accounts are in 'Removed' status")
                                        status['actions'].append("Clean up removed member accounts or re-invite if needed")
                                        
                            else:
                                # Case 3: Weird configuration - delegation but no members found
                                status['guardduty_details'].append("⚠️  No member accounts found despite delegation")
                                status['needs_changes'] = True
                                status['issues'].append("Delegated admin has no member accounts - organization setup may be incomplete")
                                status['actions'].append("Investigate organization member account setup")
                                    
                        except ClientError as e:
                            error_msg = f"List members failed: {str(e)}"
                            status['errors'].append(error_msg)
                            status['guardduty_details'].append(f"❌ Member list failed: {str(e)}")
                    else:
                        status['guardduty_details'].append("⚠️  No detectors found in delegated admin account")
                        
                except ClientError as e:
                    error_msg = f"Delegated admin detector check failed: {str(e)}"
                    status['errors'].append(error_msg)
                    status['guardduty_details'].append(f"❌ Delegated admin check failed: {str(e)}")
            else:
                status['guardduty_details'].append("❌ Failed to create cross-account client to security account")
                
    except Exception as e:
        error_msg = f"General error checking region {region}: {str(e)}"
        status['errors'].append(error_msg)
        status['guardduty_details'].append(f"❌ General error: {str(e)}")
    
    return status