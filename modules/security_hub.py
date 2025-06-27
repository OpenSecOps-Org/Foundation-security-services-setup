"""
Security Hub setup module

Automates the manual steps:
1. In the Org account, delegate administration to the Security-Adm 
   account as you enable Security Hub in all your enabled regions.
2. In the Security-Adm account, set up central configuration and consolidated 
   findings in all your enabled regions.
3. Set up two policies, one for PROD and one for DEV accounts. Make sure that 
   auto-enabling of new controls is not enabled. Also make sure that you select 
   exactly the controls you need, one by one. The PROD policy will include 
   things like multi-zone deployment, inclusion in backup plans, and deletion 
   protection of resources. The DEV policy should not require these things, to 
   ease development. Deleting a KMS key is a no-no in PROD, but should be 
   allowed in DEV, for instance.
   a. Assign the PROD policy to the org root
   b. Assign the DEV policy to IndividualBusinessUsers, Sandbox, and 
      SDLC OUs.
4. Suppress all findings in all regions to let the system start over with the new 
   settings. Relevant findings will be regenerated within 24 hours. It's a good 
   idea to wait 24 hours to verify your control setup.
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

def setup_security_hub(enabled, params, dry_run, verbose):
    """
    Setup Security Hub delegation and control policies.
    
    This function discovers the current Security Hub configuration and provides
    comprehensive recommendations based on the actual AWS environment state.
    """
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "SECURITY HUB SETUP")
        printc(LIGHT_BLUE, "="*60)
        
        if verbose:
            printc(GRAY, f"Enabled: {enabled}")
            printc(GRAY, f"Regions: {params['regions']}")
            printc(GRAY, f"Admin Account: {params['admin_account']}")
            printc(GRAY, f"Security Account: {params['security_account']}")
            printc(GRAY, f"Organization ID: {params['org_id']}")
            printc(GRAY, f"Dry Run: {dry_run}")
            printc(GRAY, f"Verbose: {verbose}")
        
        # Extract parameters
        admin_account = params['admin_account']
        security_account = params['security_account']
        regions = params['regions']
        cross_account_role = params.get('cross_account_role')
        org_id = params.get('org_id')
        root_ou = params.get('root_ou')
        
        if enabled == 'Yes':
            # Perform comprehensive Security Hub discovery and analysis
            if verbose:
                printc(GRAY, "🔍 Analyzing current Security Hub configuration...")
            
            # Check delegation status
            delegation_status = check_security_hub_delegation(admin_account, security_account, regions, verbose)
            
            # Analyze configuration in each region
            overall_config = {}
            for region in regions:
                if verbose:
                    printc(GRAY, f"🌍 Checking Security Hub in region: {region}")
                
                config = check_security_hub_in_region(region, admin_account, security_account, cross_account_role, verbose)
                overall_config[region] = config
            
            # Check control policies if delegated
            control_policies = {}
            if delegation_status.get('is_delegated_to_security', False):
                if verbose:
                    printc(GRAY, "📋 Analyzing control policies...")
                control_policies = check_control_policies(regions, admin_account, security_account, cross_account_role, verbose)
            
            # Generate comprehensive recommendations
            generate_security_hub_recommendations(delegation_status, overall_config, control_policies, params, dry_run, verbose)
            
        else:
            # Security Hub disabled - show deactivation analysis
            if verbose:
                printc(GRAY, "🔍 Analyzing Security Hub for potential deactivation...")
            
            show_security_hub_deactivation_analysis(admin_account, security_account, regions, cross_account_role, verbose)
            
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_security_hub: {e}")
        return False


# Import required modules
import boto3
from botocore.exceptions import ClientError


def get_client(service: str, account_id: str, region: str, role_name: str):
    """
    Create a cross-account AWS client using role assumption.
    This matches the pattern used in other Foundation components.
    """
    try:
        sts_client = boto3.client('sts')
        
        # Assume role in the target account
        response = sts_client.assume_role(
            RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
            RoleSessionName=f"security_hub_setup_{account_id}"
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
        if verbose:
            printc(RED, f"    ❌ Failed to assume role in account {account_id}: {str(e)}")
        return None


def check_security_hub_delegation(admin_account: str, security_account: str, regions: list, verbose=False) -> dict:
    """Check Security Hub delegation status across organization."""
    if verbose:
        printc(GRAY, "🔍 Checking Security Hub delegation status...")
    
    delegation_info = {
        'is_delegated_to_security': False,
        'delegated_admin_account': None,
        'delegation_details': {},
        'errors': []
    }
    
    try:
        # Check from any region (delegation is organization-wide)
        orgs_client = boto3.client('organizations', region_name=regions[0])
        
        # Get delegated administrators for Security Hub
        response = orgs_client.list_delegated_administrators(ServicePrincipal='securityhub.amazonaws.com')
        delegated_admins = response.get('DelegatedAdministrators', [])
        
        for admin in delegated_admins:
            admin_id = admin.get('Id')
            delegation_info['delegation_details'][admin_id] = {
                'account_name': admin.get('Name', 'Unknown'),
                'status': admin.get('Status'),
                'joined_timestamp': admin.get('JoinedTimestamp')
            }
            
            if admin_id == security_account:
                delegation_info['is_delegated_to_security'] = True
                delegation_info['delegated_admin_account'] = admin_id
                
    except ClientError as e:
        error_msg = f"Failed to check Security Hub delegation: {str(e)}"
        delegation_info['errors'].append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error checking delegation: {str(e)}"
        delegation_info['errors'].append(error_msg)
    
    return delegation_info


def check_security_hub_in_region(region: str, admin_account: str, security_account: str, cross_account_role: str, verbose=False) -> dict:
    """Check Security Hub configuration in a specific region."""
    if verbose:
        printc(GRAY, f"    🌍 Analyzing Security Hub in region: {region}")
    
    hub_config = {
        'region': region,
        'hub_enabled': False,
        'hub_arn': None,
        'consolidated_controls_enabled': False,
        'auto_enable_controls': None,
        'finding_aggregation_status': None,
        'standards_subscriptions': [],
        'member_count': 0,
        'findings_transfer_configured': False,
        'main_region_aggregation': None,
        'errors': []
    }
    
    try:
        # Check from admin account first, then switch to delegated if available
        securityhub_client = boto3.client('securityhub', region_name=region)
        
        try:
            # Get hub details
            response = securityhub_client.describe_hub()
            hub_config['hub_enabled'] = True
            hub_config['hub_arn'] = response.get('HubArn')
            hub_config['auto_enable_controls'] = response.get('AutoEnableControls', False)
            
            # CRITICAL: Check consolidated controls status
            control_finding_generator = response.get('ControlFindingGenerator')
            hub_config['finding_aggregation_status'] = control_finding_generator
            hub_config['consolidated_controls_enabled'] = (control_finding_generator == 'SECURITY_CONTROL')
            
            if verbose:
                status = "✅ ENABLED" if hub_config['consolidated_controls_enabled'] else "❌ DISABLED"
                printc(GRAY, f"      🎯 Consolidated Controls: {status}")
                
                auto_status = "❌ ENABLED (should be disabled)" if hub_config['auto_enable_controls'] else "✅ DISABLED (correct)"
                printc(GRAY, f"      🔧 Auto Enable Controls: {auto_status}")
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidAccessException':
                if verbose:
                    printc(YELLOW, f"      ⚠️  Security Hub not enabled in region {region}")
            else:
                error_msg = f"Failed to describe hub: {str(e)}"
                hub_config['errors'].append(error_msg)
        
        # If hub is enabled, get detailed configuration (preferably from delegated admin)
        if hub_config['hub_enabled']:
            # Try to get client for delegated admin account
            delegated_client = get_client('securityhub', security_account, region, cross_account_role)
            client_to_use = delegated_client if delegated_client else securityhub_client
            
            # Get enabled standards
            try:
                standards_response = client_to_use.get_enabled_standards()
                hub_config['standards_subscriptions'] = standards_response.get('StandardsSubscriptions', [])
                
                if verbose and hub_config['standards_subscriptions']:
                    printc(GRAY, f"      📋 Standards enabled: {len(hub_config['standards_subscriptions'])}")
                    for standard in hub_config['standards_subscriptions']:
                        standard_arn = standard.get('StandardsArn', 'Unknown')
                        status = standard.get('StandardsStatus', 'Unknown')
                        
                        # Extract readable standard name from ARN
                        if 'aws-foundational-security-best-practices' in standard_arn:
                            standard_name = 'AWS Foundational Security Standard'
                        elif 'cis-aws-foundations-benchmark' in standard_arn:
                            standard_name = 'CIS AWS Foundations Benchmark'
                        elif 'nist-800-53' in standard_arn:
                            standard_name = 'NIST SP 800-53'
                        elif 'pci-dss' in standard_arn:
                            standard_name = 'PCI DSS'
                        elif 'aws-resource-tagging-standard' in standard_arn:
                            standard_name = 'AWS Resource Tagging Standard'
                        elif 'service-managed-standard' in standard_arn:
                            standard_name = 'Service-Managed Standard'
                        else:
                            # Fallback to extracting from ARN path
                            standard_name = standard_arn.split('/')[-2] if '/' in standard_arn else 'Unknown Standard'
                        
                        printc(GRAY, f"        - {standard_name}: {status}")
                        
            except ClientError as e:
                error_msg = f"Failed to get enabled standards: {str(e)}"
                hub_config['errors'].append(error_msg)
            
            # Get member accounts (requires pagination)
            try:
                members = []
                paginator = client_to_use.get_paginator('list_members')
                for page in paginator.paginate():
                    members.extend(page.get('Members', []))
                
                hub_config['member_count'] = len(members)
                
                if verbose:
                    printc(GRAY, f"      👥 Member accounts: {hub_config['member_count']}")
                    
            except ClientError as e:
                error_msg = f"Failed to list members: {str(e)}"
                hub_config['errors'].append(error_msg)
            
            # CRITICAL: Check finding aggregation configuration
            try:
                # Check if this region is configured to aggregate findings
                finding_aggregator_response = client_to_use.list_finding_aggregators()
                aggregators = finding_aggregator_response.get('FindingAggregators', [])
                
                if aggregators:
                    hub_config['findings_transfer_configured'] = True
                    for aggregator in aggregators:
                        hub_config['main_region_aggregation'] = {
                            'aggregator_arn': aggregator.get('FindingAggregatorArn'),
                            'region_linking_mode': aggregator.get('RegionLinkingMode'),
                            'regions': aggregator.get('Regions', [])
                        }
                        
                        if verbose:
                            mode = aggregator.get('RegionLinkingMode', 'Unknown')
                            regions_count = len(aggregator.get('Regions', []))
                            printc(GRAY, f"      🔄 Finding Aggregation: {mode} ({regions_count} regions)")
                else:
                    if verbose:
                        printc(YELLOW, f"      ⚠️  No finding aggregators configured")
                        
            except ClientError as e:
                error_msg = f"Failed to check finding aggregation: {str(e)}"
                hub_config['errors'].append(error_msg)
                    
    except Exception as e:
        error_msg = f"Unexpected error in region {region}: {str(e)}"
        hub_config['errors'].append(error_msg)
    
    return hub_config


def check_control_policies(regions: list, admin_account: str, security_account: str, cross_account_role: str, verbose=False) -> dict:
    """Check Security Hub control policies and configuration policy associations."""
    if verbose:
        printc(GRAY, "📋 Analyzing control policies and organizational assignments...")
    
    policies_data = {
        'configuration_policies': [],
        'policy_associations': [],
        'policy_count': 0,
        'association_count': 0,
        'prod_policy': None,
        'dev_policy': None,
        'org_root_policy': None,
        'ou_policies': [],
        'errors': []
    }
    
    # Use first region for policy discovery
    region = regions[0]
    
    try:
        # Get client for delegated admin account
        delegated_client = get_client('securityhub', security_account, region, cross_account_role)
        if not delegated_client:
            policies_data['errors'].append("Cannot access delegated admin account for policy discovery")
            return policies_data
        
        # Get configuration policies through associations (more reliable than list_configuration_policies)
        try:
            # First get all policy associations to find unique policy IDs
            associations_response = delegated_client.list_configuration_policy_associations()
            associations = associations_response.get('ConfigurationPolicyAssociationSummaries', [])
            policies_data['policy_associations'] = associations
            policies_data['association_count'] = len(associations)
            
            if verbose:
                printc(GRAY, f"    🔗 Policy associations found: {len(associations)}")
            
            # Extract unique policy IDs from associations
            unique_policy_ids = set()
            for assoc in associations:
                policy_id = assoc.get('ConfigurationPolicyId')
                if policy_id:
                    unique_policy_ids.add(policy_id)
            
            # Get details for each unique policy
            all_policies = []
            for policy_id in unique_policy_ids:
                try:
                    policy_detail = delegated_client.get_configuration_policy(Identifier=policy_id)
                    policy_summary = {
                        'Id': policy_id,
                        'Name': policy_detail.get('Name', 'Unknown'),
                        'Description': policy_detail.get('Description', ''),
                        'full_details': policy_detail
                    }
                    all_policies.append(policy_summary)
                    
                    if verbose:
                        printc(GRAY, f"    📋 Found policy: {policy_summary['Name']} ({policy_id})")
                    
                except Exception as e:
                    if verbose:
                        printc(GRAY, f"    ❌ Failed to get policy {policy_id}: {str(e)}")
            
            policies_data['configuration_policies'] = all_policies
            policies_data['policy_count'] = len(all_policies)
            
            # Analyze policies for PROD/DEV patterns
            for policy in all_policies:
                policy_name = policy.get('Name', '').lower()
                if any(indicator in policy_name for indicator in ['prod', 'production']):
                    policies_data['prod_policy'] = policy
                    if verbose:
                        printc(GRAY, f"    🏭 PROD policy identified: {policy['Name']}")
                elif any(indicator in policy_name for indicator in ['dev', 'development', 'sandbox']):
                    policies_data['dev_policy'] = policy
                    if verbose:
                        printc(GRAY, f"    🧪 DEV policy identified: {policy['Name']}")
                    
        except ClientError as e:
            error_msg = f"Failed to discover configuration policies: {str(e)}"
            policies_data['errors'].append(error_msg)
        
        # Analyze policy associations (already loaded above)
        if verbose and policies_data['policy_associations']:
            printc(GRAY, f"    🔗 Analyzing {len(policies_data['policy_associations'])} policy associations...")
            
            # Analyze associations for organizational structure
            for assoc in policies_data['policy_associations']:
                target = assoc.get('Target', {})
                policy_id = assoc.get('ConfigurationPolicyId', 'Unknown')
                association_type = assoc.get('AssociationType', 'Unknown')
                
                # Find policy name for this ID
                policy_name = 'Unknown'
                for policy in all_policies:
                    if policy['Id'] == policy_id:
                        policy_name = policy['Name']
                        break
                
                if 'RootId' in target:
                    policies_data['org_root_policy'] = {
                        'policy_id': policy_id,
                        'policy_name': policy_name,
                        'target_id': target.get('RootId'),
                        'association_type': association_type
                    }
                    if verbose:
                        printc(GRAY, f"      🌳 Root OU policy: {policy_name} → {target.get('RootId')}")
                elif 'OrganizationalUnitId' in target:
                    ou_policy = {
                        'policy_id': policy_id,
                        'policy_name': policy_name,
                        'ou_id': target.get('OrganizationalUnitId'),
                        'association_type': association_type
                    }
                    policies_data['ou_policies'].append(ou_policy)
                    if verbose:
                        printc(GRAY, f"      🏢 OU policy: {policy_name} → {target.get('OrganizationalUnitId')}")
            
    except Exception as e:
        error_msg = f"Unexpected error checking control policies: {str(e)}"
        policies_data['errors'].append(error_msg)
    
    return policies_data


def generate_security_hub_recommendations(delegation_status: dict, overall_config: dict, control_policies: dict, params: dict, dry_run: bool, verbose: bool):
    """Generate comprehensive Security Hub recommendations based on current configuration."""
    
    # Extract key information
    is_delegated = delegation_status.get('is_delegated_to_security', False)
    regions = params['regions']
    main_region = regions[0]  # First region is typically the main region
    
    # Check overall configuration status
    enabled_regions = [r for r, config in overall_config.items() if config.get('hub_enabled')]
    consolidated_controls_regions = [r for r, config in overall_config.items() if config.get('consolidated_controls_enabled')]
    auto_enable_issues = [r for r, config in overall_config.items() if config.get('auto_enable_controls', False)]
    
    # Analyze findings aggregation
    main_region_config = overall_config.get(main_region, {})
    findings_aggregated = main_region_config.get('findings_transfer_configured', False)
    
    # Generate status report
    if is_delegated and enabled_regions:
        if len(consolidated_controls_regions) == len(enabled_regions) and not auto_enable_issues and findings_aggregated:
            # Perfect configuration
            printc(GREEN, "✅ Security Hub is optimally configured for consolidated controls")
            printc(GREEN, f"✅ Consolidated controls enabled in all {len(enabled_regions)} regions")
            printc(GREEN, "✅ Auto-enable controls correctly disabled (manual control selection)")
            printc(GREEN, f"✅ Finding aggregation configured to main region ({main_region})")
            
            # Report policy status
            policy_count = control_policies.get('policy_count', 0)
            association_count = control_policies.get('association_count', 0)
            if policy_count > 0 and association_count > 0:
                printc(GREEN, f"✅ {policy_count} control policies with {association_count} organizational assignments")
                
                if control_policies.get('prod_policy') and control_policies.get('dev_policy'):
                    printc(GREEN, "✅ PROD and DEV control policies identified")
                elif policy_count >= 2:
                    printc(YELLOW, f"⚠️  {policy_count} policies found but PROD/DEV naming pattern not detected")
            else:
                printc(YELLOW, "⚠️  No configuration policies found - using consolidated controls with direct control management")
                printc(YELLOW, "    (This is normal when using consolidated controls without separate PROD/DEV policies)")
                
        else:
            # Configuration issues found
            printc(YELLOW, "⚠️  Security Hub configuration needs optimization:")
            
            if len(consolidated_controls_regions) < len(enabled_regions):
                missing_regions = [r for r in enabled_regions if r not in consolidated_controls_regions]
                printc(YELLOW, f"  • Enable consolidated controls in: {', '.join(missing_regions)}")
            
            if auto_enable_issues:
                printc(YELLOW, f"  • Disable auto-enable controls in: {', '.join(auto_enable_issues)}")
                printc(YELLOW, "    (Controls should be manually selected for proper PROD/DEV differentiation)")
            
            if not findings_aggregated:
                printc(YELLOW, f"  • Configure finding aggregation to main region ({main_region})")
                printc(YELLOW, "    (All findings from other regions should flow to main region)")
                
    elif is_delegated:
        printc(YELLOW, "⚠️  Security Hub delegated but not enabled in all regions")
        missing_regions = [r for r in regions if r not in enabled_regions]
        if missing_regions:
            printc(YELLOW, f"  • Enable Security Hub in: {', '.join(missing_regions)}")
            
    else:
        printc(YELLOW, "⚠️  Security Hub not delegated to security account")
        printc(YELLOW, f"  • Delegate Security Hub administration to account {params['security_account']}")
    
    # Show what would be done in dry-run mode
    if dry_run and (not is_delegated or len(enabled_regions) < len(regions) or auto_enable_issues or not findings_aggregated):
        printc(LIGHT_BLUE, "\n🔮 DRY RUN - Actions that would be taken:")
        
        if not is_delegated:
            printc(LIGHT_BLUE, "  • Delegate Security Hub to security administration account")
            
        missing_regions = [r for r in regions if r not in enabled_regions]
        if missing_regions:
            printc(LIGHT_BLUE, f"  • Enable Security Hub in regions: {', '.join(missing_regions)}")
            
        if len(consolidated_controls_regions) < len(regions):
            printc(LIGHT_BLUE, "  • Enable consolidated controls in all regions")
            
        if auto_enable_issues:
            printc(LIGHT_BLUE, "  • Disable auto-enable controls (ensure manual control selection)")
            
        if not findings_aggregated:
            printc(LIGHT_BLUE, f"  • Configure finding aggregation to main region ({main_region})")
            
        if control_policies.get('policy_count', 0) == 0:
            printc(LIGHT_BLUE, "  • Consider creating PROD and DEV control policies for organization-wide management")


def show_security_hub_deactivation_analysis(admin_account: str, security_account: str, regions: list, cross_account_role: str, verbose: bool):
    """Show Security Hub deactivation analysis when service is disabled."""
    printc(LIGHT_BLUE, "\n🔍 SECURITY HUB DEACTIVATION ANALYSIS")
    
    # Quick check of current state
    delegation_status = check_security_hub_delegation(admin_account, security_account, regions, verbose)
    
    if delegation_status.get('is_delegated_to_security'):
        printc(YELLOW, f"⚠️  Security Hub is currently delegated to account {security_account}")
        printc(YELLOW, "⚠️  Disabling will remove:")
        printc(YELLOW, "  • Consolidated security findings across all regions")
        printc(YELLOW, "  • Cross-region finding aggregation")
        printc(YELLOW, "  • Organization-wide control policies and compliance monitoring")
        printc(YELLOW, "  • Integration with GuardDuty, Config, Inspector, and other security services")
        
        enabled_regions = []
        for region in regions:
            try:
                client = boto3.client('securityhub', region_name=region)
                client.describe_hub()
                enabled_regions.append(region)
            except:
                pass
                
        if enabled_regions:
            printc(YELLOW, f"  • Active Security Hub configuration in {len(enabled_regions)} regions: {', '.join(enabled_regions)}")
            
        printc(GRAY, "\n💡 To properly deactivate Security Hub:")
        printc(GRAY, "  1. Document current control policies and organizational assignments")
        printc(GRAY, "  2. Export critical findings and compliance reports")
        printc(GRAY, "  3. Remove policy associations from organizational units")
        printc(GRAY, "  4. Delete control policies")
        printc(GRAY, "  5. Disable finding aggregation")
        printc(GRAY, "  6. Remove member accounts")
        printc(GRAY, "  7. Disable Security Hub in each region")
        printc(GRAY, "  8. Remove delegation from security account")
        
    else:
        printc(GREEN, "✅ Security Hub is not currently configured - no deactivation needed")