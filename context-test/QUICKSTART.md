# 自动化测试脚本 - 快速使用指南

## 🚀 快速开始

### 第一步：配置 API 信息

编辑项目根目录下的 `config.json` 文件：

```json
{
  "api": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your-actual-api-key-here",
    "model": "gpt-4"
  }
}
```

**常见 API 配置示例**：

| 提供商 | base_url | model 示例 |
|--------|----------|------------|
| OpenAI | https://api.openai.com/v1 | gpt-4, gpt-4-turbo |
| Azure OpenAI | https://your-resource.openai.azure.com/openai/deployments/your-deployment | gpt-4 |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| Moonshot | https://api.moonshot.cn/v1 | moonshot-v1-128k |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-max |
| 智谱 AI | https://open.bigmodel.cn/api/paas/v4 | glm-4 |
| 百度千帆 | https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop | ERNIE-Bot-4 |

### 第二步：运行测试

```bash
cd C:\Users\Administrator\long-context-benchmark
python scripts/auto_test.py
```

### 第三步：查看结果

测试完成后，会输出汇总表格：

```
======================================================================
测试结果汇总
======================================================================

上下文      测试数量    成功数量    成功率      平均耗时
----------------------------------------------------------------------
8k         5          5          100.0%     3.2s
16k        5          5          100.0%     4.1s
32k        5          4          80.0%      6.8s
64k        5          4          80.0%      12.3s
128k       5          3          60.0%      24.5s
256k       5          2          40.0%      48.7s
1M         5          0          0.0%       95.2s
----------------------------------------------------------------------
总计       35         23         65.7%
======================================================================
```

详细结果会保存在 `results/` 目录下。

---

## ⚙️ 高级配置

### 调整测试参数

编辑 `config.json` 中的 `test` 部分：

```json
{
  "test": {
    "context_lengths": [8000, 16000, 32000, 64000, 128000, 256000],
    "tests_per_length": 10,
    "needle_depths": [0, 10, 25, 50, 75, 90, 100],
    "timeout": 180,
    "max_tokens": 150,
    "temperature": 0
  }
}
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| context_lengths | 要测试的上下文长度列表 | [8000, ..., 1000000] |
| tests_per_length | 每个长度测试次数 | 5 |
| needle_depths | 针的位置（百分比） | [0, 25, 50, 75, 100] |
| timeout | API 请求超时（秒） | 120 |
| max_tokens | 最大输出 tokens | 100 |
| temperature | 温度参数 | 0 |

---

## 📊 理解测试结果

### 成功率解读

| 成功率 | 评价 | 说明 |
|--------|------|------|
| 90-100% | 优秀 | 模型在该上下文长度下表现优秀 |
| 70-89% | 良好 | 模型表现良好，偶有失误 |
| 50-69% | 一般 | 模型能力接近极限 |
| <50% | 较差 | 模型难以处理该长度 |

### 常见现象

1. **Lost-in-the-Middle**：中间位置（40-60%）准确率下降
2. **长度衰减**：上下文越长，准确率越低
3. **API 限流**：请求过快可能被限流，适当调整 `tests_per_length`

---

## 🔧 故障排除

### 问题 1：API 认证失败

```
API 错误: 401 - Unauthorized
```

**解决**：检查 `api_key` 是否正确

### 问题 2：请求超时

```
请求超时
```

**解决**：增加 `timeout` 参数，或检查网络连接

### 问题 3：上下文长度超限

```
API 错误: 400 - This model's maximum context length is XXX tokens
```

**解决**：调整 `context_lengths`，去掉超过模型限制的长度

### 问题 4：模块缺失

```
ModuleNotFoundError: No module named 'requests'
```

**解决**：
```bash
pip install requests
```

---

## 📝 输出文件

测试结果会保存为 JSON 文件：

```
results/
└── test_results_gpt-4_20250330_143022.json
```

文件内容：
```json
{
  "config": {
    "model": "gpt-4",
    "base_url": "https://api.openai.com/v1",
    "test_time": "2025-03-30T14:30:22"
  },
  "summary": [...],
  "all_results": [...]
}
```

---

## 🎯 测试建议

1. **首次测试**：使用较小的 `tests_per_length`（如 3）快速验证
2. **完整测试**：使用默认配置（每个长度 5 次）获得可靠结果
3. **深度测试**：增加 `tests_per_length` 到 10+，添加更多测试位置
4. **对比测试**：用相同配置测试不同模型，对比性能

---

## 📚 相关文档

- [README.md](README.md) - 项目总览
- [USAGE.md](USAGE.md) - 详细使用说明
