import streamlit as st
from openai import OpenAI

# 页面全局配置
st.set_page_config(
    page_title="AI智能食谱生成器",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS美化界面
custom_css = """
<style>
    .main {
        background: linear-gradient(135deg, #f8f9fa 0%, #fff7f0 100%);
    }
    .block-container {
        padding-top: 2rem;
        max-width:900px;
    }
    h1 {
        color:#222222;
        text-align:center;
        font-weight:700;
    }
    .subtitle{
        text-align:center;
        color:#555;
        font-size:18px;
        margin-bottom:30px;
    }
    .stTextInput>div>div>input{
        border-radius:12px;
        border:1px solid #ddd;
        padding:12px;
        font-size:16px;
    }
    .stButton>button{
        border-radius:10px;
        background-color:#ff7b29;
        color:white;
        border:none;
        padding: 10px 24px;
        font-size:16px;
        font-weight:600;
    }
    .stButton>button:hover{
        background-color:#e86c1e;
    }
    .recipe-card{
        background:#ffffff;
        padding:24px;
        border-radius:16px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        margin-top:20px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 标题区域
st.markdown("<h1>🍳 AI 智能食谱生成器</h1>",unsafe_allow_html=True)
st.markdown('<p class="subtitle">输入手边食材，一键生成专业家常菜谱</p>',unsafe_allow_html=True)

# 初始化DeepSeek客户端
try:
    client = OpenAI(
        api_key=st.secrets["API_KEY"],
        base_url="https://api.deepseek.com"
    )
except Exception as e:
    st.error(f"API密钥读取失败：{e}")

# 输入框
food_input = st.text_input("🥬 请输入食材，多个食材使用英文逗号分隔", placeholder="例如：鸡蛋,番茄,青椒")
generate_btn = st.button("✨ 生成菜谱")

if generate_btn:
    if not food_input.strip():
        st.warning("⚠️ 请至少输入一种食材！")
    else:
        prompt = f"""
根据下面食材，生成一份完整美观家常菜菜谱：
食材列表：{food_input}

输出格式要求：
# 菜名
简单菜品简介

## 食材清单（表格形式）
|食材|用量|
|----|----|

## 烹饪步骤
1. xxxx
2. xxxx

## 烹饪小贴士
- 要点1
- 要点2
        """
        with st.spinner("🧑‍🍳 AI正在构思菜谱，请稍等..."):
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"user", "content": prompt}]
                )
                result = response.choices[0].message.content
                st.success("✅ 菜谱生成完成")
                st.markdown(f'<div class="recipe-card">{result}</div>',unsafe_allow_html=True)
            except Exception as err:
                st.error(f"出错了：{err}")
