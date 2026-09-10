import streamlit as st
import requests
import time
import random
import sqlite3
from io import BytesIO
from datetime import datetime
import time as time_lib

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

# ✅【龙族·路明非雨夜伤感全屏背景CSS】
custom_css = """
<style>
[data-testid="stAppViewContainer"] > .main {
    /* 雨夜都市 路明非孤独氛围感 */
    background-image: url("https://p3-flow-image-sign.byteimg.com/tos-cn-i-a9rns2rl98/34220103093b40389212442411402311~tplv-a9rns2rl98-image.image");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-color: rgba(8, 10, 22, 0.72);
    background-blend-mode: multiply;
    color:#e0e4f8;
}
.stApp {
    color:#e0e4f8;
}
.block-container {
    padding-top: 2rem;
    max-width:1050px;
}
.warning-notice{color:#ff8888; font-weight:bold;}
div[data-testid="stExpander"]{
    background-color: rgba(24, 28, 48, 0.58) !important;
    backdrop-filter: blur(5px);
}
div[data-testid="stVerticalBlock"]{
    gap:0.7rem;
}
.stMarkdown h1,.stMarkdown h2,.stMarkdown h3{
    color:#c7cdf7 !important;
}
[data-testid="stSidebar"] {
    background-color: rgba(16,19,36,0.68);
}
.stButton>button {
    background-color: rgba(60,70,110,0.65);
    color:#e6e9ff;
    border:1px solid #707cb8;
}
.stButton>button:hover {
    background-color: rgba(90,100,160,0.8);
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 读取密钥
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
if "DASHSCOPE_API_KEY" in st.secrets:
    DASHSCOPE_API_KEY = st.secrets["DASHSCOPE_API_KEY"]
else:
    DASHSCOPE_API_KEY = ""

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
    "慢走(4km/h)":3.3,
    "快走(5‑6km/h)":3.8,
    "健走(6.5km/h)":5.0,
    "慢跑(8km/h)":8.0,
    "跑步10km/h":10.0,
    "快跑12km/h":12.5,
    "爬楼梯上楼":8.0,
    "下楼梯":3.5,
    "休闲骑行(平地)":4.5,
    "中等速度骑行":6.8,
    "快速公路骑行":8.5,
    "山地车上坡骑行":14.0,
    "动感单车‑低强度":3.5,
    "动感单车‑中强度":6.8,
    "动感单车‑高强度间歇":11.0,
    "踩水休闲":4.0,
    "慢速仰泳/自由泳":5.8,
    "中速自由泳":8.0,
    "蛙泳普通速度":10.0,
    "快速自由泳":11.0,
    "蝶泳":13.8,
    "慢速跳绳":8.8,
    "中速跳绳":11.8,
    "快速高强度跳绳":12.0,
    "俯卧撑(普通节奏带休息)":3.8,
    "俯卧撑(快速高强度连续)":6.0,
    "仰卧起坐(普通速度)":4.0,
    "仰卧起坐(快速高强度)":6.5,
    "卷腹/腹部收腹训练":4.2,
    "平板支撑(静态维持)":3.5,
    "自重深蹲(普通节奏)":4.0,
    "自重深蹲(快速间歇)":6.2,
    "臀桥臀部训练":3.6,
    "引体向上(自重)":8.0,
    "轻度力量训练(慢节奏，休息久)":3.5,
    "中等力量训练(哑铃/器械常规)":5.0,
    "大重量力量训练(增肌，短休息)":6.0,
    "大强度力量间歇训练":7.5,
    "HIIT高强度间歇训练":9.5,
    "Tabata塔巴塔训练":11.0,
    "战绳训练":8.0,
    "波比跳Burpee训练":8.0,
    "开合跳间歇训练":8.0,
    "哈他瑜伽(舒缓放松)":2.5,
    "流瑜伽(动态)":4.0,
    "空中瑜伽":5.5,
    "普拉提基础":3.0,
    "普拉提进阶":4.2,
    "八段锦":3.2,
    "24式太极拳":3.5,
    "五禽戏":3.3,
    "慢舞休闲":3.0,
    "中速舞蹈":4.5,
    "拉丁舞":5.8,
    "普通广场舞":4.4,
    "高强度健身操风格广场舞":7.2,
    "第九套广播体操":5.1,
    "初级有氧健身操":7.3,
    "高级有氧健身操":9.0,
    "乒乓球休闲":4.0,
    "羽毛球休闲娱乐":4.5,
    "羽毛球比赛对抗":7.0,
    "网球双打":6.0,
    "网球单打":8.0,
    "篮球休闲投篮":4.5,
    "篮球全场比赛":8.0,
    "排球休闲":4.0,
    "排球比赛对抗":8.0,
    "足球休闲玩耍":7.0,
    "足球正式比赛":10.0,
    "平路徒步":4.0,
    "中等坡度爬山":6.0,
    "陡坡登山背包负重":8.0,
    "椭圆机‑中等强度":5.5,
    "椭圆机‑高强度":7.2,
    "划船机‑中等":5.8,
    "划船机‑高强度":8.0,
    "拳击沙袋练习":8.0,
    "散打搏击训练":9.0,
    "拖地擦地家务":3.3,
    "搬轻重物做家务":4.5
}

countable_sports = {
    "俯卧撑(普通节奏带休息)",
    "俯卧撑(快速高强度连续)",
    "仰卧起坐(普通速度)",
    "仰卧起坐(快速高强度)",
    "卷腹/腹部收腹训练",
    "平板支撑(静态维持)",
    "自重深蹲(普通节奏)",
    "自重深蹲(快速间歇)",
    "臀桥臀部训练",
    "引体向上(自重)"
}

action_sec_per_unit = {
    "俯卧撑(普通节奏带休息)":2.2,
    "俯卧撑(快速高强度连续)":1.2,
    "仰卧起坐(普通速度)":2.0,
    "仰卧起坐(快速高强度)":1.1,
    "卷腹/腹部收腹训练":1.8,
    "平板支撑(静态维持)":60,
    "自重深蹲(普通节奏)":1.8,
    "自重深蹲(快速间歇)":1.0,
    "臀桥臀部训练":2.0,
    "引体向上(自重)":3.5
}

# ✅全套音乐库：伤感、抒情、励志、沉静思考
sport_music_categories = {
    "💔极致伤感纯音乐":[
        {"name":"忧伤回忆钢琴","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-05.mp3"},
        {"name":"孤寂夜晚弦乐","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-06.mp3"},
        {"name":"落寞抒情钢琴曲","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-07.mp3"},
    ],
    "💌伤感抒情氛围":[
        {"name":"温柔遗憾旋律","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-08.mp3"},
        {"name":"怀旧往事氛围感","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-09.mp3"},
    ],
    "🔥励志热血BGM":[
        {"name":"向前拼搏力量感","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-02.mp3"},
        {"name":"冲破困境激昂","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-04.mp3"},
    ],
    "🧘人生哲理·沉静思考":[
        {"name":"安静沉思","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-03.mp3"},
        {"name":"释然平静","url":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-01.mp3"},
    ]
}

# ✅伤感/人生语录（适配路明非孤独情绪）
wisdom_quotes = [
    "有些孤独只能自己消化，就像有些路只能一个人走。",
    "好像拼尽全力，依旧留不住想要留住的人和事。",
    "生活不会一直如意，但你可以一直努力。熬过低谷，一切都会慢慢变好。",
    "不必纠结过往遗憾，过去无法改写，但未来仍然可以塑造。",
    "真正的强大，不是从不跌倒，而是跌倒之后依然愿意站起来继续往前走。",
    "人生很多事尽力就好，接受自己的普通，然后拼尽全力去与众不同。",
    "时间会筛选身边的人和事，有些失去，其实是另一种解脱。",
    "不要拿别人的标准，来否定自己的人生，每个人节奏本就不一样。",
    "痛苦和难过都会有，但不能一直停留在悲伤里面，日子总要向前走。",
    "所有看似毫不费力的背后，都是不为人知的坚持和汗水。",
    "放下不属于你的执念，才能够腾出手拥抱属于你的美好。",
    "允许自己偶尔脆弱，但不要沉溺悲伤；哭过之后，请继续好好生活。",
    "人生没有白走的路，每一步经历，都在塑造现在的你。",
    "比起结果，成长本身，才是人生最重要的礼物。",
    "世界很喧闹，偶尔留给自己一点安静，和自己和解。"
]

if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "timer_seconds" not in st.session_state:
    st.session_state.timer_seconds = 0

def format_time(sec_total):
    h = int(sec_total // 3600)
    m = int((sec_total % 3600)//60)
    s = int(sec_total % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def calc_sport_cal(sport_name, weight_kg, minute):
    met = sport_map[sport_name]
    hour = minute / 60
    cal = met * weight_kg * hour
    return round(cal,1)

# ========== DeepSeek文本接口 ==========
def generate_recipe(ingredients, taste, cuisine, avoid_list, person_num):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content‑Type":"application/json"}
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
    payload = {"model":"deepseek‑chat","messages":[{"role":"user","content":prompt}]}
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
    payload = {"model":"deepseek‑chat","messages":[{"role":"user","content":prompt}]}
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content‑Type":"application/json"}
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
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content‑Type":"application/json"}
    avoid_text = f"禁止使用食材：{','.join(avoid_list)}" if avoid_list else ""
    prompt = f"""菜名：{dish_name}，{person_num}。{avoid_text}
输出格式：
【所需准备食材】
【完整菜谱步骤】
【营养参考（仅估算，不作医疗依据）】"""
    payload = {"model":"deepseek‑chat","messages":[{"role":"user","content":prompt}]}
    try:
        res = requests.post(url,headers=headers,json=payload,timeout=45)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"反向查询异常：{str(e)}")
        return None

def random_generate_recipe(cuisine,taste,avoid_list,person_num):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content‑Type":"application/json"}
    avoid_text = f"禁止使用食材：{','.join(avoid_list)}" if avoid_list else ""
    prompt = f"""随机生成一道全新家常菜，菜系{cuisine}，口味{taste}，{person_num}。{avoid_text}
严格输出格式：
【菜名】
食材：
做法步骤：
小贴士：
🍱营养参考（仅估算，不作为医疗依据）"""
    payload = {"model":"deepseek‑chat","messages":[{"role":"user","content":prompt}]}
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

# ========== 图片生成（海外平台默认关闭） ==========
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
        "Content‑Type":"application/json",
        "X‑DashScope‑Async":"enable"
    }
    body = {
        "model":"wanx‑v1",
        "input":{"prompt":prompt},
        "parameters":{"size":"1024*1024","n":1}
    }
    try:
        resp = requests.post("https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image‑synthesis",headers=headers,json=body,timeout=30)
        resp.raise_for_status()
        task_id = resp.json()["output"]["task_id"]
        for _ in range(20):
            time.sleep(2)
            tr = requests.get(f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",headers=headers,timeout=20)
            tr.raise_for_status()
            data = tr.json()
            if data["output"]["task_status"] == "SUCCEEDED":
                return data["output"]["results"][0]["url"]
            if data["output"]["task_status"] == "FAILED":
                st.warning(f"图片失败:{data.get('output',{}).get('message','')}")
                return None
        st.warning("图片生成超时，海外平台不建议开启")
        return None
    except Exception as e:
        st.error(f"图片接口异常（海外平台网络限制）：{str(e)}")
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
    enable_img = st.checkbox("开启菜品图片生成", value=False, help="Streamlit‑Cloud海外服务器网络受限，开启大概率报错！")

# ========== 主页面 ==========
st.title("🍽️ YouKu AI食谱生成器")
quote = random.choice(healing_quotes)
st.markdown(f"<p style='text‑align:center; color:#b4bce0; font‑size:18px'>{quote}</p>",unsafe_allow_html=True)

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
            buf_txt = BytesIO(recipe_out.encode("utf‑8"))
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
                    st.warning("图片生成失败，海外平台请关闭图片开关")
            else:
                st.info("图片功能已关闭（Streamlit‑Cloud海外不建议开启）")
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
            buf_rev = BytesIO(rev_result.encode("utf‑8"))
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
                st.info("图片功能已关闭")

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
                    buf_h = BytesIO(content.encode("utf‑8"))
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
    st.markdown("<p class='warning‑notice'>⚠️全部热量、体重变化仅AI估算，仅供娱乐参考，不能替代医生、营养师专业建议！</p>",unsafe_allow_html=True)
    today_str = datetime.now().strftime("%Y‑%m‑%d")
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
        "轻度活动(每周1‑3次运动)":1.375,
        "中度活动(每周3‑5次)":1.55,
        "高强度(每周6‑7次)":1.725,
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
                    cal = st.number_input(f"【{dname}】AI估算失败，请手动填热量(大卡)",value=350.0,key=f"cal_{dname}")
                plan_dish_data.append({"dish":dname,"cal":cal})
                total_intake += cal
        st.markdown(f"✅今日菜品总预估摄入热量：**{round(total_intake)} 大卡**")
        for item in plan_dish_data:
            st.markdown(f"‑ {item['dish']}：{item['cal']} kcal")

    st.divider()
    st.subheader("🏃今日运动记录")

    # ========= 🎵音乐板块【完整保留】 =========
    with st.expander("🎵情绪音乐｜伤感｜励志｜人生感悟（点击展开）", expanded=False):
        show_quote = random.choice(wisdom_quotes)
        st.markdown(f"💡【今日人生感悟】\n> *{show_quote}*")
        st.divider()
        cat_sel = st.radio("选择音乐情绪分类", list(sport_music_categories.keys()), horizontal=True)
        music_list = sport_music_categories[cat_sel]
        sel_music_name = st.radio("选择曲目", [m["name"] for m in music_list], horizontal=True)
        sel_url = next(x["url"] for x in music_list if x["name"] == sel_music_name)
        st.audio(sel_url, format="audio/mpeg")
        st.markdown("> 💡提示：浏览器需要允许音频播放，纯音乐规避版权防盗链。")

    # ========= ⏱️运动计时器 =========
    st.markdown("#### ⏱️内置运动秒表计时器")
    col_t1, col_t2, col_t3, col_t4 = st.columns([1,1,1,1])
    with col_t1:
        btn_start = st.button("▶️ 开始计时", use_container_width=True)
    with col_t2:
        btn_pause = st.button("⏸️ 暂停计时", use_container_width=True)
    with col_t3:
        btn_reset = st.button("🔄 重置计时器", use_container_width=True)
    with col_t4:
        btn_apply = st.button("✅把计时结果填入运动时长", use_container_width=True)

    if btn_start:
        st.session_state.timer_running = True
    if btn_pause:
        st.session_state.timer_running = False
    if btn_reset:
        st.session_state.timer_running = False
        st.session_state.timer_seconds = 0

    if st.session_state.timer_running:
        st.session_state.timer_seconds +=1
        time_lib.sleep(1)
        st.rerun()

    st.info(f"计时当前：**{format_time(st.session_state.timer_seconds)}**")
    timer_minutes = round(st.session_state.timer_seconds / 60, 1)

    sport_sel = st.selectbox("选择运动类型", list(sport_map.keys()))
    is_support_count_mode = sport_sel in countable_sports

    if is_support_count_mode:
        calc_mode = st.radio("热量计算模式", ["⏱️按运动时长(分钟)", "🔢按组数计数(适合徒手动作)"], horizontal=True)
    else:
        calc_mode = "⏱️按运动时长(分钟)"
        st.info("该运动不支持组数模式，请使用运动时长计算")

    sport_cal = 0.0
    sport_min = 0.0

    if calc_mode == "⏱️按运动时长(分钟)":
        sport_min = st.number_input("运动时长(分钟)",min_value=0.0,max_value=300.0,value=timer_minutes, step=0.1)
        sport_cal = calc_sport_cal(sport_sel, weight_in, sport_min)
        if btn_apply:
            sport_min = timer_minutes
            st.toast(f"已填入计时时长 {timer_minutes} 分钟")
    else:
        col_g1,col_g2 = st.columns(2)
        with col_g1:
            per_group = st.number_input("每组数量(个/秒)", min_value=1, max_value=200, value=20)
        with col_g2:
            group_cnt = st.number_input("完成组数", min_value=1, max_value=50, value=3)
        total_unit = per_group * group_cnt
        sec_per = action_sec_per_unit[sport_sel]
        total_sec = total_unit * sec_per
        sport_min = round(total_sec / 60,1)
        st.markdown(f"✅总数量：{total_unit} ｜等效运动时长：**{sport_min} 分钟**")
        sport_cal = calc_sport_cal(sport_sel, weight_in, sport_min)

    st.markdown(f"✅本次运动预估消耗：**{sport_cal} 大卡**")
    st.info("⚠️运动热量仅为模型估算，受动作标准、间歇休息、个人体能影响，仅供参考。")

    st.divider()
    st.subheader("📊今日热量分析报告")
    total_body_daily = tdee_val
    total_out = total_body_daily + sport_cal
    net_cal = total_intake - total_out

    st.markdown(f"‑ 身体日常消耗(TDEE)：{total_body_daily} kcal")
    st.markdown(f"‑ 运动额外消耗：{sport_cal} kcal")
    st.markdown(f"‑ 今日吃进去总热量：{total_intake} kcal")
    st.markdown(f"> 📌净热量(摄入‑总消耗)：**{round(net_cal)} kcal**")

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
    read_date = st.text_input("输入日期读取(格式2026‑09‑10)",today_str)
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
st.markdown("<br><hr><p style='text‑align:center; color:#b4bce0;'>作者：youku❤youmi</p>",unsafe_allow_html=True)
