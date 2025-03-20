// 游戏关卡页面的JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const videoElement = document.getElementById('video-element');
    const poseCanvas = document.getElementById('pose-canvas');
    const monsterContainer = document.getElementById('monster-container');
    const levelCompleteModal = document.getElementById('level-complete-modal');
    
    // 游戏状态
    const gameState = {
        userId: 'C111151146', // 默认用户ID，实际应从会话中获取
        levelId: parseInt(window.location.pathname.split('/').pop()) || 1,
        currentExercise: 'squat', // 默认运动类型
        targetReps: 10,
        targetSets: 3,
        currentReps: 0,
        currentSets: 0,
        monsterCount: 3,
        monstersDefeated: 0,
        currentMonsterHp: 100,
        currentMonsterMaxHp: 100,
        playerHp: 100,
        isExercising: false,
        levelComplete: false
    };
    
    // 3D场景相关变量
    let scene, camera, renderer, monster, mixer, clock;
    
    // Socket.io连接
    const socket = io();
    
    // 初始化
    init();
    
    // 初始化函数
    async function init() {
        try {
            // 获取关卡数据
            await getLevelData();
            
            // 初始化摄像头
            await initCamera();
            
            // 初始化3D场景
            initScene();
            
            // 更新用户界面
            updateUI();
            
            // 设置事件监听器
            setupEventListeners();
            
            // 设置Socket.io事件
            setupSocketEvents();
        } catch (error) {
            console.error('初始化失败:', error);
            showCoachTip('初始化失败，请刷新页面重试');
        }
    }
    
    // 获取关卡数据
    async function getLevelData() {
        try {
            const response = await fetch(`/api/game/levels`);
            const data = await response.json();
            
            if (data.success) {
                const levelData = data.levels.find(level => level.level_id === gameState.levelId);
                
                if (levelData) {
                    document.getElementById('level-title').textContent = `第${levelData.level_id}关: ${levelData.level_name}`;
                    gameState.monsterCount = levelData.monster_count;
                    gameState.currentMonsterMaxHp = levelData.monster_hp;
                    gameState.currentMonsterHp = levelData.monster_hp;
                    
                    document.getElementById('total-monsters').textContent = gameState.monsterCount;
                    document.getElementById('monster-max-hp').textContent = gameState.currentMonsterMaxHp;
                    document.getElementById('monster-hp').textContent = gameState.currentMonsterHp;
                    
                    // 根据关卡难度调整目标次数和组数
                    if (levelData.level_id > 3) {
                        gameState.targetReps = 15;
                    }
                    if (levelData.level_id > 5) {
                        gameState.targetSets = 5;
                    }
                    
                    document.getElementById('target-reps').textContent = gameState.targetReps;
                    document.getElementById('target-sets').textContent = gameState.targetSets;
                }
            }
        } catch (error) {
            console.error('获取关卡数据失败:', error);
        }
    }
    
    // 初始化摄像头
    async function initCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            videoElement.srcObject = stream;
            
            // 等待视频元素加载
            await new Promise(resolve => {
                videoElement.onloadedmetadata = resolve;
            });
            
            // 设置Canvas尺寸
            poseCanvas.width = videoElement.videoWidth;
            poseCanvas.height = videoElement.videoHeight;
            
            showCoachTip('摄像头已准备就绪，准备开始运动！');
        } catch (error) {
            console.error('摄像头初始化失败:', error);
            showCoachTip('无法访问摄像头，请确保已授予权限');
            throw error;
        }
    }
    
    function levelCompleted() {
        console.log('關卡完成，發送請求到伺服器');
        
        // 停止偵測
        socket.emit('stop_detection', {});
        
        // 發送關卡完成請求
        fetch('/api/game/complete_level', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                level_id: currentLevel.level_id,
                user_id: document.getElementById('student-id').value || 'C111151146'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('關卡完成數據:', data);
                
                // 顯示關卡完成消息
                alert(`恭喜！你已完成關卡 ${currentLevel.level_name}！獲得 ${currentLevel.exp_reward} 經驗值！`);
                
                // 更新用戶經驗值和等級顯示
                if (data.user_data) {
                    document.getElementById('current-exp').textContent = data.user_data.total_exp;
                    document.getElementById('user-level').textContent = data.user_data.level;
                    document.getElementById('current-level-display').textContent = data.user_data.current_level;
                    document.getElementById('next-level-exp').textContent = data.user_data.next_level_exp;
                    
                    // 更新經驗條
                    const expBarFill = document.getElementById('exp-bar-fill');
                    if (expBarFill) {
                        const expPercentage = (data.user_data.total_exp % data.user_data.next_level_exp) / data.user_data.next_level_exp * 100;
                        expBarFill.style.width = `${expPercentage}%`;
                    }
                }
                
                // 如果有解鎖成就，顯示成就通知
                if (data.achievements && data.achievements.length > 0) {
                    console.log('有新成就解鎖:', data.achievements);
                    
                    // 使用新的成就通知系統
                    if (typeof showMultipleAchievements === 'function') {
                        showMultipleAchievements(data.achievements);
                    } else {
                        console.error('找不到 showMultipleAchievements 函數');
                    }
                }
                
                // 延遲後重定向到地圖頁面
                setTimeout(() => {
                    window.location.href = '/game/map';
                }, 3000);
            } else {
                console.error('關卡完成請求失敗:', data.error);
            }
        })
        .catch(error => {
            console.error('關卡完成請求發送失敗:', error);
        });
    }

        // 修改成就通知函數，確保通知會消失
    function showAchievementNotification(title, description) {
        const notification = document.getElementById('achievement-notification');
        const titleElement = document.getElementById('notification-title');
        const descriptionElement = document.getElementById('notification-description');
        
        if (notification && titleElement && descriptionElement) {
            titleElement.textContent = title;
            descriptionElement.textContent = description;
            
            notification.classList.add('show');
            
            // 清除可能存在的舊定時器
            if (window.achievementTimer) {
                clearTimeout(window.achievementTimer);
            }
            
            // 設置新的定時器，5秒後隱藏通知
            window.achievementTimer = setTimeout(() => {
                notification.classList.remove('show');
            }, 5000);
        }
    }

    // 初始化3D场景
    function initScene() {
        // 创建场景
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87CEEB); // 天蓝色背景
        
        // 创建相机
        camera = new THREE.PerspectiveCamera(75, monsterContainer.clientWidth / monsterContainer.clientHeight, 0.1, 1000);
        camera.position.z = 5;
        
        // 创建渲染器
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(monsterContainer.clientWidth, monsterContainer.clientHeight);
        monsterContainer.appendChild(renderer.domElement);
        
        // 添加光源
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(0, 10, 10);
        scene.add(directionalLight);
        
        // 加载怪物模型
        const loader = new THREE.GLTFLoader();
        loader.load('/static/models/monster.glb', (gltf) => {
            monster = gltf.scene;
            monster.scale.set(1, 1, 1);
            monster.position.set(0, -1, 0);
            scene.add(monster);
            
            // 设置动画
            mixer = new THREE.AnimationMixer(monster);
            if (gltf.animations.length > 0) {
                const idleAction = mixer.clipAction(gltf.animations[0]);
                idleAction.play();
            }
            
            // 初始化时钟
            clock = new THREE.Clock();
            
            // 开始渲染循环
            animate();
        }, undefined, (error) => {
            console.error('加载怪物模型失败:', error);
            // 加载失败时显示默认怪物
            createDefaultMonster();
        });
        
        // 窗口大小变化时调整渲染器尺寸
        window.addEventListener('resize', () => {
            camera.aspect = monsterContainer.clientWidth / monsterContainer.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(monsterContainer.clientWidth, monsterContainer.clientHeight);
        });
    }
    
    // 创建默认怪物（当3D模型加载失败时）
    function createDefaultMonster() {
        const geometry = new THREE.BoxGeometry(1, 1, 1);
        const material = new THREE.MeshPhongMaterial({ color: 0xff0000 });
        monster = new THREE.Mesh(geometry, material);
        monster.position.set(0, 0, 0);
        scene.add(monster);
        
        // 开始渲染循环
        animate();
    }
    
    // 动画循环
    function animate() {
        requestAnimationFrame(animate);
        
        // 更新动画混合器
        if (mixer) {
            mixer.update(clock.getDelta());
        }
        
        // 旋转怪物
        if (monster) {
            monster.rotation.y += 0.01;
        }
        
        renderer.render(scene, camera);
    }
    
    // 设置事件监听器
    function setupEventListeners() {
        // 退出按钮
        document.getElementById('exit-btn').addEventListener('click', () => {
            if (confirm('确定要退出关卡吗？当前进度将不会保存。')) {
                window.location.href = '/game/map';
            }
        });
        
        // 关卡完成弹窗按钮
        document.getElementById('next-level-btn').addEventListener('click', () => {
            window.location.href = `/game/level/${gameState.levelId + 1}`;
        });
        
        document.getElementById('return-map-btn').addEventListener('click', () => {
            window.location.href = '/game/map';
        });
    }
    
    // 设置Socket.io事件
    function setupSocketEvents() {
        // 连接成功
        socket.on('connect', () => {
            console.log('Socket.io连接成功');
            
            // 发送开始检测请求
            socket.emit('start_detection', {
                exercise_type: gameState.currentExercise,
                user_id: gameState.userId
            });
        });
        
        // 接收姿态检测结果
        socket.on('pose_result', (data) => {
            // 更新姿态Canvas
            updatePoseCanvas(data.keypoints);
            
            // 处理运动计数
            if (data.exercise_count && data.exercise_count > gameState.currentReps) {
                gameState.currentReps = data.exercise_count;
                document.getElementById('rep-count').textContent = gameState.currentReps;
                
                // 播放音效
                playSound('rep_complete');
                
                // 攻击怪物
                attackMonster();
                
                // 检查是否完成一组
                if (gameState.currentReps >= gameState.targetReps) {
                    completeSet();
                }
            }
            
            // 更新动作质量分数
            if (data.quality_score !== undefined) {
                document.getElementById('quality-score').textContent = Math.round(data.quality_score);
            }
        });
        
        // 接收教练提示
        socket.on('coach_tip', (data) => {
            showCoachTip(data.message);
        });
        
        // 连接错误
        socket.on('connect_error', (error) => {
            console.error('Socket.io连接错误:', error);
            showCoachTip('连接服务器失败，请刷新页面重试');
        });
    }
    
    // 更新姿态Canvas
    function updatePoseCanvas(keypoints) {
        if (!keypoints || keypoints.length === 0) return;
        
        const ctx = poseCanvas.getContext('2d');
        ctx.clearRect(0, 0, poseCanvas.width, poseCanvas.height);
        
        // 绘制骨架
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        
        // 连接关键点
        const connections = [
            [5, 7], [7, 9], // 左臂
            [6, 8], [8, 10], // 右臂
            [5, 6], [5, 11], [6, 12], // 躯干
            [11, 13], [13, 15], // 左腿
            [12, 14], [14, 16] // 右腿
        ];
        
        connections.forEach(([i, j]) => {
            if (keypoints[i] && keypoints[j] && keypoints[i].score > 0.5 && keypoints[j].score > 0.5) {
                ctx.beginPath();
                ctx.moveTo(keypoints[i].x, keypoints[i].y);
                ctx.lineTo(keypoints[j].x, keypoints[j].y);
                ctx.stroke();
            }
        });
        
        // 绘制关键点
        keypoints.forEach(point => {
            if (point && point.score > 0.5) {
                ctx.fillStyle = '#ff0000';
                ctx.beginPath();
                ctx.arc(point.x, point.y, 5, 0, 2 * Math.PI);
                ctx.fill();
            }
        });
    }
    
    // 显示教练提示
    function showCoachTip(message) {
        const coachTip = document.getElementById('coach-tip');
        coachTip.textContent = message;
        
        // 添加动画效果
        coachTip.classList.add('active');
        setTimeout(() => {
            coachTip.classList.remove('active');
        }, 3000);
    }
    
    // 攻击怪物
    function attackMonster() {
        if (gameState.currentMonsterHp <= 0) return;
        
        // 計算攻擊傷害
        const damage = calculateDamage();
        
        // 減少怪物血量
        gameState.currentMonsterHp = Math.max(0, gameState.currentMonsterHp - damage);
        
        // 更新怪物血量顯示
        document.getElementById('monster-hp').textContent = gameState.currentMonsterHp;
        document.getElementById('monster-hp-bar').style.width = `${(gameState.currentMonsterHp / gameState.monsterMaxHp) * 100}%`;
        
        // 播放攻擊動畫
        const monsterContainer = document.getElementById('monster-container');
        if (monsterContainer) {
            monsterContainer.classList.add('hit');
            setTimeout(() => {
                monsterContainer.classList.remove('hit');
            }, 300);
        }
        
        // 顯示傷害數字
        showDamageNumber(damage);
        
        // 播放攻擊音效
        playSound('attack');
        
        console.log(`攻擊怪物，造成 ${damage} 點傷害，怪物剩餘血量: ${gameState.currentMonsterHp}`);
        
        // 檢查怪物是否被擊敗
        if (gameState.currentMonsterHp <= 0) {
            monsterDefeated();
        }
    }

    function showDamageNumber(damage) {
        const monsterContainer = document.getElementById('monster-container');
        if (!monsterContainer) return;
        
        const damageElement = document.createElement('div');
        damageElement.className = 'damage-number';
        damageElement.textContent = `-${damage}`;
        
        // 隨機位置
        const randomX = Math.random() * 60 - 30;
        const randomY = Math.random() * 20 - 10;
        
        damageElement.style.left = `calc(50% + ${randomX}px)`;
        damageElement.style.top = `calc(50% + ${randomY}px)`;
        
        monsterContainer.appendChild(damageElement);
        
        // 動畫結束後移除元素
        setTimeout(() => {
            damageElement.remove();
        }, 1000);
    }
    
    // 播放攻击动画
    function playAttackAnimation() {
        // 创建攻击特效
        const attackEffect = document.createElement('div');
        attackEffect.className = 'attack-effect';
        monsterContainer.appendChild(attackEffect);
        
        // 设置随机位置
        const x = Math.random() * 80 + 10; // 10% 到 90%
        const y = Math.random() * 80 + 10; // 10% 到 90%
        attackEffect.style.left = `${x}%`;
        attackEffect.style.top = `${y}%`;
        
        // 动画结束后移除
        setTimeout(() => {
            attackEffect.remove();
        }, 500);
        
        // 怪物受击动画
        if (monster) {
            monster.position.x += (Math.random() - 0.5) * 0.2;
            monster.position.y += (Math.random() - 0.5) * 0.2;
            
            // 恢复原位
            setTimeout(() => {
                if (monster) {
                    monster.position.x = 0;
                    monster.position.y = -1;
                }
            }, 300);
        }
    }
    
    // 怪物攻击
    function monsterAttack() {
        // 只有在怪物还活着时才攻击
        if (gameState.currentMonsterHp > 0) {
            // 计算伤害值
            const damage = Math.floor(Math.random() * 5) + 1; // 1-5点伤害
            
            // 减少玩家血量
            gameState.playerHp = Math.max(0, gameState.playerHp - damage);
            
            // 更新玩家血量显示
            document.getElementById('player-hp').textContent = gameState.playerHp;
            document.getElementById('player-hp-bar').style.width = `${gameState.playerHp}%`;
            
            // 播放受击动画
            document.querySelector('.video-container').classList.add('hit');
            setTimeout(() => {
                document.querySelector('.video-container').classList.remove('hit');
            }, 300);
            
            // 显示怪物对话
            const dialogues = [
                '尝尝这个！',
                '你太弱了！',
                '再来一次！',
                '这就是我的力量！',
                '投降吧！'
            ];
            document.getElementById('monster-dialogue').textContent = dialogues[Math.floor(Math.random() * dialogues.length)];
            document.getElementById('monster-dialogue').classList.add('active');
            setTimeout(() => {
                document.getElementById('monster-dialogue').classList.remove('active');
            }, 2000);
            
            // 检查玩家是否失败
            if (gameState.playerHp <= 0) {
                gameOver();
            }
        }
    }
    
    // 完成一组运动
    function completeSet() {
        gameState.currentSets++;
        gameState.currentReps = 0;
        
        // 更新UI
        document.getElementById('set-count').textContent = gameState.currentSets;
        document.getElementById('rep-count').textContent = 0;
        
        // 播放音效
        playSound('set_complete');
        
        // 显示提示
        if (gameState.currentSets < gameState.targetSets) {
            showCoachTip(`完成第${gameState.currentSets}组！休息一下，准备下一组。`);
        } else {
            // 所有组数完成，击败当前怪物
            defeatMonster(true); // 强制击败
        }
    }
    
    // 击败怪物
    function defeatMonster(force = false) {
        // 增加击败怪物计数
        gameState.monstersDefeated++;
        
        // 更新UI
        document.getElementById('monsters-defeated').textContent = gameState.monstersDefeated;
        
        // 播放击败动画
        if (monster) {
            // 怪物消失动画
            const fadeOut = setInterval(() => {
                if (monster.scale.x > 0.1) {
                    monster.scale.x -= 0.05;
                    monster.scale.y -= 0.05;
                    monster.scale.z -= 0.05;
                    monster.position.y -= 0.05;
                } else {
                    clearInterval(fadeOut);
                    scene.remove(monster);
                    monster = null;
                }
            }, 50);
        }
        
        // 播放音效
        playSound('monster_defeated');
        
        // 显示提示
        showCoachTip(`击败了怪物！${gameState.monstersDefeated}/${gameState.monsterCount}`);
        
        // 检查是否完成关卡
        if (gameState.monstersDefeated >= gameState.monsterCount) {
            completeLevel();
        } else {
            // 重置运动计数，准备下一个怪物
            if (!force) {
                gameState.currentReps = 0;
                document.getElementById('rep-count').textContent = 0;
            }
            
            // 重置怪物血量
            gameState.currentMonsterHp = gameState.currentMonsterMaxHp;
            
            // 3秒后生成新怪物
            setTimeout(() => {
                // 重新加载怪物模型
                initScene();
                
                // 更新UI
                document.getElementById('monster-hp').textContent = gameState.currentMonsterHp;
                document.getElementById('monster-hp-bar').style.width = '100%';
                
                // 显示提示
                showCoachTip('新的怪物出现了！继续运动来击败它！');
            }, 3000);
        }
    }
    
    // 完成关卡
    function completeLevel() {
        gameState.levelComplete = true;
        
        // 停止检测
        socket.emit('stop_detection');
        
        // 计算奖励
        const expReward = gameState.monsterCount * 50;
        
        // 更新用户进度
        updateUserProgress(expReward);
        
        // 显示关卡完成弹窗
        document.getElementById('exp-reward').textContent = `+${expReward}`;
        document.getElementById('monsters-defeated-count').textContent = gameState.monstersDefeated;
        
        // 显示弹窗
        levelCompleteModal.style.display = 'block';
    }
    
    // 游戏结束
    function gameOver() {
        // 停止检测
        socket.emit('stop_detection');
        
        // 显示游戏结束提示
        showCoachTip('你的生命值耗尽了！游戏结束。');
        
        // 3秒后返回地图
        setTimeout(() => {
            window.location.href = '/game/map';
        }, 3000);
    }
    
    // 更新用户进度
    async function updateUserProgress(expReward) {
        try {
            const response = await fetch('/api/game/update_progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: gameState.userId,
                    exercise_type: gameState.currentExercise,
                    reps: gameState.targetReps * gameState.targetSets,
                    sets: gameState.targetSets
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 检查是否升级
                if (data.level_up) {
                    showCoachTip(`恭喜！你已升级到第${data.next_level.level_id}关！`);
                    
                    // 显示新成就
                    if (data.new_achievements && data.new_achievements.length > 0) {
                        const achievementsContainer = document.getElementById('new-achievements-container');
                        achievementsContainer.innerHTML = '<h3>新解锁成就</h3>';
                        
                        data.new_achievements.forEach(achievement => {
                            const achievementItem = document.createElement('div');
                            achievementItem.className = 'achievement-item';
                            achievementItem.innerHTML = `
                                <div class="achievement-icon">🏆</div>
                                <div class="achievement-info">
                                    <div class="achievement-name">${achievement.name}</div>
                                    <div class="achievement-desc">${achievement.description}</div>
                                </div>
                            `;
                            achievementsContainer.appendChild(achievementItem);
                        });
                    }
                }
            }
        } catch (error) {
            console.error('更新用户进度失败:', error);
        }
    }
    
    // 播放音效
    function playSound(soundName) {
        const audio = new Audio(`/static/sounds/${soundName}.mp3`);
        audio.volume = 0.5;
        audio.play().catch(error => {
            console.warn('播放音效失败:', error);
        });
    }
    
    // 更新UI
    function updateUI() {
        document.getElementById('current-exercise').textContent = gameState.currentExercise === 'squat' ? '深蹲' : 
                                                                 gameState.currentExercise === 'push-up' ? '俯卧撑' : 
                                                                 gameState.currentExercise === 'bicep-curl' ? '二头肌弯举' : 
                                                                 gameState.currentExercise;
        
        document.getElementById('rep-count').textContent = gameState.currentReps;
        document.getElementById('set-count').textContent = gameState.currentSets;
        document.getElementById('target-reps').textContent = gameState.targetReps;
        document.getElementById('target-sets').textContent = gameState.targetSets;
        
        document.getElementById('player-hp').textContent = gameState.playerHp;
        document.getElementById('player-hp-bar').style.width = `${gameState.playerHp}%`;
        
        document.getElementById('monster-hp').textContent = gameState.currentMonsterHp;
        document.getElementById('monster-max-hp').textContent = gameState.currentMonsterMaxHp;
        document.getElementById('monster-hp-bar').style.width = `${(gameState.currentMonsterHp / gameState.currentMonsterMaxHp) * 100}%`;
        
        document.getElementById('monsters-defeated').textContent = gameState.monstersDefeated;
        document.getElementById('total-monsters').textContent = gameState.monsterCount;
    }
});