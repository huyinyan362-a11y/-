#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试平台API接口模块
负责与测试平台工作表进行交互，包括查询待执行任务和更新任务状态
"""

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


class PlatformAPI:
    """测试平台API客户端"""

    # 默认字段ID配置（当配置文件不存在时使用）
    DEFAULT_FIELDS = {
        "task_id": "69cf92594f0b9c1e7f1da352",
        "standard_task": "69cf8fd84f0b9c1e7f1da34c",
        "model_list": "69cf8ed24f0b9c1e7f1da344",
        "exec_status": "69cf951d4f0b9c1e7f1da36e",
        "task_status": "69cf951d4f0b9c1e7f1da36e",
        "agent": "69d4c8c34f0b9c1e7f1da402",
        "exec_time": "69cf92594f0b9c1e7f1da353",
        "tokens": "69cf92594f0b9c1e7f1da354",
        "success": "69cf92594f0b9c1e7f1da355",
        "exec_date": "69d4da734f0b9c1e7f1da43a",
        "failure_reason": "69cf92594f0b9c1e7f1da356",
        "failure_analysis": "69cf92c04f0b9c1e7f1da36a",
        "judge_reason": "",
        "attachment": "69cf8d574f0b9c1e7f1da334",
        "success_criteria": "68303ff52f7dad5ce4aef33d"
    }

    def __init__(
        self,
        api_base: str = None,
        app_key: str = None,
        sign: str = None,
        worksheet_name: str = None,
        worksheet_id: str = None,
        view_id: str = None,
        config_path: str = None
    ):
        """
        初始化测试平台API客户端

        Args:
            api_base: API基础地址（默认从配置文件读取）
            app_key: 应用Key（默认从配置文件读取）
            sign: 签名（默认从配置文件读取）
            worksheet_name: 工作表名称（默认从配置文件读取default_worksheet）
            worksheet_id: 工作表ID（可选，覆盖配置文件）
            view_id: 视图ID（可选）
            config_path: 配置文件路径（可选）
        """
        # 加载配置文件
        config = load_config(config_path)
        platform_config = config.get("platform_api", {})

        # 使用传入参数或配置文件中的值
        self.api_base = api_base or platform_config.get("base_url", "http://10.8.12.22:8880/api/v2/open/worksheet")
        self.app_key = app_key or platform_config.get("app_key", "7cd1dae7bf786952")
        self.sign = sign or platform_config.get("sign", "ZDQwOWFjNzcwNzExZGQ4OGU5Nzg2ZmZiZTA5ZjhmOWQ5Y2EyZTdhYWY4NmYzM2VjYWEzMmEyMjM3ODZkYTAxYQ==")

        # 获取工作表配置
        worksheets_config = platform_config.get("worksheets", {})
        default_worksheet = platform_config.get("default_worksheet", "测试平台")
        self.worksheet_name = worksheet_name or default_worksheet

        # 获取指定工作表的配置
        if self.worksheet_name in worksheets_config:
            worksheet_config = worksheets_config[self.worksheet_name]
            self.worksheet_id = worksheet_id or worksheet_config.get("worksheet_id")
            self.view_id = view_id if view_id is not None else worksheet_config.get("view_id", "")
            fields_config = worksheet_config.get("fields", {})
        else:
            # 如果指定的工作表不存在，使用旧配置格式作为后备
            self.worksheet_id = worksheet_id or platform_config.get("worksheet_id", "69cf8d574f0b9c1e7f1da331")
            self.view_id = view_id if view_id is not None else platform_config.get("view_id", "")
            fields_config = platform_config.get("fields", {})

        self.session = requests.Session()

        # 从配置文件加载字段ID，使用默认值作为后备
        self.FIELD_TASK_ID = fields_config.get("task_id", self.DEFAULT_FIELDS["task_id"])
        self.FIELD_STANDARD_TASK = fields_config.get("standard_task", self.DEFAULT_FIELDS["standard_task"])
        self.FIELD_MODEL_LIST = fields_config.get("model_list", self.DEFAULT_FIELDS["model_list"])
        self.FIELD_TASK_STATUS = fields_config.get("task_status", self.DEFAULT_FIELDS["task_status"])
        self.FIELD_AGENT = fields_config.get("agent", self.DEFAULT_FIELDS["agent"])
        self.FIELD_EXEC_TIME = fields_config.get("exec_time", self.DEFAULT_FIELDS["exec_time"])
        self.FIELD_TOKENS = fields_config.get("tokens", self.DEFAULT_FIELDS["tokens"])
        self.FIELD_SUCCESS = fields_config.get("success", self.DEFAULT_FIELDS["success"])
        self.FIELD_EXEC_DATE = fields_config.get("exec_date", self.DEFAULT_FIELDS["exec_date"])
        self.FIELD_FAILURE_REASON = fields_config.get("failure_reason", self.DEFAULT_FIELDS["failure_reason"])
        self.FIELD_FAILURE_ANALYSIS = fields_config.get("failure_analysis", self.DEFAULT_FIELDS["failure_analysis"])
        self.FIELD_JUDGE_REASON = fields_config.get("judge_reason", self.DEFAULT_FIELDS["judge_reason"])
        self.FIELD_ATTACHMENT = fields_config.get("attachment", self.DEFAULT_FIELDS["attachment"])
        self.FIELD_SUCCESS_CRITERIA = fields_config.get("success_criteria", self.DEFAULT_FIELDS["success_criteria"])

        # 旧字段别名（保持兼容性）
        # FIELD_TASK_STATUS 用于存储测试结果（成功/失败/待定）
        # FIELD_EXEC_STATUS 用于存储执行状态（待执行/执行中/已完成）
        # 如果配置中没有单独的 exec_status 字段，则使用 task_status 字段
        self.FIELD_EXEC_STATUS = fields_config.get("exec_status", self.DEFAULT_FIELDS["exec_status"])
        self.FIELD_NAME = self.FIELD_TASK_ID

    def get_worksheet_headers(self) -> dict:
        """获取工作表API请求头"""
        return {"Content-Type": "application/json"}

    def query_pending_tasks(
        self,
        status: str = "待执行",
        page_size: int = 50,
        page_index: int = 1
    ) -> List[Dict]:
        """
        查询指定状态的待执行任务列表

        Args:
            status: 任务状态，默认"待执行"
            page_size: 每页数量
            page_index: 页码

        Returns:
            任务列表，每个任务是一个字典
        """
        print_status("正在查询待执行任务...", "📡")

        url = f"{self.api_base}/getFilterRows"

        # 使用 FIELD_EXEC_STATUS 来筛选任务（如果配置了的话）
        # 如果 exec_status 为空，则使用 FIELD_TASK_STATUS（向后兼容）
        status_field = self.FIELD_EXEC_STATUS if self.FIELD_EXEC_STATUS else self.FIELD_TASK_STATUS

        payload = {
            "appKey": self.app_key,
            "sign": self.sign,
            "worksheetId": self.worksheet_id,
            "pageSize": page_size,
            "pageIndex": page_index,
            "filters": [
                {
                    "controlId": status_field,
                    "dataType": 11,
                    "filterType": 2,
                    "value": status,
                    "valueType": 1
                }
            ]
        }

        # 只有当viewId不为空时才添加到payload
        if self.view_id:
            payload["viewId"] = self.view_id

        try:
            print_status(f"请求URL: {url}", "🔗")
            print_status(f"筛选条件: {status_field} = '{status}'", "🔍")
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_worksheet_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            print_status(f"API响应: code={result.get('code')}, success={result.get('success')}", "📨")

            if result.get("code") == 0 or result.get("success"):
                data = result.get("data", {})
                rows = data.get("rows", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                print_status(f"查询到 {len(rows)} 个待执行任务", "📋")
                return rows
            else:
                print_status(f"查询任务失败: {result.get('msg', result)}", "❌")
                return []

        except Exception as e:
            print_status(f"查询任务异常: {e}", "❌")
            return []

    def query_all_tasks(
        self,
        page_size: int = 50,
        page_index: int = 1
    ) -> List[Dict]:
        """
        查询所有任务（不筛选状态）

        Args:
            page_size: 每页数量
            page_index: 页码

        Returns:
            任务列表
        """
        print_status("正在查询所有任务...", "📡")

        url = f"{self.api_base}/getFilterRows"
        payload = {
            "appKey": self.app_key,
            "sign": self.sign,
            "worksheetId": self.worksheet_id,
            "pageSize": page_size,
            "pageIndex": page_index,
            "filters": []
        }

        # 只有当viewId不为空时才添加到payload
        if self.view_id:
            payload["viewId"] = self.view_id

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_worksheet_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0 or result.get("success"):
                data = result.get("data", {})
                rows = data.get("rows", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                print_status(f"查询到 {len(rows)} 个任务", "📋")
                return rows
            else:
                print_status(f"查询任务失败: {result.get('msg', result)}", "❌")
                return []

        except Exception as e:
            print_status(f"查询任务异常: {e}", "❌")
            return []

    def get_task_by_row_id(self, row_id: str) -> Optional[Dict]:
        """
        根据行ID获取任务详情

        Args:
            row_id: 行记录ID

        Returns:
            任务详情字典，失败返回None
        """
        print_status(f"正在获取任务详情: {row_id}", "📡")

        url = f"{self.api_base}/getRowByIdPost"
        payload = {
            "appKey": self.app_key,
            "sign": self.sign,
            "worksheetId": self.worksheet_id,
            "rowId": row_id
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self.get_worksheet_headers(),
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0 or result.get("success"):
                data = result.get("data", {})
                print_status(f"获取任务详情成功: {row_id}", "✅")
                return data
            else:
                print_status(f"获取任务详情失败: {result.get('msg', result)}", "❌")
                return None

        except Exception as e:
            print_status(f"获取任务详情异常: {e}", "❌")
            return None

    def get_model_name(self, task_data: Dict) -> str:
        """
        从任务数据中获取模型名称
        新表格中从"模型列联"字段（表关联类型）获取

        Args:
            task_data: 任务数据字典

        Returns:
            模型名称字符串
        """
        model_value = task_data.get(self.FIELD_MODEL_LIST, "")
        if not model_value:
            return "glm-4"

        # 如果是纯字符串（单选字段），直接返回
        if isinstance(model_value, str):
            # 先尝试解析为JSON（处理表关联字段的JSON字符串格式）
            try:
                import json
                parsed = json.loads(model_value)
                if isinstance(parsed, list) and len(parsed) > 0:
                    first_item = parsed[0]
                    if isinstance(first_item, dict):
                        return first_item.get("name", "glm-4")
                # 如果解析成功但不是列表格式，继续处理
            except (json.JSONDecodeError, TypeError):
                # JSON解析失败，说明是纯字符串（单选字段），直接返回
                return model_value

        # 如果是列表格式
        if isinstance(model_value, list) and len(model_value) > 0:
            first_item = model_value[0]
            if isinstance(first_item, dict):
                return first_item.get("name", "glm-4")
            elif isinstance(first_item, str):
                return first_item

        # 如果是字典格式
        if isinstance(model_value, dict):
            return model_value.get("name", "glm-4")

        return "glm-4"

    def get_agent_list(self, task_data: Dict) -> List[str]:
        """
        从任务数据中获取智能体列表

        Args:
            task_data: 任务数据字典

        Returns:
            智能体名称列表
        """
        agent_value = task_data.get(self.FIELD_AGENT, "")
        if not agent_value:
            return []

        agents = []

        # 表关联字段通常是JSON字符串格式
        if isinstance(agent_value, str):
            try:
                import json
                parsed = json.loads(agent_value)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            name = item.get("name", "")
                            if name:
                                agents.append(name)
                        elif isinstance(item, str):
                            agents.append(item)
                elif isinstance(parsed, dict):
                    name = parsed.get("name", "")
                    if name:
                        agents.append(name)
            except (json.JSONDecodeError, TypeError):
                pass

        # 如果是列表格式
        if isinstance(agent_value, list):
            for item in agent_value:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    if name:
                        agents.append(name)
                elif isinstance(item, str):
                    agents.append(item)

        # 如果是字典格式
        if isinstance(agent_value, dict):
            name = agent_value.get("name", "")
            if name:
                agents.append(name)

        return agents

    def parse_agent_tools(self, agent_value) -> List[str]:
        """
        解析智能体工具字符串或列表，返回工具列表

        Args:
            agent_value: 智能体字段值（可能是字符串、列表或字典）

        Returns:
            智能体工具名称列表
        """
        if not agent_value:
            return []

        if isinstance(agent_value, list):
            return [str(item).strip() for item in agent_value if item]

        if isinstance(agent_value, str):
            agent_value = agent_value.strip()
            if not agent_value or agent_value == "[]":
                return []

            try:
                import json
                parsed = json.loads(agent_value)
                if isinstance(parsed, list):
                    agent_tools = []
                    for item in parsed:
                        if isinstance(item, dict):
                            name = item.get("name", "")
                            if name:
                                agent_tools.append(name)
                        elif isinstance(item, str):
                            agent_tools.append(item.strip())
                    return agent_tools
            except json.JSONDecodeError:
                pass

            agent_tools = []
            for item in agent_value.replace("\n", ",").split(","):
                item = item.strip()
                if item:
                    agent_tools.append(item)
            return agent_tools

        return []

    def get_standard_task_info(self, task_data: Dict) -> Dict:
        """
        从任务数据中获取标准任务信息（表关联字段）

        Args:
            task_data: 任务数据字典

        Returns:
            标准任务信息字典，包含name等字段
        """
        standard_task_value = task_data.get(self.FIELD_STANDARD_TASK, "")
        if not standard_task_value:
            return {}

        # 表关联字段通常是JSON字符串格式
        if isinstance(standard_task_value, str):
            try:
                import json
                parsed = json.loads(standard_task_value)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed[0]
            except (json.JSONDecodeError, TypeError):
                pass

        # 如果是列表格式
        if isinstance(standard_task_value, list) and len(standard_task_value) > 0:
            return standard_task_value[0]

        # 如果是字典格式
        if isinstance(standard_task_value, dict):
            return standard_task_value

        return {}


# 便捷函数，用于快速创建平台API实例
def create_platform_api(
    api_base: str = None,
    app_key: str = None,
    sign: str = None,
    worksheet_name: str = None,
    worksheet_id: str = None,
    view_id: str = None,
    config_path: str = None
) -> PlatformAPI:
    """
    创建平台API实例的便捷函数

    使用默认值创建，或通过参数覆盖默认配置

    Args:
        api_base: API基础地址（可选）
        app_key: 应用Key（可选）
        sign: 签名（可选）
        worksheet_name: 工作表名称（可选，如"模型测评任务"、"一体机测试"、"标准任务测试"）
        worksheet_id: 工作表ID（可选）
        view_id: 视图ID（可选）
        config_path: 配置文件路径（可选）

    Returns:
        PlatformAPI实例
    """
    return PlatformAPI(
        api_base=api_base,
        app_key=app_key,
        sign=sign,
        worksheet_name=worksheet_name,
        worksheet_id=worksheet_id,
        view_id=view_id,
        config_path=config_path
    )