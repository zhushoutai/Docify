# app.py 最终版本
# 在Docify.py顶部添加
import sys
import os

# 获取当前文件绝对路径
current_file_path = os.path.abspath(__file__)

# 计算项目根目录路径（假设Docify.py在llm-examples目录）
project_root = os.path.normpath(os.path.join(current_file_path, "../../"))
sys.path.insert(0, project_root)  # 添加项目根目录到Python路径

import streamlit as st
from write import generate_markdown
from typing import Dict
import base64
from pathlib import Path

st.set_page_config(page_title="智能文档生成器", layout="wide")

# 新增图片处理函数
def get_image_base64(img_path):
    """将图片转换为Base64编码"""
    try:
        img = Path(img_path)
        if not img.exists():
            st.error(f"图片文件 {img_path} 未找到")
            return ""
        return base64.b64encode(img.read_bytes()).decode()
    except Exception as e:
        st.error(f"图片加载失败: {str(e)}")
        return ""

# 优化后的首页HTML
HOME_HTML = """
<div style="text-align: center; background: white; padding: 6em 1em;">
  <div style="
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 2rem;
    max-width: 800px;
    margin: 0 auto 2em;
  ">
    <img src="data:image/jpeg;base64,{image_base64}" 
         style="
           width: 120px;
           height: 120px;
           border-radius: 8px;
           object-fit: cover;
           box-shadow: 0 4px 12px rgba(0,0,0,0.1);
         ">
    <div style="text-align: left;">
      <h1 style="
        font-family: 'Helvetica Neue', sans-serif;
        color: #FF6F00;
        font-size: 4rem;
        margin: 0;
        font-weight: 700;
        letter-spacing: 1.5px;
      ">
        Docify
      </h1>
      <h3 style="color: #616161; margin-top: 0.5rem;">智能文档生成系统</h3>
    </div>
  </div>
  <p style="color: #757575; font-size: 1.1rem;">输入需求，即刻生成结构化文档</p>
</div>
""".format(image_base64=get_image_base64("logo.jpg"))

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