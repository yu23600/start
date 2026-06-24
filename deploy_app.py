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
import re
import time
import datetime
import hashlib
import secrets

# ========== Supabase 云数据库 ==========
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
supabase_client = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print("✅ Supabase 连接成功")
    except Exception as e:
        print(f"️ Supabase 连接失败，将使用本地JSON存储: {e}")

# ========== Supabase 自动迁移 ==========
def migrate_supabase():
    """自动给 Supabase 表添加缺失的列"""
    if not supabase_client:
        return
    try:
        # 给 meal_users 表添加 goal 列（如果不存在）
        supabase_client.rpc('exec_sql', {
            'sql': "ALTER TABLE meal_users ADD COLUMN IF NOT EXISTS goal TEXT DEFAULT '';"
        }).execute()
        print("✅ Supabase 迁移完成（goal 列）")
    except Exception as e:
        # RPC 可能不存在，尝试直接 REST 方式（忽略错误，列可能已存在）
        print(f"⚠️ Supabase 自动迁移跳过: {e}")

if SUPABASE_URL and SUPABASE_ANON_KEY:
    migrate_supabase()

# ========== 基础路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'chimei', 'web_app', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'chimei', 'web_app', 'static'))
CORS(app)

# ========== 配置 ==========
DATA_FILE = os.path.join(BASE_DIR, 'chimei', 'cafeteria_data.json')
USER_TAGS_FILE = os.path.join(BASE_DIR, 'chimei', 'user_dish_tags.json')
MEAL_LOGS_FILE = os.path.join(BASE_DIR, 'chimei', 'meal_logs.json')
MEAL_USERS_FILE = os.path.join(BASE_DIR, 'chimei', 'meal_users.json')

# ========== 主食/通用词汇过滤 ==========
STAPLE_FOODS = {"米饭", "面条"}

def filter_staples(items):
    """过滤掉主食和通用词汇"""
    return [item for item in items if item not in STAPLE_FOODS]

# ========== 营养规则库 ==========
NUTRITION_RULES = {
    "儿童(<12岁)": {
        "prefer": ["牛奶", "鸡蛋", "豆腐", "小鱼", "菠菜", "胡萝卜", "虾仁", "核桃", "蒸蛋", "粥",
                    "番茄", "南瓜", "玉米", "排骨汤", "鸡汤"],
        "avoid": ["辛辣", "油炸", "浓茶", "咖啡", "酒精", "生冷", "过硬", "麻辣", "泡椒"]
    },
    "女性经期": {
        "prefer": ["红枣", "红糖", "姜", "桂圆", "猪肝", "乌鸡", "热汤", "暖胃", "热粥", "温补",
                    "羊肉", "牛肉", "枸杞", "黑豆", "红豆"],
        "avoid": ["冰品", "西瓜", "梨", "螃蟹", "绿茶", "苦瓜", "冬瓜", "冷饮", "寒性", "冰镇", "生冷"]
    },
    "低体重(BMI<18.5)": {
        "prefer": ["坚果", "牛油果", "全脂", "橄榄油", "三文鱼", "牛肉", "鸡蛋", "高蛋白", "健康脂肪",
                    "红烧", "糖醋", "芝士", "奶油", "花生", "芝麻"],
        "avoid": []
    },
    "超重(BMI>=24)": {
        "prefer": ["清蒸", "凉拌", "杂粮", "蔬菜", "鸡胸", "豆腐", "低脂", "高纤维", "清淡",
                    "西兰花", "黄瓜", "番茄", "芹菜", "冬瓜", "苦瓜"],
        "avoid": ["红烧肉", "炸鸡", "蛋糕", "含糖饮料", "肥肉", "油炸", "高糖", "重口味",
                   "奶油", "芝士", "糖醋", "油爆", "干煸"]
    },
    "感冒": {
        "prefer": ["热汤", "粥", "姜", "葱", "清淡", "易消化", "鸡汤", "面汤", "蒸蛋"],
        "avoid": ["辛辣", "油腻", "生冷", "油炸", "麻辣", "烧烤"]
    },
    "肠胃不适": {
        "prefer": ["粥", "蒸蛋", "山药", "南瓜", "温和", "易消化", "面条", "软烂", "清汤"],
        "avoid": ["油炸", "生冷", "豆类", "辛辣", "酸性", "高纤维", "麻辣", "烧烤", "过硬", "糯米"]
    },
    "运动后": {
        "prefer": ["蛋白质", "香蕉", "牛奶", "鸡胸", "鸡蛋", "复合碳水", "牛肉", "鱼", "豆腐"],
        "avoid": []
    },
    "上火": {
        "prefer": ["绿豆", "冬瓜", "苦瓜", "黄瓜", "梨", "莲藕", "芹菜", "清淡", "凉性", "清热"],
        "avoid": ["辛辣", "油炸", "烧烤", "羊肉", "辣椒", "麻辣", "燥热", "煎炸", "姜", "蒜"]
    },
    "增肌": {
        "prefer": ["高蛋白", "鸡胸", "牛肉", "鱼", "鸡蛋", "牛奶", "豆腐", "蛋白质", "碳水"],
        "avoid": []
    },
    "海鲜过敏": {
        "prefer": [],
        "avoid": ["虾", "蟹", "鱼", "贝", "牡蛎", "扇贝", "蛤", "鱿鱼", "章鱼", "海鱼", "海鲜", "三文鱼", "龙利鱼"]
    },
    "花生过敏": {
        "prefer": [],
        "avoid": ["花生", "花生酱", "芝麻"]
    },
    "乳糖不耐": {
        "prefer": [],
        "avoid": ["牛奶", "奶油", "芝士", "酸奶", "全脂奶", "脱脂奶"]
    },
    "素食": {
        "prefer": ["豆腐", "素菜", "菌菇", "豆制品", "蔬菜", "番茄", "土豆", "茄子", "青椒"],
        "avoid": ["肉", "鱼", "鸡", "鸭", "牛", "猪", "羊", "虾", "蟹", "海鲜", "培根", "火腿", "腊肠"]
    }
}


# ========== 常见菜品营养标签库 ==========
# 用于智能匹配，给每个常见菜品打标签，提高推荐准确度
FOOD_TAGS = {
    # 蛋白质类
    "宫保鸡丁": ["高蛋白", "鸡肉", "微辣", "花生"],
    "麻婆豆腐": ["豆腐", "高蛋白", "麻辣", "下饭"],
    "西红柿炒蛋": ["鸡蛋", "番茄", "清淡", "高蛋白", "易消化"],
    "回锅肉": ["猪肉", "高脂", "微辣", "下饭"],
    "水煮肉片": ["猪肉", "高蛋白", "麻辣", "重口味"],
    "糖醋排骨": ["排骨", "糖醋", "高糖", "高脂"],
    "红烧肉": ["猪肉", "高脂", "高糖", "肥肉", "重口味"],
    "鱼香肉丝": ["猪肉", "高蛋白", "微辣", "下饭"],
    "酸菜鱼": ["鱼", "高蛋白", "酸辣", "低脂"],
    "清蒸鲈鱼": ["鱼", "高蛋白", "清淡", "低脂", "易消化"],
    "番茄牛腩": ["牛肉", "高蛋白", "番茄", "清淡"],
    "地三鲜": ["土豆", "茄子", "青椒", "油炸", "素菜"],
    "木须肉": ["猪肉", "鸡蛋", "高蛋白", "清淡"],
    "青椒肉丝": ["猪肉", "高蛋白", "微辣", "青椒"],
    "蒜蓉西兰花": ["西兰花", "素菜", "清淡", "高纤维", "低脂"],
    "干煸豆角": ["豆角", "素菜", "油炸", "微辣"],
    "红烧狮子头": ["猪肉", "高脂", "重口味"],
    "油爆虾": ["虾", "高蛋白", "油炸", "海鲜"],
    "孜然羊肉": ["羊肉", "高蛋白", "燥热", "辛辣"],
    "京酱肉丝": ["猪肉", "高蛋白", "清淡", "甜面酱"],
    "土豆牛肉": ["牛肉", "高蛋白", "土豆", "清淡"],
    "香菇肉片": ["猪肉", "高蛋白", "菌菇", "清淡"],
    "糖醋里脊": ["猪肉", "高蛋白", "糖醋", "高糖", "油炸"],
    "东坡肉": ["猪肉", "高脂", "高糖", "重口味"],
    "烤鸭": ["鸭肉", "高蛋白", "高脂", "油炸"],
    "炸鱼排": ["鱼", "高蛋白", "油炸"],
    "卤鸭头": ["鸭肉", "高蛋白", "卤味", "重口味"],
    "鸭腿": ["鸭肉", "高蛋白", "卤味"],
    "叉烧": ["猪肉", "高蛋白", "高糖", "卤味"],
    "酱排骨": ["排骨", "高蛋白", "卤味", "重口味"],
    "红烧小排": ["排骨", "高蛋白", "红烧", "高脂"],
    "糖醋小排": ["排骨", "高蛋白", "糖醋", "高糖"],
    "剁椒鱼头": ["鱼", "高蛋白", "辛辣", "剁椒"],
    "茄汁龙利鱼": ["鱼", "高蛋白", "番茄", "清淡", "低脂"],
    "小炒鸡胗": ["鸡肉", "高蛋白", "微辣"],
    "黑椒里脊": ["猪肉", "高蛋白", "黑椒", "微辣"],
    "葱油木耳": ["木耳", "素菜", "清淡", "高纤维"],
    "鸡汁娃娃菜": ["白菜", "素菜", "清淡", "高纤维"],
    "黄瓜炒肉": ["猪肉", "黄瓜", "清淡", "低脂"],
    "香干韭菜": ["豆腐干", "韭菜", "素菜", "高蛋白"],
    "苦瓜炒蛋": ["鸡蛋", "苦瓜", "清热", "高蛋白", "凉性"],
    "油炸酥肉": ["猪肉", "高蛋白", "油炸", "高脂"],
    "紫菜蛋汤": ["鸡蛋", "紫菜", "清淡", "易消化", "汤"],
    "卤莲藕": ["莲藕", "素菜", "卤味", "清淡"],
    "干豆角": ["豆角", "素菜", "高纤维"],
    "酸辣土豆丝": ["土豆", "素菜", "酸辣", "清淡"],
    "清炒时蔬": ["蔬菜", "素菜", "清淡", "高纤维", "低脂"],
    "炒菜花": ["菜花", "素菜", "清淡", "高纤维"],
    "素炒西蓝花": ["西兰花", "素菜", "清淡", "高纤维", "低脂"],
    "青菜炖豆腐": ["豆腐", "青菜", "素菜", "清淡", "高蛋白", "易消化"],
    "麻辣香锅": ["混合", "麻辣", "重口味", "油炸", "辛辣"],
    "炒豆芽": ["豆芽", "素菜", "清淡", "高纤维"],
    "卷心菜": ["素菜", "清淡", "高纤维"],
    "西蓝花": ["素菜", "清淡", "高纤维", "低脂"],
    "炒油豆腐": ["豆腐", "素菜", "油炸", "高蛋白"],
    "木耳青菜": ["木耳", "青菜", "素菜", "清淡", "高纤维"],
    "卤素鸡": ["豆制品", "素菜", "卤味", "高蛋白"],
    "茭白肉片": ["猪肉", "茭白", "清淡", "高蛋白"],
    "炸烹佛手肉": ["猪肉", "高蛋白", "油炸"],
    "炒米粉": ["碳水", "清淡"],
    "酸笋粉": ["碳水", "酸辣"],
    "炸酱面": ["碳水", "面条", "肉酱", "高脂"],
    "臊子面": ["碳水", "面条", "猪肉", "酸辣"],
    "裤带面": ["碳水", "面条"],
    "咸菜面": ["碳水", "面条", "咸菜"],
    "南园一层牛角包": ["面包", "高糖", "高脂"],
    "紫二虎皮鸡蛋": ["鸡蛋", "高蛋白", "卤味"],
    "桃李二层三杯鸡": ["鸡肉", "高蛋白", "三杯", "重口味"],
    "桃李二层冬瓜虾皮汤": ["汤", "冬瓜", "虾皮", "清淡", "凉性"],
    "清芬二层烤鸭": ["鸭肉", "高蛋白", "高脂"],
    "紫荆紫薯包": ["紫薯", "碳水", "素菜"],
    "紫三糖醋里脊": ["猪肉", "高蛋白", "糖醋", "高糖", "油炸"],
    "牛肉味状元饼": ["牛肉", "碳水", "高蛋白"],
    "红糖烧麦": ["碳水", "红糖", "高糖"],
    "三鲜锅贴": ["碳水", "猪肉", "虾", "海鲜"],
    "小笼包": ["碳水", "猪肉", "高脂"],
    "麻球": ["碳水", "高糖", "油炸"],
    "五谷豆浆": ["豆浆", "高蛋白", "清淡", "素菜"],
    "豆浆": ["豆浆", "高蛋白", "清淡", "素菜"],
    "豆腐脑": ["豆腐", "高蛋白", "清淡", "易消化", "素菜"],
    "煎蛋": ["鸡蛋", "高蛋白", "油炸"],
    "蒸蛋": ["鸡蛋", "高蛋白", "清淡", "易消化"],
    "虎皮鸡蛋": ["鸡蛋", "高蛋白", "卤味", "油炸"],
    "油条": ["碳水", "油炸", "高脂"],
    "卷饼": ["碳水"],
    "锅贴": ["碳水", "猪肉", "油炸"],
    "生煎包": ["碳水", "猪肉", "油炸", "高脂"],
    "馄饨": ["碳水", "猪肉", "汤", "易消化"],
    "本帮熏鱼": ["鱼", "高蛋白", "熏制", "高脂"],
    "腌笃鲜": ["汤", "猪肉", "笋", "清淡", "高蛋白"],
    "火龙果素肠": ["素菜", "火龙果", "清淡"],
    "哈密瓜年糕牛肉粒": ["牛肉", "高蛋白", "年糕", "碳水", "水果"],
    "月饼": ["碳水", "高糖", "高脂"],
    "粥": ["碳水", "清淡", "易消化"],
    "热粥": ["碳水", "清淡", "易消化", "暖胃"],
}


# ========== 智能匹配函数 ==========
def tag_matches(tag, item):
    """
    智能标签匹配，带词边界检测，避免误伤。
    例如："面条"不会匹配"牛肉面"，"鱼"不会匹配"鱼香肉丝"（因为"鱼香"是一个词）
    """
    if tag in item:
        # 短标签（1-2字）需要词边界检测
        if len(tag) <= 2:
            idx = item.index(tag)
            before_ok = (idx == 0) or (item[idx - 1] in '的了与和或 ')
            after_idx = idx + len(tag)
            after_ok = (after_idx >= len(item)) or (item[after_idx] in '的了与和或 ')
            # 特殊处理：某些短标签作为菜名一部分时应该匹配
            if tag in ('面', '粥', '汤', '蛋', '鱼', '肉', '鸡', '鸭', '牛', '羊', '猪', '虾', '蟹', '姜', '葱'):
                # 这些标签在菜名末尾时应该匹配（如"牛肉面"的"面"）
                if after_idx >= len(item):
                    return True
                # 这些标签在菜名开头时也应该匹配
                if idx == 0 and after_idx < len(item) and item[after_idx] not in ('香', '汤', '肉', '片', '丝', '块', '排', '腿', '翅'):
                    return True
                return before_ok or after_ok
            return before_ok and after_ok
        # 长标签（3字以上）直接子串匹配即可
        return True
    return False


def dish_has_meat(dish_name):
    """判断菜品是否含肉类（用于素食过滤）"""
    meat_keywords = ['肉', '鸡', '鸭', '牛', '猪', '羊', '鱼', '虾', '蟹', '海鲜', '培根', '火腿', '腊肠', '排骨', '鸭腿', '叉烧']
    # 排除素菜名中含肉字但不是真肉的
    veg_exceptions = ['肉丝饼', '素肉', '人造肉', '素鸡', '素鸭', '素火腿', '素培根']
    for exc in veg_exceptions:
        if exc in dish_name:
            return False
    for kw in meat_keywords:
        if tag_matches(kw, dish_name):
            return True
    return False


# ========== 众包标签体系 ==========
TAG_TAXONOMY = {
    "蛋白质": ["鸡肉", "猪肉", "牛肉", "鱼", "豆制品"],
    "蔬菜": ["蔬菜", "菌菇", "根茎类"],
    "烹饪方式": ["清淡", "油炸", "辛辣", "糖醋"],
    "营养特征": ["高蛋白", "高纤维", "低脂", "高脂", "高糖", "易消化", "碳水", "汤"]
}

ALL_VALID_TAGS = set()
for _tags in TAG_TAXONOMY.values():
    ALL_VALID_TAGS.update(_tags)


def load_user_dish_tags():
    """加载用户提交的菜品标签（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            resp = supabase_client.table('dish_tags').select('*').execute()
            data = {}
            for row in resp.data:
                data[row['dish_name']] = row['tags'] if isinstance(row['tags'], list) else json.loads(row['tags']) if isinstance(row['tags'], str) else []
            return data
        except Exception as e:
            print(f"Supabase 加载标签出错: {e}")
    if not os.path.exists(USER_TAGS_FILE):
        return {}
    try:
        with open(USER_TAGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"加载用户标签出错: {e}")
        return {}


def save_user_dish_tags(tags):
    """保存用户提交的菜品标签（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            rows = [{"dish_name": dish, "tags": tag_list} for dish, tag_list in tags.items()]
            if rows:
                supabase_client.table('dish_tags').upsert(rows, on_conflict='dish_name').execute()
            return True
        except Exception as e:
            print(f"Supabase 保存标签出错: {e}")
    try:
        with open(USER_TAGS_FILE, "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存用户标签出错: {e}")
        return False


def load_meal_logs():
    """加载三餐打卡记录（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            resp = supabase_client.table('meal_logs').select('*').execute()
            data = {}
            for row in resp.data:
                username = row['username']
                date = row['date']
                meals = row['meals']
                if isinstance(meals, str):
                    meals = json.loads(meals)
                if username not in data:
                    data[username] = {}
                data[username][date] = meals
            return data
        except Exception as e:
            print(f"Supabase 加载打卡记录出错: {e}")
    # 降级：JSON 文件
    if not os.path.exists(MEAL_LOGS_FILE):
        return {}
    try:
        with open(MEAL_LOGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        # 检测旧格式：顶层key是日期格式 → 迁移到"默认用户"下
        if data and all(isinstance(k, str) and len(k) == 10 and k[4] == '-' for k in list(data.keys())[:3]):
            migrated = {"默认用户": data}
            save_meal_logs(migrated)
            return migrated
        return data
    except Exception as e:
        print(f"加载打卡记录出错: {e}")
        return {}


def save_meal_logs(logs):
    """保存三餐打卡记录（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            rows = []
            for username, user_logs in logs.items():
                if not isinstance(user_logs, dict):
                    continue
                for date, meals in user_logs.items():
                    rows.append({
                        "username": username,
                        "date": date,
                        "meals": meals
                    })
            if rows:
                supabase_client.table('meal_logs').upsert(rows, on_conflict='username,date').execute()
            return True
        except Exception as e:
            print(f"Supabase 保存打卡记录出错: {e}")
    try:
        with open(MEAL_LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存打卡记录出错: {e}")
        return False


# ========== 打卡用户管理 ==========
def load_meal_users():
    """加载打卡用户列表（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            resp = supabase_client.table('meal_users').select('*').execute()
            data = {}
            for row in resp.data:
                data[row['username']] = {
                    "password_hash": row['password_hash'],
                    "salt": row['salt'],
                    "created_at": row['created_at'],
                    "goal": row.get('goal', '') or ''
                }
            return data
        except Exception as e:
            print(f"Supabase 加载用户出错: {e}")
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
    """保存打卡用户列表（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            rows = []
            for username, info in users.items():
                rows.append({
                    "username": username,
                    "password_hash": info.get('password_hash', ''),
                    "salt": info.get('salt', ''),
                    "created_at": info.get('created_at', datetime.datetime.now().isoformat()),
                    "goal": info.get('goal', '')
                })
            if rows:
                supabase_client.table('meal_users').upsert(rows, on_conflict='username').execute()
            return True
        except Exception as e:
            print(f"Supabase 保存用户出错: {e}")
    try:
        with open(MEAL_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存打卡用户出错: {e}")
        return False


def hash_password(password, salt=None):
    """对密码加盐哈希"""
    if salt is None:
        salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return h, salt


def verify_password(password, stored_hash, salt):
    """验证密码"""
    h, _ = hash_password(password, salt)
    return h == stored_hash


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
            "鸭腿", "麻辣香锅",
            "杀猪粉", "麻辣烫", "菜配饭",
            "烤鸭饭", "煎蛋", "番茄鸡蛋汤", "鸡蛋凉面",
            "黄焖鸡", "意大利面", "手枪腿意面", "鸡腿面",
            "拌粉", "卤味", "老鸭粉丝汤", "套餐饭", "糖醋排骨饭",
            "烤肉饭", "沙拉烤肉饭", "螺蛳粉", "渔粉", "紫米饭",
            "杂粮煎饼", "无骨炸鸡", "鸡公煲", "排骨粉",
            "饭团", "肉粽", "鸡蛋仔", "冰粉", "双皮奶", "绿豆汤",
            "四果汤", "白桃水仙",
            "卤面", "拌面", "自选水饺", "犀米家寿司",
            "烤芋头粉", "粥", "闽南香脆饭", "盖浇饭",
            "米饭", "馒头", "花卷", "面条", "拉面"
        ],
        "source": "2025年多篇宁德师范学院食堂美食攻略综合整理（含时效性校验）",
        "confidence": "high"
    },
    "福建医科大学": {
        "dishes": [
            "竹筒饭", "连江锅边", "福鼎肉片", "农家烤鱼",
            "重庆鸡公煲", "陕西凉皮", "沙茶面", "莆田打卤面",
            "牛肉面", "瓦罐汤", "刀削面", "小炒",
            "炒泗粉", "炒米粉", "卤面套餐", "鱼丸", "肉燕",
            "捞化", "拌面", "扁肉", "卤味", "豆花",
            "烧仙草", "西米露", "拌粉干", "沙县小吃",
            "汤浓盖饭", "铁板烧", "烤鱼饭", "蓝瘦香菇",
            "自选菜", "盖浇饭", "麻辣香锅",
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "回锅肉", "水煮肉片", "清炒时蔬", "酸辣土豆丝",
            "糖醋排骨", "酸菜鱼", "鱼香肉丝", "地三鲜",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "2025年多篇福建医科大学食堂美食文章及点评综合整理（含时效性校验）",
        "confidence": "high"
    },
}


# ========== 本地数据管理 ==========
def load_all_data():
    """加载所有学校数据（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            resp = supabase_client.table('school_menus').select('*').execute()
            data = {}
            for row in resp.data:
                data[row['school_name']] = {
                    "menu": row['menu'],
                    "last_modified": row['last_modified']
                }
            return data
        except Exception as e:
            print(f"Supabase 加载数据出错: {e}")
    # 降级：JSON 文件
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
    """保存所有学校数据（Supabase 优先，降级到 JSON）"""
    if supabase_client:
        try:
            rows = []
            for school_name, school_data in data.items():
                menu = school_data.get("menu", "") if isinstance(school_data, dict) else str(school_data)
                last_modified = school_data.get("last_modified", time.strftime("%Y-%m-%d %H:%M")) if isinstance(school_data, dict) else time.strftime("%Y-%m-%d %H:%M")
                rows.append({
                    "school_name": school_name,
                    "menu": menu,
                    "last_modified": last_modified
                })
            if rows:
                supabase_client.table('school_menus').upsert(rows, on_conflict='school_name').execute()
            return True
        except Exception as e:
            print(f"Supabase 保存数据出错: {e}")
    # 降级：JSON 文件
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


@app.route('/api/curated-database', methods=['GET'])
def get_curated_database():
    """返回精选菜品数据库（食堂图鉴）"""
    return jsonify({
        "success": True,
        "schools": CURATED_DATABASE,
        "count": len(CURATED_DATABASE)
    })


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
    # 排除用户不想要的菜品
    exclude = request.args.get('exclude', '').strip()
    if exclude:
        candidates = [item for item in items if item != exclude]
        if not candidates:
            candidates = items  # 只剩一个菜，无法排除
    else:
        candidates = items
    result = random.choice(candidates)
    return jsonify({
        "success": True,
        "result": result,
        "school": school_name
    })


@app.route('/api/recommend/smart', methods=['POST'])
def smart_recommend():
    """智能推荐（基于目标）"""
    data = load_all_data()
    school_name = request.json.get('school_name', '')
    goal = request.json.get('goal', '')  # cutting / bulking / healthy
    allergies = request.json.get('allergies', [])  # 海鲜过敏/花生过敏/乳糖不耐
    exclude = request.json.get('exclude', [])  # 已推荐过的菜品，不再推荐

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

    # 排除已推荐过的菜品
    if exclude:
        items = [item for item in items if item not in exclude]
        if not items:
            # 全部排除完了，重置为全部菜品
            items = filter_staples([item.strip() for item in menu.split("\n") if item.strip()])

    prefer_tags = []
    avoid_tags = []
    goal_name = ""

    # 根据目标设置偏好
    if goal == 'cutting':
        prefer_tags.extend(["清蒸", "凉拌", "杂粮", "蔬菜", "鸡胸", "豆腐", "低脂", "高纤维", "清淡",
                            "西兰花", "黄瓜", "番茄", "芹菜", "冬瓜", "苦瓜"])
        avoid_tags.extend(["红烧肉", "炸鸡", "蛋糕", "含糖饮料", "肥肉", "油炸", "高糖", "重口味",
                           "奶油", "芝士", "糖醋", "油爆", "干煸"])
        goal_name = "减脂期"
    elif goal == 'bulking':
        prefer_tags.extend(["高蛋白", "鸡胸", "牛肉", "鱼", "鸡蛋", "牛奶", "豆腐", "蛋白质", "碳水",
                            "坚果", "香蕉", "复合碳水"])
        goal_name = "增肌期"
    elif goal == 'healthy':
        prefer_tags.extend(["清蒸", "凉拌", "蔬菜", "豆腐", "鸡蛋", "清淡", "易消化",
                            "西兰花", "番茄", "胡萝卜", "菌菇"])
        goal_name = "保持健康"

    # 过敏安全过滤（始终生效）
    if "海鲜过敏" in allergies:
        avoid_tags.extend(["虾", "蟹", "鱼", "贝", "牡蛎", "扇贝", "蛤", "鱿鱼", "章鱼", "海鱼", "海鲜", "三文鱼", "龙利鱼"])
    if "花生过敏" in allergies:
        avoid_tags.extend(["花生", "花生酱", "芝麻"])
    if "乳糖不耐" in allergies:
        avoid_tags.extend(["牛奶", "奶油", "芝士", "酸奶", "全脂奶", "脱脂奶"])

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

    # 合并用户标签与内置FOOD_TAGS（内置优先）
    user_tags = load_user_dish_tags()
    merged_tags = {**user_tags, **FOOD_TAGS}

    # 双通道评分：merged_tags精确匹配(权重2) + 名称关键词匹配(权重1)
    scored_items = []
    match_details = {}
    for item in filtered_items:
        score = 0
        matches = []

        # 通道1：merged_tags精确匹配（权重2）
        if item in merged_tags:
            item_tags = merged_tags[item]
            for tag in prefer_tags:
                if tag in item_tags:
                    score += 2
                    if tag not in matches:
                        matches.append(tag)

        # 通道2：名称关键词匹配（权重1）
        for tag in prefer_tags:
            if tag_matches(tag, item):
                score += 1
                if tag not in matches:
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
        if goal_name:
            recommendation_text = f"根据你「{goal_name}」的目标，为 {school_name} 的你推荐：\n\n✅ {result}\n\n"
        else:
            recommendation_text = f"为 {school_name} 的你推荐：\n\n✅ {result}\n\n"
        if goal_name:
            details.append(f"• 目标: {goal_name}")
        if result in match_details:
            matched_tags = match_details[result]
            details.append(f"• 匹配营养需求: {', '.join(matched_tags)}")
        if filtered_reasons:
            details.append(f"• 已排除 {len(filtered_reasons)} 个不适合的菜品")
        recommendation_text += "\n".join(details) + "\n\n🍽️ 希望你用餐愉快！"
    else:
        if filtered_items:
            result = random.choice(filtered_items)
            if goal_name:
                recommendation_text = f"根据你「{goal_name}」的目标，为 {school_name} 的你推荐：\n\n✅ {result}\n\n"
            else:
                recommendation_text = f"为 {school_name} 的你推荐：\n\n✅ {result}\n\n"
            if goal_name:
                details.append(f"• 目标: {goal_name}")
            if filtered_reasons:
                details.append(f"• 已排除 {len(filtered_reasons)} 个不适合的菜品")
            if details:
                recommendation_text += "\n".join(details) + "\n\n"
            recommendation_text += "🍽️ 希望你用餐愉快！"
        else:
            if items:
                result = random.choice(items)
                recommendation_text = f"为 {school_name} 的你推荐：\n\n✅ {result}\n\n🍽️ 希望你用餐愉快！"
            else:
                return jsonify({"success": False, "message": "没有可用菜品"}), 400

    return jsonify({
        "success": True,
        "result": result,
        "recommendation": recommendation_text,
        "details": details,
        "goal": goal_name
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
        # 根据置信度返回不同提示文案
        conf = info["confidence"]
        if conf == "low":
            note = "⚠️ 该学校数据置信度较低，菜品列表可能不准确，建议核实后再保存"
        elif conf == "medium":
            note = "📋 数据来自公开文章整理，可能存在时效性偏差，建议快速浏览确认"
        else:
            note = "✅ 数据置信度高，来源可靠且经过时效性校验"
        return jsonify({
            "success": True,
            "school": school_name,
            "dishes": filtered_dishes,
            "source": "curated",
            "source_desc": info["source"],
            "confidence": conf,
            "note": note,
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


# ========== 菜品标签 API ==========
@app.route('/api/dish-tags/taxonomy', methods=['GET'])
def get_tag_taxonomy():
    """返回标签分类体系供前端渲染"""
    return jsonify({
        "success": True,
        "taxonomy": TAG_TAXONOMY,
        "all_tags": list(ALL_VALID_TAGS)
    })


@app.route('/api/dish-tags/save', methods=['POST'])
def save_dish_tags():
    """保存用户提交的菜品标签（合并模式）"""
    new_tags = request.json.get('tags', {})
    if not isinstance(new_tags, dict):
        return jsonify({"success": False, "message": "标签格式无效"}), 400

    # 验证：过滤无效标签
    cleaned = {}
    for dish, tags in new_tags.items():
        dish = dish.strip()
        if not dish or not isinstance(tags, list):
            continue
        valid = [t for t in tags if t in ALL_VALID_TAGS]
        if valid:
            cleaned[dish] = valid

    if not cleaned:
        return jsonify({"success": False, "message": "没有有效的标签"}), 400

    # 加载已有标签，合并，保存
    user_tags = load_user_dish_tags()
    user_tags.update(cleaned)

    if save_user_dish_tags(user_tags):
        return jsonify({
            "success": True,
            "message": f"已保存 {len(cleaned)} 道菜品的标签",
            "count": len(cleaned)
        })
    else:
        return jsonify({"success": False, "message": "保存失败"}), 500


@app.route('/api/dish-tags/all', methods=['GET'])
def get_all_dish_tags():
    """返回所有用户提交的菜品标签"""
    user_tags = load_user_dish_tags()
    return jsonify({
        "success": True,
        "tags": user_tags,
        "count": len(user_tags)
    })


# ========== 打卡用户认证 API ==========
@app.route('/api/meal-user/register', methods=['POST'])
def register_meal_user():
    """注册新的打卡用户"""
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "message": "昵称和密码不能为空"}), 400
    if len(username) > 12:
        return jsonify({"success": False, "message": "昵称最多12个字符"}), 400
    if len(password) < 4:
        return jsonify({"success": False, "message": "密码至少4位"}), 400

    users = load_meal_users()
    if username in users:
        return jsonify({"success": False, "message": "该昵称已被注册"}), 400

    pw_hash, salt = hash_password(password)
    users[username] = {
        "password_hash": pw_hash,
        "salt": salt,
        "created_at": datetime.datetime.now().isoformat(),
        "goal": ""
    }

    if save_meal_users(users):
        return jsonify({"success": True, "message": f"注册成功，欢迎 {username}！", "username": username})
    else:
        return jsonify({"success": False, "message": "保存失败"}), 500


@app.route('/api/meal-user/login', methods=['POST'])
def login_meal_user():
    """打卡用户登录"""
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "message": "请输入昵称和密码"}), 400

    users = load_meal_users()
    if username not in users:
        return jsonify({"success": False, "message": "用户不存在"}), 404

    user = users[username]
    if not verify_password(password, user.get('password_hash', ''), user.get('salt', '')):
        return jsonify({"success": False, "message": "密码错误"}), 401

    return jsonify({
        "success": True, 
        "message": f"欢迎回来，{username}！", 
        "username": username,
        "goal": user.get('goal', '')
    })


@app.route('/api/meal-user/check', methods=['GET'])
def check_meal_user():
    """检查用户名是否已存在"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"exists": False})
    users = load_meal_users()
    return jsonify({"exists": username in users})


@app.route('/api/meal-user/goal', methods=['GET'])
def get_user_goal():
    """获取用户目标"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"success": False, "message": "请先登录"}), 400
    users = load_meal_users()
    if username not in users:
        return jsonify({"success": False, "message": "用户不存在"}), 404
    return jsonify({
        "success": True,
        "goal": users[username].get('goal', '')
    })


@app.route('/api/meal-user/goal', methods=['PUT'])
def set_user_goal():
    """设置用户目标"""
    data = request.json or {}
    username = data.get('username', '').strip()
    goal = data.get('goal', '').strip()

    if not username:
        return jsonify({"success": False, "message": "请先登录"}), 400
    if goal not in ('cutting', 'bulking', 'healthy', ''):
        return jsonify({"success": False, "message": "无效目标"}), 400

    users = load_meal_users()
    if username not in users:
        return jsonify({"success": False, "message": "用户不存在"}), 404

    users[username]['goal'] = goal
    if save_meal_users(users):
        goal_names = {'cutting': '减脂期', 'bulking': '增肌期', 'healthy': '保持健康', '': '未设置'}
        return jsonify({"success": True, "message": f"目标已设为: {goal_names.get(goal, goal)}"})
    else:
        return jsonify({"success": False, "message": "保存失败"}), 500


# ========== 三餐打卡 API ==========
@app.route('/api/meal-log/save', methods=['POST'])
def save_meal_log():
    """保存某用户的某天某一餐记录"""
    data = request.json or {}
    username = data.get('username', '').strip()
    date_str = data.get('date', '').strip()
    meal = data.get('meal', '').strip()
    dishes = data.get('dishes', [])

    if not username:
        return jsonify({"success": False, "message": "请先输入昵称"}), 400
    if not date_str or meal not in ('breakfast', 'lunch', 'dinner'):
        return jsonify({"success": False, "message": "参数无效"}), 400
    if not isinstance(dishes, list):
        return jsonify({"success": False, "message": "菜品格式无效"}), 400

    cleaned = list(dict.fromkeys(d.strip() for d in dishes if d.strip()))

    logs = load_meal_logs()
    if username not in logs:
        logs[username] = {}
    if date_str not in logs[username]:
        logs[username][date_str] = {"breakfast": [], "lunch": [], "dinner": []}
    logs[username][date_str][meal] = cleaned

    if save_meal_logs(logs):
        return jsonify({
            "success": True,
            "message": f"已保存{meal}记录",
            "date": date_str,
            "meal": meal,
            "count": len(cleaned)
        })
    else:
        return jsonify({"success": False, "message": "保存失败"}), 500


@app.route('/api/meal-log/today', methods=['GET'])
def get_today_meal_log():
    """获取某用户今天的打卡状态"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"success": False, "message": "请先输入昵称"}), 400
    today = time.strftime("%Y-%m-%d")
    logs = load_meal_logs()
    user_logs = logs.get(username, {})
    today_data = user_logs.get(today, {"breakfast": [], "lunch": [], "dinner": []})
    return jsonify({
        "success": True,
        "date": today,
        "meals": today_data
    })


@app.route('/api/meal-log/weekly-report', methods=['GET'])
def get_weekly_report():
    """生成某用户过去7天的饮食报告（含目标指标和习惯洞察）"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"success": False, "message": "请先输入昵称"}), 400
    logs = load_meal_logs()
    user_logs = logs.get(username, {})
    today = datetime.date.today()

    # 获取用户目标
    users = load_meal_users()
    user_goal = users.get(username, {}).get('goal', '') if username in users else ''
    goal_names = {'cutting': '减脂期', 'bulking': '增肌期', 'healthy': '保持健康'}
    goal_name = goal_names.get(user_goal, '')

    user_tags = load_user_dish_tags()
    merged_tags = {**user_tags, **FOOD_TAGS}

    protein_tags_set = {"高蛋白", "蛋白质", "鸡蛋", "鸡肉", "牛肉", "鱼", "豆腐", "虾"}
    unhealthy_tags_set = {"油炸", "油爆", "干煸", "红烧", "糖醋", "高糖"}
    healthy_tags_set = {"清蒸", "凉拌", "清淡", "蔬菜", "高纤维"}

    days_checked_in = 0
    total_meals = 0
    total_dishes = 0
    dish_counter = {}
    category_counter = {}
    daily_summary = []
    meal_completion = {"breakfast": 0, "lunch": 0, "dinner": 0}

    # 每日目标指标（用于折线图）
    daily_goal_metric = []
    # 用于习惯洞察
    all_dishes_with_dates = []  # [(date_str, dish_name), ...]
    # 连续打卡天数（从今天往前数）
    consecutive_days = 0
    streak_broken = False

    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_data = user_logs.get(day_str, {"breakfast": [], "lunch": [], "dinner": []})

        day_meals = 0
        day_dish_count = 0
        day_protein = 0
        day_unhealthy = 0
        day_healthy = 0

        for meal_type in ("breakfast", "lunch", "dinner"):
            dishes = day_data.get(meal_type, [])
            if dishes:
                day_meals += 1
                meal_completion[meal_type] += 1
                for dish in dishes:
                    day_dish_count += 1
                    total_dishes += 1
                    dish_counter[dish] = dish_counter.get(dish, 0) + 1
                    all_dishes_with_dates.append((day_str, dish))
                    if dish in merged_tags:
                        tags = merged_tags[dish]
                        for tag in tags:
                            category_counter[tag] = category_counter.get(tag, 0) + 1
                        if any(t in tags for t in protein_tags_set):
                            day_protein += 1
                        if any(t in tags for t in unhealthy_tags_set):
                            day_unhealthy += 1
                        if any(t in tags for t in healthy_tags_set):
                            day_healthy += 1
                    # 名称关键词兜底
                    if any(kw in dish for kw in ["鸡胸", "牛肉", "鱼", "鸡蛋", "豆腐", "虾"]):
                        day_protein += 1
                    if any(kw in dish for kw in ["炸鸡", "红烧肉", "蛋糕", "薯条"]):
                        day_unhealthy += 1

        if day_meals > 0:
            days_checked_in += 1
        total_meals += day_meals

        # 计算每日目标指标
        if user_goal == 'cutting':
            metric_val = day_unhealthy  # 减脂期：不健康菜品数（越少越好）
        elif user_goal == 'bulking':
            metric_val = day_protein  # 增肌期：高蛋白菜品数（越多越好）
        else:
            metric_val = day_meals  # 保持健康：打卡餐数
        daily_goal_metric.append(metric_val)

        daily_summary.append({
            "date": day_str,
            "weekday": ["一", "二", "三", "四", "五", "六", "日"][day.weekday()],
            "meals": day_meals,
            "dish_count": day_dish_count
        })

    # 重新计算连续打卡天数（从今天往前连续）
    consecutive_days = 0
    for i in range(0, 7):
        day = today - datetime.timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_data = user_logs.get(day_str, {"breakfast": [], "lunch": [], "dinner": []})
        has_meals = any(len(day_data.get(m, [])) > 0 for m in ("breakfast", "lunch", "dinner"))
        if has_meals:
            consecutive_days += 1
        else:
            break

    sorted_dishes = sorted(dish_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    top_dishes = [{"name": name, "count": count} for name, count in sorted_dishes]

    sorted_cats = sorted(category_counter.items(), key=lambda x: x[1], reverse=True)[:8]
    category_distribution = {cat: count for cat, count in sorted_cats}

    # 习惯洞察
    insights = []
    if consecutive_days >= 3:
        insights.append(f"你已经连续打卡 {consecutive_days} 天，继续保持！")
    if top_dishes and top_dishes[0]["count"] >= 3:
        insights.append(f"「{top_dishes[0]['name']}」是你本周最爱，吃了 {top_dishes[0]['count']} 次")

    # 检测连续多天同一菜品
    from collections import defaultdict
    dish_dates = defaultdict(list)
    for date_str, dish in all_dishes_with_dates:
        dish_dates[dish].append(date_str)
    for dish, dates in dish_dates.items():
        unique_dates = sorted(set(dates))
        if len(unique_dates) >= 3:
            date_objs = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in unique_dates]
            consec = 1
            max_consec = 1
            for j in range(1, len(date_objs)):
                if (date_objs[j] - date_objs[j-1]).days == 1:
                    consec += 1
                    max_consec = max(max_consec, consec)
                else:
                    consec = 1
            if max_consec >= 3:
                insights.append(f"「{dish}」连续 {max_consec} 天都在吃，建议换换口味")
                break  # 只提示一条

    if not insights:
        if days_checked_in == 0:
            insights.append("本周还没有打卡记录，从今天开始记录吧！")
        elif days_checked_in < 3:
            insights.append(f"本周打卡 {days_checked_in} 天，坚持每天记录会更有参考价值")

    return jsonify({
        "success": True,
        "username": username,
        "goal": goal_name,
        "days_checked_in": days_checked_in,
        "total_meals": total_meals,
        "total_dishes": total_dishes,
        "top_dishes": top_dishes,
        "category_distribution": category_distribution,
        "daily_summary": daily_summary,
        "daily_goal_metric": daily_goal_metric,
        "meal_completion": meal_completion,
        "consecutive_days": consecutive_days,
        "insights": insights[:3]  # 最多3条
    })


@app.route('/api/meal-log/daily-briefing', methods=['GET'])
def daily_briefing():
    """今日饮食简报"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"success": False, "message": "请先登录"}), 400

    logs = load_meal_logs()
    user_logs = logs.get(username, {})
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    today_data = user_logs.get(today_str, {"breakfast": [], "lunch": [], "dinner": []})

    # 获取用户目标
    users = load_meal_users()
    user_goal = users.get(username, {}).get('goal', '') if username in users else ''
    goal_names = {'cutting': '减脂期', 'bulking': '增肌期', 'healthy': '保持健康'}
    goal_name = goal_names.get(user_goal, '')

    # 统计各餐
    meal_counts = {}
    all_dishes = []
    for meal_type in ("breakfast", "lunch", "dinner"):
        dishes = today_data.get(meal_type, [])
        meal_counts[meal_type] = len(dishes)
        all_dishes.extend(dishes)

    total_dishes = len(all_dishes)
    meals_logged = sum(1 for v in meal_counts.values() if v > 0)

    if total_dishes == 0:
        return jsonify({
            "success": True,
            "total_dishes": 0,
            "meals_logged": 0,
            "message": "今天还没有打卡记录，快去记录今天吃了什么吧！",
            "goal": goal_name
        })

    # 用 FOOD_TAGS 分析烹饪方式
    user_tags = load_user_dish_tags()
    merged_tags = {**user_tags, **FOOD_TAGS}

    cooking_methods = {}  # 烹饪方式统计
    protein_count = 0  # 高蛋白菜品数
    unhealthy_count = 0  # 不健康菜品数（油炸等）
    vegetable_count = 0  # 蔬菜菜品数

    protein_tags = ["高蛋白", "蛋白质", "鸡蛋", "鸡肉", "牛肉", "鱼", "豆腐", "虾"]
    unhealthy_tags = ["油炸", "油爆", "干煸", "红烧", "糖醋", "高糖"]
    vegetable_tags = ["蔬菜", "清淡", "凉拌", "清蒸", "高纤维"]

    for dish in all_dishes:
        tags = merged_tags.get(dish, [])
        # 烹饪方式统计
        for tag in tags:
            if tag in ["油炸", "清蒸", "红烧", "凉拌", "炒", "烤", "煮", "蒸", "煎", "糖醋", "油爆", "干煸"]:
                cooking_methods[tag] = cooking_methods.get(tag, 0) + 1
        # 分类统计
        if any(t in tags for t in protein_tags) or any(t in dish for t in ["鸡胸", "牛肉", "鱼", "鸡蛋", "豆腐", "虾"]):
            protein_count += 1
        if any(t in tags for t in unhealthy_tags) or any(t in dish for t in ["炸鸡", "红烧肉", "蛋糕", "薯条"]):
            unhealthy_count += 1
        if any(t in tags for t in vegetable_tags) or any(t in dish for t in ["西兰花", "青菜", "黄瓜", "番茄"]):
            vegetable_count += 1

    # 根据目标生成评价
    score = 70  # 默认分数
    tip = ""
    details = []

    if user_goal == 'cutting':
        # 减脂期评价
        if unhealthy_count > 0:
            score -= unhealthy_count * 10
            tip = f"今天有 {unhealthy_count} 道高油菜品，建议明天换成清蒸或凉拌的做法"
        if vegetable_count > 2:
            score += 10
            details.append(f"蔬菜摄入 {vegetable_count} 次，继续保持")
        if protein_count > 0:
            score += 5
            details.append(f"蛋白质摄入 {protein_count} 次")
        if not tip:
            if unhealthy_count == 0:
                tip = "今天饮食很清淡，减脂节奏把握得不错！"
            else:
                tip = "注意控制油脂摄入，优先选择清蒸、凉拌类菜品"
    elif user_goal == 'bulking':
        # 增肌期评价
        if protein_count >= 3:
            score += 15
            tip = f"蛋白质摄入 {protein_count} 次，增肌营养跟上了！"
        elif protein_count >= 1:
            score += 5
            tip = f"蛋白质摄入 {protein_count} 次，还可以多吃点鸡蛋和鸡胸肉"
        else:
            score -= 10
            tip = "今天蛋白质摄入不足，建议加一份鸡蛋或豆腐"
        if total_dishes >= 4:
            score += 5
            details.append(f"总摄入 {total_dishes} 道菜品，热量充足")
    else:
        # 保持健康 / 未设目标
        if meals_logged >= 3:
            score += 10
            details.append("三餐都有记录，饮食规律")
        elif meals_logged == 0:
            score -= 10
        if vegetable_count > 0 and protein_count > 0:
            score += 10
            tip = "荤素搭配不错，继续保持！"
        elif total_dishes > 0:
            tip = "记得荤素搭配，每餐都有蔬菜和蛋白质最理想"
        if unhealthy_count > 2:
            score -= unhealthy_count * 5
            details.append(f"高油菜品 {unhealthy_count} 次，稍微多了点")

    score = max(0, min(100, score))

    return jsonify({
        "success": True,
        "total_dishes": total_dishes,
        "meals_logged": meals_logged,
        "meal_counts": meal_counts,
        "protein_count": protein_count,
        "unhealthy_count": unhealthy_count,
        "vegetable_count": vegetable_count,
        "cooking_methods": cooking_methods,
        "score": score,
        "tip": tip,
        "details": details,
        "goal": goal_name
    })


@app.route('/api/meal-log/users', methods=['GET'])
def get_meal_log_users():
    """返回所有有打卡记录的用户名列表"""
    logs = load_meal_logs()
    users = [name for name in logs.keys() if isinstance(logs[name], dict)]
    return jsonify({
        "success": True,
        "users": sorted(users),
        "total": len(users)
    })


@app.route('/api/status', methods=['GET'])
def system_status():
    """系统状态诊断"""
    status = {
        "supabase_connected": supabase_client is not None,
        "supabase_url": SUPABASE_URL[:30] + "..." if SUPABASE_URL else "(未设置)",
        "storage_backend": "supabase" if supabase_client else "local_json (临时!)",
    }
    # 检查本地数据文件
    import os
    for name, path in [("cafeteria_data", DATA_FILE), ("meal_logs", MEAL_LOGS_FILE),
                        ("meal_users", MEAL_USERS_FILE), ("dish_tags", USER_TAGS_FILE)]:
        status[f"{name}_exists"] = os.path.exists(path) if path else False
    # 如果 Supabase 可用，查询数据量
    if supabase_client:
        try:
            r1 = supabase_client.table('school_menus').select('school_name', count='exact').execute()
            status["supabase_schools"] = r1.count
        except:
            status["supabase_schools"] = -1
        try:
            r2 = supabase_client.table('meal_users').select('username', count='exact').execute()
            status["supabase_users"] = r2.count
        except:
            status["supabase_users"] = -1
        try:
            r3 = supabase_client.table('meal_logs').select('username', count='exact').execute()
            status["supabase_log_rows"] = r3.count
        except:
            status["supabase_log_rows"] = -1
    return jsonify(status)


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
