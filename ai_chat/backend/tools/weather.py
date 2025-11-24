"""Weather tool implementation."""

from typing import Dict, Any
from .base import BaseTool


class WeatherTool(BaseTool):
    """Tool for querying weather information (mock data)."""
    
    # 模拟天气数据
    WEATHER_DATA = {
        "beijing": {"temp": "11", "condition": "晴天", "humidity": "30%", "wind": "西南风3级"},
        "shanghai": {"temp": "16", "condition": "多云", "humidity": "36%", "wind": "西风3级"},
        "hangzhou": {"temp": "15", "condition": "晴天", "humidity": "45%", "wind": "东风3级"},
        "shenzhen": {"temp": "22", "condition": "晴天", "humidity": "41%", "wind": "东北风3级"},
        "chengdu": {"temp": "12", "condition": "阴天", "humidity": "66%", "wind": "东北风3级"},
        "guangzhou": {"temp": "20", "condition": "晴天", "humidity": "50%", "wind": "东南风2级"},
        "nanjing": {"temp": "14", "condition": "多云", "humidity": "55%", "wind": "北风4级"},
        "wuhan": {"temp": "13", "condition": "阴天", "humidity": "60%", "wind": "东风3级"},
        "xian": {"temp": "10", "condition": "晴天", "humidity": "35%", "wind": "西北风4级"},
        "chongqing": {"temp": "14", "condition": "阴天", "humidity": "70%", "wind": "东北风2级"},
    }
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "Get weather information for major cities in China (demo with mock data)."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city name in Chinese or English, e.g. 北京, beijing, 上海, shanghai, 杭州, hangzhou"
                }
            },
            "required": ["location"]
        }
    
    async def execute(self, location: str, **kwargs) -> str:
        """
        Get weather for a location.
        
        Args:
            location: City name (Chinese or English)
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Weather information string
        """
        # 转换为小写英文进行查找
        location_key = self._normalize_location(location)
        
        if location_key in self.WEATHER_DATA:
            data = self.WEATHER_DATA[location_key]
            return (
                f"{location}天气：\n"
                f"天气状况: {data['condition']}\n"
                f"当前温度: {data['temp']}℃\n"
                f"相对湿度: {data['humidity']}\n"
                f"风力风向: {data['wind']}"
            )
        else:
            supported_cities = "北京(beijing)、上海(shanghai)、杭州(hangzhou)、深圳(shenzhen)、成都(chengdu)、广州(guangzhou)、南京(nanjing)、武汉(wuhan)、西安(xian)、重庆(chongqing)"
            return f"抱歉，没有 {location} 的天气数据。\n支持的城市：{supported_cities}"
    
    def _normalize_location(self, location: str) -> str:
        """
        Normalize location name to lowercase English key.
        
        Args:
            location: City name in Chinese or English
            
        Returns:
            Normalized key for lookup
        """
        # 中文城市名映射
        chinese_map = {
            "北京": "beijing",
            "上海": "shanghai",
            "杭州": "hangzhou",
            "深圳": "shenzhen",
            "成都": "chengdu",
            "广州": "guangzhou",
            "南京": "nanjing",
            "武汉": "wuhan",
            "西安": "xian",
            "重庆": "chongqing",
        }
        
        # 如果是中文，转换为英文
        if location in chinese_map:
            return chinese_map[location]
        
        # 如果是英文，转换为小写
        return location.lower().strip()
