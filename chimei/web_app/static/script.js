// ========== 全局变量 ==========
let currentSchool = '';
let isAdvancedMode = false;
let inputModalCallback = null;
let universitiesList = []; // 大学列表
let selectedSchool = null; // 向导中选中的学校

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    loadUniversitiesList(); // 加载大学列表
    checkFirstTimeUse(); // 检查是否首次使用
    setupEventListeners();
    loadBodyData(); // 恢复缓存的身体数据
    startNutritionTips();
});

function setupEventListeners() {
    // BMI自动计算 + 自动保存
    document.getElementById('heightInput').addEventListener('input', function() { autoCalculateBMI(); saveBodyData(); });
    document.getElementById('weightInput').addEventListener('input', function() { autoCalculateBMI(); saveBodyData(); });
    document.getElementById('ageInput').addEventListener('change', saveBodyData);

    // 性别切换时保存
    document.querySelectorAll('input[name="gender"]').forEach(function(radio) {
        radio.addEventListener('change', saveBodyData);
    });

    // 状态复选框变化时保存
    document.querySelectorAll('.checkbox-grid input[type="checkbox"]').forEach(function(cb) {
        cb.addEventListener('change', saveBodyData);
    });

    // 回车键事件
    document.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            if (isAdvancedMode) {
                smartRecommend();
            } else {
                randomRecommend();
            }
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
    } else {
        // 非首次使用，加载学校
        currentSchool = hasSchool;
        updateSchoolDisplay();
        loadMenu();
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

async function saveMenu() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    
    const menu = document.getElementById('menuText').value.trim();
    
    if (!menu) {
        if (!confirm('菜单内容为空，确定要保存吗？')) {
            return;
        }
    }
    
    try {
        const response = await fetch(`/api/menu/${encodeURIComponent(currentSchool)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ menu: menu })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('menuText').value = data.menu;
            document.getElementById('itemCount').textContent = `(${data.count} 项)`;
            showNotification(`菜单已成功保存到 ${currentSchool}！`, 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('保存菜单失败:', error);
        showNotification('保存菜单失败', 'error');
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

// ========== 模式切换 ==========
function toggleMode() {
    const simpleMode = document.getElementById('simpleMode');
    const advancedMode = document.getElementById('advancedMode');
    const toggleBtn = document.getElementById('modeToggleBtn');
    
    if (isAdvancedMode) {
        // 切换回简洁模式
        simpleMode.classList.add('active');
        advancedMode.classList.remove('active');
        toggleBtn.textContent = '切换到专业版模式';
        isAdvancedMode = false;
    } else {
        // 切换到专业模式
        simpleMode.classList.remove('active');
        advancedMode.classList.add('active');
        toggleBtn.textContent = '切换回简洁模式';
        isAdvancedMode = true;
    }
}

// ========== 随机推荐 ==========
async function randomRecommend() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/recommend/random/${encodeURIComponent(currentSchool)}`);
        const data = await response.json();
        
        if (data.success) {
            showModal(`
                <h2 style="color: #667eea; margin-bottom: 20px;">🎯 随机推荐结果</h2>
                <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 10px;">
                    <p style="font-size: 1.2em; color: #666; margin-bottom: 15px;">为 <strong>${data.school}</strong> 的你推荐：</p>
                    <p style="font-size: 2em; color: #11998e; font-weight: bold; margin: 20px 0;">✅ ${data.result}</p>
                    <p style="font-size: 1.1em; color: #888; margin-top: 20px;">🍽️ 用餐愉快！</p>
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
async function smartRecommend() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }
    
    const age = parseInt(document.getElementById('ageInput').value) || 18;
    const gender = document.querySelector('input[name="gender"]:checked').value;
    const height = parseFloat(document.getElementById('heightInput').value) || 0;
    const weight = parseFloat(document.getElementById('weightInput').value) || 0;
    
    // 收集选中的状态
    const conditions = [];
    const conditionMap = {
        'cond_child': '儿童',
        'cond_period': '经期',
        'cond_cold': '感冒',
        'cond_stomach': '肠胃不适',
        'cond_exercise': '运动后',
        'cond_underweight': '低体重',
        'cond_overweight': '超重',
        'cond_vegetarian': '素食',
        'cond_fire': '上火',
        'cond_muscle': '增肌',
        'cond_seafood_allergy': '海鲜过敏',
        'cond_peanut_allergy': '花生过敏',
        'cond_lactose': '乳糖不耐'
    };
    
    for (const [id, name] of Object.entries(conditionMap)) {
        if (document.getElementById(id).checked) {
            conditions.push(name);
        }
    }
    
    try {
        const response = await fetch('/api/recommend/smart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                school_name: currentSchool,
                age: age,
                gender: gender,
                height: height,
                weight: weight,
                conditions: conditions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            let detailsHtml = '';
            if (data.details && data.details.length > 0) {
                detailsHtml = '<div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">' +
                    data.details.map(d => `<p style="margin: 5px 0; color: #666;">${d}</p>`).join('') +
                    '</div>';
            }
            
            let bmiInfo = '';
            if (data.bmi) {
                bmiInfo = `<p style="margin-top: 10px; color: #888; font-size: 0.9em;">你的BMI值: ${data.bmi}</p>`;
            }
            
            showModal(`
                <h2 style="color: #667eea; margin-bottom: 20px;">🧠 智能推荐结果</h2>
                <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%); border-radius: 10px;">
                    <p style="font-size: 1.1em; color: #666; margin-bottom: 15px;">根据你的身体状况，为 <strong>${currentSchool}</strong> 的你决定：</p>
                    <p style="font-size: 2.2em; color: #11998e; font-weight: bold; margin: 20px 0;">✅ ${data.result}</p>
                    ${detailsHtml}
                    ${bmiInfo}
                    <p style="font-size: 1.1em; color: #888; margin-top: 20px;">🍽️ 希望你用餐愉快！</p>
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

// ========== BMI计算 ==========
async function calculateBMI() {
    const height = parseFloat(document.getElementById('heightInput').value);
    const weight = parseFloat(document.getElementById('weightInput').value);
    
    if (!height || !weight || height <= 0 || weight <= 0) {
        showNotification('请输入有效的身高和体重！', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/bmi/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                height: height,
                weight: weight
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('bmiResult').textContent = `BMI: ${data.bmi}`;
            
            // 根据BMI自动勾选状态
            if (data.bmi < 18.5) {
                document.getElementById('cond_underweight').checked = true;
                document.getElementById('cond_overweight').checked = false;
            } else if (data.bmi >= 24) {
                document.getElementById('cond_overweight').checked = true;
                document.getElementById('cond_underweight').checked = false;
            } else {
                document.getElementById('cond_underweight').checked = false;
                document.getElementById('cond_overweight').checked = false;
            }
            
            showModal(`
                <h2 style="color: #667eea; margin-bottom: 20px;">📊 BMI计算结果</h2>
                <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 10px;">
                    <p style="font-size: 3em; font-weight: bold; color: #1976d2; margin: 20px 0;">${data.bmi}</p>
                    <p style="font-size: 1.3em; color: #333; margin: 15px 0;">分类: <strong>${data.category}</strong></p>
                    <p style="font-size: 1em; color: #666; margin-top: 15px;">${data.suggestion}</p>
                </div>
            `);
        } else {
            showNotification(data.message, 'warning');
        }
    } catch (error) {
        console.error('BMI计算失败:', error);
        showNotification('计算失败', 'error');
    }
}

function autoCalculateBMI() {
    const heightText = document.getElementById('heightInput').value.trim();
    const weightText = document.getElementById('weightInput').value.trim();
    
    if (heightText && weightText) {
        const height = parseFloat(heightText);
        const weight = parseFloat(weightText);
        
        if (height > 0 && weight > 0) {
            const bmi = weight / ((height / 100) ** 2);
            document.getElementById('bmiResult').textContent = `BMI: ${bmi.toFixed(1)}`;
        }
    }
}

// ========== 身体数据缓存 ==========
function saveBodyData() {
    const bodyData = {
        age: document.getElementById('ageInput').value,
        gender: document.querySelector('input[name="gender"]:checked')?.value || '女',
        height: document.getElementById('heightInput').value,
        weight: document.getElementById('weightInput').value,
        conditions: {}
    };
    // 保存所有复选框状态
    document.querySelectorAll('.checkbox-grid input[type="checkbox"]').forEach(function(cb) {
        bodyData.conditions[cb.id] = cb.checked;
    });
    localStorage.setItem('body_data', JSON.stringify(bodyData));
}

function loadBodyData() {
    const saved = localStorage.getItem('body_data');
    if (!saved) return;
    try {
        const data = JSON.parse(saved);
        if (data.age) document.getElementById('ageInput').value = data.age;
        if (data.gender) {
            const radio = document.querySelector(`input[name="gender"][value="${data.gender}"]`);
            if (radio) radio.checked = true;
        }
        if (data.height) document.getElementById('heightInput').value = data.height;
        if (data.weight) document.getElementById('weightInput').value = data.weight;
        if (data.conditions) {
            for (const [id, checked] of Object.entries(data.conditions)) {
                const el = document.getElementById(id);
                if (el) el.checked = checked;
            }
        }
        // 恢复后自动计算BMI
        autoCalculateBMI();
    } catch (e) {
        console.error('加载缓存身体数据失败:', e);
    }
}

// ========== 营养提示 ==========
function startNutritionTips() {
    const tips = [
        "💡 选择困难？输入身高体重，让系统为你决定吃什么！",
        "🥗 均衡饮食：每餐尽量包含蛋白质、蔬菜和主食",
        "💧 每天喝足8杯水，保持身体水分平衡",
        "🍎 一天一苹果，医生远离我 - 适当补充水果",
        "🏃‍♂️ 饭后散步10分钟，有助于消化",
        "😴 充足睡眠对新陈代谢至关重要",
        "🍚 主食选择杂粮饭，营养更全面",
        "🍵 饭后半小时再喝茶，避免影响铁吸收"
    ];
    
    let currentIndex = 0;
    
    setInterval(() => {
        currentIndex = (currentIndex + 1) % tips.length;
        document.getElementById('nutritionTip').textContent = tips[currentIndex];
    }, 30000);
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
let currentMealTab = 'breakfast';
let todayMeals = { breakfast: [], lunch: [], dinner: [] };
let schoolMenuItems = [];

async function showMealCheckin() {
    if (!currentSchool) {
        showNotification('请先选择一个学校！', 'warning');
        return;
    }

    document.getElementById('mealCheckinModal').classList.add('show');

    // 显示日期
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0];
    document.getElementById('checkinDate').textContent = `📅 ${dateStr}`;

    // 加载今日打卡数据
    try {
        const resp = await fetch('/api/meal-log/today');
        const data = await resp.json();
        if (data.success) {
            todayMeals = data.meals || { breakfast: [], lunch: [], dinner: [] };
        }
    } catch (e) {
        console.error('加载打卡数据失败:', e);
    }

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

async function saveCurrentMeal() {
    const meal = currentMealTab;
    const dishes = todayMeals[meal] || [];
    const today = new Date().toISOString().split('T')[0];
    const mealNames = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐' };

    try {
        const resp = await fetch('/api/meal-log/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: today, meal: meal, dishes: dishes })
        });
        const data = await resp.json();
        if (data.success) {
            showNotification(`${mealNames[meal]}已保存 ${dishes.length} 道菜品`, 'success');
        } else {
            showNotification(data.message || '保存失败', 'error');
        }
    } catch (e) {
        console.error('保存打卡失败:', e);
        showNotification('保存失败', 'error');
    }
}

// ========== 周饮食报告 ==========
async function showWeeklyReport() {
    // 确保报告弹窗可见
    document.getElementById('weeklyReportModal').classList.add('show');
    const content = document.getElementById('reportContent');
    content.innerHTML = '<p style="text-align:center;color:#999;padding:30px;">加载中...</p>';

    try {
        const resp = await fetch('/api/meal-log/weekly-report');
        const data = await resp.json();
        if (data.success) {
            renderReport(data);
        } else {
            content.innerHTML = '<p style="color:#e74c3c;text-align:center;">加载报告失败</p>';
        }
    } catch (e) {
        console.error('加载报告失败:', e);
        content.innerHTML = '<p style="color:#e74c3c;text-align:center;">加载报告失败</p>';
    }
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

    content.innerHTML = html;
}
