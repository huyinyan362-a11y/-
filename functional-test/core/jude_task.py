#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
任务评判模块
使用AI模型判断任务执行结果是否成功
"""

import os
import sys
import json
import re
import requests
from typing import Dict, Optional
from datetime import datetime

# 添加core目录到路径
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


def load_config(config_path: str = None) -> Dict:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认为项目根目录的config.json

    Returns:
        配置字典
    """
    if config_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, "config.json")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print_status(f"配置文件未找到: {config_path}", "⚠️")
        return {}
    except json.JSONDecodeError as e:
        print_status(f"配置文件格式错误: {e}", "⚠️")
        return {}


class TaskJudge:
    """任务评判器"""

    def __init__(
        self,
        api_url: str = None,
        api_key: str = None,
        model: str = None,
        judge_prompt: str = None,
        timeout: int = None,
        config_path: str = None
    ):
        """
        初始化任务评判器

        Args:
            api_url: 评判API地址（默认从配置文件读取）
            api_key: 评判API密钥（默认从配置文件读取）
            model: 评判模型名称（默认从配置文件读取）
            judge_prompt: 评判提示词模板（默认从配置文件读取）
            timeout: 请求超时时间（秒，默认从配置文件读取）
            config_path: 配置文件路径（可选）
        """
        # 加载配置文件
        config = load_config(config_path)
        judge_config = config.get("judge_api", {})

        # 优先级：传入参数 > 配置文件 > 默认值
        self.api_url = api_url or judge_config.get("api_url", "https://api.trustoken.cn/v1/chat/completions")
        self.api_key = api_key or judge_config.get("api_key", "")
        self.model = model or judge_config.get("model", "glm-4.7")
        self.judge_prompt = judge_prompt or judge_config.get("judge_prompt", self._get_default_prompt())
        self.timeout = timeout or judge_config.get("timeout", 180)
        self.session = requests.Session()

        # 验证配置
        if not self.api_key:
            print_status("警告: 评判API Key未配置，评判功能将无法使用", "⚠️")
        else:
            print_status(f"评判API: {self.api_url}", "🔗")
            print_status(f"评判模型: {self.model}", "🤖")
            print_status(f"API Key: {self.api_key[:10]}...{self.api_key[-4:]}", "🔑")

    def _get_default_prompt(self) -> str:
        """获取默认评判提示词"""
        return """你是一个任务执行判官，需要根据任务执行结果判断任务是否成功完成。

以下是从task.json文件中提取的任务执行信息：

{task_info}

平台定义的判断成功标准（优先按此标准判断）：
{success_criteria}

判断标准：
1. 成功：任务完整执行完成，满足上述「判断成功标准」，没有出现错误或中断
2. 失败：任务执行过程中出现错误、被中断、模型拒绝执行、或明显不符合「判断成功标准」
3. 待定：无法确定任务是否成功完成

注意：请严格参考「判断成功标准」进行评判，不要过于严苛，只要核心需求完成即可判定成功。

请只返回JSON格式结果，不要包含其他内容：
{{"result": "成功/失败/待定", "reason": "判断原因说明", "confidence": "高/中/低"}}"""

    def _get_task_workdir(self, task_id: str) -> str:
        """
        获取任务工作目录路径

        Args:
            task_id: AiPy任务ID

        Returns:
            工作目录路径
        """
        # 可能的工作目录位置
        possible_paths = [
            # Windows默认路径
            os.path.join(os.path.expanduser("~"), "aipywork", task_id),
            # 桌面路径
            os.path.join(os.path.expanduser("~"), "Desktop", "anthropic_claude-sonnet-4.6", task_id),
            os.path.join(os.path.expanduser("~"), "Desktop", "anthropic_claude-opus-4.6", task_id),
            os.path.join(os.path.expanduser("~"), "Desktop", "anthropic_claude-haiku-4.5", task_id),
        ]

        # 返回第一个存在的目录
        for path in possible_paths:
            if os.path.exists(path):
                return path

        # 如果都不存在，返回默认路径
        return possible_paths[0]

    def _read_task_json(self, task_id: str) -> Optional[Dict]:
        """
        读取任务的task.json文件

        Args:
            task_id: AiPy任务ID

        Returns:
            task.json内容字典，失败返回None
        """
        workdir = self._get_task_workdir(task_id)
        task_json_path = os.path.join(workdir, "task.json")

        if not os.path.exists(task_json_path):
            print_status(f"task.json文件不存在: {task_json_path}", "❌")
            return None

        try:
            print_status(f"读取task.json: {task_json_path}", "📄")
            with open(task_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print_status(f"读取task.json异常: {e}", "❌")
            return None

    def _build_task_info(self, task_json: Dict) -> str:
        """
        从task.json构建任务信息文本

        Args:
            task_json: task.json内容字典

        Returns:
            任务信息文本
        """
        info_parts = []

        # 提取初始指令
        try:
            steps = task_json.get("steps", [])
            if steps:
                first_step = steps[0]
                initial_instruction = first_step.get("instruction", "")
                if initial_instruction:
                    info_parts.append(f"【用户指令】\n{initial_instruction}\n")
        except Exception as e:
            print_status(f"提取初始指令异常: {e}", "⚠️")

        # 提取对话轮次
        try:
            rounds_info = []
            if steps:
                first_step = steps[0]
                rounds = first_step.get("rounds", [])

                for idx, round_data in enumerate(rounds, 1):
                    # LLM响应
                    llm_response = round_data.get("llm_response", {})
                    if llm_response:
                        message = llm_response.get("message", {})
                        content = message.get("message", {}).get("content", "")
                        if content:
                            # 限制内容长度
                            content_preview = content[:500] if len(content) > 500 else content
                            rounds_info.append(f"第{idx}轮 LLM响应:\n{content_preview}\n")

                    # 系统反馈
                    system_feedback = round_data.get("system_feedback", {})
                    if system_feedback:
                        message = system_feedback.get("message", {})
                        content = message.get("content", "")
                        if content:
                            # 限制内容长度
                            content_preview = content[:300] if len(content) > 300 else content
                            rounds_info.append(f"第{idx}轮 系统反馈:\n{content_preview}\n")

                    # 工具调用
                    tool_calls = round_data.get("tool_calls", [])
                    if tool_calls:
                        tool_names = [tc.get("name", "unknown") for tc in tool_calls]
                        rounds_info.append(f"第{idx}轮 工具调用: {', '.join(tool_names)}\n")

                if rounds_info:
                    info_parts.append("【对话过程】")
                    info_parts.extend(rounds_info[:5])  # 只取前5轮
                    if len(rounds_info) > 5:
                        info_parts.append(f"... (共{len(rounds_info)}轮对话)\n")

        except Exception as e:
            print_status(f"提取对话轮次异常: {e}", "⚠️")

        # 检查错误信息
        try:
            has_error = False
            error_info = []

            if steps:
                first_step = steps[0]
                rounds = first_step.get("rounds", [])

                for round_data in rounds:
                    # 检查系统反馈中的错误
                    system_feedback = round_data.get("system_feedback", {})
                    if system_feedback:
                        message = system_feedback.get("message", {})
                        content = message.get("content", "")
                        if content and ("Error" in content or "error" in content or "错误" in content):
                            has_error = True
                            error_info.append(f"系统反馈错误: {content[:200]}")

                    # 检查finish_reason
                    llm_response = round_data.get("llm_response", {})
                    if llm_response:
                        message = llm_response.get("message", {})
                        msg_data = message.get("message", {})
                        finish_reason = msg_data.get("finish_reason", "")
                        if finish_reason and finish_reason != "stop":
                            has_error = True
                            error_info.append(f"结束原因: {finish_reason}")

                if has_error:
                    info_parts.append("【错误信息】")
                    info_parts.extend(error_info)

        except Exception as e:
            print_status(f"检查错误信息异常: {e}", "⚠️")

        return "\n".join(info_parts) if info_parts else "无法提取任务信息"

    def _parse_judge_result(self, response: str) -> Dict:
        """
        解析评判结果

        Args:
            response: AI模型返回的响应文本

        Returns:
            解析后的评判结果字典
        """
        print_status(f"解析评判结果，原始响应长度: {len(response)}", "🔍")

        # 去除markdown代码块标记
        cleaned = response
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1]
        if "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[0] if parts[0].strip() else (parts[1] if len(parts) > 1 else "")
        cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
            print_status(f"JSON解析成功", "✅")
            return result
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', cleaned, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', response, re.DOTALL)

            if json_match:
                try:
                    result = json.loads(json_match.group())
                    print_status(f"正则提取JSON成功", "✅")
                    return result
                except Exception:
                    pass

            print_status(f"无法解析评判结果，返回默认值", "⚠️")
            return {"result": "待定", "reason": "无法解析评判结果", "confidence": "低"}

    def judge_task(self, task_id: str, task_name: str = None, success_criteria: str = "") -> Optional[Dict]:
        """
        评判任务执行结果

        Args:
            task_id: AiPy任务ID
            task_name: 任务名称（可选，用于日志）

        Returns:
            评判结果字典，包含result(成功/失败/待定)、reason(原因)、confidence(置信度)
            失败返回None
        """
        task_name = task_name or task_id
        print_status(f"开始评判任务: {task_name}", "⚖️")

        # 检查API配置
        if not self.api_key:
            print_status("评判API Key未配置，无法进行评判", "❌")
            return None

        # 读取task.json
        task_json = self._read_task_json(task_id)
        if not task_json:
            print_status("无法读取task.json，评判失败", "❌")
            return None

        # 构建任务信息
        print_status("构建任务信息...", "📝")
        task_info = self._build_task_info(task_json)
        print_status(f"任务信息长度: {len(task_info)} 字符", "📊")

        # 构建评判提示词
        criteria_text = success_criteria if success_criteria else "无特殊标准，根据任务执行情况综合判断"
        prompt = self.judge_prompt.format(task_info=task_info, success_criteria=criteria_text)

        # 调用评判API
        print_status(f"正在调用评判模型 {self.model}...", "📡")
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }

            print_status(f"发送评判请求，超时时间: {self.timeout}秒", "📤")
            response = self.session.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()

            # 提取响应内容
            content = result["choices"][0]["message"]["content"]
            print_status(f"评判模型响应完成，响应长度: {len(content)} 字符", "✅")

            # 解析评判结果
            judge_result = self._parse_judge_result(content)

            # 标准化结果
            final_result = {
                "result": judge_result.get("result", "待定"),
                "reason": judge_result.get("reason", ""),
                "confidence": judge_result.get("confidence", "中"),
                "failure_type": judge_result.get("failure_type", "")  # 失败原因分类
            }

            # 确保result是有效的值
            valid_results = ["成功", "失败", "待定"]
            if final_result["result"] not in valid_results:
                # 尝试映射英文结果
                result_map = {
                    "success": "成功",
                    "failed": "失败",
                    "failure": "失败",
                    "pending": "待定"
                }
                result_lower = final_result["result"].lower()
                final_result["result"] = result_map.get(result_lower, "待定")

            print_status(f"评判结果: {final_result['result']}", "📊")
            print_status(f"判断原因: {final_result['reason'][:100]}...", "📝")
            print_status(f"置信度: {final_result['confidence']}", "🎯")
            if final_result.get("failure_type"):
                print_status(f"失败原因分类: {final_result['failure_type']}", "🔍")

            # ========== 返回评判结果 ==========
            print_status(f"========== 评判完成，返回结果: {final_result['result']} ==========", "🔄")
            return final_result

        except requests.exceptions.Timeout:
            print_status(f"评判请求超时（超过{self.timeout}秒）", "⏱️")
            return None
        except requests.exceptions.RequestException as e:
            print_status(f"评判请求异常: {e}", "❌")
            return None
        except Exception as e:
            print_status(f"评判过程异常: {e}", "❌")
            import traceback
            print_status(f"异常详情: {traceback.format_exc()}", "🔍")
            return None

    def judge_task_by_json_path(self, task_json_path: str, task_name: str = None) -> Optional[Dict]:
        """
        通过直接提供task.json路径来评判任务

        Args:
            task_json_path: task.json文件完整路径
            task_name: 任务名称（可选，用于日志）

        Returns:
            评判结果字典，失败返回None
        """
        task_name = task_name or os.path.basename(os.path.dirname(task_json_path))
        print_status(f"开始评判任务: {task_name}", "⚖️")

        # 检查API配置
        if not self.api_key:
            print_status("评判API Key未配置，无法进行评判", "❌")
            return None

        # 检查文件存在
        if not os.path.exists(task_json_path):
            print_status(f"task.json文件不存在: {task_json_path}", "❌")
            return None

        # 读取task.json
        try:
            print_status(f"读取task.json: {task_json_path}", "📄")
            with open(task_json_path, 'r', encoding='utf-8') as f:
                task_json = json.load(f)
        except Exception as e:
            print_status(f"读取task.json异常: {e}", "❌")
            return None

        # 构建任务信息
        print_status("构建任务信息...", "📝")
        task_info = self._build_task_info(task_json)
        print_status(f"任务信息长度: {len(task_info)} 字符", "📊")

        # 构建评判提示词
        criteria_text = success_criteria if success_criteria else "无特殊标准，根据任务执行情况综合判断"
        prompt = self.judge_prompt.format(task_info=task_info, success_criteria=criteria_text)

        # 调用评判API
        print_status(f"正在调用评判模型 {self.model}...", "📡")
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }

            print_status(f"发送评判请求，超时时间: {self.timeout}秒", "📤")
            response = self.session.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()

            # 提取响应内容
            content = result["choices"][0]["message"]["content"]
            print_status(f"评判模型响应完成，响应长度: {len(content)} 字符", "✅")

            # 解析评判结果
            judge_result = self._parse_judge_result(content)

            # 标准化结果
            final_result = {
                "result": judge_result.get("result", "待定"),
                "reason": judge_result.get("reason", ""),
                "confidence": judge_result.get("confidence", "中"),
                "failure_type": judge_result.get("failure_type", "")  # 失败原因分类
            }

            # 确保result是有效的值
            valid_results = ["成功", "失败", "待定"]
            if final_result["result"] not in valid_results:
                # 尝试映射英文结果
                result_map = {
                    "success": "成功",
                    "failed": "失败",
                    "failure": "失败",
                    "pending": "待定"
                }
                result_lower = final_result["result"].lower()
                final_result["result"] = result_map.get(result_lower, "待定")

            print_status(f"评判结果: {final_result['result']}", "📊")
            print_status(f"判断原因: {final_result['reason'][:100]}...", "📝")
            print_status(f"置信度: {final_result['confidence']}", "🎯")
            if final_result.get("failure_type"):
                print_status(f"失败原因分类: {final_result['failure_type']}", "🔍")

            return final_result

        except requests.exceptions.Timeout:
            print_status(f"评判请求超时（超过{self.timeout}秒）", "⏱️")
            return None
        except requests.exceptions.RequestException as e:
            print_status(f"评判请求异常: {e}", "❌")
            return None
        except Exception as e:
            print_status(f"评判过程异常: {e}", "❌")
            import traceback
            print_status(f"异常详情: {traceback.format_exc()}", "🔍")
            return None


# 便捷函数
def create_task_judge(
    api_url: str = None,
    api_key: str = None,
    model: str = None,
    judge_prompt: str = None,
    timeout: int = None,
    config_path: str = None
) -> TaskJudge:
    """
    创建任务评判器实例的便捷函数

    Args:
        api_url: 评判API地址（可选）
        api_key: 评判API密钥（可选）
        model: 评判模型名称（可选）
        judge_prompt: 评判提示词模板（可选）
        timeout: 请求超时时间（可选）
        config_path: 配置文件路径（可选）

    Returns:
        TaskJudge实例
    """
    return TaskJudge(
        api_url=api_url,
        api_key=api_key,
        model=model,
        judge_prompt=judge_prompt,
        timeout=timeout,
        config_path=config_path
    )


if __name__ == "__main__":
    # 测试代码
    import sys

    print("=" * 60)
    print("测试：任务评判")
    print("=" * 60)

    # 从命令行参数获取任务ID
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        print("请输入要评判的任务ID:")
        task_id = input().strip()

    if not task_id:
        print("错误: 任务ID不能为空")
        sys.exit(1)

    print()

    # 创建评判器并评判任务
    judge = create_task_judge()
    result = judge.judge_task(task_id)

    if result:
        print()
        print("=" * 60)
        print("评判结果")
        print("=" * 60)
        print(f"结果: {result.get('result')}")
        print(f"原因: {result.get('reason')}")
        print(f"置信度: {result.get('confidence')}")
        print("=" * 60)
    else:
        print("评判失败")