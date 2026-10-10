#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态测试
支持文本对话和本地图片绝对路径上传测试
"""

import json
import base64
import os
import sys
from datetime import datetime
import time
from openai import OpenAI

class SimpleQwen25VLTester:
    def __init__(self, base_url="http://10.0.20.51:8080/v1", model_name="qwen3.5-122b-a10b"):
        """初始化测试器"""
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.client = OpenAI(
            base_url=self.base_url,
            api_key="sk-Nbjwj3na9DD9Gs75NOXC-mJ-cDmI62nM"
        )

    def test_video_understanding(self, video_path, question="请描述这个视频的内容"):
        """测试视频理解能力"""
        print("\n" + "="*60)
        print("🎬 视频理解测试")
        print("="*60)
        print(f"📁 视频路径: {video_path}")
        print(f"📝 问题: {question}")

        # 编码视频
        video_base64 = self.encode_image_to_base64(video_path)
        if not video_base64:
            return False

        # 尝试使用video_url类型
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "video_url", "video_url": {"url": video_base64}}
                ]
            }
        ]

        result, duration = self.send_request(messages, max_tokens=1500, timeout=300)

        if result and 'choices' in result:
            response_text = result['choices'][0]['message']['content']
            print(f"\n✅ 模型回复:")
            print(f"📝 {response_text}")

            if 'usage' in result:
                usage = result['usage']
                print(f"\n📊 统计信息:")
                print(f"   Token使用: 输入={usage.get('prompt_tokens', 'N/A')}, 输出={usage.get('completion_tokens', 'N/A')}, 总计={usage.get('total_tokens', 'N/A')}")
                print(f"   响应时间: {duration:.2f}秒")
            return True
        else:
            print("❌ 视频理解测试失败")
            return False
        
    def encode_image_to_base64(self, image_path):
        """将图片或视频编码为base64格式"""
        try:
            if not os.path.exists(image_path):
                print(f"❌ 文件不存在: {image_path}")
                return None

            with open(image_path, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode('utf-8')

            # 获取文件扩展名来确定MIME类型
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp',
                '.mp4': 'video/mp4',
                '.avi': 'video/avi',
                '.mov': 'video/quicktime',
                '.mkv': 'video/x-matroska'
            }.get(ext, 'image/jpeg')

            print(f"✅ 文件编码成功: {os.path.basename(image_path)} ({ext})")
            return f"data:{mime_type};base64,{encoded_string}"

        except Exception as e:
            print(f"❌ 文件编码失败: {e}")
            return None
    
    def send_request(self, messages, max_tokens=1000, temperature=0.7, timeout=240):
        """发送请求到模型API"""
        try:
            print(f"🚀 发送请求到模型...")
            print(f"⏱️ 超时设置: {timeout}秒")

            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            end_time = time.time()

            print(f"📊 请求成功")
            print(f"⏱️ 请求耗时: {end_time-start_time:.2f}秒")

            # 将OpenAI响应转换为原始格式
            result = {
                'choices': [{
                    'message': {
                        'content': response.choices[0].message.content
                    }
                }],
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if response.usage else 'N/A',
                    'completion_tokens': response.usage.completion_tokens if response.usage else 'N/A',
                    'total_tokens': response.usage.total_tokens if response.usage else 'N/A'
                }
            }
            return result, end_time-start_time

        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return None, 0
    
    def test_text_only(self, question="请用中文简短介绍一下人工智能"):
        """测试纯文本理解能力"""
        print("\n" + "="*60)
        print("🔤 纯文本理解测试")
        print("="*60)
        print(f"📝 问题: {question}")
        
        messages = [{"role": "user", "content": question}]
        
        result, duration = self.send_request(messages, max_tokens=500, timeout=180)
        
        if result and 'choices' in result:
            response_text = result['choices'][0]['message']['content']
            print(f"\n✅ 模型回复:")
            print(f"📝 {response_text}")
            
            if 'usage' in result:
                usage = result['usage']
                print(f"\n📊 统计信息:")
                print(f"   Token使用: 输入={usage.get('prompt_tokens', 'N/A')}, 输出={usage.get('completion_tokens', 'N/A')}, 总计={usage.get('total_tokens', 'N/A')}")
                print(f"   响应时间: {duration:.2f}秒")
            return True
        else:
            print("❌ 文本测试失败")
            return False
    
    def test_image_understanding(self, image_path, question="请详细描述这张图片的内容"):
        """测试图像理解能力"""
        print("\n" + "="*60)
        print("🖼️ 图像理解测试")
        print("="*60)
        print(f"📁 图片路径: {image_path}")
        print(f"📝 问题: {question}")
        
        # 编码图片
        image_base64 = self.encode_image_to_base64(image_path)
        if not image_base64:
            return False
        
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": image_base64}}
                ]
            }
        ]
        
        result, duration = self.send_request(messages, max_tokens=1000, timeout=300)
        
        if result and 'choices' in result:
            response_text = result['choices'][0]['message']['content']
            print(f"\n✅ 模型回复:")
            print(f"📝 {response_text}")
            
            if 'usage' in result:
                usage = result['usage']
                print(f"\n📊 统计信息:")
                print(f"   Token使用: 输入={usage.get('prompt_tokens', 'N/A')}, 输出={usage.get('completion_tokens', 'N/A')}, 总计={usage.get('total_tokens', 'N/A')}")
                print(f"   响应时间: {duration:.2f}秒")
            return True
        else:
            print("❌ 图像测试失败")
            return False
    
    def test_multimodal_qa(self, image_path, question):
        """测试多模态问答能力"""
        print("\n" + "="*60)
        print("🧠 多模态问答测试")
        print("="*60)
        print(f"📁 图片路径: {image_path}")
        print(f"❓ 自定义问题: {question}")
        
        # 编码图片
        image_base64 = self.encode_image_to_base64(image_path)
        if not image_base64:
            return False
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": image_base64}}
                ]
            }
        ]
        
        result, duration = self.send_request(messages, max_tokens=1500, timeout=300)
        
        if result and 'choices' in result:
            response_text = result['choices'][0]['message']['content']
            print(f"\n✅ 模型回复:")
            print(f"📝 {response_text}")
            
            if 'usage' in result:
                usage = result['usage']
                print(f"\n📊 统计信息:")
                print(f"   Token使用: 输入={usage.get('prompt_tokens', 'N/A')}, 输出={usage.get('completion_tokens', 'N/A')}, 总计={usage.get('total_tokens', 'N/A')}")
                print(f"   响应时间: {duration:.2f}秒")
            return True
        else:
            print("❌ 多模态问答测试失败")
            return False
    
    def test_api_connection(self):
        """测试API连接"""
        print("🔗 测试API连接...")
        
        test_messages = [{"role": "user", "content": "Hi"}]
        result, _ = self.send_request(test_messages, max_tokens=10, timeout=60)
        
        if result:
            print("✅ API连接成功！")
            return True
        else:
            print("❌ API连接失败！")
            return False

def print_usage():
    """打印使用说明"""
    print("""
🤖  简化版多模态测试脚本

📋 使用方法:
  python simple_qwen2_5vl_tester.py [选项]

📝 选项:
  --text "问题内容"                    # 纯文本测试
  --image "图片绝对路径"               # 图像理解测试  
  --qa "图片路径" "问题内容"           # 多模态问答测试
  --help                              # 显示帮助信息

💡 使用示例:
  # 纯文本测试
  python simple_qwen2_5vl_tester.py --text "什么是深度学习？"
  
  # 图像理解测试
  python simple_qwen2_5vl_tester.py --image "C:\\Users\\Admin\\Pictures\\test.jpg"
  
  # 多模态问答测试
  python simple_qwen2_5vl_tester.py --qa "C:\\Users\\Admin\\Pictures\\chart.png" "这个图表显示了什么趋势？"

📌 注意事项:
  - 图片路径请使用绝对路径
  - 支持格式: jpg, jpeg, png, gif, bmp, webp
  - Windows路径示例: C:\\Users\\Username\\Pictures\\image.jpg
    """)

def main():
    """主函数"""
    print("🚀 启动  简化版多模态测试脚本")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建测试器
    tester = SimpleQwen25VLTester()
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    if not args or '--help' in args:
        print_usage()
        return
    
    # 测试API连接
    if not tester.test_api_connection():
        print("\n❌ API连接失败，无法继续测试")
        return
    
    try:
        if '--text' in args:
            # 纯文本测试
            idx = args.index('--text')
            if idx + 1 < len(args):
                question = args[idx + 1]
                tester.test_text_only(question)
            else:
                print("❌ --text 参数需要提供问题内容")
                
        elif '--image' in args:
            # 图像理解测试
            idx = args.index('--image')
            if idx + 1 < len(args):
                image_path = args[idx + 1]
                tester.test_image_understanding(image_path)
            else:
                print("❌ --image 参数需要提供图片路径")
                
        elif '--qa' in args:
            # 多模态问答测试
            idx = args.index('--qa')
            if idx + 2 < len(args):
                image_path = args[idx + 1]
                question = args[idx + 2]
                tester.test_multimodal_qa(image_path, question)
            else:
                print("❌ --qa 参数需要提供图片路径和问题内容")
                
        else:
            print("❌ 未识别的参数，请使用 --help 查看使用说明")
            
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
    
    print(f"\n🎉 测试完成！时间: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()