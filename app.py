import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="AI食谱生成器")
st.title("🍳 AI食谱生成器")
st.write("输入你有的食材，AI帮你生成菜谱！")

# 从secrets读取API密钥
try:
    client = OpenAI(
        api_key=st.secrets["API_KEY"],
        base_url="https://api.deepseek.com" # DeepSeek接口地址，必不可少
    )
except Exception as e:
    st.error(f"读取密钥失败：{e}")

food_input = st.text_input("你有哪些食材？（用逗号分隔）")
generate_btn = st.button("生成食谱")

if generate_btn:
    if not food_input.strip():
        st.warning("请输入食材！")
    else:
        prompt = f"""根据给出食材，生成一份完整家常菜菜谱。
食材：{food_input}
输出包含：菜名、食材清单、详细步骤、小贴士。"""
        with st.spinner("正在生成菜谱，请稍等..."):
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.choices[0].message.content
                st.success("✅ 菜谱生成完成")
                st.write(result)
            except Exception as err:
                st.error(f"出错了：{err}")
