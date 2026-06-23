"""
智能食堂菜品推荐系统 - 吃了么
=====================================
将 Web 前端和后端 API 合并为单个 Flask 应用，方便部署到云平台（如 Render）。

功能：
- Web 前端界面（菜品管理、智能推荐）
- 菜品自动获取（从精选数据库）
- 本地数据管理（JSON 存储）

部署到 Render 时：
- 使用环境变量 PORT（Render 自动注入）
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import random
import time

# ========== 基础路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'chimei', 'web_app', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'chimei', 'web_app', 'static'))
CORS(app)

# ========== 配置 ==========
DATA_FILE = os.path.join(BASE_DIR, 'chimei', 'cafeteria_data.json')

# ========== 主食/通用词汇过滤 ==========
STAPLE_FOODS = {
    "米饭", "馒头", "花卷", "面条", "包子", "饺子", "馄饨",
    "白粥", "稀饭", "小米粥", "八宝粥",
    "面包", "蛋糕", "饼干",
    "炒饭", "炒面", "炒粉",
}

def filter_staples(items):
    """过滤掉主食和通用词汇"""
    return [item for item in items if item not in STAPLE_FOODS]

# ========== 营养规则库 ==========
NUTRITION_RULES = {
    "儿童(<12岁)": {
        "prefer": ["牛奶", "鸡蛋", "豆腐", "小鱼干", "菠菜", "胡萝卜", "虾仁", "核桃", "蒸蛋", "粥"],
        "avoid": ["辛辣", "油炸", "浓茶", "咖啡", "酒精", "生冷", "过硬"]
    },
    "女性经期": {
        "prefer": ["红枣", "红糖", "姜", "桂圆", "猪肝", "乌鸡", "热汤", "暖胃", "热粥", "温补"],
        "avoid": ["冰品", "西瓜", "梨", "螃蟹", "绿茶", "苦瓜", "冬瓜", "冷饮", "寒性"]
    },
    "低体重(BMI<18.5)": {
        "prefer": ["坚果", "牛油果", "全脂奶", "橄榄油", "三文鱼", "牛肉", "鸡蛋", "高蛋白", "健康脂肪"],
        "avoid": []
    },
    "超重(BMI>=24)": {
        "prefer": ["清蒸", "凉拌", "杂粮", "蔬菜", "鸡胸肉", "豆腐", "低脂", "高纤维"],
        "avoid": ["红烧肉", "炸鸡", "蛋糕", "含糖饮料", "肥肉", "油炸", "高糖", "重口味"]
    },
    "感冒": {
        "prefer": ["热汤", "粥", "面", "姜", "葱白", "清淡", "易消化"],
        "avoid": ["辛辣", "油腻", "生冷"]
    },
    "肠胃不适": {
        "prefer": ["粥", "面条", "蒸蛋", "山药", "南瓜", "温和", "易消化"],
        "avoid": ["油炸", "生冷", "豆类", "辛辣", "酸性", "高纤维"]
    },
    "运动后": {
        "prefer": ["蛋白质", "香蕉", "牛奶", "鸡胸肉", "鸡蛋", "复合碳水", "水分补充"],
        "avoid": []
    }
}


# ========== 精选菜品数据库 ==========
CURATED_DATABASE = {
    "北京大学": {
        "dishes": [
            "包子", "油条", "豆腐脑", "煎蛋", "豆浆",
            "剁椒鱼头", "茄汁龙利鱼", "小炒鸡胗", "黑椒里脊杏鲍菇",
            "葱油木耳", "鸡汁娃娃菜", "麻婆豆腐", "黄瓜炒肉",
            "香干韭菜", "苦瓜炒蛋", "油炸酥肉", "紫菜蛋汤",
            "牛肉盖浇饭", "卤莲藕", "卤鸭头", "鸭腿",
            "红烧肉", "鱼香肉丝", "宫保鸡丁", "西红柿炒蛋",
            "清炒时蔬", "酸辣土豆丝", "回锅肉", "糖醋排骨",
            "水煮肉片", "干豆角", "地三鲜", "木须肉",
            "青椒肉丝", "蒜蓉西兰花", "番茄牛腩", "酸菜鱼",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "综合多篇北大食堂介绍文章整理",
        "confidence": "medium"
    },
    "清华大学": {
        "dishes": [
            "卷饼", "小笼包", "三鲜锅贴", "红糖烧麦",
            "牛肉味状元饼", "麻球", "叉烧", "五谷豆浆",
            "酱排骨", "红烧肉", "京酱肉丝", "土豆牛肉",
            "孜然羊肉", "素炒西蓝花", "青菜炖豆腐", "香菇肉片",
            "紫荆紫薯包", "紫三糖醋里脊", "桃李二层三杯鸡",
            "桃李二层冬瓜虾皮汤", "南园一层酸笋粉", "紫三炸酱面",
            "清芬二层烤鸭", "紫三酸辣粉", "观畴一层炒米粉",
            "紫二虎皮鸡蛋", "南园一层牛角包",
            "麻辣香锅", "炒菜花",
            "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "回锅肉",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "清华食堂美食攻略 + 水木食集标准化食谱",
        "confidence": "medium"
    },
    "复旦大学": {
        "dishes": [
            "粥", "东坡肉", "炒豆芽", "卷心菜", "西蓝花",
            "炒油豆腐", "木耳青菜", "卤素鸡", "炸鱼排",
            "茭白肉片", "糖醋小排", "烤鸭", "咸菜面",
            "臊子面", "裤带面", "火龙果素肠", "哈密瓜年糕牛肉粒",
            "炸烹佛手肉", "月饼",
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "清炒时蔬", "酸辣土豆丝", "回锅肉", "水煮肉片",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章",
        "confidence": "medium"
    },
    "上海交通大学": {
        "dishes": [
            "红烧肉", "糖醋排骨", "清蒸鲈鱼", "宫保鸡丁",
            "麻婆豆腐", "西红柿炒蛋", "回锅肉", "水煮肉片",
            "干煸豆角", "地三鲜", "木须肉", "青椒肉丝",
            "蒜蓉西兰花", "番茄牛腩", "酸菜鱼", "鱼香肉丝",
            "小笼包", "生煎包", "锅贴", "馄饨",
            "本帮熏鱼", "红烧狮子头", "油爆虾", "腌笃鲜",
            "米饭", "馒头", "花卷", "面条", "炒饭"
        ],
        "source": "上海高校食堂综合整理",
        "confidence": "low"
    },
    "浙江大学": {
        "dishes": [
            "红烧肉", "东坡肉", "糖醋里脊", "西湖醋鱼",
            "龙井虾仁", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "回锅肉", "水煮肉片", "干煸豆角", "地三鲜",
            "木须肉", "青椒肉丝", "蒜蓉西兰花", "番茄牛腩",
            "酸菜鱼", "鱼香肉丝", "叫花鸡", "宋嫂鱼羹",
            "片儿川", "小笼包", "葱包桧", "定胜糕",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "浙江高校食堂综合整理",
        "confidence": "low"
    },
    "中国人民大学": {
        "dishes": [
            "意大利面", "网红猪蹄",
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "回锅肉", "水煮肉片", "干煸豆角", "地三鲜",
            "木须肉", "青椒肉丝", "蒜蓉西兰花", "番茄牛腩",
            "酸菜鱼", "鱼香肉丝", "糖醋排骨", "京酱肉丝",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章",
        "confidence": "medium"
    },
    "天津大学": {
        "dishes": [
            "糖醋大排", "大牌红烧肉", "菠萝咕肉", "砂锅面",
            "水煮鱼片", "糖醋小排", "炒南瓜", "石锅拌饭",
            "豆腐汤", "铁板烧", "刀削面", "肉片金针菇",
            "盐焗虾", "海鲜面", "葱油拌面", "拉面",
            "油泼面", "肥肠面", "蛋包饭", "腊肉饭",
            "韩式烤肉饭", "日式泡菜饭", "烧鹅双拼饭",
            "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章",
        "confidence": "high"
    },
    "南京大学": {
        "dishes": [
            "辣子鸡套餐", "煮玉米",
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "回锅肉", "水煮肉片", "干煸豆角", "地三鲜",
            "木须肉", "青椒肉丝", "蒜蓉西兰花", "番茄牛腩",
            "酸菜鱼", "鱼香肉丝", "糖醋排骨", "盐水鸭",
            "鸭血粉丝汤", "小笼包", "锅贴",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章 + 南京特色补充",
        "confidence": "medium"
    },
    "四川大学": {
        "dishes": [
            "香辣烤鱼", "豆豉鱼", "钵钵鸡", "生蚝扇贝",
            "西瓜西米露", "菠萝西米露", "冰粉", "红糖凉糕",
            "西瓜椰奶", "凉面", "麻辣小龙虾", "香辣佛手螺",
            "麻辣鸭头", "鸭脖子", "香辣鸭肠", "椒麻抄手",
            "麻婆豆腐", "回锅肉", "水煮鱼", "宫保鸡丁",
            "夫妻肺片", "担担面", "钟水饺", "龙抄手",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章",
        "confidence": "high"
    },
    "武汉大学": {
        "dishes": [
            "广式烧鹅", "清蒸生蚝", "清蒸扇贝", "红烧肉",
            "蒸花卷", "红薯糕", "豆沙包", "油炸春卷",
            "炸藕夹", "热干面", "小龙虾拌面",
            "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "回锅肉", "水煮肉片", "干煸豆角", "地三鲜",
            "三鲜豆皮", "武昌鱼", "排骨藕汤", "面窝",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章",
        "confidence": "high"
    },
    "宁德师范学院": {
        "dishes": [
            "炒面", "炒米粉", "瓦罐汤",
            "过桥米线", "排骨米线", "水饺", "牛肉面",
            "凉拌河粉", "鸭腿", "麻辣香锅",
            "杀猪粉", "麻辣烫", "菜配饭",
            "烤鸭饭", "煎蛋", "番茄鸡蛋汤", "鸡蛋凉面",
            "黄焖鸡", "意大利面", "手枪腿意面", "鸡腿面",
            "拌粉", "卤味", "老鸭粉丝汤", "套餐饭", "糖醋排骨饭",
            "烤肉饭", "沙拉烤肉饭", "螺蛳粉", "渔粉", "紫米饭",
            "杂粮煎饼", "无骨炸鸡", "鸡公煲", "排骨粉",
            "饭团", "肉粽", "鸡蛋仔", "冰粉", "双皮奶", "绿豆汤",
            "四果汤", "白桃水仙",
            "米饭", "馒头", "花卷", "面条", "拉面"
        ],
        "source": "多篇宁德师范学院食堂美食攻略文章综合整理",
        "confidence": "medium"
    },
    "福建医科大学": {
        "dishes": [
            "竹筒饭", "连江锅边", "福鼎肉片", "农家烤鱼",
            "重庆鸡公煲", "陕西凉皮", "沙茶面", "莆田打卤面",
            "牛肉面", "瓦罐汤", "刀削面", "小炒",
            "炒泗粉", "炒米粉", "卤面套餐", "鱼丸", "肉燕",
            "捞化", "拌面", "扁肉", "卤味", "豆花",
            "烧仙草", "西米露", "拌粉干", "沙县小吃",
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "回锅肉", "水煮肉片", "清炒时蔬", "酸辣土豆丝",
            "糖醋排骨", "酸菜鱼", "鱼香肉丝", "地三鲜",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "多篇福建医科大学食堂美食文章及点评综合整理",
        "confidence": "medium"
    },
}


# ========== 本地数据管理 ==========
def load_all_data():
    """加载所有学校数据"""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        for school, school_data in data.items():
            if not isinstance(school_data, dict):
                if isinstance(school_data, str):
                    data[school] = {"menu": school_data, "last_modified": time.strftime("%Y-%m-%d %H:%M")}
                else:
                    data[school] = {"menu": "", "last_modified": time.strftime("%Y-%m-%d %H:%M")}
        return data
    except Exception as e:
        print(f"加载数据出错: {e}")
        return {}


def save_all_data(data):
    """保存所有学校数据"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存数据出错: {e}")
        return False


def add_default_school(data):
    """添加默认学校"""
    default_school = "我的学校"
    data[default_school] = {
        "menu": "红烧肉\n鱼香肉丝\n麻婆豆腐\n西红柿炒蛋\n清炒时蔬\n酸辣土豆丝\n宫保鸡丁\n米饭\n馒头",
        "last_modified": time.strftime("%Y-%m-%d %H:%M")
    }
    save_all_data(data)
    return default_school


# ========== Web 前端路由 ==========
@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/universities.json')
def get_universities():
    """提供大学列表JSON文件"""
    uni_file = os.path.join(BASE_DIR, 'chimei', 'universities.json')
    if os.path.exists(uni_file):
        with open(uni_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    else:
        return jsonify({"universities": []}), 404


# ========== 菜品管理 API ==========
@app.route('/api/schools', methods=['GET'])
def get_schools():
    """获取所有学校列表"""
    data = load_all_data()
    if not data:
        school_name = add_default_school({})
        data = load_all_data()
    schools = list(data.keys())
    return jsonify({"success": True, "schools": schools})


@app.route('/api/menu/<school_name>', methods=['GET'])
def get_menu(school_name):
    """获取指定学校的菜单"""
    data = load_all_data()
    if school_name not in data:
        return jsonify({"success": False, "message": "学校不存在"}), 404
    menu_data = data[school_name]
    menu_text = menu_data.get("menu", "") if isinstance(menu_data, dict) else str(menu_data)
    items = [item.strip() for item in menu_text.split("\n") if item.strip()]
    return jsonify({
        "success": True,
        "menu": menu_text,
        "items": items,
        "count": len(items)
    })


@app.route('/api/menu/<school_name>', methods=['POST'])
def save_menu(school_name):
    """保存指定学校的菜单"""
    data = load_all_data()
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    menu = request.json.get('menu', '')
    items = [item.strip() for item in menu.replace(",", "\n").split("\n") if item.strip()]
    formatted_menu = "\n".join(items)
    data[school_name] = {
        "menu": formatted_menu,
        "last_modified": time.strftime("%Y-%m-%d %H:%M")
    }
    if save_all_data(data):
        return jsonify({
            "success": True,
            "message": "保存成功",
            "menu": formatted_menu,
            "count": len(items)
        })
    else:
        return jsonify({"success": False, "message": "保存失败"}), 500


@app.route('/api/school/add', methods=['POST'])
def add_school():
    """添加新学校"""
    data = load_all_data()
    school_name = request.json.get('school_name', '').strip()
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    if school_name in data:
        return jsonify({"success": False, "message": "学校已存在"}), 400
    data[school_name] = {
        "menu": "",
        "last_modified": time.strftime("%Y-%m-%d %H:%M")
    }
    if save_all_data(data):
        return jsonify({"success": True, "message": "学校添加成功"})
    else:
        return jsonify({"success": False, "message": "添加失败"}), 500


@app.route('/api/school/rename', methods=['POST'])
def rename_school():
    """修改学校名称"""
    data = load_all_data()
    old_name = request.json.get('old_name', '').strip()
    new_name = request.json.get('new_name', '').strip()
    if not old_name or not new_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    if old_name not in data:
        return jsonify({"success": False, "message": "原学校不存在"}), 404
    if new_name in data and new_name != old_name:
        return jsonify({"success": False, "message": "新学校名称已存在"}), 400
    data[new_name] = data.pop(old_name)
    if save_all_data(data):
        return jsonify({"success": True, "message": "修改成功"})
    else:
        return jsonify({"success": False, "message": "修改失败"}), 500


# ========== 推荐 API ==========
@app.route('/api/recommend/random/<school_name>', methods=['GET'])
def random_recommend(school_name):
    """随机推荐"""
    data = load_all_data()
    if school_name not in data:
        return jsonify({"success": False, "message": "学校不存在"}), 404
    menu_data = data[school_name]
    menu = menu_data.get("menu", "") if isinstance(menu_data, dict) else str(menu_data)
    if not menu:
        return jsonify({"success": False, "message": "菜单为空"}), 400
    items = [item.strip() for item in menu.split("\n") if item.strip()]
    items = filter_staples(items)
    if not items:
        return jsonify({"success": False, "message": "没有可用菜品（已自动过滤主食）"}), 400
    result = random.choice(items)
    return jsonify({
        "success": True,
        "result": result,
        "school": school_name
    })


@app.route('/api/recommend/smart', methods=['POST'])
def smart_recommend():
    """智能推荐"""
    data = load_all_data()
    school_name = request.json.get('school_name', '')
    age = request.json.get('age', 18)
    gender = request.json.get('gender', '女')
    height = request.json.get('height', 0)
    weight = request.json.get('weight', 0)
    conditions = request.json.get('conditions', [])

    if school_name not in data:
        return jsonify({"success": False, "message": "学校不存在"}), 404

    menu_data = data[school_name]
    menu = menu_data.get("menu", "") if isinstance(menu_data, dict) else str(menu_data)
    if not menu:
        return jsonify({"success": False, "message": "菜单为空"}), 400
    items = [item.strip() for item in menu.split("\n") if item.strip()]
    items = filter_staples(items)
    if not items:
        return jsonify({"success": False, "message": "没有可用菜品（已自动过滤主食）"}), 400

    prefer_tags = []
    avoid_tags = []
    condition_names = []

    if age < 12 or "儿童" in conditions:
        prefer_tags.extend(NUTRITION_RULES["儿童(<12岁)"]["prefer"])
        avoid_tags.extend(NUTRITION_RULES["儿童(<12岁)"]["avoid"])
        condition_names.append("儿童")

    if gender == "女" and "经期" in conditions:
        prefer_tags.extend(NUTRITION_RULES["女性经期"]["prefer"])
        avoid_tags.extend(NUTRITION_RULES["女性经期"]["avoid"])
        condition_names.append("女性经期")

    bmi_value = None
    if height > 0 and weight > 0:
        bmi_value = weight / ((height / 100) ** 2)

    is_underweight = "低体重" in conditions or (bmi_value is not None and bmi_value < 18.5)
    is_overweight = "超重" in conditions or (bmi_value is not None and bmi_value >= 24)

    if is_underweight:
        prefer_tags.extend(NUTRITION_RULES["低体重(BMI<18.5)"]["prefer"])
        condition_names.append("低体重")
    elif is_overweight:
        prefer_tags.extend(NUTRITION_RULES["超重(BMI>=24)"]["prefer"])
        avoid_tags.extend(NUTRITION_RULES["超重(BMI>=24)"]["avoid"])
        condition_names.append("超重")

    if "感冒" in conditions:
        prefer_tags.extend(NUTRITION_RULES["感冒"]["prefer"])
        avoid_tags.extend(NUTRITION_RULES["感冒"]["avoid"])
        condition_names.append("感冒")

    if "肠胃不适" in conditions:
        prefer_tags.extend(NUTRITION_RULES["肠胃不适"]["prefer"])
        avoid_tags.extend(NUTRITION_RULES["肠胃不适"]["avoid"])
        condition_names.append("肠胃不适")

    if "运动后" in conditions:
        prefer_tags.extend(NUTRITION_RULES["运动后"]["prefer"])
        condition_names.append("运动后")

    if "素食" in conditions:
        avoid_tags.extend(["肉", "鱼", "鸡", "鸭", "牛肉", "猪肉", "海鲜"])
        prefer_tags.extend(["豆腐", "素菜", "菌菇", "豆制品", "蔬菜"])
        condition_names.append("素食")

    filtered_items = []
    filtered_reasons = {}
    for item in items:
        skip = False
        reason = ""
        for tag in avoid_tags:
            if tag in item:
                skip = True
                reason = f"含有禁忌: {tag}"
                break
        if skip:
            filtered_reasons[item] = reason
            continue
        filtered_items.append(item)

    scored_items = []
    match_details = {}
    for item in filtered_items:
        score = 0
        matches = []
        for tag in prefer_tags:
            if tag in item:
                score += 1
                matches.append(tag)
        scored_items.append((item, score))
        if score > 0:
            match_details[item] = matches

    recommendation_text = ""
    details = []

    if scored_items:
        scored_items.sort(key=lambda x: x[1], reverse=True)
        max_score = scored_items[0][1]
        top_items = [item for item, score in scored_items if score == max_score]
        result = random.choice(top_items)
        recommendation_text = f"根据你的身体状况，为 {school_name} 的你决定：\n\n✅ {result}\n\n"
        if condition_names:
            details.append(f"• 考虑了你的状态: {', '.join(condition_names)}")
        if result in match_details:
            matched_tags = match_details[result]
            details.append(f"• 匹配营养需求: {', '.join(matched_tags)}")
        if filtered_reasons:
            details.append(f"• 已排除 {len(filtered_reasons)} 个不适合的菜品")
        recommendation_text += "\n".join(details) + "\n\n🍽️ 希望你用餐愉快！"
    else:
        if filtered_items:
            result = random.choice(filtered_items)
            recommendation_text = f"根据你的身体状况，为 {school_name} 的你决定：\n\n✅ {result}\n\n"
            if condition_names:
                details.append(f"• 考虑了你的状态: {', '.join(condition_names)}")
            if filtered_reasons:
                details.append(f"• 已排除 {len(filtered_reasons)} 个不适合的菜品")
            if details:
                recommendation_text += "\n".join(details) + "\n\n"
            recommendation_text += "🍽️ 希望你用餐愉快！"
        else:
            if items:
                result = random.choice(items)
                recommendation_text = f"根据你的身体状况，为 {school_name} 的你决定：\n\n✅ {result}\n\n🍽️ 希望你用餐愉快！"
            else:
                return jsonify({"success": False, "message": "没有可用菜品"}), 400

    return jsonify({
        "success": True,
        "result": result,
        "recommendation": recommendation_text,
        "details": details,
        "bmi": round(bmi_value, 1) if bmi_value else None
    })


@app.route('/api/bmi/calculate', methods=['POST'])
def calculate_bmi():
    """计算BMI"""
    height = request.json.get('height', 0)
    weight = request.json.get('weight', 0)
    if height <= 0 or weight <= 0:
        return jsonify({"success": False, "message": "身高和体重必须大于0"}), 400
    bmi = weight / ((height / 100) ** 2)
    if bmi < 18.5:
        category = "偏瘦"
        suggestion = "属于偏瘦范围，建议增加健康饮食"
    elif 18.5 <= bmi < 24:
        category = "正常"
        suggestion = "属于正常范围，继续保持健康饮食"
    elif 24 <= bmi < 28:
        category = "超重"
        suggestion = "属于超重范围，建议控制饮食并增加运动"
    else:
        category = "肥胖"
        suggestion = "属于肥胖范围，建议咨询专业医生"
    return jsonify({
        "success": True,
        "bmi": round(bmi, 1),
        "category": category,
        "suggestion": suggestion
    })


# ========== 数据导出/导入 API ==========
@app.route('/api/data/export', methods=['GET'])
def export_data():
    """导出所有数据为JSON"""
    data = load_all_data()
    return jsonify({
        "success": True,
        "data": data,
        "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "school_count": len(data)
    })


@app.route('/api/data/import', methods=['POST'])
def import_data():
    """从JSON数据导入（合并模式）"""
    import_schools = request.json.get('schools', {})
    if not import_schools or not isinstance(import_schools, dict):
        return jsonify({"success": False, "message": "没有可导入的数据"}), 400

    data = load_all_data()
    added = []
    updated = []

    for school_name, school_data in import_schools.items():
        if not isinstance(school_data, dict):
            continue
        menu = school_data.get("menu", "")
        if not menu:
            continue

        if school_name in data:
            # 合并菜品，去重
            existing_menu = data[school_name].get("menu", "")
            existing_items = set(item.strip() for item in existing_menu.split("\n") if item.strip())
            new_items = [item.strip() for item in menu.split("\n") if item.strip() and item.strip() not in existing_items]
            if new_items:
                merged = existing_menu + "\n" + "\n".join(new_items)
                data[school_name]["menu"] = merged
                data[school_name]["last_modified"] = time.strftime("%Y-%m-%d %H:%M")
                updated.append(school_name)
        else:
            data[school_name] = {
                "menu": menu,
                "last_modified": time.strftime("%Y-%m-%d %H:%M")
            }
            added.append(school_name)

    if save_all_data(data):
        return jsonify({
            "success": True,
            "message": f"导入完成！新增 {len(added)} 个学校，更新 {len(updated)} 个学校",
            "added": added,
            "updated": updated
        })
    else:
        return jsonify({"success": False, "message": "保存数据失败"}), 500


# ========== 菜品自动获取 API ==========
@app.route('/api/dish-sources', methods=['GET'])
def get_dish_sources():
    """获取指定学校可用的菜品数据源"""
    school_name = request.args.get('school', '').strip()
    if not school_name:
        return jsonify({"success": False, "message": "请提供学校名称"}), 400
    sources = []
    if school_name in CURATED_DATABASE:
        info = CURATED_DATABASE[school_name]
        sources.append({
            "name": "curated",
            "label": "精选数据库",
            "confidence": info["confidence"],
            "dish_count": len(info["dishes"]),
            "source_desc": info["source"]
        })
    return jsonify({
        "success": True,
        "school": school_name,
        "sources": sources
    })


@app.route('/api/dishes/fetch', methods=['POST'])
def api_fetch_dishes():
    """获取指定学校的菜品数据"""
    data = request.json or {}
    school_name = data.get('school_name', '').strip()
    source = data.get('source', None)

    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400

    if school_name in CURATED_DATABASE:
        info = CURATED_DATABASE[school_name]
        filtered_dishes = filter_staples(info["dishes"])
        return jsonify({
            "success": True,
            "school": school_name,
            "dishes": filtered_dishes,
            "source": "curated",
            "source_desc": info["source"],
            "confidence": info["confidence"],
            "note": "数据来自公开文章整理，建议核实",
            "dish_count": len(filtered_dishes)
        })

    return jsonify({
        "success": False,
        "message": f"暂无 {school_name} 的菜品数据。你可以手动输入菜品。"
    }), 404


@app.route('/api/dish-fetcher/schools', methods=['GET'])
def get_supported_schools():
    """获取所有支持自动获取菜品的学校列表"""
    schools = []
    for name, info in CURATED_DATABASE.items():
        schools.append({
            "name": name,
            "source": "curated",
            "confidence": info["confidence"],
            "dish_count": len(info["dishes"]),
            "source_desc": info["source"]
        })
    return jsonify({
        "success": True,
        "schools": schools,
        "total": len(schools)
    })


# ========== 错误处理 ==========
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "message": "API路径不存在"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "message": "服务器内部错误"
    }), 500


# ========== 启动入口 ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 智能食堂菜品推荐系统 - 吃了么")
    print("=" * 60)

    # 确保数据文件存在
    if not os.path.exists(DATA_FILE):
        add_default_school({})

    # 获取端口（Render 通过 PORT 环境变量指定）
    port = int(os.environ.get('PORT', 5001))

    print(f"\n📡 服务地址: http://0.0.0.0:{port}")
    print(f"📊 Web前端: http://localhost:{port}/")
    print(f"\n 部署到 Render 后，手机可通过公网URL访问\n")
    print("=" * 60)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # 生产环境关闭 debug
    )
