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

# ========== 基础路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'web_app', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'web_app', 'static'))
CORS(app)

# ========== 配置 ==========
DATA_FILE = os.path.join(BASE_DIR, 'cafeteria_data.json')

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
    uni_file = os.path.join(BASE_DIR, 'universities.json')
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
        return jsonify({
            "success": True,
            "school": school_name,
            "dishes": info["dishes"],
            "source": "curated",
            "source_desc": info["source"],
            "confidence": info["confidence"],
            "note": "数据来自公开文章整理，建议核实",
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
