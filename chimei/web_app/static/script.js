// ========== 全局变量 ==========
let currentSchool = '';
let inputModalCallback = null;
let universitiesList = []; // 大学列表
let selectedSchool = null; // 向导中选中的学校
let userGoal = '';  // 用户目标: cutting / bulking / healthy / ''
let wizardGoal = ''; // 向导中临时选中的目标
let todayMeals = { breakfast: [], lunch: [], dinner: [] };
let currentMealTab = 'breakfast';
let schoolMenuItems = [];
let excludedDishes = []; // 已推荐过的菜品，避免重复
let currentUserRole = 'user'; // 当前用户角色：admin / user
let selectedCampus = ''; // 选中的校区

// ========== 校区数据 ==========
const CAMPUS_DATA = {
    // === 福建省高校（90所）===
    // 本科 - 公办
    "厦门大学": ["思明校区", "翔安校区", "漳州校区"],
    "华侨大学": ["泉州校区", "厦门校区"],
    "福州大学": ["旗山校区", "怡山校区", "铜盘校区", "泉港校区"],
    "福建理工大学": ["旗山校区", "鳝溪校区", "鼓山校区"],
    "福建农林大学": ["旗山校区", "金山校区"],
    "集美大学": ["集美学村"],
    "福建医科大学": ["旗山校区", "台江校区"],
    "福建中医药大学": ["旗山校区", "屏山校区"],
    "福建师范大学": ["旗山校区", "仓山校区"],
    "闽江大学": ["主校区"],
    "武夷学院": ["主校区"],
    "宁德师范学院": ["东侨校区", "蕉城校区"],
    "泉州师范学院": ["主校区"],
    "闽南师范大学": ["主校区"],
    "厦门理工学院": ["主校区"],
    "三明学院": ["主校区"],
    "龙岩学院": ["主校区"],
    "福建商学院": ["主校区"],
    "福建警察学院": ["主校区"],
    "莆田学院": ["紫霄校区", "学园校区"],
    "厦门医学院": ["主校区"],
    "福建江夏学院": ["主校区"],
    "福建技术师范学院": ["主校区"],
    "黎明职业大学": ["主校区"],
    "福州职业技术大学": ["主校区"],
    // 本科 - 民办/独立学院
    "仰恩大学": ["主校区"],
    "厦门华厦学院": ["主校区"],
    "闽南理工学院": ["主校区"],
    "泉州职业技术大学": ["主校区"],
    "闽南科技学院": ["主校区"],
    "福州工商学院": ["主校区"],
    "厦门工学院": ["主校区"],
    "阳光学院": ["主校区"],
    "厦门大学嘉庚学院": ["主校区"],
    "福州大学至诚学院": ["主校区"],
    "集美大学诚毅学院": ["主校区"],
    "福建师范大学协和学院": ["主校区"],
    "福州外语外贸学院": ["主校区"],
    "泉州信息工程学院": ["主校区"],
    "福州理工学院": ["主校区"],
    "福建农林大学金山学院": ["主校区"],
    "福建福耀科技大学": ["主校区"],
    // 专科 - 公办
    "福建船政交通职业学院": ["主校区"],
    "漳州职业技术学院": ["主校区"],
    "闽西职业技术学院": ["主校区"],
    "福建林业职业技术学院": ["主校区"],
    "福建信息职业技术学院": ["主校区"],
    "福建水利电力职业技术学院": ["主校区"],
    "福建电力职业技术学院": ["主校区"],
    "厦门海洋职业技术学院": ["主校区"],
    "福建农业职业技术学院": ["主校区"],
    "福建卫生职业技术学院": ["主校区"],
    "泉州医学高等专科学校": ["主校区"],
    "闽北职业技术学院": ["主校区"],
    "泉州经贸职业技术学院": ["主校区"],
    "湄洲湾职业技术学院": ["主校区"],
    "福建生物工程职业技术学院": ["主校区"],
    "福建艺术职业学院": ["主校区"],
    "福建幼儿师范高等专科学校": ["主校区"],
    "厦门城市职业学院": ["主校区"],
    "泉州工艺美术职业学院": ["主校区"],
    "三明医学科技职业学院": ["主校区"],
    "宁德职业技术学院": ["主校区"],
    "福建体育职业技术学院": ["主校区"],
    "漳州城市职业学院": ["主校区"],
    "漳州卫生职业学院": ["主校区"],
    "泉州幼儿师范高等专科学校": ["主校区"],
    "闽江师范高等专科学校": ["主校区"],
    "集美工业职业学院": ["主校区"],
    // 专科 - 民办
    "福建华南女子职业学院": ["主校区"],
    "福州英华职业学院": ["主校区"],
    "泉州纺织服装职业学院": ["主校区"],
    "泉州华光职业学院": ["主校区"],
    "福州黎明职业技术学院": ["主校区"],
    "厦门演艺职业学院": ["主校区"],
    "厦门华天涉外职业技术学院": ["主校区"],
    "福州科技职业技术学院": ["主校区"],
    "福州软件职业技术学院": ["主校区"],
    "厦门兴才职业技术学院": ["主校区"],
    "厦门软件职业技术学院": ["主校区"],
    "厦门南洋职业学院": ["主校区"],
    "厦门东海职业技术学院": ["主校区"],
    "漳州科技职业学院": ["主校区"],
    "漳州理工职业学院": ["主校区"],
    "武夷山职业学院": ["主校区"],
    "泉州海洋职业学院": ["主校区"],
    "泉州轻工职业学院": ["主校区"],
    "厦门安防科技职业学院": ["主校区"],
    "泉州工程职业技术学院": ["主校区"],
    "福州墨尔本理工职业学院": ["主校区"],
};

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    runHealthCheck();
});

/**
 * 启动健康检查：确认后端可用后再初始化页面
 * 如果后端不可用（部署中），显示维护遮罩
 */
async function runHealthCheck() {
    const maxRetries = 3;
    let ok = false;

    for (let i = 0; i < maxRetries; i++) {
        try {
            const resp = await fetch('/api/version', { signal: AbortSignal.timeout(5000) });
            if (resp.ok) {
                const data = await resp.json();
                if (data.success) {
                    ok = true;
                    // 显示版本号
                    const verEl = document.getElementById('footerVersion');
                    if (verEl) {
                        let verText = `v${data.version}`;
                        if (data.build_time) verText += ` · ${data.build_time}`;
                        verEl.textContent = verText;
                    }
                    break;
                }
            }
        } catch (e) {
            // 网络错误或超时，继续重试
            console.warn(`健康检查第${i + 1}次失败:`, e.message);
        }
        // 等待后重试（递增间隔）
        if (i < maxRetries - 1) {
            await new Promise(r => setTimeout(r, 2000 * (i + 1)));
        }
    }

    if (ok) {
        // 隐藏维护遮罩（如果之前显示了）
        hideMaintenance();
        // 正常初始化
        initApp();
    } else {
        // 显示维护遮罩
        showMaintenance();
    }
}

/**
 * 维护遮罩上的"重新加载"按钮
 */
function retryHealthCheck() {
    const overlay = document.getElementById('maintenanceOverlay');
    if (overlay) {
        const btn = overlay.querySelector('button');
        if (btn) { btn.textContent = '检查中...'; btn.disabled = true; }
    }
    runHealthCheck().then(() => {
        const btn2 = document.getElementById('maintenanceOverlay')?.querySelector('button');
        if (btn2) { btn2.textContent = '重新加载'; btn2.disabled = false; }
    });
}

function showMaintenance() {
    const el = document.getElementById('maintenanceOverlay');
    if (el) el.style.display = 'flex';
}

function hideMaintenance() {
    const el = document.getElementById('maintenanceOverlay');
    if (el) el.style.display = 'none';
}

/**
 * 应用正常初始化（在健康检查通过后调用）
 */
function initApp() {
    loadUniversitiesList(); // 加载大学列表
    checkFirstTimeUse(); // 检查是否首次使用
    loadAllergies(); // 恢复过敏设置
    loadUserGoal(); // 加载用户目标
    updateTodayCheckinBar(); // 更新顶部打卡状态
    updateDailyScore(); // 更新今日饮食评分仪表
}

function setupEventListeners() {
    // 回车键触发智能推荐
    document.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            smartRecommend();
        }
    });
}

// ========== 学校管理 ==========
/**
 * 加载大学列表
 */
async function loadUniversitiesList() {
    try {
        const response = await fetch('/universities.json');
        const data = await response.json();
        universitiesList = data.universities || [];
        console.log(`✅ 加载了 ${universitiesList.length} 所高校`);
    } catch (error) {
        console.error('加载大学列表失败:', error);
        // 使用默认列表
        universitiesList = ['北京大学', '清华大学', '复旦大学', '上海交通大学'];
    }
}

/**
 * 检查是否首次使用
 */
function checkFirstTimeUse() {
    const hasSchool = localStorage.getItem('current_school');
    
    if (!hasSchool) {
        // 首次使用，显示向导
        showSchoolWizard();
        // 学校向导关闭后再触发登录（延迟检查）
        const wizardTimer = setInterval(() => {
            if (!document.getElementById('schoolWizardModal').classList.contains('show')) {
                clearInterval(wizardTimer);
                if (localStorage.getItem('current_school')) {
                    currentSchool = localStorage.getItem('current_school');
                    startupMealLogin();
                }
            }
        }, 500);
    } else {
        // 非首次使用，加载学校
        currentSchool = hasSchool;
        updateSchoolDisplay();
        loadMenu();
        startupMealLogin(); // 应用启动时弹出登录
    }
}

/**
 * 更新学校显示
 */
function updateSchoolDisplay() {
    const schoolNameElement = document.getElementById('currentSchoolName');
    if (schoolNameElement) {
        schoolNameElement.textContent = currentSchool || '未设置';
    }
}

async function loadMenu() {
    if (!currentSchool) return;
    
    try {
        const response = await fetch(`/api/menu/${encodeURIComponent(currentSchool)}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('menuText').value = data.menu;
            document.getElementById('itemCount').textContent = `(${data.count} 项)`;
        }
    } catch (error) {
        console.error('加载菜单失败:', error);
        showNotification('加载菜单失败', 'error');
    }
}

function showAddSchoolDialog() {
    showInputDialog(
        '添加新学校',
        '请输入新学校名称:',
        '',
        async (schoolName) => {
            if (!schoolName || !schoolName.trim()) {
                showNotification('学校名称不能为空！', 'warning');
                return;
            }
            
            schoolName = schoolName.trim();
            
            try {
                const response = await fetch('/api/school/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ school_name: schoolName })
                });
                
                const data = await response.json();
                
                if (data.success || response.status === 400) {
                    currentSchool = schoolName;
                    localStorage.setItem('current_school', schoolName);
                    document.getElementById('menuText').value = '';
                    document.getElementById('itemCount').textContent = '(0 项)';
                    updateSchoolDisplay();
                    if (data.success) {
                        showNotification(`学校 '${schoolName}' 创建成功！`, 'success');
                    } else {
                        showNotification(`学校 '${schoolName}' 已存在，已切换到该学校`, 'info');
                    }
                } else {
                    showNotification(data.message, 'error');
                }
            } catch (error) {
                console.error('添加学校失败:', error);
                showNotification('添加学校失败', 'error');
            }
        }
    );
}

function showRenameSchoolDialog() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    
    showInputDialog(
        '修改学校名称',
        `将学校名称 '${currentSchool}' 修改为:`,
        currentSchool,
        async (newName) => {
            if (!newName || !newName.trim()) {
                showNotification('学校名称不能为空！', 'warning');
                return;
            }
            
            newName = newName.trim();
            
            if (newName === currentSchool) {
                return;
            }
            
            if (!confirm(`确定要将学校名称从 '${currentSchool}' 修改为 '${newName}' 吗？`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/school/rename', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        old_name: currentSchool,
                        new_name: newName
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    currentSchool = newName;
                    localStorage.setItem('current_school', newName);
                    updateSchoolDisplay();
                    await loadMenu();
                    showNotification(`学校名称已成功修改为 '${newName}'！`, 'success');
                } else {
                    showNotification(data.message, 'error');
                }
            } catch (error) {
                console.error('修改学校名称失败:', error);
                showNotification('修改学校名称失败', 'error');
            }
        }
    );
}

// ========== BMI 计算器 ==========
function toggleBmiPanel() {
    const panel = document.getElementById('bmiPanel');
    const icon = document.getElementById('bmiToggleIcon');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        icon.textContent = '▼';
    } else {
        panel.style.display = 'none';
        icon.textContent = '▶';
    }
}

function calculateBMI() {
    const height = parseFloat(document.getElementById('heightInput').value);
    const weight = parseFloat(document.getElementById('weightInput').value);
    const resultEl = document.getElementById('bmiResult');
    
    if (!height || !weight || height <= 0 || weight <= 0) {
        resultEl.textContent = '请输入有效的身高和体重';
        resultEl.style.color = '#e74c3c';
        return;
    }
    
    const bmi = weight / ((height / 100) ** 2);
    let category = '';
    let color = '';
    
    if (bmi < 18.5) {
        category = '偏瘦';
        color = '#3498db';
    } else if (bmi < 24) {
        category = '正常';
        color = '#27ae60';
    } else if (bmi < 28) {
        category = '超重';
        color = '#f39c12';
    } else {
        category = '肥胖';
        color = '#e74c3c';
    }
    
    resultEl.innerHTML = `BMI: <strong>${bmi.toFixed(1)}</strong> — <span style="color:${color}">${category}</span>`;
    resultEl.style.color = '#333';
}

// ========== 菜单编辑器 ==========
// ========== 菜单编辑器（列表式） ==========
let editorDishes = []; // 编辑器中的菜品列表
let pendingAddDish = ''; // 待添加的菜品名
let pendingAddTags = []; // 待添加菜品的标签

function showMenuEditor() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    // 从 schoolMenuItems 或隐藏 textarea 加载
    if (schoolMenuItems.length > 0) {
        editorDishes = [...schoolMenuItems];
    } else {
        const menuText = document.getElementById('menuText');
        const text = menuText ? menuText.value.trim() : '';
        editorDishes = text ? text.split('\n').map(s => s.trim()).filter(s => s) : [];
    }
    editorHasUnsavedChanges = false;
    document.getElementById('editorSchoolHint').textContent = `「${currentSchool}」共 ${editorDishes.length} 道菜品`;
    document.getElementById('addDishArea').style.display = 'none';
    // 恢复保存按钮文本
    const saveBtn = document.getElementById('saveMenuBtn');
    if (saveBtn) {
        saveBtn.style.background = '';
        saveBtn.textContent = '💾 保存菜单';
    }
    const hint = document.getElementById('saveHint');
    if (hint) hint.style.display = 'none';
    document.getElementById('menuEditorModal').classList.add('show');
    renderDishList();
}

function closeMenuEditor() {
    if (editorHasUnsavedChanges) {
        if (!confirm('有更改尚未保存，确定要关闭吗？')) return;
    }
    editorHasUnsavedChanges = false;
    document.getElementById('menuEditorModal').classList.remove('show');
    editorDishes = [];
    // 恢复保存按钮文本
    const saveBtn = document.getElementById('saveMenuBtn');
    if (saveBtn) {
        saveBtn.style.background = '';
        saveBtn.textContent = '💾 保存菜单';
    }
    const hint = document.getElementById('saveHint');
    if (hint) hint.style.display = 'none';
}

function renderDishList() {
    const container = document.getElementById('dishListContainer');
    if (editorDishes.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:#999;padding:30px;">暂无菜品，点击下方"添加菜品"按钮</p>';
    } else {
        let html = '';
        editorDishes.forEach((dish, i) => {
            html += `<div class="editor-dish-item" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid #f0f0f0;">
                <span style="flex:1;font-size:0.95em;color:#333;">${dish}</span>
                <button onclick="deleteDishFromEditor(${i})" style="background:none;border:none;color:#ff6b6b;cursor:pointer;font-size:1.1em;padding:4px 8px;border-radius:6px;" title="删除" onmouseover="this.style.background='#fff0f0'" onmouseout="this.style.background='none'">✕</button>
            </div>`;
        });
        container.innerHTML = html;
    }
    document.getElementById('editorItemCount').textContent = `共 ${editorDishes.length} 道菜品`;
}

function deleteDishFromEditor(index) {
    const dish = editorDishes[index];
    editorDishes.splice(index, 1);
    renderDishList();
    markEditorDirty();
    showNotification(`已移除「${dish}」`, 'info');
}

function showAddDishArea() {
    document.getElementById('addDishArea').style.display = 'block';
    document.getElementById('addDishTagArea').style.display = 'none';
    const input = document.getElementById('addDishInput');
    input.value = '';
    input.focus();
    pendingAddDish = '';
    pendingAddTags = [];
}

function cancelAddDish() {
    document.getElementById('addDishArea').style.display = 'none';
    pendingAddDish = '';
    pendingAddTags = [];
}

async function confirmAddDish() {
    const input = document.getElementById('addDishInput');
    const name = input.value.trim();
    if (!name) {
        showNotification('请输入菜品名称', 'warning');
        return;
    }
    if (editorDishes.includes(name)) {
        showNotification('该菜品已存在', 'info');
        return;
    }
    // 先立即加入列表并刷新显示
    editorDishes.push(name);
    renderDishList();
    markEditorDirty();
    showNotification(`已添加「${name}」，记得点保存哦`, 'success');
    // 保持输入框可见，清空以便继续添加
    input.value = '';
    input.focus();
    pendingAddDish = name;
    pendingAddTags = [];
    // 显示标注区域（可选）
    await showAddDishTagUI(name);
}

async function showAddDishTagUI(dishName) {
    const tagArea = document.getElementById('addDishTagArea');
    tagArea.style.display = 'block';
    // 加载标签分类
    let taxonomy = {};
    try {
        const resp = await fetch('/api/dish-tags/taxonomy');
        const data = await resp.json();
        if (data.success) taxonomy = data.taxonomy;
    } catch(e) {}
    // 尝试加载已有标签
    try {
        const resp = await fetch(`/api/dish-tags/${encodeURIComponent(dishName)}`);
        const data = await resp.json();
        if (data.success && data.tags) pendingAddTags = [...data.tags];
    } catch(e) {}
    // 渲染标签 chips
    const container = document.getElementById('addDishTagChips');
    let html = '';
    for (const [cat, tags] of Object.entries(taxonomy)) {
        html += `<div style="width:100%;font-size:0.8em;color:#888;margin-top:4px;">${cat}</div>`;
        for (const tag of tags) {
            const sel = pendingAddTags.includes(tag) ? 'border-color:#667eea;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;' : '';
            html += `<div class="add-tag-chip" data-tag="${tag}" onclick="toggleAddDishTag('${tag}')" style="padding:5px 12px;border:2px solid #ddd;border-radius:16px;cursor:pointer;font-size:0.85em;transition:all 0.2s;${sel}">${tag}</div>`;
        }
    }
    container.innerHTML = html;
}

function toggleAddDishTag(tag) {
    const idx = pendingAddTags.indexOf(tag);
    if (idx >= 0) {
        pendingAddTags.splice(idx, 1);
    } else {
        pendingAddTags.push(tag);
    }
    // 更新 UI
    document.querySelectorAll('.add-tag-chip').forEach(chip => {
        const t = chip.dataset.tag;
        if (pendingAddTags.includes(t)) {
            chip.style.borderColor = '#667eea';
            chip.style.background = 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)';
            chip.style.color = 'white';
        } else {
            chip.style.borderColor = '#ddd';
            chip.style.background = '#fff';
            chip.style.color = '#333';
        }
    });
}

function finishAddDishWithTags() {
    if (!pendingAddDish) return;
    // 菜品已在列表中，只需保存标签
    if (pendingAddTags.length > 0) {
        saveDishTags(pendingAddDish, pendingAddTags);
        showNotification(`已为「${pendingAddDish}」标注 ${pendingAddTags.length} 个标签`, 'success');
    }
    resetAddDishArea();
}

function finishAddDishSkipTags() {
    // 菜品已在列表中，只需关闭标注区域
    resetAddDishArea();
}

async function saveDishTags(dishName, tags) {
    try {
        await fetch('/api/dish-tags/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tags: { [dishName]: tags } })
        });
    } catch(e) { console.error('保存标签失败:', e); }
}

function resetAddDishArea() {
    document.getElementById('addDishArea').style.display = 'none';
    document.getElementById('addDishTagArea').style.display = 'none';
    document.getElementById('addDishInput').value = '';
    pendingAddDish = '';
    pendingAddTags = [];
}

// 标记编辑器有未保存的更改
let editorHasUnsavedChanges = false;

function markEditorDirty() {
    editorHasUnsavedChanges = true;
    const saveBtn = document.getElementById('saveMenuBtn');
    if (saveBtn) {
        saveBtn.style.background = 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)';
        saveBtn.textContent = '💾 保存菜单（有更改）';
    }
    const hint = document.getElementById('saveHint');
    if (hint) hint.style.display = 'block';
}

async function saveMenuFromEditor() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    const menu = editorDishes.join('\n');
    if (editorDishes.length === 0) {
        if (!confirm('菜单内容为空，确定要保存吗？')) return;
    }
    try {
        const response = await fetch(`/api/menu/${encodeURIComponent(currentSchool)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ menu: menu })
        });
        const data = await response.json();
        if (data.success) {
            const menuText = document.getElementById('menuText');
            if (menuText) menuText.value = data.menu;
            document.getElementById('itemCount').textContent = `(${data.count} 项)`;
            schoolMenuItems = data.menu.split('\n').map(s => s.trim()).filter(s => s);
            editorHasUnsavedChanges = false;
            const syncMsg = data.cloud_synced ? '菜单已保存到云端！' : '菜单已保存（云端同步失败，仅本地保存）';
            showNotification(syncMsg, data.cloud_synced ? 'success' : 'warning');
            closeMenuEditor();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('保存菜单失败:', error);
        showNotification('保存菜单失败', 'error');
    }
}

// ========== 随机推荐 ==========
async function randomRecommend(exclude = '') {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    
    try {
        let url = `/api/recommend/random/${encodeURIComponent(currentSchool)}`;
        if (exclude) {
            url += `?exclude=${encodeURIComponent(exclude)}`;
        }
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            showModal(`
                <h2 style="color: #667eea; margin-bottom: 20px;">🎯 随机推荐结果</h2>
                <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 10px;">
                    <p style="font-size: 1.2em; color: #666; margin-bottom: 15px;">为 <strong>${data.school}</strong> 的你推荐：</p>
                    <p style="font-size: 2em; color: #11998e; font-weight: bold; margin: 20px 0;">✅ ${data.result}</p>
                    <p style="font-size: 1.1em; color: #888; margin-top: 20px;">🍽️ 用餐愉快！</p>
                </div>
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="randomRecommend('${data.result.replace(/'/g, "\\'")}')" class="btn btn-info" style="padding: 12px 28px; font-size: 1em; border-radius: 25px;">
                        🔄 不喜欢？换一个
                    </button>
                </div>
            `);
        } else {
            showNotification(data.message, 'warning');
        }
    } catch (error) {
        console.error('随机推荐失败:', error);
        showNotification('推荐失败', 'error');
    }
}

// ========== 智能推荐 ==========
async function smartRecommend(excludeList) {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    
    // 收集过敏信息
    const allergies = [];
    const allergyIds = {
        'allergy_seafood': '海鲜过敏',
        'allergy_peanut': '花生过敏',
        'allergy_lactose': '乳糖不耐'
    };
    for (const [id, name] of Object.entries(allergyIds)) {
        const el = document.getElementById(id);
        if (el && el.checked) {
            allergies.push(name);
        }
    }
    
    // 如果没有目标，提示用户先选
    const goal = userGoal || localStorage.getItem('user_goal') || '';
    if (!goal) {
        showGoalSwitcher();
        showNotification('请先选择一个饮食目标！', 'warning');
        return;
    }

    // 合并传入的排除列表和全局排除列表
    const allExclude = [...new Set([...(excludeList || []), ...excludedDishes])];
    
    try {
        const response = await fetch('/api/recommend/smart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                school_name: currentSchool,
                goal: goal,
                allergies: allergies,
                exclude: allExclude
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 记录已推荐的菜品
            excludedDishes.push(data.result);
            // 防止排除列表无限增长，保留最近20个
            if (excludedDishes.length > 20) {
                excludedDishes = excludedDishes.slice(-20);
            }

            let detailsHtml = '';
            if (data.details && data.details.length > 0) {
                detailsHtml = '<div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">' +
                    data.details.map(d => `<p style="margin: 5px 0; color: #666;">${d}</p>`).join('') +
                    '</div>';
            }
            
            const goalLabel = data.goal || '';
            const goalPrefix = goalLabel ? `根据你「${goalLabel}」的目标，` : '';
            const escapedResult = data.result.replace(/'/g, "\\'");
            const escapedExclude = JSON.stringify(excludedDishes).replace(/"/g, '&quot;');
            
            showModal(`
                <h2 style="color: #667eea; margin-bottom: 20px;">🧠 智能推荐结果</h2>
                <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%); border-radius: 10px;">
                    <p style="font-size: 1.1em; color: #666; margin-bottom: 15px;">${goalPrefix}为 <strong>${currentSchool}</strong> 的你推荐：</p>
                    <p style="font-size: 2.2em; color: #11998e; font-weight: bold; margin: 20px 0;">✅ ${data.result}</p>
                    ${detailsHtml}
                    <p style="font-size: 1.1em; color: #888; margin-top: 20px;">🍽️ 希望你用餐愉快！</p>
                </div>
                <div style="text-align: center; margin-top: 20px;">
                    <button onclick="smartRecommend(['${escapedResult}'])" class="btn btn-info" style="padding: 12px 28px; font-size: 1em; border-radius: 25px;">
                        🔄 不喜欢？换一批
                    </button>
                </div>
            `);
        } else {
            showNotification(data.message, 'warning');
        }
    } catch (error) {
        console.error('智能推荐失败:', error);
        showNotification('推荐失败', 'error');
    }
}

// ========== 目标管理 ==========
async function loadUserGoal() {
    const user = getMealUser();
    if (!user) return;
    const goal = localGetGoal(user);
    if (goal) {
        userGoal = goal;
        localStorage.setItem('user_goal', goal);
    } else {
        userGoal = localStorage.getItem('user_goal') || '';
    }
    updateGoalStatusBar();
    updateGoalCards();
}

function updateGoalStatusBar() {
    const iconEl = document.getElementById('goalStatusIcon');
    const textEl = document.getElementById('goalStatusText');
    const goalMap = {
        'cutting': { icon: '🔥', text: '减脂期' },
        'bulking': { icon: '💪', text: '增肌期' },
        'healthy': { icon: '🌿', text: '保持健康' }
    };
    if (userGoal && goalMap[userGoal]) {
        iconEl.textContent = goalMap[userGoal].icon;
        textEl.textContent = goalMap[userGoal].text;
    } else {
        iconEl.textContent = '🎯';
        textEl.textContent = '点击设置饮食目标';
    }
}

function updateGoalCards() {
    const section = document.getElementById('goalCardsSection');
    if (!section) return;
    if (userGoal) {
        section.style.display = 'none'; // 已选目标，隐藏卡片
    } else {
        section.style.display = 'block'; // 未选目标，显示卡片
    }
    // Still update individual card highlights
    document.querySelectorAll('#goalCards .goal-card').forEach(card => {
        card.classList.remove('selected');
        if (card.dataset.goal === userGoal) {
            card.classList.add('selected');
        }
    });
}

function selectGoalFromCards(goal) {
    wizardGoal = goal;
    document.querySelectorAll('#goalCards .goal-card').forEach(card => {
        card.classList.remove('selected');
        if (card.dataset.goal === goal) {
            card.classList.add('selected');
        }
    });
    // 直接保存
    saveGoal(goal);
}

async function saveGoal(goal) {
    const g = wizardGoal || userGoal || goal;
    const user = getMealUser();
    if (user) {
        localSaveGoal(user, g);
    }
    userGoal = g;
    localStorage.setItem('user_goal', g);
    updateGoalStatusBar();
    updateGoalCards();
    document.getElementById('goalWizardModal').classList.remove('show');
}

function showGoalSwitcher() {
    document.getElementById('goalWizardModal').classList.add('show');
    wizardGoal = userGoal;
    document.querySelectorAll('#goalWizardModal .goal-wizard-card').forEach(card => {
        card.classList.remove('selected');
        if (card.dataset.goal === userGoal) {
            card.classList.add('selected');
        }
    });
    document.getElementById('goalConfirmBtn').disabled = !userGoal;
}

function pickGoalWizard(goal) {
    wizardGoal = goal;
    document.querySelectorAll('#goalWizardModal .goal-wizard-card').forEach(card => {
        card.classList.remove('selected');
        if (card.dataset.goal === goal) {
            card.classList.add('selected');
        }
    });
    document.getElementById('goalConfirmBtn').disabled = false;
}

function confirmGoalWizard() {
    if (wizardGoal) {
        saveGoal(wizardGoal);
    }
    document.getElementById('goalWizardModal').classList.remove('show');
}

function skipGoalWizard() {
    document.getElementById('goalWizardModal').classList.remove('show');
}

// ========== 过敏管理 ==========
function saveAllergies() {
    const allergies = [];
    if (document.getElementById('allergy_seafood')?.checked) allergies.push('海鲜过敏');
    if (document.getElementById('allergy_peanut')?.checked) allergies.push('花生过敏');
    if (document.getElementById('allergy_lactose')?.checked) allergies.push('乳糖不耐');
    localStorage.setItem('user_allergies', JSON.stringify(allergies));
}

function loadAllergies() {
    const saved = localStorage.getItem('user_allergies');
    if (!saved) return;
    try {
        const allergies = JSON.parse(saved);
        if (allergies.includes('海鲜过敏')) document.getElementById('allergy_seafood').checked = true;
        if (allergies.includes('花生过敏')) document.getElementById('allergy_peanut').checked = true;
        if (allergies.includes('乳糖不耐')) document.getElementById('allergy_lactose').checked = true;
    } catch (e) {
        console.error('加载过敏设置失败:', e);
    }
}

function toggleAllergyPanel() {
    const panel = document.getElementById('allergyPanel');
    const icon = document.getElementById('allergyToggleIcon');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        icon.textContent = '▼';
    } else {
        panel.style.display = 'none';
        icon.textContent = '▶';
    }
}

// ========== 弹窗工具 ==========
function showModal(content) {
    const modal = document.getElementById('resultModal');
    document.getElementById('modalBody').innerHTML = content;
    modal.classList.add('show');
}

function closeModal() {
    document.getElementById('resultModal').classList.remove('show');
}

function showInputDialog(title, prompt, defaultValue, callback) {
    document.getElementById('inputModalTitle').textContent = title;
    document.getElementById('inputModalPrompt').textContent = prompt;
    document.getElementById('inputModalField').value = defaultValue;
    
    inputModalCallback = callback;
    
    const modal = document.getElementById('inputModal');
    modal.classList.add('show');
    
    document.getElementById('inputModalField').focus();
}

function confirmInputModal() {
    const value = document.getElementById('inputModalField').value;
    closeInputModal();
    
    if (inputModalCallback) {
        inputModalCallback(value);
        inputModalCallback = null;
    }
}

function closeInputModal() {
    document.getElementById('inputModal').classList.remove('show');
    inputModalCallback = null;
}

// 点击弹窗外部关闭
window.onclick = function(event) {
    const resultModal = document.getElementById('resultModal');
    const inputModal = document.getElementById('inputModal');
    const schoolWizardModal = document.getElementById('schoolWizardModal');
    const dishFetcherModal = document.getElementById('dishFetcherModal');
    
    if (event.target === resultModal) {
        closeModal();
    }
    if (event.target === inputModal) {
        closeInputModal();
    }
    if (event.target === schoolWizardModal) {
        closeSchoolWizard();
    }
    if (event.target === dishFetcherModal) {
        closeDishFetcher();
    }
};

// ESC键关闭弹窗
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeModal();
        closeInputModal();
        closeSchoolWizard();
        closeDishFetcher();
    }
});

// ========== 通知工具 ==========
function showNotification(message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? '#38ef7d' : type === 'warning' ? '#ffc107' : '#dc3545'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
        max-width: 300px;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // 3秒后自动消失
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ========== 学校选择向导 ==========
/**
 * 显示学校选择向导
 */
function showSchoolWizard() {
    const modal = document.getElementById('schoolWizardModal');
    modal.classList.add('show');
    
    // 清理旧的校区选择器
    const campusContainer = document.getElementById('campusSelectorContainer');
    if (campusContainer) campusContainer.remove();
    
    // 渲染学校列表
    renderSchoolList(universitiesList);
    
    // 清空搜索框和自定义输入
    document.getElementById('schoolSearchInput').value = '';
    document.getElementById('customSchoolInput').value = '';
    selectedSchool = null;
    selectedCampus = '';
}

/**
 * 渲染学校列表
 */
function renderSchoolList(schools) {
    const listContainer = document.getElementById('schoolList');
    
    if (schools.length === 0) {
        listContainer.innerHTML = '<p class="loading-text">未找到匹配的学校</p>';
        return;
    }
    
    let html = '';
    schools.forEach(school => {
        const selectedClass = selectedSchool === school ? 'selected' : '';
        html += `
            <div class="school-item ${selectedClass}" onclick="selectSchool('${school}')">
                ${school}
            </div>
        `;
    });
    
    listContainer.innerHTML = html;
}

/**
 * 选择学校（点击列表项）
 */
function selectSchool(schoolName) {
    selectedSchool = schoolName;
    selectedCampus = ''; // 重置校区选择
    
    // 更新UI显示选中状态
    const items = document.querySelectorAll('.school-item');
    items.forEach(item => {
        item.classList.remove('selected');
        if (item.textContent.trim() === schoolName) {
            item.classList.add('selected');
        }
    });
    
    // 清空自定义输入
    document.getElementById('customSchoolInput').value = '';
    
    // 显示校区选择器
    showCampusSelector(schoolName);
}

/**
 * 显示校区选择器
 */
function showCampusSelector(schoolName) {
    let campusContainer = document.getElementById('campusSelectorContainer');
    
    // 移除旧的校区选择器
    if (campusContainer) {
        campusContainer.remove();
    }
    
    const campuses = CAMPUS_DATA[schoolName];
    if (!campuses || campuses.length <= 1) {
        // 没有多校区或只有一个校区，不需要选择
        selectedCampus = '';
        return;
    }
    
    // 创建校区选择器
    campusContainer = document.createElement('div');
    campusContainer.id = 'campusSelectorContainer';
    campusContainer.style.cssText = 'margin-top:15px;padding-top:15px;border-top:2px solid #e9ecef;';
    
    let html = '<p style="font-weight:600;color:#495057;margin-bottom:8px;">🏛️ 选择校区：</p>';
    html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
    
    // 添加"不指定"选项
    html += `<div class="campus-chip" data-campus="" onclick="selectCampus('')" style="padding:8px 16px;border:2px solid #ddd;border-radius:20px;background:#fff;cursor:pointer;font-size:0.9em;transition:all 0.2s;">不指定</div>`;
    
    for (const campus of campuses) {
        html += `<div class="campus-chip" data-campus="${campus}" onclick="selectCampus('${campus}')" style="padding:8px 16px;border:2px solid #ddd;border-radius:20px;background:#fff;cursor:pointer;font-size:0.9em;transition:all 0.2s;">${campus}</div>`;
    }
    
    html += '</div>';
    campusContainer.innerHTML = html;
    
    // 插入到自定义输入框之前
    const customOption = document.querySelector('.custom-school-option');
    if (customOption) {
        customOption.parentNode.insertBefore(campusContainer, customOption);
    }
}

/**
 * 选择校区
 */
function selectCampus(campus) {
    selectedCampus = campus;
    
    // 更新UI
    document.querySelectorAll('.campus-chip').forEach(chip => {
        chip.style.borderColor = '#ddd';
        chip.style.background = '#fff';
        chip.style.color = '#333';
    });
    
    const selected = document.querySelector(`.campus-chip[data-campus="${campus}"]`);
    if (selected) {
        selected.style.borderColor = '#667eea';
        selected.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        selected.style.color = 'white';
    }
}

/**
 * 过滤学校（搜索功能）
 */
function filterSchools() {
    const searchText = document.getElementById('schoolSearchInput').value.trim().toLowerCase();
    
    if (!searchText) {
        renderSchoolList(universitiesList);
        return;
    }
    
    const filtered = universitiesList.filter(school => 
        school.toLowerCase().includes(searchText)
    );
    
    renderSchoolList(filtered);
}

/**
 * 确认学校选择
 */
async function confirmSchoolSelection() {
    // 优先使用自定义输入
    const customInput = document.getElementById('customSchoolInput').value.trim();
    let finalSchool = customInput || selectedSchool;
    
    if (!finalSchool) {
        showNotification('请选择或输入一个学校！', 'warning');
        return;
    }
    
    // 如果有校区选择，将校区附加到学校名称
    if (selectedCampus && !customInput) {
        finalSchool = `${finalSchool}-${selectedCampus}`;
    }
    
    try {
        // 创建学校
        const response = await fetch('/api/school/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ school_name: finalSchool })
        });
        
        const data = await response.json();
        
        if (data.success || response.status === 400) {
            const oldSchool = currentSchool;
            // 保存当前学校到localStorage
            currentSchool = finalSchool;
            localStorage.setItem('current_school', finalSchool);
            
            // 关闭向导
            closeSchoolWizard();
            
            // 更新显示
            updateSchoolDisplay();
            loadMenu();
            
            // 根据情况显示不同提示
            if (oldSchool && oldSchool !== finalSchool) {
                showNotification(`已从 ${oldSchool} 切换到 ${finalSchool}`, 'success');
            } else {
                showNotification(`欢迎加入 ${finalSchool}！`, 'success');
            }
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('创建学校失败:', error);
        showNotification('创建学校失败', 'error');
    }
}

/**
 * 关闭学校向导
 */
function closeSchoolWizard() {
    const modal = document.getElementById('schoolWizardModal');
    modal.classList.remove('show');
    
    // 清理校区选择器
    const campusContainer = document.getElementById('campusSelectorContainer');
    if (campusContainer) campusContainer.remove();
    selectedCampus = '';
}

/**
 * 显示修改学校对话框
 */
function showChangeSchoolDialog() {
    // 直接显示学校选择向导，不清空数据
    showSchoolWizard();
}

// ========== 数据导出/导入功能 ==========
async function exportData() {
    try {
        const response = await fetch('/api/data/export');
        const result = await response.json();

        if (!result.success) {
            showNotification('导出失败: ' + result.message, 'error');
            return;
        }

        const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `吃了么_数据备份_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showNotification(`已导出 ${result.school_count} 个学校的数据`, 'success');
    } catch (error) {
        console.error('导出失败:', error);
        showNotification('导出失败', 'error');
    }
}

async function importData(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        const text = await file.text();
        const parsed = JSON.parse(text);

        // 支持两种格式：直接是 {学校: {menu:...}} 或 {data: {学校: {menu:...}}}
        const schoolsData = parsed.data || parsed;

        if (typeof schoolsData !== 'object' || Object.keys(schoolsData).length === 0) {
            showNotification('文件格式不正确或没有数据', 'warning');
            return;
        }

        const response = await fetch('/api/data/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ schools: schoolsData })
        });

        const result = await response.json();
        if (result.success) {
            showNotification(result.message, 'success');
            // 重新加载当前菜单
            await loadMenu();
        } else {
            showNotification('导入失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('导入失败:', error);
        showNotification('导入失败，请检查文件格式', 'error');
    }

    // 重置文件输入，以便可以再次导入同一文件
    event.target.value = '';
}

// ========== 菜品自动获取功能 ==========
let fetchedDishes = [];
let fetchResultInfo = {};
let taggingDishes = [];
let taggingIndex = 0;
let taggingTags = {};
let tagTaxonomy = null;

function showDishFetcher() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }

    const modal = document.getElementById('dishFetcherModal');
    modal.classList.add('show');

    document.getElementById('fetcherStep1').style.display = 'block';
    document.getElementById('fetcherStep2').style.display = 'none';
    document.getElementById('fetcherStep3').style.display = 'none';
    document.getElementById('fetcherLoading').style.display = 'none';
    document.getElementById('fetcherError').style.display = 'none';
    document.getElementById('fetcherActionBtn').textContent = '开始获取';
    document.getElementById('fetcherActionBtn').onclick = startFetchDishes;
    document.getElementById('extraDishes').value = '';

    // 移除可能存在的"跳过标注"按钮
    const skipBtn = document.getElementById('skipTaggingBtn');
    if (skipBtn) skipBtn.remove();

    const sourceInfo = document.getElementById('fetcherSourceInfo');

    // 先加载当前学校的已保存菜单
    fetch(`/api/menu/${encodeURIComponent(currentSchool)}`)
        .then(r => r.json())
        .then(data => {
            if (data.success && data.items && data.items.length > 0) {
                // 有已保存菜单，显示当前菜单内容
                sourceInfo.innerHTML = `
                    <p style="color:#333;font-weight:600;margin-bottom:8px;">📋 「${currentSchool}」当前菜单（${data.count} 道菜品）</p>
                    <div style="max-height:150px;overflow-y:auto;background:#f8f9fa;border-radius:8px;padding:10px;margin-bottom:10px;font-size:0.9em;color:#555;">
                        ${data.items.map(d => `<span style="display:inline-block;background:white;border:1px solid #e0e0e0;border-radius:4px;padding:2px 8px;margin:2px;font-size:0.9em;">${d}</span>`).join('')}
                    </div>
                    <p style="color:#666;">点击"开始获取"将从云端加载最新菜单数据，你可以逐条审核、增删菜品。</p>
                    <p style="color:#999;font-size:0.85em;margin-top:5px;">如果云端没有数据，将尝试从精选数据库获取参考菜品。</p>
                `;
            } else {
                // 没有已保存菜单
                sourceInfo.innerHTML = '<p style="color:#666;">当前学校暂无菜单数据。点击"开始获取"将从云端或精选数据库加载菜品。</p><p style="color:#999;font-size:0.85em;margin-top:5px;">你可以逐条审核、增删菜品，修改后保存。</p>';
            }
        })
        .catch(() => {
            sourceInfo.innerHTML = '<p style="color:#666;">点击"开始获取"将加载菜品数据。</p>';
        });
}

function closeDishFetcher() {
    document.getElementById('dishFetcherModal').classList.remove('show');
    document.getElementById('fetcherStep3').style.display = 'none';
    fetchedDishes = [];
    fetchResultInfo = {};
    taggingDishes = [];
    taggingIndex = 0;
    taggingTags = {};
    // 移除跳过标注按钮
    const skipBtn = document.getElementById('skipTaggingBtn');
    if (skipBtn) skipBtn.remove();
}

async function startFetchDishes() {
    const loading = document.getElementById('fetcherLoading');
    const errorDiv = document.getElementById('fetcherError');
    const sourceInfo = document.getElementById('fetcherSourceInfo');

    sourceInfo.style.display = 'none';
    errorDiv.style.display = 'none';
    loading.style.display = 'block';
    document.getElementById('fetcherActionBtn').disabled = true;

    try {
        // 先尝试获取当前学校的已保存菜单
        const menuResp = await fetch(`/api/menu/${encodeURIComponent(currentSchool)}`);
        const menuData = await menuResp.json();

        if (menuData.success && menuData.items && menuData.items.length > 0) {
            // 有已保存菜单，直接使用
            loading.style.display = 'none';
            document.getElementById('fetcherActionBtn').disabled = false;
            fetchedDishes = menuData.items;
            fetchResultInfo = {
                confidence: 'high',
                source_desc: '已保存的菜单数据',
                note: '这是你之前保存的菜单，可以逐条审核、增删后重新保存。',
                dish_count: menuData.items.length
            };
            showDishReviewStep();
            return;
        }

        // 没有已保存菜单，尝试从精选数据库获取
        const response = await fetch('/api/dishes/fetch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ school_name: currentSchool })
        });

        const data = await response.json();
        loading.style.display = 'none';
        document.getElementById('fetcherActionBtn').disabled = false;

        if (data.success) {
            fetchedDishes = data.dishes || [];
            fetchResultInfo = data;
            showDishReviewStep();
        } else {
            errorDiv.style.display = 'block';
            errorDiv.innerHTML = `<p><strong>未找到数据</strong></p><p style="margin-top:8px;">${data.message}</p><p style="margin-top:8px;color:#999;font-size:0.85em;">你可以继续手动输入菜品，或尝试其他学校。</p>`;
            document.getElementById('fetcherActionBtn').textContent = '返回';
            document.getElementById('fetcherActionBtn').onclick = () => {
                sourceInfo.style.display = 'block';
                errorDiv.style.display = 'none';
                document.getElementById('fetcherActionBtn').textContent = '开始获取';
                document.getElementById('fetcherActionBtn').onclick = startFetchDishes;
            };
        }
    } catch (error) {
        loading.style.display = 'none';
        document.getElementById('fetcherActionBtn').disabled = false;
        errorDiv.style.display = 'block';
        errorDiv.textContent = `请求失败: ${error.message}`;
    }
}

function showDishReviewStep() {
    document.getElementById('fetcherStep1').style.display = 'none';
    document.getElementById('fetcherStep2').style.display = 'block';

    const confMap = { high: '高', medium: '中', low: '低', unknown: '未知' };
    const conf = fetchResultInfo.confidence || 'unknown';
    const infoDiv = document.getElementById('fetcherResultInfo');

    // 根据置信度设置样式类和警告内容
    const confStyles = {
        high:   { cls: 'confidence-high',   icon: '✅', label: '数据可靠' },
        medium: { cls: 'confidence-medium', icon: '📋', label: '建议核实' },
        low:    { cls: 'confidence-low',    icon: '⚠️', label: '数据可能不准' },
        unknown:{ cls: 'confidence-low',    icon: '❓', label: '数据来源未知' }
    };
    const cs = confStyles[conf] || confStyles.unknown;

    // 移除旧的置信度类
    infoDiv.classList.remove('confidence-high', 'confidence-medium', 'confidence-low');
    infoDiv.classList.add(cs.cls);

    infoDiv.innerHTML = `
        <div class="confidence-header">
            <span class="confidence-icon">${cs.icon}</span>
            <span><strong>置信度: ${confMap[conf] || conf}</strong> — ${cs.label}</span>
            <span style="margin-left:auto;">共 ${fetchedDishes.length} 道菜品</span>
        </div>
        <div class="confidence-source">数据来源: ${fetchResultInfo.source_desc || '未知'}</div>
        ${fetchResultInfo.note ? `<div class="confidence-note">${fetchResultInfo.note}</div>` : ''}
    `;

    renderDishChecklist();
    updateSelectedCount();

    const actionBtn = document.getElementById('fetcherActionBtn');
    actionBtn.textContent = '💡 保存并开始标注';
    actionBtn.onclick = () => confirmAndSaveDishes(true);

    // 添加"跳过标注"按钮
    const footer = document.getElementById('fetcherFooter');
    let skipBtn = document.getElementById('skipTaggingBtn');
    if (!skipBtn) {
        skipBtn = document.createElement('button');
        skipBtn.id = 'skipTaggingBtn';
        skipBtn.className = 'btn btn-secondary';
        skipBtn.style.cssText = 'flex:1;min-width:80px;';
        footer.insertBefore(skipBtn, footer.querySelector('#fetcherActionBtn').nextSibling);
    }
    skipBtn.textContent = '跳过标注';
    skipBtn.onclick = () => confirmAndSaveDishes(false);
    skipBtn.style.display = '';
}

function renderDishChecklist() {
    const container = document.getElementById('dishChecklist');
    if (fetchedDishes.length === 0) {
        container.innerHTML = '<p style="color:#999;text-align:center;padding:20px;">暂无菜品数据</p>';
        return;
    }

    let html = '';
    fetchedDishes.forEach((dish, index) => {
        html += `
            <div class="dish-check-item checked" id="dish-item-${index}" onclick="toggleDishItem(${index})">
                <input type="checkbox" checked id="dish-cb-${index}" onclick="event.stopPropagation(); toggleDishItem(${index})">
                <label for="dish-cb-${index}" onclick="event.stopPropagation(); toggleDishItem(${index})">${dish}</label>
            </div>
        `;
    });
    container.innerHTML = html;
}

function toggleDishItem(index) {
    const item = document.getElementById(`dish-item-${index}`);
    const cb = document.getElementById(`dish-cb-${index}`);
    cb.checked = !cb.checked;
    item.className = `dish-check-item ${cb.checked ? 'checked' : 'unchecked'}`;
    updateSelectedCount();
}

function toggleAllDishes(selectAll) {
    fetchedDishes.forEach((_, index) => {
        const item = document.getElementById(`dish-item-${index}`);
        const cb = document.getElementById(`dish-cb-${index}`);
        cb.checked = selectAll;
        item.className = `dish-check-item ${selectAll ? 'checked' : 'unchecked'}`;
    });
    updateSelectedCount();
}

function updateSelectedCount() {
    const checked = fetchedDishes.filter((_, index) => {
        const cb = document.getElementById(`dish-cb-${index}`);
        return cb && cb.checked;
    }).length;
    document.getElementById('selectedCount').textContent = `已选 ${checked} / ${fetchedDishes.length}`;
}

async function confirmAndSaveDishes(proceedToTagging = false) {
    const selectedDishes = fetchedDishes.filter((_, index) => {
        const cb = document.getElementById(`dish-cb-${index}`);
        return cb && cb.checked;
    });

    const extraText = document.getElementById('extraDishes').value.trim();
    if (extraText) {
        const extraItems = extraText.split('\n').map(s => s.trim()).filter(s => s);
        selectedDishes.push(...extraItems);
    }

    if (selectedDishes.length === 0) {
        showNotification('请至少选择一个菜品！', 'warning');
        return;
    }

    const menuText = selectedDishes.join('\n');

    try {
        const response = await fetch(`/api/menu/${encodeURIComponent(currentSchool)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ menu: menuText })
        });

        const data = await response.json();
        if (data.success) {
            document.getElementById('menuText').value = data.menu;
            document.getElementById('itemCount').textContent = `(${data.count} 项)`;
            showNotification(`已成功保存 ${data.count} 道菜品到 ${currentSchool}！`, 'success');

            if (proceedToTagging) {
                startTagging(selectedDishes);
            } else {
                closeDishFetcher();
            }
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('保存菜品失败:', error);
        showNotification('保存失败', 'error');
    }
}

// ========== 众包打标功能 ==========
async function startTagging(dishes) {
    // 隐藏 Step 2，显示 Step 3
    document.getElementById('fetcherStep2').style.display = 'none';
    document.getElementById('fetcherStep3').style.display = 'block';
    // 隐藏 footer 按钮（标注步骤不需要）
    document.getElementById('fetcherFooter').style.display = 'none';

    taggingDishes = dishes;
    taggingIndex = 0;
    taggingTags = {};
    dishes.forEach(d => { taggingTags[d] = []; });

    // 获取标签分类体系
    try {
        const resp = await fetch('/api/dish-tags/taxonomy');
        const data = await resp.json();
        if (data.success) {
            tagTaxonomy = data.taxonomy;
        } else {
            showNotification('加载标签分类失败', 'warning');
            closeDishFetcher();
            return;
        }
    } catch (e) {
        console.error('获取标签分类失败:', e);
        showNotification('加载标签分类失败', 'error');
        closeDishFetcher();
        return;
    }

    renderTaggingDish();
}

function renderTaggingDish() {
    if (taggingDishes.length === 0) return;

    const dish = taggingDishes[taggingIndex];
    const total = taggingDishes.length;

    // 进度条
    const pct = ((taggingIndex + 1) / total * 100).toFixed(0);
    document.getElementById('taggingProgress').style.width = pct + '%';
    document.getElementById('taggingProgressText').textContent = `第 ${taggingIndex + 1} 道 / 共 ${total} 道`;

    // 菜名
    document.getElementById('taggingDishName').textContent = dish;

    // 导航按钮状态
    document.getElementById('tagPrevBtn').disabled = taggingIndex === 0;
    document.getElementById('tagNextBtn').textContent = taggingIndex === total - 1 ? '下一道 ➡' : '下一道 ➡';

    // 标签分类
    const container = document.getElementById('taggingCategories');
    const currentTags = taggingTags[dish] || [];
    let html = '';

    for (const [category, tags] of Object.entries(tagTaxonomy)) {
        html += `<div class="tag-category-title">${category}</div>`;
        html += '<div class="tag-chips">';
        for (const tag of tags) {
            const selected = currentTags.includes(tag) ? ' selected' : '';
            html += `<div class="tag-chip${selected}" onclick="toggleTagForDish('${tag}')">${tag}</div>`;
        }
        html += '</div>';
    }

    container.innerHTML = html;
}

function toggleTagForDish(tag) {
    const dish = taggingDishes[taggingIndex];
    if (!taggingTags[dish]) taggingTags[dish] = [];

    const idx = taggingTags[dish].indexOf(tag);
    if (idx >= 0) {
        taggingTags[dish].splice(idx, 1);
    } else {
        taggingTags[dish].push(tag);
    }

    renderTaggingDish();
}

function taggingNavigate(delta) {
    const newIndex = taggingIndex + delta;
    if (newIndex >= 0 && newIndex < taggingDishes.length) {
        taggingIndex = newIndex;
        renderTaggingDish();
    }
}

function taggingSkip() {
    // 跳到最后一道之后，直接完成
    finishTagging();
}

async function finishTagging() {
    // 过滤掉没有标注任何标签的菜品
    const tagsToSave = {};
    for (const [dish, tags] of Object.entries(taggingTags)) {
        if (tags.length > 0) {
            tagsToSave[dish] = tags;
        }
    }

    const taggedCount = Object.keys(tagsToSave).length;

    if (taggedCount > 0) {
        try {
            const resp = await fetch('/api/dish-tags/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tags: tagsToSave })
            });
            const data = await resp.json();
            if (data.success) {
                showNotification(`已保存 ${taggedCount} 道菜品的标签，推荐引擎将更准确！`, 'success');
            } else {
                showNotification(data.message || '保存标签失败', 'warning');
            }
        } catch (e) {
            console.error('保存标签失败:', e);
            showNotification('保存标签失败', 'error');
        }
    } else {
        showNotification('未标注任何标签，已跳过', 'info');
    }

    // 恢复 footer 并关闭弹窗
    document.getElementById('fetcherFooter').style.display = '';
    closeDishFetcher();
}

// ========== 三餐打卡功能 ==========

// --- localStorage 数据层（用户数据全部存在浏览器本地，不依赖服务器） ---

function _loadLocalUsers() {
    try { return JSON.parse(localStorage.getItem('chimei_users') || '{}'); } catch { return {}; }
}
function _saveLocalUsers(users) {
    localStorage.setItem('chimei_users', JSON.stringify(users));
}
function _loadLocalLogs() {
    try { return JSON.parse(localStorage.getItem('chimei_meal_logs') || '{}'); } catch { return {}; }
}
function _saveLocalLogs(logs) {
    localStorage.setItem('chimei_meal_logs', JSON.stringify(logs));
}

// 注册（本地）
function localRegister(username, password) {
    const users = _loadLocalUsers();
    if (users[username]) return { success: false, message: '该昵称已存在' };
    users[username] = { password: password, created_at: new Date().toISOString() };
    _saveLocalUsers(users);
    return { success: true };
}

// 登录验证（本地）
function localLogin(username, password) {
    const users = _loadLocalUsers();
    const user = users[username];
    if (!user) return { success: false, message: '昵称不存在，请先注册' };
    if (user.password !== password) return { success: false, message: '密码错误' };
    return { success: true, goal: user.goal || '' };
}

// 保存打卡记录（本地）
function localSaveMealLog(username, date, meal, dishes) {
    const logs = _loadLocalLogs();
    if (!logs[username]) logs[username] = {};
    if (!logs[username][date]) logs[username][date] = { breakfast: [], lunch: [], dinner: [] };
    logs[username][date][meal] = dishes;
    _saveLocalLogs(logs);
}

// 获取某天某用户的打卡记录
function localGetMealLog(username, date) {
    const logs = _loadLocalLogs();
    if (!logs[username] || !logs[username][date]) return { breakfast: [], lunch: [], dinner: [] };
    return logs[username][date];
}

// 获取用户目标（本地）
function localGetGoal(username) {
    const users = _loadLocalUsers();
    return (users[username] && users[username].goal) || '';
}

// 保存用户目标（本地）
function localSaveGoal(username, goal) {
    const users = _loadLocalUsers();
    if (users[username]) {
        users[username].goal = goal;
        _saveLocalUsers(users);
    }
}

// 获取过去7天的打卡数据（用于周报）
function localGetWeeklyData(username) {
    const logs = _loadLocalLogs();
    const userLogs = logs[username] || {};
    const today = new Date();
    const result = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const dateStr = d.toISOString().split('T')[0];
        result.push({
            date: dateStr,
            data: userLogs[dateStr] || { breakfast: [], lunch: [], dinner: [] }
        });
    }
    return result;
}

// --- 用户身份管理 ---
function getMealUser() {
    return localStorage.getItem('meal_user') || '';
}

function setMealUser(name) {
    localStorage.setItem('meal_user', name.trim());
}

function clearMealAuth() {
    localStorage.removeItem('meal_user');
    localStorage.removeItem('meal_pwd');
    localStorage.removeItem('meal_auto_login');
}

function isAutoLogin() {
    return localStorage.getItem('meal_auto_login') === 'true' && localStorage.getItem('meal_pwd');
}

function showMealLoginDialog() {
    return new Promise((resolve) => {
        let mode = 'login'; // 'login' or 'register'
        const existingUser = getMealUser();

        const overlay = document.createElement('div');
        overlay.id = 'mealLoginOverlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:10000;display:flex;align-items:center;justify-content:center;';

        function renderDialog() {
            const isLogin = mode === 'login';
            overlay.innerHTML = `
                <div style="background:#fff;border-radius:16px;padding:30px;max-width:380px;width:90%;box-shadow:0 10px 40px rgba(0,0,0,0.2);">
                    <h3 style="margin:0 0 6px;color:#667eea;text-align:center;">${isLogin ? '🔑 登录' : '📝 注册'}</h3>
                    <p style="margin:0 0 18px;color:#999;text-align:center;font-size:0.85em;">${isLogin ? '输入昵称和密码登录' : '创建新的打卡账号'}</p>
                    <div id="loginError" style="display:none;color:#e74c3c;text-align:center;font-size:0.85em;margin-bottom:10px;"></div>
                    <input type="text" id="loginUsername" class="form-control" placeholder="昵称（最多12字）" value="${existingUser}" style="width:100%;margin-bottom:10px;" maxlength="12">
                    <input type="password" id="loginPassword" class="form-control" placeholder="密码${isLogin ? '' : '（至少4位）'}" style="width:100%;margin-bottom:10px;">
                    ${isLogin ? '' : '<input type="password" id="loginPassword2" class="form-control" placeholder="确认密码" style="width:100%;margin-bottom:10px;">'}
                    ${isLogin ? `<label style="display:flex;align-items:center;gap:6px;font-size:0.85em;color:#666;margin-bottom:12px;cursor:pointer;">
                        <input type="checkbox" id="autoLoginCheck" ${localStorage.getItem('meal_auto_login') === 'true' ? 'checked' : ''}> 自动登录（下次自动进入）
                    </label>` : ''}
                    <div style="display:flex;gap:10px;margin-bottom:14px;">
                        <button id="loginCancelBtn" class="btn btn-secondary" style="flex:1;">取消</button>
                        <button id="loginSubmitBtn" class="btn btn-primary" style="flex:1;">${isLogin ? '登录' : '注册'}</button>
                    </div>
                    <div style="text-align:center;font-size:0.85em;">
                        ${isLogin
                            ? '还没有账号？<a href="#" id="switchToRegister" style="color:#667eea;">立即注册</a>'
                            : '已有账号？<a href="#" id="switchToLogin" style="color:#667eea;">去登录</a>'}
                    </div>
                </div>`;

            // 绑定事件
            overlay.querySelector('#loginCancelBtn').onclick = () => {
                document.body.removeChild(overlay);
                resolve(null);
            };

            overlay.querySelector('#loginSubmitBtn').onclick = async () => {
                const username = overlay.querySelector('#loginUsername').value.trim();
                const password = overlay.querySelector('#loginPassword').value;
                const errorEl = overlay.querySelector('#loginError');

                if (!username || !password) {
                    errorEl.textContent = '请填写昵称和密码';
                    errorEl.style.display = '';
                    return;
                }

                const btn = overlay.querySelector('#loginSubmitBtn');
                btn.disabled = true;
                btn.textContent = '处理中...';

                if (mode === 'register') {
                    const password2 = overlay.querySelector('#loginPassword2').value;
                    if (password.length < 4) {
                        errorEl.textContent = '密码至少4位';
                        errorEl.style.display = '';
                        btn.disabled = false;
                        btn.textContent = '注册';
                        return;
                    }
                    if (password !== password2) {
                        errorEl.textContent = '两次密码不一致';
                        errorEl.style.display = '';
                        btn.disabled = false;
                        btn.textContent = '注册';
                        return;
                    }
                    // 先调用服务器API注册，确保昵称全局唯一
                    try {
                        const resp = await fetch('/api/meal-user/register', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ username, password })
                        });
                        const data = await resp.json();
                        if (data.success) {
                            // 服务器注册成功，同步到本地缓存
                            localRegister(username, password);
                            setMealUser(username);
                            document.body.removeChild(overlay);
                            resolve(username);
                        } else {
                            errorEl.textContent = data.message || '注册失败';
                            errorEl.style.display = '';
                            btn.disabled = false;
                            btn.textContent = '注册';
                        }
                    } catch (e) {
                        // 服务器不可用，降级到本地注册
                        console.warn('服务器注册失败，使用本地注册:', e.message);
                        const result = localRegister(username, password);
                        if (result.success) {
                            setMealUser(username);
                            document.body.removeChild(overlay);
                            resolve(username);
                        } else {
                            errorEl.textContent = result.message;
                            errorEl.style.display = '';
                            btn.disabled = false;
                            btn.textContent = '注册';
                        }
                    }
                } else {
                    // 登录：优先调用服务器API验证身份
                    try {
                        const resp = await fetch('/api/meal-user/login', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ username, password })
                        });
                        const data = await resp.json();
                        if (data.success) {
                            // 服务器验证通过，同步到本地
                            localRegister(username, password);
                            if (data.goal) localSaveGoal(username, data.goal);
                            setMealUser(username);
                            const autoCheck = overlay.querySelector('#autoLoginCheck');
                            if (autoCheck && autoCheck.checked) {
                                localStorage.setItem('meal_pwd', password);
                                localStorage.setItem('meal_auto_login', 'true');
                            } else {
                                localStorage.removeItem('meal_pwd');
                                localStorage.removeItem('meal_auto_login');
                            }
                            document.body.removeChild(overlay);
                            resolve(username);
                        } else if (data.message && data.message.includes('不存在')) {
                            // 服务器上不存在，尝试本地登录（兼容旧账号）
                            const localResult = localLogin(username, password);
                            if (localResult.success) {
                                // 本地登录成功，自动注册到服务器
                                try {
                                    await fetch('/api/meal-user/register', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ username, password })
                                    });
                                } catch (regErr) {
                                    console.warn('自动同步账号到服务器失败:', regErr.message);
                                }
                                setMealUser(username);
                                const autoCheck = overlay.querySelector('#autoLoginCheck');
                                if (autoCheck && autoCheck.checked) {
                                    localStorage.setItem('meal_pwd', password);
                                    localStorage.setItem('meal_auto_login', 'true');
                                } else {
                                    localStorage.removeItem('meal_pwd');
                                    localStorage.removeItem('meal_auto_login');
                                }
                                document.body.removeChild(overlay);
                                resolve(username);
                            } else {
                                errorEl.textContent = '昵称或密码错误';
                                errorEl.style.display = '';
                                btn.disabled = false;
                                btn.textContent = '登录';
                            }
                        } else {
                            errorEl.textContent = data.message || '登录失败';
                            errorEl.style.display = '';
                            btn.disabled = false;
                            btn.textContent = '登录';
                        }
                    } catch (e) {
                        // 服务器不可用，降级到本地登录
                        console.warn('服务器登录失败，使用本地登录:', e.message);
                        const result = localLogin(username, password);
                        if (result.success) {
                            setMealUser(username);
                            const autoCheck = overlay.querySelector('#autoLoginCheck');
                            if (autoCheck && autoCheck.checked) {
                                localStorage.setItem('meal_pwd', password);
                                localStorage.setItem('meal_auto_login', 'true');
                            } else {
                                localStorage.removeItem('meal_pwd');
                                localStorage.removeItem('meal_auto_login');
                            }
                            document.body.removeChild(overlay);
                            resolve(username);
                        } else {
                            errorEl.textContent = result.message;
                            errorEl.style.display = '';
                            btn.disabled = false;
                            btn.textContent = '登录';
                        }
                    }
                }
            };

            // 密码框回车提交
            const lastPwInput = overlay.querySelector('#loginPassword2') || overlay.querySelector('#loginPassword');
            lastPwInput.onkeypress = (e) => {
                if (e.key === 'Enter') overlay.querySelector('#loginSubmitBtn').click();
            };

            // 切换模式
            const switchLink = overlay.querySelector(isLogin ? '#switchToRegister' : '#switchToLogin');
            if (switchLink) {
                switchLink.onclick = (e) => {
                    e.preventDefault();
                    mode = isLogin ? 'register' : 'login';
                    renderDialog();
                };
            }

            // 聚焦
            const pwInput = overlay.querySelector('#loginPassword');
            if (existingUser) pwInput.focus();
            else overlay.querySelector('#loginUsername').focus();
        }

        document.body.appendChild(overlay);
        renderDialog();
    });
}

async function tryAutoLogin() {
    const user = getMealUser();
    const pwd = localStorage.getItem('meal_pwd');
    if (!user || !pwd) return null;
    // 优先调用服务器API验证
    try {
        const resp = await fetch('/api/meal-user/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pwd })
        });
        const data = await resp.json();
        if (data.success) {
            if (data.goal) localSaveGoal(user, data.goal);
            return user;
        }
        localStorage.removeItem('meal_pwd');
        localStorage.removeItem('meal_auto_login');
        return null;
    } catch (e) {
        // 服务器不可用，降级到本地验证
        const result = localLogin(user, pwd);
        if (result.success) return user;
        localStorage.removeItem('meal_pwd');
        localStorage.removeItem('meal_auto_login');
        return null;
    }
}

async function startupMealLogin() {
    // 1. 尝试自动登录
    if (isAutoLogin()) {
        const user = await tryAutoLogin();
        if (user) {
            setMealUser(user); // 设置角色并更新管理员按钮
            updateMealUserDisplay();
            updateDailyScore(); // 登录后刷新评分仪表
            // 检查是否需要设置目标
            await checkAndShowGoalWizard();
            return;
        }
    }
    // 2. 没有自动登录凭据或自动登录失败 → 弹出登录弹窗
    //    用户可以选择取消（跳过登录）
    const user = await showMealLoginDialog();
    if (user) {
        updateMealUserDisplay();
        updateDailyScore(); // 登录后刷新评分仪表
        // 登录后检查是否需要设置目标
        await checkAndShowGoalWizard();
    }
}

async function checkAndShowGoalWizard() {
    const user = getMealUser();
    if (!user) return;
    const goal = localGetGoal(user);
    if (goal) {
        userGoal = goal;
        localStorage.setItem('user_goal', goal);
        updateGoalStatusBar();
        updateGoalCards();
    } else {
        showGoalSwitcher();
    }
}

function updateMealUserDisplay() {
    const user = getMealUser();
    const el = document.getElementById('mealUserDisplay');
    if (el) el.textContent = user || '未设置';
    updateAccountButton();
}

async function switchMealUser() {
    clearMealAuth();
    const name = await showMealLoginDialog();
    if (name) {
        updateMealUserDisplay();
        updateAccountButton();
        showMealCheckin();
    }
}

// ========== 账号管理面板 ==========
function updateAccountButton() {
    const user = getMealUser();
    const avatarText = document.getElementById('accountAvatarText');
    if (avatarText) {
        avatarText.textContent = user ? user.charAt(0).toUpperCase() : '?';
    }
    const statusName = document.getElementById('accountStatusName');
    if (statusName) {
        statusName.textContent = user || '未登录';
    }
}

function showAccountPanel() {
    const user = getMealUser();
    if (!user) {
        showNotification('请先登录', 'warning');
        return;
    }
    // 填充用户信息
    const avatarText = document.getElementById('accountPanelAvatarText');
    if (avatarText) avatarText.textContent = user.charAt(0).toUpperCase();

    const nameEl = document.getElementById('accountPanelName');
    if (nameEl) nameEl.textContent = user;

    // 注册时间
    const users = _loadLocalUsers();
    const userData = users[user];
    const createdEl = document.getElementById('accountPanelCreated');
    if (createdEl) {
        if (userData && userData.created_at) {
            const d = new Date(userData.created_at);
            createdEl.textContent = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
        } else {
            createdEl.textContent = '未知';
        }
    }

    // 饮食目标
    const goalEl = document.getElementById('accountPanelGoal');
    if (goalEl) {
        const goal = localGetGoal(user) || userGoal || '';
        const goalLabels = { cutting: '减脂期', bulking: '增肌期', healthy: '健康饮食' };
        goalEl.textContent = goalLabels[goal] || '未设置';
    }

    // 累计打卡天数
    const checkinEl = document.getElementById('accountPanelCheckins');
    if (checkinEl) {
        const logs = _loadLocalLogs();
        const userLogs = logs[user] || {};
        const days = Object.keys(userLogs).filter(date => {
            const day = userLogs[date];
            return (day.breakfast && day.breakfast.length > 0) ||
                   (day.lunch && day.lunch.length > 0) ||
                   (day.dinner && day.dinner.length > 0);
        }).length;
        checkinEl.textContent = `${days} 天`;
    }

    document.getElementById('accountModal').classList.add('show');
}

function closeAccountPanel() {
    document.getElementById('accountModal').classList.remove('show');
}

async function logoutAccount() {
    if (!confirm('确定要退出当前账号吗？')) return;
    closeAccountPanel();
    clearMealAuth();
    userGoal = '';
    localStorage.removeItem('user_goal');
    const name = await showMealLoginDialog();
    if (name) {
        updateMealUserDisplay();
        updateAccountButton();
        updateDailyScore();
        updateTodayCheckinBar();
    }
}

async function switchAccountFromPanel() {
    closeAccountPanel();
    clearMealAuth();
    const name = await showMealLoginDialog();
    if (name) {
        updateMealUserDisplay();
        updateAccountButton();
        updateDailyScore();
        updateTodayCheckinBar();
        showNotification(`已切换到「${name}」`, 'success');
    }
}

async function showMealCheckin() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }

    // 检查是否已登录（启动时应该已经登录过了）
    let user = getMealUser();
    if (!user) {
        // 启动时跳过了登录，现在需要登录才能打卡
        user = await showMealLoginDialog();
        if (!user) return;
    }

    document.getElementById('mealCheckinModal').classList.add('show');
    updateMealUserDisplay();

    // 显示日期
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    document.getElementById('checkinDate').textContent = `📅 ${dateStr}`;

    // 加载今日打卡数据（从本地存储）
    todayMeals = localGetMealLog(user, dateStr);

    // 加载学校菜单
    try {
        const resp = await fetch(`/api/menu/${encodeURIComponent(currentSchool)}`);
        const data = await resp.json();
        if (data.success) {
            schoolMenuItems = data.items || [];
        } else {
            schoolMenuItems = [];
        }
    } catch (e) {
        console.error('加载学校菜单失败:', e);
        schoolMenuItems = [];
    }

    updateCheckinStatus();
    switchMealTab('breakfast');
}

function closeMealCheckin() {
    document.getElementById('mealCheckinModal').classList.remove('show');
}

function switchMealTab(meal) {
    currentMealTab = meal;

    // 更新标签页样式
    document.querySelectorAll('.meal-tab').forEach(tab => tab.classList.remove('active'));
    const tabId = { breakfast: 'tabBreakfast', lunch: 'tabLunch', dinner: 'tabDinner' }[meal];
    document.getElementById(tabId).classList.add('active');

    renderMealMenu(meal);
}

function renderMealMenu(meal) {
    const container = document.getElementById('mealMenuList');
    const selected = todayMeals[meal] || [];

    if (schoolMenuItems.length === 0) {
        container.innerHTML = '<p style="color:#999;text-align:center;padding:20px;">当前学校暂无菜单数据，请手动输入菜品</p>';
    } else {
        let html = '';
        for (const dish of schoolMenuItems) {
            const checked = selected.includes(dish) ? 'checked' : '';
            html += `<label class="meal-menu-item">
                <input type="checkbox" ${checked} onchange="toggleMealDish('${meal}', '${dish.replace(/'/g, "\\'")}', this.checked)">
                <span>${dish}</span>
            </label>`;
        }
        container.innerHTML = html;
    }

    // 显示已选菜品
    updateSelectedDisplay(meal);
}

function toggleMealDish(meal, dish, checked) {
    if (!todayMeals[meal]) todayMeals[meal] = [];

    if (checked) {
        if (!todayMeals[meal].includes(dish)) {
            todayMeals[meal].push(dish);
        }
    } else {
        todayMeals[meal] = todayMeals[meal].filter(d => d !== dish);
    }

    updateSelectedDisplay(meal);
    updateCheckinStatus();
}

function addCustomDish() {
    const input = document.getElementById('customDishInput');
    const dish = input.value.trim();
    if (!dish) return;

    const meal = currentMealTab;
    if (!todayMeals[meal]) todayMeals[meal] = [];

    if (todayMeals[meal].includes(dish)) {
        showNotification('该菜品已添加', 'warning');
        return;
    }

    todayMeals[meal].push(dish);
    input.value = '';
    renderMealMenu(meal);
    updateCheckinStatus();
}

function updateSelectedDisplay(meal) {
    const selected = todayMeals[meal] || [];
    const display = document.getElementById('selectedDishesDisplay');
    if (selected.length === 0) {
        display.innerHTML = '<span style="color:#999;">尚未选择任何菜品</span>';
    } else {
        display.innerHTML = `<strong>已选 ${selected.length} 道:</strong> ${selected.join('、')}`;
    }
}

function updateCheckinStatus() {
    const bar = document.getElementById('checkinStatusBar');
    const mealNames = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' };
    let html = '';
    for (const [meal, name] of Object.entries(mealNames)) {
        const done = (todayMeals[meal] && todayMeals[meal].length > 0);
        html += `<span class="meal-status-item${done ? ' done' : ''}">${done ? '✅' : '⬜'} ${name}</span>`;
    }
    bar.innerHTML = html;
}

function updateTodayCheckinBar() {
    const user = getMealUser();
    if (!user) return;
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    const data = localGetMealLog(user, dateStr);

    // Update date display
    const dateDisplay = document.getElementById('checkinDateDisplay');
    if (dateDisplay) {
        const month = today.getMonth() + 1;
        const day = today.getDate();
        dateDisplay.textContent = `${month}月${day}日`;
    }

    // Update dots
    const meals = ['breakfast', 'lunch', 'dinner'];
    const dotIds = ['dotBreakfast', 'dotLunch', 'dotDinner'];
    let checkedCount = 0;
    for (let i = 0; i < meals.length; i++) {
        const dot = document.getElementById(dotIds[i]);
        if (dot) {
            const hasData = data[meals[i]] && data[meals[i]].length > 0;
            if (hasData) {
                dot.classList.add('active');
                checkedCount++;
            } else {
                dot.classList.remove('active');
            }
        }
    }

    // Update summary
    const summary = document.getElementById('checkinSummary');
    if (summary) {
        if (checkedCount === 0) summary.textContent = '今日还未打卡';
        else if (checkedCount === 1) summary.textContent = '已打卡 1 餐';
        else if (checkedCount === 2) summary.textContent = '已打卡 2 餐';
        else summary.textContent = '今日三餐已打卡 ✅';
    }
}

// ========== 今日饮食评分仪表 ==========
async function updateDailyScore() {
    const user = getMealUser();
    if (!user) return;

    const ring = document.getElementById('heroGaugeRing');
    const scoreEl = document.getElementById('heroScoreNumber');
    const commentEl = document.getElementById('heroComment');
    const tagsEl = document.getElementById('heroTags');
    if (!ring || !scoreEl) return;

    // 从本地存储读取今日数据
    const today = new Date().toISOString().split('T')[0];
    const todayData = localGetMealLog(user, today);
    const breakfast = todayData.breakfast || [];
    const lunch = todayData.lunch || [];
    const dinner = todayData.dinner || [];
    const allDishes = [...breakfast, ...lunch, ...dinner];
    const totalDishes = allDishes.length;

    const checkin = {
        breakfast: breakfast.length > 0,
        lunch: lunch.length > 0,
        dinner: dinner.length > 0
    };
    const mealsLogged = [checkin.breakfast, checkin.lunch, checkin.dinner].filter(Boolean).length;

    // 无数据
    if (totalDishes === 0) {
        setGaugeDisplay(0, '#bdc3c7', 'hero-score-gray', checkin, '今天还没有打卡哦，快去记录第一餐吧！', []);
        return;
    }

    // 获取目标
    const goal = localGetGoal(user) || localStorage.getItem('user_goal') || '';

    // 分析菜品
    let proteinCount = 0, vegetableCount = 0, unhealthyCount = 0, friedCount = 0;
    for (const dish of allDishes) {
        if (["鸡胸","牛肉","鱼","鸡蛋","豆腐","虾","排骨","瘦肉"].some(kw => dish.includes(kw))) proteinCount++;
        if (["西兰花","青菜","黄瓜","番茄","蔬菜","沙拉","白菜","菠菜","芹菜","萝卜"].some(kw => dish.includes(kw))) vegetableCount++;
        if (["炸鸡","红烧肉","蛋糕","薯条"].some(kw => dish.includes(kw))) { unhealthyCount++; friedCount++; }
        if (["炸","煎"].some(kw => dish.includes(kw)) && !["清炸"].some(kw => dish.includes(kw))) friedCount++;
    }

    // 评分计算
    let score = 70;
    if (goal === 'cutting') {
        if (unhealthyCount > 0) score -= unhealthyCount * 10;
        if (vegetableCount > 2) score += 10;
        if (proteinCount > 0) score += 5;
        if (mealsLogged >= 3) score += 5;
    } else if (goal === 'bulking') {
        if (proteinCount >= 3) score += 15;
        else if (proteinCount >= 1) score += 5;
        else score -= 10;
        if (totalDishes >= 4) score += 5;
    } else {
        if (mealsLogged >= 3) score += 10;
        if (vegetableCount > 0 && proteinCount > 0) score += 10;
        else if (totalDishes > 0 && vegetableCount === 0) score -= 5;
        if (friedCount > 2) score -= 5;
    }

    // 动态评语
    let comment = '';
    if (score >= 90) comment = '今天饮食非常均衡，继续保持！';
    else if (score >= 70) comment = '今天吃得不错，还可以更好哦';
    else if (score >= 50) comment = '饮食还有改善空间，注意荤素搭配';
    else comment = '今天饮食需要注意调整哦';

    if (goal === 'bulking') {
        if (proteinCount >= 3) comment = `蛋白质摄入${proteinCount}次，增肌营养跟上了！`;
        else if (proteinCount === 0) comment = '今天蛋白质摄入不足，建议加份鸡蛋或豆腐';
    } else if (goal === 'cutting') {
        if (unhealthyCount === 0 && vegetableCount > 0) comment = '清淡饮食+蔬菜，减脂节奏把握得很好！';
        else if (unhealthyCount > 0) comment = `今天有${unhealthyCount}道高油菜品，建议换成清蒸或凉拌`;
    }

    // 统计标签
    const tags = [];
    if (proteinCount > 0) tags.push({ text: `蛋白质 ${proteinCount}次`, type: 'good' });
    if (vegetableCount > 0) tags.push({ text: `蔬菜 ${vegetableCount}次`, type: 'good' });
    if (vegetableCount === 0 && totalDishes > 0) tags.push({ text: '蔬菜摄入偏少', type: 'warn' });
    if (friedCount > 0) tags.push({ text: `油炸 ${friedCount}次`, type: friedCount > 1 ? 'warn' : 'info' });
    if (mealsLogged < 3) tags.push({ text: `已打卡${mealsLogged}餐`, type: 'info' });

    score = Math.max(0, Math.min(100, score));

    // 颜色
    let color, colorClass;
    if (score >= 90) { color = '#27ae60'; colorClass = 'hero-score-green'; }
    else if (score >= 70) { color = '#2980b9'; colorClass = 'hero-score-blue'; }
    else if (score >= 50) { color = '#e67e22'; colorClass = 'hero-score-orange'; }
    else { color = '#e74c3c'; colorClass = 'hero-score-red'; }

    setGaugeDisplay(score, color, colorClass, checkin, comment, tags);
}

function setGaugeDisplay(score, color, colorClass, checkin, comment, tags) {
    const ring = document.getElementById('heroGaugeRing');
    const scoreEl = document.getElementById('heroScoreNumber');
    const commentEl = document.getElementById('heroComment');
    const tagsEl = document.getElementById('heroTags');

    if (!ring || !scoreEl) return;

    const angle = (score / 100) * 360;
    ring.style.background = `conic-gradient(${color} ${angle}deg, #e8ecf1 ${angle}deg)`;

    scoreEl.textContent = score;
    scoreEl.className = 'hero-score-number ' + colorClass;

    updateHeroCheckin('heroBreakfast', '早餐', checkin.breakfast);
    updateHeroCheckin('heroLunch', '午餐', checkin.lunch);
    updateHeroCheckin('heroDinner', '晚餐', checkin.dinner);

    if (commentEl) commentEl.textContent = comment || '';

    if (tagsEl) {
        tagsEl.innerHTML = '';
        (tags || []).forEach(tag => {
            const span = document.createElement('span');
            span.className = 'hero-tag hero-tag-' + (tag.type || 'info');
            span.textContent = tag.text;
            tagsEl.appendChild(span);
        });
    }
}

function updateHeroCheckin(elementId, mealName, isChecked) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.className = 'hero-checkin-item ' + (isChecked ? 'checked' : 'unchecked');
    el.innerHTML = mealName + ' <em>' + (isChecked ? '✅' : '✗') + '</em>';
}

async function saveCurrentMeal() {
    const today = new Date().toISOString().split('T')[0];
    const mealNames = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' };
    const user = getMealUser();

    if (!user) {
        showNotification('请先设置昵称', 'warning');
        return;
    }

    // 保存所有三餐记录
    let totalCount = 0;
    let savedMeals = [];
    for (const meal of ['breakfast', 'lunch', 'dinner']) {
        const dishes = todayMeals[meal] || [];
        localSaveMealLog(user, today, meal, dishes);
        if (dishes.length > 0) {
            totalCount += dishes.length;
            savedMeals.push(mealNames[meal]);
        }
    }

    if (savedMeals.length > 0) {
        showNotification(`已保存：${savedMeals.join('、')}（共 ${totalCount} 道菜品）`, 'success');
    } else {
        showNotification('没有需要保存的菜品', 'info');
    }
    updateTodayCheckinBar();
    updateDailyScore();
    submitScoreToLeaderboard();
}

// ========== 排行榜：提交分数 ==========
async function submitScoreToLeaderboard() {
    const user = getMealUser();
    if (!user) return;

    // 检查隐私设置
    try {
        const privacyResp = await fetch('/api/leaderboard/privacy?username=' + encodeURIComponent(user));
        const privacyData = await privacyResp.json();
        if (privacyData.success && privacyData.opted_in === false) return; // 用户选择退出排行榜
    } catch (e) {
        console.warn('获取隐私设置失败:', e.message);
        // 如果无法获取隐私设置，默认提交（首次用户未设置过）
    }

    const today = new Date().toISOString().split('T')[0];
    const todayData = localGetMealLog(user, today);
    const breakfast = todayData.breakfast || [];
    const lunch = todayData.lunch || [];
    const dinner = todayData.dinner || [];
    const allDishes = [...breakfast, ...lunch, ...dinner];
    const totalDishes = allDishes.length;
    if (totalDishes === 0) return;

    const mealsLogged = [breakfast.length > 0, lunch.length > 0, dinner.length > 0].filter(Boolean).length;
    const goal = localGetGoal(user) || localStorage.getItem('user_goal') || '';

    // 复用评分逻辑
    let proteinCount = 0, vegetableCount = 0, unhealthyCount = 0, friedCount = 0;
    for (const dish of allDishes) {
        if (["鸡胸","牛肉","鱼","鸡蛋","豆腐","虾","排骨","瘦肉"].some(kw => dish.includes(kw))) proteinCount++;
        if (["西兰花","青菜","黄瓜","番茄","蔬菜","沙拉","白菜","菠菜","芹菜","萝卜"].some(kw => dish.includes(kw))) vegetableCount++;
        if (["炸鸡","红烧肉","蛋糕","薯条"].some(kw => dish.includes(kw))) { unhealthyCount++; friedCount++; }
        if (["炸","煎"].some(kw => dish.includes(kw)) && !["清炸"].some(kw => dish.includes(kw))) friedCount++;
    }

    let score = 70;
    if (goal === 'cutting') {
        if (unhealthyCount > 0) score -= unhealthyCount * 10;
        if (vegetableCount > 2) score += 10;
        if (proteinCount > 0) score += 5;
        if (mealsLogged >= 3) score += 5;
    } else if (goal === 'bulking') {
        if (proteinCount >= 3) score += 15;
        else if (proteinCount >= 1) score += 5;
        else score -= 10;
        if (totalDishes >= 4) score += 5;
    } else {
        if (mealsLogged >= 3) score += 10;
        if (vegetableCount > 0 && proteinCount > 0) score += 10;
        else if (totalDishes > 0 && vegetableCount === 0) score -= 5;
        if (friedCount > 2) score -= 5;
    }
    score = Math.max(0, Math.min(100, score));

    try {
        await fetch('/api/leaderboard/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: user,
                date: today,
                score: score,
                school: currentSchool || '',
                meals_count: mealsLogged
            })
        });
    } catch (e) {
        console.warn('提交排行榜分数失败:', e.message);
    }
}

// ========== 周饮食报告 ==========
async function showWeeklyReport() {
    document.getElementById('weeklyReportModal').classList.add('show');
    const content = document.getElementById('reportContent');
    content.innerHTML = '<p style="text-align:center;color:#999;padding:30px;">加载中...</p>';

    const user = getMealUser();
    if (!user) {
        content.innerHTML = '<p style="color:#e74c3c;text-align:center;">请先设置昵称</p>';
        return;
    }

    const weeklyData = localGetWeeklyData(user);
    const goal = localGetGoal(user);
    const goalNames = { cutting: '减脂期', bulking: '增肌期', healthy: '保持健康' };
    const goalName = goalNames[goal] || '';

    // Compute stats
    let days_checked_in = 0, total_meals = 0, total_dishes = 0;
    let dish_counter = {}, category_counter = {};
    let daily_summary = [];
    let meal_completion = { breakfast: 0, lunch: 0, dinner: 0 };
    let daily_goal_metric = [];

    for (const day of weeklyData) {
        let day_meals = 0, day_dish_count = 0, day_protein = 0, day_unhealthy = 0;
        for (const mealType of ["breakfast", "lunch", "dinner"]) {
            const dishes = day.data[mealType] || [];
            if (dishes.length > 0) {
                day_meals++;
                meal_completion[mealType]++;
                for (const dish of dishes) {
                    day_dish_count++;
                    total_dishes++;
                    dish_counter[dish] = (dish_counter[dish] || 0) + 1;
                    // Keyword-based classification
                    if (["鸡胸","牛肉","鱼","鸡蛋","豆腐","虾"].some(kw => dish.includes(kw))) day_protein++;
                    if (["炸鸡","红烧肉","蛋糕","薯条"].some(kw => dish.includes(kw))) day_unhealthy++;
                }
            }
        }
        if (day_meals > 0) days_checked_in++;
        total_meals += day_meals;

        const metricVal = goal === 'cutting' ? day_unhealthy : goal === 'bulking' ? day_protein : day_meals;
        daily_goal_metric.push(metricVal);

        const d = new Date(day.date);
        daily_summary.push({
            date: day.date,
            weekday: ["一","二","三","四","五","六","日"][d.getDay() === 0 ? 6 : d.getDay() - 1],
            meals: day_meals,
            dish_count: day_dish_count
        });
    }

    // Consecutive days
    let consecutive_days = 0;
    for (let i = weeklyData.length - 1; i >= 0; i--) {
        const day = weeklyData[i];
        const hasMeals = ["breakfast","lunch","dinner"].some(m => (day.data[m] || []).length > 0);
        if (hasMeals) consecutive_days++;
        else break;
    }

    const sorted_dishes = Object.entries(dish_counter).sort((a,b) => b[1]-a[1]).slice(0,5);
    const top_dishes = sorted_dishes.map(([name,count]) => ({name, count}));

    // Insights
    let insights = [];
    if (consecutive_days >= 3) insights.push(`你已经连续打卡 ${consecutive_days} 天，继续保持！`);
    if (top_dishes.length && top_dishes[0].count >= 3) insights.push(`「${top_dishes[0].name}」是你本周最爱，吃了 ${top_dishes[0].count} 次`);
    if (!insights.length) {
        if (days_checked_in === 0) insights.push('本周还没有打卡记录，从今天开始记录吧！');
        else if (days_checked_in < 3) insights.push(`本周打卡 ${days_checked_in} 天，坚持每天记录会更有参考价值`);
    }

    renderReport({
        days_checked_in, total_meals, total_dishes, top_dishes,
        category_distribution: category_counter,
        daily_summary, daily_goal_metric, meal_completion,
        consecutive_days, insights: insights.slice(0,3),
        goal: goalName
    });
}

function closeWeeklyReport() {
    document.getElementById('weeklyReportModal').classList.remove('show');
}

function renderReport(data) {
    const content = document.getElementById('reportContent');

    // 如果没有数据
    if (data.days_checked_in === 0) {
        content.innerHTML = `
            <div class="report-empty">
                <span class="empty-icon">📭</span>
                <p>过去 7 天还没有打卡记录</p>
                <p style="font-size:0.9em;margin-top:8px;">点击"今日打卡"开始记录你的饮食吧！</p>
            </div>`;
        return;
    }

    let html = '';

    // 概览卡片
    const cardColors = [
        'linear-gradient(135deg, #667eea, #764ba2)',
        'linear-gradient(135deg, #11998e, #38ef7d)',
        'linear-gradient(135deg, #ee9ca7, #ffdde1)'
    ];
    html += '<div class="report-stat-cards">';
    html += `<div class="report-stat-card" style="background:${cardColors[0]}">
        <span class="stat-number">${data.days_checked_in}</span>
        <span class="stat-label">打卡天数 / 7天</span>
    </div>`;
    html += `<div class="report-stat-card" style="background:${cardColors[1]}">
        <span class="stat-number">${data.total_meals}</span>
        <span class="stat-label">总餐数</span>
    </div>`;
    html += `<div class="report-stat-card" style="background:${cardColors[2]}">
        <span class="stat-number">${data.total_dishes}</span>
        <span class="stat-label">总菜品</span>
    </div>`;
    html += '</div>';

    // 目标进度（如果有目标数据）
    if (data.goal && data.daily_goal_metric) {
        html += '<div class="report-section-title">🎯 本周目标趋势</div>';
        html += '<div class="report-chart-container"><canvas id="goalTrendChart" width="400" height="200"></canvas></div>';
    }

    // 打卡日历
    html += '<div class="report-section-title">📅 打卡日历</div>';
    html += '<div class="report-calendar">';
    for (const day of data.daily_summary) {
        const hasData = day.meals > 0;
        const shortDate = day.date.slice(5); // MM-DD
        html += `<div class="report-day${hasData ? ' has-data' : ''}">
            <span class="day-label">周${day.weekday}</span>
            <span class="day-date">${shortDate}</span>
            <div class="day-dots">
                <span class="day-dot${day.meals >= 1 ? ' filled' : ''}" title="早餐"></span>
                <span class="day-dot${day.meals >= 2 ? ' filled' : ''}" title="午餐"></span>
                <span class="day-dot${day.meals >= 3 ? ' filled' : ''}" title="晚餐"></span>
            </div>
        </div>`;
    }
    html += '</div>';

    // 最常吃菜品
    if (data.top_dishes.length > 0) {
        html += '<div class="report-section-title">🍽️ 最常吃的菜</div>';
        html += '<div class="report-bar-chart">';
        const maxCount = data.top_dishes[0].count;
        for (const dish of data.top_dishes) {
            const pct = (dish.count / maxCount * 100).toFixed(0);
            html += `<div class="report-bar-row">
                <span class="report-bar-label" title="${dish.name}">${dish.name}</span>
                <div class="report-bar-track">
                    <div class="report-bar-fill" style="width:${pct}%"></div>
                </div>
                <span class="report-bar-count">${dish.count}次</span>
            </div>`;
        }
        html += '</div>';
    }

    // 营养分类分布
    const catEntries = Object.entries(data.category_distribution);
    if (catEntries.length > 0) {
        html += '<div class="report-section-title">🥗 营养分类分布</div>';
        html += '<div class="report-bar-chart">';
        const maxCat = catEntries[0][1];
        for (const [cat, count] of catEntries) {
            const pct = (count / maxCat * 100).toFixed(0);
            html += `<div class="report-bar-row">
                <span class="report-bar-label">${cat}</span>
                <div class="report-bar-track">
                    <div class="report-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,#11998e,#38ef7d)"></div>
                </div>
                <span class="report-bar-count">${count}次</span>
            </div>`;
        }
        html += '</div>';
    }

    // 各餐完成率
    html += '<div class="report-section-title">📊 各餐打卡情况</div>';
    const mealLabels = { breakfast: '🌅 早餐', lunch: '☀️ 午餐', dinner: '🌙 晚餐' };
    html += '<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">';
    for (const [meal, count] of Object.entries(data.meal_completion)) {
        const pct = Math.round(count / 7 * 100);
        html += `<div style="text-align:center;padding:10px 15px;background:#f8f9fa;border-radius:8px;min-width:80px;">
            <div style="font-size:0.85em;color:#666;">${mealLabels[meal]}</div>
            <div style="font-size:1.5em;font-weight:bold;color:#667eea;">${pct}%</div>
            <div style="font-size:0.75em;color:#999;">${count}/7天</div>
        </div>`;
    }
    html += '</div>';

    // 习惯洞察
    if (data.insights && data.insights.length > 0) {
        html += '<div class="report-section-title">💡 饮食洞察</div>';
        html += '<div class="insights-container">';
        for (const insight of data.insights) {
            html += `<div class="insight-card">${insight}</div>`;
        }
        html += '</div>';
    }

    content.innerHTML = html;

    // 渲染 Chart.js 折线图
    if (data.goal && data.daily_goal_metric) {
        renderGoalTrendChart(data);
    }
}

function renderGoalTrendChart(data) {
    const ctx = document.getElementById('goalTrendChart');
    if (!ctx) return;

    const labels = data.daily_summary.map(d => d.date.slice(5)); // MM-DD
    const metricData = data.daily_goal_metric;

    let label = '打卡餐数';
    let borderColor = '#667eea';
    let backgroundColor = 'rgba(102, 126, 234, 0.2)';

    if (data.goal === 'cutting') {
        label = '不健康菜品数';
        borderColor = '#ee9ca7';
        backgroundColor = 'rgba(238, 156, 167, 0.2)';
    } else if (data.goal === 'bulking') {
        label = '高蛋白菜品数';
        borderColor = '#11998e';
        backgroundColor = 'rgba(17, 153, 142, 0.2)';
    }

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: metricData,
                borderColor: borderColor,
                backgroundColor: backgroundColor,
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

// ========== 每日简报 ==========
async function showDailyBriefing() {
    document.getElementById('briefingModal').classList.add('show');
    const content = document.getElementById('briefingContent');
    const user = getMealUser();
    if (!user) {
        content.innerHTML = '<p style="color:#e74c3c;text-align:center;">请先设置昵称</p>';
        return;
    }

    const today = new Date().toISOString().split('T')[0];
    const todayData = localGetMealLog(user, today);
    const allDishes = [...(todayData.breakfast||[]), ...(todayData.lunch||[]), ...(todayData.dinner||[])];
    const mealCounts = { breakfast: (todayData.breakfast||[]).length, lunch: (todayData.lunch||[]).length, dinner: (todayData.dinner||[]).length };
    const totalDishes = allDishes.length;
    const mealsLogged = Object.values(mealCounts).filter(v => v > 0).length;
    const goalNames = { cutting: '减脂期', bulking: '增肌期', healthy: '保持健康' };
    const goal = localGetGoal(user);
    const goalName = goalNames[goal] || '';

    if (totalDishes === 0) {
        content.innerHTML = `<div style="text-align:center;padding:30px;color:#999;">
            <p>今天还没有打卡记录</p><p style="font-size:0.9em;margin-top:8px;">快去记录今天吃了什么吧！</p></div>`;
        return;
    }

    let proteinCount = 0, unhealthyCount = 0, vegetableCount = 0;
    for (const dish of allDishes) {
        if (["鸡胸","牛肉","鱼","鸡蛋","豆腐","虾"].some(kw => dish.includes(kw))) proteinCount++;
        if (["炸鸡","红烧肉","蛋糕","薯条"].some(kw => dish.includes(kw))) unhealthyCount++;
        if (["西兰花","青菜","黄瓜","番茄","蔬菜","沙拉"].some(kw => dish.includes(kw))) vegetableCount++;
    }

    let score = 70, tip = '', details = [];
    if (goal === 'cutting') {
        if (unhealthyCount > 0) { score -= unhealthyCount * 10; tip = `今天有 ${unhealthyCount} 道高油菜品，建议明天换成清蒸或凉拌`; }
        if (vegetableCount > 2) { score += 10; details.push(`蔬菜摄入 ${vegetableCount} 次，继续保持`); }
        if (proteinCount > 0) { score += 5; details.push(`蛋白质摄入 ${proteinCount} 次`); }
        if (!tip) tip = unhealthyCount === 0 ? '今天饮食很清淡，减脂节奏把握得不错！' : '注意控制油脂摄入';
    } else if (goal === 'bulking') {
        if (proteinCount >= 3) { score += 15; tip = `蛋白质摄入 ${proteinCount} 次，增肌营养跟上了！`; }
        else if (proteinCount >= 1) { score += 5; tip = `蛋白质摄入 ${proteinCount} 次，还可以多吃点鸡蛋和鸡胸肉`; }
        else { score -= 10; tip = '今天蛋白质摄入不足，建议加一份鸡蛋或豆腐'; }
    } else {
        if (mealsLogged >= 3) { score += 10; details.push('三餐都有记录，饮食规律'); }
        if (vegetableCount > 0 && proteinCount > 0) { score += 10; tip = '荤素搭配不错，继续保持！'; }
        else if (totalDishes > 0) tip = '记得荤素搭配，每餐都有蔬菜和蛋白质最理想';
    }
    score = Math.max(0, Math.min(100, score));

    let html = `<div style="text-align:center;padding:20px;background:linear-gradient(135deg,#667eea22,#764ba222);border-radius:12px;margin-bottom:15px;">
        <div style="font-size:2.5em;font-weight:bold;color:#667eea;">${score}</div>
        <div style="color:#888;font-size:0.9em;">今日饮食评分</div>
        ${goalName ? `<div style="margin-top:5px;color:#667eea;font-size:0.85em;">🎯 ${goalName}</div>` : ''}
    </div>
    <p style="text-align:center;font-size:1em;color:#444;margin-bottom:15px;padding:0 10px;">${tip}</p>
    <div style="display:flex;gap:10px;justify-content:center;margin-bottom:15px;flex-wrap:wrap;">
        <div style="text-align:center;padding:8px 15px;background:#f0f7ff;border-radius:8px;"><div style="font-size:1.3em;font-weight:bold;color:#667eea;">${totalDishes}</div><div style="font-size:0.75em;color:#888;">总菜品</div></div>
        <div style="text-align:center;padding:8px 15px;background:#f0fff4;border-radius:8px;"><div style="font-size:1.3em;font-weight:bold;color:#27ae60;">${proteinCount}</div><div style="font-size:0.75em;color:#888;">高蛋白</div></div>
        <div style="text-align:center;padding:8px 15px;background:#fff9e6;border-radius:8px;"><div style="font-size:1.3em;font-weight:bold;color:#f39c12;">${unhealthyCount}</div><div style="font-size:0.75em;color:#888;">高油菜品</div></div>
        <div style="text-align:center;padding:8px 15px;background:#f0fff0;border-radius:8px;"><div style="font-size:1.3em;font-weight:bold;color:#2ecc71;">${vegetableCount}</div><div style="font-size:0.75em;color:#888;">蔬菜</div></div>
    </div>`;
    if (details.length) {
        html += '<div style="padding:10px 15px;background:#f8f9fa;border-radius:8px;">';
        html += details.map(d => `<p style="margin:4px 0;color:#666;font-size:0.9em;">• ${d}</p>`).join('');
        html += '</div>';
    }
    content.innerHTML = html;
}

function closeBriefing() {
    document.getElementById('briefingModal').classList.remove('show');
}

function renderBriefing(data) {
    const content = document.getElementById('briefingContent');

    if (data.total_dishes === 0) {
        content.innerHTML = `
            <div class="briefing-empty">
                <span class="empty-icon">🍽️</span>
                <p>${data.message || '今天还没有打卡记录'}</p>
            </div>`;
        return;
    }

    let html = '';

    // 评分卡片
    const scoreColor = data.score >= 80 ? '#11998e' : data.score >= 60 ? '#f39c12' : '#e74c3c';
    html += `<div class="briefing-score-card" style="background: linear-gradient(135deg, ${scoreColor}22, ${scoreColor}44);">
        <div class="briefing-score" style="color: ${scoreColor};">${data.score}</div>
        <div class="briefing-score-label">今日饮食评分</div>
    </div>`;

    // 目标提示
    if (data.goal) {
        html += `<div class="briefing-goal">当前目标：${data.goal}</div>`;
    }

    // 主要建议
    if (data.tip) {
        html += `<div class="briefing-tip">💡 ${data.tip}</div>`;
    }

    // 详细数据
    html += '<div class="briefing-details">';
    html += `<div class="briefing-detail-row">
        <span>总菜品数</span>
        <span class="briefing-detail-value">${data.total_dishes}</span>
    </div>`;
    html += `<div class="briefing-detail-row">
        <span>打卡餐数</span>
        <span class="briefing-detail-value">${data.meals_logged}/3</span>
    </div>`;

    if (data.protein_count !== undefined) {
        html += `<div class="briefing-detail-row">
            <span>高蛋白菜品</span>
            <span class="briefing-detail-value">${data.protein_count} 次</span>
        </div>`;
    }
    if (data.unhealthy_count !== undefined) {
        html += `<div class="briefing-detail-row">
            <span>高油菜品</span>
            <span class="briefing-detail-value" style="color: ${data.unhealthy_count > 2 ? '#e74c3c' : '#666'};">${data.unhealthy_count} 次</span>
        </div>`;
    }
    if (data.vegetable_count !== undefined) {
        html += `<div class="briefing-detail-row">
            <span>蔬菜菜品</span>
            <span class="briefing-detail-value" style="color: #11998e;">${data.vegetable_count} 次</span>
        </div>`;
    }
    html += '</div>';

    // 烹饪方式分布
    if (data.cooking_methods && Object.keys(data.cooking_methods).length > 0) {
        html += '<div class="briefing-section-title">烹饪方式分布</div>';
        html += '<div class="briefing-cooking-methods">';
        const maxCount = Math.max(...Object.values(data.cooking_methods));
        for (const [method, count] of Object.entries(data.cooking_methods)) {
            const pct = (count / maxCount * 100).toFixed(0);
            html += `<div class="cooking-method-row">
                <span class="cooking-method-label">${method}</span>
                <div class="cooking-method-bar">
                    <div class="cooking-method-fill" style="width:${pct}%"></div>
                </div>
                <span class="cooking-method-count">${count}</span>
            </div>`;
        }
        html += '</div>';
    }

    // 额外建议
    if (data.details && data.details.length > 0) {
        html += '<div class="briefing-extra-tips">';
        for (const detail of data.details) {
            html += `<div class="briefing-extra-tip">• ${detail}</div>`;
        }
        html += '</div>';
    }

    content.innerHTML = html;
}

// ========== 高校食堂图鉴 ==========
async function showGallery() {
    const modal = document.getElementById('galleryModal');
    const loading = document.getElementById('galleryLoading');
    const grid = document.getElementById('galleryGrid');

    modal.classList.add('show');
    loading.style.display = '';
    grid.style.display = 'none';

    try {
        const resp = await fetch('/api/curated-database');
        const data = await resp.json();
        if (data.success) {
            document.getElementById('gallerySchoolCount').textContent = data.count;
            renderGallery(data.schools);
            loading.style.display = 'none';
            grid.style.display = '';
        } else {
            loading.textContent = '加载失败';
        }
    } catch (e) {
        console.error('加载图鉴失败:', e);
        loading.textContent = '网络错误，请重试';
    }
}

function closeGallery() {
    document.getElementById('galleryModal').classList.remove('show');
}

function renderGallery(schools) {
    const grid = document.getElementById('galleryGrid');
    const confLabels = { high: '高', medium: '中', low: '低' };
    const confClasses = { high: 'gallery-confidence-high', medium: 'gallery-confidence-medium', low: 'gallery-confidence-low' };

    let html = '';
    for (const [name, info] of Object.entries(schools)) {
        const dishes = info.dishes || [];
        const source = info.source || '';
        const confidence = info.confidence || 'medium';

        html += `<div class="gallery-card">
            <div class="gallery-school-header">
                <span class="gallery-school-name">${name}</span>
                <span class="gallery-confidence ${confClasses[confidence] || ''}">${confLabels[confidence] || '中'}</span>
            </div>
            <div class="gallery-dishes">`;

        for (const dish of dishes) {
            html += `<span class="gallery-dish-tag">${dish}</span>`;
        }

        html += `</div>`;

        if (source) {
            html += `<div class="gallery-source">${source}</div>`;
        }

        html += `</div>`;
    }

    grid.innerHTML = html;
}


// ========== 管理员功能 ==========
// ========== 开发者模式 ==========
let devModeVerified = false; // 当前会话是否已验证

function showDevModeDialog() {
    if (devModeVerified) {
        // 已验证，直接打开管理面板
        showAdminPanel();
        return;
    }
    // 显示密码输入弹窗
    const overlay = document.createElement('div');
    overlay.id = 'devPasswordOverlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:10000;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `
        <div style="background:white;border-radius:16px;padding:30px;max-width:360px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
            <h3 style="text-align:center;color:#667eea;margin-bottom:20px;">🔧 开发者模式</h3>
            <p style="text-align:center;color:#888;font-size:0.9em;margin-bottom:15px;">请输入开发者密码</p>
            <input type="password" id="devPasswordInput" placeholder="密码" style="width:100%;padding:12px 16px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;outline:none;box-sizing:border-box;margin-bottom:15px;" onkeypress="if(event.key==='Enter')verifyDevPassword()">
            <p id="devPasswordError" style="color:#ff4444;font-size:0.85em;text-align:center;display:none;margin-bottom:10px;"></p>
            <div style="display:flex;gap:10px;">
                <button onclick="verifyDevPassword()" style="flex:1;padding:12px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border:none;border-radius:10px;font-size:1em;cursor:pointer;font-weight:600;">验证</button>
                <button onclick="closeDevDialog()" style="flex:1;padding:12px;background:#f0f0f0;color:#666;border:none;border-radius:10px;font-size:1em;cursor:pointer;">取消</button>
            </div>
            <p style="text-align:center;margin-top:15px;"><a href="javascript:void(0)" onclick="showChangePasswordDialog()" style="color:#999;font-size:0.8em;text-decoration:none;">修改密码</a></p>
        </div>
    `;
    document.body.appendChild(overlay);
    setTimeout(() => document.getElementById('devPasswordInput').focus(), 100);
}

function closeDevDialog() {
    const overlay = document.getElementById('devPasswordOverlay');
    if (overlay) overlay.remove();
}

async function verifyDevPassword() {
    const input = document.getElementById('devPasswordInput');
    const errorEl = document.getElementById('devPasswordError');
    const password = input.value.trim();
    if (!password) {
        errorEl.textContent = '请输入密码';
        errorEl.style.display = 'block';
        return;
    }
    try {
        const resp = await fetch('/api/dev/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password })
        });
        const data = await resp.json();
        if (data.success) {
            devModeVerified = true;
            closeDevDialog();
            showNotification('开发者模式已激活', 'success');
            showAdminPanel();
        } else {
            errorEl.textContent = data.message || '密码错误';
            errorEl.style.display = 'block';
            input.value = '';
            input.focus();
        }
    } catch(e) {
        errorEl.textContent = '验证失败，请重试';
        errorEl.style.display = 'block';
    }
}

async function showChangePasswordDialog() {
    // 先获取安全问题
    let question = '创始人的外号';
    try {
        const resp = await fetch('/api/dev/question');
        const data = await resp.json();
        if (data.success) question = data.question;
    } catch(e) {}
    
    closeDevDialog();
    const overlay = document.createElement('div');
    overlay.id = 'devPasswordOverlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:10000;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `
        <div style="background:white;border-radius:16px;padding:30px;max-width:380px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
            <h3 style="text-align:center;color:#667eea;margin-bottom:20px;">🔑 修改开发者密码</h3>
            <p style="color:#555;font-size:0.9em;margin-bottom:8px;">安全问题：${question}</p>
            <input type="text" id="devAnswerInput" placeholder="回答问题" style="width:100%;padding:12px 16px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;outline:none;box-sizing:border-box;margin-bottom:12px;">
            <input type="password" id="devNewPasswordInput" placeholder="新密码（至少4位）" style="width:100%;padding:12px 16px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;outline:none;box-sizing:border-box;margin-bottom:15px;">
            <p id="devChangePwError" style="color:#ff4444;font-size:0.85em;text-align:center;display:none;margin-bottom:10px;"></p>
            <div style="display:flex;gap:10px;">
                <button onclick="submitChangePassword()" style="flex:1;padding:12px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border:none;border-radius:10px;font-size:1em;cursor:pointer;font-weight:600;">确认修改</button>
                <button onclick="closeDevDialog()" style="flex:1;padding:12px;background:#f0f0f0;color:#666;border:none;border-radius:10px;font-size:1em;cursor:pointer;">返回</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

async function submitChangePassword() {
    const answer = document.getElementById('devAnswerInput').value.trim();
    const newPw = document.getElementById('devNewPasswordInput').value.trim();
    const errorEl = document.getElementById('devChangePwError');
    if (!answer) { errorEl.textContent = '请回答安全问题'; errorEl.style.display = 'block'; return; }
    if (!newPw || newPw.length < 4) { errorEl.textContent = '新密码至少4位'; errorEl.style.display = 'block'; return; }
    try {
        const resp = await fetch('/api/dev/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer: answer, new_password: newPw })
        });
        const data = await resp.json();
        if (data.success) {
            closeDevDialog();
            showNotification('密码修改成功！', 'success');
        } else {
            errorEl.textContent = data.message || '修改失败';
            errorEl.style.display = 'block';
        }
    } catch(e) {
        errorEl.textContent = '请求失败';
        errorEl.style.display = 'block';
    }
}

function showAdminPanel() {
    const modal = document.getElementById('adminModal');
    modal.classList.add('show');
    const user = getMealUser();
    document.getElementById('adminUsernameDisplay').textContent = user ? user : '';
    switchAdminTab('menu');
}

function closeAdminPanel() {
    document.getElementById('adminModal').classList.remove('show');
}

function switchAdminTab(tabName) {
    // 更新标签按钮状态
    document.querySelectorAll('.admin-tab').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // 更新标签内容显示
    document.querySelectorAll('.admin-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById('adminTab' + tabName.charAt(0).toUpperCase() + tabName.slice(1)).classList.add('active');
    
    // 加载对应标签页内容
    if (tabName === 'menu') {
        loadAdminMenus();
    } else if (tabName === 'users') {
        loadAdminUsers();
    } else if (tabName === 'admins') {
        loadAdminAdmins();
    } else if (tabName === 'stats') {
        loadAdminStats();
    }
}

async function loadAdminMenus() {
    const container = document.getElementById('adminMenuList');
    container.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">加载中...</div>';
    
    try {
        const resp = await fetch('/api/schools');
        const data = await resp.json();
        
        if (data.success && data.schools.length > 0) {
            let html = '';
            for (const school of data.schools) {
                html += `
                    <div class="admin-school-item">
                        <div class="admin-school-name">${school}</div>
                        <div class="admin-school-actions">
                            <button onclick="adminResetMenu('${school}')" class="btn btn-small btn-warning" title="重置为精选菜单">🔄 重置</button>
                            <button onclick="adminClearMenu('${school}')" class="btn btn-small btn-danger" title="清空菜单">️ 清空</button>
                            <button onclick="adminEditMenu('${school}')" class="btn btn-small btn-primary" title="编辑菜单">️ 编辑</button>
                        </div>
                    </div>
                `;
            }
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">暂无学校数据</div>';
        }
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; padding:20px; color:#e74c3c;">加载失败</div>';
    }
}

async function adminResetMenu(schoolName) {
    if (!confirm(`确定要将「${schoolName}」的菜单重置为精选版本吗？`)) return;
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch('/api/admin/menu/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user.username, school_name: schoolName })
        });
        const data = await resp.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            loadAdminMenus();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (e) {
        showNotification('操作失败', 'error');
    }
}

async function adminClearMenu(schoolName) {
    if (!confirm(`确定要清空「${schoolName}」的菜单吗？此操作不可恢复！`)) return;
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch('/api/admin/menu/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user.username, school_name: schoolName })
        });
        const data = await resp.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            loadAdminMenus();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (e) {
        showNotification('操作失败', 'error');
    }
}

function adminEditMenu(schoolName) {
    // 复用现有的菜单编辑器
    currentSchool = schoolName;
    showMenuEditor();
}

async function loadAdminUsers() {
    const container = document.getElementById('adminUserList');
    container.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">加载中...</div>';
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch(`/api/admin/users?username=${encodeURIComponent(user.username)}`);
        const data = await resp.json();
        
        if (data.success && data.users.length > 0) {
            let html = '';
            for (const u of data.users) {
                const roleBadge = u.role === 'admin' ? '<span class="role-badge admin">管理员</span>' : '';
                html += `
                    <div class="admin-user-item">
                        <div class="admin-user-info">
                            <div class="admin-user-name">${u.username} ${roleBadge}</div>
                            <div class="admin-user-meta">注册：${u.created_at ? u.created_at.split('T')[0] : '未知'} | 打卡：${u.meal_count} 次</div>
                        </div>
                        <div class="admin-user-actions">
                            ${u.username !== user.username ? `<button onclick="adminDeleteUser('${u.username}')" class="btn btn-small btn-danger">删除</button>` : ''}
                        </div>
                    </div>
                `;
            }
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">暂无用户</div>';
        }
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; padding:20px; color:#e74c3c;">加载失败</div>';
    }
}

async function adminDeleteUser(username) {
    if (!confirm(`确定要删除用户「${username}」及其所有数据吗？此操作不可恢复！`)) return;
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch(`/api/admin/user/${encodeURIComponent(username)}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user.username })
        });
        const data = await resp.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            loadAdminUsers();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (e) {
        showNotification('操作失败', 'error');
    }
}

async function loadAdminAdmins() {
    const container = document.getElementById('adminAdminList');
    container.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">加载中...</div>';
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch(`/api/admin/users?username=${encodeURIComponent(user.username)}`);
        const data = await resp.json();
        
        if (data.success) {
            const admins = data.users.filter(u => u.role === 'admin');
            if (admins.length > 0) {
                let html = '';
                for (const u of admins) {
                    html += `
                        <div class="admin-user-item">
                            <div class="admin-user-info">
                                <div class="admin-user-name">${u.username} <span class="role-badge admin">管理员</span></div>
                            </div>
                            <div class="admin-user-actions">
                                ${u.username !== user.username ? `<button onclick="adminRemoveAdmin('${u.username}')" class="btn btn-small btn-warning">移除</button>` : '<span style="color:#999;font-size:0.85em;">(自己)</span>'}
                            </div>
                        </div>
                    `;
                }
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">暂无管理员</div>';
            }
        }
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; padding:20px; color:#e74c3c;">加载失败</div>';
    }
}

async function adminAddAdmin() {
    const input = document.getElementById('addAdminUsername');
    const targetUsername = input.value.trim();
    
    if (!targetUsername) {
        showNotification('请输入用户名', 'warning');
        return;
    }
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch('/api/admin/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user.username, target_username: targetUsername })
        });
        const data = await resp.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            input.value = '';
            loadAdminAdmins();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (e) {
        showNotification('操作失败', 'error');
    }
}

async function adminRemoveAdmin(username) {
    if (!confirm(`确定要移除「${username}」的管理员权限吗？`)) return;
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch('/api/admin/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user.username, target_username: username })
        });
        const data = await resp.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            loadAdminAdmins();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (e) {
        showNotification('操作失败', 'error');
    }
}

async function loadAdminStats() {
    const container = document.getElementById('adminStatsContent');
    container.innerHTML = '<div style="text-align:center; padding:20px; color:#999;">加载中...</div>';
    
    const user = getMealUser();
    if (!user) return;
    
    try {
        const resp = await fetch(`/api/admin/stats?username=${encodeURIComponent(user.username)}`);
        const data = await resp.json();
        
        if (data.success) {
            const s = data.stats;
            container.innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${s.school_count}</div>
                    <div class="stat-label">学校数量</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.user_count}</div>
                    <div class="stat-label">用户总数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.admin_count}</div>
                    <div class="stat-label">管理员数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.total_meal_logs}</div>
                    <div class="stat-label">打卡记录</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.total_dishes_logged}</div>
                    <div class="stat-label">菜品记录</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${s.dish_tags_count}</div>
                    <div class="stat-label">菜品标签</div>
                </div>
            `;
        } else {
            container.innerHTML = '<div style="text-align:center; padding:20px; color:#e74c3c;">加载失败</div>';
        }
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; padding:20px; color:#e74c3c;">加载失败</div>';
    }
}

// ========== 排行榜功能 ==========
let currentLeaderboardTab = 'daily';

async function showLeaderboard() {
    const modal = document.getElementById('leaderboardModal');
    modal.classList.add('show');
    await loadPrivacyPreference();
    await loadLeaderboardData();
}

function closeLeaderboard() {
    document.getElementById('leaderboardModal').classList.remove('show');
}

function switchLeaderboardTab(period) {
    currentLeaderboardTab = period;
    document.querySelectorAll('.lb-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.period === period);
    });
    loadLeaderboardData();
}

async function loadLeaderboardData() {
    const listEl = document.getElementById('leaderboardList');
    listEl.innerHTML = '<div style="text-align:center;padding:30px;color:#999;">加载中...</div>';

    const user = getMealUser();

    try {
        let url;
        if (currentLeaderboardTab === 'streak') {
            url = '/api/leaderboard/streak';
        } else {
            url = '/api/leaderboard?period=' + currentLeaderboardTab;
        }

        const resp = await fetch(url);
        const data = await resp.json();

        if (!data.success) {
            listEl.innerHTML = '<div class="lb-empty"><span class="empty-icon">😕</span><p>加载失败</p></div>';
            return;
        }

        renderLeaderboardList(data.rankings || [], user);
    } catch (e) {
        console.warn('加载排行榜失败:', e.message);
        listEl.innerHTML = '<div class="lb-empty"><span class="empty-icon">📡</span><p>网络错误，请稍后重试</p></div>';
    }
}

function renderLeaderboardList(rankings, currentUser) {
    const listEl = document.getElementById('leaderboardList');

    if (!rankings || rankings.length === 0) {
        listEl.innerHTML = '<div class="lb-empty"><span class="empty-icon">🏆</span><p>暂无排行数据</p><p style="font-size:0.85em;margin-top:6px;">打卡后自动上榜！</p></div>';
        return;
    }

    const medals = ['🥇', '🥈', '🥉'];
    let html = '';

    rankings.forEach(function(entry, idx) {
        const rank = idx + 1;
        const isMe = currentUser && entry.username === currentUser;
        let topClass = rank <= 3 ? 'top-' + rank : '';
        let meClass = isMe ? 'is-me' : '';

        let rankDisplay;
        if (rank <= 3) {
            rankDisplay = '<span class="medal">' + medals[idx] + '</span>';
        } else {
            rankDisplay = rank;
        }

        let scoreDisplay;
        if (currentLeaderboardTab === 'streak') {
            scoreDisplay = '<div class="lb-streak"><span class="streak-fire">🔥</span>' + entry.streak_days + '天</div>';
        } else {
            var unit = currentLeaderboardTab === 'daily' ? '分' : '分/天';
            scoreDisplay = '<div class="lb-score">' + entry.score + '<small>' + unit + '</small></div>';
        }

        html += '<div class="lb-item ' + topClass + ' ' + meClass + '">'
            + '<div class="lb-rank">' + rankDisplay + '</div>'
            + '<div class="lb-info">'
            + '<div class="lb-name">' + escapeHtml(entry.username) + (isMe ? ' (我)' : '') + '</div>'
            + '</div>'
            + scoreDisplay
            + '</div>';
    });

    listEl.innerHTML = html;
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function toggleLeaderboardPrivacy() {
    var toggle = document.getElementById('leaderboardPrivacyToggle');
    var optedIn = toggle.checked;
    var user = getMealUser();
    if (!user) return;

    try {
        var resp = await fetch('/api/leaderboard/privacy', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, opted_in: optedIn })
        });
        var data = await resp.json();
        if (data.success) {
            showNotification(optedIn ? '已加入排行榜' : '已从排行榜隐藏', 'success');
        } else {
            showNotification('设置失败，请重试', 'error');
            toggle.checked = !optedIn;
        }
    } catch (e) {
        console.warn('设置隐私失败:', e.message);
        showNotification('网络错误', 'error');
        toggle.checked = !optedIn;
    }
}

async function loadPrivacyPreference() {
    var user = getMealUser();
    if (!user) return;
    try {
        var resp = await fetch('/api/leaderboard/privacy?username=' + encodeURIComponent(user));
        var data = await resp.json();
        if (data.success) {
            var toggle = document.getElementById('leaderboardPrivacyToggle');
            if (toggle) toggle.checked = data.opted_in !== false;
        }
    } catch (e) {
        console.warn('加载隐私设置失败:', e.message);
    }
}
