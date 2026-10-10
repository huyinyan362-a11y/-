# LLM 长上下文能力测试集

## 📋 测试集概述

本测试集用于评估大型语言模型在 256k 上下文长度下的能力表现，采用分档测试策略。

---

## 🎯 测试方法论

### 核心评估方法

#### 1. Needle-in-a-Haystack（大海捞针）
将关键信息（针）随机插入长文本（草垛）中，测试模型能否准确提取关键信息。

#### 2. Multi-Needle（多针测试）
在长文本中插入多个关键信息，测试模型同时提取多个目标的能力。

#### 3. Sequential-NIAH（顺序针提取）
测试模型按顺序提取多个关键信息的能力。

#### 4. 长文本理解任务
基于长文本的问答、摘要、推理任务。

---

## 📊 测试分档方案

### 档位设计

| 档位 | 上下文长度 | Token 数量 | 测试目标 |
|------|-----------|-----------|---------|
| 入门档 | 4k - 16k | 4,000 - 16,000 | 基础长文本理解 |
| 中档 | 32k - 64k | 32,000 - 64,000 | 中等长度信息提取 |
| 高档 | 128k - 256k | 128,000 - 256,000 | 长上下文极限测试 |

### 各档位详细配置

#### 🟢 入门档 (4k - 16k tokens)

**适用场景**: 基础长文本能力验证

**测试类型**:
- 单针提取 (Single Needle)
  - 针深度位置: 0%, 25%, 50%, 75%, 100%
  - 测试样本数: 50 个

- 短文本问答
  - 文本长度: 2000-4000 tokens
  - 问题类型: 事实性、推理型
  - 样本数: 30 个

**评分标准**:
- 准确率 >= 90%: 通过
- 准确率 70-90%: 勉强通过
- 准确率 < 70%: 不通过

#### 🟡 中档 (32k - 64k tokens)

**适用场景**: 中长文本信息提取与理解

**测试类型**:
- 单针提取
  - 针深度位置: 10%, 30%, 50%, 70%, 90%
  - 测试样本数: 100 个

- 多针提取 (Multi-Needle, 3-5 针)
  - 针数量: 3, 5 个
  - 测试样本数: 各 50 个

- 长文档问答
  - 文本长度: 16000-32000 tokens
  - 问题类型: 事实性、推理型、总结型
  - 样本数: 50 个

**评分标准**:
- 单针准确率 >= 85%
- 多针准确率 >= 70%
- 问答 F1 >= 0.75

#### 🔴 高档 (128k - 256k tokens)

**适用场景**: 长上下文极限能力测试

**测试类型**:
- 单针提取
  - 针深度位置: 每 10% 一个位置
  - 测试样本数: 200 个

- 多针提取 (Multi-Needle, 5-10 针)
  - 针数量: 5, 7, 10 个
  - 测试样本数: 各 50 个

- 顺序针提取 (Sequential-NIAH)
  - 按顺序提取 5-10 个关键信息
  - 测试样本数: 50 个

- 长文档深度理解
  - 文本长度: 64000-128000 tokens
  - 任务类型: 跨文档推理、信息整合、长期依赖追踪
  - 样本数: 50 个

**评分标准**:
- 单针准确率 >= 80%
- 多针准确率 >= 60%
- 顺序提取准确率 >= 60%
- 深度理解 F1 >= 0.65

---

## 📁 测试数据结构

```
long-context-benchmark/
├── data/
│   ├── haystack/              # 草垛文本（填充内容）
│   │   ├── books/             # 书籍文本
│   │   ├── articles/          # 文章文本
│   │   ├── code/              # 代码文本
│   │   └── synthetic/         # 合成文本
│   ├── needles/               # 针（关键信息）
│   │   ├── facts.json         # 事实性针
│   │   ├── codes.json         # 代码类针
│   │   └── questions.json     # 问题类针
│   └── prompts/               # 测试提示词
│       ├── single_needle.txt
│       ├── multi_needle.txt
│       └── sequential.txt
├── tests/
│   ├── tier1_basic/           # 入门档测试
│   ├── tier2_medium/          # 中档测试
│   └── tier3_advanced/        # 高档测试
├── results/                   # 测试结果
└── scripts/                   # 测试脚本
```

---

## 🔧 测试工具

### 推荐框架

1. **OpenCompass** - [文档](https://opencompass.readthedocs.io/zh-cn/latest/advanced_guides/needleinahaystack_eval.html)
   - 支持 Needle-in-a-Haystack 评估
   - 自动化测试流程

2. **EvalScope** - [文档](https://evalscope.readthedocs.io/zh-cn/latest/benchmarks/needle_haystack.html)
   - 专门的长上下文信息检索测试
   - 支持多档位测试

3. **RULER** - 长上下文评估基准
   - 涵盖多种测试类型
   - 支持最大 1M token 测试

---

## 📈 评估指标

### 主要指标

| 指标 | 说明 | 计算方式 |
|------|------|---------|
| 准确率 (Accuracy) | 回答正确的比例 | 正确数 / 总数 |
| F1 分数 | 精确率和召回率的调和平均 | 2×P×R/(P+R) |
| 位置敏感准确率 | 不同深度位置的准确率 | 分位置统计 |
| 顺序准确率 | 顺序提取的正确率 | 顺序正确数 / 总数 |

### 附加指标

- **迷失率 (Lost-in-the-Middle)**: 中间位置准确率下降程度
- **鲁棒性**: 不同类型针的表现稳定性
- **效率**: 推理时间与上下文长度的关系

---

## 🚀 快速开始

```bash
# 1. 克隆测试框架
git clone https://github.com/open-compass/opencompass.git

# 2. 安装依赖
pip install opencompass

# 3. 运行入门档测试
python run_needle_test.py --tier basic --length 16k

# 4. 运行完整测试
python run_full_test.py --max-length 256k
```

---

## 📚 参考资料

### 学术资源

- [LV-Eval: A Balanced Long-Context Benchmark](https://openreview.net/forum?id=FJIetdSItj) - 五档长度测试（16k-256k）
- [LongBench v2](https://longbench2.github.io/) - 真实世界长上下文任务
- [Sequential-NIAH](https://arxiv.org/abs/2505.10610v1) - 顺序针提取基准

### 工具资源

- [OpenCompass 大海捞针评估](https://opencompass.readthedocs.io/zh-cn/latest/advanced_guides/needleinahaystack_eval.html)
- [EvalScope 长上下文测试](https://evalscope.readthedocs.io/zh-cn/latest/benchmarks/needle_haystack.html)
- [NoLiMa GitHub](https://github.com/adobe-research/NoLiMa) - Adobe 长上下文评估

---

## 📝 更新日志

- **2025-03-30**: 创建测试集框架，定义三档测试方案
