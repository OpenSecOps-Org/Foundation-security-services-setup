"""
Amazon Detective setup module

Automates the manual steps:
1. In Org, delegate Amazon Detective in all your regions to Security-Adm 
   (the GUI will suggest this account automatically).
2. In Security-Adm, configure Detective in all your selected regions.
"""

from .utils import printc, get_client, YELLOW, LIGHT_BLUE, GREEN, RED, GRAY, END, BOLD

def setup_detective(enabled, params, dry_run, verbose):
    """Setup Amazon Detective delegation and configuration with comprehensive discovery."""
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "DETECTIVE SETUP")
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
            printc(GRAY, "Detective is disabled - checking for active resources to deactivate")
            
            # Check current Detective state and suggest deactivation if active
            regions = params['regions']
            admin_account = params['admin_account']
            security_account = params['security_account']
            cross_account_role = params['cross_account_role']
            
            detective_is_active = False
            detective_delegation_exists = False
            active_graphs = []
            total_members = 0
            
            # Check delegation first
            try:
                import boto3
                from botocore.exceptions import ClientError
                orgs_client = boto3.client('organizations', region_name=regions[0])
                paginator = orgs_client.get_paginator('list_delegated_administrators')
                detective_admins = []
                for page in paginator.paginate(ServicePrincipal='detective.amazonaws.com'):
                    detective_admins.extend(page.get('DelegatedAdministrators', []))
                
                if any(admin.get('Id') == security_account for admin in detective_admins):
                    detective_delegation_exists = True
                    if verbose:
                        printc(GRAY, f"   ✅ Detective delegated to Security account ({security_account})")
            except Exception:
                pass  # Ignore delegation check errors
            
            # Check for active Detective graphs in each region
            if detective_delegation_exists:
                for region in regions:
                    try:
                        detective_client = boto3.client('detective', region_name=region)
                        response = detective_client.list_graphs()
                        graphs = response.get('GraphList', [])
                        
                        if graphs:
                            detective_is_active = True
                            active_graphs.extend(graphs)
                            if verbose:
                                printc(GRAY, f"   📊 Active graphs in {region}: {len(graphs)}")
                            
                            # Count members in graphs
                            for graph in graphs:
                                try:
                                    members_paginator = detective_client.get_paginator('list_members')
                                    for page in members_paginator.paginate(GraphArn=graph.get('Arn')):
                                        total_members += len(page.get('MemberDetails', []))
                                except Exception:
                                    pass
                    except Exception:
                        pass  # Ignore region check errors
            
            # Show deactivation recommendations based on current state
            if detective_is_active:
                printc(YELLOW, f"\n⚠️  DETECTIVE DEACTIVATION NEEDED:")
                printc(YELLOW, f"Amazon Detective is currently ACTIVE but configured as disabled")
                printc(YELLOW, f"")
                printc(YELLOW, f"Current active Detective resources:")
                printc(YELLOW, f"  • {len(active_graphs)} investigation graph(s) across {len(regions)} regions")
                if total_members > 0:
                    printc(YELLOW, f"  • {total_members} member account(s) in Detective")
                printc(YELLOW, f"  • Delegated to Security account ({security_account})")
                printc(YELLOW, f"")
                
                if dry_run:
                    printc(YELLOW, f"🔍 DRY RUN: Would deactivate Detective:")
                    for region in regions:
                        printc(YELLOW, f"  • Delete Detective behavior graph in {region}")
                        printc(YELLOW, f"  • Remove member account invitations in {region}")
                        printc(YELLOW, f"  • Disable automatic member enrollment in {region}")
                    printc(YELLOW, f"  • Remove Detective delegation from Security account ({security_account})")
                    printc(YELLOW, f"  • This will stop all security investigation data collection")
                else:
                    printc(YELLOW, f"📋 RECOMMENDED DEACTIVATION STEPS:")
                    printc(YELLOW, f"  1. Remove member accounts from Detective behavior graphs")
                    printc(YELLOW, f"  2. Disable automatic member enrollment for new accounts")
                    printc(YELLOW, f"  3. Delete Detective behavior graphs in all regions")
                    printc(YELLOW, f"  4. Remove Detective delegation from Security account")
                    printc(YELLOW, f"  5. This will fully stop Detective security investigation capabilities")
                    printc(YELLOW, f"  ⚠️  Note: All investigation data and findings history will be lost")
                    
            elif detective_delegation_exists:
                printc(YELLOW, f"\n💡 DELEGATION CLEANUP SUGGESTION:")
                printc(YELLOW, f"Detective is delegated to Security account ({security_account}) but not active")
                printc(YELLOW, f"Since Detective is disabled, consider removing the delegation to clean up")
                printc(YELLOW, f"This will remove Detective administrative permissions from the Security account")
            else:
                # Check for spurious Detective activations in ALL regions (since service is disabled)
                if verbose:
                    printc(GRAY, f"   🔍 Checking all AWS regions for spurious Detective activation...")
                
                # Pass empty list as expected_regions so ALL regions are checked
                anomalous_regions = check_anomalous_detective_regions([], admin_account, security_account, verbose)
                
                if anomalous_regions:
                    printc(YELLOW, f"\n⚠️  SPURIOUS DETECTIVE ACTIVATION DETECTED:")
                    printc(YELLOW, f"Detective graphs found in unexpected regions:")
                    total_graphs = sum(anomaly['graph_count'] for anomaly in anomalous_regions)
                    printc(YELLOW, f"")
                    printc(YELLOW, f"Current spurious Detective resources:")
                    printc(YELLOW, f"  • {total_graphs} investigation graph(s) across {len(anomalous_regions)} unexpected region(s)")
                    for anomaly in anomalous_regions:
                        region = anomaly['region']
                        graph_count = anomaly['graph_count']
                        printc(YELLOW, f"    📍 {region}: {graph_count} graph(s) active")
                        for graph_detail in anomaly['graph_details']:
                            member_count = graph_detail['member_count']
                            printc(YELLOW, f"      📊 Graph: {member_count} member(s)")
                    printc(YELLOW, f"")
                    printc(YELLOW, f"📋 SPURIOUS ACTIVATION RECOMMENDATIONS:")
                    printc(YELLOW, f"  • Review: These graphs may be configuration drift or forgotten resources")
                    printc(YELLOW, f"  • Recommended: Disable Detective graphs in these regions to control costs")
                    printc(YELLOW, f"  • Note: Detective generates charges based on data ingestion volume per region")
                else:
                    if verbose:
                        printc(GRAY, f"   ✅ Detective is not delegated or active - no cleanup needed")
            
            return True
        
        # enabled == 'Yes' - proceed with Detective setup/verification
        regions = params['regions']
        admin_account = params['admin_account']
        security_account = params['security_account']
        cross_account_role = params['cross_account_role']
        
        printc(YELLOW, f"Checking Amazon Detective setup in {len(regions)} regions...")
        if verbose:
            printc(GRAY, f"Admin account ({admin_account}): Should delegate to Security account")
            printc(GRAY, f"Security account ({security_account}): Should be delegated admin for organization")
            printc(GRAY, f"Detective requires GuardDuty to be properly configured first")
        
        # Step 1: Check GuardDuty dependency (Detective requires GuardDuty)
        if verbose:
            printc(GRAY, f"\n🔍 Checking GuardDuty prerequisite...")
        
        guardduty_status = check_guardduty_prerequisite(admin_account, security_account, cross_account_role, regions, verbose)
        
        if guardduty_status != 'ready':
            printc(YELLOW, f"\n⚠️  PREREQUISITE NOTICE: GuardDuty Dependency")
            printc(YELLOW, f"Amazon Detective works best when GuardDuty is properly configured.")
            printc(YELLOW, f"GuardDuty provides the security findings that Detective analyzes for investigation.")
            printc(YELLOW, f"")
            printc(YELLOW, f"Current GuardDuty status: {guardduty_status}")
            printc(YELLOW, f"")
            printc(GRAY, f"📋 NOTE: Proceeding with Detective configuration analysis...")
            printc(GRAY, f"  • Detective delegation and setup can be configured independently")
            printc(GRAY, f"  • GuardDuty should be configured for full Detective functionality")
            if verbose:
                printc(GRAY, f"  • Investigation capabilities will be limited until GuardDuty is properly configured")
        
        # Step 2: Check Detective delegation status per region
        detective_status = {}
        any_changes_needed = False
        
        for region in regions:
            if verbose:
                printc(GRAY, f"\n🔍 Checking Detective in region {region}...")
            
            region_status = check_detective_in_region(region, admin_account, security_account, cross_account_role, verbose)
            detective_status[region] = region_status
            
            if not region_status['needs_changes']:
                if verbose:
                    printc(GREEN, f"  ✅ Detective properly configured in {region}")
            else:
                any_changes_needed = True
                # Always show issues when changes are needed, even without verbose
                printc(YELLOW, f"  ⚠️  Detective needs changes in {region}")
                # Show basic issues without verbose
                if not verbose:
                    for issue in region_status['issues'][:2]:  # Show first 2 issues
                        printc(YELLOW, f"    • {issue}")
                    if len(region_status['issues']) > 2:
                        printc(YELLOW, f"    • ... and {len(region_status['issues']) - 2} more (use --verbose for details)")
        
        # Step 2: Check for anomalous Detective graphs in unexpected regions
        if verbose:
            printc(GRAY, f"\n🔍 Checking for Detective graphs in unexpected regions...")
        
        anomalous_regions = check_anomalous_detective_regions(regions, admin_account, security_account, verbose)
        
        if anomalous_regions:
            any_changes_needed = True  # Anomalous regions require attention
            printc(YELLOW, f"\n⚠️  ANOMALOUS DETECTIVE GRAPHS DETECTED:")
            printc(YELLOW, f"Detective investigation graphs are active in regions outside your configuration:")
            for anomaly in anomalous_regions:
                region = anomaly['region']
                graph_count = anomaly['graph_count']
                printc(YELLOW, f"  • {region}: {graph_count} graph(s) active (not in your regions list)")
            printc(YELLOW, f"")
            printc(YELLOW, f"📋 ANOMALY RECOMMENDATIONS:")
            printc(YELLOW, f"  • Review: Determine if these graphs are intentional or configuration drift")
            printc(YELLOW, f"  • Recommended: Disable Detective graphs in these regions to control costs")
            printc(YELLOW, f"  • Note: Adding regions to OpenSecOps requires full system redeployment")
            printc(YELLOW, f"  💰 Cost Impact: Detective generates charges based on data ingestion volume per region")
        
        # Report findings and take action
        if not any_changes_needed:
            printc(GREEN, "✅ Amazon Detective is already properly configured in all regions!")
            printc(GREEN, "   Investigation capabilities are available for GuardDuty findings analysis.")
            
            # Show detailed configuration for each region ONLY when verbose
            if verbose:
                printc(LIGHT_BLUE, "\n📋 Current Amazon Detective Configuration:")
                for region, status in detective_status.items():
                    printc(LIGHT_BLUE, f"\n🌍 Region: {region}")
                    if status['detective_enabled']:
                        for detail in status['detective_details']:
                            printc(GRAY, f"  {detail}")
                    else:
                        printc(GRAY, "  Detective not enabled in this region")
            
            return True
        
        # Show specific recommendations based on what's missing
        printc(YELLOW, "⚠️  Amazon Detective needs configuration:")
        
        # Show missing delegation and configuration recommendations per region
        missing_regions = []
        for region, status in detective_status.items():
            if status['needs_changes']:
                missing_regions.append(region)
        
        if missing_regions:
            printc(YELLOW, f"\n📋 DETECTIVE CONFIGURATION NEEDED:")
            for region in missing_regions:
                status = detective_status[region]
                
                printc(YELLOW, f"\n  🌍 Region: {region}")
                
                if status['delegation_status'] == 'not_delegated':
                    printc(YELLOW, f"    • Missing: Detective delegation to Security account")
                    printc(YELLOW, f"      Recommend: Delegate Detective administration to {security_account}")
                
                if status['detective_enabled'] and status['member_count'] == 0:
                    printc(YELLOW, f"    • Missing: Organization member accounts")
                    printc(YELLOW, f"      Recommend: Add existing organization accounts to Detective")
                    printc(YELLOW, f"      Recommend: Enable auto-enrollment for new accounts")
                
                if not status['detective_enabled']:
                    printc(YELLOW, f"    • Missing: Detective investigation capabilities")
                    printc(YELLOW, f"      Recommend: Enable Detective investigation capabilities")
                    printc(YELLOW, f"      Recommend: Add existing organization accounts as Detective members")
                    printc(YELLOW, f"      Recommend: Enable automatic member invitation for new accounts")
                    printc(YELLOW, f"      Recommend: Configure data retention period (default: 365 days)")
                    printc(YELLOW, f"      Note: Detective requires 48 hours of GuardDuty data before activation")
        
        # Show what actions would be taken
        if dry_run:
            printc(YELLOW, "\n🔍 DRY RUN: Recommended actions to fix Detective setup:")
            
            action_count = 1
            for region in missing_regions:
                status = detective_status[region]
                
                if status['delegation_status'] == 'not_delegated':
                    printc(YELLOW, f"  {action_count}. Delegate Detective administration to Security account {security_account} in {region}")
                    action_count += 1
                
                if not status['detective_enabled']:
                    printc(YELLOW, f"  {action_count}. Enable Detective investigation capabilities in {region}")
                    action_count += 1
                    printc(YELLOW, f"  {action_count}. Configure data retention settings for Detective in {region}")
                    action_count += 1
                
                if status['detective_enabled'] and status['member_count'] == 0:
                    printc(YELLOW, f"  {action_count}. Invite all organization accounts to Detective in {region}")
                    action_count += 1
                    printc(YELLOW, f"  {action_count}. Enable automatic member invitation for new accounts in {region}")
                    action_count += 1
                elif not status['detective_enabled']:
                    # If no graph exists, these steps are part of initial setup
                    printc(YELLOW, f"  {action_count}. Invite all organization accounts to Detective in {region}")
                    action_count += 1
                    printc(YELLOW, f"  {action_count}. Enable automatic member invitation for new accounts in {region}")
                    action_count += 1
        else:
            printc(YELLOW, "\n🔧 Making Detective changes...")
            # TODO: Implement actual Detective changes
            for region in missing_regions:
                printc(YELLOW, f"  TODO: Configure Detective in {region}")
        
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_detective: {e}")
        return False

def check_guardduty_prerequisite(admin_account, security_account, cross_account_role, regions, verbose=False):
    """
    Check if GuardDuty is properly configured as a prerequisite for Detective.
    
    Detective requires GuardDuty to be running to provide findings for investigation.
    Returns: 'ready', 'not_configured', 'partially_configured'
    """
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        # Simple check - is GuardDuty delegated and working in main region
        main_region = regions[0]
        
        # Check if GuardDuty is delegated
        orgs_client = boto3.client('organizations', region_name=main_region)
        try:
            paginator = orgs_client.get_paginator('list_delegated_administrators')
            guardduty_admins = []
            for page in paginator.paginate(ServicePrincipal='guardduty.amazonaws.com'):
                guardduty_admins.extend(page.get('DelegatedAdministrators', []))
        except ClientError:
            return 'not_configured'
        
        # Check if delegated to our security account
        is_delegated = any(admin.get('Id') == security_account for admin in guardduty_admins)
        
        if not is_delegated:
            return 'not_configured'
        
        # Quick check if GuardDuty detector exists in main region
        guardduty_client = boto3.client('guardduty', region_name=main_region)
        try:
            detectors = guardduty_client.list_detectors()
            if not detectors.get('DetectorIds'):
                return 'not_configured'
        except ClientError:
            return 'not_configured'
        
        if verbose:
            printc(GRAY, f"    ✅ GuardDuty appears to be configured (delegation + detector found)")
        
        return 'ready'
        
    except Exception as e:
        if verbose:
            printc(GRAY, f"    ⚠️  GuardDuty prerequisite check failed: {str(e)}")
        return 'not_configured'

def check_detective_in_region(region, admin_account, security_account, cross_account_role, verbose=False):
    """
    Check AWS Detective status in a specific region.
    
    Handles all configuration scenarios:
    1. Not delegated - No Detective delegation found
    2. Delegated but not enabled - Delegation exists but no graph
    3. Enabled but no members - Graph exists but no member accounts
    4. Fully configured - Delegation + graph + members
    
    Returns status dictionary with needed changes and detailed findings.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    status = {
        'region': region,
        'detective_enabled': False,
        'delegation_status': 'unknown',
        'member_count': 0,
        'graph_arn': None,
        'needs_changes': False,
        'issues': [],
        'actions': [],
        'errors': [],
        'detective_details': []
    }
    
    try:
        # Check delegation status first
        try:
            orgs_client = boto3.client('organizations', region_name=region)
            all_delegated_admins = []
            paginator = orgs_client.get_paginator('list_delegated_administrators')
            for page in paginator.paginate(ServicePrincipal='detective.amazonaws.com'):
                all_delegated_admins.extend(page.get('DelegatedAdministrators', []))
            
            is_delegated_to_security = False
            for admin in all_delegated_admins:
                if admin.get('Id') == security_account:
                    status['delegation_status'] = 'delegated'
                    is_delegated_to_security = True
                    status['detective_details'].append(f"✅ Delegated Admin: {admin.get('Name', admin.get('Id'))}")
                    break
            else:
                if all_delegated_admins:
                    # Delegated to wrong account
                    status['delegation_status'] = 'delegated_wrong'
                    other_admin_ids = [admin.get('Id') for admin in all_delegated_admins]
                    status['detective_details'].append(f"⚠️  Detective delegated to other account(s): {', '.join(other_admin_ids)}")
                    status['issues'].append(f"Detective delegated to {', '.join(other_admin_ids)} instead of Security account {security_account}")
                    status['actions'].append("Remove existing delegation and delegate to Security account")
                    status['needs_changes'] = True
                else:
                    # Not delegated
                    status['delegation_status'] = 'not_delegated'
                    status['needs_changes'] = True
                    status['issues'].append("Detective is not delegated to Security account")
                    status['actions'].append("Delegate Detective administration to Security account")
                    status['detective_details'].append("❌ No delegation found - should delegate to Security account")
                    
        except ClientError as e:
            error_msg = f"Check delegated administrators failed: {str(e)}"
            status['errors'].append(error_msg)
            status['detective_details'].append(f"❌ Delegation check failed: {str(e)}")
        
        # Check Detective graphs from admin account perspective
        try:
            detective_client = boto3.client('detective', region_name=region)
            
            # Detective list_graphs is NOT paginated - use direct call
            response = detective_client.list_graphs()
            all_graphs = response.get('GraphList', [])
            
            if all_graphs:
                status['detective_enabled'] = True
                status['graph_arn'] = all_graphs[0].get('Arn')  # Typically one graph per region
                status['detective_details'].append(f"✅ Detective Graph: {len(all_graphs)} found")
                
                # Check each graph for member details
                for graph in all_graphs:
                    graph_arn = graph.get('Arn')
                    graph_created = graph.get('CreatedTime')
                    
                    status['detective_details'].append(f"   📝 Graph ARN: {graph_arn}")
                    status['detective_details'].append(f"      Created: {graph_created}")
                    
                    # Get member accounts for this graph
                    try:
                        members_paginator = detective_client.get_paginator('list_members')
                        all_members = []
                        for page in members_paginator.paginate(GraphArn=graph_arn):
                            all_members.extend(page.get('MemberDetails', []))
                        
                        status['member_count'] = len(all_members)
                        status['detective_details'].append(f"      Members: {len(all_members)} accounts")
                        
                        if len(all_members) == 0:
                            status['needs_changes'] = True
                            status['issues'].append("Detective graph has no member accounts")
                            status['actions'].append("Add organization member accounts to Detective")
                            status['actions'].append("Enable auto-enrollment for new accounts")
                        else:
                            # Show member summary
                            invited_count = sum(1 for member in all_members if member.get('Status') == 'INVITED')
                            enabled_count = sum(1 for member in all_members if member.get('Status') == 'ENABLED')
                            
                            if invited_count > 0:
                                status['detective_details'].append(f"      Pending Invitations: {invited_count}")
                            if enabled_count > 0:
                                status['detective_details'].append(f"      Active Members: {enabled_count}")
                                
                    except ClientError as e:
                        error_msg = f"List members failed for graph {graph_arn}: {str(e)}"
                        status['errors'].append(error_msg)
                        status['detective_details'].append(f"      ❌ Member check failed: {str(e)}")
                        
            else:
                # No graphs found
                if status['delegation_status'] == 'delegated':
                    status['needs_changes'] = True
                    status['issues'].append("Detective delegated but no investigation graph found")
                    status['actions'].append("Enable Detective investigation graph")
                    status['detective_details'].append("❌ No investigation graph found despite delegation")
                else:
                    status['detective_details'].append("❌ No investigation graph found")
                    
        except ClientError as e:
            error_msg = f"List graphs failed: {str(e)}"
            status['errors'].append(error_msg)
            status['detective_details'].append(f"❌ List graphs failed: {str(e)}")
        
        # Get comprehensive organization data if delegated to security account
        if (is_delegated_to_security and 
            cross_account_role and 
            security_account != admin_account):
            
            if verbose:
                printc(GRAY, f"    🔄 Switching to delegated admin account for complete data...")
            
            # Create cross-account client to security account
            delegated_client = get_client('detective', security_account, region, cross_account_role)
            
            if delegated_client:
                try:
                    # Get graphs from delegated admin perspective  
                    # Detective list_graphs is NOT paginated - use direct call
                    delegated_response = delegated_client.list_graphs()
                    all_delegated_graphs = delegated_response.get('GraphList', [])
                    
                    if all_delegated_graphs:
                        status['detective_details'].append(f"✅ Delegated Admin View: {len(all_delegated_graphs)} graph(s)")
                        
                        # Update from delegated admin perspective (more authoritative)
                        status['detective_enabled'] = True
                        
                        for graph in all_delegated_graphs:
                            graph_arn = graph.get('Arn')
                            status['detective_details'].append(f"   📝 Delegated Graph: {graph_arn}")
                            
                            # Get comprehensive member data from delegated admin
                            try:
                                members_paginator = delegated_client.get_paginator('list_members')
                                all_members = []
                                for page in members_paginator.paginate(GraphArn=graph_arn):
                                    all_members.extend(page.get('MemberDetails', []))
                                
                                status['member_count'] = len(all_members)
                                
                                if len(all_members) > 0:
                                    enabled_members = [m for m in all_members if m.get('Status') == 'ENABLED']
                                    invited_members = [m for m in all_members if m.get('Status') == 'INVITED']
                                    
                                    status['detective_details'].append(f"      📊 Total Members: {len(all_members)}")
                                    status['detective_details'].append(f"      ✅ Active Members: {len(enabled_members)}")
                                    if invited_members:
                                        status['detective_details'].append(f"      📨 Pending Invitations: {len(invited_members)}")
                                else:
                                    status['detective_details'].append(f"      ❌ No member accounts found")
                                    
                            except ClientError as e:
                                status['detective_details'].append(f"      ⚠️  Member check failed: {str(e)}")
                        
                    else:
                        status['detective_details'].append("⚠️  No graphs found in delegated admin account")
                        
                except ClientError as e:
                    error_msg = f"Delegated admin graph check failed: {str(e)}"
                    status['errors'].append(error_msg)
                    status['detective_details'].append(f"❌ Delegated admin check failed: {str(e)}")
                
    except Exception as e:
        error_msg = f"General error checking region {region}: {str(e)}"
        status['errors'].append(error_msg)
        status['detective_details'].append(f"❌ General error: {str(e)}")
    
    return status

def check_anomalous_detective_regions(expected_regions, admin_account, security_account, verbose=False):
    """
    Check for Detective investigation graphs active in regions outside the expected list.
    
    This detects configuration drift where Detective was enabled in regions
    not included in the current setup, which could generate unexpected costs.
    
    Returns list of anomalous regions with graph details.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    anomalous_regions = []
    
    try:
        # Get all AWS regions to check for anomalous Detective graphs
        ec2_client = boto3.client('ec2', region_name=expected_regions[0] if expected_regions else 'us-east-1')
        regions_response = ec2_client.describe_regions()
        all_regions = [region['RegionName'] for region in regions_response['Regions']]
        
        # Check regions that are NOT in our expected list
        unexpected_regions = [region for region in all_regions if region not in expected_regions]
        
        if verbose:
            printc(GRAY, f"    Checking {len(unexpected_regions)} regions outside configuration...")
        
        for region in unexpected_regions:
            try:
                detective_client = boto3.client('detective', region_name=region)
                
                # Check if there are any Detective graphs in this region
                graphs_response = detective_client.list_graphs()
                graphs = graphs_response.get('GraphList', [])
                
                graph_details = []
                for graph in graphs:
                    try:
                        # Get member accounts for this graph to check if it's active
                        members_paginator = detective_client.get_paginator('list_members')
                        all_members = []
                        for page in members_paginator.paginate(GraphArn=graph['Arn']):
                            all_members.extend(page.get('MemberDetails', []))
                        
                        graph_details.append({
                            'graph_arn': graph['Arn'],
                            'created_time': graph.get('CreatedTime', 'Unknown'),
                            'member_count': len(all_members)
                        })
                    except ClientError as e:
                        if verbose:
                            printc(GRAY, f"    (Could not get members for graph {graph['Arn']}: {str(e)})")
                        graph_details.append({
                            'graph_arn': graph['Arn'],
                            'created_time': graph.get('CreatedTime', 'Unknown'),
                            'member_count': 0
                        })
                
                if graph_details:
                    anomalous_regions.append({
                        'region': region,
                        'graph_count': len(graph_details),
                        'graph_details': graph_details
                    })
                    
                    if verbose:
                        printc(YELLOW, f"    ⚠️  Anomalous Detective in {region}: {len(graph_details)} graph(s)")
                        for detail in graph_details:
                            printc(YELLOW, f"       Graph {detail['graph_arn'].split('/')[-1]}: {detail['member_count']} members")
                            
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