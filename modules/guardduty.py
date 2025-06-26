"""
GuardDuty setup module

Automates the manual steps:
1. Enable GuardDuty in all your activated regions.
2. Delegate administration of GuardDuty to the Security-Adm account in 
   all your activated regions.
3. Log in to Security-Adm, enable and set up auto-enable in all your activated 
   regions.
"""

def setup_guardduty(enabled, accounts, dry_run, verbose):
    """Setup GuardDuty delegation and configuration."""
    try:
        print("\n" + "="*60)
        print("GUARDDUTY SETUP")
        print("="*60)
        print(f"Enabled: {enabled}")
        print(f"Dry Run: {dry_run}")
        print(f"Verbose: {verbose}")
        
        if enabled.lower() == 'yes':
            if dry_run:
                print("DRY RUN: Would enable GuardDuty in all activated regions")
                print("DRY RUN: Would delegate administration to Security-Adm account")
                print("DRY RUN: Would configure auto-enable in Security-Adm account")
            else:
                print("TODO: Enable GuardDuty in all activated regions")
                print("TODO: Delegate administration to Security-Adm account")
                print("TODO: Configure auto-enable in Security-Adm account")
        else:
            print("GuardDuty is disabled - skipping")
            
        return True
        
    except Exception as e:
        print(f"ERROR in setup_guardduty: {e}")
        return False