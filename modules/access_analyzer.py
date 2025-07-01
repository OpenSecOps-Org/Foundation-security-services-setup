"""
IAM Access Analyzer setup module

Automates the manual steps:
1. In the Org account, delegate administration to Security-Adm account
2. In Security-Adm, set up organisation-wide analyzer for external access (all regions)
3. In Security-Adm, set up organisation-wide analyzer for unused access (main region only)
"""

from .utils import printc, get_client, DelegationChecker, AnomalousRegionChecker, create_service_status, YELLOW, LIGHT_BLUE, GREEN, RED, GRAY, END, BOLD

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
            printc(RED, "\n" + "" * 15)
            printc(RED, " WARNING: IAM Access Analyzer Disable Requested ")
            printc(RED, "" * 15)
            printc(RED, "")
            printc(RED, "IAM Access Analyzer is a CRITICAL security service that:")
            printc(RED, "• Identifies resources shared with external entities")
            printc(RED, "• Detects unused access permissions and roles")
            printc(RED, "• Provides continuous security posture monitoring")
            printc(RED, "• Required for compliance and access governance")
            printc(RED, "")
            printc(RED, "⛔ DISABLING ACCESS ANALYZER REDUCES SECURITY VISIBILITY")
            printc(RED, "")
            printc(RED, "Access Analyzer setup SKIPPED due to enabled=No parameter.")
            printc(RED, "" * 15)
            
            # Check for spurious Access Analyzer activations in ALL regions (since service is disabled)
            regions = params['regions']
            admin_account = params['admin_account']
            security_account = params['security_account']
            cross_account_role = params['cross_account_role']
            
            if verbose:
                printc(GRAY, f"\n Checking all AWS regions for spurious Access Analyzer activation...")
            
            # Pass empty list as expected_regions so ALL regions are checked
            anomalous_regions = AnomalousRegionChecker.check_service_anomalous_regions(
                service_name='access_analyzer',
                expected_regions=[],
                admin_account=admin_account,
                security_account=security_account,
                cross_account_role=cross_account_role,
                verbose=verbose
            )
            
            if anomalous_regions:
                printc(YELLOW, f"\n⚠️  SPURIOUS ACCESS ANALYZER ACTIVATION DETECTED:")
                printc(YELLOW, f"Access Analyzer analyzers found in unexpected regions:")
                printc(YELLOW, f"")
                printc(YELLOW, f"Current spurious Access Analyzer resources:")
                printc(YELLOW, f"  • Analyzers active across {len(anomalous_regions)} unexpected region(s)")
                for anomaly in anomalous_regions:
                    region = anomaly.region
                    analyzer_count = anomaly.resource_count
                    printc(YELLOW, f"     {region}: {analyzer_count} analyzer(s) active (not in configured regions)")
                printc(YELLOW, f"")
                printc(YELLOW, f" SPURIOUS ACTIVATION RECOMMENDATIONS:")
                printc(YELLOW, f"  • Review: These analyzers may be configuration drift or forgotten resources")
                printc(YELLOW, f"  • Recommended: Disable Access Analyzer analyzers in these regions to control costs")
                printc(YELLOW, f"  • Note: Access Analyzer generates charges per analyzer and finding")
            else:
                if verbose:
                    printc(GRAY, f"   ✅ Access Analyzer is not active in any region - no cleanup needed")
            
            return True
        
        # enabled == 'Yes' - proceed with Access Analyzer setup/verification
        regions = params['regions']
        admin_account = params['admin_account']
        security_account = params['security_account']
        cross_account_role = params['cross_account_role']
        main_region = regions[0]
        
        printc(YELLOW, f"Checking IAM Access Analyzer setup...")
        if verbose:
            printc(GRAY, f"Expected regions: {', '.join(regions)}")
            printc(GRAY, f"Admin account ({admin_account}): Should delegate to Security account")
            printc(GRAY, f"Security account ({security_account}): Should be delegated admin for organization")
            printc(GRAY, f"Main region ({main_region}): Should have both external and unused access analyzers")
            printc(GRAY, f"Other regions: Should have external access analyzers only")
        
        # Step 1: Check delegation status globally (Access Analyzer delegation is organization-wide)
        if verbose:
            printc(GRAY, f"\n Checking Access Analyzer delegation (organization-wide)...")
            
        delegation_status = check_access_analyzer_delegation(admin_account, security_account, cross_account_role, verbose)
        
        if delegation_status == 'not_delegated':
            printc(YELLOW, f"⚠️  Access Analyzer is not delegated to Security account")
        elif delegation_status == 'delegated_wrong':
            printc(YELLOW, f"⚠️  Access Analyzer is delegated to wrong account")
        elif delegation_status == 'delegated':
            if verbose:
                printc(GREEN, f"✅ Access Analyzer properly delegated to Security account")
        
        # Step 2: Check for anomalous analyzers in unexpected regions
        anomalous_regions = AnomalousRegionChecker.check_service_anomalous_regions(
            service_name='access_analyzer',
            expected_regions=regions,
            admin_account=admin_account,
            security_account=security_account,
            cross_account_role=cross_account_role,
            verbose=verbose
        )
        
        any_changes_needed = False
        if anomalous_regions:
            any_changes_needed = True
            printc(RED, f"\n ANOMALOUS ANALYZERS DETECTED")
            printc(RED, f"Access Analyzer analyzers found in regions NOT in your specified regions list:")
            for anomaly in anomalous_regions:
                region = anomaly.region
                analyzer_count = anomaly.resource_count
                printc(RED, f"  • {region}: {analyzer_count} analyzer(s) but not in regions parameter")
                printc(RED, f"    This may indicate accidental analyzer creation or configuration drift")
            printc(RED, f"⚠️  Consider reviewing these regions and removing unneeded analyzers")
        
        # Step 3: Check analyzer presence in expected regions
        analyzer_status = {}
        for region in regions:
            if verbose:
                printc(GRAY, f"\n Checking analyzers in region {region}...")
            
            is_main_region = (region == main_region)
            region_status = check_access_analyzer_in_region(region, admin_account, security_account, cross_account_role, is_main_region, delegation_status, verbose)
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
        
        # Step 4: Factor in delegation issues
        if delegation_status != 'delegated':
            any_changes_needed = True
        
        # Report findings and take action
        if not any_changes_needed:
            printc(GREEN, "✅ IAM Access Analyzer is already properly configured in all regions")
            printc(GREEN, "   No changes needed - existing setup meets stringent security standards")
            
            # Show detailed configuration for each region ONLY when verbose
            if verbose:
                printc(LIGHT_BLUE, "\n Current IAM Access Analyzer Configuration:")
                for region, status in analyzer_status.items():
                    printc(LIGHT_BLUE, f"\n Region: {region}")
                    if status['service_enabled']:
                        for detail in status['service_details']:
                            printc(GRAY, f"  {detail}")
                    else:
                        printc(GRAY, "  Access Analyzer not enabled in this region")
            
            return True
        
        # Show specific recommendations based on what's missing
        printc(YELLOW, "⚠️  IAM Access Analyzer needs configuration:")
        
        # Show delegation issues first
        if delegation_status == 'not_delegated':
            printc(YELLOW, f"\n DELEGATION REQUIRED:")
            printc(YELLOW, f"  • Access Analyzer is not delegated to Security account")
            printc(YELLOW, f"  • Recommend: Delegate Access Analyzer administration to {security_account}")
        elif delegation_status == 'delegated_wrong':
            printc(YELLOW, f"\n DELEGATION ISSUE:")
            printc(YELLOW, f"  • Access Analyzer is delegated to wrong account")
            printc(YELLOW, f"  • Recommend: Re-delegate to Security account {security_account}")
        
        # Show missing analyzer recommendations per region
        missing_regions = []
        for region, status in analyzer_status.items():
            if status['needs_changes']:
                missing_regions.append(region)
        
        if missing_regions:
            printc(YELLOW, f"\n MISSING ANALYZERS:")
            for region in missing_regions:
                status = analyzer_status[region]
                is_main = (region == main_region)
                
                printc(YELLOW, f"\n   Region: {region}")
                
                # Main region needs both external and unused access analyzers
                if is_main:
                    if status['external_analyzer_count'] == 0:
                        printc(YELLOW, f"    • Missing: External Access Analyzer (organization-wide)")
                        printc(YELLOW, f"      Recommend: Create ORGANIZATION analyzer for external access monitoring")
                    
                    if status['unused_analyzer_count'] == 0:
                        printc(YELLOW, f"    • Missing: Unused Access Analyzer (main region only)")
                        printc(YELLOW, f"      Recommend: Create ORGANIZATION analyzer for unused access detection")
                
                # Other regions need external access analyzer only
                else:
                    if status['external_analyzer_count'] == 0:
                        printc(YELLOW, f"    • Missing: External Access Analyzer (organization-wide)")
                        printc(YELLOW, f"      Recommend: Create ORGANIZATION analyzer for external access monitoring")
                    
                    # Note about unused access (should only be in main region)
                    if status['unused_analyzer_count'] == 0:
                        printc(GRAY, f"    ✓ Unused Access Analyzer not needed (main region: {main_region})")
        
        # Show what actions would be taken
        if dry_run:
            printc(YELLOW, "\n DRY RUN: Recommended actions to fix Access Analyzer setup:")
            
            if delegation_status != 'delegated':
                printc(YELLOW, f"  1. Delegate Access Analyzer administration to Security account {security_account}")
            
            action_count = 2 if delegation_status != 'delegated' else 1
            for region in missing_regions:
                status = analyzer_status[region]
                is_main = (region == main_region)
                
                if status['external_analyzer_count'] == 0:
                    printc(YELLOW, f"  {action_count}. Create External Access Analyzer in {region}")
                    action_count += 1
                
                if is_main and status['unused_analyzer_count'] == 0:
                    printc(YELLOW, f"  {action_count}. Create Unused Access Analyzer in {region} (main region)")
                    action_count += 1
        else:
            printc(YELLOW, "\n Making Access Analyzer changes...")
            # TODO: Implement actual Access Analyzer changes
            if delegation_status != 'delegated':
                printc(YELLOW, f"  TODO: Delegate Access Analyzer to {security_account}")
            
            for region in missing_regions:
                printc(YELLOW, f"  TODO: Create required analyzers in {region}")
        
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_access_analyzer: {e}")
        return False

def check_access_analyzer_delegation(admin_account, security_account, cross_account_role='AWSControlTowerExecution', verbose=False):
    """
    Check AWS IAM Access Analyzer delegation status (organization-wide) using shared utility.
    
    Access Analyzer delegation is global, not per-region, so we check it once.
    
    Returns: 'delegated', 'delegated_wrong', or 'not_delegated'
    """
    # Use shared delegation checker
    delegation_result = DelegationChecker.check_service_delegation(
        service_principal='access-analyzer.amazonaws.com',
        admin_account=admin_account,
        security_account=security_account,
        cross_account_role=cross_account_role,
        verbose=verbose
    )
    
    if delegation_result['delegation_check_failed']:
        if verbose:
            printc(RED, f"    ❌ Delegation check failed: {', '.join(delegation_result['errors'])}")
        return 'check_failed'
    
    if delegation_result['is_delegated_to_security']:
        if verbose:
            printc(GREEN, f"    ✅ Delegated to Security account: {security_account}")
        return 'delegated'
    
    # Check if delegated to other accounts
    if delegation_result['delegation_details']:
        other_admin_ids = [admin.get('Id') for admin in delegation_result['delegation_details']]
        if verbose:
            printc(YELLOW, f"    ⚠️  Delegated to other account(s): {', '.join(other_admin_ids)}")
            printc(YELLOW, f"    Expected delegation to Security account: {security_account}")
        return 'delegated_wrong'
    
    # No delegation found
    if verbose:
        printc(RED, f"    ❌ No delegation found - should delegate to Security account")
    return 'not_delegated'

def check_access_analyzer_in_region(region, admin_account, security_account, cross_account_role, is_main_region, delegation_status, verbose=False):
    """
    Check AWS IAM Access Analyzer analyzers in a specific region.
    Returns standardized status dictionary with uniform field names.
    
    Note: IAM Access Analyzer delegation is organization-wide, not per-region.
    This function focuses on checking analyzer presence and configuration per region.
    
    Handles analyzer scenarios:
    1. No analyzers - Region has no analyzers created
    2. Missing required analyzers - Some but not all required analyzer types
    3. Suboptimal analyzer setup - Wrong types or inefficient configuration
    4. Optimal analyzer setup - Correct analyzers for external and unused access
    
    Returns status dictionary with needed changes and detailed findings.
    """
    import boto3
    from botocore.exceptions import ClientError
    
    # Create standardized status using new dataclass structure
    status_obj = create_service_status('access_analyzer', region)
    
    # Convert to dict for backward compatibility during transition
    status = status_obj.to_dict()
    
    # Set delegation status from parameter
    status['delegation_status'] = delegation_status
    
    # Ensure all Access Analyzer-specific fields are present (from AccessAnalyzerRegionStatus)
    if 'external_analyzer_count' not in status:
        status['external_analyzer_count'] = 0
    if 'unused_analyzer_count' not in status:
        status['unused_analyzer_count'] = 0
    
    try:
        # Check for analyzers in this region (from admin account perspective first)
        try:
            analyzer_client = get_client('accessanalyzer', admin_account, region, 'AWSControlTowerExecution')
            all_analyzers = []
            paginator = analyzer_client.get_paginator('list_analyzers')
            for page in paginator.paginate():
                all_analyzers.extend(page.get('analyzers', []))
            
            if all_analyzers:
                status['service_enabled'] = True
                status['service_details'].append(f"✅ Found {len(all_analyzers)} analyzer(s) in {region}")
                
                # Analyze each analyzer
                for analyzer in all_analyzers:
                    analyzer_name = analyzer.get('name')
                    analyzer_type = analyzer.get('type')
                    analyzer_status = analyzer.get('status')
                    
                    status['service_details'].append(f"    Analyzer '{analyzer_name}':")
                    status['service_details'].append(f"      Type: {analyzer_type}")
                    status['service_details'].append(f"      Status: {analyzer_status}")
                    
                    # Classify analyzer types based on naming and configuration
                    if 'external' in analyzer_name.lower() or analyzer_type == 'ORGANIZATION':
                        status['external_analyzer_count'] += 1
                        status['service_details'].append(f"       External Access Analyzer")
                    elif 'unused' in analyzer_name.lower():
                        status['unused_analyzer_count'] += 1
                        status['service_details'].append(f"      📊 Unused Access Analyzer")
                    else:
                        # Generic analyzer - assume external access for now
                        status['external_analyzer_count'] += 1
                        status['service_details'].append(f"       General Analyzer (assuming external access)")
            else:
                # Only show this if delegation isn't going to provide better data
                if delegation_status != 'delegated':
                    status['service_details'].append(f"❌ No analyzers found in {region}")
                    
        except ClientError as e:
            error_msg = f"List analyzers failed: {str(e)}"
            status['errors'].append(error_msg)
            status['service_details'].append(f"❌ List analyzers failed: {str(e)}")
        
        # If delegated to security account, get comprehensive data from delegated admin perspective
        if (delegation_status == 'delegated' and 
            cross_account_role and 
            security_account != admin_account):
            
            if verbose:
                printc(GRAY, f"     Checking from delegated admin perspective...")
            
            # Create cross-account client to security account
            delegated_client = get_client('accessanalyzer', security_account, region, cross_account_role)
            
            if delegated_client:
                try:
                    # Get analyzers from delegated admin perspective
                    all_delegated_analyzers = []
                    delegated_paginator = delegated_client.get_paginator('list_analyzers')
                    for page in delegated_paginator.paginate():
                        all_delegated_analyzers.extend(page.get('analyzers', []))
                    
                    if all_delegated_analyzers:
                        status['service_details'].append(f"✅ Delegated Admin View: {len(all_delegated_analyzers)} analyzers")
                        
                        # Reset counters for delegated admin perspective (more authoritative)
                        status['external_analyzer_count'] = 0
                        status['unused_analyzer_count'] = 0
                        status['service_enabled'] = True
                        
                        for analyzer in all_delegated_analyzers:
                            analyzer_name = analyzer.get('name')
                            analyzer_type = analyzer.get('type')
                            analyzer_status = analyzer.get('status')
                            
                            status['service_details'].append(f"    Delegated Analyzer '{analyzer_name}':")
                            status['service_details'].append(f"      Type: {analyzer_type}")
                            status['service_details'].append(f"      Status: {analyzer_status}")
                            
                            # Classify analyzer types
                            if 'external' in analyzer_name.lower() or analyzer_type == 'ORGANIZATION':
                                status['external_analyzer_count'] += 1
                                status['service_details'].append(f"       External Access Analyzer")
                            elif 'unused' in analyzer_name.lower():
                                status['unused_analyzer_count'] += 1
                                status['service_details'].append(f"      📊 Unused Access Analyzer")
                            else:
                                status['external_analyzer_count'] += 1
                                status['service_details'].append(f"       General Analyzer (assuming external access)")
                            
                            # Get findings count for this analyzer
                            try:
                                findings_count = 0
                                analyzer_type = analyzer.get('type')
                                
                                # Use appropriate API based on analyzer type
                                if analyzer_type == 'ORGANIZATION_UNUSED_ACCESS':
                                    # Use ListFindingsV2 for Unused Access analyzers
                                    try:
                                        findings_paginator = delegated_client.get_paginator('list_findings_v2')
                                        for page in findings_paginator.paginate(analyzerArn=analyzer.get('arn')):
                                            findings_count += len(page.get('findings', []))
                                    except Exception:
                                        # Fallback: Skip findings count for unused access analyzers
                                        status['service_details'].append(f"       Findings: (Unused Access - count not available)")
                                        continue
                                else:
                                    # Use ListFindings for External Access analyzers
                                    findings_paginator = delegated_client.get_paginator('list_findings')
                                    for page in findings_paginator.paginate(analyzerArn=analyzer.get('arn')):
                                        findings_count += len(page.get('findings', []))
                                
                                if findings_count > 0:
                                    status['service_details'].append(f"       Active Findings: {findings_count}")
                                else:
                                    status['service_details'].append(f"      ✅ No Active Findings")
                                    
                            except ClientError as e:
                                status['service_details'].append(f"      ⚠️  Findings check failed: {str(e)}")
                        
                    else:
                        status['service_details'].append("⚠️  No analyzers found in delegated admin account")
                        
                except ClientError as e:
                    error_msg = f"Delegated admin analyzer check failed: {str(e)}"
                    status['errors'].append(error_msg)
                    status['service_details'].append(f"❌ Delegated admin check failed: {str(e)}")
        
        # Determine if changes are needed based on analyzer requirements
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
        
        # Check delegation-specific issues
        if delegation_status == 'delegated':
            # Report coverage summary when properly delegated
            if status['external_analyzer_count'] > 0:
                status['service_details'].append(f"   ✅ External Access Coverage: {status['external_analyzer_count']} analyzer(s)")
            if status['unused_analyzer_count'] > 0:
                status['service_details'].append(f"   ✅ Unused Access Coverage: {status['unused_analyzer_count']} analyzer(s)")
                
        elif delegation_status == 'not_delegated':
            if status['service_enabled']:
                status['needs_changes'] = True
                status['issues'].append("Analyzers exist but Access Analyzer not delegated to Security account")
                status['actions'].append("Delegate Access Analyzer administration to Security account")
            else:
                # No analyzers but also not delegated - delegation should happen first
                status['needs_changes'] = True
                status['issues'].append("Access Analyzer not delegated to Security account")
                status['actions'].append("Delegate Access Analyzer administration to Security account")
                
    except Exception as e:
        error_msg = f"General error checking region {region}: {str(e)}"
        status['errors'].append(error_msg)
        status['service_details'].append(f"❌ General error: {str(e)}")
    
    return status

