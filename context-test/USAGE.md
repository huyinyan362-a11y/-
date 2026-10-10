# LLM 长上下文能力测试集 - 快速上手指南

## 📖 目录

1. [快速开始](#快速开始)
2. [测试档位说明](#测试档位说明)
3. [测试类型详解](#测试类型详解)
4. [使用示例](#使用示例)
5. [结果分析](#结果分析)

---

## 🚀 快速开始

### 环境准备

```bash
# 1. 创建项目目录
cd C:\Users\Administrator\long-context-benchmark

# 2. 安装依赖（需要 Python 3.8+）
pip install openai tiktoken

# 3. 验证安装
python scripts/run_benchmark.py --help
```

### 目录结构

```
long-context-benchmark/
├── README.md              # 项目说明
├── USAGE.md              # 本文档
├── data/
│   ├── needles/          # 针（关键信息）数据
│   │   └── example_facts.json
│   ├── prompts/          # 提示词模板
│   │   └── templates.json
│   └── haystack/         # 草垛（填充内容）
├── scripts/
│   └── run_benchmark.py  # 测试脚本
└── results/              # 测试结果输出
```

---

## 📊 测试档位说明

### 🟢 入门档 (Basic Tier)

**适用场景**: 快速验证模型的基础长文本能力

**参数配置**:
| 参数 | 值 |
|------|-----|
| 上下文长度 | 4k, 8k, 16k tokens |
| 测试类型 | 单针提取 |
| 针数量 | 1 个 |
| 针位置 | 0%, 25%, 50%, 75%, 100% |

**运行方式**:
```bash
python scripts/run_benchmark.py --tier basic
```

**预期结果**:
- 优秀模型: 准确率 >= 90%
- 合格模型: 准确率 >= 70%

### 🟡 中档 (Medium Tier)

**适用场景**: 评估模型在中等长度上下文中的表现

**参数配置**:
| 参数 | 值 |
|------|-----|
| 上下文长度 | 32k, 64k tokens |
| 测试类型 | 单针、多针 |
| 针数量 | 1, 3, 5 个 |
| 针位置 | 10%, 30%, 50%, 70%, 90% |

**运行方式**:
```bash
python scripts/run_benchmark.py --tier medium
```

**预期结果**:
- 优秀模型: 单针 >= 85%, 多针 >= 70%
- 合格模型: 单针 >= 70%, 多针 >= 50%

### 🔴 高档 (Advanced Tier)

**适用场景**: 压力测试模型的长上下文极限能力

**参数配置**:
| 参数 | 值 |
|------|-----|
| 上下文长度 | 128k, 256k tokens |
| 测试类型 | 单针、多针、顺序提取 |
| 针数量 | 1, 5, 10 个 |
| 针位置 | 每 10% 一个位置 |

**运行方式**:
```bash
python scripts/run_benchmark.py --tier advanced
```

**预期结果**:
- 优秀模型: 单针 >= 80%, 多针 >= 60%
- 合格模型: 单针 >= 60%, 多针 >= 40%

---

## 🔍 测试类型详解

### 1. 单针提取 (Single Needle)

**原理**: 在长文本中插入一条关键信息，测试模型能否找到它。

**示例**:
```
上下文长度: 16k tokens
针内容: "魔法数字是 9527"
针位置: 50% (中间)
问题: "文中提到的魔法数字是什么？"
```

**评估标准**:
- 模型输出包含 "9527" 即为正确
- 忽略大小写和周围文字

### 2. 多针提取 (Multi-Needle)

**原理**: 在长文本中插入多条关键信息，测试模型能否同时找到它们。

**示例**:
```
上下文长度: 32k tokens
针数量: 3 个
针1: "API密钥是 SK-2025-ABCD"
针2: "端口是 8080"
针3: "超时时间是 30秒"
问题: "请分别找出 API密钥、端口和超时时间"
```

**评估标准**:
- 所有针都被找到才为正确
- 部分找到算部分正确

### 3. 顺序提取 (Sequential)

**原理**: 测试模型按出现顺序提取信息的能力。

**示例**:
```
上下文长度: 64k tokens
目标: 按顺序提取 5 个日期
问题: "请按时间顺序列出文中提到的所有里程碑日期"
```

**评估标准**:
- 顺序和内容都要正确
- 错序或遗漏都算错误

### 4. 长文本问答 (QA)

**原理**: 基于长文本进行复杂的问答任务。

**示例**:
```
上下文长度: 128k tokens
文档类型: 技术文档
问题类型: 推理、总结、信息整合
```

**评估标准**:
- 使用 F1 分数评估
- 考虑语义相似度

---

## 💡 使用示例

### 示例 1: 测试特定模型

```python
import openai
from scripts.run_benchmark import LongContextBenchmark, TestConfig

# 初始化
benchmark = LongContextBenchmark()

# 创建配置
config = TestConfig(
    context_length=16000,
    needle_count=1,
    needle_depth=50,
    test_type="single",
    tier="basic"
)

# 生成测试用例
prompt, expected = benchmark.create_test_case(config)

# 调用模型
response = openai.ChatCompletion.create(
    model="your-model-name",
    messages=[{"role": "user", "content": prompt}]
)

# 评估结果
actual_answer = response.choices[0].message.content
is_correct = benchmark.evaluate_answer(expected, actual_answer)

print(f"期望答案: {expected}")
print(f"实际答案: {actual_answer}")
print(f"是否正确: {is_correct}")
```

### 示例 2: 批量测试

```python
# 测试不同长度下的表现
lengths = [4000, 8000, 16000, 32000, 64000]
results = {}

for length in lengths:
    config = TestConfig(
        context_length=length,
        needle_count=1,
        needle_depth=50,
        test_type="single",
        tier="medium"
    )

    # 运行测试...
    results[length] = accuracy

# 绘制性能曲线
import matplotlib.pyplot as plt
plt.plot(lengths, [results[l] for l in lengths])
plt.xlabel('Context Length (tokens)')
plt.ylabel('Accuracy (%)')
plt.title('Long Context Performance')
plt.show()
```

### 示例 3: 位置敏感测试

```python
# 测试不同深度位置的准确率
depths = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
position_results = {}

for depth in depths:
    config = TestConfig(
        context_length=32000,
        needle_count=1,
        needle_depth=depth,
        test_type="single",
        tier="medium"
    )

    # 运行测试...
    position_results[depth] = accuracy

# 分析 "Lost in the Middle" 现象
# 中间位置的准确率如果明显下降，说明存在此现象
```

---

## 📈 结果分析

### 准确率分析

```
总体准确率: 85.2%
├── 入门档 (4k-16k):   92.5% ████
├── 中档 (32k-64k):    84.3% ███
└── 高档 (128k-256k):  78.8% ██
```

### 位置敏感分析

```
位置准确率分布:
0%   |████████| 95%
10%  |███████ | 88%
20%  |██████  | 82%
30%  |██████  | 80%
40%  |█████   | 75%
50%  |█████   | 73%  ← 中间位置可能下降
60%  |█████   | 74%
70%  |██████  | 79%
80%  |██████  | 83%
90%  |███████ | 87%
100% |████████| 94%
```

### Lost-in-the-Middle 检测

如果中间位置 (40%-60%) 的准确率明显低于两端，说明模型存在 "Lost in the Middle" 现象。

**解决建议**:
- 使用重排序 (Re-ranking) 技术
- 调整提示词，强调中间内容的重要性
- 考虑使用分块处理策略

### 多针性能分析

```
单针准确率: 90.2%
3针准确率:  78.5%  ↓ 11.7%
5针准确率:  65.3%  ↓ 25.0%
10针准确率: 48.7%  ↓ 41.5%
```

**趋势**: 随着针数量增加，准确率下降

**建议**:
- 对于多信息提取任务，考虑多次查询
- 使用专门的提取提示词
- 评估时考虑使用 F1 分数

---

## 🔧 高级配置

### 自定义针数据

创建 `custom_needles.json`:

```json
{
  "needles": [
    {
      "id": "custom_001",
      "type": "fact",
      "category": "domain_specific",
      "content": "你的自定义关键信息",
      "question": "你的自定义问题",
      "expected_answer": "期望的答案",
      "difficulty": "medium"
    }
  ]
}
```

### 自定义模板

在测试时可以自定义提示词模板以提高性能：

```python
custom_template = {
    "system_prompt": "你是一个专业助手，请仔细阅读文档...",
    "user_prompt_template": "文档内容：\n{context}\n\n请回答：{question}"
}
```

---

## 📚 参考资源

- [OpenCompass 文档](https://opencompass.readthedocs.io/)
- [Needle-in-a-Haystack 论文](https://arxiv.org/abs/2307.11264)
- [LV-Eval 基准测试](https://openreview.net/forum?id=FJIetdSItj)

---

## 🤝 贡献

欢迎提交新的测试用例、模板和改进建议！

---

**最后更新**: 2025-03-30
