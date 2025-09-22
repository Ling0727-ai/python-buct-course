#!/usr/bin/env python3
"""
北化课程平台主程序
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from buct_course import BUCTClient

def main():
    """主程序入口"""
    print("=" * 60)
    print("🎓 北化课程平台 - 作业提醒系统")
    print("=" * 60)
    
    # 创建客户端
    client = BUCTClient()
    
    # 运行交互式客户端
    client.run_interactive()

if __name__ == "__main__":
    main()