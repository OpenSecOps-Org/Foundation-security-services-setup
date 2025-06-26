"""
AWS Config setup module

Automates the manual steps:
1. In the Org account, enable AWS Config in your main region. Remove the 
   filter: in this region, you want to record IAM global events.
2. Enable AWS Config in your other enabled regions. Do not remove the IAM 
   global filter in these regions.
"""

def setup_aws_config(enabled, accounts, dry_run, verbose):
    """Setup AWS Config in org account with proper IAM global event recording."""
    try:
        print("\n" + "="*60)
        print("AWS CONFIG SETUP")
        print("="*60)
        print(f"Enabled: {enabled}")
        print(f"Dry Run: {dry_run}")
        print(f"Verbose: {verbose}")
        
        if enabled.lower() == 'yes':
            if dry_run:
                print("DRY RUN: Would enable AWS Config in main region (remove IAM global filter)")
                print("DRY RUN: Would enable AWS Config in other regions (keep IAM global filter)")
            else:
                print("TODO: Enable AWS Config in main region, remove IAM global filter")
                print("TODO: Enable AWS Config in other regions, keep IAM global filter")
        else:
            print("AWS Config is disabled - skipping")
            
        return True
        
    except Exception as e:
        print(f"ERROR in setup_aws_config: {e}")
        return False