"""
LLM 长上下文能力自动测试脚本
自动测试 8k, 16k, 32k, 64k, 128k, 256k, 1M 上下文成功率
"""

import os
import json
import time
import random
import csv
import requests
import tiktoken
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict


# ==================== 配置区域 ====================
# 方式1: 直接在这里配置
CONFIG = {
    "base_url": "https://api.openai.com/v1",  # 你的 API Base URL
    "api_key": "your-api-key-here",            # 你的 API Key
    "model": "gpt-4",                          # 模型名称
}

# 测试配置
TEST_CONFIG = {
    "context_lengths": [8000, 16000, 32000, 64000, 128000, 256000, 1000000],  # 上下文长度
    "tests_per_length": 5,           # 每个长度测试次数
    "needle_depths": [0, 25, 50, 75, 100],  # 针的位置（百分比）
    "timeout": 120,                  # API 请求超时时间（秒）
    "max_tokens": 100,               # 模型最大输出 tokens
    "temperature": 0,                # 温度参数（0 使输出更确定）
}

# ==================== 评估配置（用于智能判断答案是否正确）====================
EVAL_CONFIG = {
    "base_url": "https://api.trustoken.cn/v1",
    "api_key": "sk-3KqNgManXsqmNRoV38712b75Ec4342Dc92Ca91B4A6C6B10d",
    "model": "glm-5",
    "timeout": 120,                   # 评估 API 超时时间（秒）
    "enabled": True,                 # 是否启用大模型评估（False 则使用本地匹配）
}

# 方式2: 从 config.json 文件加载（推荐）
# 如果 config.json 存在，会优先使用文件中的配置


class LongContextTester:
    """长上下文测试器"""

    def __init__(self, config: dict, test_config: dict):
        self.config = config
        self.test_config = test_config
        self.base_dir = Path(__file__).parent.parent
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)

        # 线程锁（用于并发打印和CSV写入）
        self.print_lock = threading.Lock()
        self.csv_lock = threading.Lock()
        self.completed_count = 0
        self.total_count = 0

        # Excel 详细日志缓存（用于批量写入）
        self.excel_rows = []  # 缓存所有测试行
        self.excel_lock = threading.Lock()

        # 尝试从配置文件加载
        self._load_config_from_file()

        # 验证配置
        self._validate_config()

        # 初始化 Token 编码器
        self.tokenizer = self._init_tokenizer()

        # 初始化 CSV 文件
        self.csv_filepath = self._init_csv_file()

        # Excel 文件路径
        excel_name = self.csv_filepath.stem.replace("test_log_", "test_report_") + ".xlsx"
        self.excel_filepath = self.results_dir / excel_name

        # 加载测试数据
        self.needles = self._load_needles()
        self.haystack = self._generate_haystack()

        # 测试结果
        self.results = []

    def _load_config_from_file(self):
        """从 config.json 加载配置"""
        config_file = self.base_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)

                # 合并配置（文件配置优先）
                if "api" in file_config:
                    self.config.update(file_config["api"])
                if "test" in file_config:
                    self.test_config.update(file_config["test"])

                print("已从 config.json 加载配置")
            except Exception as e:
                print(f"加载配置文件失败: {e}")

    def _validate_config(self):
        """验证配置"""
        if self.config.get("api_key") == "your-api-key-here":
            print("\n" + "!" * 70)
            print("警告: 请先配置 API 信息！")
            print("!" * 70)
            print("请编辑 config.json 文件，填写以下信息：")
            print("  - base_url: API Base URL")
            print("  - api_key: API Key")
            print("  - model: 模型名称")
            print("!" * 70)
            raise ValueError("请先配置 API 信息")

    def _init_tokenizer(self):
        """初始化 Token 编码器"""
        try:
            # 根据模型名称选择合适的编码器
            model_name = self.config.get("model", "")

            # 编码器映射表
            tokenizer_mapping = {
                "gpt-4": "cl100k_base",
                "gpt-4-": "cl100k_base",  # gpt-4-turbo, gpt-4o 等
                "gpt-3.5": "cl100k_base",
                "text-davinci": "p50k_base",
                "qwen": "o200k_base",      # 通义千问使用 cl100k_base 兼容
                "qwn": "o200k_base",        # QWN 模型
                "deepseek": "cl100k_base",  # DeepSeek
            }

            # 查找匹配的编码器
            encoding_name = "cl100k_base"  # 默认使用 GPT-4 的编码器
            for key, value in tokenizer_mapping.items():
                if key in model_name.lower():
                    encoding_name = value
                    break

            tokenizer = tiktoken.get_encoding(encoding_name)
            print(f"使用 Token 编码器: {encoding_name}")
            return tokenizer
        except Exception as e:
            print(f"初始化 Token 编码器失败: {e}，将使用字符估算方式")
            return None

    def _init_csv_file(self) -> Path:
        """初始化 CSV 文件并写入表头"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_log_{self.config['model'].replace('/', '_')}_{timestamp}.csv"
        filepath = self.results_dir / filename

        # CSV 表头
        headers = [
            "执行时间",
            "上下文长度",
            "针位置(%)",
            "Prompt长度(字符)",
            "Prompt(Tokens)",
            "输出结果",
            "期望答案",
            "是否成功",
            "响应时间(秒)",
            "输入Tokens",
            "输出Tokens",
            "总Tokens",
            "API状态"
        ]

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

        print(f"CSV 日志文件: {filepath}")
        return filepath

    def _write_csv_row(self, row_data: List[str]):
        """线程安全地写入 CSV 行，带重试机制"""
        retry_delays = [60, 180, 300]  # 1分钟、3分钟、5分钟（秒）

        with self.csv_lock:
            for attempt, delay in enumerate(retry_delays, 1):
                try:
                    with open(self.csv_filepath, 'a', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(row_data)
                    return  # 成功写入，退出
                except PermissionError as e:
                    if attempt < len(retry_delays):
                        print(f"    [警告] CSV 文件被占用，第 {attempt} 次写入失败，{delay//60} 分钟后重试...")
                        time.sleep(delay)
                    else:
                        print(f"    [错误] CSV 文件写入失败，已重试 {len(retry_delays)} 次")
                        print(f"    [提示] 请关闭文件: {self.csv_filepath}")
                        # 将失败的数据缓存到内存，稍后可尝试写入备份文件
                        self._cache_failed_row(row_data)
                except Exception as e:
                    print(f"    [错误] CSV 写入异常: {e}")
                    self._cache_failed_row(row_data)
                    return

    def _cache_failed_row(self, row_data: List[str]):
        """缓存写入失败的行到备份文件"""
        try:
            backup_file = self.csv_filepath.parent / f"{self.csv_filepath.stem}_backup.csv"
            # 如果备份文件不存在，先写入表头
            if not backup_file.exists():
                headers = [
                    "执行时间", "上下文长度", "针位置(%)", "Prompt长度(字符)",
                    "Prompt(Tokens)", "输出结果", "期望答案", "是否成功",
                    "响应时间(秒)", "输入Tokens", "输出Tokens", "总Tokens", "API状态"
                ]
                with open(backup_file, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
            # 追加失败的行
            with open(backup_file, 'a', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
            print(f"    [备份] 数据已写入备份文件: {backup_file.name}")
        except Exception as e:
            print(f"    [严重错误] 备份文件写入也失败: {e}")

    def _add_excel_row(self, row_data: List[str]):
        """添加行到 Excel 缓存"""
        with self.excel_lock:
            self.excel_rows.append(row_data)

    def _generate_excel_report(self, all_results: List[Dict]):
        """生成 Excel 测试报告"""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            print("未安装 openpyxl，跳过 Excel 报告生成。安装命令: pip install openpyxl")
            return

        # 创建工作簿
        wb = openpyxl.Workbook()
        ws1 = wb.active
        ws1.title = "详细日志"

        # Sheet1: 详细日志表头
        headers1 = [
            "执行时间", "上下文长度", "针位置(%)", "Prompt长度(字符)",
            "Prompt(Tokens)", "输出结果", "期望答案", "是否成功",
            "响应时间(秒)", "输入Tokens", "输出Tokens", "总Tokens", "API状态"
        ]
        ws1.append(headers1)

        # 表头样式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        for col_num, header in enumerate(headers1, 1):
            cell = ws1.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 写入详细日志数据
        for row_data in self.excel_rows:
            ws1.append(row_data)

        # 设置列宽
        column_widths = [20, 12, 10, 15, 15, 50, 30, 10, 12, 12, 12, 12, 10]
        for col_num, width in enumerate(column_widths, 1):
            ws1.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = width

        # Sheet2: 汇总统计报告
        ws2 = wb.create_sheet("汇总报告")

        # 计算汇总数据
        summary_data = self._calculate_summary(all_results)

        # 汇总报告表头
        headers2 = ["上下文长度", "针位置(%)", "测试次数", "成功次数", "成功率(%)", "平均响应时间(秒)"]
        ws2.append(headers2)

        for col_num, header in enumerate(headers2, 1):
            cell = ws2.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # 写入汇总数据
        for row in summary_data:
            ws2.append(row)

        # 设置列宽
        summary_widths = [15, 12, 12, 12, 12, 18]
        for col_num, width in enumerate(summary_widths, 1):
            ws2.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = width

        # 应用边框到所有数据行
        for ws in [ws1, ws2]:
            max_row = ws.max_row
            max_col = ws.max_column
            for row in ws.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col):
                for cell in row:
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

        # 冻结首行
        ws1.freeze_panes = "A2"
        ws2.freeze_panes = "A2"

        # 保存 Excel 文件
        wb.save(self.excel_filepath)
        print(f"\nExcel 测试报告已保存: {self.excel_filepath}")

    def _calculate_summary(self, all_results: List[Dict]) -> List[List[str]]:
        """计算汇总统计数据"""
        # 按上下文长度和针位置分组统计
        stats = defaultdict(lambda: {"total": 0, "success": 0, "times": []})

        for result in all_results:
            key = (result["context_length"], result["needle_depth"])
            stats[key]["total"] += 1
            if result["is_correct"]:
                stats[key]["success"] += 1
            stats[key]["times"].append(result["response_time"])

        # 获取所有唯一的上下文长度和针位置
        context_lengths = sorted(set(k[0] for k in stats.keys()))
        needle_depths = sorted(set(k[1] for k in stats.keys()))

        summary_rows = []
        summary_rows.append(["=== 按上下文长度分组 ==="])
        for ctx_len in context_lengths:
            total = sum(stats[(ctx_len, d)]["total"] for d in needle_depths if (ctx_len, d) in stats)
            success = sum(stats[(ctx_len, d)]["success"] for d in needle_depths if (ctx_len, d) in stats)
            times = []
            for d in needle_depths:
                if (ctx_len, d) in stats:
                    times.extend(stats[(ctx_len, d)]["times"])
            avg_time = sum(times) / len(times) if times else 0
            rate = (success / total * 100) if total > 0 else 0
            label = f"{ctx_len//1000}k" if ctx_len < 1000000 else "1M"
            summary_rows.append([label, "全部", total, success, f"{rate:.1f}", f"{avg_time:.2f}"])

        summary_rows.append([])
        summary_rows.append(["=== 按针位置分组 ==="])
        for depth in needle_depths:
            total = sum(stats[(l, depth)]["total"] for l in context_lengths if (l, depth) in stats)
            success = sum(stats[(l, depth)]["success"] for l in context_lengths if (l, depth) in stats)
            times = []
            for l in context_lengths:
                if (l, depth) in stats:
                    times.extend(stats[(l, depth)]["times"])
            avg_time = sum(times) / len(times) if times else 0
            rate = (success / total * 100) if total > 0 else 0
            summary_rows.append(["全部", depth, total, success, f"{rate:.1f}", f"{avg_time:.2f}"])

        summary_rows.append([])
        summary_rows.append(["=== 详细统计（每个组合）==="])
        # 详细统计表头
        detail_headers = ["上下文长度", "针位置(%)", "测试次数", "成功次数", "成功率(%)", "平均响应时间(秒)"]
        summary_rows.extend(detail_headers)

        # 按上下文长度和针位置排序输出
        for ctx_len in context_lengths:
            for depth in needle_depths:
                key = (ctx_len, depth)
                if key in stats:
                    data = stats[key]
                    rate = (data["success"] / data["total"] * 100) if data["total"] > 0 else 0
                    avg_time = sum(data["times"]) / len(data["times"]) if data["times"] else 0
                    label = f"{ctx_len//1000}k" if ctx_len < 1000000 else "1M"
                    summary_rows.append([
                        label, depth, data["total"], data["success"],
                        f"{rate:.1f}", f"{avg_time:.2f}"
                    ])

        return summary_rows

    def _count_tokens(self, text: str) -> int:
        """精确计算文本的 Token 数量"""
        if self.tokenizer is None:
            # 回退到估算方式：中文约 1.5 字符/token，英文约 4 字符/token
            # 混合文本取中间值 2 字符/token
            return len(text) // 2
        return len(self.tokenizer.encode(text))

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """将文本截断到指定的 Token 数量"""
        if self.tokenizer is None:
            # 回退到字符估算
            target_chars = max_tokens * 2
            return text[:target_chars]

        # 使用 tiktoken 精确截断
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens)

    def _load_needles(self) -> List[Dict]:
        """加载测试针数据"""
        needles_file = self.base_dir / "data" / "needles" / "example_facts.json"
        if needles_file.exists():
            with open(needles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("needles", [])

        # 如果文件不存在，使用默认数据
        return [
            {
                "id": "fact_001",
                "content": "魔法数字是 9527",
                "question": "文中提到的魔法数字是什么？",
                "expected_answer": "9527",
            },
            {
                "id": "fact_002",
                "content": "API 密钥是 SK-2025-ABCD-1234-EFGH",
                "question": "API 密钥是什么？",
                "expected_answer": "SK-2025-ABCD-1234-EFGH",
            },
            {
                "id": "fact_003",
                "content": "服务器地址是 192.168.1.100:8080",
                "question": "服务器的地址和端口是什么？",
                "expected_answer": "192.168.1.100:8080",
            },
            {
                "id": "fact_004",
                "content": "项目代号是 PHOENIX-RISE-2025",
                "question": "项目代号是什么？",
                "expected_answer": "PHOENIX-RISE-2025",
            },
            {
                "id": "fact_005",
                "content": "关键日期是 2025年12月31日",
                "question": "关键日期是什么？",
                "expected_answer": "2025年12月31日",
            },
        ]

    def _generate_haystack(self) -> str:
        """生成草垛文本（填充内容）"""
        content_pieces = []

        # 多样化内容，避免重复
        templates = [
            "在{domain}领域，{concept}是一个重要的概念。研究表明，{detail}。",
            "根据{source}的报道，{subject}在{time}期间取得了显著进展。",
            "专家指出，{topic}的发展对{industry}产生了深远影响。",
            "{company}发布的报告显示，{metric}在过去一年中增长了{percent}%。",
            "从{perspective}角度来看，{issue}的解决需要{approach}方法。",
            "数据表明，{phenomenon}在{context}环境下表现出{characteristic}特征。",
            "研究人员发现，{element}与{factor}之间存在显著相关性。",
            "在{scenario}情况下，{strategy}被认为是最有效的解决方案。",
            "{technology}的普及使得{application}变得更加普及和便捷。",
            "历史经验告诉我们，{lesson}对于{future}具有重要参考价值。",
        ]

        domains = ["人工智能", "云计算", "区块链", "量子计算", "生物技术", "新能源", "航天技术"]
        concepts = ["机器学习", "分布式系统", "去中心化", "量子纠缠", "基因编辑", "储能技术", "深空探测"]
        sources = ["国际期刊", "行业报告", "权威机构", "研究团队", "学术会议"]
        subjects = ["模型性能", "系统稳定性", "网络效率", "计算精度", "编辑成功率", "能量密度", "推进系统"]
        times = ["2023年", "2024年", "2025年", "近年来", "过去十年"]
        topics = ["大语言模型", "微服务架构", "Web3技术", "量子优势", "CRISPR技术", "固态电池", "可回收火箭"]
        industries = ["软件开发", "金融服务", "医疗健康", "教育培训", "制造业", "交通运输"]
        companies = ["知名咨询公司", "科技巨头", "研究机构", "行业协会"]
        metrics = ["用户规模", "处理速度", "准确率", "市场份额", "投资回报", "满意度"]
        percents = ["15", "25", "35", "45", "55"]
        perspectives = ["技术", "商业", "社会", "政策", "伦理"]
        issues = ["数据隐私", "算法偏见", "能源消耗", "就业影响", "监管合规"]
        approaches = ["综合", "多学科", "协作", "创新", "渐进"]
        phenomena = ["网络效应", "规模经济", "学习曲线", "边际效用", "路径依赖"]
        contexts = ["竞争", "合作", "监管", "创新", "转型"]
        characteristics = ["稳定", "动态", "复杂", "不确定", "非线性"]
        elements = ["数据质量", "算力资源", "算法优化", "用户体验", "安全防护"]
        factors = ["模型性能", "部署成本", "开发周期", "维护难度", "扩展能力"]
        scenarios = ["高并发", "大数据", "实时处理", "多用户", "跨平台"]
        strategies = ["负载均衡", "缓存优化", "异步处理", "分布式架构", "容器化部署"]
        technologies = ["5G网络", "边缘计算", "物联网", "云计算", "人工智能"]
        applications = ["远程办公", "在线教育", "智慧医疗", "智能制造", "自动驾驶"]
        lessons = ["技术创新", "用户体验", "生态建设", "风险管控", "长期投入"]
        futures = ["产品迭代", "业务拓展", "产业升级", "数字化转型", "可持续发展"]

        # 生成大量内容
        all_vars = [
            domains, concepts, sources, subjects, times, topics, industries, companies,
            metrics, percents, perspectives, issues, approaches, phenomena, contexts,
            characteristics, elements, factors, scenarios, strategies, technologies,
            applications, lessons, futures
        ]

        # 生成足够长的内容
        for i in range(50000):
            template = templates[i % len(templates)]
            # 随机填充变量
            text = template.format(
                domain=random.choice(domains),
                concept=random.choice(concepts),
                detail=random.choice(["这一发现具有重要意义", "相关研究仍在进行中", "实际应用效果显著"]),
                source=random.choice(sources),
                subject=random.choice(subjects),
                time=random.choice(times),
                topic=random.choice(topics),
                industry=random.choice(industries),
                company=random.choice(companies),
                metric=random.choice(metrics),
                percent=random.choice(percents),
                perspective=random.choice(perspectives),
                issue=random.choice(issues),
                approach=random.choice(approaches),
                phenomenon=random.choice(phenomena),
                context=random.choice(contexts),
                characteristic=random.choice(characteristics),
                element=random.choice(elements),
                factor=random.choice(factors),
                scenario=random.choice(scenarios),
                strategy=random.choice(strategies),
                technology=random.choice(technologies),
                application=random.choice(applications),
                lesson=random.choice(lessons),
                future=random.choice(futures),
            )
            content_pieces.append(text)

        return "\n\n".join(content_pieces)

    def _create_test_prompt(self, context_length: int, needle_depth: int, needle: Optional[Dict] = None) -> Tuple[str, str]:
        """
        创建测试提示词（带长针补偿）

        Args:
            context_length: 上下文长度（tokens）
            needle_depth: 针的深度位置（百分比）
            needle: 指定的针（None则随机选择）

        Returns:
            (prompt, expected_answer)
        """
        # 选择针（如果指定则使用指定的，否则随机选择）
        if needle is None:
            needle = random.choice(self.needles)
        expected = needle["expected_answer"]

        # 插入针的文本
        needle_text = f"\n>>> 关键信息: {needle['content']} <<<\n"
        needle_tokens = self._count_tokens(needle_text)

        # ========== 精确上下文长度控制 ==========
        # 目标：让实际发送长度 = context_length（精确匹配）
        # 策略：草垛空间 = context_length - needle_tokens
        # 然后按 needle_depth 比例分配 before 和 after

        # 计算草垛可用空间（总长度减去针本身）
        haystack_available = context_length - needle_tokens

        # 如果针太长，草垛空间为负或太小，给予警告
        if haystack_available < context_length * 0.1:
            print(f"    [警告] 针太大 ({needle_tokens} tokens)，占上下文 {needle_tokens/context_length:.1%}，草垛空间不足")

        # 计算针的位置（按草垛空间的百分比）
        needle_position_tokens = int(haystack_available * needle_depth / 100)

        # 计算前后的草垛数量
        before_tokens = needle_position_tokens
        after_tokens = haystack_available - needle_position_tokens

        # 实际发送的总长度应该精确等于 context_length
        actual_total = before_tokens + needle_tokens + after_tokens
        # ==================================

        # 获取并截断草垛内容
        before_text = self._truncate_to_tokens(self.haystack, before_tokens)
        after_text = self._truncate_to_tokens(self.haystack, after_tokens)

        # 构建上下文
        context = before_text + needle_text + after_text

        # 验证并调整上下文长度（确保精确匹配目标）
        actual_tokens = self._count_tokens(context)
        if actual_tokens > context_length:
            # 如果超出，重新截断
            excess_tokens = actual_tokens - context_length
            after_text = self._truncate_to_tokens(after_text, max(0, after_tokens - excess_tokens))
            context = before_text + needle_text + after_text

        # 调试信息：显示针的占用情况
        needle_ratio = needle_tokens / context_length
        if needle_ratio > 0.1:  # 针超过10%时显示
            print(f"    [长针] 占 {needle_ratio:.1%} ({needle_tokens} tokens)，草垛 {haystack_available} tokens，实际总长 ~{context_length}")

        # 构建提示词
        prompt = f"""

内容：
{context}

问题：{needle['question']}

请直接给出答案，不要添加任何解释："""

        return prompt, expected

    def _call_api(self, prompt: str, prompt_tokens: int) -> Tuple[str, float, bool, Dict[str, int]]:
        """
        调用 LLM API

        Args:
            prompt: 提示词
            prompt_tokens: 提示词的 token 数量

        Returns:
            (response_text, response_time, success, token_stats)
        """
        headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.config["model"],
            "messages": [
                {
                    "role": "system",
                    "content": "完成任务只给出答案，不要添加任何解释。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.test_config["max_tokens"],
            "temperature": self.test_config["temperature"],
        }

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.config['base_url']}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.test_config["timeout"]
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                message = result["choices"][0]["message"]

                # 处理带推理过程的模型（content 可能为 null）
                answer = message.get("content")
                if answer is None:
                    # 尝试从 reasoning_content 获取
                    answer = message.get("reasoning_content", "")

                if not answer:
                    token_stats = {
                        "input": prompt_tokens,
                        "output": 0,
                        "total": prompt_tokens
                    }
                    return "API 返回空内容", response_time, False, token_stats

                # 获取 token 使用统计
                usage = result.get("usage", {})
                if usage:
                    input_tokens = usage.get("prompt_tokens", prompt_tokens)
                    output_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
                else:
                    # 如果 API 没有返回 usage，使用 tokenizer 计算
                    output_tokens = self._count_tokens(str(answer).strip())
                    input_tokens = prompt_tokens
                    total_tokens = input_tokens + output_tokens

                token_stats = {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens
                }

                return str(answer).strip(), response_time, True, token_stats
            else:
                token_stats = {
                    "input": prompt_tokens,
                    "output": 0,
                    "total": prompt_tokens
                }
                return f"API 错误: {response.status_code} - {response.text}", response_time, False, token_stats

        except requests.exceptions.Timeout:
            token_stats = {
                "input": prompt_tokens,
                "output": 0,
                "total": prompt_tokens
            }
            return "请求超时", time.time() - start_time, False, token_stats
        except Exception as e:
            token_stats = {
                "input": prompt_tokens,
                "output": 0,
                "total": prompt_tokens
            }
            return f"请求失败: {str(e)}", time.time() - start_time, False, token_stats

    def _evaluate_answer(self, expected: str, actual: str) -> bool:
        """使用大模型评估答案是否正确"""
        # 如果评估功能被禁用，直接使用本地匹配
        if not EVAL_CONFIG.get("enabled", True):
            return self._local_match(expected, actual)

        prompt = f"""你是一个精确的答案评估助手。请判断"实际答案"是否正确回答了问题。

【期望答案】：{expected}

【实际答案】：{actual}

评估标准：
1. 核心信息必须一致（如数字、日期、关键术语）
2. 格式、空格、标点符号的差异不影响正确性
3. 语义等价的表达应判定为正确

请只返回 "true" 或 "false"，不要添加任何解释："""

        try:
            headers = {
                "Authorization": f"Bearer {EVAL_CONFIG['api_key']}",
                "Content-Type": "application/json",
            }

            data = {
                "model": EVAL_CONFIG["model"],
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个精确的答案评估助手。请严格按照标准评估答案是否正确，只返回 true 或 false。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 10,
                "temperature": 0,
            }

            response = requests.post(
                f"{EVAL_CONFIG['base_url']}/chat/completions",
                headers=headers,
                json=data,
                timeout=EVAL_CONFIG.get("timeout", 30)
            )

            if response.status_code == 200:
                result = response.json()
                answer = result["choices"][0]["message"]["content"]
                # 清理并判断结果
                answer_clean = answer.strip().lower()
                return answer_clean in ["true", "正确", "yes", "是"]

        except Exception as e:
            print(f"    [评估API调用失败: {e}，使用本地匹配]")

        # 回退到本地匹配逻辑
        return self._local_match(expected, actual)

    def _local_match(self, expected: str, actual: str) -> bool:
        """本地字符串匹配逻辑（作为评估API的回退方案）"""
        import re

        expected_clean = expected.lower().strip()
        actual_clean = actual.lower().strip()

        if expected_clean in actual_clean:
            return True

        expected_no_space = re.sub(r'\s+', '', expected_clean)
        actual_no_space = re.sub(r'\s+', '', actual_clean)
        if expected_no_space in actual_no_space:
            return True

        return False

    def run_single_test(self, context_length: int, needle_depth: int, needle: Optional[Dict] = None) -> Dict:
        """运行单次测试"""
        print(f"  测试 {context_length//1000}k 上下文，位置 {needle_depth}%...", end=" ")

        # 创建测试用例
        prompt, expected = self._create_test_prompt(context_length, needle_depth, needle)
        prompt_tokens = self._count_tokens(prompt)

        # 调用 API
        actual, response_time, api_success, token_stats = self._call_api(prompt, prompt_tokens)

        # 评估结果
        if api_success:
            is_correct = self._evaluate_answer(expected, actual)
            status = "[OK]" if is_correct else "[FAIL]"
        else:
            is_correct = False
            status = "[ERROR]"

        print(f"{status} ({response_time:.1f}s)")

        # 如果失败，打印详细信息
        if not is_correct and api_success:
            print(f"    期望: {expected}")
            print(f"    实际: {actual[:100]}{'...' if len(actual) > 100 else ''}")

        # 写入 CSV
        csv_row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{context_length//1000}k" if context_length < 1000000 else "1M",
            needle_depth,
            len(prompt),
            prompt_tokens,
            actual[:500] + "..." if len(actual) > 500 else actual,  # 截断长输出
            expected,
            "成功" if is_correct else "失败",
            f"{response_time:.2f}",
            token_stats["input"],
            token_stats["output"],
            token_stats["total"],
            "成功" if api_success else "失败"
        ]
        self._write_csv_row(csv_row)

        # 同时写入 Excel 缓存
        self._add_excel_row(csv_row)

        return {
            "context_length": context_length,
            "needle_depth": needle_depth,
            "expected": expected,
            "actual": actual,
            "is_correct": is_correct,
            "response_time": response_time,
            "api_success": api_success,
            "token_stats": token_stats,
            "prompt": prompt,
        }

    def run_single_test_threaded(self, context_length: int, needle_depth: int, index: int, total: int, needle: Optional[Dict] = None) -> Dict:
        """运行单次测试（线程安全版本）"""
        length_label = f"{context_length//1000}k" if context_length < 1000000 else "1M"

        with self.print_lock:
            self.completed_count += 1
            print(f"  [{self.completed_count}/{total}] 测试 {length_label} 位置 {needle_depth}%...", end=" ", flush=True)

        # 创建测试用例
        prompt, expected = self._create_test_prompt(context_length, needle_depth, needle)
        prompt_tokens = self._count_tokens(prompt)

        # 调用 API
        actual, response_time, api_success, token_stats = self._call_api(prompt, prompt_tokens)

        # 评估结果
        if api_success:
            is_correct = self._evaluate_answer(expected, actual)
            status = "[OK]" if is_correct else "[FAIL]"
        else:
            is_correct = False
            status = "[ERROR]"

        with self.print_lock:
            print(f"{status} ({response_time:.1f}s)")

        # 实时写入 CSV（线程安全）
        csv_row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            f"{context_length//1000}k" if context_length < 1000000 else "1M",
            needle_depth,
            len(prompt),
            prompt_tokens,
            actual[:500] + "..." if len(actual) > 500 else actual,  # 截断长输出
            expected,
            "成功" if is_correct else "失败",
            f"{response_time:.2f}",
            token_stats["input"],
            token_stats["output"],
            token_stats["total"],
            "成功" if api_success else "失败"
        ]
        self._write_csv_row(csv_row)

        # 同时写入 Excel 缓存
        self._add_excel_row(csv_row)

        return {
            "context_length": context_length,
            "needle_depth": needle_depth,
            "expected": expected,
            "actual": actual,
            "is_correct": is_correct,
            "response_time": response_time,
            "api_success": api_success,
            "token_stats": token_stats,
            "prompt": prompt,
        }

    def run_all_tests(self) -> List[Dict]:
        """运行所有测试（支持并发）"""
        # 获取并发数
        concurrent = self.test_config.get("concurrent_requests", 1)

        print("=" * 70)
        print("LLM 长上下文能力测试")
        print("=" * 70)
        print(f"模型: {self.config['model']}")
        print(f"测试长度: {', '.join([str(l//1000) + 'k' if l < 1000000 else '1M' for l in self.test_config['context_lengths']])}")
        print(f"针数量: {len(self.needles)} 个（每个位置遍历全部，不重复）")
        print(f"测试位置: {self.test_config['needle_depths']}")
        print(f"每个长度测试数: {len(self.needles)} × {len(self.test_config['needle_depths'])} = {len(self.needles) * len(self.test_config['needle_depths'])} 个")
        print(f"并发数: {concurrent}")
        print("=" * 70)
        print()

        all_results = []
        self.completed_count = 0

        # 计算总测试数
        total_tests = (len(self.test_config["context_lengths"]) *
                       len(self.needles) *
                       len(self.test_config["needle_depths"]))
        self.total_count = total_tests

        # 为每个上下文长度创建测试任务
        for context_length in self.test_config["context_lengths"]:
            print(f"\n{'='*70}")
            length_label = f"{context_length//1000}k" if context_length < 1000000 else "1M"
            print(f"测试上下文长度: {length_label} ({context_length} tokens)")
            print(f"{'='*70}")

            length_results = []
            test_tasks = []

            # 方式A: 每个位置独立遍历所有针（不重复）
            # 每个位置用全部20个针，共 5位置 × 20针 = 100 个测试
            for needle_depth in self.test_config["needle_depths"]:
                for needle in self.needles:
                    test_tasks.append((context_length, needle_depth, needle))

            # 使用线程池并发执行
            with ThreadPoolExecutor(max_workers=concurrent) as executor:
                futures = {
                    executor.submit(self.run_single_test_threaded, length, depth, idx, len(test_tasks), needle): (idx, length, depth)
                    for idx, (length, depth, needle) in enumerate(test_tasks)
                }

                for future in as_completed(futures):
                    result = future.result()
                    length_results.append(result)
                    all_results.append(result)

            # 打印当前长度统计
            correct = sum(1 for r in length_results if r["is_correct"])
            total = len(length_results)
            success_rate = (correct / total * 100) if total > 0 else 0

            print(f"\n{length_label} 统计: {correct}/{total} 成功, 成功率: {success_rate:.1f}%")

        # 生成 Excel 测试报告
        self._generate_excel_report(all_results)

        return all_results

    def generate_summary_table(self, results: List[Dict]):
        """生成汇总表格"""
        print("\n" + "=" * 70)
        print("测试结果汇总")
        print("=" * 70)

        # 按上下文长度分组
        summary = []

        for context_length in self.test_config["context_lengths"]:
            length_results = [r for r in results if r["context_length"] == context_length]

            total = len(length_results)
            success = sum(1 for r in length_results if r["is_correct"])
            rate = (success / total * 100) if total > 0 else 0
            avg_time = sum(r["response_time"] for r in length_results) / total if total > 0 else 0

            length_label = f"{context_length//1000}k" if context_length < 1000000 else "1M"

            summary.append({
                "context_length": length_label,
                "context_tokens": context_length,
                "total_tests": total,
                "success_count": success,
                "success_rate": rate,
                "avg_time": avg_time,
            })

        # 打印表格
        print(f"\n{'上下文':<10} {'测试数量':<10} {'成功数量':<10} {'成功率':<10} {'平均耗时':<10}")
        print("-" * 70)

        for s in summary:
            print(f"{s['context_length']:<10} {s['total_tests']:<10} {s['success_count']:<10} {s['success_rate']:<9.1f}% {s['avg_time']:<9.1f}s")

        # 打印总体统计
        total_tests = sum(s["total_tests"] for s in summary)
        total_success = sum(s["success_count"] for s in summary)
        overall_rate = (total_success / total_tests * 100) if total_tests > 0 else 0

        print("-" * 70)
        print(f"{'总计':<10} {total_tests:<10} {total_success:<10} {overall_rate:<9.1f}%")
        print("=" * 70)

        # 保存结果到文件
        self._save_results(summary, results)

        return summary

    def _save_results(self, summary: List[Dict], all_results: List[Dict]):
        """保存测试结果到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{self.config['model'].replace('/', '_')}_{timestamp}.json"
        filepath = self.results_dir / filename

        # 提取失败用例
        failed_cases = [r for r in all_results if not r["is_correct"]]

        output = {
            "config": {
                "model": self.config["model"],
                "base_url": self.config["base_url"],
                "test_time": datetime.now().isoformat(),
            },
            "summary": summary,
            "all_results": all_results,
            "failed_cases": failed_cases,
            "failed_count": len(failed_cases),
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n详细结果已保存到: {filepath}")

        # 单独保存失败用例
        if failed_cases:
            failed_filename = f"failed_cases_{self.config['model'].replace('/', '_')}_{timestamp}.json"
            failed_filepath = self.results_dir / failed_filename

            with open(failed_filepath, 'w', encoding='utf-8') as f:
                json.dump(failed_cases, f, ensure_ascii=False, indent=2)

            print(f"失败用例已保存到: {failed_filepath}")

            # 打印失败用例摘要
            print(f"\n{'='*70}")
            print("失败用例摘要")
            print(f"{'='*70}")

            for i, case in enumerate(failed_cases[:10], 1):  # 只显示前10个
                length_label = f"{case['context_length']//1000}k" if case['context_length'] < 1000000 else "1M"
                print(f"\n{i}. {length_label} 上下文，位置 {case['needle_depth']}%")
                print(f"   期望: {case['expected']}")
                actual = case['actual']
                if len(actual) > 80:
                    actual = actual[:80] + "..."
                print(f"   实际: {actual}")

            if len(failed_cases) > 10:
                print(f"\n... 还有 {len(failed_cases) - 10} 个失败用例，详见文件")

            print(f"{'='*70}")


def main():
    """主函数"""
    try:
        # 创建测试器
        tester = LongContextTester(CONFIG, TEST_CONFIG)

        # 运行测试
        results = tester.run_all_tests()

        # 生成汇总表格
        summary = tester.generate_summary_table(results)

    except ValueError as e:
        print(f"\n错误: {e}")
    except KeyboardInterrupt:
        print("\n\n测试已中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
