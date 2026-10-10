#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试任务状态监控和停止功能
"""

import sys
import os
import json
import time

# 添加core目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(current_dir, 'core')
sys.path.insert(0, core_dir)

from aipypro_run import create_aipy_client, print_status


def test_task_status_monitoring():
    """测试任务状态监控功能"""

    print("=" * 60)
    print("测试：任务状态监控和停止")
    print("=" * 60)
    print()

    # 创建AiPy客户端
    client = create_aipy_client()

    # 从命令行参数获取任务ID，或使用默认测试ID
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        print("请输入要监控的任务ID:")
        task_id = input().strip()

    if not task_id:
        print("错误: 任务ID不能为空")
        return

    print(f"开始监控任务: {task_id}")
    print("=" * 60)
    print()

    # 首先获取当前任务状态
    print_status("获取当前任务状态...", "📊")
    task_info = client.get_task_info(task_id)

    if task_info:
        print(f"任务ID: {task_info.get('id')}")
        print(f"任务标题: {task_info.get('title')}")
        print(f"任务状态: {task_info.get('state')}")
        print(f"使用模型: {task_info.get('model')}")
        print(f"工作目录: {task_info.get('workdir')}")
        print()
    else:
        print("无法获取任务信息")
        return

    # 判断任务是否已完成
    if client.is_task_completed(task_id):
        print_status("任务已完成", "✅")
        return

    print_status("任务未完成，开始等待...", "⏳")

    # 等待任务完成（每5秒检查一次，最多等待60秒）
    print_status("开始监控任务状态（每5秒检查一次）...", "👀")
    print()

    max_wait_time = 60  # 最多等待60秒
    check_interval = 5   # 每5秒检查一次
    elapsed = 0

    while elapsed < max_wait_time:
        time.sleep(check_interval)
        elapsed += check_interval

        # 获取任务状态
        task_info = client.get_task_info(task_id)
        if task_info:
            state = task_info.get("state", "UNKNOWN")
            print_status(f"任务状态: {state} ({elapsed}/{max_wait_time}秒)", "📊")

            # 判断是否完成
            if client.is_task_completed(task_id):
                print_status(f"任务执行完成!", "✅")
                print()
                print("=" * 60)
                print("任务已完成，无需停止")
                print("=" * 60)
                return

    # 如果超时，询问是否停止任务
    print()
    print("=" * 60)
    print(f"任务在{max_wait_time}秒内未完成")
    print("=" * 60)

    # 自动停止任务
    print_status("任务未完成，正在停止任务...", "⏹️")
    stop_success = client.stop_task(task_id)

    if stop_success:
        print_status("任务已成功停止", "✅")
    else:
        print_status("停止任务失败", "❌")


if __name__ == "__main__":
    try:
        test_task_status_monitoring()
    except KeyboardInterrupt:
        print_status("\n用户中断", "⚠️")
        sys.exit(0)
    except Exception as e:
        print_status(f"执行异常: {e}", "❌")
        import traceback
        traceback.print_exc()
        sys.exit(1)
