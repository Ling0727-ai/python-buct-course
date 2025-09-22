#!/usr/bin/env python3
"""
BUCT客户端演示
展示新的BUCTClient类的使用方法
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buct_course import BUCTClient

client = BUCTClient()
client.run_interactive()