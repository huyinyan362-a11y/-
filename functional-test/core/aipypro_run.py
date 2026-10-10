#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AiPy客户端API接口模块
负责与AiPy Pro客户端进行交互，包括创建任务、更新模型、启动执行等
"""
#  $env:AIPY_CLIENT_API_KEY
import requests
import json
import os
from typing import Dict, List, Optional
from datetime import datetime


def print_status(message: str, emoji: str = ""):
    """实时输出状态"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        if emoji:
            print(f"[{timestamp}] {emoji} {message}", flush=True)
        else:
            print(f"[{timestamp}] {message}", flush=True)
    except UnicodeEncodeError:
        # Windows console编码问题，移除emoji重试
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
        # 默认配置文件路径：项目根目录的config.json
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


class AiPyClientAPI:
    """AiPy Pro客户端API客户端"""

    def __init__(
        self,
        api_base: str = None,
        api_key: str = None,
        config_path: str = None
    ):
        """
        初始化AiPy客户端API

        Args:
            api_base: API基础地址（默认从配置文件或环境变量读取）
            api_key: API密钥（默认从配置文件或环境变量读取）
            config_path: 配置文件路径（可选）
        """
        # 加载配置文件
        config = load_config(config_path)
        aipy_config = config.get("aipy_api", {})

        # 优先级：传入参数 > 配置文件 > 环境变量 > 默认值
        self.api_base = api_base or aipy_config.get("base_url") or os.getenv("AIPY_CLIENT_API", "http://127.0.0.1:41970")
        self.api_key = api_key or aipy_config.get("api_key") or os.getenv("AIPY_CLIENT_API_KEY", "")
        self.session = requests.Session()

        if self.api_key:
            print_status(f"AiPy API: {self.api_base}", "🔗")
            print_status(f"API Key: {self.api_key[:10]}...{self.api_key[-4:]}", "🔑")
        else:
            print_status("警告: API Key未配置，部分功能可能无法使用", "⚠️")

    def get_headers(self) -> dict:
        """获取API请求头"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def create_task(
        self,
        title: str,
        instruction: str = None,
        model: str = None,
        mcp_list: List[str] = None
    ) -> Optional[str]:
        """
        创建AiPy任务

        Args:
            title: 任务标题
            instruction: 任务指令/提示词（可选）
            model: 使用的模型（可选，如"glm-5"）
            mcp_list: 启用的MCP/智能体列表（可选）

        Returns:
            任务ID，失败返回None
        """
        print_status(f"正在创建任务: {title}", "➕")

        url = f"{self.api_base}/api/aipy/create-task"
        payload_data = {"title": title}

        if instruction:
            payload_data["instruction"] = instruction
        if model:
            payload_data["model"] = model
        if mcp_list:
            payload_data["mcp"] = mcp_list

        payload = [payload_data]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            task_id = result.get("data")
            if task_id:
                print_status(f"任务创建成功: {task_id}", "✅")
                return task_id
            else:
                print_status(f"任务创建失败: {result}", "❌")
                return None

        except Exception as e:
            print_status(f"任务创建异常: {e}", "❌")
            return None

    def update_task_provider(
        self,
        task_id: str,
        provider: str = "",
        provider_id: int = -1,
        model: str = None
    ) -> bool:
        """
        更新AiPy任务的Provider（用于一体机测试）

        Args:
            task_id: 任务ID
            provider: Provider名称（如"一体机"）
            provider_id: Provider ID（默认-1）
            model: 使用的模型（可选）

        Returns:
            是否成功
        """
        print_status(f"正在更新任务Provider: {task_id}", "🔧")

        url = f"{self.api_base}/api/aipy/task-update-provider-by-id"

        # 构建请求数据
        payload_data = {
            "provider": provider,
            "providerId": provider_id
        }

        if model:
            payload_data["model"] = model
            print_status(f"设置模型: {model}", "📊")

        payload = [task_id, payload_data]

        print_status(f"请求URL: {url}", "🔍")
        print_status(f"请求头: {self.get_headers()}", "🔍")
        print_status(f"请求参数: {payload}", "🔍")
        print_status(f"请求参数JSON: {json.dumps(payload, ensure_ascii=False)}", "🔍")

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            print_status(f"响应状态码: {response.status_code}", "🔍")
            print_status(f"响应头: {dict(response.headers)}", "🔍")
            print_status(f"响应内容: {response.text}", "🔍")

            response.raise_for_status()
            result = response.json()
            print_status(f"响应数据: {result}", "🔍")
            print_status(f"任务Provider更新成功: {provider}, 模型: {model}", "✅")
            return True

        except Exception as e:
            print_status(f"任务Provider更新异常: {e}", "❌")
            return False

    def update_task(
        self,
        task_id: str,
        model: str = None,
        instruction: str = None,
        mcp_list: List[str] = None
    ) -> bool:
        """
        更新AiPy任务

        Args:
            task_id: 任务ID
            model: 更新的模型（可选）
            instruction: 更新的指令（可选）
            mcp_list: 更新的MCP列表（可选）

        Returns:
            是否成功
        """
        print_status(f"正在更新任务: {task_id}", "🔧")

        url = f"{self.api_base}/api/aipy/task-update-by-id"
        payload_data = {}

        if model:
            payload_data["model"] = model
        if instruction:
            payload_data["instruction"] = instruction
        if mcp_list is not None:
            payload_data["mcp"] = mcp_list

        payload = [task_id, payload_data]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            print_status("任务更新成功", "✅")
            return True

        except Exception as e:
            print_status(f"任务更新异常: {e}", "❌")
            return False

    def enable_agents(
        self,
        task_id: str,
        agent_list: List[str]
    ) -> bool:
        """
        启用多个智能体/MCP

        Args:
            task_id: 任务ID
            agent_list: 智能体名称列表（如["@aipy-pro/vision", "@aipy-pro/image"]）

        Returns:
            是否成功
        """
        if not agent_list:
            return True

        print_status(f"正在启用智能体: {', '.join(agent_list)}", "🤖")

        # 构建智能体启用字典 {agent_name: True}
        agents_dict = {agent: True for agent in agent_list}

        # 使用update_task来启用智能体
        url = f"{self.api_base}/api/aipy/task-update-by-id"
        payload = [task_id, agents_dict]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            print_status(f"智能体启用成功", "✅")
            return True

        except Exception as e:
            print_status(f"智能体启用异常: {e}", "❌")
            return False

    def enable_agent(
        self,
        task_id: str,
        agent_name: str
    ) -> bool:
        """
        启用单个智能体/MCP（兼容方法）

        Args:
            task_id: 任务ID
            agent_name: 智能体名称（如"@aipy-pro/vision"）

        Returns:
            是否成功
        """
        return self.enable_agents(task_id, [agent_name])

    def resume_task(
        self,
        task_id: str,
        instruction: str = None,
        model: str = None,
        mcp_list: List[str] = None
    ) -> bool:
        """
        启动/恢复任务执行

        Args:
            task_id: 任务ID
            instruction: 任务指令（可选，如不设置则使用任务原有指令）
            model: 模型（可选）
            mcp_list: MCP/智能体列表（可选）

        Returns:
            是否成功
        """
        print_status(f"正在启动任务执行: {task_id}", "🚀")

        url = f"{self.api_base}/api/aipy/resume-task"
        payload_data = {}

        if instruction:
            payload_data["instruction"] = instruction
        if model:
            payload_data["model"] = model
        if mcp_list:
            payload_data["mcp"] = mcp_list

        payload = [task_id, payload_data]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            print_status("任务启动成功", "✅")
            return True

        except Exception as e:
            print_status(f"任务启动异常: {e}", "❌")
            return False

    def stop_task(self, task_id: str) -> bool:
        """
        停止任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功
        """
        print_status(f"正在停止任务: {task_id}", "⏹️")

        url = f"{self.api_base}/api/aipy/stop-task"
        payload = [task_id]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            print_status("任务已停止", "✅")
            return True

        except Exception as e:
            print_status(f"停止任务异常: {e}", "❌")
            return False

    def is_task_completed(self, task_id: str) -> bool:
        """
        判断任务是否执行完成

        Args:
            task_id: 任务ID

        Returns:
            任务是否已完成（state为EXIT或其他完成状态）
        """
        task_info = self.get_task_info(task_id)
        if not task_info:
            return False

        state = task_info.get("state", "")
        # EXIT表示任务已退出完成
        # 其他可能的完成状态可以根据实际情况添加
        return state == "EXIT"

    def wait_for_completion(
        self,
        task_id: str,
        check_interval: int = 5,
        timeout: int = 600
    ) -> bool:
        """
        等待任务执行完成

        Args:
            task_id: 任务ID
            check_interval: 检查间隔（秒），默认5秒
            timeout: 超时时间（秒），默认600秒（10分钟）

        Returns:
            任务是否在超时前完成
        """
        import time
        print_status(f"开始等待任务完成: {task_id}", "⏳")

        elapsed = 0
        while elapsed < timeout:
            if self.is_task_completed(task_id):
                print_status(f"任务执行完成: {task_id}", "✅")
                return True

            print_status(f"任务执行中... ({elapsed}/{timeout}秒)", "⏳")
            time.sleep(check_interval)
            elapsed += check_interval

        print_status(f"等待任务超时: {task_id}", "⏱️")
        return False

    def stop_task(self, task_id: str) -> bool:
        """
        停止任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功
        """
        print_status(f"正在停止任务: {task_id}", "⏹️")

        url = f"{self.api_base}/api/aipy/stop-task"
        payload = [task_id]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            print_status("任务已停止", "✅")
            return True

        except Exception as e:
            print_status(f"停止任务异常: {e}", "❌")
            return False

    def get_task_info(self, task_id: str) -> Optional[Dict]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典，失败返回None
        """
        url = f"{self.api_base}/api/aipy/task-find-by-id"
        payload = [task_id]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            task_data = result.get("data")
            if task_data:
                return task_data
            else:
                return None

        except Exception as e:
            print_status(f"获取任务信息异常: {e}", "❌")
            return None

    def get_task_with_events(self, task_id: str) -> Optional[Dict]:
        """
        获取任务详情及消息列表

        Args:
            task_id: 任务ID

        Returns:
            任务信息及消息字典，失败返回None
        """
        url = f"{self.api_base}/api/aipy/task-with-events-by-id"
        payload = [task_id]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            task_data = result.get("data")
            if task_data:
                return task_data
            else:
                return None

        except Exception as e:
            print_status(f"获取任务消息异常: {e}", "❌")
            return None

    def get_task_list(self, limit: int = 50) -> List[Dict]:
        """
        获取任务列表

        Args:
            limit: 返回数量限制

        Returns:
            任务列表
        """
        url = f"{self.api_base}/api/aipy/task-find-many"
        payload = [{"where": "type = 'task'", "orderBy": "create_time DESC", "limit": limit}]

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            tasks = result.get("data", [])
            return tasks if isinstance(tasks, list) else []

        except Exception as e:
            print_status(f"获取任务列表异常: {e}", "❌")
            return []


def create_aipy_client(
    api_base: str = None,
    api_key: str = None,
    config_path: str = None
) -> AiPyClientAPI:
    """
    创建AiPy客户端API实例的便捷函数

    使用默认值创建，或通过参数覆盖默认配置

    Args:
        api_base: API基础地址（可选）
        api_key: API密钥（可选）
        config_path: 配置文件路径（可选）

    Returns:
        AiPyClientAPI实例
    """
    return AiPyClientAPI(
        api_base=api_base,
        api_key=api_key,
        config_path=config_path
    )

