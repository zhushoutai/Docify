import streamlit as st
import os
import time
import asyncio
from pathlib import Path
from metagpt.roles.researcher import Researcher
from metagpt.schema import Message
from metagpt.logs import logger
import nest_asyncio
nest_asyncio.apply()

# 确保 MetaGPT 路径正确（根据实际路径调整）
import sys
sys.path.append("../../MetaGPT")

# 页面设置保持不变
st.title("📄 自动调研助手 Agent")
st.markdown("请输入你希望调研的主题，系统将自动生成一份完整的调研报告（Markdown 格式）。")

# 输出目录设置保持不变
output_dir = "../../MetaGPT/data/research"
Path(output_dir).mkdir(parents=True, exist_ok=True)

def sanitize_filename(topic):
    filename = topic.strip()
    for char in r'\/:*?"<>|':
        filename = filename.replace(char, "_")
    filename = filename.replace("\n", "_")
    return filename[:100] + ".md"

def get_output_path(topic):
    return os.path.join(output_dir, sanitize_filename(topic))

# 初始化状态保持不变
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好，我是 AI 调研助手，请告诉我你想调研的主题。"}
    ]
if "feedback" not in st.session_state:
    st.session_state.feedback = {}
if "current_topic" not in st.session_state:
    st.session_state.current_topic = None

# 历史消息展示保持不变
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 新增核心功能：直接调用 Researcher 角色
async def generate_research_report(topic: str) -> str:
    """使用 MetaGPT Researcher 生成调研报告"""
    role = Researcher()
    result = await role.run(Message(content=topic))
    return result.content

# 用户输入处理部分改造
if topic_prompt := st.chat_input("你想调研的主题是？（比如：AI 在医疗行业中的应用）"):
    st.session_state.messages.append({"role": "user", "content": topic_prompt})
    with st.chat_message("user"):
        st.markdown(topic_prompt)

    st.session_state.current_topic = topic_prompt

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("🧠 正在调用 agent 进行调研，请稍等...")

        try:
            # 改为直接调用异步函数
            report = asyncio.run(generate_research_report(topic_prompt))
            placeholder.markdown("✅ 调研完成，正在加载报告...")
            
            # 保存报告文件（保持原有文件处理逻辑）
            output_file = get_output_path(topic_prompt)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)

            # 显示报告内容
            st.markdown("📑 **调研报告预览：**")
            st.markdown(report)
            st.download_button(
                label="📥 下载 Markdown 报告",
                data=report,
                file_name=output_file,
                mime="text/markdown"
            )
            st.session_state.messages.append({"role": "assistant", "content": report})

        except Exception as e:
            error_msg = f"❌ 调研过程中发生错误：\n\n{str(e)}"
            placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            logger.error(f"Research error: {str(e)}")

# 反馈处理部分改造（保持原有逻辑，仅修改生成方式）
if st.session_state.current_topic:
    st.markdown("---")
    st.markdown(f"✏️ **你对 「{st.session_state.current_topic}」 的报告是否有任何修改建议？**")
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

        # 构建新 prompt
        feedbacks = st.session_state.feedback.get(topic, [])
        combined_prompt = f"{topic}\n用户反馈:\n" + "\n".join(f"- {fb}" for fb in feedbacks)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("🔄 正在根据反馈生成更新后的报告，请稍等...")

            try:
                # 使用相同方式生成更新报告
                updated_report = asyncio.run(generate_research_report(combined_prompt))
                
                # 保存更新后的报告
                output_file = get_output_path(topic)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(updated_report)

                placeholder.markdown("✅ 报告更新完成，正在加载...")
                st.markdown("📑 **更新后的调研报告预览：**")
                st.markdown(updated_report)
                st.download_button(
                    label="📥 下载最新报告",
                    data=updated_report,
                    file_name=os.path.basename(output_file),
                    mime="text/markdown"
                )
                st.session_state.messages.append({"role": "assistant", "content": updated_report})

            except Exception as e:
                error_msg = f"❌ 更新报告时发生错误：\n\n{str(e)}"
                placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                logger.error(f"Update error: {str(e)}")