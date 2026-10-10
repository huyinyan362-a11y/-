#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模态能力综合测试脚本
支持音频识别、图片识别和视频识别能力测试
自动生成Excel测试报告
"""

import os
import sys
import io
import base64
import time
from pathlib import Path
from datetime import datetime
from openai import OpenAI
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ============================================================================
# ⚙️ 配置区域 - 每次测试前请修改以下配置
# ============================================================================

BASE_URL = "http://10.0.20.51:8080/v1"      # API基础URL
API_KEY = "sk-Nbjwj3na9DD9Gs75NOXC-mJ-cDmI62nM"  # API密钥
MODEL_NAME = "qwn3.5-27b-fp8"           # 模型名称

# 测试文件夹路径（脚本所在目录下的"图片"文件夹）
TEST_FOLDER = Path(__file__).parent / "图片"

# 最大输出tokens限制
MAX_TOKENS = 81920

# 请求超时时间（秒）
REQUEST_TIMEOUT = 300

# ============================================================================
# 🎨 Excel样式配置
# ============================================================================

class ExcelStyles:
    """Excel样式配置"""

    @staticmethod
    def get_header_style():
        """表头样式"""
        return Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')

    @staticmethod
    def get_header_fill():
        """表头填充色"""
        return PatternFill(start_color='366092', end_color='366092', fill_type='solid')

    @staticmethod
    def get_alignment():
        """对齐方式"""
        return Alignment(horizontal='center', vertical='center', wrap_text=True)

    @staticmethod
    def get_border():
        """边框样式"""
        thin_border = Side(border_style='thin', color='000000')
        return Border(
            left=thin_border, right=thin_border,
            top=thin_border, bottom=thin_border
        )

# ============================================================================
# 📋 多模态测试器类
# ============================================================================

class MultimodalTester:
    """多模态能力测试器"""

    def __init__(self, base_url, api_key, model_name):
        """初始化测试器"""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.test_results = []

    def get_mime_type(self, file_path):
        """根据文件扩展名获取MIME类型"""
        ext_to_mime = {
            # 图片格式
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.tiff': 'image/tiff',
            '.ico': 'image/x-icon',
            '.ppm': 'image/x-portable-pixmap',
            # 视频格式
            '.mp4': 'video/mp4',
            '.avi': 'video/avi',
            '.mov': 'video/quicktime',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            # 音频格式
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
            '.flac': 'audio/flac',
            '.aac': 'audio/aac',
            '.ogg': 'audio/ogg',
        }
        file_ext = Path(file_path).suffix.lower()
        return ext_to_mime.get(file_ext, 'application/octet-stream')

    def encode_file_to_base64(self, file_path):
        """将文件编码为base64格式"""
        try:
            if not os.path.exists(file_path):
                return None, f"文件不存在: {file_path}"

            with open(file_path, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode('utf-8')

            mime_type = self.get_mime_type(file_path)
            return f"data:{mime_type};base64,{encoded_string}", None

        except Exception as e:
            return None, f"文件编码失败: {str(e)}"

    def get_file_type(self, file_path):
        """获取文件类型（图片/视频/音频）"""
        ext = Path(file_path).suffix.lower()

        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.ico', '.ppm']
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        audio_exts = ['.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg']

        if ext in image_exts:
            return 'image'
        elif ext in video_exts:
            return 'video'
        elif ext in audio_exts:
            return 'audio'
        else:
            return 'unknown'

    def get_test_prompt(self, file_type):
        """根据文件类型获取测试提示词"""
        prompts = {
            'image': '请详细描述这张图片的内容，包括画面中的物体、人物、文字、颜色、布局等所有可见信息。',
            'video': '请详细描述这个视频的内容，包括视频中的场景、人物、动作、情节等所有可见信息。',
            'audio': '请详细描述这个音频文件的内容，包括声音类型、语言、内容等所有可听信息。如果是语音，请转写出具体内容。'
        }
        return prompts.get(file_type, '请描述这个文件的内容。')

    def test_file(self, file_path, index):
        """测试单个文件"""
        filename = os.path.basename(file_path)
        file_ext = Path(file_path).suffix.upper().replace('.', '')
        file_type = self.get_file_type(file_path)

        print(f"\n{'='*70}")
        print(f"[{index}] 正在测试: {filename}")
        print(f"{'='*70}")
        print(f"📁 文件路径: {file_path}")
        print(f"📋 文件类型: {file_type.upper()}")
        print(f"📄 文件格式: {file_ext}")

        # 编码文件
        print(f"🔄 正在编码文件...")
        data_url, error = self.encode_file_to_base64(file_path)
        if error:
            print(f"❌ {error}")
            return {
                '序号': index,
                '文件名': filename,
                '格式': file_ext,
                '文件类型': file_type.upper(),
                '输入tokens': '错误',
                '输出tokens': '错误',
                '总tokens': '错误',
                '耗时(秒)': '错误',
                '是否具备识别能力': '否',
                '模型完整输出': error
            }

        # 获取提示词
        prompt = self.get_test_prompt(file_type)

        # 构建请求消息
        # 根据文件类型构建不同的content结构
        content = [{"type": "text", "text": prompt}]

        if file_type == 'image':
            content.append({"type": "image_url", "image_url": {"url": data_url}})
        elif file_type == 'video':
            content.append({"type": "video_url", "video_url": {"url": data_url}})
        elif file_type == 'audio':
            content.append({"type": "audio_url", "audio_url": {"url": data_url}})

        messages = [
            {
                "role": "user",
                "content": content
            }
        ]

        # 发送请求
        print(f"🚀 正在发送请求到模型...")
        print(f"🤖 模型: {self.model_name}")

        try:
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=MAX_TOKENS,
                timeout=REQUEST_TIMEOUT
            )
            duration = time.time() - start_time

            # 提取响应信息
            output_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            # 判断是否具备识别能力
            has_capability = self.check_recognition_capability(output_text, file_type)

            print(f"\n✅ 请求成功!")
            print(f"⏱️  耗时: {duration:.2f}秒")
            print(f"📊 Token统计:")
            print(f"   输入tokens: {input_tokens}")
            print(f"   输出tokens: {output_tokens}")
            print(f"   总tokens: {total_tokens}")
            print(f"🔍 识别能力: {'✅ 具备' if has_capability == '是' else '❌ 不具备'}")
            print(f"\n📝 模型输出:")
            print(f"{'-'*70}")
            print(output_text)
            print(f"{'-'*70}")

            return {
                '序号': index,
                '文件名': filename,
                '格式': file_ext,
                '文件类型': file_type.upper(),
                '输入tokens': input_tokens,
                '输出tokens': output_tokens,
                '总tokens': total_tokens,
                '耗时(秒)': round(duration, 2),
                '是否具备识别能力': has_capability,
                '模型完整输出': output_text
            }

        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            print(f"\n❌ {error_msg}")

            return {
                '序号': index,
                '文件名': filename,
                '格式': file_ext,
                '文件类型': file_type.upper(),
                '输入tokens': '错误',
                '输出tokens': '错误',
                '总tokens': '错误',
                '耗时(秒)': '错误',
                '是否具备识别能力': '否',
                '模型完整输出': error_msg
            }

    def check_recognition_capability(self, output_text, file_type):
        """检查模型是否具备识别能力"""
        if not output_text or output_text.strip() == '':
            return '否'

        # 检查是否有明显的错误信息
        error_keywords = ['无法识别', '不支持', '错误', 'error', 'invalid', 'not supported',
                         '无法处理', '抱歉', 'sorry']
        output_lower = output_text.lower()
        for keyword in error_keywords:
            if keyword in output_lower:
                # 进一步检查是否真的错误还是只是描述中包含这些词
                if len(output_text) < 100:  # 如果输出很短且包含错误关键词，认为是错误
                    return '否'

        # 检查输出长度
        if len(output_text) < 10:
            return '否'

        return '是'

    def scan_test_files(self, test_folder):
        """扫描测试文件夹中的所有文件"""
        if not test_folder.exists():
            print(f"❌ 测试文件夹不存在: {test_folder}")
            return []

        # 支持的文件扩展名
        supported_exts = {
            # 图片
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.ico', '.ppm',
            # 视频
            '.mp4', '.avi', '.mov', '.mkv', '.webm',
            # 音频
            '.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg'
        }

        # 扫描文件
        test_files = []
        for file_path in test_folder.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                test_files.append(file_path)

        # 按文件类型和名称排序
        def sort_key(f):
            type_order = {'image': 0, 'video': 1, 'audio': 2}
            file_type = self.get_file_type(f)
            return (type_order.get(file_type, 99), f.name.lower())

        test_files.sort(key=sort_key)

        return test_files

    def run_all_tests(self, test_folder):
        """运行所有测试"""
        print(f"\n{'#'*70}")
        print(f"# 多模态能力综合测试")
        print(f"{'#'*70}")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🤖 模型名称: {self.model_name}")
        print(f"🌐 API地址: {self.base_url}")
        print(f"📁 测试文件夹: {test_folder}")

        # 扫描测试文件
        test_files = self.scan_test_files(test_folder)

        if not test_files:
            print(f"\n❌ 未找到任何支持的测试文件！")
            print(f"📋 支持的文件格式:")
            print(f"   图片: JPG, JPEG, PNG, GIF, BMP, WEBP, TIFF, ICO, PPM")
            print(f"   视频: MP4, AVI, MOV, MKV, WEBM")
            print(f"   音频: WAV, MP3, M4A, FLAC, AAC, OGG")
            return

        print(f"\n📊 找到 {len(test_files)} 个测试文件")
        print(f"{'='*70}")

        # 按类型分组显示
        image_files = [f for f in test_files if self.get_file_type(f) == 'image']
        video_files = [f for f in test_files if self.get_file_type(f) == 'video']
        audio_files = [f for f in test_files if self.get_file_type(f) == 'audio']

        print(f"📸 图片文件: {len(image_files)} 个")
        print(f"🎬 视频文件: {len(video_files)} 个")
        print(f"🎵 音频文件: {len(audio_files)} 个")
        print(f"{'='*70}")

        # 运行测试
        for index, file_path in enumerate(test_files, start=1):
            result = self.test_file(file_path, index)
            self.test_results.append(result)
            time.sleep(0.5)  # 避免请求过快

        return self.test_results

# ============================================================================
# 📊 Excel报告生成器
# ============================================================================

class ExcelReportGenerator:
    """Excel测试报告生成器"""

    def __init__(self, output_path):
        """初始化报告生成器"""
        self.output_path = output_path
        self.styles = ExcelStyles()

    def generate_report(self, test_results, model_name):
        """生成Excel测试报告"""
        print(f"\n📊 正在生成Excel报告...")

        # 创建工作簿
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "多模态能力测试报告"

        # 定义列
        columns = [
            '序号', '文件名', '格式', '文件类型',
            '输入tokens', '输出tokens', '总tokens',
            '耗时(秒)', '是否具备识别能力', '模型完整输出'
        ]

        # 设置列宽
        column_widths = {
            'A': 6,   # 序号
            'B': 30,  # 文件名
            'C': 8,   # 格式
            'D': 10,  # 文件类型
            'E': 12,  # 输入tokens
            'F': 12,  # 输出tokens
            'G': 10,  # 总tokens
            'H': 10,  # 耗时
            'I': 16,  # 是否具备识别能力
            'J': 60   # 模型完整输出
        }

        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width

        # 写入表头
        header_row = 1
        for col_idx, column_name in enumerate(columns, start=1):
            cell = ws.cell(row=header_row, column=col_idx)
            cell.value = column_name
            cell.font = self.styles.get_header_style()
            cell.fill = self.styles.get_header_fill()
            cell.alignment = self.styles.get_alignment()
            cell.border = self.styles.get_border()

        # 写入测试结果
        for row_idx, result in enumerate(test_results, start=2):
            for col_idx, column_name in enumerate(columns, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = result.get(column_name, '')
                cell.alignment = Alignment(
                    horizontal='left' if column_name == '模型完整输出' else 'center',
                    vertical='top',
                    wrap_text=True
                )
                cell.border = self.styles.get_border()

                # 根据识别能力设置行背景色
                if column_name == '是否具备识别能力':
                    if result[column_name] == '是':
                        cell.fill = PatternFill(
                            start_color='C6EFCE',
                            end_color='C6EFCE',
                            fill_type='solid'
                        )
                    else:
                        cell.fill = PatternFill(
                            start_color='FFC7CE',
                            end_color='FFC7CE',
                            fill_type='solid'
                        )

        # 添加统计信息
        self._add_summary_sheet(wb, test_results, model_name)

        # 保存文件
        try:
            wb.save(self.output_path)
            print(f"✅ Excel报告已生成: {self.output_path}")
            return True
        except Exception as e:
            print(f"❌ 保存Excel报告失败: {str(e)}")
            return False

    def _add_summary_sheet(self, workbook, test_results, model_name):
        """添加统计汇总表"""
        ws_summary = workbook.create_sheet("测试汇总")
        ws_summary.column_dimensions['A'].width = 25
        ws_summary.column_dimensions['B'].width = 20

        # 标题
        ws_summary['A1'] = "多模态能力测试汇总"
        ws_summary['A1'].font = Font(name='微软雅黑', size=14, bold=True)
        ws_summary.merge_cells('A1:B1')

        # 模型信息
        ws_summary['A3'] = "模型名称:"
        ws_summary['B3'] = model_name
        ws_summary['A4'] = "测试时间:"
        ws_summary['B4'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 统计数据
        total_files = len(test_results)
        success_count = sum(1 for r in test_results if r['是否具备识别能力'] == '是')
        fail_count = total_files - success_count

        image_count = sum(1 for r in test_results if r['文件类型'] == 'IMAGE')
        video_count = sum(1 for r in test_results if r['文件类型'] == 'VIDEO')
        audio_count = sum(1 for r in test_results if r['文件类型'] == 'AUDIO')

        # 计算平均tokens和耗时（只统计成功的）
        success_results = [r for r in test_results if isinstance(r.get('输入tokens'), (int, float))]
        if success_results:
            avg_input = sum(r['输入tokens'] for r in success_results) / len(success_results)
            avg_output = sum(r['输出tokens'] for r in success_results) / len(success_results)
            avg_duration = sum(r['耗时(秒)'] for r in success_results) / len(success_results)
        else:
            avg_input = avg_output = avg_duration = 0

        # 写入统计
        summary_data = [
            ("", ""),
            ("测试统计", ""),
            ("总文件数", total_files),
            ("测试成功", success_count),
            ("测试失败", fail_count),
            ("成功率", f"{success_count/total_files*100:.1f}%" if total_files > 0 else "N/A"),
            ("", ""),
            ("文件类型统计", ""),
            ("图片文件", image_count),
            ("视频文件", video_count),
            ("音频文件", audio_count),
            ("", ""),
            ("平均指标（仅成功）", ""),
            ("平均输入tokens", f"{avg_input:.0f}"),
            ("平均输出tokens", f"{avg_output:.0f}"),
            ("平均耗时(秒)", f"{avg_duration:.2f}"),
        ]

        row = 6
        for label, value in summary_data:
            ws_summary[f'A{row}'] = label
            ws_summary[f'B{row}'] = value
            if label:
                ws_summary[f'A{row}'].font = Font(name='微软雅黑', size=11)
            row += 1

# ============================================================================
# 🚀 主程序入口
# ============================================================================

def main():
    """主函数"""
    print(f"\n{'#'*70}")
    print(f"# 多模态能力综合测试脚本")
    print(f"# 支持音频识别、图片识别和视频识别能力测试")
    print(f"{'#'*70}")

    # 显示当前配置
    print(f"\n⚙️  当前配置:")
    print(f"   BASE_URL: {BASE_URL}")
    print(f"   API_KEY: {API_KEY[:10]}...")
    print(f"   MODEL_NAME: {MODEL_NAME}")
    print(f"   TEST_FOLDER: {TEST_FOLDER}")
    print(f"   MAX_TOKENS: {MAX_TOKENS}")

    # 确认配置
    print(f"\n⚠️  请确认以上配置是否正确，如需修改请编辑脚本中的配置区域")
    print(f"🚀 即将开始测试...")
    time.sleep(1)  # 给用户1秒时间看到配置信息

    # 创建测试器
    tester = MultimodalTester(BASE_URL, API_KEY, MODEL_NAME)

    # 运行所有测试
    results = tester.run_all_tests(TEST_FOLDER)

    if not results:
        print(f"\n❌ 测试未完成，没有生成报告")
        return

    # 生成Excel报告
    report_path = Path(__file__).parent / "多模态能力测试报告.xlsx"
    generator = ExcelReportGenerator(report_path)
    generator.generate_report(results, MODEL_NAME)

    # 显示最终统计
    print(f"\n{'='*70}")
    print(f"🎉 测试完成！")
    print(f"{'='*70}")
    print(f"📊 测试统计:")
    print(f"   总文件数: {len(results)}")
    print(f"   测试成功: {sum(1 for r in results if r['是否具备识别能力'] == '是')}")
    print(f"   测试失败: {sum(1 for r in results if r['是否具备识别能力'] == '否')}")
    print(f"   成功率: {sum(1 for r in results if r['是否具备识别能力'] == '是')/len(results)*100:.1f}%")
    print(f"\n📄 报告文件: {report_path}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
