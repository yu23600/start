from flask import Flask, render_template, request, jsonify
import json
import os
import random
import time
import hashlib
import secrets
from dish_fetcher import fetch_dishes, get_available_sources, get_all_supported_schools, CURATED_DATABASE

app = Flask(__name__)

# ========== 全局配置 ==========
DATA_FILE = "cafeteria_data.json"
MEAL_USERS_FILE = "meal_users.json"
MEAL_LOGS_FILE = "meal_logs.json"
USER_TAGS_FILE = "user_dish_tags.json"

# ========== 管理员配置 ==========
ADMIN_USERNAMES = ['nick3448450113']  # 预设管理员账号列表

def is_admin(username):
    """检查用户是否为管理员"""
    if not username:
        return False
    if username in ADMIN_USERNAMES:
        return True
    users = load_meal_users()
    if username in users:
        return users[username].get('role') == 'admin'
    return False


# ========== 打卡用户管理 ==========
def load_meal_users():
    """加载打卡用户列表"""
    if not os.path.exists(MEAL_USERS_FILE):
        return {}
    try:
        with open(MEAL_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"加载打卡用户出错: {e}")
        return {}


def save_meal_users(users):
    """保存打卡用户列表"""
    try:
        with open(MEAL_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存打卡用户出错: {e}")
        return False


def load_meal_logs():
    """加载三餐打卡记录"""
    if not os.path.exists(MEAL_LOGS_FILE):
        return {}
    try:
        with open(MEAL_LOGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"加载打卡记录出错: {e}")
        return {}


def save_meal_logs(logs):
    """保存三餐打卡记录"""
    try:
        with open(MEAL_LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存打卡记录出错: {e}")
        return False


def load_user_dish_tags():
    """加载用户提交的菜品标签"""
    if not os.path.exists(USER_TAGS_FILE):
        return {}
    try:
        with open(USER_TAGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"加载用户标签出错: {e}")
        return {}

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


def load_all_data():
    """加载所有学校数据"""
    if not os.path.exists(DATA_FILE):
        return {}
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            return {}
        
        # 验证每个学校的格式
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


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/universities.json')
def get_universities():
    """提供大学列表JSON文件"""
    import os
    uni_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'universities.json')
    
    if os.path.exists(uni_file):
        with open(uni_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    else:
        return jsonify({"universities": []}), 404


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
    
    # 格式化菜单
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
    
    if not items:
        return jsonify({"success": False, "message": "没有可用菜品"}), 400
    
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
    
    if not items:
        return jsonify({"success": False, "message": "没有可用菜品"}), 400
    
    # 分析用户需求
    prefer_tags = []
    avoid_tags = []
    condition_names = []
    
    # 1. 根据年龄/儿童状态
    if age < 12 or "儿童" in conditions:
        prefer_tags.extend(NUTRITION_RULES["儿童(<12岁)"]["prefer"])
        avoid_tags.extend(NUTRITION_RULES["儿童(<12岁)"]["avoid"])
        condition_names.append("儿童")
    
    # 2. 根据性别和经期状态
    if gender == "女" and "经期" in conditions:
        prefer_tags.extend(NUTRITION_RULES["女性经期"]["prefer"])
        avoid_tags.extend(NUTRITION_RULES["女性经期"]["avoid"])
        condition_names.append("女性经期")
    
    # 3. 根据BMI
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
    
    # 4. 根据其他状态
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
    
    # 智能筛选逻辑
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
    
    # 计算匹配分数
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
    
    # 选择最佳菜品
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


@app.route('/api/dish-sources', methods=['GET'])
def get_dish_sources():
    """获取指定学校可用的菜品数据源"""
    school_name = request.args.get('school', '').strip()
    if not school_name:
        return jsonify({"success": False, "message": "请提供学校名称"}), 400
    
    sources = get_available_sources(school_name)
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
    
    result = fetch_dishes(school_name, source)
    
    if result["success"]:
        return jsonify(result)
    else:
        return jsonify(result), 404


@app.route('/api/dish-fetcher/schools', methods=['GET'])
def get_supported_schools():
    """获取所有支持自动获取菜品的学校列表"""
    schools = get_all_supported_schools()
    return jsonify({
        "success": True,
        "schools": schools,
        "total": len(schools)
    })


# ========== 管理员 API ==========
@app.route('/api/admin/menu/reset', methods=['POST'])
def admin_reset_menu():
    """管理员重置指定学校菜单为精选版本"""
    data = request.json or {}
    username = data.get('username', '').strip()
    school_name = data.get('school_name', '').strip()
    
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    
    if school_name not in CURATED_DATABASE:
        return jsonify({"success": False, "message": f"精选数据库中暂无 {school_name} 的数据"}), 404
    
    curated_dishes = CURATED_DATABASE[school_name]["dishes"]
    formatted_menu = "\n".join(curated_dishes)
    now = time.strftime("%Y-%m-%d %H:%M")
    
    db_data = load_all_data()
    db_data[school_name] = {"menu": formatted_menu, "last_modified": now}
    save_all_data(db_data)
    
    return jsonify({
        "success": True,
        "message": f"已将「{school_name}」菜单重置为精选版本（{len(curated_dishes)} 道菜品）",
        "count": len(curated_dishes)
    })


@app.route('/api/admin/menu/clear', methods=['POST'])
def admin_clear_menu():
    """管理员清空指定学校菜单"""
    data = request.json or {}
    username = data.get('username', '').strip()
    school_name = data.get('school_name', '').strip()
    
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    
    db_data = load_all_data()
    if school_name in db_data:
        del db_data[school_name]
    save_all_data(db_data)
    
    return jsonify({
        "success": True,
        "message": f"已清空「{school_name}」的菜单"
    })


@app.route('/api/admin/menu/edit', methods=['POST'])
def admin_edit_menu():
    """管理员直接编辑指定学校菜单"""
    data = request.json or {}
    username = data.get('username', '').strip()
    school_name = data.get('school_name', '').strip()
    menu = data.get('menu', '')
    
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    
    items = [item.strip() for item in menu.replace(",", "\n").split("\n") if item.strip()]
    formatted_menu = "\n".join(items)
    now = time.strftime("%Y-%m-%d %H:%M")
    
    db_data = load_all_data()
    db_data[school_name] = {"menu": formatted_menu, "last_modified": now}
    save_all_data(db_data)
    
    return jsonify({
        "success": True,
        "message": f"已更新「{school_name}」菜单（{len(items)} 道菜品）",
        "count": len(items)
    })


@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    """管理员获取所有用户列表"""
    username = request.args.get('username', '').strip()
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    
    users = load_meal_users()
    logs = load_meal_logs()
    
    user_list = []
    for name, info in users.items():
        meal_count = 0
        if name in logs:
            for date_data in logs[name].values():
                for meal_dishes in date_data.values():
                    meal_count += len(meal_dishes)
        user_list.append({
            "username": name,
            "role": info.get('role', 'user'),
            "created_at": info.get('created_at', ''),
            "goal": info.get('goal', ''),
            "meal_count": meal_count
        })
    
    return jsonify({
        "success": True,
        "users": sorted(user_list, key=lambda x: x.get('created_at', ''), reverse=True),
        "total": len(user_list)
    })


@app.route('/api/admin/user/<target_username>', methods=['DELETE'])
def admin_delete_user(target_username):
    """管理员删除用户"""
    data = request.json or {}
    username = data.get('username', '').strip()
    
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not target_username:
        return jsonify({"success": False, "message": "目标用户不能为空"}), 400
    
    users = load_meal_users()
    if target_username not in users:
        return jsonify({"success": False, "message": "用户不存在"}), 404
    
    del users[target_username]
    save_meal_users(users)
    
    logs = load_meal_logs()
    if target_username in logs:
        del logs[target_username]
        save_meal_logs(logs)
    
    return jsonify({
        "success": True,
        "message": f"已删除用户「{target_username}」及其所有数据"
    })


@app.route('/api/admin/add', methods=['POST'])
def admin_add_admin():
    """添加管理员"""
    data = request.json or {}
    username = data.get('username', '').strip()
    target_username = data.get('target_username', '').strip()
    
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not target_username:
        return jsonify({"success": False, "message": "目标用户不能为空"}), 400
    
    users = load_meal_users()
    if target_username not in users:
        return jsonify({"success": False, "message": "用户不存在"}), 404
    
    users[target_username]['role'] = 'admin'
    if target_username not in ADMIN_USERNAMES:
        ADMIN_USERNAMES.append(target_username)
    
    if save_meal_users(users):
        return jsonify({"success": True, "message": f"已将「{target_username}」设为管理员"})
    else:
        return jsonify({"success": False, "message": "保存失败"}), 500


@app.route('/api/admin/remove', methods=['POST'])
def admin_remove_admin():
    """移除管理员权限"""
    data = request.json or {}
    username = data.get('username', '').strip()
    target_username = data.get('target_username', '').strip()
    
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not target_username:
        return jsonify({"success": False, "message": "目标用户不能为空"}), 400
    if target_username == username:
        return jsonify({"success": False, "message": "不能移除自己的管理员权限"}), 400
    
    users = load_meal_users()
    if target_username not in users:
        return jsonify({"success": False, "message": "用户不存在"}), 404
    
    users[target_username]['role'] = 'user'
    if target_username in ADMIN_USERNAMES:
        ADMIN_USERNAMES.remove(target_username)
    
    if save_meal_users(users):
        return jsonify({"success": True, "message": f"已移除「{target_username}」的管理员权限"})
    else:
        return jsonify({"success": False, "message": "保存失败"}), 500


@app.route('/api/admin/stats', methods=['GET'])
def admin_get_stats():
    """获取系统统计"""
    username = request.args.get('username', '').strip()
    if not username or not is_admin(username):
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    
    db_data = load_all_data()
    users = load_meal_users()
    logs = load_meal_logs()
    user_tags = load_user_dish_tags()
    
    total_meals = 0
    total_dishes = 0
    for user_logs in logs.values():
        for date_data in user_logs.values():
            for meal_dishes in date_data.values():
                total_meals += 1
                total_dishes += len(meal_dishes)
    
    return jsonify({
        "success": True,
        "stats": {
            "school_count": len(db_data),
            "user_count": len(users),
            "admin_count": sum(1 for u in users.values() if u.get('role') == 'admin' or u.get('username', '') in ADMIN_USERNAMES),
            "total_meal_logs": total_meals,
            "total_dishes_logged": total_dishes,
            "dish_tags_count": len(user_tags)
        }
    })


if __name__ == '__main__':
    # 确保数据文件存在
    if not os.path.exists(DATA_FILE):
        add_default_school({})
    
    app.run(debug=True, host='0.0.0.0', port=5001)
