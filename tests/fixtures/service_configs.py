"""
Service-specific configuration test data for Foundation Security Services Setup.

This module provides test data for AWS security service configurations,
including existing setups that should be preserved during testing.
"""

# GuardDuty test configurations
GUARDDUTY_DETECTOR_CONFIG = {
    'DetectorId': 'test-detector-12345',
    'Status': 'ENABLED',
    'ServiceRole': 'arn:aws:iam::123456789012:role/aws-guardduty-service-role',
    'DataSources': {
        'CloudTrail': {'Status': 'ENABLED'},
        'DNSLogs': {'Status': 'ENABLED'},
        'FlowLogs': {'Status': 'ENABLED'},
        'S3Logs': {'Status': 'ENABLED'}
    }
}

GUARDDUTY_MEMBER_CONFIG = {
    'AccountId': '234567890123',
    'MasterId': '123456789012',
    'Email': 'security@example.com',
    'RelationshipStatus': 'Enabled',
    'InvitedAt': '2023-01-01T00:00:00Z',
    'UpdatedAt': '2023-01-01T00:00:00Z'
}

# Security Hub test configurations
SECURITY_HUB_ENABLED_CONFIG = {
    'HubArn': 'arn:aws:securityhub:us-east-1:123456789012:hub/default',
    'SubscribedAt': '2023-01-01T00:00:00Z'
}

SECURITY_HUB_STANDARDS = [
    {
        'StandardsArn': 'arn:aws:securityhub:us-east-1::ruleset/finding-format/aws-foundational-security-best-practices/v/1.0.0',
        'Name': 'AWS Foundational Security Best Practices v1.0.0',
        'Description': 'AWS Foundational Security Best Practices',
        'EnabledByDefault': True
    }
]

SECURITY_HUB_EXISTING_POLICIES = {
    'PROD': {
        'Id': 'test-prod-policy-123',
        'Name': 'PROD-Security-Policy',
        'Description': 'Production security controls policy'
    },
    'DEV': {
        'Id': 'test-dev-policy-456', 
        'Name': 'DEV-Security-Policy',
        'Description': 'Development security controls policy'
    }
}

# Detective test configurations
DETECTIVE_GRAPH_CONFIG = {
    'Arn': 'arn:aws:detective:us-east-1:123456789012:graph:123456789',
    'CreatedTime': '2023-01-01T00:00:00Z'
}

DETECTIVE_MEMBER_CONFIG = {
    'AccountId': '234567890123',
    'EmailAddress': 'security@example.com',
    'GraphArn': 'arn:aws:detective:us-east-1:123456789012:graph:123456789',
    'Status': 'ENABLED',
    'InvitedTime': '2023-01-01T00:00:00Z'
}

# Inspector test configurations
INSPECTOR_ENABLED_CONFIG = {
    'AccountId': '123456789012',
    'ResourceState': {
        'ec2': {'Status': 'ENABLED'},
        'ecr': {'Status': 'ENABLED'}
    },
    'State': {'Status': 'ENABLED'}
}

# Access Analyzer test configurations
ACCESS_ANALYZER_CONFIG = {
    'analyzerName': 'organization-analyzer',
    'analyzerArn': 'arn:aws:access-analyzer:us-east-1:123456789012:analyzer/organization-analyzer',
    'type': 'ORGANIZATION',
    'createdAt': '2023-01-01T00:00:00Z',
    'status': 'ACTIVE'
}

ACCESS_ANALYZER_UNUSED_CONFIG = {
    'analyzerName': 'unused-access-analyzer',
    'analyzerArn': 'arn:aws:access-analyzer:us-east-1:123456789012:analyzer/unused-access-analyzer',
    'type': 'ORGANIZATION_UNUSED_ACCESS',
    'createdAt': '2023-01-01T00:00:00Z',
    'status': 'ACTIVE'
}

# AWS Config test configurations
CONFIG_RECORDER_CONFIG = {
    'name': 'default',
    'roleARN': 'arn:aws:iam::123456789012:role/aws-config-role',
    'recordingGroup': {
        'allSupported': True,
        'includeGlobalResourceTypes': True,
        'resourceTypes': []
    }
}

CONFIG_DELIVERY_CHANNEL_CONFIG = {
    'name': 'default',
    's3BucketName': 'aws-config-bucket-123456789012-us-east-1',
    's3KeyPrefix': 'config',
    'configSnapshotDeliveryProperties': {
        'deliveryFrequency': 'TwentyFour_Hours'
    }
}

# Existing configuration scenarios for testing safety rules
EXISTING_CONFIGURATIONS = {
    'guardduty': {
        'detector_exists': True,
        'delegation_exists': True,
        'delegated_account': '234567890123'
    },
    'security_hub': {
        'enabled': True,
        'policies_exist': True,
        'prod_policy_exists': True,
        'dev_policy_exists': True
    },
    'detective': {
        'graph_exists': True,
        'delegation_exists': True
    },
    'inspector': {
        'enabled': True,
        'custom_schedule': True
    },
    'access_analyzer': {
        'org_analyzer_exists': True,
        'unused_analyzer_exists': True,
        'custom_scope': True
    },
    'config': {
        'recorder_exists': True,
        'delivery_channel_exists': True,
        'custom_settings': True
    }
}

def create_existing_service_config(service_name, scenario='default'):
    """
    Create existing service configuration for testing preservation logic.
    
    Args:
        service_name (str): Name of the AWS service
        scenario (str): Configuration scenario to simulate
        
    Returns:
        dict: Service configuration data
    """
    configs = {
        'guardduty': GUARDDUTY_DETECTOR_CONFIG,
        'security_hub': SECURITY_HUB_ENABLED_CONFIG,
        'detective': DETECTIVE_GRAPH_CONFIG,
        'inspector': INSPECTOR_ENABLED_CONFIG,
        'access_analyzer': ACCESS_ANALYZER_CONFIG,
        'config': CONFIG_RECORDER_CONFIG
    }
    
    return configs.get(service_name, {})