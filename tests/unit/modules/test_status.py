"""
Tests for standardized status data structures.

These tests ensure the new standardized status structures work correctly
and provide backward compatibility during the transition from legacy
service-specific field names to uniform field names.
"""

import pytest
from modules.utils import (
    ServiceRegionStatus,
    AnomalousRegionStatus,
    GuardDutyRegionStatus,
    SecurityHubRegionStatus,
    ConfigRegionStatus,
    AccessAnalyzerRegionStatus,
    DetectiveRegionStatus,
    InspectorRegionStatus,
    create_service_status,
    create_anomalous_status
)


class TestServiceRegionStatus:
    """Test the base ServiceRegionStatus dataclass."""
    
    def test_create_default_status(self):
        """Test creating status with minimal required fields."""
        status = ServiceRegionStatus(region='us-east-1')
        
        assert status.region == 'us-east-1'
        assert status.service_enabled is False
        assert status.delegation_status is None
        assert status.member_count == 0
        assert status.needs_changes is False
        assert status.issues == []
        assert status.actions == []
        assert status.errors == []
        assert status.service_details == []
    
    def test_create_full_status(self):
        """Test creating status with all fields populated."""
        status = ServiceRegionStatus(
            region='us-west-2',
            service_enabled=True,
            delegation_status='delegated',
            member_count=5,
            needs_changes=True,
            issues=['Issue 1', 'Issue 2'],
            actions=['Action 1'],
            errors=['Error 1'],
            service_details=['Detail 1', 'Detail 2']
        )
        
        assert status.region == 'us-west-2'
        assert status.service_enabled is True
        assert status.delegation_status == 'delegated'
        assert status.member_count == 5
        assert status.needs_changes is True
        assert status.issues == ['Issue 1', 'Issue 2']
        assert status.actions == ['Action 1']
        assert status.errors == ['Error 1']
        assert status.service_details == ['Detail 1', 'Detail 2']
    
    def test_to_dict_conversion(self):
        """Test converting status to dictionary."""
        status = ServiceRegionStatus(
            region='eu-west-1',
            service_enabled=True,
            delegation_status='not_delegated',
            needs_changes=True
        )
        
        result = status.to_dict()
        
        expected = {
            'region': 'eu-west-1',
            'service_enabled': True,
            'delegation_status': 'not_delegated',
            'member_count': 0,
            'needs_changes': True,
            'issues': [],
            'actions': [],
            'errors': [],
            'service_details': []
        }
        
        assert result == expected
    


class TestAnomalousRegionStatus:
    """Test the AnomalousRegionStatus dataclass."""
    
    def test_create_default_anomalous_status(self):
        """Test creating anomalous status with minimal fields."""
        status = AnomalousRegionStatus(region='us-east-1', resource_count=3)
        
        assert status.region == 'us-east-1'
        assert status.resource_count == 3
        assert status.resource_details == []
        assert status.account_details == []
    
    def test_create_full_anomalous_status(self):
        """Test creating anomalous status with all fields."""
        resource_details = [{'id': 'res-1'}, {'id': 'res-2'}]
        account_details = [{'account_id': '123456789012'}]
        
        status = AnomalousRegionStatus(
            region='eu-central-1',
            resource_count=2,
            resource_details=resource_details,
            account_details=account_details
        )
        
        assert status.region == 'eu-central-1'
        assert status.resource_count == 2
        assert status.resource_details == resource_details
        assert status.account_details == account_details
    
    def test_anomalous_to_dict_conversion(self):
        """Test converting anomalous status to dictionary."""
        status = AnomalousRegionStatus(
            region='ap-northeast-1',
            resource_count=1,
            resource_details=[{'name': 'test-resource'}],
            account_details=[{'account_id': '111111111111'}]
        )
        
        result = status.to_dict()
        
        expected = {
            'region': 'ap-northeast-1',
            'resource_count': 1,
            'resource_details': [{'name': 'test-resource'}],
            'account_details': [{'account_id': '111111111111'}]
        }
        
        assert result == expected


class TestServiceSpecificStatuses:
    """Test service-specific status extensions."""
    
    def test_guardduty_specific_fields(self):
        """Test GuardDuty-specific fields."""
        status = GuardDutyRegionStatus(
            region='us-east-1',
            service_enabled=True,
            organization_auto_enable=True
        )
        
        assert status.region == 'us-east-1'
        assert status.service_enabled is True
        assert status.organization_auto_enable is True
    
    def test_security_hub_specific_fields(self):
        """Test Security Hub-specific fields."""
        status = SecurityHubRegionStatus(
            region='us-west-2',
            service_enabled=True,
            hub_arn='arn:aws:securityhub:us-west-2:123456789012:hub/default',
            consolidated_controls_enabled=True,
            auto_enable_controls=False
        )
        
        assert status.region == 'us-west-2'
        assert status.service_enabled is True
        assert status.hub_arn == 'arn:aws:securityhub:us-west-2:123456789012:hub/default'
        assert status.consolidated_controls_enabled is True
        assert status.auto_enable_controls is False
    
    def test_config_specific_fields(self):
        """Test AWS Config-specific fields."""
        status = ConfigRegionStatus(
            region='us-east-1',
            service_enabled=True,
            records_global_iam=True
        )
        
        assert status.region == 'us-east-1'
        assert status.service_enabled is True
        assert status.records_global_iam is True
    
    def test_access_analyzer_specific_fields(self):
        """Test Access Analyzer-specific fields."""
        status = AccessAnalyzerRegionStatus(
            region='eu-west-1',
            service_enabled=True,
            external_analyzer_count=1,
            unused_analyzer_count=1
        )
        
        assert status.region == 'eu-west-1'
        assert status.service_enabled is True
        assert status.external_analyzer_count == 1
        assert status.unused_analyzer_count == 1
    
    def test_detective_specific_fields(self):
        """Test Detective-specific fields."""
        status = DetectiveRegionStatus(
            region='us-east-1',
            service_enabled=True,
            graph_arn='arn:aws:detective:us-east-1:123456789012:graph:123abc'
        )
        
        assert status.region == 'us-east-1'
        assert status.service_enabled is True
        assert status.graph_arn == 'arn:aws:detective:us-east-1:123456789012:graph:123abc'
    
    def test_inspector_specific_fields(self):
        """Test Inspector-specific fields."""
        status = InspectorRegionStatus(
            region='us-west-2',
            service_enabled=True,
            scan_types_enabled=2
        )
        
        assert status.region == 'us-west-2'
        assert status.service_enabled is True
        assert status.scan_types_enabled == 2


class TestFactoryFunctions:
    """Test factory functions for creating status objects."""
    
    def test_create_service_status_guardduty(self):
        """Test creating GuardDuty status via factory."""
        status = create_service_status('guardduty', 'us-east-1')
        
        assert isinstance(status, GuardDutyRegionStatus)
        assert status.region == 'us-east-1'
        assert status.service_enabled is False
        assert status.organization_auto_enable is False
    
    def test_create_service_status_security_hub(self):
        """Test creating Security Hub status via factory."""
        status = create_service_status('security_hub', 'us-west-2')
        
        assert isinstance(status, SecurityHubRegionStatus)
        assert status.region == 'us-west-2'
        assert status.service_enabled is False
        assert status.hub_arn is None
        assert status.consolidated_controls_enabled is False
    
    def test_create_service_status_config(self):
        """Test creating AWS Config status via factory."""
        status = create_service_status('aws_config', 'eu-west-1')
        
        assert isinstance(status, ConfigRegionStatus)
        assert status.region == 'eu-west-1'
        assert status.service_enabled is False
        assert status.records_global_iam is False
    
    def test_create_service_status_unknown_service(self):
        """Test creating status for unknown service returns base class."""
        status = create_service_status('unknown_service', 'ap-south-1')
        
        assert isinstance(status, ServiceRegionStatus)
        assert not isinstance(status, GuardDutyRegionStatus)  # Should be base class
        assert status.region == 'ap-south-1'
        assert status.service_enabled is False
    
    def test_create_anomalous_status(self):
        """Test creating anomalous status via factory."""
        status = create_anomalous_status('eu-central-1', resource_count=5)
        
        assert isinstance(status, AnomalousRegionStatus)
        assert status.region == 'eu-central-1'
        assert status.resource_count == 5
        assert status.resource_details == []
        assert status.account_details == []



class TestBackwardCompatibility:
    """Test that status structures maintain backward compatibility."""
    
    def test_to_dict_maintains_data_integrity(self):
        """Test that to_dict() preserves all data correctly."""
        original_status = ServiceRegionStatus(
            region='us-east-1',
            service_enabled=True,
            delegation_status='delegated',
            member_count=5,
            needs_changes=True,
            issues=['Issue 1', 'Issue 2'],
            actions=['Action 1'],
            errors=['Error 1'],
            service_details=['Detail 1', 'Detail 2']
        )
        
        # Convert to dict
        dict_form = original_status.to_dict()
        
        # Verify all fields are present and correct
        assert dict_form['region'] == original_status.region
        assert dict_form['service_enabled'] == original_status.service_enabled
        assert dict_form['delegation_status'] == original_status.delegation_status
        assert dict_form['member_count'] == original_status.member_count
        assert dict_form['needs_changes'] == original_status.needs_changes
        assert dict_form['issues'] == original_status.issues
        assert dict_form['actions'] == original_status.actions
        assert dict_form['errors'] == original_status.errors
        assert dict_form['service_details'] == original_status.service_details
    
    def test_list_modification_safety(self):
        """Test that modifying returned lists doesn't affect original status."""
        status = ServiceRegionStatus(
            region='us-west-2',
            issues=['Original issue'],
            actions=['Original action']
        )
        
        # Get dict representation
        status_dict = status.to_dict()
        
        # Modify the lists in the dict
        status_dict['issues'].append('Modified issue')
        status_dict['actions'].append('Modified action')
        
        # Original status should be unchanged
        assert status.issues == ['Original issue']
        assert status.actions == ['Original action']
        
        # Verify copies were made
        assert status_dict['issues'] == ['Original issue', 'Modified issue']
        assert status_dict['actions'] == ['Original action', 'Modified action']