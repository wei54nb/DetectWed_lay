
let currentUserId = null;
let caloriesChart = null;
let muscleGrowthChart = null;


// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('頁面加載完成，初始化健身報告功能');
    setupManualInput();
    
    // 默認加載固定用戶ID的數據（用於測試）
    loadFitnessReport('C111151146');
});

// 新增手動查詢功能
function setupManualInput() {
    const manualInputBtn = document.getElementById('manual-load-btn');
    const manualUserIdInput = document.getElementById('manual-user-id');
    const errorDisplay = document.getElementById('manual-input-error');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    if (!manualInputBtn || !manualUserIdInput) {
        console.error('找不到手動輸入元素');
        return;
    }
    
    console.log('設置手動輸入功能');
    
    manualInputBtn.addEventListener('click', async () => {
        const userId = manualUserIdInput.value.trim();
        
        if (!userId) {
            errorDisplay.textContent = '請輸入用戶ID';
            errorDisplay.style.display = 'block';
            return;
        }
        
        errorDisplay.style.display = 'none';
        loadingIndicator.style.display = 'block';
        
        try {
            await loadFitnessReport(userId);
            console.log(`成功加載用戶 ${userId} 的健身報告`);
        } catch (error) {
            console.error('加載健身報告失敗:', error);
            errorDisplay.textContent = `查詢失敗: ${error.message}`;
            errorDisplay.style.display = 'block';
        } finally {
            loadingIndicator.style.display = 'none';
        }
    });
    
    // 回車鍵觸發查詢
    manualUserIdInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            manualInputBtn.click();
        }
    });
}


// 获取健身报告数据
async function loadFitnessReport(userId) {
    if (!userId) {
        throw new Error('未提供用戶ID');
    }
    
    console.log(`正在加載用戶 ${userId} 的健身報告`);
    currentUserId = userId; // 這裡嘗試修改 currentUserId
    
    try {
        // 明確指定完整URL，避免相對路徑問題
        const url = `/api/fitness/dashboard?user_id=${encodeURIComponent(userId)}`;
        console.log(`請求URL: ${url}`);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });
        
        console.log('API響應狀態:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP錯誤! 狀態碼: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('API響應數據:', data);
        
        if (!data.success) {
            throw new Error(data.message || '獲取數據失敗');
        }
        
        // 處理數據並更新UI
        updateDashboardUI(data);
        renderCharts(data);
        renderExerciseStats(data.exercise_stats);
        renderRecentExercises(data.recent_exercises);
        
        return data;
    } catch (error) {
        console.error('加載健身報告失敗:', error);
        throw error;
    }
}


// 渲染圖表
function renderCharts(data) {
    console.log('渲染圖表');
    renderCaloriesChart(data.calories_trend);
    renderMuscleGrowthChart(data.muscle_growth);
}



function processAndDisplayData(data) {
    // 強制轉換數據類型
    const processedData = {
        ...data,
        total_weight: parseFloat(data.total_weight) || 0,
        total_calories: parseFloat(data.total_calories) || 0,
        total_training_time: parseInt(data.total_training_time) || 0,
        training_frequency: parseInt(data.training_frequency) || 0,
        calories_trend: data.calories_trend?.map(Number) || Array(7).fill(0),
        muscle_growth: {
            arms: parseInt(data.muscle_growth?.arms) || 0,
            chest: parseInt(data.muscle_growth?.chest) || 0,
            core: parseInt(data.muscle_growth?.core) || 0,
            legs: parseInt(data.muscle_growth?.legs) || 0,
            shoulders: parseInt(data.muscle_growth?.shoulders) || 0
        }
    };
    
    // 更新UI
    updateDashboardUI(processedData);
    
    // 渲染圖表
    renderCaloriesChart(processedData.calories_trend);
    renderMuscleGrowthChart(processedData.muscle_growth);
}


// 顯示錯誤訊息
function showErrorMessage(message) {
    console.error(message);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    
    const reportContainer = document.getElementById('fitness-report');
    if (reportContainer) {
        reportContainer.prepend(errorDiv);
    } else {
        document.body.appendChild(errorDiv);
    }
}



function updateDashboardUI(data) {
    console.log('更新儀表板UI');
    
    // 更新總重量
    const totalWeightElement = document.getElementById('total-weight');
    if (totalWeightElement) {
        totalWeightElement.textContent = `${data.total_weight.toFixed(1)} kg`;
    }
    
    // 更新總卡路里
    const totalCaloriesElement = document.getElementById('total-calories');
    if (totalCaloriesElement) {
        totalCaloriesElement.textContent = `${data.total_calories.toFixed(0)} 卡路里`;
    }
    
    // 更新總訓練時間
    const totalTrainingTimeElement = document.getElementById('total-training-time');
    if (totalTrainingTimeElement) {
        const hours = Math.floor(data.total_training_time / 60);
        const minutes = data.total_training_time % 60;
        totalTrainingTimeElement.textContent = `${hours} 小時 ${minutes} 分鐘`;
    }
    
    // 更新訓練頻率
    const trainingFrequencyElement = document.getElementById('training-frequency');
    if (trainingFrequencyElement) {
        trainingFrequencyElement.textContent = `${data.training_frequency} 次/周`;
    }
}


// 渲染卡路里消耗趨勢圖
function renderCaloriesChart(caloriesTrend) {
    const ctx = document.getElementById('calories-chart');
    if (!ctx) {
        console.error('找不到卡路里圖表元素');
        return;
    }
    
    console.log('渲染卡路里消耗趨勢圖:', caloriesTrend);
    
    // 如果已有圖表，先銷毀
    if (caloriesChart) {
        caloriesChart.destroy();
    }
    
    // 確保數據是數字類型
    const values = Array.isArray(caloriesTrend) ? caloriesTrend.map(Number) : [];
    
    // 創建標籤（最近7天）
    const labels = [];
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('zh-TW', {month: 'short', day: 'numeric'}));
    }
    
    // 如果數據少於7天，補充為7天
    while (values.length < 7) {
        values.unshift(0);
    }
    
    // 只取最近7天的數據
    const recentValues = values.slice(-7);
    
    caloriesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '卡路里消耗',
                data: recentValues,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y.toFixed(0)} 卡路里`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '卡路里'
                    }
                }
            }
        }
    });
}



// 當前用戶
const currentUser = "{{ current_user.username }}";




// 每種運動的卡路里消耗
const CALORIES_PER_REP = {
'squat': 0.5,
'bicep-curl': 0.3,
'shoulder-press': 0.4,
'push-up': 0.3,
'pull-up': 0.5,
'dumbbell-row': 0.4
};


// 全局變量
let progressChart = null;
let activityChart = null;
let currentPeriod = 'week'; // 默認顯示一週的數據


// 初始化圖表
function initCharts() {
// 如果图表已存在，先销毁它们
if (progressChart) {
    progressChart.destroy();
}
if (activityChart) {
    activityChart.destroy();
}

const progressCtx = document.getElementById('progress-chart').getContext('2d');
const activityCtx = document.getElementById('activity-chart').getContext('2d');

progressChart = new Chart(progressCtx, {
    type: 'line',
    data: {
        labels: ['載入中...'],
        datasets: [
            {
                label: '運動次數',
                data: [0],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                tension: 0.3,
                fill: true
            },
            {
                label: '消耗熱量',
                data: [0],
                borderColor: '#2ecc71',
                backgroundColor: 'rgba(46, 204, 113, 0.1)',
                tension: 0.3,
                fill: true
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        plugins: {
            legend: {
                position: 'top',
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

activityChart = new Chart(activityCtx, {
    type: 'bar',
    data: {
        labels: ['載入中...'],
        datasets: [
            {
                label: '組數',
                data: [0],
                backgroundColor: 'rgba(52, 152, 219, 0.7)'
            },
            {
                label: '次數',
                data: [0],
                backgroundColor: 'rgba(46, 204, 113, 0.7)'
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});
}


// 渲染肌肉群發展圖
function renderMuscleGrowthChart(muscleData) {
    const ctx = document.getElementById('muscle-growth-chart');
    if (!ctx) {
        console.error('找不到肌肉發展圖表元素');
        return;
    }
    
    console.log('渲染肌肉群發展圖:', muscleData);
    
    // 如果已有圖表，先銷毀
    if (muscleGrowthChart) {
        muscleGrowthChart.destroy();
    }
    
    // 確保數據是數字類型
    const data = [
        Number(muscleData.arms) || 0,
        Number(muscleData.chest) || 0,
        Number(muscleData.core) || 0,
        Number(muscleData.legs) || 0,
        Number(muscleData.shoulders) || 0
    ];
    
    muscleGrowthChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['手臂', '胸部', '核心', '腿部', '肩膀'],
            datasets: [{
                label: '肌肉群發展',
                data: data,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '發展指數'
                    }
                }
            }
        }
    });
}


// 更新統計數據
function updateStats(data) {
// 防止數據為空
if (!data || data.length === 0) {
    console.warn("沒有可用的運動數據");
    document.getElementById('total-calories').textContent = "0";
    document.getElementById('total-sets').textContent = "0";
    document.getElementById('active-days').textContent = "0";
    
    // 清空图表数据
    progressChart.data.labels = ['無數據'];
    progressChart.data.datasets[0].data = [0];
    progressChart.data.datasets[1].data = [0];
    progressChart.update();
    
    activityChart.data.labels = ['無數據'];
    activityChart.data.datasets[0].data = [0];
    activityChart.data.datasets[1].data = [0];
    activityChart.update();
    
    return;
}

const totalCalories = data.reduce((sum, day) => sum + (day.weight * day.reps * day.sets * 0.1), 0);
const totalSets = data.reduce((sum, day) => sum + day.totalSets, 0);
const activeDays = new Set(data.map(day => day.date)).size; // 計算不重複的日期數

document.getElementById('total-calories').textContent = Math.round(totalCalories);
document.getElementById('total-sets').textContent = totalSets;
document.getElementById('active-days').textContent = activeDays;

// 獲取唯一的日期列表並排序
const uniqueDates = [...new Set(data.map(d => d.date))].sort();

// 為每個日期準備數據
const repsByDate = {};
const caloriesByDate = {};
const setsByDate = {};

uniqueDates.forEach(date => {
    repsByDate[date] = 0;
    caloriesByDate[date] = 0;
    setsByDate[date] = 0;
});

// 累計每個日期的數據
data.forEach(item => {
    repsByDate[item.date] += item.totalReps;
    caloriesByDate[item.date] += item.calories;
    setsByDate[item.date] += item.totalSets;
});

// 更新圖表數據
progressChart.data.labels = uniqueDates;
progressChart.data.datasets[0].data = uniqueDates.map(date => repsByDate[date]);
progressChart.data.datasets[1].data = uniqueDates.map(date => caloriesByDate[date]);
progressChart.update();

activityChart.data.labels = uniqueDates;
activityChart.data.datasets[0].data = uniqueDates.map(date => setsByDate[date]);
activityChart.data.datasets[1].data = uniqueDates.map(date => repsByDate[date]);
activityChart.update();
}

// 獲取數據
async function fetchData() {
    try {
        // 添加用户ID参数
        const response = await fetch(`/api/exercise_data?user_id=${currentUserId}`);
        const result = await response.json();

        if (result.success && result.data) {
            console.log("API返回數據:", result.data);
            const processedData = processData(result.data);
            updateStats(processedData);
        } else {
            console.warn("未獲取到數據", result.message || "API返回格式不正確");
            // 显示无数据状态，不再使用随机数据
            updateStats([]);
        }
    } catch (error) {
        console.error("獲取數據錯誤:", error);
        // 显示无数据状态，不再使用随机数据
        updateStats([]);
    }
}

// 生成預設數據
function generateDefaultData() {
        const today = new Date();
        const data = [];
        
        // 生成過去7天的預設數據
        for (let i = 6; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            
            data.push({
                date: dateStr,
                totalSets: Math.floor(Math.random() * 10) + 1,
                totalReps: Math.floor(Math.random() * 50) + 10,
                calories: Math.floor(Math.random() * 200) + 50,
                exercises: ['squat', 'push-up']
            });
        }
        
    return data;
}


function renderCaloriesChart(data) {
    const ctx = document.getElementById('calories-chart');
    
    // 檢查是否已有圖表實例，如果有則先銷毀
    if (ctx.chart) {
        ctx.chart.destroy();
    }
    
    ctx.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || ['週一', '週二', '週三', '週四', '週五', '週六', '週日'],
            datasets: [{
                label: '熱量消耗',
                data: data.values || [0, 0, 0, 0, 0, 0, 0],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// 處理數據
function processData(records) {
// 確保records是一個數組
if (!Array.isArray(records)) {
    console.error("API返回的數據不是數組格式");
    return [];
}

const groupedData = {}; // 用來存放每一天的數據

// 按日期分組
records.forEach(record => {
    // 確保record是一個有效的對象
    if (!record || typeof record !== 'object') {
        return;
    }
    
    // 獲取日期
    const date = record.date || '';
    if (!date) return;
    
    if (!groupedData[date]) {
        groupedData[date] = {
            date: date,
            totalSets: 0,
            totalReps: 0,
            calories: 0,
            exercises: []
        };
    }
    
    // 從數據庫獲取的值可能是字符串，需要轉換為數字
    const sets = parseInt(record.total_sets) || 0;
    const reps = parseInt(record.total_reps) || 0;
    
    groupedData[date].totalSets += sets;
    groupedData[date].totalReps += reps;
    
    if (record.exercise_type) {
        if (!groupedData[date].exercises.includes(record.exercise_type)) {
            groupedData[date].exercises.push(record.exercise_type);
        }
        
        // 計算卡路里消耗
        const caloriesPerRep = CALORIES_PER_REP[record.exercise_type] || 0.3;
        groupedData[date].calories += reps * caloriesPerRep;
    }
});

// 轉換為數組並按日期排序
const result = Object.values(groupedData);
if (result.length === 0) {
    return [];
}
return result.sort((a, b) => new Date(a.date) - new Date(b.date));
}   


// 切換週期
function switchPeriod(period) {
    currentPeriod = period;
    
    // 移除所有按鈕的active類
    document.querySelectorAll('.time-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 添加當前按鈕的active類
    document.querySelector(`.time-button[data-period="${period}"]`).classList.add('active');
    
    fetchData();
}

// 顯示遊戲通知
function showNotification(title, message) {
    const notification = document.getElementById('game-notification');
    notification.querySelector('.notification-title').textContent = title;
    notification.querySelector('.notification-message').textContent = message;
    notification.classList.add('show');
    
    // 5秒後自動關閉
    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}

// 關閉通知
function closeNotification() {
    document.getElementById('game-notification').classList.remove('show');
}

// 淡入效果
function handleIntersection(entries, observer) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}

// 渲染運動統計
function renderExerciseStats(exerciseStats) {
    const container = document.getElementById('exercise-stats-container');
    if (!container) {
        console.error('找不到運動統計容器元素');
        return;
    }
    
    console.log('渲染運動統計:', exerciseStats);
    
    if (!exerciseStats || exerciseStats.length === 0) {
        container.innerHTML = '<p class="no-data">暫無運動統計數據</p>';
        return;
    }
    
    // 創建運動統計HTML
    let html = '<div class="stats-grid">';
    
    exerciseStats.forEach(stat => {
        html += `
            <div class="stat-item">
                <div class="stat-name">${formatExerciseName(stat.name)}</div>
                <div class="stat-count">${stat.count} 次</div>
                <div class="stat-bar">
                    <div class="stat-bar-fill" style="width: ${Math.min(100, stat.count / 2)}%"></div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}


// 渲染最近訓練記錄
function renderRecentExercises(recentExercises) {
    const container = document.getElementById('recent-exercises-container');
    if (!container) {
        console.error('找不到最近訓練記錄容器元素');
        return;
    }
    
    console.log('渲染最近訓練記錄:', recentExercises);
    
    if (!recentExercises || recentExercises.length === 0) {
        container.innerHTML = '<p class="no-data">暫無訓練記錄</p>';
        return;
    }
    
    // 創建最近訓練記錄HTML
    let html = '<div class="recent-list">';
    
    recentExercises.forEach(exercise => {
        html += `
            <div class="recent-item">
                <div class="recent-date">${exercise.date}</div>
                <div class="recent-exercise">${formatExerciseName(exercise.exercise)}</div>
                <div class="recent-reps">${exercise.reps} 次</div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// 格式化運動名稱
function formatExerciseName(name) {
    const nameMap = {
        'squat': '深蹲',
        'push-up': '伏地挺身',
        'bicep-curl': '二頭彎舉',
        'shoulder-press': '肩推',
        'pull-up': '引體向上',
        'dumbbell-row': '啞鈴划船',
        'tricep-extension': '三頭肌伸展',
        'lunge': '弓步蹲',
        'bench-press': '臥推'
    };
    
    return nameMap[name] || name;
}




