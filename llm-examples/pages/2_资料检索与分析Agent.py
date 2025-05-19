import streamlit as st
import subprocess
import os
import time
from pathlib import Path


with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="feedback_api_key", type="password")
    "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/pages/5_Chat_with_user_feedback.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

# 页面设置
# st.set_page_config(page_title="📄 AI 调研助手", layout="wide")
st.title("📄 自动调研助手 Agent")
st.markdown("请输入你希望调研的主题，系统将自动生成一份完整的调研报告（Markdown 格式）。")

# 输出目录
output_dir = "/data/metagpt/MetaGPT/data/research"
Path(output_dir).mkdir(parents=True, exist_ok=True)

def sanitize_filename(topic):
    filename = topic.strip()
    for char in r'\/:*?"<>|':
        filename = filename.replace(char, "_")
    filename = filename.replace("\n", "_")
    return filename[:100] + ".md"

def get_output_path(topic):
    return os.path.join(output_dir, sanitize_filename(topic))

# 初始化 state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好，我是 AI 调研助手，请告诉我你想调研的主题。"}
    ]
if "feedback" not in st.session_state:
    st.session_state.feedback = {}  # {topic: [feedback1, feedback2, ...]}
if "current_topic" not in st.session_state:
    st.session_state.current_topic = None

# 展示历史聊天
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入新调研主题
if topic_prompt := st.chat_input("你想调研的主题是？（比如：AI 在医疗行业中的应用）"):
    st.session_state.messages.append({"role": "user", "content": topic_prompt})
    with st.chat_message("user"):
        st.markdown(topic_prompt)

    st.session_state.current_topic = topic_prompt
    topic = topic_prompt

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("🧠 正在调用 agent 进行调研，请稍等...")

        try:
            result = subprocess.run(
                ["python3", "-m", "metagpt.roles.researcher", f"{topic}"],
                check=True,
                capture_output=True,
                text=True
            )
            placeholder.markdown("✅ 调研完成，正在加载报告...")
        except subprocess.CalledProcessError as e:
            error_msg = f"❌ 调研过程中发生错误：\n\n```\n{e.stderr}\n```"
            placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            st.stop()

        time.sleep(1)
        output_file = get_output_path(topic)
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                report = f.read()

            st.markdown("📑 **调研报告预览：**")
            st.markdown(report)
            st.download_button(
                label="📥 下载 Markdown 报告",
                data=report,
                file_name=os.path.basename(output_file),
                mime="text/markdown"
            )

            st.session_state.messages.append({"role": "assistant", "content": report[:]})
        else:
            error_msg = "❌ 未找到调研报告文件，请检查 agent 是否正确写入。"
            st.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

# 追加反馈意见
# 添加反馈建议
if st.session_state.current_topic:
    st.markdown("---")
    st.markdown(f"✏️ **你对 “{st.session_state.current_topic}” 的报告是否有任何修改建议？**")
    feedback_input = st.text_area("请填写你的修改建议(比如:添加更多关于XXX的数据)", key="feedback_input")
    if st.button("提交修改建议"):
        topic = st.session_state.current_topic
        if topic not in st.session_state.feedback:
            st.session_state.feedback[topic] = []
        st.session_state.feedback[topic].append(feedback_input)

        st.success("修改建议已记录，将立即生成新的报告。")
        st.session_state.messages.append({
            "role": "user",
            "content": f"🔧 用户修改建议：{feedback_input}"
        })

        # === 重新构建 prompt 并调用 agent ===
        feedbacks = st.session_state.feedback.get(topic, [])
        combined_prompt = f"topic:{topic}\nUser's Request:\n" + "\n".join(f"- {fb}" for fb in feedbacks)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("🔄 正在根据反馈生成更新后的报告，请稍等...")
            print(f"combined_prompt:{combined_prompt}")

            try:
                result = subprocess.run(
                    ["python3", "-m", "metagpt.roles.researcher", combined_prompt],
                    check=True,
                    capture_output=True,
                    text=True
                )
                placeholder.markdown("✅ 报告更新完成，正在加载...")
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ 更新报告时发生错误：\n\n```\n{e.stderr}\n```"
                placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                st.stop()

            time.sleep(1)
            output_file = get_output_path(topic)
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    report = f.read()

                st.markdown("📑 **更新后的调研报告预览：**")
                st.markdown(report)
                st.download_button(
                    label="📥 下载最新报告",
                    data=report,
                    file_name=os.path.basename(output_file),
                    mime="text/markdown"
                )
                st.session_state.messages.append({"role": "assistant", "content": report[:]})
            else:
                error_msg = "❌ 未找到更新后的报告文件，请检查 agent 是否正确写入。"
                st.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})



