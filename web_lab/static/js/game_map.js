// 游戏地图页面的JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const levelNodesContainer = document.getElementById('level-nodes');
    const levelModal = document.getElementById('level-modal');
    const achievementsModal = document.getElementById('achievements-modal');
    const achievementNotification = document.getElementById('achievement-notification');

    const completedLevelsBtn = document.getElementById('completed-levels-btn');
    if (completedLevelsBtn) {
        completedLevelsBtn.addEventListener('click', showCompletedLevels);
    }
    
    // 用户信息
    let userData = {
        userId: 'C111151146', // 默认用户ID，实际应从会话中获取
        currentLevel: 1,
        totalExp: 0,
        nextLevelExp: 100
    };
    
    // 关卡数据
    let levelsData = [];
    
    // 初始化
    init();
    
    // 初始化函数
    async function init() {
        try {
            // 获取用户进度
            await getUserProgress();
            
            // 获取关卡数据
            await getLevelsData();
            
            // 渲染关卡节点
            renderLevelNodes();
            
            // 更新用户界面
            updateUserInterface();
            
            // 设置事件监听器
            setupEventListeners();
        } catch (error) {
            console.error('初始化失败:', error);
        }
    }
    
    // 获取用户进度
    async function getUserProgress() {
        try {
            const response = await fetch(`/api/game/user_progress?user_id=${userData.userId}`);
            const data = await response.json();
            
            if (data.success) {
                userData.currentLevel = data.progress.current_level;
                userData.totalExp = data.progress.total_exp;
                
                // 设置下一级所需经验
                if (data.current_level && data.current_level.required_exp) {
                    userData.nextLevelExp = data.current_level.required_exp;
                }
                
                // 检查是否有新成就
                if (data.achievements && data.achievements.length > 0) {
                    const latestAchievement = data.achievements[data.achievements.length - 1];
                    const achievementTime = new Date(latestAchievement.unlocked_at);
                    const now = new Date();
                    
                    // 如果成就是在过去24小时内解锁的，显示通知
                    if ((now - achievementTime) / (1000 * 60 * 60) < 24) {
                        showAchievementNotification(latestAchievement.achievement_name, latestAchievement.achievement_description);
                    }
                }
            }
        } catch (error) {
            console.error('获取用户进度失败:', error);
        }
    }
    
    // 获取关卡数据
    async function getLevelsData() {
        try {
            const response = await fetch('/api/game/levels');
            const data = await response.json();
            
            if (data.success) {
                levelsData = data.levels;
            }
        } catch (error) {
            console.error('获取关卡数据失败:', error);
        }
    }
    
    // 渲染关卡节点
    function renderLevelNodes() {
        levelNodesContainer.innerHTML = '';
        
        levelsData.forEach(level => {
            const levelNode = document.createElement('div');
            levelNode.className = 'level-node';
            levelNode.dataset.levelId = level.level_id;
            
            // 设置节点状态 (已完成/当前/锁定)
            if (level.level_id < userData.currentLevel) {
                levelNode.classList.add('completed');
            } else if (level.level_id === userData.currentLevel) {
                levelNode.classList.add('current');
            } else {
                levelNode.classList.add('locked');
            }
            
            // 设置节点位置 (可以根据关卡ID设置不同位置)
            levelNode.style.left = `${(level.level_id - 1) * 15 + 10}%`;
            levelNode.style.top = `${Math.sin((level.level_id - 1) * 0.5) * 20 + 50}%`;
            
            // 节点内容
            levelNode.innerHTML = `
                <div class="node-number">${level.level_id}</div>
                <div class="node-name">${level.level_name}</div>
            `;
            
            // 添加点击事件
            levelNode.addEventListener('click', () => {
                if (level.level_id <= userData.currentLevel) {
                    showLevelDetails(level);
                }
            });
            
            levelNodesContainer.appendChild(levelNode);
            
            // 如果不是第一个节点，添加连接线
            if (level.level_id > 1) {
                const prevLevel = levelsData.find(l => l.level_id === level.level_id - 1);
                if (prevLevel) {
                    const connector = document.createElement('div');
                    connector.className = 'level-connector';
                    
                    // 设置连接线状态
                    if (level.level_id <= userData.currentLevel) {
                        connector.classList.add('active');
                    }
                    
                    // 计算连接线位置和角度
                    const prevLeft = (prevLevel.level_id - 1) * 15 + 10;
                    const prevTop = Math.sin((prevLevel.level_id - 1) * 0.5) * 20 + 50;
                    const currLeft = (level.level_id - 1) * 15 + 10;
                    const currTop = Math.sin((level.level_id - 1) * 0.5) * 20 + 50;
                    
                    const length = Math.sqrt(Math.pow(currLeft - prevLeft, 2) + Math.pow(currTop - prevTop, 2));
                    const angle = Math.atan2(currTop - prevTop, currLeft - prevLeft) * 180 / Math.PI;
                    
                    connector.style.width = `${length}%`;
                    connector.style.left = `${prevLeft}%`;
                    connector.style.top = `${prevTop}%`;
                    connector.style.transform = `rotate(${angle}deg)`;
                    connector.style.transformOrigin = '0 0';
                    
                    levelNodesContainer.appendChild(connector);
                }
            }
        });
    }
    
    // 更新用户界面
    function updateUserInterface() {
        document.getElementById('user-level').textContent = userData.currentLevel;
        document.getElementById('current-exp').textContent = userData.totalExp;
        document.getElementById('next-level-exp').textContent = userData.nextLevelExp;
        
        // 更新经验条
        const expPercentage = Math.min(100, (userData.totalExp / userData.nextLevelExp) * 100);
        document.getElementById('exp-bar-fill').style.width = `${expPercentage}%`;
    }
    
    // 设置事件监听器
    function setupEventListeners() {
        // 成就按钮点击事件
        document.getElementById('achievements-btn').addEventListener('click', showAchievements);
        
        // 关闭模态框按钮
        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', function() {
                levelModal.style.display = 'none';
                achievementsModal.style.display = 'none';
            });
        });
        
        // 开始关卡按钮
        document.getElementById('start-level-btn').addEventListener('click', startLevel);
        
        // 点击模态框外部关闭
        window.addEventListener('click', function(event) {
            if (event.target === levelModal) {
                levelModal.style.display = 'none';
            } else if (event.target === achievementsModal) {
                achievementsModal.style.display = 'none';
            }
        });
    }
    
    // 显示关卡详情
    function showLevelDetails(level) {
        document.getElementById('level-title').textContent = `第${level.level_id}关: ${level.level_name}`;
        document.getElementById('level-description').textContent = level.description;
        document.getElementById('monster-count').textContent = level.monster_count;
        document.getElementById('monster-hp').textContent = level.monster_hp;
        
        // 设置关卡图片
        const levelImage = document.getElementById('level-image');
        levelImage.src = `/static/img/game/level_${level.level_id}.jpg`;
        levelImage.onerror = function() {
            // 如果特定关卡图片不存在，使用默认图片
            this.src = '/static/img/game/default_level.jpg';
        };
        
        // 设置关卡奖励
        document.getElementById('level-rewards').textContent = `经验值 +${level.required_exp / 2}`;
        
        // 保存当前选中的关卡ID
        document.getElementById('start-level-btn').dataset.levelId = level.level_id;
        
        // 显示模态框
        levelModal.style.display = 'block';
    }
    
    // 显示成就列表
    async function showAchievements() {
        try {
            const response = await fetch(`/api/game/user_progress?user_id=${userData.userId}`);
            const data = await response.json();
            
            if (data.success && data.achievements) {
                const achievementsList = document.getElementById('achievements-list');
                achievementsList.innerHTML = '';
                
                if (data.achievements.length === 0) {
                    achievementsList.innerHTML = '<div class="no-achievements">还没有解锁任何成就</div>';
                } else {
                    data.achievements.forEach(achievement => {
                        const achievementItem = document.createElement('div');
                        achievementItem.className = 'achievement-item';
                        
                        achievementItem.innerHTML = `
                            <div class="achievement-icon">
                                <img src="${achievement.icon_path}" onerror="this.src='/static/img/achievements/default.png'">
                            </div>
                            <div class="achievement-info">
                                <div class="achievement-name">${achievement.achievement_name}</div>
                                <div class="achievement-desc">${achievement.achievement_description}</div>
                                <div class="achievement-date">解锁于: ${new Date(achievement.unlocked_at).toLocaleString()}</div>
                            </div>
                        `;
                        
                        achievementsList.appendChild(achievementItem);
                    });
                }
                
                achievementsModal.style.display = 'block';
            }
        } catch (error) {
            console.error('获取成就失败:', error);
        }
    }
    
    // 显示成就通知
    function showAchievementNotification(title, description) {
        document.getElementById('notification-title').textContent = title;
        document.getElementById('notification-description').textContent = description;
        
        achievementNotification.classList.add('show');
        
        // 5秒后隐藏通知
        setTimeout(() => {
            achievementNotification.classList.remove('show');
        }, 5000);
    }
    
    // 开始关卡
    function startLevel() {
        const levelId = document.getElementById('start-level-btn').dataset.levelId;
        window.location.href = `/game/level/${levelId}`;
    }
});


async function showCompletedLevels() {
    try {
        const response = await fetch(`/api/game/completed_levels?user_id=${userData.userId}`);
        const data = await response.json();
        
        if (data.success && data.completed_levels) {
            const completedLevelsList = document.getElementById('completed-levels-list');
            if (!completedLevelsList) {
                console.error('找不到完成關卡列表元素');
                return;
            }
            
            completedLevelsList.innerHTML = '';
            
            if (data.completed_levels.length === 0) {
                completedLevelsList.innerHTML = '<div class="no-completed-levels">還沒有完成任何關卡</div>';
                return;
            }
            
            // 創建表格顯示完成的關卡
            const table = document.createElement('table');
            table.className = 'completed-levels-table';
            
            // 添加表頭
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr>
                    <th>關卡名稱</th>
                    <th>完成時間</th>
                    <th>獲得經驗</th>
                    <th>運動類型</th>
                    <th>運動次數</th>
                </tr>
            `;
            table.appendChild(thead);
            
            // 添加表格內容
            const tbody = document.createElement('tbody');
            data.completed_levels.forEach(level => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${level.level_name || `關卡 ${level.level_id}`}</td>
                    <td>${level.completion_time || '未知'}</td>
                    <td>${level.exp_earned || 0}</td>
                    <td>${level.exercise_type || '未知'}</td>
                    <td>${level.exercise_count || 0}</td>
                `;
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            
            completedLevelsList.appendChild(table);
        } else {
            console.error('獲取完成關卡記錄失敗:', data.message);
        }
    } catch (error) {
        console.error('獲取完成關卡記錄時出錯:', error);
    }
}