#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试任务自动执行主程序
从测试平台获取待执行任务，并在AiPy客户端创建并执行任务
"""

import sys
import os
import json
import time
import threading

# 添加core目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.join(current_dir, 'core')
sys.path.insert(0, core_dir)

from platform import create_platform_api, print_status
from aipypro_run import create_aipy_client
from updata import parse_and_update_task_result, parse_task_result, update_platform_task_result
from jude_task import create_task_judge


# 全局变量用于存储正在运行的任务
running_tasks = {}  # {task_id: {"name": task_name, "start_time": start_time, "row_id": row_id}}
monitoring_active = True


def monitor_task_status(aipy_client, platform_api, task_judge, task_id, task_name, row_id, timeout_seconds):
    """
    监控任务状态的线程函数

    Args:
        aipy_client: AiPy客户端实例
        platform_api: PlatformAPI实例
        task_judge: 任务评判器实例
        task_id: 任务ID
        task_name: 任务名称
        row_id: 平台任务行ID
        timeout_seconds: 监控超时时间（秒）
    """
    global monitoring_active

    try:
        start_time = time.time()

        while monitoring_active and task_id in running_tasks:
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                print_status(f"[监控] 任务 '{task_name}' 监控超时 ({timeout_seconds}秒)，正在停止...", "⏱️")
                aipy_client.stop_task(task_id)
                print_status(f"[监控] 任务 '{task_name}' 已超时停止", "⏹️")

                # 超时后直接更新平台状态为"任务超时"，不进行评判
                _update_timeout_status(platform_api, task_id, task_name, row_id, int(elapsed))
                del running_tasks[task_id]
                break

            # 获取任务状态
            task_info = aipy_client.get_task_info(task_id)
            if task_info:
                state = task_info.get("state", "UNKNOWN")
                stdin = task_info.get("stdin", False)

                print_status(f"[监控] 任务 '{task_name}' 状态: {state} ({int(elapsed)}秒)", "👁️")

                # 如果任务完成（EXIT状态），进行评判并更新平台
                if state == "EXIT":
                    print_status(f"[监控] 任务 '{task_name}' 已完成，正在评判...", "✅")

                    # 评判任务并更新平台（评判完成后再删除任务）
                    _judge_and_update(task_judge, platform_api, task_id, task_name, row_id)
                    del running_tasks[task_id]
                    break

                # 如果stdin为true，表示任务正在等待输入，可以停止
                if stdin:
                    print_status(f"[监控] 任务 '{task_name}' 等待输入(stdin=true)，正在停止...", "⏹️")
                    aipy_client.stop_task(task_id)
                    print_status(f"[监控] 任务 '{task_name}' 已停止", "✅")

                    # 评判任务并更新平台（评判完成后再删除任务）
                    _judge_and_update(task_judge, platform_api, task_id, task_name, row_id)
                    del running_tasks[task_id]
                    break
            else:
                # API调用失败，无法获取任务状态
                print_status(f"[监控] 警告: 无法获取任务 '{task_name}' 的状态信息", "⚠️")

            time.sleep(5)  # 每5秒检查一次

    except Exception as e:
        print_status(f"[监控] 任务 '{task_name}' 监控异常: {e}", "⚠️")
        if task_id in running_tasks:
            del running_tasks[task_id]


def _update_timeout_status(platform_api, task_id, task_name, row_id, elapsed_time):
    """
    更新任务超时状态到平台

    Args:
        platform_api: PlatformAPI实例
        task_id: AiPy任务ID
        task_name: 任务名称
        row_id: 平台任务行ID
        elapsed_time: 已执行时间（秒）
    """
    try:
        print_status(f"[超时] ========== 更新超时状态 ==========", "📝")
        print_status(f"[超时] 任务: {task_name}", "📋")
        print_status(f"[超时] 执行时间: {elapsed_time}秒", "⏱️")
        print_status(f"[超时] Row ID: {row_id}", "📌")

        # 导入更新函数
        from updata import update_platform_task_result

        # 更新到平台，状态为"任务超时"
        update_platform_task_result(
            platform_api=platform_api,
            row_id=row_id,
            aipy_task_id=task_id,
            execution_time=elapsed_time,
            tokens=None,
            success=False,
            failure_reason=f"任务执行超时（{elapsed_time}秒）",
            task_json_path=None,
            judge_result="失败",
            exec_status="任务超时"
        )

        print_status(f"[超时] ========== 超时状态更新完成 ==========", "✅")

    except Exception as e:
        print_status(f"[超时] 更新超时状态异常: {e}", "❌")
        import traceback
        print_status(f"[超时] 异常详情: {traceback.format_exc()}", "🔍")


def _judge_and_update(task_judge, platform_api, task_id, task_name, row_id, timeout=False):
    """
    评判任务并更新到平台

    Args:
        task_judge: 任务评判器实例
        platform_api: PlatformAPI实例
        task_id: 任务ID
        task_name: 任务名称
        row_id: 平台任务行ID
        timeout: 是否超时
    """
    try:
        # 进行AI评判
        print_status(f"[评判] 正在评判任务 '{task_name}'...", "⚖️")
        # 从任务数据中获取平台定义的判断成功标准
        success_criteria = running_tasks.get(task_id, {}).get("success_criteria", "")
        judge_result = task_judge.judge_task(task_id, task_name, success_criteria=success_criteria)

        if judge_result:
            result = judge_result.get("result", "待定")
            reason = judge_result.get("reason", "")
            failure_type = judge_result.get("failure_type", "")
            confidence = judge_result.get("confidence", "中")

            print_status(f"[评判] ========== 收到评判结果 ==========", "📥")
            print_status(f"[评判] 评判结果: {result}", "📊")
            print_status(f"[评判] 判断原因: {reason[:100]}...", "📝")
            if failure_type:
                print_status(f"[评判] 失败原因分类: {failure_type}", "🔍")
            print_status(f"[评判] 置信度: {confidence}", "🎯")
            print_status(f"[评判] ===================================", "📥")

            # 解析任务结果（获取执行时间和tokens）
            parse_result = parse_task_result(task_id)

            execution_time = None
            tokens = None
            task_json_path = None

            if parse_result:
                execution_time = parse_result.get("execution_time")
                tokens = parse_result.get("tokens")
                task_json_path = parse_result.get("task_json_path")

            # 更新到平台（传递judge_result和judge_reason）
            print_status(f"[更新] ========== 准备更新平台 ==========", "📤")
            print_status(f"[更新] AI判断结果: {result}", "⚖️")
            print_status(f"[更新] Row ID: {row_id}", "📌")
            update_platform_task_result(
                platform_api=platform_api,
                row_id=row_id,
                aipy_task_id=task_id,
                execution_time=execution_time,
                tokens=tokens,
                success=(result == "成功"),  # 保留兼容性
                failure_reason=reason if result != "成功" else "",
                task_json_path=task_json_path,
                judge_result=result,  # 传递AI评判结果到单选字段
                judge_reason=reason  # 传递AI判断原因说明
            )
        else:
            print_status(f"[评判] 评判失败，使用默认结果", "⚠️")
            # 评判失败时，解析结果并更新（默认为失败）
            parse_and_update_task_result(
                platform_api=platform_api,
                aipy_task_id=task_id,
                row_id=row_id,
                judge_result="失败"  # 评判失败时默认为失败
            )

    except Exception as e:
        print_status(f"[评判] 评判过程异常: {e}", "❌")
        import traceback
        print_status(f"[评判] 异常详情: {traceback.format_exc()}", "🔍")

        # 评判异常时，解析结果并更新
        parse_and_update_task_result(
            platform_api=platform_api,
            aipy_task_id=task_id,
            row_id=row_id,
            judge_result="失败"  # 评判异常时默认为失败
        )


def start_task_monitoring(aipy_client, platform_api, task_judge, task_id, task_name, row_id, timeout_seconds):
    """
    启动任务状态监控线程

    Args:
        aipy_client: AiPy客户端实例
        platform_api: PlatformAPI实例
        task_judge: 任务评判器实例
        task_id: 任务ID
        task_name: 任务名称
        row_id: 平台任务行ID
        timeout_seconds: 监控超时时间（秒）
    """
    global running_tasks

    # 添加到运行任务列表
    running_tasks[task_id] = {
        "name": task_name,
        "start_time": time.time(),
        "row_id": row_id,
        "success_criteria": kwargs.get("success_criteria", "")
    }

    # 创建监控线程
    monitor_thread = threading.Thread(
        target=monitor_task_status,
        args=(aipy_client, platform_api, task_judge, task_id, task_name, row_id, timeout_seconds),
        daemon=True
    )
    monitor_thread.start()


def stop_all_monitoring():
    """停止所有任务监控"""
    global monitoring_active
    monitoring_active = False
    running_tasks.clear()


def load_config(config_path: str = None) -> dict:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    if config_path is None:
        config_path = os.path.join(current_dir, "config.json")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print_status(f"配置文件未找到: {config_path}", "❌")
        print_status("请确保config.json文件存在于项目根目录", "❌")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_status(f"配置文件格式错误: {e}", "❌")
        sys.exit(1)


def execute_single_task(aipy_client, task, platform_api, task_idx, total_tasks):
    """
    执行单个任务

    Args:
        aipy_client: AiPy客户端实例
        task: 任务数据
        platform_api: PlatformAPI实例
        task_idx: 任务索引
        total_tasks: 总任务数

    Returns:
        (success, aipy_task_id, task_name, row_id) 元组
    """
    row_id = task.get("rowid") or task.get("rowId")
    task_id = task.get(platform_api.FIELD_TASK_ID, "")
    status = task.get(platform_api.FIELD_TASK_STATUS, "")

    # 获取标准任务信息
    standard_task = platform_api.get_standard_task_info(task)
    task_name = standard_task.get("name", "") if standard_task else ""

    # 获取模型名称
    model_name = platform_api.get_model_name(task)
    print_status(f"DEBUG: 从平台获取到的model_name原始值: {repr(model_name)}", "DEBUG")

    # 修正模型名称的常见拼写错误
    if model_name:
        model_name_fixed = model_name.replace("0pus", "Opus").replace("0PUS", "OPUS")
        if model_name_fixed != model_name:
            print_status(f"修正模型名称拼写: {model_name} -> {model_name_fixed}", "🔧")
            model_name = model_name_fixed

    # 获取智能体列表
    agent_list = platform_api.get_agent_list(task)

    # 判断是否为"一体机测试"表格
    is_aio_test = (platform_api.worksheet_name == "一体机测试")

    print("=" * 60)
    print(f"处理任务 {task_idx}/{total_tasks}")
    print("=" * 60)
    print(f"Row ID: {row_id}")
    print(f"任务ID: {task_id}")
    print(f"状态: {status}")
    print(f"标准任务: {task_name}")
    print(f"使用模型: {model_name}")
    print(f"工作表名称: {platform_api.worksheet_name}")
    print(f"是否一体机测试: {is_aio_test}")
    if agent_list:
        print(f"智能体: {', '.join(agent_list)}")
    print()

    if not task_name:
        print_status("任务名称为空，跳过", "⚠️")
        return False, None, None, row_id

    # 步骤1：创建AiPy任务（不填写instruction）
    print_status(f"步骤1: 创建AiPy任务...", "步骤1")
    aipy_task_id = aipy_client.create_task(title=task_name)

    if not aipy_task_id:
        print_status("AiPy任务创建失败", "[失败]")
        return False, None, None, row_id

    print_status(f"任务创建成功: {aipy_task_id}", "[成功]")

    # 创建任务后等待2秒，确保任务创建完成
    import time
    print_status(f"等待2秒让任务创建完成...", "⏳")
    time.sleep(2)

    # 步骤2：更新模型（根据工作表类型选择不同的API）
    if is_aio_test:
        # 一体机测试：使用task-update-provider-by-id
        if model_name:
            provider_name = "一体机"
            print_status(f"步骤2: 更新一体机Provider: {provider_name}, 模型: {model_name}", "步骤2")
            print_status(f"DEBUG: task_id={aipy_task_id}, provider={provider_name}, providerId=-1, model={model_name}", "DEBUG")
            update_success = aipy_client.update_task_provider(
                task_id=aipy_task_id,
                provider=provider_name,
                provider_id=-1,
                model=model_name
            )
            if update_success:
                print_status(f"一体机Provider更新成功", "[成功]")

                # 更新模型后等待2秒，确保更新生效
                print_status(f"等待2秒让模型更新生效...", "⏳")
                time.sleep(2)

                # 验证更新是否生效
                task_info = aipy_client.get_task_info(aipy_task_id)
                if task_info:
                    current_model = task_info.get("model", "unknown")
                    current_provider = task_info.get("provider", "unknown")
                    print_status(f"验证 - 当前模型: {current_model}, Provider: {current_provider}", "📊")
                    if current_model != model_name:
                        print_status(f"警告: 模型更新未生效！期望: {model_name}, 实际: {current_model}", "⚠️")
                    else:
                        print_status(f"验证成功: 模型已正确更新", "✅")
                else:
                    print_status(f"无法获取任务信息进行验证", "⚠️")
            else:
                print_status(f"一体机Provider更新失败，将使用默认配置", "⚠️")
        else:
            print_status(f"未从平台获取到模型名称，跳过Provider更新", "⚠️")
    else:
        # 普通测试：使用task-update-by-id
        if model_name:
            model_lower = model_name.lower()
            print_status(f"步骤2: 更新任务模型: {model_lower}", "步骤2")
            update_success = aipy_client.update_task(
                task_id=aipy_task_id,
                model=model_lower
            )
            if update_success:
                print_status(f"模型更新成功", "[成功]")
            else:
                print_status(f"模型更新失败，将使用默认模型", "⚠️")

    # 步骤3：启动任务
    print_status(f"步骤3: 启动任务执行", "步骤3")
    if agent_list:
        print_status(f"启用智能体: {', '.join(agent_list)}", "🤖")

    # 启动前再次验证模型设置
    task_info_before = aipy_client.get_task_info(aipy_task_id)
    if task_info_before:
        print_status(f"启动前验证 - 模型: {task_info_before.get('model')}, Provider: {task_info_before.get('provider')}", "🔍")

    start_success = aipy_client.resume_task(
        task_id=aipy_task_id,
        instruction=task_name,
        model=None,  # 不传递model参数（已在步骤2设置）
        mcp_list=agent_list if agent_list else None  # 通过resume_task启用智能体
    )

    # 启动后验证模型设置
    time.sleep(1)
    task_info_after = aipy_client.get_task_info(aipy_task_id)
    if task_info_after:
        model_after = task_info_after.get("model")
        provider_after = task_info_after.get("provider")
        print_status(f"启动后验证 - 模型: {model_after}, Provider: {provider_after}", "🔍")
        if is_aio_test and model_name and model_after != model_name:
            print_status(f"警告: resume_task后模型被改变！期望: {model_name}, 实际: {model_after}", "⚠️")

    if start_success:
        print_status(f"提示词已设置，任务已启动执行", "[成功]")
        if agent_list:
            print_status(f"已启用智能体: {', '.join(agent_list)}", "[智能体]")
        return True, aipy_task_id, task_name, row_id
    else:
        print_status(f"任务启动失败", "⚠️")
        return False, None, None, row_id


def sync_and_execute_tasks():
    """从平台获取待执行任务并同步到AiPy执行（动态并发控制）"""

    print("=" * 60)
    print("测试任务自动执行系统（动态并发模式）")
    print("=" * 60)
    print()

    # 加载配置
    config = load_config()
    task_settings = config.get("task_settings", {})
    status_filter = task_settings.get("status_filter", "待执行")
    monitor_timeout = task_settings.get("monitor_timeout", 300)
    max_concurrent_tasks = task_settings.get("max_concurrent_tasks", 2)

    # 创建平台API客户端
    print_status("正在初始化测试平台API...", "🔌")
    platform_api = create_platform_api()

    # 创建AiPy客户端
    print_status("正在初始化AiPy客户端...", "🔌")
    aipy_client = create_aipy_client()

    # 创建任务评判器
    print_status("正在初始化任务评判器...", "⚖️")
    task_judge = create_task_judge()

    print()
    print("=" * 60)
    print(f"从平台获取状态为 '{status_filter}' 的任务")
    print("=" * 60)
    print()

    # 获取待执行任务
    tasks = platform_api.query_pending_tasks(status=status_filter)

    if not tasks:
        print_status("没有找到待执行任务", "ℹ️")
        return

    total_tasks = len(tasks)
    print_status(f"找到 {total_tasks} 个待执行任务", "📋")
    print_status(f"最大并发任务数: {max_concurrent_tasks}", "⚙️")
    print_status(f"监控超时时间: {monitor_timeout}秒", "⏱️")
    print()

    # 任务队列和计数器
    pending_tasks = tasks.copy()  # 待处理任务队列
    processed_count = 0  # 已处理任务数
    success_count = 0
    failed_count = 0

    print("=" * 60)
    print(f"开始执行任务（保持 {max_concurrent_tasks} 个任务并发）")
    print("=" * 60)
    print()

    # 首先启动第一批任务
    initial_batch_size = min(max_concurrent_tasks, len(pending_tasks))
    for i in range(initial_batch_size):
        task = pending_tasks.pop(0)
        processed_count += 1

        success, aipy_task_id, task_name, row_id = execute_single_task(
            aipy_client, task, platform_api, processed_count, total_tasks
        )

        if success and aipy_task_id:
            start_task_monitoring(aipy_client, platform_api, task_judge, aipy_task_id, task_name, row_id, monitor_timeout)
            print_status(f"任务监控已启动", "[监控]")
        else:
            failed_count += 1

        print()

    # 动态补充任务：当有任务完成时，立即从队列中取新任务补充
    while pending_tasks:
        # 等待直到有任务完成（running_tasks数量减少）
        current_running = len(running_tasks)
        if current_running >= max_concurrent_tasks:
            # 等待任务完成
            print_status(f"当前有 {current_running} 个任务执行中，等待任务完成...", "⏳")
            while len(running_tasks) >= max_concurrent_tasks and pending_tasks:
                time.sleep(2)

        # 检查是否可以补充新任务
        if len(running_tasks) < max_concurrent_tasks and pending_tasks:
            task = pending_tasks.pop(0)
            processed_count += 1

            print()
            print("=" * 60)
            print(f"补充新任务 ({len(running_tasks)} 个运行中, {len(pending_tasks)} 个待处理)")
            print("=" * 60)

            success, aipy_task_id, task_name, row_id = execute_single_task(
                aipy_client, task, platform_api, processed_count, total_tasks
            )

            if success and aipy_task_id:
                start_task_monitoring(aipy_client, platform_api, task_judge, aipy_task_id, task_name, row_id, monitor_timeout)
                print_status(f"任务监控已启动", "[监控]")
                success_count += 1
            else:
                failed_count += 1

            print()

    # 等待所有剩余任务完成
    if running_tasks:
        print()
        print("=" * 60)
        print(f"所有任务已下发，等待 {len(running_tasks)} 个任务完成...")
        print("=" * 60)
        print("按 Ctrl+C 可查看当前任务状态并退出")
        print()

        try:
            while running_tasks:
                time.sleep(2)
        except KeyboardInterrupt:
            print()
            print("=" * 60)
            print("用户中断 - 当前任务状态")
            print("=" * 60)

            # 显示所有正在运行的任务状态
            for task_id, task_info in list(running_tasks.items()):
                task_name = task_info.get("name", "未知")
                task_data = aipy_client.get_task_info(task_id)
                if task_data:
                    state = task_data.get("state", "UNKNOWN")
                    stdin = task_data.get("stdin", False)
                    print(f"\n任务: {task_name}")
                    print(f"  ID: {task_id}")
                    print(f"  状态: {state}")
                    print(f"  等待输入: {stdin}")
                    print(f"  模型: {task_data.get('model', '未知')}")
                else:
                    print(f"\n任务: {task_name}")
                    print(f"  ID: {task_id}")
                    print(f"  状态: 无法获取")

            print()
            print("=" * 60)
            print("是否要停止所有正在运行的任务？(y/n): ", end="")

            try:
                choice = input().strip().lower()
                if choice == 'y':
                    print()
                    for task_id, task_info in list(running_tasks.items()):
                        task_name = task_info.get("name", "未知")
                        print_status(f"正在停止任务: {task_name}", "⏹️")
                        aipy_client.stop_task(task_id)
                    print_status("所有任务已停止", "✅")
                else:
                    print_status("任务将继续在后台运行", "ℹ️")
            except:
                print_status("任务将继续在后台运行", "ℹ️")

        finally:
            # 停止监控
            stop_all_monitoring()

    # 输出统计信息
    print("=" * 60)
    print("执行统计")
    print("=" * 60)
    print(f"总任务数: {len(tasks)}")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        sync_and_execute_tasks()
    except KeyboardInterrupt:
        print_status("\n用户中断执行", "⚠️")
        sys.exit(0)
    except Exception as e:
        print_status(f"执行异常: {e}", "❌")
        import traceback
        traceback.print_exc()
        sys.exit(1)