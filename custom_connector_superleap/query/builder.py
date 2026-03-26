from typing import List, Dict, Any, Union
import logging

from custom_connector_sdk.connector.fields import FieldDataType
from custom_connector_sdk.connector.context import EntityDefinition
from custom_connector_queryfilter.queryfilter.parse_tree_builder import parse
import re
from datetime import datetime, timedelta

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

class QueryObject:
    """Stores parameters to be built into a Superleap query."""
    def __init__(self,
                 entity_identifier: str,
                 selected_field_names: List[str] = None,
                 filter_expression: str = None,
                 fields: List[str] = None,
                 next_token: str = None,
                 entity_definition: EntityDefinition = None):
        self.entity_identifier = entity_identifier
        self.selected_field_names = selected_field_names
        self.filter_expression = filter_expression
        self.fields = fields
        self.next_token = next_token
        self.entity_definition = entity_definition
    
    def __str__(self):
        return (f"QueryObject(object={self.entity_identifier}, fields={self.selected_field_names}, "
                f"filter={self.filter_expression}, next_token: {self.next_token}")




class SuperleapFilterParser:
    """Parse AppFlow filter expressions into Superleap filter format"""
    
    # Mapping from AppFlow operators to Superleap operators
    OPERATOR_MAP = {
        'EQUAL_TO': 'eq',
        'NOT_EQUAL_TO': 'neq',
        'CONTAINS': 'contains',
        'GREATER_THAN': 'gt',
        'GREATER_THAN_OR_EQUAL_TO': 'gte',
        'LESS_THAN': 'lt',
        'LESS_THAN_OR_EQUAL_TO': 'lte',
        'BETWEEN': 'between',
        'IN': 'in'
    }
    
    def __init__(self, replica_buffer_minutes: int = 0):
        """
        Initialize parser with optional replica buffer
        
        Args:
            replica_buffer_minutes: Minutes to subtract from start time for replica lag
        """
        self.replica_buffer_minutes = replica_buffer_minutes
    
    def parse(self, filter_expression: str) -> Dict[str, Any]:
        """
        Parse AppFlow filter expression into Superleap format
        Following the two-level nested structure:
        FilterType -> ConditionGroupType -> ConditionType
        
        Args:
            filter_expression: AppFlow filter string like "created_at between X and Y"
            
        Returns:
            Dict with Superleap filter format matching FilterType
        """
        if not filter_expression:
            LOGGER.info("No filter expression provided")
            return {}
        
        
        # Parse the conditions
        conditions = []
        
        # Handle BETWEEN operator (most common for incremental pulls)
        if 'between' in filter_expression.lower():
            conditions = self._parse_between(filter_expression)
        # Handle IN operator
        elif ' IN ' in filter_expression or ' in ' in filter_expression:
            conditions = self._parse_in(filter_expression)
        # Handle AND conditions
        elif ' and ' in filter_expression.lower():
            conditions = self._parse_and_conditions(filter_expression)
        # Handle OR conditions
        elif ' or ' in filter_expression.lower():
            conditions = self._parse_or_conditions(filter_expression)
        # Handle single comparison
        else:
            condition = self._parse_single_condition(filter_expression)
            if condition:
                conditions = [condition]
        
        # Build the two-level nested structure
        if not conditions:
            return {}
        
        # For BETWEEN, we need AND logic between the two conditions
        if len(conditions) > 1:
            # Multiple conditions from BETWEEN or explicit AND
            return {
                "and": [
                    {
                        "and": conditions
                    }
                ]
            }
        else:
            # Single condition
            return {
                "and": [
                    {
                        "and": conditions
                    }
                ]
            }
    
    def _parse_between(self, expression: str) -> List[Dict[str, Any]]:
        """
        Parse BETWEEN expression into two conditions (gte and lte)
        Example: "created_at between 2025-08-17T09:53:10.536Z and 2025-08-17T10:05:05.279Z"
        """
        pattern = r'(\w+)\s+between\s+([^\s]+)\s+and\s+([^\s]+)'
        match = re.match(pattern, expression, re.IGNORECASE)
        
        if not match:
            LOGGER.error(f"Failed to parse BETWEEN expression: {expression}")
            return []
        
        field = match.group(1)
        start_value = match.group(2)
        end_value = match.group(3)
        
        
        # Apply buffer for replica lag on timestamp fields
        if field in ['created_at', 'updated_at', 'deleted_at'] and self.replica_buffer_minutes > 0:
            start_value = self._add_buffer_to_timestamp(start_value)
        
        # Convert timestamps to epoch milliseconds if they're ISO format
        if self._is_iso_timestamp(start_value):
            start_value = self._iso_to_epoch_millis(start_value)
        if self._is_iso_timestamp(end_value):
            end_value = self._iso_to_epoch_millis(end_value)
        
        # Return two conditions for BETWEEN
        return [
            {
                "field": field,
                "operator": "gte",
                "value": start_value
            },
            {
                "field": field,
                "operator": "lte",
                "value": end_value
            }
        ]
    
    def _parse_in(self, expression: str) -> List[Dict[str, Any]]:
        """
        Parse IN expression
        Example: "status IN ('active', 'pending')"
        """
        pattern = r'(\w+)\s+IN\s*\(([^)]+)\)'
        match = re.match(pattern, expression, re.IGNORECASE)
        
        if not match:
            LOGGER.error(f"Failed to parse IN expression: {expression}")
            return []
        
        field = match.group(1)
        values_str = match.group(2)
        
        # Parse values (remove quotes and split by comma)
        values = [v.strip().strip("'\"") for v in values_str.split(',')]
        
        
        return [
            {
                "field": field,
                "operator": "in",
                "value": values  # Array for IN operator
            }
        ]
    
    def _parse_single_condition(self, expression: str) -> Dict[str, Any]:
        """
        Parse single comparison operator
        Examples:
        - "status EQUAL_TO 'active'"
        - "amount GREATER_THAN 100"
        - "email CONTAINS '@example.com'"
        """
        # Build pattern with all known operators
        operators = '|'.join(self.OPERATOR_MAP.keys())
        pattern = rf'(\w+)\s+({operators})\s+(.+)'
        match = re.match(pattern, expression, re.IGNORECASE)
        
        if not match:
            LOGGER.error(f"Failed to parse comparison expression: {expression}")
            return {}
        
        field = match.group(1)
        operator = match.group(2).upper()
        value = match.group(3).strip()
        
        # Remove quotes if present
        if value.startswith(("'", '"')) and value.endswith(("'", '"')):
            value = value[1:-1]
        
        # Handle data type conversion
        value = self._convert_value(field, value)
        
        
        # Convert operator to Superleap format
        superleap_operator = self.OPERATOR_MAP.get(operator, operator.lower())
        
        # Special handling for case-insensitive fields
        if field in ['name', 'email', 'phone'] and superleap_operator == 'eq':
            # Use leq (lower equal) for case-insensitive comparison
            superleap_operator = 'leq'
        
        # Handle CONTAINS operator (add wildcards if needed)
        if operator == 'CONTAINS' and isinstance(value, str):
            # For name, text, email, phone - use contains by default
            if field in ['name', 'email', 'phone', 'search_field']:
                if not value.startswith('%'):
                    value = f"%{value}"
                if not value.endswith('%'):
                    value = f"{value}%"
        
        return {
            "field": field,
            "operator": superleap_operator,
            "value": value
        }
    
    def _parse_and_conditions(self, expression: str) -> List[Dict[str, Any]]:
        """Parse multiple AND conditions"""
        conditions = []
        parts = expression.split(' and ', flags=re.IGNORECASE)
        
        for part in parts:
            condition = self._parse_single_condition(part.strip())
            if condition:
                conditions.append(condition)
        
        return conditions
    
    def _parse_or_conditions(self, expression: str) -> List[Dict[str, Any]]:
        """Parse multiple OR conditions - returns them for OR grouping"""
        conditions = []
        parts = expression.split(' or ', flags=re.IGNORECASE)
        
        for part in parts:
            condition = self._parse_single_condition(part.strip())
            if condition:
                conditions.append(condition)
        
        # For OR conditions, we need to restructure
        # This will be handled by the calling function
        return conditions
    
    def _is_iso_timestamp(self, value: str) -> bool:
        """Check if value is an ISO timestamp"""
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        return bool(re.match(iso_pattern, value))
    
    def _iso_to_epoch_millis(self, timestamp_str: str) -> int:
        """Convert ISO timestamp to epoch milliseconds"""
        try:
            # Parse ISO format
            if timestamp_str.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            else:
                dt = datetime.fromisoformat(timestamp_str)
            
            # Convert to epoch milliseconds
            epoch_millis = int(dt.timestamp() * 1000)
            return epoch_millis
        except Exception as e:
            LOGGER.error(f"Failed to convert timestamp {timestamp_str}: {e}")
            return timestamp_str
    
    def _add_buffer_to_timestamp(self, timestamp_str: str) -> str:
        """
        Subtract buffer time from timestamp for replica lag handling
        
        Args:
            timestamp_str: ISO format timestamp
            
        Returns:
            Modified timestamp string
        """
        try:
            # Parse ISO format
            if timestamp_str.endswith('Z'):
                dt = datetime.fromisoformat(timestamp_str[:-1] + '+00:00')
            else:
                dt = datetime.fromisoformat(timestamp_str)
            
            # Subtract buffer
            dt = dt - timedelta(minutes=self.replica_buffer_minutes)
            
            # Return in ISO format with Z suffix
            return dt.isoformat().replace('+00:00', 'Z')
        except Exception as e:
            LOGGER.error(f"Failed to add buffer to timestamp {timestamp_str}: {e}")
            return timestamp_str
    
    def _convert_value(self, field: str, value: str) -> Union[str, int, float, bool]:
        """Convert value based on field type"""
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            else:
                # Check if it's a timestamp field that needs epoch conversion
                if field in ['created_at', 'updated_at'] and self._is_iso_timestamp(value):
                    return self._iso_to_epoch_millis(value)
                return int(value)
        except ValueError:
            pass
        
        # Check for boolean
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Keep as string
        return value

def build_query(query_object: QueryObject) -> dict:
    """Build Superleap specific query given a QueryObject."""
    
    if not query_object.selected_field_names:
        LOGGER.error("No fields were selected for Superleap Query")
        raise ValueError('No fields were selected for Superleap Query')
    
    if query_object.next_token is not None and query_object.next_token != '':
        LOGGER.info(f"Using next token for pagination: {query_object.next_token}")

            # page = int(query_object.next_token)



    # Parse filter expression
    filters = {}
    if query_object.filter_expression:
        parser = SuperleapFilterParser(replica_buffer_minutes=0)
        filters = parser.parse(query_object.filter_expression)



    query_data = {
        "query": {
            "fields": query_object.selected_field_names,
            "filter": filters
        },
        "next_token": query_object.next_token
    }
    # Make sure the records are being ordered by created_at in ascending order by default so that the records are always properly retrieved.


    return query_data
