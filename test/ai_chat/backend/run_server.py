#!/usr/bin/env python3
"""
React Agent 测试脚本
快速启动后端服务器
"""

import sys
import os

# 将 backend 目录添加到 Python 路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    import uvicorn
    from config import config
    
    print("=" * 60)
    print("🚀 启动 React Agent AI Chat 后端服务")
    print("=" * 60)
    print(f"📍 服务地址: http://{config.server.host}:{config.server.port}")
    print(f"🤖 模型: {config.llm.model}")
    print(f"🔧 默认模式: React Agent (支持多轮工具调用)")
    print("=" * 60)
    print("\n💡 提示:")
    print("  - 使用 React 模式: 支持多轮工具调用和复杂推理")
    print("  - 使用 Simple 模式: 单次工具调用")
    print("  - 前端地址: frontend/index.html")
    print("\n按 Ctrl+C 停止服务\n")
    
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        reload=True  # 开发模式，代码修改自动重载
    )
