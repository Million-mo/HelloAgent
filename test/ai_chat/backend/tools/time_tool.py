"""Time and date tool."""

from typing import Dict, Any
from datetime import datetime, timedelta
import datetime as dt
from .base import BaseTool


class TimeTool(BaseTool):
    """Tool for getting current time and date information."""
    
    @property
    def name(self) -> str:
        return "get_current_time"
    
    @property
    def description(self) -> str:
        return "Get current date and time information. Can return time in different timezones and formats."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone offset in hours, e.g. '+8' for Beijing, '+0' for UTC, '-5' for New York EST",
                    "default": "+8"
                },
                "output_format": {
                    "type": "string",
                    "description": "Output format: 'full' (详细), 'date' (仅日期), 'time' (仅时间), 'timestamp' (时间戳)",
                    "enum": ["full", "date", "time", "timestamp"],
                    "default": "full"
                }
            },
            "required": []
        }
    
    async def execute(self, timezone: str = "+8", output_format: str = "full", **kwargs) -> str:
        """
        Get current time information.
        
        Args:
            timezone: Timezone offset (default: +8 for Beijing)
            output_format: Output format
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Time information as string
        """
        try:
            # 解析时区偏移
            if timezone.startswith('+') or timezone.startswith('-'):
                offset_hours = int(timezone)
            else:
                offset_hours = int(timezone) if timezone else 8
            
            # 获取当前 UTC 时间并应用时区偏移
            utc_now = datetime.now(tz=dt.timezone.utc)
            local_time = utc_now + timedelta(hours=offset_hours)
            
            # 根据格式返回结果
            if output_format == "timestamp":
                return f"当前时间戳: {int(local_time.timestamp())}"
            elif output_format == "date":
                weekdays = ["一", "二", "三", "四", "五", "六", "日"]
                weekday = weekdays[local_time.weekday()]
                return local_time.strftime(f"%Y年%m月%d日 星期{weekday}")
            elif output_format == "time":
                return local_time.strftime("%H:%M:%S")
            else:  # full
                weekdays = ["一", "二", "三", "四", "五", "六", "日"]
                weekday = weekdays[local_time.weekday()]
                date_str = local_time.strftime(f"%Y年%m月%d日 星期{weekday}")
                time_str = local_time.strftime("%H:%M:%S")
                tz_str = f"UTC{timezone}" if timezone.startswith(('+', '-')) else f"UTC+{timezone}"
                return f"{date_str} {time_str} ({tz_str})"
                
        except ValueError:
            return f"错误：无效的时区偏移 '{timezone}'。请使用格式如 '+8', '-5' 等"
        except Exception as e:
            return f"错误：获取时间失败 - {str(e)}"
