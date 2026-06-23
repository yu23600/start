# 吃了么 - Web版本

一个智能食堂菜品推荐系统的Web应用。

## 🚀 快速开始

### 1. 安装依赖

```bash
cd web_app
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python app.py
```

### 3. 访问应用

打开浏览器访问: http://localhost:5000

## ✨ 功能特性

### 简洁模式
- 📝 管理学校菜单
- 🎲 随机推荐菜品
- 💾 数据自动保存
- 📤 支持多学校管理

### 专业模式
- 🧠 智能营养推荐
- 📊 BMI计算与健康建议
- 👤 个性化身体数据分析
- 🥗 基于健康状况的推荐
  - 儿童饮食建议
  - 女性经期饮食
  - 感冒/肠胃不适饮食
  - 运动后营养补充
  - 体重管理建议
  - 素食推荐

## 📁 项目结构

```
web_app/
├── app.py              # Flask后端主程序
├── requirements.txt    # Python依赖
├── templates/
│   └── index.html     # 前端页面
├── static/
│   ├── style.css      # 样式文件
│   └── script.js      # JavaScript交互逻辑
└── cafeteria_data.json # 数据存储文件（自动生成）
```

## 🎨 界面设计

- 现代化渐变色彩设计
- 响应式布局，支持手机/平板/电脑
- 流畅的动画效果
- 直观的用户交互

## 🔧 技术栈

**后端:**
- Flask - Python Web框架
- JSON - 数据存储

**前端:**
- HTML5
- CSS3 (渐变、动画、响应式)
- JavaScript (ES6+, Fetch API)

## 📱 部署建议

### 本地开发
```bash
python app.py
```

### 生产环境部署

1. **使用 Gunicorn (Linux/Mac)**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. **使用 Waitress (Windows)**
```bash
pip install waitress
waitress-serve --port=5000 app:app
```

3. **部署到云平台**
   - Heroku
   - PythonAnywhere
   - Railway
   - Vercel (需要适配)

## 🌐 移动端访问

应用采用响应式设计，可以在手机上完美显示。在同一局域网内，其他设备可以通过以下方式访问：

```
http://你的电脑IP地址:5000
```

例如: `http://192.168.1.100:5000`

## 💡 使用提示

1. **首次使用**: 系统会自动创建默认学校和菜单
2. **添加菜品**: 在文本框中输入菜品，每行一个
3. **智能推荐**: 输入身高体重，勾选身体状况，获得个性化推荐
4. **数据保存**: 所有数据自动保存到 `cafeteria_data.json`

## 🔐 数据安全

- 所有数据存储在本地JSON文件
- 不会上传到任何服务器
- 可以手动备份 `cafeteria_data.json` 文件

## 📝 API接口

- `GET /api/schools` - 获取学校列表
- `GET /api/menu/<school>` - 获取菜单
- `POST /api/menu/<school>` - 保存菜单
- `POST /api/school/add` - 添加学校
- `POST /api/school/rename` - 重命名学校
- `GET /api/recommend/random/<school>` - 随机推荐
- `POST /api/recommend/smart` - 智能推荐
- `POST /api/bmi/calculate` - 计算BMI

## 🎯 未来计划

- [ ] 用户登录系统
- [ ] 云端数据同步
- [ ] 菜品图片上传
- [ ] 营养成分数据库
- [ ] 历史记录查看
- [ ] 分享推荐结果
- [ ] PWA支持（可安装到手机）

## 📄 许可证

MIT License

## 👨‍💻 开发者

吃了么团队 © 2026

---

享受健康饮食，从"吃了么"开始！🍽️
