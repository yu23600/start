"""
菜品数据获取模块 - 多数据源 + 降级策略

数据源优先级:
1. 精选数据库 (curated) - 从公开文章/博客整理的可靠数据
2. 网络爬取 (web_scrape) - 从高校后勤网站等爬取

使用方式:
    from dish_fetcher import fetch_dishes
    result = fetch_dishes("北京大学")
    # result = {"success": True, "school": "北京大学", "dishes": [...], "source": "curated", ...}
"""

import json
import os
import re
import time
from typing import Dict, List, Optional, Tuple

# ============================================================
# 1. 精选数据库 - 从公开文章、博客、高校介绍等整理的菜品数据
#    数据来源会在每个条目中标注，方便追溯和验证
# ============================================================

CURATED_DATABASE: Dict[str, Dict] = {
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
        "source_url": "https://www.sohu.com/a/561870609_519114",
        "last_updated": "2026-06-23",
        "confidence": "medium",
        "note": "基础菜品来自公开文章，部分常见菜品为补充，建议用户核实"
    },
    "清华大学": {
        "dishes": [
            "卷饼", "小笼包", "三鲜锅贴", "红糖烧麦",
            "牛肉味状元饼", "麻球", "叉烧", "五谷豆浆",
            "酱排骨", "红烧肉", "京酱肉丝", "土豆牛肉",
            "孜然羊肉", "素炒西蓝花", "青菜炖豆腐", "香菇肉片",
            "紫荆紫薯包", "紫三糖醋里脊", "桃李二层三杯鸡",
            "桃李二层冬瓜虾皮汤", "南园一层酸笋粉", "紫三炸酱面",
            "清芬二层烤鸭", "紫三酸辣粉", "桃李二层黄油紫薯花卷",
            "观畴一层炒米粉", "紫二虎皮鸡蛋", "南园一层牛角包",
            "麻辣香锅", "炒菜花",
            "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋", "回锅肉",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "清华食堂美食攻略 + 水木食集标准化食谱",
        "source_url": "https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt_4545449471727987647",
        "last_updated": "2026-06-23",
        "confidence": "medium",
        "note": "包含清华特色菜品（紫荆/桃李/南园/清芬/观畴食堂），建议用户核实"
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
        "source_url": "https://www.sohu.com/a/561870609_519114",
        "last_updated": "2026-06-23",
        "confidence": "medium",
        "note": "基础菜品来自公开文章，部分常见菜品为补充"
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
        "source_url": "",
        "last_updated": "2026-06-23",
        "confidence": "low",
        "note": "基于上海高校食堂常见菜品整理，含本帮菜特色，建议用户重点核实"
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
        "source_url": "",
        "last_updated": "2026-06-23",
        "confidence": "low",
        "note": "基于浙江高校食堂常见菜品整理，含杭帮菜特色，建议用户重点核实"
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
        "source_url": "https://www.sohu.com/a/561870609_519114",
        "last_updated": "2026-06-23",
        "confidence": "medium",
        "note": "基础菜品来自公开文章，部分常见菜品为补充"
    },
    "天津大学": {
        "dishes": [
            "糖醋大排", "大牌红烧肉", "菠萝咕咾肉", "砂锅面",
            "水煮鱼片", "糖醋小排", "炒南瓜", "石锅拌饭",
            "豆腐汤", "铁板烧", "刀削面", "肉片金针菇",
            "盐焗虾", "海鲜面", "葱油拌面", "拉面",
            "油泼面", "肥肠面", "蛋包饭", "腊肉饭",
            "韩式烤肉饭", "日式泡菜饭", "烧鹅双拼饭",
            "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章",
        "source_url": "https://www.sohu.com/a/561870609_519114",
        "last_updated": "2026-06-23",
        "confidence": "high",
        "note": "菜品数据较详细，来自专门的天大食堂介绍"
    },
    "南京大学": {
        "dishes": [
            "辣子鸡套餐", "煮玉米",
            "红烧肉", "宫保鸡丁", "麻婆豆腐", "西红柿炒蛋",
            "回锅肉", "水煮肉片", "干煸豆角", "地三鲜",
            "木须肉", "青椒肉丝", "蒜蓉西兰花", "番茄牛",
            "酸菜鱼", "鱼香肉丝", "糖醋排骨", "盐水鸭",
            "鸭血粉丝汤", "小笼包", "锅贴",
            "米饭", "馒头", "花卷", "面条"
        ],
        "source": "985高校食堂对比文章 + 南京特色补充",
        "source_url": "https://www.sohu.com/a/561870609_519114",
        "last_updated": "2026-06-23",
        "confidence": "medium",
        "note": "基础菜品来自公开文章，含南京特色菜品补充"
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
        "source_url": "https://www.sohu.com/a/561870609_519114",
        "last_updated": "2026-06-23",
        "confidence": "high",
        "note": "川菜特色菜品丰富，数据较详细"
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
        "source_url": "https://www.sohu.com/a/561870609_519114",
        "last_updated": "2026-06-23",
        "confidence": "high",
        "note": "含武汉特色菜品（热干面/三鲜豆皮/武昌鱼等），数据较详细"
    },
    "宁德师范学院": {
        "dishes": [
            # 一食堂
            "炒面", "炒米粉", "瓦罐汤",
            # 二食堂
            "过桥米线", "排骨米线", "水饺", "牛肉面",
            # 三食堂
            "凉拌河粉", "鸭腿", "麻辣香锅",
            # 四食堂/新食堂
            "杀猪粉", "麻辣烫", "菜配饭",
            # 旧食堂
            "烤鸭饭", "煎蛋", "番茄鸡蛋汤", "鸡蛋凉面",
            # 学生街周边
            "黄焖鸡", "意大利面", "手枪腿意面", "牛肉面", "鸡腿面",
            "拌粉", "卤味", "老鸭粉丝汤", "套餐饭", "糖醋排骨饭",
            "烤肉饭", "沙拉烤肉饭", "螺蛳粉", "渔粉", "紫米饭",
            "杂粮煎饼", "无骨炸鸡", "鸡公煲", "排骨粉",
            # 小吃甜品
            "饭团", "肉粽", "鸡蛋仔", "冰粉", "双皮奶", "绿豆汤",
            "四果汤", "白桃水仙",
            # 常见主食
            "米饭", "馒头", "花卷", "面条", "拉面"
        ],
        "source": "多篇宁德师范学院食堂美食攻略文章综合整理",
        "source_url": "https://mbd.baidu.com/newspage/data/dtlandingsuper?nid=dt_4416254505955582617",
        "last_updated": "2026-06-23",
        "confidence": "medium",
        "note": "数据来自多篇学生美食攻略，按食堂/学生街分类整理，建议用户核实具体档口是否仍在营业"
    },
}


# ============================================================
# 2. 网络爬取配置 - 针对特定高校后勤网站的爬取规则
# ============================================================

SCRAPE_CONFIGS: Dict[str, Dict] = {
    # 示例配置格式（实际爬取需要根据目标网站结构调整）:
    # "北京大学": {
    #     "url": "https://dinner.pku.edu.cn/menu",
    #     "method": "GET",
    #     "parser": "html",
    #     "selectors": {
    #         "dish_name": ".menu-item .name",
    #         "dish_price": ".menu-item .price"
    #     },
    #     "headers": {
    #         "User-Agent": "Mozilla/5.0 ..."
    #     }
    # },
}


# ============================================================
# 3. 核心获取逻辑
# ============================================================

def get_available_sources(school_name: str) -> List[Dict]:
    """
    获取指定学校可用的数据源列表
    
    Returns:
        [{"name": "curated", "label": "精选数据库", "confidence": "medium", ...}, ...]
    """
    sources = []
    
    # 检查精选数据库
    if school_name in CURATED_DATABASE:
        info = CURATED_DATABASE[school_name]
        sources.append({
            "name": "curated",
            "label": "精选数据库",
            "confidence": info["confidence"],
            "dish_count": len(info["dishes"]),
            "source_desc": info["source"],
            "note": info["note"]
        })
    
    # 检查爬取配置
    if school_name in SCRAPE_CONFIGS:
        sources.append({
            "name": "web_scrape",
            "label": "网络爬取",
            "confidence": "unknown",
            "dish_count": 0,
            "source_desc": f"从 {SCRAPE_CONFIGS[school_name].get('url', '未知')} 爬取",
            "note": "爬取结果需要仔细核实"
        })
    
    return sources


def fetch_from_curated(school_name: str) -> Dict:
    """从精选数据库获取菜品"""
    if school_name not in CURATED_DATABASE:
        return {
            "success": False,
            "message": f"精选数据库中暂无 {school_name} 的数据",
            "source": "curated"
        }
    
    info = CURATED_DATABASE[school_name]
    return {
        "success": True,
        "school": school_name,
        "dishes": info["dishes"],
        "source": "curated",
        "source_desc": info["source"],
        "source_url": info.get("source_url", ""),
        "confidence": info["confidence"],
        "note": info["note"],
        "dish_count": len(info["dishes"]),
        "last_updated": info["last_updated"]
    }


def fetch_from_web(school_name: str) -> Dict:
    """
    从网络爬取菜品（需要安装 requests + beautifulsoup4）
    
    目前为框架代码，需要根据具体学校配置爬取规则。
    """
    if school_name not in SCRAPE_CONFIGS:
        return {
            "success": False,
            "message": f"暂无 {school_name} 的网络爬取配置",
            "source": "web_scrape"
        }
    
    config = SCRAPE_CONFIGS[school_name]
    
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {
            "success": False,
            "message": "网络爬取需要安装 requests 和 beautifulsoup4: pip install requests beautifulsoup4",
            "source": "web_scrape"
        }
    
    try:
        url = config["url"]
        headers = config.get("headers", {})
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, config.get("parser", "html.parser"))
        selectors = config.get("selectors", {})
        dish_selector = selectors.get("dish_name", "")
        
        if not dish_selector:
            return {
                "success": False,
                "message": "爬取配置中未指定菜品选择器",
                "source": "web_scrape"
            }
        
        elements = soup.select(dish_selector)
        dishes = []
        for elem in elements:
            text = elem.get_text(strip=True)
            if text and len(text) < 50:  # 过滤掉过长的文本
                dishes.append(text)
        
        # 去重
        dishes = list(dict.fromkeys(dishes))
        
        return {
            "success": True,
            "school": school_name,
            "dishes": dishes,
            "source": "web_scrape",
            "source_desc": f"从 {url} 爬取",
            "source_url": url,
            "confidence": "low",
            "note": "爬取结果需要仔细核实",
            "dish_count": len(dishes)
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"网络请求失败: {str(e)}",
            "source": "web_scrape"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"爬取过程出错: {str(e)}",
            "source": "web_scrape"
        }


def fetch_dishes(school_name: str, source: Optional[str] = None) -> Dict:
    """
    获取指定学校的菜品数据（多数据源 + 自动降级）
    
    Args:
        school_name: 学校名称
        source: 指定数据源 ("curated" 或 "web_scrape")，不指定则自动选择最佳源
    
    Returns:
        {
            "success": True/False,
            "school": "学校名",
            "dishes": ["菜品1", "菜品2", ...],
            "source": "数据来源",
            "source_desc": "来源描述",
            "confidence": "high/medium/low",
            "note": "注意事项",
            "dish_count": 数量,
            ...
        }
    """
    if not school_name or not school_name.strip():
        return {
            "success": False,
            "message": "学校名称不能为空"
        }
    
    school_name = school_name.strip()
    
    # 如果指定了数据源，直接使用
    if source == "curated":
        return fetch_from_curated(school_name)
    elif source == "web_scrape":
        return fetch_from_web(school_name)
    
    # 自动选择：优先精选数据库，再尝试网络爬取
    # 1. 尝试精选数据库
    result = fetch_from_curated(school_name)
    if result["success"]:
        return result
    
    # 2. 尝试网络爬取
    result = fetch_from_web(school_name)
    if result["success"]:
        return result
    
    # 3. 都没有数据
    return {
        "success": False,
        "message": f"暂无 {school_name} 的菜品数据。所有数据源均不可用。",
        "available_sources": get_available_sources(school_name)
    }


def get_all_supported_schools() -> List[Dict]:
    """获取所有支持自动获取的学校列表"""
    schools = []
    for name, info in CURATED_DATABASE.items():
        schools.append({
            "name": name,
            "source": "curated",
            "confidence": info["confidence"],
            "dish_count": len(info["dishes"]),
            "source_desc": info["source"]
        })
    for name, config in SCRAPE_CONFIGS.items():
        if name not in CURATED_DATABASE:
            schools.append({
                "name": name,
                "source": "web_scrape",
                "confidence": "unknown",
                "dish_count": 0,
                "source_desc": config.get("url", "未知")
            })
    return schools


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("菜品数据获取模块 - 测试")
    print("=" * 60)
    
    # 列出所有支持的学校
    schools = get_all_supported_schools()
    print(f"\n支持自动获取的学校 ({len(schools)} 所):")
    for s in schools:
        conf_map = {"high": "高", "medium": "中", "low": "低", "unknown": "未知"}
        print(f"  - {s['name']} ({conf_map.get(s['confidence'], s['confidence'])}置信度, {s['dish_count']}道菜品)")
    
    # 测试获取
    print("\n" + "-" * 60)
    for school in ["北京大学", "清华大学", "四川大学", "武汉大学", "不存在的学校"]:
        print(f"\n获取 [{school}] 的菜品:")
        result = fetch_dishes(school)
        if result["success"]:
            print(f"  来源: {result['source_desc']}")
            print(f"  置信度: {result['confidence']}")
            print(f"  菜品数: {result['dish_count']}")
            print(f"  前5道: {', '.join(result['dishes'][:5])}")
        else:
            print(f"  失败: {result['message']}")
