"""
IAM Access Analyzer setup module

Automates the manual steps:
1. In the Org account, delegate administration to Security-Adm account
2. In Security-Adm, set up organisation-wide analyzer for external access (all regions)
3. In Security-Adm, set up organisation-wide analyzer for unused access (main region only)
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

def setup_access_analyzer(enabled, params, dry_run, verbose):
    """Setup IAM Access Analyzer delegation and organization-wide analyzers."""
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "IAM ACCESS ANALYZER SETUP")
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
            # WARNING when someone tries to disable Access Analyzer
            printc(RED, "\n" + "🚨" * 15)
            printc(RED, "🚨 WARNING: IAM Access Analyzer Disable Requested! 🚨")
            printc(RED, "🚨" * 15)
            printc(RED, "")
            printc(RED, "IAM Access Analyzer is a CRITICAL security service that:")
            printc(RED, "• Identifies resources shared with external entities")
            printc(RED, "• Detects unused access permissions and roles")
            printc(RED, "• Provides continuous security posture monitoring")
            printc(RED, "• Required for compliance and access governance")
            printc(RED, "")
            printc(RED, "⛔ DISABLING ACCESS ANALYZER REDUCES SECURITY VISIBILITY!")
            printc(RED, "")
            printc(RED, "Access Analyzer setup SKIPPED due to enabled=No parameter.")
            printc(RED, "🚨" * 15)
            return True
        
        # enabled == 'Yes' - proceed with Access Analyzer setup/verification
        regions = params['regions']
        admin_account = params['admin_account']
        security_account = params['security_account']
        cross_account_role = params['cross_account_role']
        main_region = regions[0]
        
        printc(YELLOW, f"Checking IAM Access Analyzer setup in {len(regions)} regions...")
        if verbose:
            printc(GRAY, f"Admin account ({admin_account}): Should delegate to Security account")
            printc(GRAY, f"Security account ({security_account}): Should be delegated admin for organization")
            printc(GRAY, f"Main region ({main_region}): Should have both external and unused access analyzers")
            printc(GRAY, f"Other regions: Should have external access analyzers only")
        
        # Check current Access Analyzer state in all regions
        analyzer_status = {}
        any_changes_needed = False
        
        # First, check for anomalous regions (Access Analyzer enabled in regions not in our list)
        anomalous_regions = detect_anomalous_access_analyzer_regions(regions, admin_account, security_account, cross_account_role, verbose)
            
        if anomalous_regions:
            any_changes_needed = True
            printc(RED, f"\n🚨 ANOMALOUS ACCESS ANALYZER REGIONS DETECTED!")
            printc(RED, f"Access Analyzer is enabled in regions NOT in your specified regions list:")
            for anomalous_region in anomalous_regions:
                printc(RED, f"  • {anomalous_region}: Access Analyzer enabled but not in regions parameter")
                printc(RED, f"    This may indicate accidental enablement or configuration drift")
            printc(RED, f"⚠️  Consider reviewing these regions and disabling Access Analyzer if not needed")
        
        for region in regions:
            if verbose:
                printc(GRAY, f"\n🔍 Checking Access Analyzer in region {region}...")
            
            is_main_region = (region == main_region)
            region_status = check_access_analyzer_in_region(region, admin_account, security_account, cross_account_role, is_main_region, verbose)
            analyzer_status[region] = region_status
            
            if not region_status['needs_changes']:
                if verbose:
                    printc(GREEN, f"  ✅ Access Analyzer properly configured in {region}")
            else:
                any_changes_needed = True
                # Always show issues when changes are needed, even without verbose
                printc(YELLOW, f"  ⚠️  Access Analyzer needs changes in {region}")
                # Show basic issues without verbose
                if not verbose:
                    for issue in region_status['issues'][:2]:  # Show first 2 issues
                        printc(YELLOW, f"    • {issue}")
                    if len(region_status['issues']) > 2:
                        printc(YELLOW, f"    • ... and {len(region_status['issues']) - 2} more (use --verbose for details)")
        
        # Report findings and take action
        if not any_changes_needed:
            printc(GREEN, "✅ IAM Access Analyzer is already properly configured in all regions!")
            printc(GREEN, "   No changes needed - existing setup meets stringent security standards.")
            
            # Show detailed configuration for each region ONLY when verbose
            if verbose:
                printc(LIGHT_BLUE, "\n📋 Current IAM Access Analyzer Configuration:")
                for region, status in analyzer_status.items():
                    printc(LIGHT_BLUE, f"\n🌍 Region: {region}")
                    if status['analyzer_enabled']:
                        for detail in status['analyzer_details']:
                            printc(GRAY, f"  {detail}")
                    else:
                        printc(GRAY, "  Access Analyzer not enabled in this region")
            
            return True
        
        # Some changes needed
        printc(YELLOW, "⚠️  IAM Access Analyzer needs configuration in some regions:")
        
        for region, status in analyzer_status.items():
            if status['needs_changes']:
                for issue in status['issues']:
                    printc(YELLOW, f"  • {region}: {issue}")
        
        if dry_run:
            printc(YELLOW, "\n🔍 DRY RUN: Would make the following changes:")
            for region, status in analyzer_status.items():
                if status['needs_changes']:
                    for action in status['actions']:
                        printc(YELLOW, f"  • {region}: {action}")
        else:
            printc(YELLOW, "\n🔧 Making Access Analyzer changes...")
            # TODO: Implement actual Access Analyzer changes
            for region, status in analyzer_status.items():
                if status['needs_changes']:
                    printc(YELLOW, f"  TODO: Implement changes for {region}")
        
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_access_analyzer: {e}")
        return False

def check_access_analyzer_in_region(region, admin_account, security_account, cross_account_role, is_main_region, verbose=False):
    """
    Check AWS IAM Access Analyzer status in a specific region.
    
    Handles all configuration scenarios:
    1. Unconfigured service - No Access Analyzer delegation found
    2. Configuration but missing analyzers - Delegated but missing required analyzers
    3. Weird configurations - Wrong delegation, suboptimal analyzer types, incomplete coverage
    4. Valid configurations - Properly delegated with correct analyzers for external and unused access
    
    Returns status dictionary with needed changes and detailed findings.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    status = {
        'region': region,
        'analyzer_enabled': False,
        'delegation_status': 'unknown',
        'external_analyzer_count': 0,
        'unused_analyzer_count': 0,
        'needs_changes': False,
        'issues': [],
        'actions': [],
        'errors': [],
        'analyzer_details': []
    }
    
    try:
        # Check delegation status first
        try:
            orgs_client = boto3.client('organizations', region_name=region)
            all_delegated_admins = []
            paginator = orgs_client.get_paginator('list_delegated_administrators')
            for page in paginator.paginate(ServicePrincipal='access-analyzer.amazonaws.com'):
                all_delegated_admins.extend(page.get('DelegatedAdministrators', []))
            
            is_delegated_to_security = False
            for admin in all_delegated_admins:
                if admin.get('Id') == security_account:
                    status['delegation_status'] = 'delegated'
                    is_delegated_to_security = True
                    status['analyzer_details'].append(f"✅ Delegated Admin: {admin.get('Name', admin.get('Id'))}")
                    break
            else:
                if all_delegated_admins:
                    # Case 3: Weird configuration - delegated to wrong account
                    status['delegation_status'] = 'delegated_wrong'
                    other_admin_ids = [admin.get('Id') for admin in all_delegated_admins]
                    status['analyzer_details'].append(f"⚠️  Access Analyzer delegated to other account(s): {', '.join(other_admin_ids)}")
                    status['analyzer_details'].append(f"⚠️  Expected delegation to Security account: {security_account}")
                    status['issues'].append(f"Access Analyzer delegated to {', '.join(other_admin_ids)} instead of Security account {security_account}")
                    status['actions'].append("Remove existing delegation and delegate to Security account")
                    status['needs_changes'] = True
                else:
                    # Case 1: Unconfigured service - no delegation
                    status['delegation_status'] = 'not_delegated'
                    status['needs_changes'] = True
                    status['issues'].append("Access Analyzer is not delegated to Security account")
                    status['actions'].append("Delegate Access Analyzer administration to Security account")
                    status['analyzer_details'].append("❌ No delegation found - should delegate to Security account")
                    
        except ClientError as e:
            error_msg = f"Check delegated administrators failed: {str(e)}"
            status['errors'].append(error_msg)
            status['analyzer_details'].append(f"❌ Delegation check failed: {str(e)}")
            
        # Check analyzers from admin account perspective
        try:
            analyzer_client = boto3.client('accessanalyzer', region_name=region)
            all_analyzers = []
            paginator = analyzer_client.get_paginator('list_analyzers')
            for page in paginator.paginate():
                all_analyzers.extend(page.get('analyzers', []))
            
            if all_analyzers:
                status['analyzer_enabled'] = True
                status['analyzer_details'].append(f"✅ Access Analyzers: {len(all_analyzers)} found")
                
                # Analyze each analyzer
                for analyzer in all_analyzers:
                    analyzer_name = analyzer.get('name')
                    analyzer_type = analyzer.get('type')
                    analyzer_status = analyzer.get('status')
                    
                    status['analyzer_details'].append(f"   📝 Analyzer '{analyzer_name}':")
                    status['analyzer_details'].append(f"      Type: {analyzer_type}")
                    status['analyzer_details'].append(f"      Status: {analyzer_status}")
                    
                    # Count analyzer types based on naming patterns and configuration
                    # External access analyzers typically focus on external access
                    # Unused access analyzers focus on unused permissions
                    if 'external' in analyzer_name.lower() or analyzer_type == 'ORGANIZATION':
                        status['external_analyzer_count'] += 1
                        status['analyzer_details'].append(f"      🌍 External Access Analyzer")
                    elif 'unused' in analyzer_name.lower():
                        status['unused_analyzer_count'] += 1
                        status['analyzer_details'].append(f"      📊 Unused Access Analyzer")
                    else:
                        # Generic analyzer - could be either type, count as external for now
                        status['external_analyzer_count'] += 1
                        status['analyzer_details'].append(f"      📋 General Analyzer (assuming external access)")
                        
            else:
                # Case 2: Configuration but missing analyzers
                if status['delegation_status'] == 'delegated':
                    status['needs_changes'] = True
                    status['issues'].append("Access Analyzer delegated but no analyzers found")
                    status['actions'].append("Create required analyzers for external and unused access")
                    status['analyzer_details'].append("❌ No analyzers found despite delegation")
                else:
                    status['analyzer_details'].append("❌ No analyzers found")
                    
        except ClientError as e:
            error_msg = f"List analyzers failed: {str(e)}"
            status['errors'].append(error_msg)
            status['analyzer_details'].append(f"❌ List analyzers failed: {str(e)}")
        
        # Get comprehensive organization data if delegated to security account
        if (is_delegated_to_security and 
            cross_account_role and 
            security_account != admin_account):
            
            if verbose:
                printc(GRAY, f"    🔄 Switching to delegated admin account for complete data...")
            
            # Create cross-account client to security account
            delegated_client = get_client('accessanalyzer', security_account, region, cross_account_role)
            
            if delegated_client:
                try:
                    # Get analyzers from delegated admin perspective (with pagination)
                    all_delegated_analyzers = []
                    delegated_paginator = delegated_client.get_paginator('list_analyzers')
                    for page in delegated_paginator.paginate():
                        all_delegated_analyzers.extend(page.get('analyzers', []))
                    
                    if all_delegated_analyzers:
                        status['analyzer_details'].append(f"✅ Delegated Admin View: {len(all_delegated_analyzers)} analyzers")
                        
                        # Reset counters for delegated admin perspective
                        status['external_analyzer_count'] = 0
                        status['unused_analyzer_count'] = 0
                        
                        for analyzer in all_delegated_analyzers:
                            analyzer_name = analyzer.get('name')
                            analyzer_type = analyzer.get('type')
                            analyzer_status = analyzer.get('status')
                            
                            status['analyzer_details'].append(f"   📝 Delegated Analyzer '{analyzer_name}':")
                            status['analyzer_details'].append(f"      Type: {analyzer_type}")
                            status['analyzer_details'].append(f"      Status: {analyzer_status}")
                            
                            # More sophisticated analyzer type detection
                            if 'external' in analyzer_name.lower() or analyzer_type == 'ORGANIZATION':
                                status['external_analyzer_count'] += 1
                                status['analyzer_details'].append(f"      🌍 External Access Analyzer")
                            elif 'unused' in analyzer_name.lower():
                                status['unused_analyzer_count'] += 1
                                status['analyzer_details'].append(f"      📊 Unused Access Analyzer")
                            else:
                                status['external_analyzer_count'] += 1
                                status['analyzer_details'].append(f"      📋 General Analyzer (assuming external access)")
                            
                            # Get findings count (with pagination)
                            try:
                                findings_count = 0
                                findings_paginator = delegated_client.get_paginator('list_findings')
                                for page in findings_paginator.paginate(analyzerArn=analyzer.get('arn')):
                                    findings_count += len(page.get('findings', []))
                                
                                if findings_count > 0:
                                    status['analyzer_details'].append(f"      🔍 Active Findings: {findings_count}")
                                else:
                                    status['analyzer_details'].append(f"      ✅ No Active Findings")
                                    
                            except ClientError as e:
                                error_msg = f"List findings failed for {analyzer_name}: {str(e)}"
                                status['errors'].append(error_msg)
                                status['analyzer_details'].append(f"      ❌ Findings check failed: {str(e)}")
                        
                    else:
                        # Case 3: Weird configuration - delegation but no analyzers in delegated account
                        status['analyzer_details'].append("⚠️  No analyzers found in delegated admin account")
                        status['needs_changes'] = True
                        status['issues'].append("Delegated admin has no analyzers - setup may be incomplete")
                        status['actions'].append("Create required analyzers in delegated admin account")
                        
                except ClientError as e:
                    error_msg = f"Delegated admin analyzer check failed: {str(e)}"
                    status['errors'].append(error_msg)
                    status['analyzer_details'].append(f"❌ Delegated admin check failed: {str(e)}")
            else:
                status['analyzer_details'].append("❌ Failed to create cross-account client to security account")
        
        # Validate analyzer coverage based on region requirements
        if status['delegation_status'] == 'delegated' and status['analyzer_enabled']:
            # Case 4: Valid configuration vs Case 3: Weird configuration assessment
            
            # All regions should have external access analyzer
            if status['external_analyzer_count'] == 0:
                status['needs_changes'] = True
                status['issues'].append("Missing external access analyzer for organization-wide monitoring")
                status['actions'].append("Create organization-wide analyzer for external access")
            
            # Main region should also have unused access analyzer
            if is_main_region and status['unused_analyzer_count'] == 0:
                status['needs_changes'] = True
                status['issues'].append("Main region missing unused access analyzer")
                status['actions'].append("Create organization-wide analyzer for unused access (main region only)")
            
            # Non-main regions should NOT have unused access analyzer (optimal setup)
            if not is_main_region and status['unused_analyzer_count'] > 0:
                status['analyzer_details'].append(f"   ⚠️  Unused access analyzer in non-main region (consider consolidating to main region)")
            
            # Report coverage summary
            if status['external_analyzer_count'] > 0:
                status['analyzer_details'].append(f"   ✅ External Access Coverage: {status['external_analyzer_count']} analyzer(s)")
            if status['unused_analyzer_count'] > 0:
                status['analyzer_details'].append(f"   ✅ Unused Access Coverage: {status['unused_analyzer_count']} analyzer(s)")
                
    except Exception as e:
        error_msg = f"General error checking region {region}: {str(e)}"
        status['errors'].append(error_msg)
        status['analyzer_details'].append(f"❌ General error: {str(e)}")
    
    return status

def detect_anomalous_access_analyzer_regions(expected_regions, admin_account, security_account, cross_account_role, verbose=False):
    """
    Detect regions where Access Analyzer is enabled but not in the expected regions list.
    
    This is a safety feature to identify configuration drift or accidental enablement.
    Returns list of regions that have Access Analyzer enabled but aren't expected.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    anomalous_regions = []
    
    try:
        # Get list of all AWS regions where organizations service is available
        ec2_client = boto3.client('ec2', region_name=expected_regions[0])  # Use first region as base
        all_regions_response = ec2_client.describe_regions()
        all_regions = [region['RegionName'] for region in all_regions_response['Regions']]
        
        if verbose:
            printc(GRAY, f"🔍 Scanning {len(all_regions)} AWS regions for anomalous Access Analyzer configurations...")
        
        # Check each region that's not in our expected list
        regions_to_check = [region for region in all_regions if region not in expected_regions]
        
        for region in regions_to_check:
            try:
                # Check if Access Analyzer has any delegation in this region
                orgs_client = boto3.client('organizations', region_name=region)
                all_delegated_admins = []
                try:
                    paginator = orgs_client.get_paginator('list_delegated_administrators')
                    for page in paginator.paginate(ServicePrincipal='access-analyzer.amazonaws.com'):
                        all_delegated_admins.extend(page.get('DelegatedAdministrators', []))
                except ClientError as e:
                    # Some regions might not support organizations or delegation
                    if 'UnsupportedOperation' not in str(e) and 'AccessDenied' not in str(e):
                        if verbose:
                            printc(GRAY, f"  ⚠️  Could not check delegation in {region}: {str(e)}")
                    continue
                
                # If there's any delegation for Access Analyzer in this region, it's anomalous
                if all_delegated_admins:
                    anomalous_regions.append(region)
                    if verbose:
                        delegated_accounts = [admin.get('Id') for admin in all_delegated_admins]
                        printc(GRAY, f"  🚨 Found Access Analyzer delegation in {region}: {', '.join(delegated_accounts)}")
                
                # Also check if there are any analyzers directly (without delegation)
                try:
                    analyzer_client = boto3.client('accessanalyzer', region_name=region)
                    all_analyzers = []
                    paginator = analyzer_client.get_paginator('list_analyzers')
                    for page in paginator.paginate():
                        all_analyzers.extend(page.get('analyzers', []))
                    
                    if all_analyzers and region not in anomalous_regions:
                        anomalous_regions.append(region)
                        if verbose:
                            printc(GRAY, f"  🚨 Found {len(all_analyzers)} analyzers in {region}")
                            
                except ClientError as e:
                    # Access Analyzer might not be available in all regions
                    if 'UnsupportedOperation' not in str(e) and 'AccessDenied' not in str(e):
                        if verbose:
                            printc(GRAY, f"  ⚠️  Could not check analyzers in {region}: {str(e)}")
                    continue
                    
            except Exception as e:
                if verbose:
                    printc(GRAY, f"  ⚠️  Error checking region {region}: {str(e)}")
                continue
        
        if verbose and not anomalous_regions:
            printc(GRAY, f"  ✅ No anomalous Access Analyzer configurations found in other regions")
        
    except Exception as e:
        printc(RED, f"  ❌ Error during anomalous region detection: {str(e)}")
    
    return anomalous_regions