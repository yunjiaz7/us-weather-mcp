#!/usr/bin/env python3
"""全美天气查询 MCP 服务器 - 基于 FastMCP"""
import httpx
import json
from datetime import datetime
from typing import Any
from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP 服务器
mcp = FastMCP("us-weather-server")

def c_to_f(celsius: float) -> float:
    """摄氏度转华氏度公式: F = C * 9/5 + 32"""
    return (celsius * 9 / 5) + 32

@mcp.tool()
async def get_us_weather(city_query: str) -> str:
    """
    获取美国指定城市的天气。
    Args:
        city_query: 城市名称，建议格式为 "City" 或 "City, State" (例如 "San Jose, CA" 或 "New York").
    """
    # 处理空格，适应 URL
    formatted_query = city_query.replace(" ", "+")
    # 使用 wttr.in 获取 JSON 格式数据
    url = f"https://wttr.in/{formatted_query}?format=j1"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            current = data["current_condition"][0]
            
            # 数据提取与单位转换
            temp_c = float(current["temp_C"])
            feels_like_c = float(current["FeelsLikeC"])
            
            weather_info = {
                "city": city_query,
                "temperature": {
                    "celsius": temp_c,
                    "fahrenheit": round(c_to_f(temp_c), 1)
                },
                "feels_like": {
                    "celsius": feels_like_c,
                    "fahrenheit": round(c_to_f(feels_like_c), 1)
                },
                "humidity": int(current["humidity"]),
                "condition": current["weatherDesc"][0]["value"],
                # wttr.in 返回 kmph，转换为 m/s
                "wind_speed_ms": round(float(current["windspeedKmph"]) / 3.6, 1),
                "visibility_km": float(current["visibility"]),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "US Weather MCP"
            }
            
            return json.dumps(weather_info, indent=2, ensure_ascii=False)
            
        except httpx.HTTPStatusError:
            return json.dumps({"error": f"无法找到城市: {city_query}", "status": "failed"})
        except Exception as e:
            return json.dumps({"error": str(e), "status": "error"})

if __name__ == "__main__":
    mcp.run(transport='stdio')