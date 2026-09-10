import streamlit as st
import requests
import time
import random
import sqlite3
from io import BytesIO
from datetime import datetime

# ========== 页面全局配置 ==========
st.set_page_config(
    page_title="YouKu AI食谱生成器",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

healing_quotes = [
    "人间烟火气，最抚凡人心🍲",
    "简单食材，也能烹制出治愈美味",
    "好好做饭，是热爱生活的证明",
    "一餐一饭，皆是生活温柔💛",
    "厨房里藏着最踏实的幸福感",
    "用心烹饪，平凡日子也闪光",
    "美食治愈疲惫，暖胃也暖心",
    "享受下厨，享受属于你的时光✨"
]

custom_css = """
<style>
.main {
    background: linear-gradient(180deg, #f7f9ff 0%, #eef2ff 100%);
}
.stApp {
    color:#2c333a;
}
.block-container {
    padding-top: 2rem;
    max-width:960px;
}
.warning-notice{color:#d03b3b; font-weight:bold;}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 读取密钥
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
DASHSCOPE_API_KEY = st.secrets["DASHSCOPE_API_KEY"]

# ========== 数据库 ==========
def init_db():
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS recipes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  dish_name TEXT,
                  ingredients TEXT,
                  recipe_content TEXT,
                  image_url TEXT,
                  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  is_favorite INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS diet_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_date TEXT,
        gender TEXT,
        height REAL,
        weight REAL,
        age INTEGER,
        activity_level REAL,
        dish_list TEXT,
        total_intake_cal REAL DEFAULT 0,
        total_sport_cal REAL DEFAULT 0,
        note TEXT,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

def save_recipe_to_db(dish_name, ingredients, recipe_content, image_url):
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute('INSERT INTO recipes (dish_name, ingredients, recipe_content, image_url) VALUES (?,?,?,?)',
              (dish_name, ingredients, recipe_content, image_url))
    conn.commit()
    conn.close()

def toggle_favorite(rid):
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute("UPDATE recipes SET is_favorite = 1 - is_favorite WHERE id = ?", (rid,))
    conn.commit()
    conn.close()

def get_all_recipes():
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute("SELECT * FROM recipes ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_recipe_by_id(rid):
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute("DELETE FROM recipes WHERE id = ?", (rid,))
    conn.commit()
    conn.close()

def clear_all_recipes():
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute("DELETE FROM recipes")
    conn.commit()
    conn.close()

def save_diet_plan(plan_date, gender, height, weight, age, activity_level, dish_list, total_intake_cal, total_sport_cal, note):
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute('''INSERT INTO diet_plan
    (plan_date,gender,height,weight,age,activity_level,dish_list,total_intake_cal,total_sport_cal,note)
    VALUES (?,?,?,?,?,?,?,?,?,?)''',
    (plan_date, gender, height, weight, age, activity_level, dish_list, total_intake_cal, total_sport_cal, note))
    conn.commit()
    conn.close()

def get_diet_plan_by_date(target_date):
    conn = sqlite3.connect("youku_recipe.db")
    c = conn.cursor()
    c.execute("SELECT * FROM diet_plan WHERE plan_date = ? ORDER BY id DESC LIMIT 1", (target_date,))
    row = c.fetchone()
    conn.close()
    return row

# ========== Dialog弹窗 ==========
@st.dialog("⚠️确认删除单条菜谱")
def dialog_delete_one(rid, dish):
    st.write(f"确定删除菜谱：**{dish}**？操作不可撤销！")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("❌取消",use_container_width=True):
            st.rerun()
    with c2:
        if st.button("🗑️确认删除",type="primary",use_container_width=True):
            delete_recipe_by_id(rid)
            st.toast(f"已删除：{dish}")
            st.rerun()

@st.dialog("⚠️确认清空全部历史")
def dialog_clear_all():
    st.markdown("### 危险操作！")
    st.write("将会删除所有保存菜谱，无法恢复！")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("❌取消",use_container_width=True):
            st.rerun()
    with c2:
        if st.button("💥全部清空",type="primary",use_container_width=True):
            clear_all_recipes()
            st.toast("✅全部历史菜谱已清空")
            st.rerun()

# ========== 身体热量计算工具 ==========
def calc_bmr(gender, height_cm, weight_kg, age):
    if gender == "男":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return round(bmr,1)

def calc_tdee(bmr, activity_factor):
    return round(bmr * activity_factor,1)

sport_map = {
    "快走(5km/h)": 3.5,
    "慢跑(8km/h)":8.0,
    "跳绳":10.0,
    "骑行":6.0,
    "游泳":9.0,
    "力量健身训练":6.5,
    "瑜伽":3.0
}
def calc_sport_cal(sport_name, weight_kg, minute):
    met = sport_map[sport_name]
    hour = minute / 60
    cal = met * weight_kg * hour
    return round(cal,1)

# ========== DeepSeek文本接口 ==========
def generate_recipe(ingredients, taste, cuisine, avoid_list, person_num):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type":"application/json"}
    avoid_text = f"**严禁使用以下食材：{','.join(avoid_list)}**，菜谱全程不能出现这些食材。" if avoid_list else ""
    prompt = f"""根据食材生成一份详细中式菜谱，严格按下面格式输出：
【菜名】
食材（{person_num}）：
做法步骤：
小贴士：
🍱营养参考（仅估算，不作为医疗依据）：热量、蛋白质简单描述。

要求：菜系：{cuisine}，口味风格：{taste}
{avoid_text}
可用食材：{ingredients}"""
    payload = {"model":"deepseek-chat","messages":[{"role":"user","content":prompt}]}
    try:
        res = requests.post(url,headers=headers,json=payload,timeout=45)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"菜谱生成异常：{str(e)}")
        return None

def estimate_dish_calorie(dish_name, recipe_text):
    prompt = f"""下面是菜品【{dish_name}】的菜谱，请只输出估算总热量数值（单位大卡kcal），只返回数字，不要多余文字：
{recipe_text}"""
    payload = {"model":"deepseek-chat","messages":[{"role":"user","content":prompt}]}
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type":"application/json"}
    try:
        res = requests.post("https://api.deepseek.com/v1/chat/completions",headers=headers,json=payload,timeout=30)
        res.raise_for_status()
        num_str = res.json()["choices"][0]["message"]["content"].strip()
        num = float(''.join([c for c in num_str if c in '0123456789.']))
        return round(num,0)
    except:
        return None

def reverse_query_dish(dish_name, avoid_list, person_num):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type":"application/json"}
    avoid_text = f"禁止使用食材：{','.join(avoid_list)}" if avoid_list else ""
    prompt = f"""菜名：{dish_name}，{person_num}。{avoid_text}
输出格式：
【所需准备食材】
【完整菜谱步骤】
【营养参考（仅估算，不作医疗依据）】"""
    payload = {"model":"deepseek-chat","messages":[{"role":"user","content":prompt}]}
    try:
        res = requests.post(url,headers=headers,json=payload,timeout=45)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"反向查询异常：{str(e)}")
        return None

def random_generate_recipe(cuisine,taste,avoid_list,person_num):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type":"application/json"}
    avoid_text = f"禁止使用食材：{','.join(avoid_list)}" if avoid_list else ""
    prompt = f"""随机生成一道全新家常菜，菜系{cuisine}，口味{taste}，{person_num}。{avoid_text}
严格输出格式：
【菜名】
食材：
做法步骤：
小贴士：
🍱营养参考（仅估算，不作为医疗依据）"""
    payload = {"model":"deepseek-chat","messages":[{"role":"user","content":prompt}]}
    try:
        res = requests.post(url,headers=headers,json=payload,timeout=45)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"随机生成异常：{str(e)}")
        return None

def extract_dish_name(text):
    if not text:
        return ""
    try:
        s = text.find("【菜名】") + 4
        e = text.find("\n",s)
        return text[s:e].strip()
    except:
        return ""

# ========== 图片生成（修复wanx‑v1） ==========
def gen_dish_image(dish_name, img_style):
    if not DASHSCOPE_API_KEY or not dish_name:
        return None
    style_map = {
        "写实实拍":"实拍美食照片，45度俯拍，暖自然光，家常白瓷盘，高清，真实质感，柔和阴影，画面干净，无文字，无logo",
        "ins美食风":"ins风美食摄影，明亮柔和柔光，浅色系餐盘，简约干净背景，精致摆盘，高清，无文字，无logo",
        "日系清新":"日系治愈美食，自然光，原木桌面，清淡色调，胶片质感，柔和虚化背景，无文字，无logo",
        "复古胶片":"复古胶片美食摄影，暖色调，颗粒质感，暗角，氛围感餐桌，写实菜品，无文字，无logo"
    }
    prompt = f"{style_map[img_style]}，菜品「{dish_name}」"
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type":"application/json",
        "X-DashScope-Async":"enable"
    }
    body = {
        "model":"wanx-v1",
        "input":{"prompt":prompt},
        "parameters":{"size":"1024*1024","n":1}
    }
    try:
        resp = requests.post("https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",headers=headers,json=body,timeout=30)
        resp.raise_for_status()
        task_id = resp.json()["output"]["task_id"]
        for _ in range(60):
            time.sleep(2)
            tr = requests.get(f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",headers=headers,timeout=20)
            tr.raise_for_status()
            data = tr.json()
            if data["output"]["task_status"] == "SUCCEEDED":
                return data["output"]["results"][0]["url"]
            if data["output"]["task_status"] == "FAILED":
                st.warning(f"图片失败:{data.get('output',{}).get('message','')}")
                return None
        st.warning("图片生成超时")
        return None
    except Exception as e:
        st.error(f"图片接口异常：{str(e)}")
        return None

def download_img_from_url(url):
    try:
        r = requests.get(url,timeout=20)
        return BytesIO(r.content)
    except:
        return None

# ========== 侧边栏开关 ==========
with st.sidebar:
    st.header("⚙️设置")
    enable_img = st.checkbox("开启菜品图片生成", value=False, help="Streamlit Cloud海外环境访问阿里云容易失败，关闭只生成文字菜谱")

# ========== 主页面 ==========
st.title("🍽️ YouKu AI食谱生成器")
quote = random.choice(healing_quotes)
st.markdown(f"<p style='text-align:center; color:#5b6b8c; font-size:18px'>{quote}</p>",unsafe_allow_html=True)

tab_main, tab_reverse, tab_history, tab_diet = st.tabs(["✨食材生成菜谱","🔍菜名反查食材","📚历史菜谱","📅每日饮食&热量计划"])

allergen_list = ["香菜", "葱", "姜", "蒜", "花生", "海鲜", "鸡蛋", "牛奶"]

with tab_main:
    c1,c2 = st.columns([1,1])
    with c1:
        cuisine_opt = st.selectbox("🍽️菜系",["家常菜","川菜","粤菜","湘菜","鲁菜","浙菜"])
        person_opt = st.selectbox("👨‍👩‍👧‍👦用餐人数",["1人份","2人份","3人份","4人份","5人份","6人份"])
    with c2:
        taste_opt = st.selectbox("🌶️口味",["清淡","微辣","重辣","酸甜","鲜香","咸香"])
        img_style_opt = st.selectbox("🖼️图片风格",["写实实拍","ins美食风","日系清新","复古胶片"], disabled=not enable_img)

    avoid_selected = st.multiselect("🚫过敏原/不吃食材黑名单",allergen_list)
    food_input = st.text_input("🥬输入食材，逗号隔开","土豆，牛肉，洋葱")

    bt1,bt2 = st.columns(2)
    with bt1:
        btn_gen = st.button("✨生成菜谱+菜品图",type="primary",use_container_width=True)
    with bt2:
        btn_rand = st.button("🎲随机生成一道菜",use_container_width=True)

    recipe_out = None
    dish_out = ""
    img_out = None

    if btn_gen:
        if not food_input.strip():
            st.warning("⚠️请填写食材！")
            st.stop()
        with st.spinner("生成菜谱中..."):
            recipe_out = generate_recipe(food_input,taste_opt,cuisine_opt,avoid_selected,person_opt)
        if not recipe_out: st.stop()
        dish_out = extract_dish_name(recipe_out)

    if btn_rand:
        with st.spinner("随机构思美食..."):
            recipe_out = random_generate_recipe(cuisine_opt,taste_opt,avoid_selected,person_opt)
        if not recipe_out: st.stop()
        dish_out = extract_dish_name(recipe_out)

    if recipe_out:
        col_a,col_b = st.columns([1,1])
        with col_a:
            st.subheader("📖菜谱结果")
            st.markdown(recipe_out)
            st.code(recipe_out,language="markdown")
            buf_txt = BytesIO(recipe_out.encode("utf-8"))
            st.download_button("📄下载菜谱TXT",data=buf_txt,file_name=f"{dish_out}.txt",mime="text/plain")
        with col_b:
            st.subheader("🍽️菜品图片")
            if enable_img and dish_out:
                with st.spinner("绘制菜品图片..."):
                    img_out = gen_dish_image(dish_out,img_style_opt)
                if img_out:
                    st.image(img_out,caption=dish_out,use_container_width=True)
                    img_bytes = download_img_from_url(img_out)
                    if img_bytes:
                        st.download_button("🖼️下载菜品图片",data=img_bytes,file_name=f"{dish_out}.jpg",mime="image/jpeg")
                else:
                    st.warning("图片生成失败")
            else:
                st.info("图片功能已关闭，在侧边栏开启")
        if dish_out:
            save_recipe_to_db(dish_out,food_input,recipe_out,img_out)
            st.success("✅菜谱已保存进历史！")

with tab_reverse:
    st.markdown("### 🔍输入菜名，反查需要准备的食材")
    rev_dish = st.text_input("请输入菜名，例如：红烧肉","红烧肉")
    rev_person = st.selectbox("👨‍👩‍👧‍👦用餐人数(反查)",["1人份","2人份","3人份","4人份","5人份","6人份"])
    rev_avoid = st.multiselect("🚫黑名单(反查)",allergen_list)
    rev_img_style = st.selectbox("🖼️图片风格(反查)",["写实实拍","ins美食风","日系清新","复古胶片"], disabled=not enable_img)
    if st.button("🔎开始查询",type="primary"):
        if not rev_dish.strip():
            st.warning("请输入菜名！")
            st.stop()
        with st.spinner("正在查询该菜品信息..."):
            rev_result = reverse_query_dish(rev_dish,rev_avoid,rev_person)
        if not rev_result: st.stop()
        rev_name = extract_dish_name(rev_result)
        ca,cb = st.columns([1,1])
        with ca:
            st.markdown(rev_result)
            st.code(rev_result,language="markdown")
            buf_rev = BytesIO(rev_result.encode("utf-8"))
            st.download_button("📄下载TXT",data=buf_rev,file_name=f"{rev_name}.txt")
        with cb:
            st.subheader("🍽️菜品图片")
            if enable_img and rev_name:
                with st.spinner("生成图片..."):
                    rev_img = gen_dish_image(rev_name,rev_img_style)
                if rev_img:
                    st.image(rev_img,caption=rev_name,use_container_width=True)
                    rev_img_byte = download_img_from_url(rev_img)
                    if rev_img_byte:
                        st.download_button("🖼️下载图片",data=rev_img_byte,file_name=f"{rev_name}.jpg")
                else:
                    st.warning("图片生成失败")
            else:
                st.info("图片功能已关闭，在侧边栏开启")

with tab_history:
    st.subheader("📚历史菜谱库")
    hist_search = st.text_input("🔍搜索菜名","")
    show_fav_only = st.checkbox("⭐只看收藏菜谱")
    if st.button("💥清空全部历史",use_container_width=True):
        dialog_clear_all()
    all_data = get_all_recipes()
    if len(all_data) == 0:
        st.info("暂无保存菜谱！")
    else:
        for row in all_data:
            rid,dish,ing,content,imgurl,ctime,fav = row
            if hist_search and hist_search.lower() not in dish.lower():
                continue
            if show_fav_only and fav != 1:
                continue
            star_text = "⭐" if fav ==1 else "☆"
            with st.expander(f"{star_text} {dish} 【{ctime}】"):
                c_h1,c_h2 = st.columns([1,1])
                with c_h1:
                    st.markdown(f"**原始输入食材：**{ing}")
                    st.markdown(content)
                    st.code(content,language="markdown")
                    buf_h = BytesIO(content.encode("utf-8"))
                    st.download_button("📄下载TXT",data=buf_h,file_name=f"{dish}.txt",key=f"htxt_{rid}")
                    if st.button(f"{star_text}切换收藏状态",key=f"fav_{rid}"):
                        toggle_favorite(rid)
                        st.rerun()
                with c_h2:
                    if imgurl:
                        st.image(imgurl,caption=dish,use_container_width=True)
                        h_img_byte = download_img_from_url(imgurl)
                        if h_img_byte:
                            st.download_button("🖼️下载图片",data=h_img_byte,file_name=f"{dish}.jpg",key=f"himg_{rid}")
                if st.button(f"🗑️删除这条 #{rid}",key=f"hdel_{rid}"):
                    dialog_delete_one(rid,dish)

with tab_diet:
    st.markdown("# 📅每日饮食计划 · 热量体重估算")
    st.markdown("<p class='warning-notice'>⚠️全部热量、体重变化仅AI估算，仅供娱乐参考，不能替代医生、营养师专业建议！</p>",unsafe_allow_html=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    st.info(f"📆今日日期：{today_str}")

    st.subheader("👤填写你的身体指标")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        gender_sel = st.selectbox("性别",["男","女"])
        height_in = st.number_input("身高(cm)",min_value=100.0,max_value=230.0,value=165.0)
    with col_b2:
        weight_in = st.number_input("体重(kg)",min_value=20.0,max_value=300.0,value=60.0)
        age_in = st.number_input("年龄",min_value=10,max_value=100,value=25)

    act_map = {
        "久坐几乎不动":1.2,
        "轻度活动(每周1-3次运动)":1.375,
        "中度活动(每周3-5次)":1.55,
        "高强度(每周6-7次)":1.725,
        "重体力劳动":1.9
    }
    act_sel = st.selectbox("日常身体活动水平",list(act_map.keys()))
    act_factor = act_map[act_sel]

    bmr_val = calc_bmr(gender_sel, height_in, weight_in, age_in)
    tdee_val = calc_tdee(bmr_val, act_factor)
    st.markdown(f"> 🔥你的基础代谢BMR：**{bmr_val} 大卡/天**")
    st.markdown(f"> 🔥你的每日总消耗TDEE：**{tdee_val} 大卡/天**（日常生活+工作消耗）")

    st.divider()
    st.subheader("🍱今日计划吃的菜品（可以从历史菜谱勾选）")
    all_rec = get_all_recipes()
    dish_options = [f"{r[1]}" for r in all_rec]
    selected_dishes = st.multiselect("选择菜谱加入今日饮食计划", dish_options)

    plan_dish_data = []
    total_intake = 0
    if selected_dishes:
        with st.spinner("AI估算选中菜品热量..."):
            for dname in selected_dishes:
                find_rec = next((x for x in all_rec if x[1]==dname),None)
                cal = None
                if find_rec:
                    cal = estimate_dish_calorie(dname, find_rec[3])
                if cal is None:
                    cal = st.number_input(f"【{dname}】AI估算失败，请手动填热量(大卡)",value=350,key=f"cal_{dname}")
                plan_dish_data.append({"dish":dname,"cal":cal})
                total_intake += cal
        st.markdown(f"✅今日菜品总预估摄入热量：**{round(total_intake)} 大卡**")
        for item in plan_dish_data:
            st.markdown(f"- {item['dish']}：{item['cal']} kcal")

    st.divider()
    st.subheader("🏃今日运动记录")
    sport_sel = st.selectbox("选择运动类型", list(sport_map.keys()))
    sport_min = st.number_input("运动时长(分钟)",min_value=0,max_value=300,value=30)
    sport_cal = calc_sport_cal(sport_sel, weight_in, sport_min)
    st.markdown(f"✅本次运动预估消耗：**{sport_cal} 大卡**")

    st.divider()
    st.subheader("📊今日热量分析报告")
    total_body_daily = tdee_val
    total_out = total_body_daily + sport_cal
    net_cal = total_intake - total_out

    st.markdown(f"- 身体日常消耗(TDEE)：{total_body_daily} kcal")
    st.markdown(f"- 运动额外消耗：{sport_cal} kcal")
    st.markdown(f"- 今日吃进去总热量：{total_intake} kcal")
    st.markdown(f"> 📌净热量(摄入-总消耗)：**{round(net_cal)} kcal**")

    FAT_KG_CAL = 7700
    if net_cal > 0:
        week_gain_kg = round((net_cal *7)/FAT_KG_CAL,2)
        st.warning(f"💡热量盈余！如果每天都保持这个差值，一周大约会增加脂肪 {week_gain_kg} kg。建议适当增加运动或减少主食油脂。")
    elif net_cal <0:
        week_loss_kg = round((abs(net_cal)*7)/FAT_KG_CAL,2)
        st.success(f"💡热量缺口！如果每天保持这个差值，一周大约可以减少脂肪 {week_loss_kg} kg。注意缺口不要长期超过700大卡，保护身体健康。")
    else:
        st.info("💡热量收支平衡，维持当前体重。")

    note_text = st.text_area("📝今日饮食备注","")
    if st.button("💾保存今日饮食计划",type="primary"):
        dish_list_str = ";".join([i["dish"]+f"|{i['cal']}" for i in plan_dish_data])
        save_diet_plan(today_str,gender_sel,height_in,weight_in,age_in,act_factor,dish_list_str,total_intake,sport_cal,note_text)
        st.toast("✅今日饮食计划保存成功！")

    st.divider()
    st.subheader("📂读取某天保存过的计划")
    read_date = st.text_input("输入日期读取(格式2026-09-10)",today_str)
    if st.button("🔍读取记录"):
        row = get_diet_plan_by_date(read_date)
        if row:
            rid,pdate,gen,h,w,a,actf,dishlist,tin,tsp,note,ct = row
            st.markdown(f"日期：{pdate}｜性别{gen}｜身高{h}cm｜体重{w}kg｜年龄{a}")
            st.markdown(f"总摄入：{tin} kcal｜运动消耗：{tsp} kcal")
            st.markdown(f"备注：{note}")
            st.markdown(f"菜品列表：{dishlist}")
        else:
            st.info("该日期没有保存计划记录")

# 页脚作者
st.markdown("<br><hr><p style='text-align:center; color:#5b6b8c;'>作者：youku❤youmi</p>",unsafe_allow_html=True)
