"""
AWS parameter test data for Foundation Security Services Setup tests.

This module provides standardized test data for AWS accounts, regions, and
configuration parameters used across all test suites.
"""

def create_test_params(
    admin_account='123456789012',
    security_account='234567890123',
    regions=None,
    cross_account_role='AWSControlTowerExecution',
    org_id='o-example12345',
    root_ou='r-example12345'
):
    """
    Create standardized test parameters for security services setup.
    
    Args:
        admin_account (str): Organization management account ID
        security_account (str): Security administration account ID
        regions (list): List of AWS regions (main region first)
        cross_account_role (str): Cross-account role name
        org_id (str): AWS Organization ID
        root_ou (str): Root organizational unit ID
        
    Returns:
        dict: Standardized parameter dictionary
    """
    if regions is None:
        regions = ['us-east-1', 'us-west-2', 'eu-west-1']
    
    return {
        'admin_account': admin_account,
        'security_account': security_account,
        'regions': regions,
        'cross_account_role': cross_account_role,
        'org_id': org_id,
        'root_ou': root_ou
    }

def create_service_flags(
    aws_config='Yes',
    guardduty='Yes', 
    security_hub='Yes',
    access_analyzer='Yes',
    detective='No',
    inspector='No'
):
    """
    Create standardized service enable/disable flags.
    
    Args:
        aws_config (str): Enable AWS Config ('Yes'/'No')
        guardduty (str): Enable GuardDuty ('Yes'/'No')
        security_hub (str): Enable Security Hub ('Yes'/'No')
        access_analyzer (str): Enable Access Analyzer ('Yes'/'No')
        detective (str): Enable Detective ('Yes'/'No')
        inspector (str): Enable Inspector ('Yes'/'No')
        
    Returns:
        dict: Service flag dictionary
    """
    return {
        'aws_config': aws_config,
        'guardduty': guardduty,
        'security_hub': security_hub,
        'access_analyzer': access_analyzer,
        'detective': detective,
        'inspector': inspector
    }

# Common test scenarios
VALID_ACCOUNT_IDS = [
    '123456789012', 
    '234567890123', 
    '345678901234',
    '456789012345'
]

VALID_REGIONS = [
    ['us-east-1'],
    ['us-east-1', 'us-west-2'],
    ['us-east-1', 'us-west-2', 'eu-west-1'],
    ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
]

VALID_ORG_IDS = [
    'o-example12345',
    'o-test987654321',
    'o-prod1234567890'
]

VALID_ROOT_OUS = [
    'r-example12345',
    'r-test987654321', 
    'r-prod1234567890'
]

# Invalid test data for negative testing
INVALID_ACCOUNT_IDS = [
    '12345',        # Too short
    '1234567890123',  # Too long
    'abc123456789',   # Non-numeric
    '',             # Empty
    None            # None value
]

INVALID_REGIONS = [
    [],             # Empty list
    ['invalid-region'],  # Invalid region name
    ['us-east-1', ''],   # Empty region in list
    None            # None value
]

INVALID_ORG_IDS = [
    'invalid-org',  # Wrong format
    'o-',           # Too short
    '',             # Empty
    None            # None value
]