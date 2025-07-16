"""
Cost Management System for SizeComparator

Tracks API usage costs, enforces spending limits, and provides cost alerts.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Single cost record for API usage."""
    timestamp: datetime
    provider: str
    service: str
    tokens_used: int
    cost_usd: float
    request_id: str
    model: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'provider': self.provider,
            'service': self.service,
            'tokens_used': self.tokens_used,
            'cost_usd': self.cost_usd,
            'request_id': self.request_id,
            'model': self.model
        }


@dataclass
class CostSummary:
    """Cost summary for a time period."""
    total_cost: float
    total_requests: int
    total_tokens: int
    provider_breakdown: Dict[str, float]
    service_breakdown: Dict[str, float]
    period_start: datetime
    period_end: datetime


class CostManager:
    """Manages API cost tracking and enforcement."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('cost_tracking_enabled', True)
        self.daily_limit = config.get('daily_cost_limit', 10.0)
        self.monthly_limit = config.get('monthly_cost_limit', 100.0)
        self.alert_threshold = config.get('cost_alert_threshold', 0.8)
        self.alert_email = config.get('cost_alert_email')
        
        # Storage for cost records
        self.cost_records: List[CostRecord] = []
        self.cost_file = Path("cost_tracking.json")
        self._alerts_sent = set()
        
        # Load existing records
        self._load_cost_records()
    
    def _load_cost_records(self):
        """Load cost records from persistent storage."""
        if not self.cost_file.exists():
            return
            
        try:
            with open(self.cost_file, 'r') as f:
                data = json.load(f)
                
            for record_data in data.get('records', []):
                record = CostRecord(
                    timestamp=datetime.fromisoformat(record_data['timestamp']),
                    provider=record_data['provider'],
                    service=record_data['service'],
                    tokens_used=record_data['tokens_used'],
                    cost_usd=record_data['cost_usd'],
                    request_id=record_data['request_id'],
                    model=record_data.get('model', '')
                )
                self.cost_records.append(record)
                
        except Exception as e:
            logger.warning(f"Failed to load cost records: {e}")
    
    def _save_cost_records(self):
        """Save cost records to persistent storage."""
        try:
            # Keep only last 30 days of records
            cutoff_date = datetime.now() - timedelta(days=30)
            recent_records = [r for r in self.cost_records if r.timestamp >= cutoff_date]
            
            data = {
                'records': [record.to_dict() for record in recent_records],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.cost_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.cost_records = recent_records
            
        except Exception as e:
            logger.error(f"Failed to save cost records: {e}")
    
    async def record_cost(
        self,
        provider: str,
        service: str,
        tokens_used: int,
        cost_usd: float,
        request_id: str,
        model: str = ""
    ) -> bool:
        """Record a cost entry and check limits."""
        if not self.enabled:
            return True
            
        # Create cost record
        record = CostRecord(
            timestamp=datetime.now(),
            provider=provider,
            service=service,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            request_id=request_id,
            model=model
        )
        
        self.cost_records.append(record)
        
        # Check limits
        within_limits = await self._check_cost_limits(record)
        
        # Save periodically
        if len(self.cost_records) % 10 == 0:
            self._save_cost_records()
        
        return within_limits
    
    async def _check_cost_limits(self, new_record: CostRecord) -> bool:
        """Check if current usage is within limits."""
        now = datetime.now()
        
        # Check daily limit
        daily_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_cost = sum(
            r.cost_usd for r in self.cost_records 
            if r.timestamp >= daily_start
        )
        
        if daily_cost > self.daily_limit:
            await self._send_alert(f"Daily cost limit exceeded: ${daily_cost:.2f} > ${self.daily_limit:.2f}")
            return False
            
        # Check monthly limit
        monthly_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_cost = sum(
            r.cost_usd for r in self.cost_records 
            if r.timestamp >= monthly_start
        )
        
        if monthly_cost > self.monthly_limit:
            await self._send_alert(f"Monthly cost limit exceeded: ${monthly_cost:.2f} > ${self.monthly_limit:.2f}")
            return False
        
        # Check alert thresholds
        daily_threshold = self.daily_limit * self.alert_threshold
        monthly_threshold = self.monthly_limit * self.alert_threshold
        
        if daily_cost > daily_threshold and "daily_threshold" not in self._alerts_sent:
            await self._send_alert(f"Daily cost threshold reached: ${daily_cost:.2f} (${daily_threshold:.2f} threshold)")
            self._alerts_sent.add("daily_threshold")
            
        if monthly_cost > monthly_threshold and "monthly_threshold" not in self._alerts_sent:
            await self._send_alert(f"Monthly cost threshold reached: ${monthly_cost:.2f} (${monthly_threshold:.2f} threshold)")
            self._alerts_sent.add("monthly_threshold")
        
        return True
    
    async def _send_alert(self, message: str):
        """Send cost alert (placeholder for email/webhook)."""
        logger.warning(f"COST ALERT: {message}")
        
        # In production, this would send email/webhook
        if self.alert_email:
            logger.info(f"Would send alert to {self.alert_email}: {message}")
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> CostSummary:
        """Get cost summary for a specific day."""
        if date is None:
            date = datetime.now()
        
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        return self._get_summary(day_start, day_end)
    
    def get_monthly_summary(self, date: Optional[datetime] = None) -> CostSummary:
        """Get cost summary for a specific month."""
        if date is None:
            date = datetime.now()
        
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        
        return self._get_summary(month_start, month_end)
    
    def _get_summary(self, start: datetime, end: datetime) -> CostSummary:
        """Get cost summary for a time period."""
        period_records = [
            r for r in self.cost_records 
            if start <= r.timestamp < end
        ]
        
        if not period_records:
            return CostSummary(
                total_cost=0.0,
                total_requests=0,
                total_tokens=0,
                provider_breakdown={},
                service_breakdown={},
                period_start=start,
                period_end=end
            )
        
        total_cost = sum(r.cost_usd for r in period_records)
        total_requests = len(period_records)
        total_tokens = sum(r.tokens_used for r in period_records)
        
        provider_breakdown = {}
        service_breakdown = {}
        
        for record in period_records:
            provider_breakdown[record.provider] = provider_breakdown.get(record.provider, 0) + record.cost_usd
            service_breakdown[record.service] = service_breakdown.get(record.service, 0) + record.cost_usd
        
        return CostSummary(
            total_cost=total_cost,
            total_requests=total_requests,
            total_tokens=total_tokens,
            provider_breakdown=provider_breakdown,
            service_breakdown=service_breakdown,
            period_start=start,
            period_end=end
        )
    
    def get_current_limits_status(self) -> Dict[str, Any]:
        """Get current status relative to limits."""
        daily_summary = self.get_daily_summary()
        monthly_summary = self.get_monthly_summary()
        
        return {
            'daily': {
                'current_cost': daily_summary.total_cost,
                'limit': self.daily_limit,
                'percentage': (daily_summary.total_cost / self.daily_limit) * 100 if self.daily_limit > 0 else 0,
                'requests': daily_summary.total_requests
            },
            'monthly': {
                'current_cost': monthly_summary.total_cost,
                'limit': self.monthly_limit,
                'percentage': (monthly_summary.total_cost / self.monthly_limit) * 100 if self.monthly_limit > 0 else 0,
                'requests': monthly_summary.total_requests
            }
        }
    
    def cleanup(self):
        """Clean up resources."""
        if self.cost_records:
            self._save_cost_records()