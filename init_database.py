# -*- coding: utf-8 -*-
"""数据库初始化脚本"""
import os
from pathlib import Path

# 设置项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
os.environ['PROJECT_ROOT'] = str(PROJECT_ROOT)

print("初始化数据库...")

# 导入服务会自动触发数据库初始化
from biz.service.review_service import ReviewService
from biz.service.rule_service import RuleService

print("✓ 数据库初始化完成")
print("✓ 规则表已创建")
print("✓ 规则已从YAML导入")
