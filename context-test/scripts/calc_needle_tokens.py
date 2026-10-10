"""计算第一个针的 token 数量和补偿后的上下文长度"""
import json
import tiktoken

# 加载针数据
needles_file = r"C:\Users\Administrator\Desktop\新建文件夹\一体机模型测试\上下文测试\data\needles\example_facts.json"
with open(needles_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
    needles = data["needles"]

# 初始化 tokenizer（与测试脚本保持一致）
tokenizer = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(tokenizer.encode(text))

# 获取第一个针
first_needle = needles[0]
needle_content = first_needle["content"]

# 构建完整的针文本（与测试脚本保持一致）
needle_text = f"\n>>> 关键信息: {needle_content} <<<\n"
needle_tokens = count_tokens(needle_text)

print("=" * 60)
print(f"第一个针 (fact_001) Token 分析")
print("=" * 60)
print(f"针原始内容长度: {len(needle_content)} 字符")
print(f"针原始内容 Token: {count_tokens(needle_content)}")
print(f"包装后针 Token: {needle_tokens}")
print()

# 计算各个测试长度下的补偿情况
test_lengths = [8000, 16000, 32000, 64000, 128000, 256000, 1000000]

print("=" * 60)
print("各测试长度下的补偿效果")
print("=" * 60)
print(f"{'测试长度':<10} {'针占比':<10} {'调整后长度':<12} {'草垛空间':<10} {'实际总长度':<10}")
print("-" * 60)

for context_length in test_lengths:
    # 计算补偿（与测试脚本逻辑一致）
    needle_ratio = needle_tokens / context_length

    if needle_ratio > 0.05:
        compensation_factor = 1 / (1 - needle_ratio * 0.5)
        adjusted_length = int(context_length * compensation_factor)
    else:
        adjusted_length = context_length

    # 计算草垛空间（调整后长度减去针本身）
    haystack_space = adjusted_length - needle_tokens

    # 实际发送的总长度（调整后的长度）
    actual_total = adjusted_length

    label = f"{context_length//1000}k" if context_length < 1000000 else "1M"
    print(f"{label:<10} {needle_ratio:>6.1%}    {adjusted_length:<12} {haystack_space:<10} {actual_total:<10}")

print("=" * 60)
print()
print("说明:")
print("- 针占比: 针占目标测试长度的比例")
print("- 调整后长度: 补偿后的目标长度")
print("- 草垛空间: 调整后长度减去针本身，留给填充内容的空间")
print("- 实际总长度: 发送给 API 的最终上下文长度")
