"""
智能食堂菜品推荐系统 - 云端服务器
=====================================
功能：提供真正的联网云端数据共享服务
技术栈：Flask + SQLite
部署建议：Render / Railway / Heroku (都有免费套餐)

使用方法：
1. 安装依赖: pip install flask flask-cors
2. 运行服务器: python app_server.py
3. 本地测试: http://localhost:5000
4. 部署到云端后，修改客户端的 CLOUD_SERVER_URL
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import time
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求（Tkinter客户端需要）

# ========== 配置 ==========
DATABASE = 'cafeteria_cloud.db'
CLOUD_SERVER_URL = os.environ.get('CLOUD_SERVER_URL', 'http://localhost:5000')

# ========== 数据库初始化 ==========
def init_db():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 创建学校菜单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS school_menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT UNIQUE NOT NULL,
            menu_content TEXT NOT NULL,
            available_items TEXT DEFAULT '',
            contributor TEXT DEFAULT 'anonymous',
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            download_count INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0
        )
    ''')
    
    # 创建上传记录表（用于统计和防重复）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS upload_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contributor_id TEXT NOT NULL,
            school_name TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_school_name ON school_menus(school_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_contributor ON school_menus(contributor)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_updated_at ON school_menus(updated_at DESC)')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化成功")


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # 支持字典式访问
    return conn


# ========== API路由 ==========

@app.route('/')
def index():
    """首页 - API文档"""
    return jsonify({
        "service": "智能食堂云端数据共享服务",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "GET /api/schools": "获取所有学校列表",
            "GET /api/menu/<school_name>": "获取指定学校菜单",
            "POST /api/upload": "上传学校菜单数据",
            "POST /api/download": "批量下载/同步数据",
            "POST /api/like/<school_name>": "点赞某个学校的菜单",
            "GET /api/stats": "获取云端统计数据"
        },
        "example": {
            "upload": "POST /api/upload with JSON body",
            "download": "POST /api/download with last_sync_time"
        }
    })


@app.route('/api/schools', methods=['GET'])
def get_schools():
    """获取所有学校列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT school_name, contributor, version, updated_at, download_count, likes
            FROM school_menus
            ORDER BY updated_at DESC
        ''')
        
        schools = []
        for row in cursor.fetchall():
            schools.append({
                "school_name": row["school_name"],
                "contributor": row["contributor"],
                "version": row["version"],
                "updated_at": row["updated_at"],
                "download_count": row["download_count"],
                "likes": row["likes"]
            })
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(schools),
            "schools": schools
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取学校列表失败: {str(e)}"
        }), 500


@app.route('/api/menu/<school_name>', methods=['GET'])
def get_menu(school_name):
    """获取指定学校的菜单"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM school_menus WHERE school_name = ?
        ''', (school_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                "success": False,
                "message": f"学校 '{school_name}' 不存在"
            }), 404
        
        # 增加下载次数
        conn = get_db_connection()
        conn.execute('''
            UPDATE school_menus SET download_count = download_count + 1 
            WHERE school_name = ?
        ''', (school_name,))
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": {
                "school_name": row["school_name"],
                "menu_content": row["menu_content"],
                "available_items": row["available_items"],
                "contributor": row["contributor"],
                "version": row["version"],
                "updated_at": row["updated_at"]
            }
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取菜单失败: {str(e)}"
        }), 500


@app.route('/api/upload', methods=['POST'])
def upload_data():
    """
    上传学校菜单数据
    请求体格式:
    {
        "contributor_id": "用户标识(可选)",
        "schools": {
            "学校名": {
                "menu": "菜品1\\n菜品2",
                "available_items": [...]
            }
        }
    }
    """
    try:
        data = request.json
        
        if not data or 'schools' not in data:
            return jsonify({
                "success": False,
                "message": "请求数据格式错误，需要包含 'schools' 字段"
            }), 400
        
        schools_data = data['schools']
        contributor_id = data.get('contributor_id', 'anonymous')
        
        if not isinstance(schools_data, dict):
            return jsonify({
                "success": False,
                "message": "'schools' 必须是对象格式"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        uploaded_count = 0
        updated_count = 0
        skipped_count = 0
        
        for school_name, school_info in schools_data.items():
            if not school_name or not school_info:
                continue
            
            # 提取菜单内容
            if isinstance(school_info, dict):
                menu_content = school_info.get('menu', '')
                available_items = json.dumps(school_info.get('available_items', []), ensure_ascii=False)
            else:
                menu_content = str(school_info)
                available_items = ''
            
            # 检查是否已存在
            cursor.execute('SELECT id, version FROM school_menus WHERE school_name = ?', (school_name,))
            existing = cursor.fetchone()
            
            if existing:
                # 更新已有记录（总是接受最新版本）
                cursor.execute('''
                    UPDATE school_menus 
                    SET menu_content = ?, 
                        available_items = ?,
                        contributor = ?,
                        version = version + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE school_name = ?
                ''', (menu_content, available_items, contributor_id, school_name))
                updated_count += 1
            else:
                # 插入新记录
                cursor.execute('''
                    INSERT INTO school_menus (school_name, menu_content, available_items, contributor)
                    VALUES (?, ?, ?, ?)
                ''', (school_name, menu_content, available_items, contributor_id))
                uploaded_count += 1
            
            # 记录上传日志
            cursor.execute('''
                INSERT INTO upload_logs (contributor_id, school_name, ip_address)
                VALUES (?, ?, ?)
            ''', (contributor_id, school_name, request.remote_addr))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "上传成功",
            "stats": {
                "uploaded": uploaded_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "total": uploaded_count + updated_count
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"上传失败: {str(e)}"
        }), 500


@app.route('/api/download', methods=['POST'])
def download_data():
    """
    批量下载/同步数据
    支持增量同步，只返回更新的学校
    
    请求体格式:
    {
        "last_sync_time": "上次同步时间 (可选，格式: YYYY-MM-DD HH:MM:SS)",
        "school_name": "学校名称 (可选，如果提供则只返回该学校的数据)"
    }
    """
    try:
        data = request.json or {}
        last_sync_time = data.get('last_sync_time', None)
        school_name = data.get('school_name', None)  # 新增：学校名称筛选
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        if school_name:
            # 如果指定了学校，只查询该学校
            if last_sync_time:
                cursor.execute('''
                    SELECT * FROM school_menus 
                    WHERE school_name = ? AND updated_at > ?
                    ORDER BY updated_at DESC
                ''', (school_name, last_sync_time))
            else:
                cursor.execute('''
                    SELECT * FROM school_menus 
                    WHERE school_name = ?
                    ORDER BY updated_at DESC
                ''', (school_name,))
        else:
            # 否则查询所有学校
            if last_sync_time:
                # 增量同步：只返回更新的数据
                cursor.execute('''
                    SELECT * FROM school_menus 
                    WHERE updated_at > ?
                    ORDER BY updated_at DESC
                ''', (last_sync_time,))
            else:
                # 全量同步：返回所有数据
                cursor.execute('''
                    SELECT * FROM school_menus 
                    ORDER BY updated_at DESC
                ''')
        
        schools = {}
        for row in cursor.fetchall():
            schools[row["school_name"]] = {
                "menu": row["menu_content"],
                "available_items": json.loads(row["available_items"]) if row["available_items"] else [],
                "contributor": row["contributor"],
                "version": row["version"],
                "updated_at": row["updated_at"]
            }
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(schools),
            "schools": schools,
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sync_type": "incremental" if last_sync_time else "full",
            "filtered_by_school": school_name is not None  # 标记是否按学校过滤
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"下载失败: {str(e)}"
        }), 500


@app.route('/api/like/<school_name>', methods=['POST'])
def like_school(school_name):
    """给某个学校的菜单点赞"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查学校是否存在
        cursor.execute('SELECT id FROM school_menus WHERE school_name = ?', (school_name,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                "success": False,
                "message": f"学校 '{school_name}' 不存在"
            }), 404
        
        # 增加点赞数
        cursor.execute('''
            UPDATE school_menus SET likes = likes + 1 WHERE school_name = ?
        ''', (school_name,))
        
        cursor.execute('SELECT likes FROM school_menus WHERE school_name = ?', (school_name,))
        likes = cursor.fetchone()["likes"]
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "likes": likes,
            "message": "点赞成功"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"点赞失败: {str(e)}"
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取云端统计数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 学校总数
        cursor.execute('SELECT COUNT(*) as count FROM school_menus')
        school_count = cursor.fetchone()["count"]
        
        # 总上传次数
        cursor.execute('SELECT COUNT(*) as count FROM upload_logs')
        upload_count = cursor.fetchone()["count"]
        
        # 最近7天上传趋势
        cursor.execute('''
            SELECT DATE(upload_time) as date, COUNT(*) as count
            FROM upload_logs
            WHERE upload_time >= DATE('now', '-7 days')
            GROUP BY DATE(upload_time)
            ORDER BY date DESC
        ''')
        recent_uploads = [{"date": row["date"], "count": row["count"]} for row in cursor.fetchall()]
        
        # 最受欢迎的学校（按点赞数）
        cursor.execute('''
            SELECT school_name, likes, download_count
            FROM school_menus
            ORDER BY likes DESC
            LIMIT 10
        ''')
        popular_schools = [{
            "school_name": row["school_name"],
            "likes": row["likes"],
            "download_count": row["download_count"]
        } for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_schools": school_count,
                "total_uploads": upload_count,
                "recent_uploads": recent_uploads,
                "popular_schools": popular_schools
            }
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取统计数据失败: {str(e)}"
        }), 500


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
    print("🚀 智能食堂云端服务器启动中...")
    print("=" * 60)
    
    # 初始化数据库
    init_db()
    
    # 获取端口（从环境变量或使用默认值）
    port = int(os.environ.get('PORT', 5000))
    
    print(f"\n📡 服务器地址: http://localhost:{port}")
    print(f"📊 API文档: http://localhost:{port}/")
    print(f"\n💡 提示: 部署到云端后，记得修改客户端的 CLOUD_SERVER_URL\n")
    print("=" * 60)
    
    # 启动服务器
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )
