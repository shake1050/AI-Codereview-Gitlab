# -*- coding: utf-8 -*-
"""简单启动脚本"""
import subprocess
import sys
import psutil
import time

DEFAULT_PORT = 8501

def kill_process_on_port(port):
    """关闭占用指定端口的进程"""
    killed = False
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            connections = proc.info.get('connections')
            if connections:
                for conn in connections:
                    if hasattr(conn, 'laddr') and conn.laddr.port == port:
                        print(f"发现占用端口 {port} 的进程: {proc.info['name']} (PID: {proc.info['pid']})")
                        proc.kill()
                        killed = True
                        print(f"已终止进程 PID: {proc.info['pid']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed:
        print(f"等待端口 {port} 释放...")
        time.sleep(2)
    return killed

print("启动 AI Code Review 系统...")
print(f"检查端口 {DEFAULT_PORT} 是否被占用...")

# 清理占用端口的进程
if kill_process_on_port(DEFAULT_PORT):
    print(f"端口 {DEFAULT_PORT} 已清理完成")
else:
    print(f"端口 {DEFAULT_PORT} 未被占用")

print(f"\n访问地址: http://localhost:{DEFAULT_PORT}")
print(f"规则管理: http://localhost:{DEFAULT_PORT}/rule_management")
print("\n按 Ctrl+C 停止服务\n")

# 使用 python -m streamlit 方式启动，指定端口
subprocess.run([
    sys.executable, "-m", "streamlit", "run", "ui.py",
    "--server.port", str(DEFAULT_PORT),
    "--server.headless", "true"
])
