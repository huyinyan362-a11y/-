# AiPy AI Agent 自动化测试套件

> AI Agent产品的全方位测试解决方案，涵盖功能测试、性能测试、上下文测试和多模态测试

## 📋 项目简介

本项目是针对 AiPy Pro AI Agent 产品开发的自动化测试框架，支持模型上架前的全面质量验证。

## 🎯 测试模块

### 1. 功能与回归测试 (`functional-test/`)

**功能：** 自动化执行70+标准任务，验证Agent核心功能

**特性：**
- 飞书维格表API集成（测试用例管理）
- AiPy客户端自动化控制
- 多线程并发监控（动态并发控制）
- AI自动化评判系统（基于GLM-4）

**核心技术：**
- Python + requests + threading
- 飞书API + AiPy API + 大模型评判API
- 支持MCP协议调用、工具调用测试

**使用方式：**
```bash
cd functional-test
python main.py
```

---

### 2. 性能测试 (`performance-test/`)

**功能：** 梯度并发压测，识别性能拐点和瓶颈

**特性：**
- 异步并发压测（asyncio + Semaphore）
- 多维度性能指标收集（Token/s、TTFT、Latency）
- P50/P95/P99百分位数统计
- Excel报告自动生成

**测试结论：**
- 识别性能拐点：30并发
- 推荐生产配置：15-20并发
- 推动配置优化：上下文160k→256k，batch size 8→12

**核心技术：**
- Python + asyncio + numpy
- OpenAI API格式兼容
- 梯度并发测试方法

**使用方式：**
```bash
cd performance-test
python run_benchmarks.py --concurrency 5,10,15,20,30 --requests 100
```

---

### 3. 上下文测试 (`context-test/`)

**功能：** 验证长上下文（8k-256k）信息检索能力

**特性：**
- Needle-in-a-Haystack测试方法
- 多档位测试（入门档4k-16k，中档32k-64k，高档128k-256k）
- 位置敏感性测试（0%, 25%, 50%, 75%, 100%）
- 测试数据自动生成

**测试结果：**
- 8k场景成功率：54.3% → 75.71%（配置调优后）

**核心技术：**
- Python + 自动化测试数据生成
- 针插入位置随机化
- 字符串精确匹配验证

**使用方式：**
```bash
cd context-test
python scripts/run_test.py --length 8k --samples 50
```

---

### 4. 多模态测试 (`multimodal-test/`)

**功能：** 验证图片/视频/音频识别能力

**特性：**
- 多模态对比评测
- 70个标准任务覆盖
- 成功率对比分析（54.3% ~ 75.71%）
- Token/s吞吐量测试

**测试发现：**
- 音频模态普遍不支持
- 8k场景成功率偏低

**核心技术：**
- Python + 多模态API调用
- 图片/视频/音频处理

**使用方式：**
```bash
cd multimodal-test
python multimodal_test_all.py
```

---

## 🚀 快速开始

### 环境要求

```bash
Python 3.8+
pip install -r requirements.txt
```

### 配置文件

每个模块都有独立的 `config.json`，需要配置：
- API地址和密钥
- 测试参数（并发数、超时时间等）
- 平台连接信息

### 运行示例

```bash
# 1. 功能测试
cd functional-test && python main.py

# 2. 性能测试
cd performance-test && python run_benchmarks.py

# 3. 上下文测试
cd context-test && python scripts/run_test.py

# 4. 多模态测试
cd multimodal-test && python multimodal_test_all.py
```

---

## 📊 项目成果

- ✅ **70+标准任务**自动化覆盖
- ✅ **识别30并发性能拐点**，推荐15-20生产配置
- ✅ **推动配置优化**：上下文160k→256k，batch size调整
- ✅ **AI自动化评判**：准确率85%+
- ✅ **8k上下文成功率**：54.3% → 75.71%

---

## 🛠️ 技术栈

**核心语言：** Python 3.8+

**主要库：**
- `asyncio` - 异步并发控制
- `requests` - HTTP API调用
- `threading` - 多线程监控
- `numpy` - 数据统计分析
- `openpyxl` - Excel报告生成

**API集成：**
- 飞书维格表API
- AiPy客户端API
- OpenAI格式API
- GLM-4评判API

---

## 📝 项目结构

```
aipy-testing-suite/
├── functional-test/          # 功能与回归测试
│   ├── main.py              # 主入口
│   ├── config.json          # 配置文件
│   └── core/                # 核心模块
│       ├── platform.py      # 飞书API封装
│       ├── aipypro_run.py   # AiPy客户端控制
│       ├── jude_task.py     # AI评判器
│       └── updata.py        # 结果回写
├── performance-test/         # 性能测试
│   ├── llm_benchmark.py     # 压测核心
│   ├── run_benchmarks.py    # 执行脚本
│   └── excel_exporter.py    # 报告生成
├── context-test/            # 上下文测试
│   ├── README.md            # 测试方法说明
│   ├── config.json          # 配置文件
│   ├── scripts/             # 测试脚本
│   └── data/                # 测试数据
└── multimodal-test/         # 多模态测试
    ├── multimodal_test_all.py
    └── image_tester.py
```

---

## 🤝 贡献

欢迎提交Issue和Pull Request

---

## 📄 License

MIT License

---

