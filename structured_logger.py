"""
Structured Logging System for Splunk Query Bot
Records all actions with clear format: timestamp, user, command, channel, action, result, changes
"""

import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Log actions in structured format for audit trail and export"""
    
    def __init__(self, log_file: str = "bot_audit.log"):
        self.log_file = log_file
        self.logs: List[Dict[str, Any]] = []
        self.load_logs()
    
    def load_logs(self):
        """Load existing logs from file"""
        if Path(self.log_file).exists():
            try:
                with open(self.log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                self.logs.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                logger.error(f"Error loading logs: {e}")
    
    def log_action(self, 
                   user_id: str,
                   user_name: str,
                   command: str,
                   channel_id: str,
                   channel_name: str,
                   action: str,
                   result: str,
                   changes: Dict[str, Any] = None,
                   error: str = None):
        """
        Log an action with full details
        
        Args:
            user_id: Slack user ID
            user_name: Slack user name
            command: Command executed (e.g., "!admin-add")
            channel_id: Channel ID where command was run
            channel_name: Channel name
            action: What was done (e.g., "Added admin user")
            result: Success/Failure status
            changes: Dict of config changes made
            error: Error message if failed
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_name": user_name,
            "command": command,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "action": action,
            "result": result,
            "changes": changes or {},
            "error": error
        }
        
        self.logs.append(log_entry)
        
        # Write to file
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Error writing log: {e}")
        
        # Also print readable format to console/logger
        self._print_readable(log_entry)
    
    def _print_readable(self, entry: Dict[str, Any]):
        """Print log in readable format"""
        timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # HH:MM:SS
        date = entry['timestamp'].split('T')[0]  # YYYY-MM-DD
        
        message = (
            f"\n{'='*70}\n"
            f"📋 LOG ENTRY\n"
            f"{'='*70}\n"
            f"⏰ When:    {date} {timestamp}\n"
            f"👤 Who:     {entry['user_name']} ({entry['user_id']})\n"
            f"💬 Where:   {entry['channel_name']} ({entry['channel_id']})\n"
            f"🎯 Command: {entry['command']}\n"
            f"📝 Action:  {entry['action']}\n"
            f"✅ Result:  {entry['result']}\n"
        )
        
        if entry['changes']:
            message += f"🔄 Changes: {json.dumps(entry['changes'], indent=2)}\n"
        
        if entry['error']:
            message += f"⚠️  Error:   {entry['error']}\n"
        
        message += f"{'='*70}\n"
        logger.info(message)
    
    def export_json(self, output_file: str = "logs_export.json") -> str:
        """Export logs as JSON"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.logs, f, indent=2)
            return output_file
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            return None
    
    def export_csv(self, output_file: str = "logs_export.csv") -> str:
        """Export logs as CSV"""
        if not self.logs:
            return None
        
        try:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        'timestamp', 'user_id', 'user_name', 'command',
                        'channel_id', 'channel_name', 'action', 'result',
                        'changes', 'error'
                    ]
                )
                writer.writeheader()
                for log in self.logs:
                    log['changes'] = json.dumps(log.get('changes', {}))
                    writer.writerow(log)
            return output_file
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return None
    
    def export_txt(self, output_file: str = "logs_export.txt") -> str:
        """Export logs as readable text"""
        try:
            with open(output_file, 'w') as f:
                f.write("SPLUNK QUERY BOT - AUDIT LOG EXPORT\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Total Entries: {len(self.logs)}\n")
                f.write("="*80 + "\n\n")
                
                for entry in self.logs:
                    timestamp = entry['timestamp'].split('T')[1].split('.')[0]
                    date = entry['timestamp'].split('T')[0]
                    
                    f.write(f"Date/Time:  {date} {timestamp}\n")
                    f.write(f"User:       {entry['user_name']} ({entry['user_id']})\n")
                    f.write(f"Channel:    {entry['channel_name']} ({entry['channel_id']})\n")
                    f.write(f"Command:    {entry['command']}\n")
                    f.write(f"Action:     {entry['action']}\n")
                    f.write(f"Result:     {entry['result']}\n")
                    
                    if entry['changes']:
                        f.write(f"Changes:    {json.dumps(entry['changes'])}\n")
                    
                    if entry['error']:
                        f.write(f"Error:      {entry['error']}\n")
                    
                    f.write("-"*80 + "\n\n")
            
            return output_file
        except Exception as e:
            logger.error(f"Error exporting TXT: {e}")
            return None
    
    def get_user_logs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific user"""
        return [log for log in self.logs if log['user_id'] == user_id]
    
    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent logs"""
        return self.logs[-limit:]
    
    def get_logs_by_command(self, command: str) -> List[Dict[str, Any]]:
        """Get logs for a specific command"""
        return [log for log in self.logs if log['command'] == command]
