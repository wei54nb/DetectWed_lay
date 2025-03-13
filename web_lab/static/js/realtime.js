

document.addEventListener('DOMContentLoaded', () => {
    // 使用正确的命名空间连接
    const startButton = document.getElementById('start-detection');
    const stopButton = document.getElementById('stop-detection');
    const exerciseSelect = document.getElementById('exercise-type');
    const videoFeed = document.getElementById('video-feed');
    const exerciseCount = document.getElementById('exercise-count');
    const exerciseCountStats = document.getElementById('exercise-count-stats');
    const remainingSetsDisplay = document.getElementById('remaining-sets');
    const coachTipText = document.querySelector('.coach-tip-text');
    const qualityScore = document.querySelector('.quality-value');
    const qualityTitle = document.querySelector('.quality-title');
    const qualityDisplay = document.querySelector('.quality-display');
    const setDetectionLineButton = document.getElementById('set-detection-line');
    const resetCountButton = document.getElementById('reset-count');
    const exportExcelButton = document.getElementById('export-excel');
    const socket = io.connect('/exercise');


    let scene, camera, renderer;
    let monster;
    let monsterHP = 100;
    const monsterMaxHP = 100;
    let monsterState = 'idle'; // 初始狀態
    let monsterAnimationMixer;
    let monsterAnimations = {};
    let lastAnimationTime = 0;
    let floatingSpeed = 0.005;
    let startY = 0; // 調整初始Y軸位置
    let monsterDialogueTimer = null; // 怪物對話計時器
    let lastMonsterHPThreshold = 100; // 上次觸發動作的血量閾值
    
    // 初始化怪物3D場景
    initMonsterScene();

    function initMonsterScene() {
        // 創建場景
        scene = new THREE.Scene();
        scene.background = null; // 確保背景透明
    
        // 設置相機 - 調整相機參數以顯示全身模型
        camera = new THREE.PerspectiveCamera(40, 1, 0.1, 1000);
        // 將相機位置調整到更遠的位置
        camera.position.set(0, 0, 100); // 增加相機距離，從20調整到30
        camera.lookAt(0, -3, 0); // 調整視角更向下，從-3調整到-5
    
        // 設置渲染器
        renderer = new THREE.WebGLRenderer({
            alpha: true,
            antialias: true
        });
        
        // 調整渲染大小 - 使用固定尺寸
        const size = 300; // 調整尺寸
        renderer.setSize(size, size);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setClearColor(0x000000, 0);
    
        // 將渲染器添加到特定容器中 - 修正位置問題
        const monsterContainer = document.getElementById('monster-scene-container');
        if (monsterContainer) {
            // 清空現有內容
            monsterContainer.innerHTML = '';
            // 添加渲染器到指定容器
            monsterContainer.appendChild(renderer.domElement);
            // 確保容器有適當的樣式
            monsterContainer.style.width = `${size}px`;
            monsterContainer.style.height = `${size}px`;
            monsterContainer.style.position = 'relative'; // 使用相對定位而非絕對定位
            monsterContainer.style.overflow = 'hidden';
        } else {
            console.error("找不到怪物容器元素，無法添加3D場景");
            return; // 如果找不到容器，則退出初始化
        }
    

        // 環境光 - 提高亮度
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8); // 增加環境光強度
        scene.add(ambientLight);
    
        // 主光源 - 從前上方照射
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
        directionalLight.position.set(0, 5, 10);
        scene.add(directionalLight);
    
        // 補充光源 - 從左側照射
        const leftLight = new THREE.DirectionalLight(0xffffff, 0.8);
        leftLight.position.set(-5, 0, 5);
        scene.add(leftLight);
    
        // 補充光源 - 從右側照射
        const rightLight = new THREE.DirectionalLight(0xffffff, 0.8);
        rightLight.position.set(5, 0, 5);
        scene.add(rightLight);
    
        // 底部填充光 - 避免底部過暗
        const bottomLight = new THREE.DirectionalLight(0xffffff, 0.5);
        bottomLight.position.set(0, -5, 5);
        scene.add(bottomLight);
    
        // 載入模型
        loadMonsterModel('idle');
    
        // 添加窗口大小調整監聽器
        window.addEventListener('resize', onWindowResize, false);
        
        // 開始動畫循環
        animate();
    }



    function loadMonsterModel(state) {
        const loader = new THREE.GLTFLoader();
        // 根據狀態選擇不同的模型文件
        let modelPath = `/static/models/${state}.glb`;
        
        // 如果是特殊狀態但文件不存在，使用默認模型
        const fallbackStates = {
            'run': 'idle',
            'attack': 'idle',
            'provocative': 'idle',
            'start': 'idle'
        };
        
        loader.load(
            modelPath,
            function (gltf) {
                // 如果已有模型，先移除
                if (monster) {
                    scene.remove(monster);
                }
                
                monster = gltf.scene;
                // 調整模型大小和位置
                monster.scale.set(0.5, 0.5, 0.5);
                monster.position.set(0, -3, 0);
                monster.rotation.y = 0; // 確保模型正
                
                // 遍歷模型的所有部分，確保材質正確
                monster.traverse((child) => {
                    if (child.isMesh) {
                        // 確保材質正確渲染
                        child.material.side = THREE.DoubleSide; // 雙面渲染
                        child.material.transparent = true; // 支持透明
                        child.material.needsUpdate = true; // 更新材質
                        
                        // 提高材質亮度
                        if (child.material.color) {
                            // 提高顏色亮度，但不要過白
                            const color = child.material.color;
                            color.r = Math.min(1, color.r * 1.2);
                            color.g = Math.min(1, color.g * 1.2);
                            color.b = Math.min(1, color.b * 1.2);
                        }
                        
                        // 如果有法線貼圖，確保正確應用
                        if (child.material.normalMap) {
                            child.material.normalScale.set(1, 1);
                        }
                    }
                });
                
                scene.add(monster);
                console.log(`✅ 怪物模型(${state})載入成功！`);
                
                // 設置動畫
                if (gltf.animations && gltf.animations.length > 0) {
                    monsterAnimationMixer = new THREE.AnimationMixer(monster);
                    
                    gltf.animations.forEach((clip) => {
                        const action = monsterAnimationMixer.clipAction(clip);
                        monsterAnimations[state] = action;
                        
                        // 如果是逃跑動畫，設置只播放一次
                        if (state === 'run') {
                            action.setLoop(THREE.LoopOnce);
                            action.clampWhenFinished = true;
                        }
                        
                        action.play();
                    });
                }
                
                monsterState = state;

                // 如果是新載入的怪物，根據當前血量顯示適當的對話
                if (monsterHP <= 75 && monsterHP > 50) {
                    showMonsterDialogue('你的攻擊還不錯嘛，再加把勁！');
                } else if (monsterHP <= 50 && monsterHP > 25) {
                    showMonsterDialogue('唔...你的力量讓我感到威脅了...');
                } else if (monsterHP <= 25 && monsterHP > 0) {
                    showMonsterDialogue('我快撐不住了...再堅持一下！');
                }

            },
            function (progress) {
                console.log('載入進度:', (progress.loaded / progress.total * 100) + '%');
            },
            function (error) {
                console.error(`❌ 怪物模型(${state})載入失敗！`, error);
                // 如果載入失敗，嘗試載入默認模型
                if (state !== 'idle') {
                    loadMonsterModel('idle');
                }
            }
        );
    }

    function showMonsterDialogue(text, duration = 4000) {
        // 檢查是否已存在對話框，如果有則移除
        const existingDialogue = document.querySelector('.monster-dialogue');
        if (existingDialogue) {
            existingDialogue.remove();
        }
        
        // 創建新的對話框
        const dialogue = document.createElement('div');
        dialogue.className = 'monster-dialogue';
        dialogue.textContent = text;
        
        // 添加到怪物容器中
        const monsterContainer = document.getElementById('monster-scene-container');
        if (monsterContainer) {
            monsterContainer.parentElement.appendChild(dialogue);
            
            // 調整對話框位置，將其放在更下方
            dialogue.style.top = '-10px'; // 從-60px調整到-30px，讓對話框更靠近怪獸

            // 設置定時器自動移除對話框
            if (monsterDialogueTimer) {
                clearTimeout(monsterDialogueTimer);
            }
            
            monsterDialogueTimer = setTimeout(() => {
                dialogue.classList.add('fade-out');
                setTimeout(() => dialogue.remove(), 500);
            }, duration);
            
            // 確保對話框完全可見
            setTimeout(() => {
                const dialogueRect = dialogue.getBoundingClientRect();
                const containerRect = monsterContainer.getBoundingClientRect();
                
                // 如果對話框頂部超出視窗，調整位置
                if (dialogueRect.top < 0) {
                    dialogue.style.top = '0px'; // 確保至少在視窗內
                    dialogue.style.bottom = 'auto';
                }
            }, 10);
        }
    }

    function updateMonsterStateByHP() {
        // 血量閾值和對應的狀態及對話
        const hpThresholds = [
            { threshold: 75, state: 'provocative', dialogue: '哈哈，就這麼點能耐嗎，真遜！' },
            { threshold: 50, state: 'attack', dialogue: '你打得我好痛！我要反擊了！' },
            { threshold: 25, state: 'idle', dialogue: '我...我快不行了...' },
            { threshold: 0, state: 'run', dialogue: '好討厭的感覺~~~我要逃走了！' }
        ];
        
        // 檢查當前血量是否低於任何閾值
        for (const { threshold, state, dialogue } of hpThresholds) {
            if (monsterHP <= threshold && lastMonsterHPThreshold > threshold) {
                // 更新上次觸發的閾值
                lastMonsterHPThreshold = threshold;
                
                // 更改怪物狀態
                changeMonsterState(state);
                
                // 顯示對話
                showMonsterDialogue(dialogue);
                
                // 如果血量為0，設置逃跑動畫後隱藏
                if (threshold === 0) {
                    setTimeout(() => {
                        if (monster) monster.visible = false;
                        
                        // 顯示擊敗提示
                        const defeatModal = document.createElement('div');
                        defeatModal.className = 'completion-modal';
                        defeatModal.innerHTML = `
                            <div class="completion-content">
                                <h2>🎉 恭喜擊敗怪物！</h2>
                                <p>你獲得了 ${parseInt(exerciseCount.textContent) * 5} 點經驗值！</p>
                                <button onclick="this.parentElement.parentElement.remove(); monsterHP = 100; lastMonsterHPThreshold = 100; updateHPDisplay(); if(monster) { monster.visible = true; changeMonsterState('idle'); }">繼續訓練</button>
                            </div>
                        `;
                        document.body.appendChild(defeatModal);
                    }, 3000); // 3秒後隱藏怪物
                }
                
                break;
            }
        }
    }



    
    function changeMonsterState(newState) {
        if (monsterState === newState) return;
        
        // 檢查是否需要載入新模型
        if (!monsterAnimations[newState]) {
            loadMonsterModel(newState);
        } else {
            // 停止當前動畫
            if (monsterAnimations[monsterState]) {
                monsterAnimations[monsterState].stop();
            }
            
            // 播放新動畫
            monsterAnimations[newState].play();
            monsterState = newState;
        }
    }
    
    function onWindowResize() {
        // 不再根據窗口大小調整，使用固定尺寸
        camera.aspect = 1; // 保持1:1比例
        camera.updateProjectionMatrix();
        
        // 渲染器大小保持不變
    }
    
    function animate() {
        requestAnimationFrame(animate);
        
        // 更新動畫混合器
        if (monsterAnimationMixer) {
            monsterAnimationMixer.update(0.016); // 約60fps
        }
        
        if (monster) {
            // 根據狀態添加不同的動作
            if (monsterState === 'idle') {
                // 保留上下浮動動畫，但減小浮動幅度
                monster.position.y = -5 + Math.sin(Date.now() * 0.001) * 0.05;
            } else if (monsterState === 'run') {
                // 逃跑動畫時，讓怪物向後移動
                monster.position.z -= 0.1;
            }
        }
        
        renderer.render(scene, camera);
    }

    
    // 怪物受傷效果
    function monsterHitEffect() {
        if (!monster) return;
        
        // 根據血量決定反應
        if (monsterHP > 75) {
            // 血量高時偶爾挑釁
            if (Math.random() > 0.7) {
                showMonsterDialogue('哈！這點攻擊根本不痛不癢！');
            }
        } else if (monsterHP > 50) {
            // 血量中高時顯示輕微受傷
            if (Math.random() > 0.6) {
                showMonsterDialogue('嗯...你的攻擊開始有點感覺了...');
            }
        } else if (monsterHP > 25) {
            // 血量中低時顯示明顯受傷
            if (Math.random() > 0.5) {
                showMonsterDialogue('啊！好痛！你真的很強！');
            }
        } else {
            // 血量很低時顯示瀕臨失敗
            if (Math.random() > 0.3) {
                showMonsterDialogue('不...我快不行了...饒了我吧！');
            }
        }
        
        // 隨機選擇動作：攻擊或挑釁
        const now = Date.now();
        if (now - lastAnimationTime > 3000) { // 至少3秒間隔
            // 根據血量選擇不同的反應
            let action;
            if (monsterHP > 50) {
                action = Math.random() > 0.5 ? 'attack' : 'provocative';
            } else {
                action = 'idle'; // 血量低時保持虛弱狀態
            }
            
            changeMonsterState(action);
            
            // 3秒後恢復閒置狀態
            setTimeout(() => {
                changeMonsterState('idle');
            }, 3000);
            
            lastAnimationTime = now;
        }
        
        monster.traverse((child) => {
            if (child.isMesh && child.material) {
                // 保存原始顏色
                const originalColor = child.material.color ? child.material.color.clone() : new THREE.Color(1, 1, 1);
                
                // 設置為紅色
                if (child.material.color) {
                    child.material.color.setRGB(1, 0, 0);
                } else {
                    child.material.color = new THREE.Color(1, 0, 0);
                }
                
                // 恢復原始顏色
                setTimeout(() => {
                    if (child.material.color) {
                        child.material.color.copy(originalColor);
                    }
                }, 200);
            }
        });
    }
    
    // 更新血量顯示
    function updateHPDisplay() {
        const hpElement = document.getElementById('monster-hp');
        if (hpElement) {
            hpElement.textContent = Math.max(0, monsterHP);
            // 添加血量變化的視覺效果
            hpElement.style.animation = 'pulse 0.5s ease-in-out';
            setTimeout(() => {
                hpElement.style.animation = '';
            }, 500);
        }
    }
    
    // 顯示傷害數字
    function showDamageText(damage) {
        const damageText = document.createElement('div');
        damageText.className = 'damage-text';
        damageText.textContent = `-${damage}`;
        
        // 設置初始位置（在怪物血條附近）
        const randomX = Math.random() * 100 - 50;
        const randomY = Math.random() * 50;
        damageText.style.position = 'fixed';
        damageText.style.right = `calc(10% + ${randomX}px)`;
        damageText.style.top = `calc(30% + ${randomY}px)`;
        
        // 添加樣式
        damageText.style.color = '#ff0000';
        damageText.style.fontWeight = 'bold';
        damageText.style.fontSize = '24px';
        damageText.style.textShadow = '2px 2px 4px rgba(0,0,0,0.5)';
        
        document.body.appendChild(damageText);
        
        // 添加動畫
        requestAnimationFrame(() => {
            damageText.style.transition = 'all 1s ease-out';
            damageText.style.transform = 'translateY(-100px)';
            damageText.style.opacity = '0';
        });
        
        // 移除元素
        setTimeout(() => {
            damageText.remove();
        }, 1000);
    }
    
    // 更新怪物信息
    function updateMonsterInfo(data) {
        if (!monsterContainer) return;
        
        const monsterInfoDisplay = document.querySelector('.monster-display');
        if (!monsterInfoDisplay) {
            const infoDisplay = document.createElement('div');
            infoDisplay.classList.add('monster-display');
            document.body.appendChild(infoDisplay);
            
            infoDisplay.innerHTML = `
                <h3>🐲 怪物狀態</h3>
                <div><strong>名稱:</strong> ${data.name || '未知'}</div>
                <div><strong>健康值:</strong> 
                    <span style="color:${data.health < 30 ? '#F44336' : '#4CAF50'}">${data.health || 0}/100</span>
                </div>
                <div><strong>經驗值:</strong> ${data.exp || 0}</div>
                <div><strong>等級:</strong> ${data.level || 1}</div>
                <div><strong>狀態:</strong> ${data.status || '正常'}</div>
            `;
        } else {
            monsterInfoDisplay.innerHTML = `
                <h3>🐲 怪物狀態</h3>
                <div><strong>名稱:</strong> ${data.name || '未知'}</div>
                <div><strong>健康值:</strong> 
                    <span style="color:${data.health < 30 ? '#F44336' : '#4CAF50'}">${data.health || 0}/100</span>
                </div>
                <div><strong>經驗值:</strong> ${data.exp || 0}</div>
                <div><strong>等級:</strong> ${data.level || 1}</div>
                <div><strong>狀態:</strong> ${data.status || '正常'}</div>
            `;
        }
    }

    socket.on('exercise_count_update', function(data) {
        console.log("Received exercise_count_update:", data);
        exerciseCount.textContent = data.count;
        exerciseCountStats.textContent = data.count;
        exerciseReps++;
        
        // 檢查成就
        handleExerciseAchievement(parseInt(data.count), exerciseSelect.value);
        
        const repsGoal = parseInt(document.getElementById('reps').value) || 0;
        if (repsGoal > 0 && exerciseReps >= repsGoal && remainingSets > 0) {
            exerciseReps = 0;
            remainingSets--;
            remainingSetsDisplay.textContent = remainingSets;
            if (remainingSets <= 0) {
                showCompletionMessage();
                stopButton.click();
            }
        }
        
        // 怪物受傷處理
        if (monsterHP > 0) {
            const damage = 10;
            monsterHP = Math.max(0, monsterHP - damage);

            // 更新血量顯示
            updateHPDisplay();

            // 顯示傷害數字
            showDamageText(damage);

            // 觸發怪物受傷效果
            monsterHitEffect();
            
            // 根據血量更新怪物狀態
            updateMonsterStateByHP();

            // 更新怪物信息
            updateMonsterInfo({
                name: "訓練怪獸",
                health: monsterHP,
                exp: parseInt(data.count) * 5,
                level: Math.floor(parseInt(data.count) / 10) + 1,
                status: monsterHP <= 30 ? "虛弱" : "正常"
            });

            // 檢查怪物是否死亡
            if (monsterHP <= 0) {
                if (monster) {
                    // 播放死亡動畫
                    changeMonsterState('idle');
                    setTimeout(() => {
                        monster.visible = false;
                    }, 1000);
                    
                    // 顯示擊敗提示
                    const defeatModal = document.createElement('div');
                    defeatModal.className = 'completion-modal';
                    defeatModal.innerHTML = `
                        <div class="completion-content">
                            <h2>🎉 恭喜擊敗怪物！</h2>
                            <p>你獲得了 ${parseInt(data.count) * 5} 點經驗值！</p>
                            <button onclick="this.parentElement.parentElement.remove(); monsterHP = 100; updateHPDisplay(); if(monster) monster.visible = true;">繼續訓練</button>
                        </div>
                    `;
                    document.body.appendChild(defeatModal);
                }
            }
        }
    });
    
    // 當選擇不同的運動類型時重置怪物
    exerciseSelect.addEventListener('change', function() {
        // 重置怪物血量
        monsterHP = monsterMaxHP;
        updateHPDisplay();
        
        // 如果怪物不可見，重新顯示
        if (monster && !monster.visible) {
            monster.visible = true;
        }
        
        // 根據運動類型切換怪物動作
        switch(this.value) {
            case 'squat':
                changeMonsterState('provocative');
                setTimeout(() => changeMonsterState('idle'), 3000);
                break;
            case 'bicep-curl':
                changeMonsterState('attack');
                setTimeout(() => changeMonsterState('idle'), 3000);
                break;
            default:
                changeMonsterState('idle');
        }
    });
    
    // 當開始偵測時，顯示怪物出場動畫
    startButton.addEventListener('click', function() {
        // 如果怪物已載入，播放出場動畫
        if (monster) {
            changeMonsterState('start');
            setTimeout(() => changeMonsterState('idle'), 3000);
        }
    });
    
    // 當停止偵測時，隱藏怪物
    stopButton.addEventListener('click', function() {
        // 如果有怪物，先播放離場動畫，然後隱藏
        if (monster) {
            changeMonsterState('idle');
            setTimeout(() => {
                if (monster) monster.visible = false;
            }, 1000);
        }
    });
    
    // 初始化怪物系統
    updateHPDisplay();
    
    // 怪物事件监听
    socket.on('monster_event', (data) => {
        try {

            if (data.health && data.health < 20) {
                alert('注意：怪物即將被打倒！');
            }
        } catch (error) {
            console.error('處理怪物數據錯誤:', error);
            alert('無法更新怪物資訊，請稍後再試！');
        }
    });

    // 確保所有關鍵元素存在的檢查
    const requiredElements = [
        {element: startButton, name: '開始偵測按鈕'},
        {element: stopButton, name: '停止偵測按鈕'},
        {element: exerciseSelect, name: '運動類型選擇'},
        {element: videoFeed, name: '視頻源'},
        {element: exerciseCount, name: '運動次數顯示'},
        {element: coachTipText, name: '教練提示文本'}
    ];

    const missingElements = requiredElements.filter(item => !item.element);
    if (missingElements.length > 0) {
        console.error('以下元素未找到:', missingElements.map(item => item.name).join(', '));
        alert('頁面初始化失敗，請重新載入頁面');
        return;
    }

    // 設定初始按鈕狀態
    startButton.disabled = false;
    stopButton.disabled = true;

    // 初始化變數
    let exerciseReps = 0;
    let remainingSets = 0;
    let detectionLineY = null;
    let currentQualityScore = 0;
    let scoreResetTimer = null;
    const SCORE_RESET_TIMEOUT = 10000; // 10秒後無更新則歸零

    // 全域變數，用於二頭彎舉記數狀態
    let bicep_state = "down";
    let last_curl_time = 0;

    // Socket.IO 事件處理
    socket.on('connect', () => {
        console.log('已連接到 Socket.IO 伺服器');
        if (document.getElementById('connection-status')) {
            document.getElementById('connection-status').textContent = '已连接';
            document.getElementById('connection-status').style.color = 'green';
        }
    });

    socket.on('disconnect', () => {
        console.log('与服务器断开连接');
        if (document.getElementById('connection-status')) {
            document.getElementById('connection-status').textContent = '已断开';
            document.getElementById('connection-status').style.color = 'red';
        }
    });

    socket.on('video_frame', (data) => {
        if (videoFeed) {
            videoFeed.src = 'data:image/jpeg;base64,' + data.frame;
        }
    });

    socket.on('exercise_count', (data) => {
        if (exerciseCount) {
            exerciseCount.textContent = data.count;
        }
        
        // 如果有质量评分，更新质量评分
        if (data.quality !== undefined && document.getElementById('quality-score')) {
            document.getElementById('quality-score').textContent = data.quality;
        }
    });

    // 監聽各運動評分事件
    socket.on('squat_quality', (data) => {
        console.log("收到深蹲品質評分數據:", data);
        if (!data || typeof data.score === 'undefined') {
            console.error("深蹲品質評分數據格式不正確:", data);
            return;
        }
        updateQualityScore('squat_quality', data);
    });

    socket.on('shoulder_press_score', (data) => {
        console.log("Received shoulder_press_score:", data);
        updateQualityScore('shoulder_press_score', data);
    });

    socket.on('bicep_curl_score', (data) => {
        console.log("Received bicep_curl_score:", data);
        updateQualityScore('bicep_curl_score', data);
    });

    socket.on('exercise_count_update', (data) => {
        console.log("Received exercise_count_update:", data);
        exerciseCount.textContent = data.count;
        exerciseCountStats.textContent = data.count;
        exerciseReps++;
        const repsGoal = parseInt(document.getElementById('reps').value) || 0;
        if (repsGoal > 0 && exerciseReps >= repsGoal && remainingSets > 0) {
            exerciseReps = 0;
            remainingSets--;
            remainingSetsDisplay.textContent = remainingSets;
            if (remainingSets <= 0) {
                alert("已完成所有組數！");
                stopButton.click();
            }
        }
    });

    socket.on('angle_data', (data) => {
        console.log("收到角度數據:", data);
        if (!data || Object.keys(data).length === 0) {
            console.error("角度數據為空或格式不正確");
            return;
        }
        // 更新角度顯示
        const angleDisplay = document.querySelector('.angle-display');
        if (angleDisplay) {
            angleDisplay.innerHTML = "";
            for (let key in data) {
                const angleElement = document.createElement("div");
                angleElement.classList.add("angle-card");
                angleElement.innerHTML = `<div class="angle-label">${key}</div>
                                    <div class="angle-value">${data[key].toFixed(1)}°</div>`;
                angleDisplay.appendChild(angleElement);
            }
            // 根據角度數據生成教練提示
            updateCoachTips(data);
        }
    });

    socket.on('coach_tip', (data) => {
        console.log("收到教練提示:", data);
        if (coachTipText && data.tip) {
            coachTipText.textContent = data.tip;
        }
    });

    socket.on('detection_line_set', (data) => {
        if (data.error) {
            alert(`設置偵測線失敗：${data.error}`);
        } else {
            detectionLineY = data.detection_line_y;
            alert(`偵測線已設定完成！位置：${detectionLineY}px`);
        }
    });

    // 開始偵測按鈕事件
    if (startButton) {
        function handleFetchError(error, context) {
            console.error(`${context} 錯誤:`, error);
            alert(`${context}失敗：${error.message || '未知錯誤'}`);
        }

        startButton.addEventListener('click', () => {
            const exerciseType = exerciseSelect.value;
            const weight = document.getElementById('weight').value;
            const reps = document.getElementById('reps').value;
            const sets = document.getElementById('sets').value;
            const studentId = document.getElementById('student-id').value;

            console.log("開始偵測 - 發送請求參數:", {exerciseType, weight, reps, sets, studentId});
            fetch(`/exercise/start_detection?exercise_type=${exerciseType}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({weight, reps, sets, student_id: studentId})
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('後端回應失敗');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    exerciseCount.textContent = '0';
                    exerciseReps = 0;
                    remainingSets = parseInt(sets) || 0;
                    remainingSetsDisplay.textContent = remainingSets;
                    videoFeed.src = `/exercise/video_feed?t=${new Date().getTime()}`;
                    coachTipText.textContent = '正在偵測，請保持動作標準...';

                    // 重置品質評分
                    if (qualityScore) {
                        qualityScore.textContent = '0';
                        qualityScore.style.color = '';
                    }
                    currentQualityScore = 0;

                    // 根據運動類型顯示/隱藏品質評分
                    if (qualityDisplay) {
                        qualityDisplay.style.display = (exerciseType === 'squat' || exerciseType === 'shoulder-press' || exerciseType === 'bicep-curl') ? 'block' : 'none';
                    }

                    resetScoreTimer();
                } else {
                    throw new Error('後端回應失敗');
                }
            })
            .catch(error => {
                console.error('開始偵測錯誤:', error);
                alert(`啟動偵測失敗: ${error.message}`);
            });
        });
    }

    // 停止偵測按鈕事件
    if (stopButton) {
        stopButton.addEventListener('click', () => {
            console.log("停止偵測 - 發送請求");
            fetch('/exercise/stop_detection', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => {
                if (!response.ok) throw new Error('停止偵測失敗');
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    videoFeed.src = '';
                    coachTipText.textContent = '偵測已停止，請重新開始以獲得建議。';
                    exerciseReps = 0;
                    remainingSets = 0;
                    remainingSetsDisplay.textContent = '0';

                    if (scoreResetTimer) {
                        clearTimeout(scoreResetTimer);
                        scoreResetTimer = null;
                    }

                    if (qualityScore) {
                        qualityScore.textContent = '0';
                        qualityScore.style.color = '';
                    }
                    currentQualityScore = 0;
                } else {
                    throw new Error('後端回應失敗');
                }
            })
            .catch(error => {
                console.error('停止偵測錯誤:', error);
                alert(`停止偵測失敗: ${error.message}`);
            });
        });
    }

    // 設置偵測線按鈕事件
    if (setDetectionLineButton) {
        setDetectionLineButton.addEventListener('click', () => {
            socket.emit('set_detection_line');
            alert('正在啟動攝像機並設置偵測線，請在鏡頭前保持站立姿勢，系統將根據您的髖關節位置設置偵測線');
            videoFeed.src = `/video_feed?t=${new Date().getTime()}`;
        });
    }

    // 重置计数按钮事件
    if (resetCountButton) {
        resetCountButton.addEventListener('click', () => {
            socket.emit('reset_count');
            console.log('发送重置计数请求');
        });
    }
    
    // 导出Excel按钮事件
    if (exportExcelButton) {
        exportExcelButton.addEventListener('click', () => {
            const studentId = document.getElementById('student-id').value;
            const exerciseType = exerciseSelect.value;
            const weight = document.getElementById('weight').value;
            const count = exerciseCount.textContent;
            
            if (!studentId) {
                alert('請先輸入學號');
                return;
            }
            
            console.log('导出Excel数据:', {studentId, exerciseType, weight, count});
            
            fetch('/exercise/export_data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    student_id: studentId,
                    exercise_type: exerciseType,
                    weight: weight,
                    count: count
                })
            })
            .then(response => {
                if (!response.ok) throw new Error('導出數據失敗');
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `exercise_data_${studentId}_${new Date().toISOString().slice(0,10)}.xlsx`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                alert('數據導出成功！');
            })
            .catch(error => {
                console.error('導出數據錯誤:', error);
                alert(`導出數據失敗: ${error.message}`);
            });
        });
    }

    // 運動類型變更時更新品質評分標題和重置分數
    if (exerciseSelect) {
        exerciseSelect.addEventListener('change', () => {
            const exerciseType = exerciseSelect.value;
            socket.emit('change_exercise_type', { exercise_type: exerciseType });
            console.log('发送更改运动类型请求:', exerciseType);
            
            switch (exerciseType) {
                case 'squat':
                    qualityTitle.textContent = '深蹲品質評分';
                    break;
                case 'shoulder-press':
                    qualityTitle.textContent = '肩推品質評分';
                    break;
                case 'bicep-curl':
                    qualityTitle.textContent = '二頭彎舉品質評分';
                    break;
                case 'push-up':
                    qualityTitle.textContent = '俯卧撑品質評分';
                    break;
                case 'pull-up':
                qualityTitle.textContent = '俯卧撑品質評分';
                    break;
                case 'pull-up':
                    qualityTitle.textContent = '引體向上品質評分';
                    break;
                case 'dumbbell-row':
                    qualityTitle.textContent = '啞鈴划船品質評分';
                    break;
                default:
                    qualityTitle.textContent = '品質評分';
            }
            
            if (qualityScore) {
                qualityScore.textContent = '0';
                qualityScore.style.color = '';
            }
            currentQualityScore = 0;
        });
        // 初始觸發一次 change 事件
        exerciseSelect.dispatchEvent(new Event('change'));
    }

    // 更新品質評分函數，支援 squat、shoulder-press 與 bicep-curl
    function updateQualityScore(event, data) {
        const currentExercise = exerciseSelect.value;
        const scoreEvents = {
            'squat': 'squat_quality',
            'shoulder-press': 'shoulder_press_score',
            'bicep-curl': 'bicep_curl_score'
        };
        
        if (event === scoreEvents[currentExercise] && qualityScore) {
            qualityScore.textContent = data.score;
            currentQualityScore = data.score;
            
            if (currentExercise === 'squat') {
                if (data.score >= 4) {
                    qualityScore.style.color = '#FFFFFF';
                } else if (data.score >= 3) {
                    qualityScore.style.color = '#FFC107';
                } else {
                    qualityScore.style.color = '#F44336';
                }
            } else if (currentExercise === 'shoulder-press') {
                if (data.score >= 80) {
                    qualityScore.style.color = '#FFFFFF';
                } else if (data.score >= 60) {
                    qualityScore.style.color = '#FFC107';
                } else {
                    qualityScore.style.color = '#F44336';
                }
            } else if (currentExercise === 'bicep-curl') {
                if (data.score >= 80) {
                    qualityScore.style.color = '#FFFFFF';
                } else if (data.score >= 60) {
                    qualityScore.style.color = '#FFC107';
                } else {
                    qualityScore.style.color = '#F44336';
                }
            }
            
            resetScoreTimer();
        }
    }

    // 重置分數計時器，如果長時間沒有更新分數則歸零
    function resetScoreTimer() {
        if (scoreResetTimer) {
            clearTimeout(scoreResetTimer);
        }
        
        scoreResetTimer = setTimeout(() => {
            if (qualityScore) {
                qualityScore.textContent = '0';
                qualityScore.style.color = '';
            }
            currentQualityScore = 0;
        }, SCORE_RESET_TIMEOUT);
    }

    // 更新教練提示函數
    function updateCoachTips(angleData) {
        if (!angleData || Object.keys(angleData).length === 0) {
            console.log("角度數據為空，無法生成教練提示");
            return;
        }
        
        let tips = '';
        const exerciseType = exerciseSelect.value;
        
        console.log(`生成${exerciseType}運動提示，使用角度數據:`, angleData);
        
        switch (exerciseType) {
            case 'squat':
                tips = getSquatTips(angleData);
                break;
            case 'shoulder-press':
                tips = getShoulderPressTips(angleData);
                break;
            case 'bicep-curl':
                tips = getBicepCurlTips(angleData);
                break;
            case 'push-up':
                tips = getPushUpTips(angleData);
                break;
            case 'pull-up':
                tips = getPullUpTips(angleData);
                break;
            case 'dumbbell-row':
                tips = getDumbbellRowTips(angleData);
                break;
            default:
                tips = '請選擇運動類型並開始偵測以獲得即時建議。';
        }
        
        if (coachTipText && tips) {
            console.log("更新教練提示:", tips);
            coachTipText.textContent = tips;
        }
    }

    // 深蹲提示
    function getSquatTips(angleData) {
        if (!angleData) return '正在分析您的深蹲動作...';
        
        let tips = '';
        
        // 檢查膝蓋角度
        if ('左膝蓋' in angleData && '右膝蓋' in angleData) {
            const leftKneeAngle = angleData['左膝蓋'];
            const rightKneeAngle = angleData['右膝蓋'];
            const avgKneeAngle = (leftKneeAngle + rightKneeAngle) / 2;
            
            if (avgKneeAngle < 90) {
                tips += '膝蓋彎曲過度，請注意不要讓膝蓋超過腳尖。\n';
            } else if (avgKneeAngle > 160) {
                tips += '膝蓋彎曲不足，請嘗試蹲得更深一些。\n';
            } else {
                tips += '膝蓋彎曲角度良好！\n';
            }
        }
        
        // 檢查髖部角度
        if ('左髖部' in angleData && '右髖部' in angleData) {
            const leftHipAngle = angleData['左髖部'];
            const rightHipAngle = angleData['右髖部'];
            const avgHipAngle = (leftHipAngle + rightHipAngle) / 2;
            
            if (avgHipAngle < 80) {
                tips += '髖部彎曲過度，請保持背部挺直。\n';
            } else if (avgHipAngle > 160) {
                tips += '髖部彎曲不足，請更加下蹲。\n';
            } else {
                tips += '髖部角度良好！\n';
            }
        }
        
        return tips || '請保持正確姿勢，開始深蹲運動。';
    }

    // 肩推提示
    function getShoulderPressTips(angleData) {
        if (!angleData) return '正在分析您的肩推動作...';
        
        let tips = '';
        
        // 檢查肘部角度
        if ('左手肘' in angleData && '右手肘' in angleData) {
            const leftElbowAngle = angleData['左手肘'];
            const rightElbowAngle = angleData['右手肘'];
            const avgElbowAngle = (leftElbowAngle + rightElbowAngle) / 2;
            
            if (avgElbowAngle < 90) {
                tips += '手臂彎曲過度，請嘗試將啞鈴推高至頭頂上方。\n';
            } else if (avgElbowAngle > 170) {
                tips += '手臂伸展良好，保持這個姿勢！\n';
            } else {
                tips += '繼續向上推，直到手臂完全伸直。\n';
            }
        }
        
        // 檢查肩部角度
        if ('左肩膀' in angleData && '右肩膀' in angleData) {
            const leftShoulderAngle = angleData['左肩膀'];
            const rightShoulderAngle = angleData['右肩膀'];
            const avgShoulderAngle = (leftShoulderAngle + rightShoulderAngle) / 2;
            
            if (avgShoulderAngle < 80) {
                tips += '肩部抬起不足，請將啞鈴推高至頭頂上方。\n';
            } else if (avgShoulderAngle > 170) {
                tips += '肩部角度良好，啞鈴位置正確！\n';
            } else {
                tips += '肩部需要更加伸展，請完全舉起啞鈴。\n';
            }
        }
        
        // 檢查左右平衡
        if ('左手肘' in angleData && '右手肘' in angleData) {
            const elbowDiff = Math.abs(angleData['左手肘'] - angleData['右手肘']);
            if (elbowDiff > 15) {
                tips += '左右手臂不平衡，請保持兩側均勻用力。\n';
            }
        }
        
        return tips || '請保持正確姿勢，開始肩推運動。';
    }

    // 二頭彎舉提示
    function getBicepCurlTips(angleData) {
        if (!angleData) return '正在分析您的二頭彎舉動作...';
        
        let tips = '';
        
        // 檢查肘部角度
        if ('左手肘' in angleData && '右手肘' in angleData) {
            const leftElbowAngle = angleData['左手肘'];
            const rightElbowAngle = angleData['右手肘'];
            const avgElbowAngle = (leftElbowAngle + rightElbowAngle) / 2;
            
            if (avgElbowAngle < 60) {
                tips += '手臂彎曲良好，保持這個姿勢！\n';
            } else if (avgElbowAngle > 150) {
                tips += '手臂伸展過直，請彎曲手肘舉起啞鈴。\n';
            } else {
                tips += '繼續彎曲手肘，將啞鈴舉至肩膀高度。\n';
            }
        }
        
        // 檢查肩部穩定性
        if ('左肩膀' in angleData && '右肩膀' in angleData) {
            const leftShoulderAngle = angleData['左肩膀'];
            const rightShoulderAngle = angleData['右肩膀'];
            
            // 理想的肩部角度應接近90度（手臂垂直於軀幹）
            const leftDeviation = Math.abs(90 - leftShoulderAngle);
            const rightDeviation = Math.abs(90 - rightShoulderAngle);
            
            if (leftDeviation > 20 || rightDeviation > 20) {
                tips += '肩部不穩定，請保持上臂貼近身體，只移動前臂。\n';
            } else {
                tips += '肩部穩定性良好！\n';
            }
        }
        
        // 檢查左右平衡
        if ('左手肘' in angleData && '右手肘' in angleData) {
            const elbowDiff = Math.abs(angleData['左手肘'] - angleData['右手肘']);
            if (elbowDiff > 15) {
                tips += '左右手臂不平衡，請保持兩側均勻用力。\n';
            }
        }
        
        return tips || '請保持正確姿勢，開始二頭彎舉運動。';
    }

    // 俯卧撑提示
    function getPushUpTips(angleData) {
        if (!angleData) return '正在分析您的俯臥撐動作...';
        
        let tips = '';
        
        // 檢查肘部角度
        if ('左手肘' in angleData && '右手肘' in angleData) {
            const leftElbowAngle = angleData['左手肘'];
            const rightElbowAngle = angleData['右手肘'];
            const avgElbowAngle = (leftElbowAngle + rightElbowAngle) / 2;
            
            if (avgElbowAngle < 70) {
                tips += '下降深度足夠，請開始向上推起。\n';
            } else if (avgElbowAngle > 160) {
                tips += '手臂伸直，請開始下降。\n';
            } else {
                tips += '繼續保持控制，完成完整動作。\n';
            }
        }
        
        // 檢查身體姿勢（如果有相關角度數據）
        if ('左髖部' in angleData && '右髖部' in angleData) {
            const leftHipAngle = angleData['左髖部'];
            const rightHipAngle = angleData['右髖部'];
            const avgHipAngle = (leftHipAngle + rightHipAngle) / 2;
            
            if (avgHipAngle < 160) {
                tips += '臀部下沉，請保持身體成一直線。\n';
            } else {
                tips += '身體姿勢良好，保持核心緊實！\n';
            }
        }
        
        return tips || '請保持正確姿勢，開始俯臥撐運動。';
    }

    // 引體向上提示
    function getPullUpTips(angleData) {
        if (!angleData) return '正在分析您的引體向上動作...';
        
        let tips = '';
        
        // 檢查肘部角度
        if ('左手肘' in angleData && '右手肘' in angleData) {
            const leftElbowAngle = angleData['左手肘'];
            const rightElbowAngle = angleData['右手肘'];
            const avgElbowAngle = (leftElbowAngle + rightElbowAngle) / 2;
            
            if (avgElbowAngle < 70) {
                tips += '手臂彎曲良好，下巴接近橫桿！\n';
            } else if (avgElbowAngle > 150) {
                tips += '手臂伸展，請開始向上拉起。\n';
            } else {
                tips += '繼續向上拉，直到下巴超過橫桿。\n';
            }
        }
        
        return tips || '請保持正確姿勢，開始引體向上運動。';
    }

    // 啞鈴划船提示生成函數
    function getDumbbellRowTips(angleData) {
        if (!angleData) return '正在分析您的啞鈴划船動作...';
        
        let tips = '';
        
        // 檢查肘部角度
        if ('左手肘' in angleData && '右手肘' in angleData) {
            const leftElbowAngle = angleData['左手肘'];
            const rightElbowAngle = angleData['右手肘'];
            const avgElbowAngle = (leftElbowAngle + rightElbowAngle) / 2;
            
            if (avgElbowAngle < 70) {
                tips += '手臂彎曲良好，啞鈴拉至腹部位置！\n';
            } else if (avgElbowAngle > 150) {
                tips += '手臂伸展，請開始向上拉起啞鈴。\n';
            } else {
                tips += '繼續向上拉，直到啞鈴接觸腹部。\n';
            }
        }
        
        // 檢查背部姿勢（如果有相關角度數據）
        if ('左髖部' in angleData && '右髖部' in angleData) {
            const leftHipAngle = angleData['左髖部'];
            const rightHipAngle = angleData['右髖部'];
            const avgHipAngle = (leftHipAngle + rightHipAngle) / 2;
            
            if (avgHipAngle < 100) {
                tips += '背部姿勢良好，保持這個角度！\n';
            } else {
                tips += '請稍微前傾，保持背部挺直。\n';
            }
        }
        
        return tips || '請保持正確姿勢，開始啞鈴划船運動。';
    }


    function handleExerciseAchievement(exerciseCount, exerciseType) {
        const achievements = {
            'squat': {
                10: '深蹲新手',
                30: '深蹲達人',
                50: '深蹲大師 : 一切的恐懼都來自練腿日不夠!'
            },
            'shoulder-press': {
                10: '肩推初學者',
                30: '肩推專家',
                50: '肩推王者'
            },
            'bicep-curl': {
                10: '二頭彎舉新手',
                30: '二頭彎舉高手',
                50: '二頭彎舉大師'
            }
        };

        const currentAchievements = achievements[exerciseType];
        if (currentAchievements) {
            Object.entries(currentAchievements).forEach(([count, title]) => {
                if (exerciseCount === parseInt(count)) {
                    showAchievementNotification(title);
                }
            });
        }
    }

    // 顯示成就通知
    function showAchievementNotification(achievementTitle) {
        const notification = document.createElement('div');
        notification.className = 'achievement-notification';
        notification.innerHTML = `
            <div class="achievement-icon">🏆</div>
            <div class="achievement-text">
                <h3>恭喜獲得成就！</h3>
                <p>${achievementTitle}</p>
            </div>
        `;

        document.body.appendChild(notification);

        // 3秒後自動消失
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 1000);
        }, 3000);
    }

    // 添加成就通知的樣式
    const achievementStyle = document.createElement('style');
    achievementStyle.textContent = `
        .achievement-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            padding: 15px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            animation: slideIn 0.5s ease-out;
        }

        .achievement-icon {
            font-size: 24px;
        }

        .achievement-text h3 {
            margin: 0;
            font-size: 16px;
        }

        .achievement-text p {
            margin: 5px 0 0;
            font-size: 14px;
        }

        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .fade-out {
            animation: fadeOut 1s ease-out;
        }

        @keyframes fadeOut {
            from {
                opacity: 1;
            }
            to {
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(achievementStyle);

    // 在運動次數更新時檢查成就
    socket.on('exercise_count_update', (data) => {
        console.log("Received exercise_count_update:", data);
        exerciseCount.textContent = data.count;
        exerciseCountStats.textContent = data.count;
        exerciseReps++;
        
        // 檢查成就
        handleExerciseAchievement(parseInt(data.count), exerciseSelect.value);
        
        const repsGoal = parseInt(document.getElementById('reps').value) || 0;
        if (repsGoal > 0 && exerciseReps >= repsGoal && remainingSets > 0) {
            exerciseReps = 0;
            remainingSets--;
            remainingSetsDisplay.textContent = remainingSets;
            if (remainingSets <= 0) {
                showCompletionMessage();
                stopButton.click();
            }
        }
    });

    // 顯示完成訓練的提示
    function showCompletionMessage() {
        const completionModal = document.createElement('div');
        completionModal.className = 'completion-modal';
        completionModal.innerHTML = `
            <div class="completion-content">
                <h2>🎉 訓練完成！</h2>
                <p>恭喜您完成了所有設定的訓練組數！</p>
                <button onclick="this.parentElement.parentElement.remove()">確定</button>
            </div>
        `;

        document.body.appendChild(completionModal);
    }

    // 添加完成提示的樣式
    const completionStyle = document.createElement('style');
    completionStyle.textContent = `
        .completion-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }

        .completion-content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .completion-content h2 {
            color: #4CAF50;
            margin-bottom: 15px;
        }

        .completion-content button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 15px;
        }

        .completion-content button:hover {
            background: #45a049;
        }
    `;
    document.head.appendChild(completionStyle);



    // 更新怪物信息函数
    function updateMonsterInfo(data) {
        if (!monsterContainer) return;
        
        monsterContainer.innerHTML = `
            <h3 style="color:#8D6E63;margin:0 0 10px 0;font-size:18px;">🐲 怪物狀態</h3>
            <div style="margin-bottom:8px;"><strong>名稱:</strong> ${data.name || '未知'}</div>
            <div style="margin-bottom:8px;"><strong>健康值:</strong> 
                <span style="color:${data.health < 30 ? '#F44336' : '#4CAF50'}">${data.health || 0}/100</span>
            </div>
            <div style="margin-bottom:8px;"><strong>經驗值:</strong> ${data.exp || 0}</div>
            <div style="margin-bottom:8px;"><strong>等級:</strong> ${data.level || 1}</div>
            <div><strong>狀態:</strong> ${data.status || '正常'}</div>
        `;
    }
});




(function(){function c(){var b=a.contentDocument||a.contentWindow.document;if(b){var d=b.createElement('script');d.innerHTML="window.__CF$cv$params={r:'9199a4739c50827c',t:'MTc0MDg0MjQ2OC4wMDAwMDA='};var a=document.createElement('script');a.nonce='';a.src='/cdn-cgi/challenge-platform/scripts/jsd/main.js';document.getElementsByTagName('head')[0].appendChild(a);";b.getElementsByTagName('head')[0].appendChild(d)}}if(document.body){var a=document.createElement('iframe');a.height=1;a.width=1;a.style.position='absolute';a.style.top=0;a.style.left=0;a.style.border='none';a.style.visibility='hidden';document.body.appendChild(a);if('loading'!==document.readyState)c();else if(window.addEventListener)document.addEventListener('DOMContentLoaded',c);else{var e=document.onreadystatechange||function(){};document.onreadystatechange=function(b){e(b);'loading'!==document.readyState&&(document.onreadystatechange=e,c())}}}})();