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

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    loadUniversitiesList(); // 加载大学列表
    checkFirstTimeUse(); // 检查是否首次使用
    loadAllergies(); // 恢复过敏设置
    loadUserGoal(); // 加载用户目标
    updateTodayCheckinBar(); // 更新顶部打卡状态
});

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
function showMenuEditor() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    const menuText = document.getElementById('menuText');
    document.getElementById('menuEditText').value = menuText ? menuText.value : '';
    document.getElementById('menuEditorModal').classList.add('show');
}

function closeMenuEditor() {
    document.getElementById('menuEditorModal').classList.remove('show');
}

async function saveMenuFromEditor() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    
    const menu = document.getElementById('menuEditText').value.trim();
    
    if (!menu) {
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
            // 同步到隐藏的 textarea
            const menuText = document.getElementById('menuText');
            if (menuText) menuText.value = data.menu;
            document.getElementById('itemCount').textContent = `(${data.count} 项)`;
            // 更新 schoolMenuItems
            schoolMenuItems = data.menu.split('\n').map(s => s.trim()).filter(s => s);
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
    
    // 渲染学校列表
    renderSchoolList(universitiesList);
    
    // 清空搜索框和自定义输入
    document.getElementById('schoolSearchInput').value = '';
    document.getElementById('customSchoolInput').value = '';
    selectedSchool = null;
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
    const finalSchool = customInput || selectedSchool;
    
    if (!finalSchool) {
        showNotification('请选择或输入一个学校！', 'warning');
        return;
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

    document.getElementById('fetcherSubtitle').textContent = `为「${currentSchool}」自动获取菜品数据`;

    const sourceInfo = document.getElementById('fetcherSourceInfo');
    sourceInfo.innerHTML = '<p style="color:#666;">点击"开始获取"将从精选数据库中查找菜品数据。</p><p style="color:#999;font-size:0.85em;margin-top:5px;">获取后你可以逐条审核、增删菜品，确保数据准确。</p>';
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
        skipBtn.className = 'btn btn-secondary btn-large';
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
                } else {
                    // 登录
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
    const result = localLogin(user, pwd);
    if (result.success) return user;
    localStorage.removeItem('meal_pwd');
    localStorage.removeItem('meal_auto_login');
    return null;
}

async function startupMealLogin() {
    // 1. 尝试自动登录
    if (isAutoLogin()) {
        const user = await tryAutoLogin();
        if (user) {
            updateMealUserDisplay();
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
}

async function switchMealUser() {
    clearMealAuth();
    const name = await showMealLoginDialog();
    if (name) {
        updateMealUserDisplay();
        showMealCheckin();
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

async function saveCurrentMeal() {
    const meal = currentMealTab;
    const dishes = todayMeals[meal] || [];
    const today = new Date().toISOString().split('T')[0];
    const mealNames = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' };
    const user = getMealUser();

    if (!user) {
        showNotification('请先设置昵称', 'warning');
        return;
    }

    localSaveMealLog(user, today, meal, dishes);
    showNotification(`${mealNames[meal]}已保存 ${dishes.length} 道菜品`, 'success');
    updateTodayCheckinBar();
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
