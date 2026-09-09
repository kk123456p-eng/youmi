import streamlit as st
import requests

# 页面配置
st.set_page_config(page_title="食谱生成器", page_icon="🍳")
st.title("🍳 AI 食谱生成器")
st.write("输入你有的食材，AI 帮你生成菜谱！")

# 从 Streamlit Secrets 读取API密钥
api_key = st.secrets["API_KEY"]
base_url = "https://api.deepseek.com/v1"

# 用户输入框
ingredients = st.text_area("你有哪些食材？（用逗号分隔）", placeholder="例如：鸡蛋, 番茄, 葱")

if st.button("生成食谱"):
    if not ingredients:
        st.warning("请先输入食材")
    else:
        with st.spinner("AI 正在思考..."):
            try:
                response = requests.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "你是一个专业厨师，根据用户提供的食材，给出详细的菜谱，包括菜名、用料、步骤。"},
                            {"role": "user", "content": f"我有这些食材：{ingredients}，请给我一个菜谱"}
                        ],
                        "temperature": 0.7
                    }
                )
                result = response.json()
                recipe = result["choices"][0]["message"]["content"]
                st.success("生成完成！")
                st.markdown(recipe)
            except Exception as e:
                st.error(f"出错了：{str(e)}")
