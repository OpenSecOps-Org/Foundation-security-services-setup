"""
AWS Config setup module

Automates the manual steps:
1. In the Org account, enable AWS Config in your main region. Remove the 
   filter: in this region, you want to record IAM global events.
2. Enable AWS Config in your other enabled regions. Do not remove the IAM 
   global filter in these regions.
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

def setup_aws_config(enabled, params, dry_run, verbose):
    """Setup AWS Config in org account with proper IAM global event recording."""
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "AWS CONFIG SETUP")
        printc(LIGHT_BLUE, "="*60)
        
        if verbose:
            printc(GRAY, f"Enabled: {enabled}")
            printc(GRAY, f"Regions: {params.get('regions')}")
            printc(GRAY, f"Organization ID: {params.get('org_id')}")
            printc(GRAY, f"Dry Run: {dry_run}")
            printc(GRAY, f"Verbose: {verbose}")
        
        if enabled.lower() == 'yes':
            regions = params.get('regions', [])
            main_region = regions[0] if regions else 'unknown'
            other_regions = regions[1:] if len(regions) > 1 else []
            
            if dry_run:
                printc(YELLOW, f"DRY RUN: Would enable AWS Config in main region ({main_region}) - remove IAM global filter")
                if other_regions:
                    printc(YELLOW, f"DRY RUN: Would enable AWS Config in other regions ({other_regions}) - keep IAM global filter")
            else:
                printc(YELLOW, f"TODO: Enable AWS Config in main region ({main_region}) - remove IAM global filter")
                if other_regions:
                    printc(YELLOW, f"TODO: Enable AWS Config in other regions ({other_regions}) - keep IAM global filter")
        else:
            printc(GRAY, "AWS Config is disabled - skipping")
            
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_aws_config: {e}")
        return False