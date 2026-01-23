"""
Admin & Security Manager for Splunk Slack Bot
Handles user authorization and audit logging
"""

import os
import logging
from datetime import datetime
from typing import Tuple, List

logger = logging.getLogger(__name__)


class AdminManager:
    """Manage admin access and security policies"""
    
    def __init__(self):
        # Get admin configuration
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        admin_channels_str = os.getenv("ADMIN_CHANNEL_IDS", "")
        
        # Parse comma-separated values and remove quotes
        self.admin_user_ids = [
            uid.strip().strip("'\"") 
            for uid in admin_ids_str.split(",") 
            if uid.strip().strip("'\"")
        ]
        self.admin_channel_ids = [
            cid.strip().strip("'\"")
            for cid in admin_channels_str.split(",")
            if cid.strip().strip("'\"")
        ]
        
        # Feature flags
        self.spl_query_enabled = os.getenv("ENABLE_SPL_QUERY", "true").lower() == "true"
        self.approval_required = os.getenv("REQUIRE_SPL_APPROVAL", "false").lower() == "true"
        
        logger.info(f"AdminManager initialized with {len(self.admin_user_ids)} admins: {self.admin_user_ids}")
    
    def is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        # Strip quotes from user_id as well, just in case
        clean_user_id = user_id.strip().strip("'\"")
        is_admin_result = clean_user_id in self.admin_user_ids
        logger.debug(f"Checking admin status for {clean_user_id}: {is_admin_result} (admin list: {self.admin_user_ids})")
        return is_admin_result
    
    def is_admin_channel(self, channel_id: str) -> bool:
        """Check if command is in admin-only channel"""
        return channel_id in self.admin_channel_ids
    
    def can_execute_spl(self, user_id: str, channel_id: str = None) -> Tuple[bool, str]:
        """
        Determine if user can execute SPL query
        
        Returns: (is_allowed, reason)
        """
        # Check if feature is enabled
        if not self.spl_query_enabled:
            return False, "SPL query execution is currently disabled"
        
        # Check if user is admin
        if not self.is_admin(user_id):
            return False, "❌ SPL queries are restricted to admins only"
        
        return True, "✅ Admin access granted"
    
    def audit_log(self, event_type: str, user_id: str, details: dict):
        """Log security events for audit trail"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "user_id": user_id,
            "details": details
        }
        
        logger.info(f"AUDIT: {event_type} | User: {user_id} | Details: {details}")
        
        # In production, also send to:
        # - Splunk logging
        # - CloudWatch/App Insights
        # - Slack admin channel
        return log_entry
    
    def get_admin_list(self) -> List[str]:
        """Get list of admin user IDs"""
        return self.admin_user_ids
    
    def add_admin(self, user_id: str):
        """Add user to admin list (runtime only, persist in .env)"""
        if user_id not in self.admin_user_ids:
            self.admin_user_ids.append(user_id)
            logger.info(f"Added admin: {user_id}")
    
    def remove_admin(self, user_id: str):
        """Remove user from admin list"""
        if user_id in self.admin_user_ids:
            self.admin_user_ids.remove(user_id)
            logger.info(f"Removed admin: {user_id}")
