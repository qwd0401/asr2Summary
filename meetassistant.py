import requests
import os

# 读取转录文件内容
def read_transcription_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}")
        return None
    except Exception as e:
        print(f"读取文件时出错：{e}")
        return None

# 生成会议总结
def generate_meeting_summary(transcription_text):
    url = "https://api.linkapi.org/v1/chat/completions"
    
    # 使用COSTAR框架优化的提示词（针对互联网产品经理）
    system_prompt = """
# CONTEXT (背景)
你是一位资深的互联网产品专家，专门负责产品会议记录和总结，深度理解产品开发流程、用户需求分析、技术实现和业务目标。

# OBJECTIVE (目标)
基于提供的产品会议转录内容，生成一份面向产品团队的结构化会议总结，重点关注产品决策、功能规划、用户体验和项目推进。

# STYLE (风格)
采用互联网产品团队常用的简洁明了风格，重点突出可执行性，使用产品术语和敏捷开发语言。

# TONE (语调)
保持务实、高效、目标导向的语调，关注用户价值和业务影响，体现产品思维。

# AUDIENCE (受众)
面向产品经理、开发工程师、设计师、测试工程师、运营同学等产品团队成员。

# RESPONSE (响应格式)
请严格按照以下Markdown格式输出：

## 📱 会议概览
- **会议类型**：[产品评审/需求讨论/迭代规划/用户反馈/技术方案等]
- **产品模块**：[涉及的产品功能模块]
- **参与角色**：[PM/开发/设计/测试/运营等]
- **会议时长**：[如果能推断出来]

## 🎯 产品议题
[按优先级排序，列出主要产品议题，如功能需求、用户体验、技术方案等]

## ✅ 产品决策
[明确列出产品相关决策，包括功能取舍、优先级调整、技术选型等]

## 📋 任务清单
[格式：- **任务描述** | 负责人：@XXX | 预期完成：XXX | 优先级：P0/P1/P2]

## 💭 讨论要点
[记录重要的产品讨论，如用户需求分析、技术可行性、竞品对比等]

## 🚨 风险识别
[产品风险、技术风险、时间风险、用户体验风险等]

## 📅 下步计划
[下个迭代安排、评审时间、上线计划、数据验证等]

## 📊 数据&指标
[如涉及数据分析、用户反馈、业务指标等]

请确保内容准确、完整，如某些信息在转录中不明确，请标注"[待确认]"。对于产品相关的专业术语和缩写，请保持原样。
    """
    
    payload = {
        "model": "gemini-2.5-pro-preview-06-05",
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"以下是需要总结的会议转录内容：\n\n{transcription_text}\n\n请按照上述格式要求生成会议总结。"
            }
        ]
    }
    
    headers = {
        "Authorization": "Bearer sk-ceh8SGEq8hYxwKWTE7Fe9e6bB25d4909Bf852396239d7b7d",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求失败：{e}")
        return None

# 生成唯一的文件名（避免覆盖）
def generate_unique_filename(base_name="meeting_summary", extension=".md"):
    import datetime
    import os
    
    # 使用时间戳生成唯一文件名
    timestamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}{extension}"
    
    # 如果文件仍然存在，添加序号
    counter = 1
    while os.path.exists(filename):
        filename = f"{base_name}_{timestamp}_{counter:02d}{extension}"
        counter += 1
    
    return filename

# 保存会议总结为Markdown格式
def save_summary_as_markdown(summary_content, base_filename="meeting_summary"):
    try:
        # 生成唯一的文件名
        output_file = generate_unique_filename(base_filename)
        
        # 添加Markdown格式的标题和时间戳
        import datetime
        current_time = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        
        markdown_content = f"# 会议总结\n\n**生成时间：** {current_time}\n\n{summary_content}\n"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"会议总结已保存到：{output_file}")
        return output_file
    except Exception as e:
        print(f"保存文件时出错：{e}")
        return None

# 主程序
def main():
    transcription_file = 'transcription_result.txt'
    
    # 读取转录内容
    transcription_text = read_transcription_file(transcription_file)
    if not transcription_text:
        return
    
    print("正在生成会议总结...")
    
    # 生成总结
    response = generate_meeting_summary(transcription_text)
    if response and 'choices' in response:
        summary_content = response['choices'][0]['message']['content']
        
        # 保存总结为Markdown格式（自动生成唯一文件名）
        saved_file = save_summary_as_markdown(summary_content)
        if saved_file:
            print(f"✅ 会议总结生成完成！文件已保存为：{saved_file}")
    else:
        print("生成会议总结失败")

if __name__ == "__main__":
    main()