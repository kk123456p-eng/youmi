import streamlit as st
from openai import OpenAI
import random

# 页面基础配置
st.set_page_config(
    page_title="AI智能食谱生成器",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 治愈语录：兼顾年轻人+宝妈
healing_quotes = [
    "好好吃饭，是送给自己最简单的浪漫✨",
    "忙碌生活里，一顿热饭就能治愈所有疲惫",
    "不用追求大餐，简单家常菜也超有幸福感",
    "照顾家人的同时，别忘了多心疼一下自己💛",
    "厨房的烟火气，是平凡日子里的小温柔",
    "不用事事完美，认真吃好每一餐就很棒",
    "哪怕只有简单食材，也能变出美味与快乐",
    "累了就歇一会，美食永远在等你呀🥰"
]

# 软萌可爱清新CSS
custom_css = """
<style>
    .main {
        background: linear-gradient(180deg, #fff9f3 0%, #fff7ef 100%);
    }
    .stApp {
        color:#3a3a3a;
    }
    .block-container {
        padding-top: 2rem;
        max-width:860px;
    }
    .cute-card{
        background:#ffffff;
        border-radius:22px;
        padding:26px;
        box-shadow: 0 4px 14px rgba(240, 190, 150, 0.18);
        border:1px solid #fff1e4;
        margin-bottom:22px;
    }
    h1 {
        text-align:center;
        font-weight:700;
        color:#e67e4f;
    }
    .subtitle{
        text-align:center;
        color:#777777;
        font-size:18px;
        margin-bottom:24px;
    }
    .quote-text{
        text-align:center;
        font-size:17px;
        color:#c96b3e;
    }
    .stTextInput>div>div>input{
        border-radius:16px;
        border:1px solid #f2d9c6;
        background:#fffdfa;
        padding:14px;
        font-size:16px;
    }
    .stButton>button{
        border-radius:14px;
        background-color:#ff9664;
        color:white;
        border:none;
        padding:11px 28px;
        font-size:16px;
        font-weight:600;
    }
    .stButton>button:hover{
        background-color:#f5824f;
        box-shadow: 0 3px 10px rgba(255,150,100,0.25);
    }
    .author-footer{
        text-align:center;
        margin-top:45px;
        color:#99887a;
        font-size:14px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 页面标题
st.markdown("<h1>🍳 AI 智能食谱生成器</h1>",unsafe_allow_html=True)
st.markdown('<p class="subtitle">输入手边食材，一键生成暖心家常菜谱</p>',unsafe_allow_html=True)

# 食愈小语卡片
with st.container():
    st.markdown('<div class="cute-card">',unsafe_allow_html=True)
    st.subheader("💛 今日食愈小语")
    if "current_quote" not in st.session_state:
        st.session_state.current_quote = random.choice(healing_quotes)
    st.markdown(f'<p class="quote-text">“{st.session_state.current_quote}”</p>',unsafe_allow_html=True)
    if st.button("🔄 换一句暖心话"):
        st.session_state.current_quote = random.choice(healing_quotes)
    st.markdown("</div>",unsafe_allow_html=True)

# DeepSeek API
try:
    client = OpenAI(
        api_key=st.secrets["API_KEY"],
        base_url="https://api.deepseek.com"
    )
except Exception as e:
    st.error(f"API密钥读取失败：{e}")

# 食材输入框
food_input = st.text_input("🥬 请输入食材，多个食材使用英文逗号分隔", placeholder="例如：鸡蛋,番茄,青椒,土豆")
generate_btn = st.button("✨ 生成暖心菜谱")

# 生成菜谱逻辑
if generate_btn:
    if not food_input.strip():
        st.warning("⚠️ 请至少输入一种食材哦！")
    else:
        prompt = f"""
根据下面食材，生成一份完整好看的家常菜菜谱：
食材列表：{food_input}

输出格式严格按照下面：
# 菜名
简短菜品介绍

## 食材清单（表格）
|食材|用量|
|----|----|

## 烹饪步骤
1. xxxx
2. xxxx

## 烹饪小提示
- 要点1
- 要点2

最后单独一段，写一句温柔治愈的短句（30字左右，适合年轻人和宝妈，暖心情绪鼓励）
        """
        with st.spinner("🍳 正在为你构思美味菜谱，请稍等..."):
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role":"user", "content": prompt}]
                )
                result = response.choices[0].message.content
                st.success("✅ 菜谱生成完成！")
                st.markdown(f'<div class="cute-card">{result}</div>',unsafe_allow_html=True)
            except Exception as err:
                st.error(f"出错啦：{err}")

# 底部作者署名
st.markdown('<p class="author-footer">作者：youku-youmi</p>',unsafe_allow_html=True)
