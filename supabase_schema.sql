-- ============================================
-- 吃了么 Supabase 建表脚本
-- 在 Supabase Dashboard → SQL Editor 中运行
-- ============================================

-- 1. 学校菜单数据
CREATE TABLE IF NOT EXISTS school_menus (
    school_name TEXT PRIMARY KEY,
    menu TEXT NOT NULL,
    last_modified TEXT NOT NULL
);

-- 2. 众包菜品标签
CREATE TABLE IF NOT EXISTS dish_tags (
    dish_name TEXT PRIMARY KEY,
    tags JSONB NOT NULL DEFAULT '[]'
);

-- 3. 三餐打卡记录
CREATE TABLE IF NOT EXISTS meal_logs (
    username TEXT NOT NULL,
    date TEXT NOT NULL,
    meals JSONB NOT NULL DEFAULT '{"breakfast":[],"lunch":[],"dinner":[]}',
    PRIMARY KEY (username, date)
);

-- 4. 打卡用户认证
CREATE TABLE IF NOT EXISTS meal_users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 启用 RLS（Row Level Security）— 允许 anon key 读写
ALTER TABLE school_menus ENABLE ROW LEVEL SECURITY;
ALTER TABLE dish_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_users ENABLE ROW LEVEL SECURITY;

-- 允许匿名读写（配合 anon key 使用）
CREATE POLICY "allow_select_school_menus" ON school_menus FOR SELECT USING (true);
CREATE POLICY "allow_insert_school_menus" ON school_menus FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_update_school_menus" ON school_menus FOR UPDATE USING (true);

CREATE POLICY "allow_select_dish_tags" ON dish_tags FOR SELECT USING (true);
CREATE POLICY "allow_insert_dish_tags" ON dish_tags FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_update_dish_tags" ON dish_tags FOR UPDATE USING (true);

CREATE POLICY "allow_select_meal_logs" ON meal_logs FOR SELECT USING (true);
CREATE POLICY "allow_insert_meal_logs" ON meal_logs FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_update_meal_logs" ON meal_logs FOR UPDATE USING (true);

CREATE POLICY "allow_select_meal_users" ON meal_users FOR SELECT USING (true);
CREATE POLICY "allow_insert_meal_users" ON meal_users FOR INSERT WITH CHECK (true);
CREATE POLICY "allow_update_meal_users" ON meal_users FOR UPDATE USING (true);
