# app.py 最终版本
import streamlit as st
from write import generate_markdown

st.set_page_config(page_title="智能文档生成器", layout="wide")

# 根据图片样式精确调整的首页
HOME_HTML = """
<div style="text-align: center; background: white; padding: 6em 1em;">
  <h1 style="
    font-family: 'Helvetica Neue', sans-serif;
    color: #FF6F00;
    font-size: 4rem;
    margin: 0.5em 0;
    font-weight: 700;
    letter-spacing: 1.5px;
  ">
    Docify
  </h1>
  <h3 style="color: #616161; margin-top: 0;">智能文档生成系统</h3>
  <p style="color: #757575; font-size: 1.1rem;">输入需求，即刻生成结构化文档</p>
</div>
"""

with st.sidebar:
    st.header("设置")
    language = st.selectbox("输出语言", ["中文", "English"])

if "history" not in st.session_state:
    st.session_state.history = []

def process_markdown(output):
    """优化版标题处理器"""
    lines = output.split('\n')
    title_count = 0
    processed = []
    
    for line in lines:
        stripped = line.strip()
        # 精确匹配一级标题
        if stripped.startswith('# ') and not stripped.startswith('##'):
            title_count += 1
            if title_count == 1:
                processed.append(line)
        else:
            processed.append(line)
    return '\n'.join(processed)

# 显示区域处理
if not st.session_state.history:
    st.markdown(HOME_HTML, unsafe_allow_html=True)
else:
    for item in st.session_state.history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if "output" in item:
                with st.expander("查看源码"):
                    st.code(item["output"], language="markdown")
                st.markdown("---")
                # 添加Markdown渲染容器
                with st.container():
                    st.markdown(item["output"], unsafe_allow_html=True)

if prompt := st.chat_input("请输入文档需求..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("正在生成文档结构..."):
            try:
                raw_output = generate_markdown(prompt)
                processed_output = process_markdown(raw_output)
                
                # 添加渲染保障措施
                if not processed_output.strip().startswith("# "):
                    processed_output = "# 生成文档\n" + processed_output
                
            except Exception as e:
                processed_output = f"生成失败：{str(e)}"

        if processed_output.startswith("生成失败"):
            st.error(processed_output)
        else:
            with st.expander("查看markdown源码"):
                st.code(processed_output, language="markdown")
            st.markdown("---")
            # 使用容器确保渲染空间
            with st.container():
                st.markdown(processed_output, unsafe_allow_html=True)

    st.session_state.history.append({
        "role": "user",
        "content": prompt,
        "output": processed_output
    })