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

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_cors import CORS
import json
import os
import random
import re
import time
import datetime
import hashlib
import secrets

# ========== 启动诊断 ==========
import inspect as _inspect
_deploy_file = _inspect.getfile(_inspect.currentframe())
_deploy_lines = len(open(_deploy_file, 'r', encoding='utf-8').readlines())
print("[DEPLOY DIAG] file=" + _deploy_file + " lines=" + str(_deploy_lines) + " deploy_id=v17-lb-supabase")

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
        print(f"⚠️ Supabase 连接失败，将使用本地JSON存储: {e}")

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
        print("OK: Supabase migration (goal column)")
    except Exception as e:
        print(f"WARN: Supabase migration skipped (goal): {e}")
    
    try:
        # 给 meal_users 表添加 role 列（如果不存在）
        supabase_client.rpc('exec_sql', {
            'sql': "ALTER TABLE meal_users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';"
        }).execute()
        print("OK: Supabase migration (role column)")
    except Exception as e:
        print(f"WARN: Supabase migration skipped (role): {e}")

    # 创建排行榜分数表
    try:
        supabase_client.rpc('exec_sql', {
            'sql': """CREATE TABLE IF NOT EXISTS leaderboard_scores (
                username TEXT NOT NULL,
                date TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                school TEXT DEFAULT '',
                meals_count INTEGER DEFAULT 0,
                submitted_at TEXT DEFAULT '',
                PRIMARY KEY (username, date)
            );"""
        }).execute()
        print("OK: leaderboard_scores table")
    except Exception as e:
        print(f"WARN: leaderboard_scores table creation: {e}")

    # 创建排行榜隐私表
    try:
        supabase_client.rpc('exec_sql', {
            'sql': """CREATE TABLE IF NOT EXISTS leaderboard_privacy (
                username TEXT PRIMARY KEY,
                opted_in BOOLEAN DEFAULT true
            );"""
        }).execute()
        print("OK: leaderboard_privacy table")
    except Exception as e:
        print(f"WARN: leaderboard_privacy table creation: {e}")

    # 设置 RLS 策略
    for tbl in ['leaderboard_scores', 'leaderboard_privacy']:
        try:
            supabase_client.rpc('exec_sql', {
                'sql': f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;"
            }).execute()
        except:
            pass
        try:
            supabase_client.rpc('exec_sql', {
                'sql': f"""DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_select_{tbl}' AND tablename = '{tbl}') THEN
                        CREATE POLICY "anon_select_{tbl}" ON {tbl} FOR SELECT TO anon USING (true);
                    END IF;
                END $$;"""
            }).execute()
        except:
            pass
        try:
            supabase_client.rpc('exec_sql', {
                'sql': f"""DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'anon_insert_{tbl}' AND tablename = '{tbl}') THEN
                        CREATE POLICY "anon_insert_{tbl}" ON {tbl} FOR INSERT TO anon WITH CHECK (true);
                    END IF;
                END $$;"""
            }).execute()
        except:
            pass

if SUPABASE_URL and SUPABASE_ANON_KEY:
    migrate_supabase()


# ========== 管理员验证（开发者密码） ==========
def is_admin(username=None):
    """检查是否已通过开发者密码验证（唯一管理员手段）"""
    return session.get('dev_verified', False)


# ========== 基础路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'chimei', 'web_app', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'chimei', 'web_app', 'static'))
CORS(app)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'chimei-dev-2026')

# ========== 配置 ==========
DATA_FILE = os.path.join(BASE_DIR, 'chimei', 'cafeteria_data.json')
USER_TAGS_FILE = os.path.join(BASE_DIR, 'chimei', 'user_dish_tags.json')
MEAL_LOGS_FILE = os.path.join(BASE_DIR, 'chimei', 'meal_logs.json')
MEAL_USERS_FILE = os.path.join(BASE_DIR, 'chimei', 'meal_users.json')
DEV_CONFIG_FILE = os.path.join(BASE_DIR, 'chimei', 'dev_config.json')
VERSION_FILE = os.path.join(BASE_DIR, 'chimei', 'version.json')
LEADERBOARD_FILE = os.path.join(BASE_DIR, 'chimei', 'leaderboard_scores.json')
LEADERBOARD_PRIVACY_FILE = os.path.join(BASE_DIR, 'chimei', 'leaderboard_privacy.json')

# 开发者模式默认配置
DEFAULT_DEV_CONFIG = {
    "password": "chimeifj",
    "security_question": "创始人的外号",
    "security_answer": "yb"
}

def load_dev_config():
    """加载开发者模式配置"""
    if os.path.exists(DEV_CONFIG_FILE):
        try:
            with open(DEV_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return dict(DEFAULT_DEV_CONFIG)

def save_dev_config(config):
    """保存开发者模式配置"""
    try:
        with open(DEV_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存开发者配置失败: {e}")
        return False

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
            # 如"面"在"牛肉面"中是菜名核心，应该匹配
            if tag in ('面', '粥', '汤', '蛋', '鱼', '肉', '鸡', '鸭', '牛', '羊', '猪', '虾', '蟹', '姜', '葱'):
                # 这些标签在菜名末尾时应该匹配（如"牛肉面"的"面"）
                if after_idx >= len(item):
                    return True
                # 这些标签在菜名开头时也应该匹配（如"鱼香肉丝"的"鱼"不应该匹配"鱼"标签，因为"鱼香"是调味）
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
    "厦门大学": {
        "dishes": [
            "沙茶面", "海蛎煎", "铁板炒面", "辣子鸡", "糖醋小排", "地三鲜", "金汤酸菜鱼", "鸡丝凉面",
            "麻婆豆腐", "香嘴牛肉", "鱼香肉丝", "蚂蚁上树", "脆皮鱼条", "炒牛河", "刀削面", "金汤巴沙鱼",
            "咖喱肉片", "水煮肉片", "芋泥香酥鸭", "厦门炒面线", "厦门封猪脚", "港式茶点", "广式烧腊",
            "同安封肉套饭", "香芋猪蹄套饭", "铁板炒饭", "布丁口袋包", "酸奶菠萝包", "乳酪方包", "毛毛虫面包",
            "米饭", "馒头", "花卷", "面条",
        ],
        "source": "多篇厦门大学食堂美食攻略文章综合整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "数据来自多篇学生美食攻略，含厦大特色菜品，建议用户核实"
    },
    "华侨大学": {
        "dishes": [
            "肠粉", "糖醋排骨", "麻辣烫", "牛排", "牛丸汤", "白灼海水虾", "泉州姜母鸭", "红烧肉", "宫保鸡丁",
            "麻婆豆腐", "西红柿炒蛋", "回锅肉", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "华侨大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含泉州/厦门校区特色菜品，建议用户核实"
    },
    "福州大学": {
        "dishes": [
            "海鲜锅边糊", "猪肉炖粉条", "章鱼小丸子", "鸡汤肉燕", "无骨鱼柳滑蛋饭", "酸菜鱼", "荔枝肉", "鸡爪",
            "川香辣子鸡", "红烧牛肉面", "回锅肉肉肠饭", "小份菜", "烤味", "红烧肉", "宫保鸡丁", "麻婆豆腐",
            "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福州大学食堂美食推荐文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含福大特色菜品（锅边糊、肉燕、荔枝肉等），建议用户核实"
    },
    "福建理工大学": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建农林大学": {
        "dishes": [
            "酸菜牛肉", "香辣鱼块", "沙茶面", "土豆烧鸡烩面", "鸭腿盖饭", "十元快餐", "鸡胸肉", "热狗",
            "水果捞", "纸火锅", "干锅饭", "芝士焗饭", "炖肉", "烫菜", "扁食", "肉丸面", "砂锅", "鱼肉套餐",
            "椒麻鸡", "牛肉汤", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福建农林大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含农林大特色菜品，建议用户核实"
    },
    "集美大学": {
        "dishes": [
            "番茄鸡蛋面", "拌粿条", "同安封肉套饭", "香芋猪蹄套饭", "铁板炒饭", "布丁口袋包", "酸奶菠萝包",
            "乳酪方包", "毛毛虫面包", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "集美大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含集美大学特色菜品，建议用户核实"
    },
    "福建医科大学": {
        "dishes": [
            "打卤面", "特色汤面", "牛肉面", "瓦罐汤", "刀削面", "茄子粉丝", "炸酱面", "面线糊", "红烧肉",
            "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福建医科大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含医科大特色面食，建议用户核实"
    },
    "福建中医药大学": {
        "dishes": [
            "早餐炒菜", "糕点", "佛跳墙", "鱼粉", "炖菜", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷",
            "面条",
        ],
        "source": "福建中医药大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含佛跳墙等特色菜品，建议用户核实"
    },
    "福建师范大学": {
        "dishes": [
            "蟹柳炒米粉", "牛肉粉丝泡馍", "兰州拉面", "福鼎肉片", "沙茶面", "生煎包", "烫菜", "牛排", "拉面",
            "小笼包", "五元套餐", "红烧肉", "宫保鸡丁", "麻婆豆腐", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福建师范大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含师大特色菜品，建议用户核实"
    },
    "闽江大学": {
        "dishes": [
            "快餐", "沙县小吃", "韩式料理", "意式料理", "回转火锅", "红烧肉", "宫保鸡丁", "麻婆豆腐", "米饭",
            "馒头", "花卷", "面条",
        ],
        "source": "闽江大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含多国料理特色，建议用户核实"
    },
    "武夷学院": {
        "dishes": [
            "五花肉烧黑笋干", "武夷熏鹅", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "武夷学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含武夷山地方特色菜品（熏鹅、黑笋干），建议用户核实"
    },
    "宁德师范学院": {
        "dishes": [
            "炒面", "炒米粉", "瓦罐汤", "过桥米线", "排骨米线", "水饺", "牛肉面", "凉拌河粉", "鸭腿",
            "麻辣香锅", "杀猪粉", "麻辣烫", "菜配饭", "烤鸭饭", "煎蛋", "番茄鸡蛋汤", "鸡蛋凉面", "黄焖鸡",
            "意大利面", "手枪腿意面", "牛肉面", "鸡腿面", "拌粉", "卤味", "老鸭粉丝汤", "套餐饭", "糖醋排骨饭",
            "烤肉饭", "沙拉烤肉饭", "螺蛳粉", "渔粉", "紫米饭", "杂粮煎饼", "无骨炸鸡", "鸡公煲", "排骨粉",
            "福鼎肉片", "饭团", "肉粽", "鸡蛋仔", "冰粉", "双皮奶", "绿豆汤", "四果汤", "白桃水仙", "米饭",
            "馒头", "花卷", "面条", "拉面",
        ],
        "source": "多篇宁德师范学院食堂美食攻略文章综合整理",
        "source_url": "https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt_4416254505955582617",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "数据来自多篇学生美食攻略，按食堂/学生街分类整理，已新增福鼎肉片，建议用户核实具体档口是否仍在营业"
    },
    "泉州师范学院": {
        "dishes": [
            "烧味", "掉渣饼", "燕麦粥", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "泉州师范学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含泉师特色菜品，建议用户核实"
    },
    "闽南师范大学": {
        "dishes": [
            "啤酒鸭", "煎饼果子", "拉面", "刀削面", "北方酱骨面", "衡阳鱼粉", "花甲粉", "麻辣烫", "瓦罐汤",
            "东北特色大水饺", "凉皮", "拌饭", "卤面", "小面", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷",
            "面条",
        ],
        "source": "闽南师范大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含多地风味菜品，建议用户核实"
    },
    "厦门理工学院": {
        "dishes": [
            "茶餐厅菜品", "香锅", "鸡腿", "豆浆", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "厦门理工学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含茶餐厅特色，建议用户核实"
    },
    "三明学院": {
        "dishes": [
            "葱油拌面", "快餐", "自助快餐", "沙县小吃", "黄焖鸡", "大面条", "掉渣饼", "烤肉拌饭", "麻辣香锅",
            "牛柳饭", "烧茄子", "蒸蛋", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "三明学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含沙县小吃等特色，建议用户核实"
    },
    "龙岩学院": {
        "dishes": [
            "客家牛肉丸", "瘦肉面", "拌面", "烧烤", "烫菜", "炒饭", "红烧肉", "宫保鸡丁", "米饭", "馒头",
            "花卷", "面条",
        ],
        "source": "龙岩学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含客家特色菜品（牛肉丸等），建议用户核实"
    },
    "福建商学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建警察学院": {
        "dishes": [
            "鸡排", "小龙虾", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福建警察学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含警院特色菜品，建议用户核实"
    },
    "莆田学院": {
        "dishes": [
            "莆田卤面", "鱼粉", "牛肉饭", "麻辣香锅", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "莆田学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含莆田特色卤面，建议用户核实"
    },
    "厦门医学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建江夏学院": {
        "dishes": [
            "牛排", "酸辣粉", "烫菜", "水煮", "水果捞", "汉堡", "红烧肉", "宫保鸡丁", "米饭", "馒头",
            "花卷", "面条",
        ],
        "source": "福建江夏学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含江夏特色菜品，建议用户核实"
    },
    "福建技术师范学院": {
        "dishes": [
            "炸鸡", "卤面", "特色汤面", "烫菜", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福建技术师范学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含福清特色卤面，建议用户核实"
    },
    "黎明职业大学": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福州职业技术大学": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "仰恩大学": {
        "dishes": [
            "烤冷面", "麻辣香锅", "枪腿饭", "泡菜焗饭", "寿司", "福鼎肉片", "炒粉", "炒鸭饭", "铁板烧",
            "韭菜盒子", "麻辣烫", "烧烤", "牛肉", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "仰恩大学食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含仰恩特色菜品，建议用户核实"
    },
    "厦门华厦学院": {
        "dishes": [
            "意大利面", "炒面", "拔丝地瓜", "甜汤", "奶茶", "麻辣香锅", "蛋包饭", "凉皮", "砂锅",
            "过桥米线", "沙茶面", "山城小面", "洪城拌粉", "三秦凉皮", "牛腩酸菜面", "花甲米粉", "螺蛳粉",
            "汉堡炸鸡", "红烧肉", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "厦门华厦学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含多地风味菜品，建议用户核实"
    },
    "闽南理工学院": {
        "dishes": [
            "麻辣香锅", "水煮鸡肉", "套餐饭", "烫菜", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "闽南理工学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含理工特色菜品，建议用户核实"
    },
    "泉州职业技术大学": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "闽南科技学院": {
        "dishes": [
            "馄饨", "小笼包", "手抓饼", "福鼎肉片", "烤鸭饭", "炒面", "炸酱面", "麻辣香锅", "杂粮煎饼",
            "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "闽南科技学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含科技特色菜品，建议用户核实"
    },
    "福州工商学院": {
        "dishes": [
            "煎饼果子", "鸡蛋饼", "年糕火锅", "日料", "奶茶", "烧烤", "红烧肉", "宫保鸡丁", "米饭", "馒头",
            "花卷", "面条",
        ],
        "source": "福州工商学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含工商特色菜品，建议用户核实"
    },
    "厦门工学院": {
        "dishes": [
            "套餐", "五谷鱼粉", "盖浇饭", "麻辣香锅", "肠粉", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷",
            "面条",
        ],
        "source": "厦门工学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含工学院特色菜品，建议用户核实"
    },
    "阳光学院": {
        "dishes": [
            "牛排意面", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "阳光学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含阳光特色菜品，建议用户核实"
    },
    "厦门大学嘉庚学院": {
        "dishes": [
            "大盘鸡拉面", "手撕鸡拌面", "陈家酸汤鱼", "一口天鸡排", "汉堡", "薯条", "鸡腿", "炖汤", "私房面",
            "刀削面", "烩面", "小面", "水饺", "肉片", "担担面", "红烧肉", "宫保鸡丁", "米饭", "馒头",
            "花卷", "面条",
        ],
        "source": "厦门大学嘉庚学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含嘉庚特色菜品，建议用户核实"
    },
    "福州大学至诚学院": {
        "dishes": [
            "U米良品", "古法蒸制", "陈家生煎", "港式烧腊", "飘香小炒", "拉面", "客家菜", "瓦罐", "馄饨",
            "鸭面", "炒面粉", "粥", "饼", "筒骨饭", "鸡公煲", "红烧肉", "宫保鸡丁", "米饭", "馒头",
            "花卷", "面条",
        ],
        "source": "福州大学至诚学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含至诚特色档口菜品，建议用户核实"
    },
    "集美大学诚毅学院": {
        "dishes": [
            "炸鸡排", "鸡腿", "炒饭", "炒面", "拉面", "水饺", "杂粮饼", "自助砂锅", "蛋包饭", "披萨",
            "牛排", "炸酱面", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "集美大学诚毅学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含诚毅特色菜品，建议用户核实"
    },
    "福建师范大学协和学院": {
        "dishes": [
            "沙茶面", "兰州拉面", "炸鸡汉堡", "麻辣烫", "过桥米线", "沙县小吃", "铁板牛肉", "烫菜", "特色汤面",
            "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福建师范大学协和学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含协和特色菜品，建议用户核实"
    },
    "福州外语外贸学院": {
        "dishes": [
            "牛排", "披萨", "意面", "水煮活鱼", "肉片", "烧烤", "韩国料理", "红烧肉", "宫保鸡丁", "米饭",
            "馒头", "花卷", "面条",
        ],
        "source": "福州外语外贸学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含多国料理特色，建议用户核实"
    },
    "泉州信息工程学院": {
        "dishes": [
            "麻辣香锅", "牛肉饭", "烤肉", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "泉州信息工程学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含信工特色菜品，建议用户核实"
    },
    "福州理工学院": {
        "dishes": [
            "五谷鱼粉", "港式扒饭", "港式汤煲", "小火锅", "沙茶面", "麻辣烫", "生煎包", "羊肉串", "瓦罐汤",
            "狗不理包子", "肉夹馍", "凉皮", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福州理工学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含多地风味菜品，建议用户核实"
    },
    "福建农林大学金山学院": {
        "dishes": [
            "盖浇面", "番茄肥牛", "盖浇刀削面", "红烧肉", "宫保鸡丁", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福建农林大学金山学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含金山学院特色盖浇面，建议用户核实"
    },
    "福建福耀科技大学": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "新建校，基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建船政交通职业学院": {
        "dishes": [
            "烫菜", "红烧肉", "宫保鸡丁", "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝",
            "回锅肉", "米饭", "馒头", "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "漳州职业技术学院": {
        "dishes": [
            "麻辣烫", "红烧肉", "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭",
            "馒头", "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "闽西职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建林业职业技术学院": {
        "dishes": [
            "咖啡奶茶", "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头",
            "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建信息职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建水利电力职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建电力职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门海洋职业技术学院": {
        "dishes": [
            "海鲜类", "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头",
            "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，含海鲜特色，建议用户重点核实"
    },
    "福建农业职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建卫生职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州医学高等专科学校": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "闽北职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州经贸职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "湄洲湾职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建生物工程职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建艺术职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建幼儿师范高等专科学校": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门城市职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州工艺美术职业学院": {
        "dishes": [
            "特色饭", "面", "粉", "饼", "精致小菜", "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，含工艺美术特色，建议用户重点核实"
    },
    "三明医学科技职业学院": {
        "dishes": [
            "烤鱼", "水煮", "螺蛳粉", "奶茶", "果汁", "四果汤", "红烧肉", "宫保鸡丁", "麻婆豆腐",
            "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "宁德职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建体育职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "漳州城市职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "漳州卫生职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州幼儿师范高等专科学校": {
        "dishes": [
            "川菜", "鲁菜", "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭",
            "馒头", "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，含川菜鲁菜风味，建议用户重点核实"
    },
    "闽江师范高等专科学校": {
        "dishes": [
            "蛋花汤", "海带汤", "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭",
            "馒头", "花卷", "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "集美工业职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福建华南女子职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福州英华职业学院": {
        "dishes": [
            "炒饭", "炒米粉", "炒河粉", "炒面", "荔枝肉", "烧鸭", "辣子鸡", "卤牛肉", "清蒸鱼", "炒三鲜",
            "炒青蔬", "米饭", "馒头", "花卷", "面条",
        ],
        "source": "福州英华职业学院食堂美食介绍文章",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "medium",
        "note": "含英华特色菜品，建议用户核实"
    },
    "泉州纺织服装职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州华光职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福州黎明职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门演艺职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门华天涉外职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福州科技职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福州软件职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门兴才职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门软件职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门南洋职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门东海职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "漳州科技职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "漳州理工职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "武夷山职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州海洋职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州轻工职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "厦门安防科技职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "泉州工程职业技术学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
    },
    "福州墨尔本理工职业学院": {
        "dishes": [
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "酸辣土豆丝", "回锅肉", "米饭", "馒头", "花卷",
            "面条", "炒面", "炒饭",
        ],
        "source": "中国高校食堂常见菜品整理",
        "source_url": "",
        "last_updated": "2026-06-25",
        "confidence": "low",
        "note": "基于高校食堂常见菜品整理，建议用户重点核实"
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
    """保存所有学校数据（JSON 保底 + Supabase 同步）"""
    json_ok = False
    supabase_ok = False

    # 1. 始终写入 JSON 文件作为保底（防止 Supabase 写入失败丢数据）
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        json_ok = True
    except Exception as e:
        print(f"[save_all_data] JSON 保存失败: {e}")

    # 2. 尝试同步到 Supabase
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
                resp = supabase_client.table('school_menus').upsert(rows, on_conflict='school_name').execute()
                supabase_ok = True
                print(f"[save_all_data] Supabase 同步成功，{len(rows)} 所学校")
        except Exception as e:
            print(f"[save_all_data] Supabase 同步失败: {e}")

    if json_ok:
        return True
    return supabase_ok


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
    """返回所有学校的已保存菜单（食堂图鉴）"""
    db_data = load_all_data()
    schools = {}
    for name, info in db_data.items():
        menu = info.get("menu", "") if isinstance(info, dict) else str(info)
        items = [item.strip() for item in menu.split("\n") if item.strip()]
        if items:
            last_modified = info.get("last_modified", "") if isinstance(info, dict) else ""
            schools[name] = {
                "dishes": items,
                "source": f"云端菜单（{last_modified}）" if last_modified else "云端菜单",
                "confidence": "high",
                "dish_count": len(items)
            }
    # 如果数据库为空，回退到精选数据库
    if not schools:
        schools = CURATED_DATABASE
    return jsonify({
        "success": True,
        "schools": schools,
        "count": len(schools)
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
    """保存指定学校的菜单（优先直接更新 Supabase 单行，失败则全量保存）"""
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    menu = request.json.get('menu', '')
    items = [item.strip() for item in menu.replace(",", "\n").split("\n") if item.strip()]
    formatted_menu = "\n".join(items)
    now = time.strftime("%Y-%m-%d %H:%M")

    # 优先尝试直接更新 Supabase 单行（高效且可靠）
    supabase_ok = False
    if supabase_client:
        try:
            supabase_client.table('school_menus').upsert({
                "school_name": school_name,
                "menu": formatted_menu,
                "last_modified": now
            }, on_conflict='school_name').execute()
            supabase_ok = True
            print(f"[save_menu] {school_name} 菜单已同步到 Supabase ({len(items)} 项)")
        except Exception as e:
            print(f"[save_menu] Supabase 单行更新失败: {e}")

    # 同时写入 JSON 保底 + 更新内存数据
    data = load_all_data()
    data[school_name] = {
        "menu": formatted_menu,
        "last_modified": now
    }
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_menu] JSON 保存失败: {e}")

    storage_info = "云端+本地" if supabase_ok else "仅本地（云端同步失败）"
    return jsonify({
        "success": True,
        "message": f"保存成功（{storage_info}）",
        "menu": formatted_menu,
        "count": len(items),
        "cloud_synced": supabase_ok
    })


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
    if not items:
        return jsonify({"success": False, "message": "没有可用菜品"}), 400
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
    if not items:
        return jsonify({"success": False, "message": "没有可用菜品"}), 400

    # 排除已推荐过的菜品
    if exclude:
        items = [item for item in items if item not in exclude]
        if not items:
            # 全部排除完了，重置为全部菜品
            items = [item.strip() for item in menu.split("\n") if item.strip()]

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
    """获取指定学校的菜品数据（优先返回用户已保存的菜单）"""
    data = request.json or {}
    school_name = data.get('school_name', '').strip()
    source = data.get('source', None)

    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400

    # 优先从数据库读取用户已保存的菜单
    db_data = load_all_data()
    if school_name in db_data:
        school_info = db_data[school_name]
        menu = school_info.get("menu", "") if isinstance(school_info, dict) else str(school_info)
        items = [item.strip() for item in menu.split("\n") if item.strip()]
        if items:
            last_modified = school_info.get("last_modified", "") if isinstance(school_info, dict) else ""
            return jsonify({
                "success": True,
                "school": school_name,
                "dishes": items,
                "source": "saved",
                "source_desc": f"云端菜单（{last_modified}）" if last_modified else "云端菜单",
                "confidence": "high",
                "note": f"✅ 已加载「{school_name}」的云端菜单，共 {len(items)} 道菜品",
                "dish_count": len(items)
            })

    # 数据库没有，回退到精选数据库
    if school_name in CURATED_DATABASE:
        info = CURATED_DATABASE[school_name]
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
            "dishes": info["dishes"],
            "source": "curated",
            "source_desc": info["source"],
            "confidence": conf,
            "note": note,
            "dish_count": len(info["dishes"])
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


@app.route('/api/dish-tags/<dish_name>', methods=['GET'])
def get_dish_tags(dish_name):
    """获取指定菜品的已有标签"""
    user_tags = load_user_dish_tags()
    tags = user_tags.get(dish_name, [])
    # 也检查内置 FOOD_TAGS
    if not tags and dish_name in FOOD_TAGS:
        tags = FOOD_TAGS[dish_name]
    return jsonify({
        "success": True,
        "dish_name": dish_name,
        "tags": tags
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
    # 检查是否为预设管理员
    role = 'user'
    users[username] = {
        "password_hash": pw_hash,
        "salt": salt,
        "created_at": datetime.datetime.now().isoformat(),
        "goal": "",
        "role": role
    }

    if save_meal_users(users):
        return jsonify({"success": True, "message": f"注册成功，欢迎 {username}！", "username": username, "role": role})
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

    role = user.get('role', 'user')

    return jsonify({
        "success": True, 
        "message": f"欢迎回来，{username}！", 
        "username": username,
        "goal": user.get('goal', ''),
        "role": role
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



# ========== 管理员 API ==========
@app.route('/api/admin/menu/reset', methods=['POST'])
def admin_reset_menu():
    """管理员重置指定学校菜单为精选数据库版本"""
    data = request.json or {}
    username = data.get('username', '').strip()
    school_name = data.get('school_name', '').strip()
    
    if not is_admin():
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    if school_name not in CURATED_DATABASE:
        return jsonify({"success": False, "message": "该学校不在精选数据库中"}), 404
    
    # 获取精选数据库的菜品
    curated_dishes = CURATED_DATABASE[school_name]["dishes"]
    formatted_menu = "\n".join(curated_dishes)
    now = time.strftime("%Y-%m-%d %H:%M")
    
    # 写入数据库
    supabase_ok = False
    if supabase_client:
        try:
            supabase_client.table('school_menus').upsert({
                "school_name": school_name,
                "menu": formatted_menu,
                "last_modified": now
            }, on_conflict='school_name').execute()
            supabase_ok = True
        except Exception as e:
            print(f"[admin_reset_menu] Supabase 更新失败：{e}")
    
    # JSON 保底
    db_data = load_all_data()
    db_data[school_name] = {"menu": formatted_menu, "last_modified": now}
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[admin_reset_menu] JSON 保存失败：{e}")
    
    return jsonify({
        "success": True,
        "message": f"已将「{school_name}」菜单重置为精选版本（{len(curated_dishes)} 道菜品）",
        "count": len(curated_dishes),
        "cloud_synced": supabase_ok
    })


@app.route('/api/admin/menu/clear', methods=['POST'])
def admin_clear_menu():
    """管理员清空指定学校菜单"""
    data = request.json or {}
    username = data.get('username', '').strip()
    school_name = data.get('school_name', '').strip()
    
    if not is_admin():
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    
    # 从数据库删除
    supabase_ok = False
    if supabase_client:
        try:
            supabase_client.table('school_menus').delete().eq('school_name', school_name).execute()
            supabase_ok = True
        except Exception as e:
            print(f"[admin_clear_menu] Supabase 删除失败：{e}")
    
    # JSON 保底
    db_data = load_all_data()
    if school_name in db_data:
        del db_data[school_name]
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[admin_clear_menu] JSON 保存失败：{e}")
    
    return jsonify({
        "success": True,
        "message": f"已清空「{school_name}」的菜单",
        "cloud_synced": supabase_ok
    })


@app.route('/api/admin/menu/edit', methods=['POST'])
def admin_edit_menu():
    """管理员直接编辑指定学校菜单"""
    data = request.json or {}
    username = data.get('username', '').strip()
    school_name = data.get('school_name', '').strip()
    menu = data.get('menu', '')
    
    if not is_admin():
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not school_name:
        return jsonify({"success": False, "message": "学校名称不能为空"}), 400
    
    items = [item.strip() for item in menu.replace(",", "\n").split("\n") if item.strip()]
    formatted_menu = "\n".join(items)
    now = time.strftime("%Y-%m-%d %H:%M")
    
    # 写入数据库
    supabase_ok = False
    if supabase_client:
        try:
            supabase_client.table('school_menus').upsert({
                "school_name": school_name,
                "menu": formatted_menu,
                "last_modified": now
            }, on_conflict='school_name').execute()
            supabase_ok = True
        except Exception as e:
            print(f"[admin_edit_menu] Supabase 更新失败：{e}")
    
    # JSON 保底
    db_data = load_all_data()
    db_data[school_name] = {"menu": formatted_menu, "last_modified": now}
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[admin_edit_menu] JSON 保存失败：{e}")
    
    return jsonify({
        "success": True,
        "message": f"已更新「{school_name}」菜单（{len(items)} 道菜品）",
        "count": len(items),
        "cloud_synced": supabase_ok
    })


@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    """管理员获取所有用户列表"""
    username = request.args.get('username', '').strip()
    if not is_admin():
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
    
    if not is_admin():
        return jsonify({"success": False, "message": "需要管理员权限"}), 403
    if not target_username:
        return jsonify({"success": False, "message": "目标用户不能为空"}), 400
    
    # 删除用户
    users = load_meal_users()
    if target_username not in users:
        return jsonify({"success": False, "message": "用户不存在"}), 404
    
    del users[target_username]
    save_meal_users(users)
    
    # 删除打卡记录
    logs = load_meal_logs()
    if target_username in logs:
        del logs[target_username]
        save_meal_logs(logs)
    
    return jsonify({
        "success": True,
        "message": f"已删除用户「{target_username}」及其所有数据"
    })


@app.route('/api/admin/stats', methods=['GET'])
def admin_get_stats():
    """获取系统统计（从Supabase查询）"""
    username = request.args.get('username', '').strip()
    if not is_admin():
        return jsonify({"success": False, "message": "需要管理员权限"}), 403

    school_count = 0
    user_count = 0
    admin_count = 0
    total_meal_logs = 0
    total_dishes_logged = 0
    dish_tags_count = 0

    if supabase_client:
        try:
            r = supabase_client.table('school_menus').select('school_name', count='exact').execute()
            school_count = r.count or 0
        except:
            pass
        try:
            r = supabase_client.table('meal_users').select('username,role', count='exact').execute()
            user_count = r.count or 0
            admin_count = sum(1 for u in (r.data or []) if u.get('role') == 'admin')
        except:
            pass
        try:
            r = supabase_client.table('meal_logs').select('dishes', count='exact').execute()
            total_meal_logs = r.count or 0
            total_dishes_logged = sum(len((row.get('dishes') or '').split(',')) for row in (r.data or []) if row.get('dishes'))
        except:
            pass
        try:
            r = supabase_client.table('dish_tags').select('dish_name', count='exact').execute()
            dish_tags_count = r.count or 0
        except:
            pass

    return jsonify({
        "success": True,
        "stats": {
            "school_count": school_count,
            "user_count": user_count,
            "admin_count": admin_count,
            "total_meal_logs": total_meal_logs,
            "total_dishes_logged": total_dishes_logged,
            "dish_tags_count": dish_tags_count
        }
    })


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

        # 连续打卡天数（从今天往前）
        day_idx = 6 - i  # 0=6天前, 6=今天
        if day_meals > 0 and not streak_broken:
            if i == 0:  # 今天
                consecutive_days = 1
            elif consecutive_days > 0:
                consecutive_days += 1
        elif day_meals == 0 and i == 0:
            streak_broken = True

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
            # 检查是否连续
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


@app.route('/api/daily-score', methods=['GET'])
def daily_score():
    """今日饮食评分 - 用于首页英雄仪表组件"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"success": False, "message": "请先登录"}), 400

    today = time.strftime("%Y-%m-%d")
    logs = load_meal_logs()
    user_logs = logs.get(username, {})
    today_data = user_logs.get(today, {"breakfast": [], "lunch": [], "dinner": []})

    breakfast = today_data.get("breakfast", [])
    lunch = today_data.get("lunch", [])
    dinner = today_data.get("dinner", [])
    all_dishes = breakfast + lunch + dinner
    total_dishes = len(all_dishes)

    # 打卡状态
    checkin = {
        "breakfast": len(breakfast) > 0,
        "lunch": len(lunch) > 0,
        "dinner": len(dinner) > 0
    }
    meals_logged = sum(1 for v in checkin.values() if v)

    # 无数据时返回基础信息
    if total_dishes == 0:
        return jsonify({
            "success": True,
            "score": 0,
            "checkin": checkin,
            "meals_logged": 0,
            "total_dishes": 0,
            "protein_count": 0,
            "vegetable_count": 0,
            "unhealthy_count": 0,
            "fried_count": 0,
            "comment": "今天还没有打卡哦，快去记录第一餐吧！",
            "tags": [],
            "goal": ""
        })

    # 获取用户目标
    users = load_meal_users()
    goal = users.get(username, {}).get('goal', '') or ''

    # 分析菜品标签
    all_tags = []
    protein_count = 0
    vegetable_count = 0
    unhealthy_count = 0
    fried_count = 0

    for dish in all_dishes:
        dish_tags = FOOD_TAGS.get(dish, [])
        all_tags.extend(dish_tags)

        has_protein_tag = any(t in dish_tags for t in ["高蛋白", "鸡肉", "猪肉", "牛肉", "鱼", "豆制品", "鸡蛋", "豆腐", "虾"])
        if not has_protein_tag:
            for kw in ["鸡胸", "牛肉", "鱼", "鸡蛋", "豆腐", "虾", "排骨", "瘦肉"]:
                if kw in dish:
                    has_protein_tag = True
                    break
        if has_protein_tag:
            protein_count += 1

        has_veg_tag = any(t in dish_tags for t in ["蔬菜", "菌菇", "根茎类"])
        if not has_veg_tag:
            for kw in ["西兰花", "青菜", "黄瓜", "番茄", "蔬菜", "沙拉", "白菜", "菠菜", "芹菜", "萝卜"]:
                if kw in dish:
                    has_veg_tag = True
                    break
        if has_veg_tag:
            vegetable_count += 1

        has_unhealthy_tag = any(t in dish_tags for t in ["高脂", "高糖"])
        if not has_unhealthy_tag:
            for kw in ["炸鸡", "红烧肉", "蛋糕", "薯条", "炸"]:
                if kw in dish:
                    has_unhealthy_tag = True
                    break
        if has_unhealthy_tag:
            unhealthy_count += 1

        has_fried_tag = "油炸" in dish_tags or any(t in dish_tags for t in ["油炸"])
        if not has_fried_tag:
            for kw in ["炸鸡", "薯条", "炸"]:
                if kw in dish:
                    has_fried_tag = True
                    break
        if has_fried_tag:
            fried_count += 1

    # 评分计算
    score = 70

    if goal == 'cutting':
        if unhealthy_count > 0:
            score -= unhealthy_count * 10
        if vegetable_count > 2:
            score += 10
        if protein_count > 0:
            score += 5
        if meals_logged >= 3:
            score += 5
    elif goal == 'bulking':
        if protein_count >= 3:
            score += 15
        elif protein_count >= 1:
            score += 5
        else:
            score -= 10
        if total_dishes >= 4:
            score += 5
    else:  # healthy or no goal
        if meals_logged >= 3:
            score += 10
        if vegetable_count > 0 and protein_count > 0:
            score += 10
        elif total_dishes > 0 and vegetable_count == 0:
            score -= 5
        if fried_count > 2:
            score -= 5

    # 动态评语
    comment = ""
    if score >= 90:
        comment = "今天饮食非常均衡，继续保持！"
    elif score >= 70:
        comment = "今天吃得不错，还可以更好哦"
    elif score >= 50:
        comment = "饮食还有改善空间，注意荤素搭配"
    else:
        comment = "今天饮食需要注意调整哦"

    # 目标相关的详细评语
    if goal == 'bulking':
        if protein_count >= 3:
            comment = f"蛋白质摄入{protein_count}次，增肌营养跟上了！"
        elif protein_count == 0:
            comment = "今天蛋白质摄入不足，建议加份鸡蛋或豆腐"
    elif goal == 'cutting':
        if unhealthy_count == 0 and vegetable_count > 0:
            comment = "清淡饮食+蔬菜，减脂节奏把握得很好！"
        elif unhealthy_count > 0:
            comment = f"今天有{unhealthy_count}道高油菜品，建议换成清蒸或凉拌"

    # 统计标签
    tags = []
    if protein_count > 0:
        tags.append({"text": f"蛋白质 {protein_count}次", "type": "good"})
    if vegetable_count > 0:
        tags.append({"text": f"蔬菜 {vegetable_count}次", "type": "good"})
    if vegetable_count == 0 and total_dishes > 0:
        tags.append({"text": "蔬菜摄入偏少", "type": "warn"})
    if fried_count > 0:
        tags.append({"text": f"油炸 {fried_count}次", "type": "warn" if fried_count > 1 else "info"})
    if meals_logged < 3 and total_dishes > 0:
        tags.append({"text": f"已打卡{meals_logged}餐", "type": "info"})

    score = max(0, min(100, score))

    return jsonify({
        "success": True,
        "score": score,
        "checkin": checkin,
        "meals_logged": meals_logged,
        "total_dishes": total_dishes,
        "protein_count": protein_count,
        "vegetable_count": vegetable_count,
        "unhealthy_count": unhealthy_count,
        "fried_count": fried_count,
        "comment": comment,
        "tags": tags,
        "goal": goal
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


@app.route('/api/version', methods=['GET'])
def get_version():
    """返回当前版本号，同时用作健康检查端点"""
    try:
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                info = json.load(f)
            return jsonify({
                "success": True,
                "version": info.get("version", "unknown"),
                "build_time": info.get("build_time", ""),
                "changelog": info.get("changelog", "")
            })
    except Exception as e:
        print(f"读取版本文件失败: {e}")
    return jsonify({
        "success": True,
        "version": "unknown",
        "build_time": "",
        "changelog": ""
    })


@app.route('/api/status', methods=['GET'])
def system_status():
    """系统状态诊断"""
    status = {
        "supabase_connected": supabase_client is not None,
        "supabase_url": SUPABASE_URL[:30] + "..." if SUPABASE_URL else "(未设置)",
        "storage_backend": "supabase" if supabase_client else "local_json (临时!)",
        "deploy_id": "v15-lb-fix-0625",
    }
    import os
    for name, path in [("cafeteria_data", DATA_FILE), ("meal_logs", MEAL_LOGS_FILE),
                        ("meal_users", MEAL_USERS_FILE), ("dish_tags", USER_TAGS_FILE)]:
        status[f"{name}_exists"] = os.path.exists(path) if path else False
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


# ========== 开发者模式 API ==========
@app.route('/api/dev/verify', methods=['POST'])
def dev_verify():
    """验证开发者模式密码"""
    data = request.json or {}
    password = data.get('password', '').strip()
    config = load_dev_config()
    if password == config.get('password', ''):
        session['dev_verified'] = True
        return jsonify({"success": True, "message": "验证成功"})
    return jsonify({"success": False, "message": "密码错误"}), 403


@app.route('/api/dev/question', methods=['GET'])
def dev_question():
    """获取安全问题"""
    config = load_dev_config()
    return jsonify({
        "success": True,
        "question": config.get('security_question', '创始人的外号')
    })


@app.route('/api/dev/change-password', methods=['POST'])
def dev_change_password():
    """修改开发者模式密码（需回答安全问题）"""
    data = request.json or {}
    answer = data.get('answer', '').strip()
    new_password = data.get('new_password', '').strip()
    if not new_password or len(new_password) < 4:
        return jsonify({"success": False, "message": "新密码至少4位"}), 400
    config = load_dev_config()
    if answer != config.get('security_answer', ''):
        return jsonify({"success": False, "message": "安全问题答案错误"}), 403
    config['password'] = new_password
    if save_dev_config(config):
        return jsonify({"success": True, "message": "密码修改成功"})
    return jsonify({"success": False, "message": "保存失败"}), 500


# ========== 诊断测试 ==========
@app.route('/api/test/leaderboard-check')
def leaderboard_check():
    """诊断：确认排行榜代码是否已部署"""
    return jsonify({
        "success": True,
        "message": "排行榜代码已部署",
        "leaderboard_file": LEADERBOARD_FILE,
        "file_exists": os.path.exists(LEADERBOARD_FILE)
    })


# ========== 排行榜 API ==========
def load_leaderboard_scores():
    """加载排行榜分数数据 - 优先Supabase"""
    if supabase_client:
        try:
            resp = supabase_client.table('leaderboard_scores').select('*').execute()
            result = {}
            for row in (resp.data or []):
                u = row['username']
                if u not in result:
                    result[u] = {}
                result[u][row['date']] = {
                    'score': row.get('score', 0),
                    'school': row.get('school', ''),
                    'meals_count': row.get('meals_count', 0),
                    'submitted_at': row.get('submitted_at', '')
                }
            return result
        except Exception as e:
            print(f"Supabase加载排行榜失败: {e}")
    if os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_leaderboard_scores(data):
    """保存排行榜分数数据 - 仅JSON fallback"""
    try:
        with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存排行榜数据失败: {e}")
        return False

def load_leaderboard_privacy():
    """加载排行榜隐私设置 - 优先Supabase"""
    if supabase_client:
        try:
            resp = supabase_client.table('leaderboard_privacy').select('*').execute()
            return {row['username']: row.get('opted_in', True) for row in (resp.data or [])}
        except Exception as e:
            print(f"Supabase加载隐私设置失败: {e}")
    if os.path.exists(LEADERBOARD_PRIVACY_FILE):
        try:
            with open(LEADERBOARD_PRIVACY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_leaderboard_privacy(data):
    """保存排行榜隐私设置 - 仅JSON fallback"""
    try:
        with open(LEADERBOARD_PRIVACY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存隐私设置失败: {e}")
        return False

def is_opted_in(username):
    """检查用户是否参与排行榜（默认参与）- 优先Supabase"""
    if supabase_client:
        try:
            resp = supabase_client.table('leaderboard_privacy').select('opted_in').eq('username', username).execute()
            if resp.data and len(resp.data) > 0:
                return resp.data[0].get('opted_in', True)
            return True
        except:
            pass
    privacy = load_leaderboard_privacy()
    return privacy.get(username, True)

@app.route('/api/leaderboard/submit', methods=['POST'])
def submit_leaderboard_score():
    """提交每日分数到排行榜"""
    data = request.json or {}
    username = data.get('username', '').strip()
    date = data.get('date', '').strip()
    score = data.get('score', 0)
    school = data.get('school', '').strip()
    meals_count = data.get('meals_count', 0)

    if not username or not date:
        return jsonify({"success": False, "message": "参数不完整"}), 400

    # 优先写入Supabase
    if supabase_client:
        try:
            supabase_client.table('leaderboard_scores').upsert({
                'username': username,
                'date': date,
                'score': score,
                'school': school,
                'meals_count': meals_count,
                'submitted_at': datetime.datetime.now().isoformat()
            }, on_conflict='username,date').execute()
            print(f"排行榜分数已保存到Supabase: {username} {date} {score}")
            return jsonify({"success": True})
        except Exception as e:
            print(f"Supabase保存排行榜失败: {e}")

    # Fallback: JSON文件
    scores = load_leaderboard_scores()
    if username not in scores:
        scores[username] = {}
    scores[username][date] = {
        "score": score,
        "school": school,
        "meals_count": meals_count,
        "submitted_at": datetime.datetime.now().isoformat()
    }
    save_leaderboard_scores(scores)
    return jsonify({"success": True})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """获取排行榜（日/周/月，全局排行）"""
    period = request.args.get('period', 'daily')
    target_date = request.args.get('date', datetime.date.today().isoformat())
    rankings = []

    if supabase_client:
        try:
            from datetime import timedelta
            target = datetime.date.fromisoformat(target_date)
            if period == 'daily':
                date_list = [target_date]
            elif period == 'weekly':
                date_list = [(target - timedelta(days=i)).isoformat() for i in range(7)]
            else:
                date_list = [(target - timedelta(days=i)).isoformat() for i in range(30)]

            # 获取opted-in用户
            priv_resp = supabase_client.table('leaderboard_privacy').select('username,opted_in').execute()
            opted_out = {r['username'] for r in (priv_resp.data or []) if not r.get('opted_in', True)}

            # 查询日期范围内的分数
            start_date = date_list[-1]
            scores_resp = supabase_client.table('leaderboard_scores').select('*').gte('date', start_date).lte('date', target_date).execute()
            all_rows = scores_resp.data or []

            # 按用户聚合
            user_entries = {}
            for row in all_rows:
                u = row['username']
                if u in opted_out or row['date'] not in date_list:
                    continue
                if u not in user_entries:
                    user_entries[u] = []
                user_entries[u].append(row)

            for username, entries in user_entries.items():
                if period == 'daily':
                    for e in entries:
                        rankings.append({"username": username, "score": e["score"], "meals_count": e.get("meals_count", 0)})
                else:
                    avg_score = sum(e["score"] for e in entries) / len(entries)
                    total_meals = sum(e.get("meals_count", 0) for e in entries)
                    rankings.append({"username": username, "score": round(avg_score, 1), "meals_count": total_meals, "days": len(entries)})

            rankings.sort(key=lambda x: x["score"], reverse=True)
            return jsonify({"success": True, "rankings": rankings[:50]})
        except Exception as e:
            print(f"Supabase排行榜查询失败: {e}")

    # Fallback: JSON文件
    scores = load_leaderboard_scores()
    privacy = load_leaderboard_privacy()

    if period == 'daily':
        for username, user_scores in scores.items():
            if not privacy.get(username, True):
                continue
            if target_date in user_scores:
                entry = user_scores[target_date]
                rankings.append({"username": username, "score": entry["score"], "meals_count": entry.get("meals_count", 0)})
    elif period == 'weekly':
        from datetime import timedelta
        target = datetime.date.fromisoformat(target_date)
        week_dates = [(target - timedelta(days=i)).isoformat() for i in range(7)]
        for username, user_scores in scores.items():
            if not privacy.get(username, True):
                continue
            week_entries = [user_scores[d] for d in week_dates if d in user_scores]
            if not week_entries:
                continue
            avg_score = sum(e["score"] for e in week_entries) / len(week_entries)
            total_meals = sum(e.get("meals_count", 0) for e in week_entries)
            rankings.append({"username": username, "score": round(avg_score, 1), "meals_count": total_meals, "days": len(week_entries)})
    elif period == 'monthly':
        from datetime import timedelta
        target = datetime.date.fromisoformat(target_date)
        month_dates = [(target - timedelta(days=i)).isoformat() for i in range(30)]
        for username, user_scores in scores.items():
            if not privacy.get(username, True):
                continue
            month_entries = [user_scores[d] for d in month_dates if d in user_scores]
            if not month_entries:
                continue
            avg_score = sum(e["score"] for e in month_entries) / len(month_entries)
            total_meals = sum(e.get("meals_count", 0) for e in month_entries)
            rankings.append({"username": username, "score": round(avg_score, 1), "meals_count": total_meals, "days": len(month_entries)})

    rankings.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({"success": True, "rankings": rankings[:50]})

@app.route('/api/leaderboard/streak', methods=['GET'])
def get_streak_leaderboard():
    """获取连续打卡天数排行榜（毅力榜）"""
    rankings = []

    if supabase_client:
        try:
            from datetime import timedelta
            priv_resp = supabase_client.table('leaderboard_privacy').select('username,opted_in').execute()
            opted_out = {r['username'] for r in (priv_resp.data or []) if not r.get('opted_in', True)}

            today = datetime.date.today()
            start = (today - timedelta(days=365)).isoformat()
            end = today.isoformat()
            scores_resp = supabase_client.table('leaderboard_scores').select('username,date').gte('date', start).lte('date', end).execute()
            all_rows = scores_resp.data or []

            user_dates = {}
            for row in all_rows:
                u = row['username']
                if u in opted_out:
                    continue
                if u not in user_dates:
                    user_dates[u] = set()
                user_dates[u].add(row['date'])

            for username, dates_set in user_dates.items():
                dates = sorted(dates_set, reverse=True)
                if not dates:
                    continue
                streak = 1
                last_date = datetime.date.fromisoformat(dates[0])
                if (today - last_date).days > 1:
                    streak = 0
                else:
                    for i in range(1, len(dates)):
                        curr = datetime.date.fromisoformat(dates[i-1])
                        prev = datetime.date.fromisoformat(dates[i])
                        if (curr - prev).days == 1:
                            streak += 1
                        else:
                            break
                if streak > 0:
                    rankings.append({"username": username, "streak_days": streak})

            rankings.sort(key=lambda x: x["streak_days"], reverse=True)
            return jsonify({"success": True, "rankings": rankings[:50]})
        except Exception as e:
            print(f"Supabase毅力榜查询失败: {e}")

    # Fallback: JSON文件
    scores = load_leaderboard_scores()
    privacy = load_leaderboard_privacy()

    for username, user_scores in scores.items():
        if not privacy.get(username, True):
            continue
        dates = sorted(user_scores.keys(), reverse=True)
        if not dates:
            continue
        streak = 1
        today = datetime.date.today()
        last_date = datetime.date.fromisoformat(dates[0])
        if (today - last_date).days > 1:
            streak = 0
        else:
            for i in range(1, len(dates)):
                curr = datetime.date.fromisoformat(dates[i-1])
                prev = datetime.date.fromisoformat(dates[i])
                if (curr - prev).days == 1:
                    streak += 1
                else:
                    break
        if streak > 0:
            rankings.append({"username": username, "streak_days": streak})

    rankings.sort(key=lambda x: x["streak_days"], reverse=True)
    return jsonify({"success": True, "rankings": rankings[:50]})

@app.route('/api/leaderboard/privacy', methods=['GET'])
def get_leaderboard_privacy():
    """获取用户的排行榜隐私设置"""
    username = request.args.get('username', '').strip()
    if not username:
        return jsonify({"success": False, "message": "请提供用户名"}), 400
    opted_in = is_opted_in(username)
    return jsonify({"success": True, "opted_in": opted_in})

@app.route('/api/leaderboard/privacy', methods=['PUT'])
def set_leaderboard_privacy():
    """设置用户的排行榜隐私（参与/退出）"""
    data = request.json or {}
    username = data.get('username', '').strip()
    opted_in = data.get('opted_in', True)
    if not username:
        return jsonify({"success": False, "message": "请提供用户名"}), 400
    # 优先写入Supabase
    if supabase_client:
        try:
            supabase_client.table('leaderboard_privacy').upsert({
                'username': username,
                'opted_in': opted_in
            }).execute()
            return jsonify({"success": True, "opted_in": opted_in})
        except Exception as e:
            print(f"Supabase保存隐私设置失败: {e}")
    # Fallback: JSON文件
    privacy = load_leaderboard_privacy()
    privacy[username] = opted_in
    save_leaderboard_privacy(privacy)
    return jsonify({"success": True, "opted_in": opted_in})


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
