#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
任务结果解析模块
从AiPy任务工作目录读取task.html和task.json文件，解析任务执行结果
并更新到测试平台
"""

import os
import re
import json
import sys
import requests
import base64
from typing import Dict, Optional
from datetime import datetime

# 添加core目录到路径以导入platform模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def print_status(message: str, emoji: str = ""):
    """实时输出状态"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        if emoji:
            print(f"[{timestamp}] {emoji} {message}", flush=True)
        else:
            print(f"[{timestamp}] {message}", flush=True)
    except UnicodeEncodeError:
        if emoji:
            print(f"[{timestamp}] {message}", flush=True)
        else:
            print(f"[{timestamp}] {message}", flush=True)


class TaskResultParser:
    """任务结果解析器"""

    def __init__(self, task_id: str, workdir: str = None):
        """
        初始化任务结果解析器

        Args:
            task_id: AiPy任务ID
            workdir: 任务工作目录（可选，如果不提供则使用默认路径）
        """
        self.task_id = task_id
        self.workdir = workdir or self._get_default_workdir()
        self.task_html_path = os.path.join(self.workdir, "task.html")
        self.task_json_path = os.path.join(self.workdir, "task.json")

    def _get_default_workdir(self) -> str:
        """
        获取默认工作目录路径

        Returns:
            工作目录路径
        """
        # 可能的工作目录位置
        possible_paths = [
            # Windows默认路径
            os.path.join(os.path.expanduser("~"), "aipywork", self.task_id),
            # 桌面路径
            os.path.join(os.path.expanduser("~"), "Desktop", "anthropic_claude-sonnet-4.6", self.task_id),
            # 当前用户桌面路径
            os.path.join(os.path.expanduser("~"), "Desktop", "anthropic_claude-opus-4.6", self.task_id),
            os.path.join(os.path.expanduser("~"), "Desktop", "anthropic_claude-haiku-4.5", self.task_id),
        ]

        # 返回第一个存在的目录
        for path in possible_paths:
            if os.path.exists(path):
                return path

        # 如果都不存在，返回默认路径
        return possible_paths[0]

    def check_files_exist(self) -> Dict[str, bool]:
        """
        检查任务文件是否存在

        Returns:
            文件存在状态字典
        """
        return {
            "workdir": os.path.exists(self.workdir),
            "task.html": os.path.exists(self.task_html_path),
            "task.json": os.path.exists(self.task_json_path)
        }

    def parse_execution_time_and_tokens(self) -> Optional[Dict[str, any]]:
        """
        从task.html解析执行时间和tokens

        Returns:
            包含execution_time和tokens的字典，失败返回None
        """
        if not os.path.exists(self.task_html_path):
            print_status(f"task.html文件不存在: {self.task_html_path}", "❌")
            return None

        try:
            with open(self.task_html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 查找模式："结束处理指令 1 | 10s | Tokens: 8352 (⇧8192 + ⇩160)"
            # 使用正则表达式提取
            pattern = r'结束处理指令\s*\d+\s*\|\s*(\d+)s\s*\|\s*Tokens:\s*(\d+)\s*\('
            match = re.search(pattern, content)

            if match:
                execution_time = int(match.group(1))  # 秒
                tokens = int(match.group(2))

                return {
                    "execution_time": execution_time,
                    "tokens": tokens,
                    "execution_time_formatted": f"{execution_time}s"
                }
            else:
                print_status(f"未找到执行时间和tokens信息", "⚠️")
                return None

        except Exception as e:
            print_status(f"解析task.html异常: {e}", "❌")
            return None

    def read_task_json(self) -> Optional[Dict]:
        """
        读取task.json文件

        Returns:
            task.json内容字典，失败返回None
        """
        if not os.path.exists(self.task_json_path):
            print_status(f"task.json文件不存在: {self.task_json_path}", "❌")
            return None

        try:
            with open(self.task_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print_status(f"读取task.json异常: {e}", "❌")
            return None

    def get_task_result(self) -> Optional[Dict]:
        """
        获取完整的任务结果信息

        Returns:
            包含执行时间、tokens和task.json内容的字典
        """
        print_status(f"开始解析任务结果: {self.task_id}", "📊")

        # 检查文件存在性
        files_status = self.check_files_exist()
        if not files_status["workdir"]:
            print_status(f"工作目录不存在: {self.workdir}", "❌")
            return None

        print_status(f"工作目录: {self.workdir}", "📁")

        # 解析执行时间和tokens
        execution_result = self.parse_execution_time_and_tokens()

        # 读取task.json
        task_json = self.read_task_json()

        result = {
            "task_id": self.task_id,
            "workdir": self.workdir,
            "task_json_path": self.task_json_path  # 添加task.json路径
        }

        if execution_result:
            result.update(execution_result)
            print_status(f"执行时间: {execution_result['execution_time']}s", "⏱️")
            print_status(f"消耗Tokens: {execution_result['tokens']}", "📊")
        else:
            result["execution_time"] = None
            result["tokens"] = None

        if task_json:
            result["task_json"] = task_json
            print_status(f"task.json读取成功", "✅")
        else:
            result["task_json"] = None

        return result


def encode_file_to_base64(filepath: str) -> Optional[str]:
    """
    将文件编码为Base64格式

    Args:
        filepath: 文件路径

    Returns:
        Base64编码的字符串，失败返回None
    """
    if not os.path.exists(filepath):
        print_status(f"文件不存在: {filepath}", "❌")
        return None

    try:
        with open(filepath, 'rb') as f:
            file_content = f.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
            print_status(f"文件已编码为Base64，大小: {len(base64_content)} 字符", "📊")
            return base64_content
    except Exception as e:
        print_status(f"文件编码失败: {e}", "❌")
        return None


def update_platform_task_result(
    platform_api,
    row_id: str,
    aipy_task_id: str = None,
    execution_time: int = None,
    tokens: int = None,
    success: bool = True,
    failure_reason: str = "",
    task_json_path: str = None,
    judge_result: str = None,
    exec_status: str = None,
    judge_reason: str = None
) -> bool:
    """
    更新测试平台任务结果

    Args:
        platform_api: PlatformAPI实例
        row_id: 平台任务行ID
        aipy_task_id: AiPy任务ID
        execution_time: 执行时间（秒）
        tokens: 消耗的tokens
        success: 是否成功
        failure_reason: 失败原因
        task_json_path: task.json文件路径（可选，用于上传附件）
        judge_result: AI评判结果（"成功"/"失败"/"待定"）用于更新单选字段
        exec_status: 执行状态（"已完成"/"任务超时"/"执行失败"等，默认"已完成"）
        judge_reason: AI判断原因说明

    Returns:
        是否更新成功
    """
    print_status(f"正在更新平台任务结果: {row_id}", "📝")

    url = f"{platform_api.api_base}/editRow"
    controls = []

    # 添加AiPy任务ID
    if aipy_task_id:
        controls.append({
            "controlId": platform_api.FIELD_TASK_ID,
            "value": aipy_task_id
        })

    # 添加执行时间（数字类型）
    if execution_time is not None:
        controls.append({
            "controlId": platform_api.FIELD_EXEC_TIME,
            "value": execution_time
        })

    # 添加tokens（数字类型）
    if tokens is not None:
        controls.append({
            "controlId": platform_api.FIELD_TOKENS,
            "value": tokens
        })

    # 添加AI判断结果（单选字段）- 优先使用judge_result，否则使用success参数
    if judge_result:
        # judge_result是AI评判的结果（成功/失败/待定）
        controls.append({
            "controlId": platform_api.FIELD_SUCCESS,
            "value": judge_result,
            "valueType": 1
        })
        print_status(f"AI判断结果: {judge_result}", "⚖️")
    elif success is not None:
        # 如果没有judge_result，使用success参数
        success_value = "成功" if success else "失败"
        controls.append({
            "controlId": platform_api.FIELD_SUCCESS,
            "value": success_value,
            "valueType": 1
        })

    # 添加执行日期（当前日期，格式：2018-8-8）
    import datetime
    now = datetime.datetime.now()
    # Windows和Linux/Mac去除前导零的格式
    exec_date = now.strftime("%Y-%-m-%-d") if os.name != 'nt' else now.strftime("%Y-%#m-%#d")
    controls.append({
        "controlId": platform_api.FIELD_EXEC_DATE,
        "value": exec_date
    })
    print_status(f"执行日期: {exec_date}", "📅")

    # 添加失败原因
    if failure_reason:
        controls.append({
            "controlId": platform_api.FIELD_FAILURE_REASON,
            "value": failure_reason
        })

    # 添加AI判断原因说明
    if judge_reason and platform_api.FIELD_JUDGE_REASON:
        controls.append({
            "controlId": platform_api.FIELD_JUDGE_REASON,
            "value": judge_reason
        })
        print_status(f"AI判断原因: {judge_reason[:100]}...", "📝")

    # 更新执行状态（使用FIELD_EXEC_STATUS，单选字段需要valueType）
    # 如果配置了exec_status字段，则更新它；否则更新task_status字段（向后兼容）
    exec_status_field = platform_api.FIELD_EXEC_STATUS if platform_api.FIELD_EXEC_STATUS else platform_api.FIELD_TASK_STATUS
    status_value = exec_status if exec_status else "已完成"
    controls.append({
        "controlId": exec_status_field,
        "value": status_value,
        "valueType": 1
    })
    print_status(f"执行状态: {status_value}", "📋")

    # 上传task.json文件到附件字段
    if task_json_path and os.path.exists(task_json_path):
        print_status(f"检测到task.json文件: {task_json_path}", "📎")
        base64_content = encode_file_to_base64(task_json_path)
        if base64_content:
            filename = os.path.basename(task_json_path)
            controls.append({
                "controlId": platform_api.FIELD_ATTACHMENT,
                "valueType": "2",
                "editType": "0",
                "controlFiles": [
                    {
                        "baseFile": base64_content,
                        "fileName": filename
                    }
                ]
            })
            print_status(f"附件已准备上传: {filename}", "✅")

    payload = {
        "appKey": platform_api.app_key,
        "sign": platform_api.sign,
        "worksheetId": platform_api.worksheet_id,
        "rowId": row_id,
        "controls": controls,
        "triggerWorkflow": True
    }

    # ========== 开始更新到平台 ==========
    print_status(f"========== 开始更新测试平台 ==========", "🚀")
    print_status(f"更新URL: {url}", "🌐")
    print_status(f"Row ID: {row_id}", "📌")
    print_status(f"将更新 {len(controls)} 个字段:", "📋")
    for i, ctrl in enumerate(controls, 1):
        value_preview = str(ctrl.get('value', ''))[:50]
        print_status(f"  {i}. 字段ID: {ctrl['controlId']}, 值: {value_preview}", "→")
    print_status(f"====================================", "🚀")

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()

        # 检查响应（success=true表示成功）
        if result.get("success") or result.get("code") == 0:
            print_status(f"========== 平台任务结果更新成功 ==========", "✅")
            return True
        else:
            print_status(f"========== 平台任务结果更新失败 ==========", "❌")
            print_status(f"错误信息: {result.get('msg', result)}", "⚠️")
            return False

    except Exception as e:
        print_status(f"========== 平台任务结果更新异常 ==========", "❌")
        print_status(f"异常信息: {e}", "⚠️")
        return False


def parse_and_update_task_result(
    platform_api,
    aipy_task_id: str,
    row_id: str,
    judge_result: str = None,
    exec_status: str = None
) -> bool:
    """
    解析AiPy任务结果并更新到测试平台

    Args:
        platform_api: PlatformAPI实例
        aipy_task_id: AiPy任务ID
        row_id: 平台任务行ID
        judge_result: AI评判结果（可选，默认为"失败"）
        exec_status: 执行状态（可选，如"任务超时"、"执行失败"等，默认"已完成"）

    Returns:
        是否成功
    """
    print_status(f"开始处理任务结果: {aipy_task_id}", "🔄")

    # 解析任务结果
    result = parse_task_result(aipy_task_id)

    if not result:
        print_status(f"无法解析任务结果: {aipy_task_id}", "❌")
        return False

    execution_time = result.get("execution_time")
    tokens = result.get("tokens")
    task_json_path = result.get("task_json_path")  # 获取task.json路径

    print_status(f"任务执行时间: {execution_time}s, Tokens: {tokens}", "📊")

    # 更新到平台（包含附件上传）
    return update_platform_task_result(
        platform_api=platform_api,
        row_id=row_id,
        aipy_task_id=aipy_task_id,
        execution_time=execution_time,
        tokens=tokens,
        success=True,
        task_json_path=task_json_path,  # 传递task.json路径
        judge_result=judge_result or "失败",  # 传递judge_result，默认为失败
        exec_status=exec_status  # 传递自定义执行状态
    )


def parse_task_result(task_id: str, workdir: str = None) -> Optional[Dict]:
    """
    解析任务结果的便捷函数

    Args:
        task_id: AiPy任务ID
        workdir: 任务工作目录（可选）

    Returns:
        任务结果字典
    """
    parser = TaskResultParser(task_id, workdir)
    return parser.get_task_result()


# 兼容旧名称
def create_task_parser(task_id: str, workdir: str = None) -> TaskResultParser:
    """
    创建任务解析器的便捷函数（兼容旧名称）

    Args:
        task_id: AiPy任务ID
        workdir: 任务工作目录（可选）

    Returns:
        TaskResultParser实例
    """
    return TaskResultParser(task_id, workdir)


if __name__ == "__main__":
    # 测试代码
    import sys

    print("=" * 60)
    print("测试：任务结果解析")
    print("=" * 60)

    # 从命令行参数获取任务ID
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        print("请输入要解析的任务ID:")
        task_id = input().strip()

    if not task_id:
        print("错误: 任务ID不能为空")
        sys.exit(1)

    print()

    # 解析任务结果
    result = parse_task_result(task_id)

    if result:
        print()
        print("=" * 60)
        print("解析结果")
        print("=" * 60)
        print(f"任务ID: {result.get('task_id')}")
        print(f"工作目录: {result.get('workdir')}")
        print(f"执行时间: {result.get('execution_time')}s")
        print(f"消耗Tokens: {result.get('tokens')}")
        print(f"task.json存在: {result.get('task_json') is not None}")
        print("=" * 60)
    else:
        print("解析失败")
