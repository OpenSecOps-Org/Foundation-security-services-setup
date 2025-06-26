"""
GuardDuty setup module

Automates the manual steps:
1. Enable GuardDuty in all your activated regions.
2. Delegate administration of GuardDuty to the Security-Adm account in 
   all your activated regions.
3. Log in to Security-Adm, enable and set up auto-enable in all your activated 
   regions.
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

def setup_guardduty(enabled, accounts, dry_run, verbose):
    """Setup GuardDuty delegation and configuration."""
    try:
        printc(LIGHT_BLUE, "\n" + "="*60)
        printc(LIGHT_BLUE, "GUARDDUTY SETUP")
        printc(LIGHT_BLUE, "="*60)
        
        if verbose:
            printc(GRAY, f"Enabled: {enabled}")
            printc(GRAY, f"Dry Run: {dry_run}")
            printc(GRAY, f"Verbose: {verbose}")
        
        if enabled.lower() == 'yes':
            if dry_run:
                printc(YELLOW, "DRY RUN: Would enable GuardDuty in all activated regions")
                printc(YELLOW, "DRY RUN: Would delegate administration to Security-Adm account")
                printc(YELLOW, "DRY RUN: Would configure auto-enable in Security-Adm account")
            else:
                printc(YELLOW, "TODO: Enable GuardDuty in all activated regions")
                printc(YELLOW, "TODO: Delegate administration to Security-Adm account")
                printc(YELLOW, "TODO: Configure auto-enable in Security-Adm account")
        else:
            printc(GRAY, "GuardDuty is disabled - skipping")
            
        return True
        
    except Exception as e:
        printc(RED, f"ERROR in setup_guardduty: {e}")
        return False