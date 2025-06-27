"""
Amazon Inspector setup module

Automates the manual steps:
1. In the Org account, delegate administration of Amazon Inspector to 
   the Security-Adm account in all your chosen regions.
2. In the Security-Adm account, configure Inspector in each chosen 
   region. Note that you must activate/invite the individual existing member 
   accounts in each region as well as enable automatic activation of new 
   accounts.

COST-CONSCIOUS APPROACH:
- Minimal scanning setup (delegation + member management only)
- No automatic scanning enablement to avoid unexpected costs
- Client controls specific scan types (ECR, EC2, Lambda) based on needs
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
    This matches the pattern used in other Foundation components.
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

def setup_inspector(enabled, params, dry_run, verbose):
    """Setup Amazon Inspector delegation and configuration with cost-conscious minimal approach."""
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "INSPECTOR SETUP")
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
            printc(GRAY, "Inspector is disabled - checking for active resources to deactivate")
            
            # Check current Inspector state and suggest deactivation if active
            regions = params['regions']
            admin_account = params['admin_account']
            security_account = params['security_account']
            cross_account_role = params['cross_account_role']
            
            inspector_is_active = False
            inspector_delegation_exists = False
            active_scanning_regions = []
            total_scan_types_enabled = 0
            total_members = 0
            
            # Check delegation first
            try:
                import boto3
                from botocore.exceptions import ClientError
                orgs_client = boto3.client('organizations', region_name=regions[0])
                paginator = orgs_client.get_paginator('list_delegated_administrators')
                inspector_admins = []
                for page in paginator.paginate(ServicePrincipal='inspector2.amazonaws.com'):
                    inspector_admins.extend(page.get('DelegatedAdministrators', []))
                
                if any(admin.get('Id') == security_account for admin in inspector_admins):
                    inspector_delegation_exists = True
                    if verbose:
                        printc(GRAY, f"   ✅ Inspector delegated to Security account ({security_account})")
            except Exception:
                pass  # Ignore delegation check errors
            
            # Check for active Inspector scanning in ALL regions (regardless of delegation)
            # Inspector scanning can exist even without delegation, and we want to detect unexpected costs
            try:
                import boto3
                ec2_client = boto3.client('ec2', region_name=regions[0] if regions else 'us-east-1')
                regions_response = ec2_client.describe_regions()
                all_regions = [region['RegionName'] for region in regions_response['Regions']]
                
                if verbose:
                    printc(GRAY, f"   🔍 Checking all {len(all_regions)} AWS regions for spurious Inspector activation...")
            except Exception:
                # Fallback to configured regions if we can't get all regions
                all_regions = regions
                if verbose:
                    printc(GRAY, f"   🔍 Checking configured regions for Inspector activation...")
            
            for region in all_regions:
                try:
                    inspector_client = boto3.client('inspector2', region_name=region)
                    
                    # Check scanning status
                    scanning_status = inspector_client.batch_get_account_status()
                    
                    region_scan_types = 0
                    account_details = []
                    for account in scanning_status.get('accounts', []):
                        account_id = account.get('accountId')
                        resource_state = account.get('resourceState', {})
                        enabled_scan_types = []
                        
                        for resource_type, state_info in resource_state.items():
                            if state_info.get('status') == 'ENABLED':
                                region_scan_types += 1
                                total_scan_types_enabled += 1
                                enabled_scan_types.append(resource_type)
                        
                        if enabled_scan_types:
                            account_details.append({
                                'account_id': account_id,
                                'enabled_scan_types': enabled_scan_types
                            })
                    
                    if region_scan_types > 0:
                        inspector_is_active = True
                        is_configured_region = region in regions
                        active_scanning_regions.append({
                            'region': region, 
                            'scan_types': region_scan_types,
                            'is_configured': is_configured_region,
                            'account_details': account_details
                        })
                        if verbose:
                            status = "configured" if is_configured_region else "UNEXPECTED"
                            printc(GRAY, f"   🔍 Active scanning in {region}: {region_scan_types} types ({status})")
                            for account in account_details:
                                account_id = account['account_id']
                                enabled_types = ', '.join(account['enabled_scan_types'])
                                printc(GRAY, f"       Account {account_id}: {enabled_types}")
                    
                    # Count members only if delegation exists (requires delegation to see members)
                    if inspector_delegation_exists:
                        try:
                            members_paginator = inspector_client.get_paginator('list_members')
                            for page in members_paginator.paginate():
                                total_members += len(page.get('members', []))
                        except Exception:
                            pass
                except Exception:
                    pass  # Ignore region check errors
            
            # Show deactivation recommendations based on current state
            if inspector_is_active:
                # Separate configured vs unexpected regions
                configured_regions = [info for info in active_scanning_regions if info['is_configured']]
                unexpected_regions = [info for info in active_scanning_regions if not info['is_configured']]
                
                printc(YELLOW, f"\n⚠️  INSPECTOR DEACTIVATION NEEDED:")
                printc(YELLOW, f"Amazon Inspector is currently ACTIVE but configured as disabled")
                printc(YELLOW, f"")
                printc(YELLOW, f"Current active Inspector resources:")
                
                if configured_regions:
                    printc(YELLOW, f"  • {len(configured_regions)} configured region(s) with active scanning:")
                    for region_info in configured_regions:
                        region = region_info['region']
                        scan_types = region_info['scan_types']
                        accounts = region_info.get('account_details', [])
                        printc(YELLOW, f"    📍 {region} ({scan_types} scan types):")
                        for account in accounts:
                            account_id = account['account_id']
                            enabled_types = ', '.join(account['enabled_scan_types'])
                            printc(YELLOW, f"      🔹 Account {account_id}: {enabled_types}")
                
                if unexpected_regions:
                    printc(YELLOW, f"  • {len(unexpected_regions)} UNEXPECTED region(s) with active scanning:")
                    printc(YELLOW, f"    ⚠️  These regions are outside your configuration and generating costs!")
                    for region_info in unexpected_regions:
                        region = region_info['region']
                        scan_types = region_info['scan_types']
                        accounts = region_info.get('account_details', [])
                        printc(YELLOW, f"    📍 {region} ({scan_types} scan types):")
                        for account in accounts:
                            account_id = account['account_id']
                            enabled_types = ', '.join(account['enabled_scan_types'])
                            printc(YELLOW, f"      🔹 Account {account_id}: {enabled_types}")
                
                printc(YELLOW, f"  • {total_scan_types_enabled} scan type(s) enabled (ECR/EC2/Lambda)")
                if total_members > 0:
                    printc(YELLOW, f"  • {total_members} member account(s) in Inspector")
                if inspector_delegation_exists:
                    printc(YELLOW, f"  • Delegated to Security account ({security_account})")
                else:
                    printc(YELLOW, f"  • No delegation found (scanning active without delegation)")
                printc(YELLOW, f"")
                
                if dry_run:
                    printc(YELLOW, f"🔍 DRY RUN: Would deactivate Inspector:")
                    for region_info in active_scanning_regions:
                        region = region_info['region']
                        scan_types = region_info['scan_types']
                        is_configured = region_info['is_configured']
                        accounts = region_info.get('account_details', [])
                        status = "configured" if is_configured else "UNEXPECTED"
                        printc(YELLOW, f"  📍 {region} ({scan_types} scan types, {status}):")
                        for account in accounts:
                            account_id = account['account_id']
                            enabled_types = ', '.join(account['enabled_scan_types'])
                            printc(YELLOW, f"    🔹 Disable {enabled_types} in account {account_id}")
                        printc(YELLOW, f"    • Remove member account invitations in {region}")
                        printc(YELLOW, f"    • Disable automatic member enrollment in {region}")
                    if inspector_delegation_exists:
                        printc(YELLOW, f"  • Remove Inspector delegation from Security account ({security_account})")
                    printc(YELLOW, f"  • This will stop all vulnerability scanning and cost generation")
                else:
                    printc(YELLOW, f"📋 RECOMMENDED DEACTIVATION STEPS:")
                    printc(YELLOW, f"  1. Disable vulnerability scanning (ECR, EC2, Lambda) in all regions")
                    if inspector_delegation_exists:
                        printc(YELLOW, f"  2. Remove member accounts from Inspector organization")
                        printc(YELLOW, f"  3. Disable automatic member enrollment for new accounts")
                        printc(YELLOW, f"  4. Remove Inspector delegation from Security account")
                        printc(YELLOW, f"  5. This will fully stop Inspector vulnerability scanning and costs")
                    else:
                        printc(YELLOW, f"  2. Disable Inspector scanning directly in each region (no delegation to remove)")
                        printc(YELLOW, f"  3. This will stop vulnerability scanning and cost generation")
                    printc(YELLOW, f"  💰 Note: This will eliminate Inspector scanning costs but remove vulnerability detection")
                    
            elif inspector_delegation_exists:
                printc(YELLOW, f"\n💡 DELEGATION CLEANUP SUGGESTION:")
                printc(YELLOW, f"Inspector is delegated to Security account ({security_account}) but not actively scanning")
                printc(YELLOW, f"Since Inspector is disabled, consider removing the delegation to clean up")
                printc(YELLOW, f"This will remove Inspector administrative permissions from the Security account")
            else:
                if verbose:
                    printc(GRAY, f"   ✅ Inspector is not delegated or active - no cleanup needed")
            
            return True
        
        # enabled == 'Yes' - proceed with Inspector setup/verification
        regions = params['regions']
        admin_account = params['admin_account']
        security_account = params['security_account']
        cross_account_role = params['cross_account_role']
        
        printc(YELLOW, f"Checking Amazon Inspector setup in {len(regions)} regions...")
        if verbose:
            printc(GRAY, f"Admin account ({admin_account}): Should delegate to Security account")
            printc(GRAY, f"Security account ({security_account}): Should be delegated admin for organization")
            printc(GRAY, f"Cost-conscious approach: Minimal scanning setup only")
        
        # Step 1: Check for anomalous Inspector scanning in unexpected regions
        if verbose:
            printc(GRAY, f"\n🔍 Checking for Inspector scanning in unexpected regions...")
        
        anomalous_regions = check_anomalous_inspector_regions(regions, admin_account, security_account, verbose)
        
        if anomalous_regions:
            printc(YELLOW, f"\n⚠️  ANOMALOUS INSPECTOR SCANNING DETECTED:")
            printc(YELLOW, f"Inspector scanning is active in regions outside your configuration:")
            for anomaly in anomalous_regions:
                region = anomaly['region']
                scan_types = anomaly['scan_types_enabled']
                printc(YELLOW, f"  • {region}: {scan_types} scan type(s) enabled (not in your regions list)")
            printc(YELLOW, f"")
            printc(YELLOW, f"📋 ANOMALY RECOMMENDATIONS:")
            printc(YELLOW, f"  • Review: Determine if this scanning is intentional or configuration drift")
            printc(YELLOW, f"  • Recommended: Disable Inspector scanning in these regions to control costs")
            printc(YELLOW, f"  • Note: Adding regions to OpenSecOps requires full system redeployment")
            printc(YELLOW, f"  💰 Important: Unexpected scanning generates ongoing costs that should be stopped")
        
        # Step 2: Check Inspector delegation status per region
        inspector_status = {}
        any_changes_needed = False
        
        for region in regions:
            if verbose:
                printc(GRAY, f"\n🔍 Checking Inspector in region {region}...")
            
            region_status = check_inspector_in_region(region, admin_account, security_account, cross_account_role, verbose)
            inspector_status[region] = region_status
            
            if not region_status['needs_changes']:
                if verbose:
                    printc(GREEN, f"  ✅ Inspector properly configured in {region}")
            else:
                any_changes_needed = True
                # Always show issues when changes are needed, even without verbose
                printc(YELLOW, f"  ⚠️  Inspector needs changes in {region}")
                # Show basic issues without verbose
                if not verbose:
                    for issue in region_status['issues'][:2]:  # Show first 2 issues
                        printc(YELLOW, f"    • {issue}")
                    if len(region_status['issues']) > 2:
                        printc(YELLOW, f"    • ... and {len(region_status['issues']) - 2} more (use --verbose for details)")
        
        # Report findings and take action
        if not any_changes_needed:
            printc(GREEN, "✅ Amazon Inspector is already properly configured in all regions!")
            printc(GREEN, "   Vulnerability scanning delegation is available for organization-wide security.")
            
            # Show summary information about Inspector configuration
            total_members = sum(status.get('member_count', 0) for status in inspector_status.values())
            total_scan_types = sum(status.get('scan_types_enabled', 0) for status in inspector_status.values())
            
            printc(LIGHT_BLUE, f"\n📊 Inspector Configuration Summary:")
            printc(LIGHT_BLUE, f"  • Organization accounts covered: {total_members}")
            printc(LIGHT_BLUE, f"  • Scan types enabled across regions: {total_scan_types}")
            printc(LIGHT_BLUE, f"  • Regions configured: {len([r for r, s in inspector_status.items() if s['inspector_enabled']])}")
            
            # Check auto-activation status
            auto_activation_info = check_inspector_auto_activation(regions, admin_account, security_account, cross_account_role, verbose)
            if auto_activation_info:
                printc(LIGHT_BLUE, f"  • Auto-activation for new accounts: {auto_activation_info['status']}")
                if auto_activation_info['enabled_types']:
                    enabled_types = ', '.join(auto_activation_info['enabled_types'])
                    printc(LIGHT_BLUE, f"  • Auto-enabled scan types: {enabled_types}")
            
            # Show detailed configuration for each region ONLY when verbose
            if verbose:
                printc(LIGHT_BLUE, "\n📋 Current Amazon Inspector Configuration:")
                for region, status in inspector_status.items():
                    printc(LIGHT_BLUE, f"\n🌍 Region: {region}")
                    if status['inspector_enabled']:
                        for detail in status['inspector_details']:
                            printc(GRAY, f"  {detail}")
                    else:
                        printc(GRAY, "  Inspector not enabled in this region")
            
            return True
        
        # Show specific recommendations based on what's missing
        printc(YELLOW, "⚠️  Amazon Inspector needs configuration:")
        
        # Show missing delegation and configuration recommendations per region
        missing_regions = []
        for region, status in inspector_status.items():
            if status['needs_changes']:
                missing_regions.append(region)
        
        if missing_regions:
            printc(YELLOW, f"\n📋 INSPECTOR CONFIGURATION NEEDED:")
            for region in missing_regions:
                status = inspector_status[region]
                
                printc(YELLOW, f"\n  🌍 Region: {region}")
                
                if status['delegation_status'] == 'not_delegated':
                    printc(YELLOW, f"    • Missing: Inspector delegation to Security account")
                    printc(YELLOW, f"      Recommend: Delegate Inspector administration to {security_account}")
                
                if status['delegation_status'] == 'delegated' and status['member_count'] == 0:
                    printc(YELLOW, f"    • Missing: Organization member accounts")
                    printc(YELLOW, f"      Recommend: Add existing organization accounts to Inspector")
                    printc(YELLOW, f"      Recommend: Enable auto-enrollment for new accounts")
                
                if status['delegation_status'] == 'delegated':
                    printc(YELLOW, f"    • Missing: Minimal Inspector configuration")
                    printc(YELLOW, f"      Recommend: Configure Inspector for organization member management")
                    printc(YELLOW, f"      Recommend: Enable automatic member invitation for new accounts")
                    printc(YELLOW, f"      Recommend: Configure auto-activation for new organization accounts")
                    printc(YELLOW, f"      Note: Specific scan types (ECR/EC2/Lambda) left for client to enable")
                    printc(YELLOW, f"      Note: Cost-conscious setup - no automatic scanning enablement")
        
        # Show what actions would be taken
        if dry_run:
            printc(YELLOW, "\n🔍 DRY RUN: Recommended actions to fix Inspector setup:")
            
            action_count = 1
            for region in missing_regions:
                status = inspector_status[region]
                
                if status['delegation_status'] == 'not_delegated':
                    printc(YELLOW, f"  {action_count}. Delegate Inspector administration to Security account {security_account} in {region}")
                    action_count += 1
                
                if status['delegation_status'] == 'delegated':
                    printc(YELLOW, f"  {action_count}. Configure Inspector organization settings in {region}")
                    action_count += 1
                    printc(YELLOW, f"  {action_count}. Add all organization accounts to Inspector in {region}")
                    action_count += 1
                    printc(YELLOW, f"  {action_count}. Enable automatic member invitation for new accounts in {region}")
                    action_count += 1
                    printc(YELLOW, f"  {action_count}. Configure auto-activation for new organization accounts in {region}")
                    action_count += 1
                    printc(YELLOW, f"  Note: Scan types (ECR/EC2/Lambda) left disabled for cost control")
        else:
            printc(YELLOW, "\n🔧 Making Inspector changes...")
            # TODO: Implement actual Inspector changes
            for region in missing_regions:
                printc(YELLOW, f"  TODO: Configure Inspector in {region}")
        
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_inspector: {e}")
        return False

def check_inspector_in_region(region, admin_account, security_account, cross_account_role, verbose=False):
    """
    Check AWS Inspector status in a specific region.
    
    Handles all configuration scenarios:
    1. Not delegated - No Inspector delegation found
    2. Delegated but no members - Delegation exists but no member accounts
    3. Fully configured - Delegation + members + minimal setup
    
    Returns status dictionary with needed changes and detailed findings.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    status = {
        'region': region,
        'inspector_enabled': False,
        'delegation_status': 'unknown',
        'member_count': 0,
        'scan_types_enabled': 0,
        'needs_changes': False,
        'issues': [],
        'actions': [],
        'errors': [],
        'inspector_details': []
    }
    
    try:
        # Check delegation status first
        try:
            orgs_client = boto3.client('organizations', region_name=region)
            all_delegated_admins = []
            paginator = orgs_client.get_paginator('list_delegated_administrators')
            for page in paginator.paginate(ServicePrincipal='inspector2.amazonaws.com'):
                all_delegated_admins.extend(page.get('DelegatedAdministrators', []))
            
            is_delegated_to_security = False
            for admin in all_delegated_admins:
                if admin.get('Id') == security_account:
                    status['delegation_status'] = 'delegated'
                    is_delegated_to_security = True
                    status['inspector_details'].append(f"✅ Delegated Admin: {admin.get('Name', admin.get('Id'))}")
                    break
            else:
                if all_delegated_admins:
                    # Delegated to wrong account
                    status['delegation_status'] = 'delegated_wrong'
                    other_admin_ids = [admin.get('Id') for admin in all_delegated_admins]
                    status['inspector_details'].append(f"⚠️  Inspector delegated to other account(s): {', '.join(other_admin_ids)}")
                    status['issues'].append(f"Inspector delegated to {', '.join(other_admin_ids)} instead of Security account {security_account}")
                    status['actions'].append("Remove existing delegation and delegate to Security account")
                    status['needs_changes'] = True
                else:
                    # Not delegated
                    status['delegation_status'] = 'not_delegated'
                    status['needs_changes'] = True
                    status['issues'].append("Inspector is not delegated to Security account")
                    status['actions'].append("Delegate Inspector administration to Security account")
                    status['inspector_details'].append("❌ No delegation found - should delegate to Security account")
                    
        except ClientError as e:
            error_msg = f"Check delegated administrators failed: {str(e)}"
            status['errors'].append(error_msg)
            status['inspector_details'].append(f"❌ Delegation check failed: {str(e)}")
        
        # Check Inspector configuration from admin account perspective
        if is_delegated_to_security:
            try:
                inspector_client = boto3.client('inspector2', region_name=region)
                
                # Check scanning status
                scanning_response = inspector_client.batch_get_account_status()
                
                scan_types_enabled = 0
                for account in scanning_response.get('accounts', []):
                    resource_state = account.get('resourceState', {})
                    for resource_type, state_info in resource_state.items():
                        if state_info.get('status') == 'ENABLED':
                            scan_types_enabled += 1
                
                status['scan_types_enabled'] = scan_types_enabled
                status['inspector_enabled'] = True  # Delegation exists, consider enabled
                status['inspector_details'].append(f"✅ Inspector Configuration: {scan_types_enabled} scan types enabled")
                
                # Check member accounts
                try:
                    members_paginator = inspector_client.get_paginator('list_members')
                    all_members = []
                    for page in members_paginator.paginate():
                        all_members.extend(page.get('members', []))
                    
                    status['member_count'] = len(all_members)
                    status['inspector_details'].append(f"✅ Inspector Members: {len(all_members)} accounts")
                    
                    if len(all_members) == 0:
                        status['needs_changes'] = True
                        status['issues'].append("Inspector has no member accounts configured")
                        status['actions'].append("Add organization member accounts to Inspector")
                        status['actions'].append("Enable auto-enrollment for new accounts")
                    else:
                        # Show member status breakdown
                        status_counts = {}
                        for member in all_members:
                            member_status = member.get('relationshipStatus', 'UNKNOWN')
                            status_counts[member_status] = status_counts.get(member_status, 0) + 1
                        
                        for member_status, count in status_counts.items():
                            status['inspector_details'].append(f"      {member_status}: {count} members")
                            
                except ClientError as e:
                    error_msg = f"List members failed: {str(e)}"
                    status['errors'].append(error_msg)
                    status['inspector_details'].append(f"❌ Member check failed: {str(e)}")
                        
            except ClientError as e:
                error_msg = f"Inspector configuration check failed: {str(e)}"
                status['errors'].append(error_msg)
                status['inspector_details'].append(f"❌ Configuration check failed: {str(e)}")
        
    except Exception as e:
        error_msg = f"General error checking region {region}: {str(e)}"
        status['errors'].append(error_msg)
        status['inspector_details'].append(f"❌ General error: {str(e)}")
    
    return status

def check_anomalous_inspector_regions(expected_regions, admin_account, security_account, verbose=False):
    """
    Check for Inspector scanning active in regions outside the expected list.
    
    This detects configuration drift where Inspector scanning was enabled
    in regions not included in the current setup, which could generate unexpected costs.
    
    Returns list of anomalous regions with scanning details.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    anomalous_regions = []
    
    try:
        # Get all AWS regions to check for anomalous scanning
        ec2_client = boto3.client('ec2', region_name=expected_regions[0] if expected_regions else 'us-east-1')
        regions_response = ec2_client.describe_regions()
        all_regions = [region['RegionName'] for region in regions_response['Regions']]
        
        # Check regions that are NOT in our expected list
        unexpected_regions = [region for region in all_regions if region not in expected_regions]
        
        if verbose:
            printc(GRAY, f"    Checking {len(unexpected_regions)} regions outside configuration...")
        
        for region in unexpected_regions:
            try:
                inspector_client = boto3.client('inspector2', region_name=region)
                
                # Check if there's any scanning activity in this region
                scanning_status = inspector_client.batch_get_account_status()
                
                scan_types_enabled = 0
                scan_details = []
                
                for account in scanning_status.get('accounts', []):
                    account_id = account.get('accountId')
                    resource_state = account.get('resourceState', {})
                    
                    for resource_type, state_info in resource_state.items():
                        if state_info.get('status') == 'ENABLED':
                            scan_types_enabled += 1
                            scan_details.append({
                                'account_id': account_id,
                                'resource_type': resource_type,
                                'status': state_info.get('status')
                            })
                
                if scan_types_enabled > 0:
                    anomalous_regions.append({
                        'region': region,
                        'scan_types_enabled': scan_types_enabled,
                        'scan_details': scan_details
                    })
                    
                    if verbose:
                        printc(YELLOW, f"    ⚠️  Anomalous scanning in {region}: {scan_types_enabled} types enabled")
                        for detail in scan_details:
                            printc(YELLOW, f"       Account {detail['account_id']}: {detail['resource_type']} = {detail['status']}")
                            
            except ClientError as e:
                if verbose:
                    printc(GRAY, f"    (Skipping {region}: {str(e)})")
                continue
            except Exception as e:
                if verbose:
                    printc(GRAY, f"    (Error checking {region}: {str(e)})")
                continue
        
        return anomalous_regions
        
    except Exception as e:
        if verbose:
            printc(GRAY, f"    ⚠️  Anomaly check failed: {str(e)}")
        return []

def check_inspector_auto_activation(regions, admin_account, security_account, cross_account_role, verbose=False):
    """
    Check Inspector auto-activation configuration across regions.
    
    Auto-activation automatically enables Inspector scanning for new accounts
    that join the organization, ensuring consistent vulnerability coverage.
    
    Returns dictionary with auto-activation status and enabled scan types.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    auto_activation_info = {
        'status': 'unknown',
        'enabled_types': [],
        'regions_checked': 0,
        'regions_with_auto_activation': 0
    }
    
    try:
        main_region = regions[0] if regions else 'us-east-1'
        
        # Check auto-activation from the delegated admin account if possible
        inspector_client = None
        if security_account != admin_account and cross_account_role:
            inspector_client = get_client('inspector2', security_account, main_region, cross_account_role)
        
        if not inspector_client:
            inspector_client = boto3.client('inspector2', region_name=main_region)
        
        if inspector_client:
            try:
                # Get auto-enable configuration
                auto_enable_response = inspector_client.batch_get_auto_enable()
                
                auto_enable_accounts = auto_enable_response.get('autoEnable', [])
                if auto_enable_accounts:
                    # Check what scan types are auto-enabled
                    enabled_types = set()
                    for account_config in auto_enable_accounts:
                        resource_types = account_config.get('resourceTypes', [])
                        enabled_types.update(resource_types)
                    
                    if enabled_types:
                        auto_activation_info['status'] = 'enabled'
                        auto_activation_info['enabled_types'] = list(enabled_types)
                    else:
                        auto_activation_info['status'] = 'disabled'
                else:
                    auto_activation_info['status'] = 'disabled'
                
                if verbose:
                    printc(GRAY, f"    Auto-activation status: {auto_activation_info['status']}")
                    if auto_activation_info['enabled_types']:
                        printc(GRAY, f"    Auto-enabled types: {', '.join(auto_activation_info['enabled_types'])}")
                        
            except ClientError as e:
                if verbose:
                    printc(GRAY, f"    ⚠️  Auto-activation check failed: {str(e)}")
                auto_activation_info['status'] = 'check_failed'
        
        return auto_activation_info
        
    except Exception as e:
        if verbose:
            printc(GRAY, f"    ⚠️  Auto-activation check error: {str(e)}")
        return auto_activation_info