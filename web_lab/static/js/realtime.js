
// 全局變量
let currentLevel = null;
let currentMonsterIndex = 0;
let totalMonsters = 1; // 修改為每關只有1個怪物
let monsterHP = 100;
let initialMonsterHP = 100;
let monsterShield = 0; // 怪物護盾值
let initialMonsterShield = 0; // 初始護盾值
let shieldWeightFactor = 1; // 護盾重量係數，影響經驗值計算

// 添加全局变量，避免重复定义
let isDetecting = false;
let hasReceivedResponse = false;
let currentExerciseType = '';
let detectionLine = 0.5;
let exerciseCounter = 0;
let remainingSets = 3;
let lastQuality = 0;
let socket = null;

// 全局UI元素引用
let videoFeed, startButton, stopButton, resetButton, exerciseCount;
let exerciseCountStats, qualityScore, remainingSetsDisplay, coachTipText;
let qualityDisplay, qualityTitle, exerciseSelect;




function generateCoachTips(angles, exerciseType) {
    if (!angles || Object.keys(angles).length === 0) {
        return "等待接收角度數據...";
    }
    
    let tips = [];
    
    // 根據運動類型分析角度並生成建議
    switch (exerciseType) {
        case 'squat': // 深蹲
            // 膝蓋角度 (通常應該在最低點時約為90度)
            if (angles.knee && angles.knee < 70) {
                tips.push("膝蓋彎曲過度，可能會增加膝蓋壓力。嘗試不要蹲得太低。");
            } else if (angles.knee && angles.knee > 100) {
                tips.push("深蹲深度不足，嘗試蹲得更低，膝蓋彎曲至約90度。");
            }
            
            // 髖部角度
            if (angles.hip && angles.hip < 45) {
                tips.push("髖部彎曲不足，記得向後推臀部，保持背部挺直。");
            }
            
            // 背部角度 (應該保持挺直)
            if (angles.back && angles.back < 45) {
                tips.push("背部過度前傾，保持胸部挺起，背部挺直。");
            }
            break;
            
        case 'bicep-curl': // 二頭彎舉
            // 肘部角度
            if (angles.elbow && angles.elbow < 30) {
                tips.push("手臂彎曲過度，可能會造成肘部壓力。保持輕微的張力。");
            } else if (angles.elbow && angles.elbow > 160) {
                tips.push("手臂沒有充分彎曲，嘗試將啞鈴舉得更高。");
            }
            
            // 肩部角度 (應保持穩定)
            if (angles.shoulder && angles.shoulder > 20) {
                tips.push("肩部過度參與，保持上臂靠近身體，只移動前臂。");
            }
            break;
            
        case 'shoulder-press': // 肩推
            // 肘部角度
            if (angles.elbow && angles.elbow < 90 && angles.elbow > 30) {
                tips.push("起始位置正確，繼續向上推舉。");
            } else if (angles.elbow && angles.elbow > 150) {
                tips.push("手臂已充分伸展，現在可以控制下放。");
            }
            
            // 肩部角度
            if (angles.shoulder && angles.shoulder < 80) {
                tips.push("肩部需要更多參與，確保肩膀向上推舉。");
            }
            break;
            
        case 'push-up': // 伏地挺身
            // 肘部角度
            if (angles.elbow && angles.elbow < 60) {
                tips.push("下降深度適中，現在可以向上推。");
            } else if (angles.elbow && angles.elbow > 150) {
                tips.push("手臂已充分伸展，可以控制下降。");
            }
            
            // 身體角度 (應保持直線)
            if (angles.body && angles.body < 160) {
                tips.push("保持身體成一直線，不要讓臀部下沉或抬高。");
            }
            break;
            
        case 'pull-up': // 引體向上
            // 肘部角度
            if (angles.elbow && angles.elbow < 60) {
                tips.push("已拉起到位，保持控制下降。");
            } else if (angles.elbow && angles.elbow > 150) {
                tips.push("手臂已充分伸展，開始向上拉起。");
            }
            
            // 肩部角度
            if (angles.shoulder && angles.shoulder > 160) {
                tips.push("確保肩膀充分參與，將肩胛骨向下拉。");
            }
            break;
            
        case 'dumbbell-row': // 啞鈴划船
            // 背部角度
            if (angles.back && angles.back < 30) {
                tips.push("保持背部平行於地面，不要過度彎腰。");
            }
            
            // 肘部角度
            if (angles.elbow && angles.elbow < 60) {
                tips.push("手臂已充分彎曲，控制下放啞鈴。");
            } else if (angles.elbow && angles.elbow > 150) {
                tips.push("手臂已充分伸展，開始向上拉起啞鈴。");
            }
            break;
            
        default:
            tips.push("選擇一種運動開始訓練，將獲得針對性建議。");
    }
    
    // 如果沒有特定建議，提供一般性建議
    if (tips.length === 0) {
        switch (exerciseType) {
            case 'squat':
                tips.push("保持背部挺直，膝蓋不要超過腳尖，向下蹲時呼氣。");
                break;
            case 'bicep-curl':
                tips.push("保持上臂固定，只移動前臂，控制動作速度。");
                break;
            case 'shoulder-press':
                tips.push("保持核心緊張，不要過度弓背，控制啞鈴下放速度。");
                break;
            case 'push-up':
                tips.push("保持身體成一直線，肘部靠近身體，控制呼吸節奏。");
                break;
            case 'pull-up':
                tips.push("控制下降速度，充分伸展肩膀，每次拉起時收緊背部。");
                break;
            case 'dumbbell-row':
                tips.push("保持背部平行於地面，拉起時收緊背部肌肉，控制下放。");
                break;
            default:
                tips.push("選擇一種運動開始訓練，將獲得針對性建議。");
        }
    }
    
    // 返回建議文本
    return tips.join(" ");
}   

// 更新教練提示函數
function updateCoachTip(tip, angles) {
    if (coachTipText) {
        // 如果提供了具體的提示文本，直接使用
        if (typeof tip === 'string' && tip.trim() !== '') {
            coachTipText.textContent = tip;
            return;
        }
        
        // 否則根據角度和運動類型生成建議
        const exerciseType = currentExerciseType || 'squat';
        const generatedTip = generateCoachTips(angles, exerciseType);
        coachTipText.textContent = generatedTip;
    } else {
        console.error('找不到教練提示文本元素');
        // 嘗試重新獲取元素
        coachTipText = document.getElementById('coach-tip-text');
        if (coachTipText) {
            const exerciseType = currentExerciseType || 'squat';
            const generatedTip = generateCoachTips(angles, exerciseType);
            coachTipText.textContent = generatedTip;
        }
    }
}

function loadMonsterModel() {
    // 獲取怪物容器
    const monsterScene = document.getElementById('monster-scene');
    if (!monsterScene) {
        console.error('找不到怪物場景容器元素');
        return;
    }
    
    try {
        console.log('開始初始化怪物模型場景');
        
        // 創建 Three.js 場景
        const scene = new THREE.Scene();
        scene.background = null; // 確保背景透明
        
        // 設置相機 - 調整相機參數以顯示全身模型
        const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 1000);
        camera.position.set(0, 0, 100); // 增加相機距離
        camera.lookAt(0, -5, 0); // 調整視角更向下
        
        // 設置渲染器
        const renderer = new THREE.WebGLRenderer({
            alpha: true,
            antialias: true
        });
        
        // 調整渲染大小 - 使用固定尺寸
        const size = Math.min(300, monsterScene.clientWidth);
        renderer.setSize(size, size);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setClearColor(0x000000, 0); // 透明背景
        
        // 清空容器並添加渲染器
        monsterScene.innerHTML = '';
        monsterScene.appendChild(renderer.domElement);
        
        // 確保容器有適當的樣式 - 添加置中樣式
        monsterScene.style.width = `${size}px`;
        monsterScene.style.height = `${size}px`;
        monsterScene.style.position = 'relative';
        monsterScene.style.overflow = 'hidden';
        monsterScene.style.margin = '0 auto'; // 水平置中
        
        // 確保外層容器也有置中樣式
        if (monsterScene.parentElement) {
            monsterScene.parentElement.style.display = 'flex';
            monsterScene.parentElement.style.justifyContent = 'center';
            monsterScene.parentElement.style.alignItems = 'center';
            monsterScene.parentElement.style.width = '100%';
        }
        
        // 環境光 - 提高亮度
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
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
        
        // 添加調試信息
        console.log('THREE.js 版本:', THREE.REVISION);
        console.log('場景初始化完成，準備載入模型');
        
        // 檢查 GLTFLoader 是否可用
        let loader;
        if (typeof THREE.GLTFLoader !== 'undefined') {
            console.log('使用 THREE.GLTFLoader');
            loader = new THREE.GLTFLoader();
        } else if (typeof THREE !== 'undefined' && typeof THREE.GLTFLoader !== 'undefined') {
            console.log('使用 THREE.GLTFLoader (第二種檢查方式)');
            loader = new THREE.GLTFLoader();
        } else if (typeof window.GLTFLoader !== 'undefined') {
            console.log('使用 window.GLTFLoader');
            loader = new window.GLTFLoader();
        } else {
            console.error('GLTFLoader 未定義，請確保已載入 GLTFLoader 腳本');
            
            // 顯示錯誤信息
            monsterScene.innerHTML = '<div style="color: red; padding: 20px;">無法載入怪物模型：GLTFLoader 未定義</div>';
            
            // 使用基本幾何體作為替代
            const geometry = new THREE.BoxGeometry(2, 2, 2);
            const material = new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
            const cube = new THREE.Mesh(geometry, material);
            scene.add(cube);
            
            function animate() {
                requestAnimationFrame(animate);
                cube.rotation.x += 0.01;
                cube.rotation.y += 0.01;
                renderer.render(scene, camera);
            }
            
            animate();
            return;
        }
        
        // 確保 loader 已定義
        if (!loader) {
            console.error('無法創建 GLTFLoader 實例');
            monsterScene.innerHTML = '<div style="color: red; padding: 20px;">無法載入怪物模型：無法創建 GLTFLoader</div>';
            return;
        }
        
        // 添加載入進度顯示
        monsterScene.innerHTML = '<div style="color: white; padding: 20px;">正在載入怪物模型...</div>';
        
        // 嘗試載入模型 - 使用 idle.glb 作為默認模型
        console.log('開始載入模型: /static/models/idle.glb');
        loader.load(
            '/static/models/idle.glb',
            function(gltf) {
                console.log('模型載入成功:', gltf);
                
                // 清除載入提示
                monsterScene.innerHTML = '';
                monsterScene.appendChild(renderer.domElement);
                
                // 成功載入
                const model = gltf.scene;
                scene.add(model);
                
                // 調整模型大小和位置 - 縮小模型並降低位置以適應全身顯示
                model.scale.set(0.4, 0.4, 0.4);
                model.position.set(0, -5, 0);
                model.rotation.y = 0; // 確保模型正面朝向
                
                // 遍歷模型的所有部分，確保材質正確
                model.traverse((child) => {
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
                    }
                });
                
                // 設置動畫
                if (gltf.animations && gltf.animations.length > 0) {
                    console.log('模型包含動畫:', gltf.animations.length);
                    const mixer = new THREE.AnimationMixer(model);
                    const action = mixer.clipAction(gltf.animations[0]);
                    action.play();
                    
                    // 動畫循環
                    const clock = new THREE.Clock();
                    
                    function animate() {
                        requestAnimationFrame(animate);
                        
                        // 更新動畫
                        const delta = clock.getDelta();
                        mixer.update(delta);
                        
                        // 添加簡單的浮動動畫 - 調整浮動位置
                        model.position.y = -5 + Math.sin(Date.now() * 0.001) * 0.1;
                        
                        renderer.render(scene, camera);
                    }
                    
                    animate();
                    
                    // 將模型和混合器暴露給全局，以便後續更新
                    window.monsterModel = model;
                    window.monsterMixer = mixer;
                    window.monsterScene = scene;
                    window.monsterCamera = camera;
                    window.monsterRenderer = renderer;
                    window.monsterClock = clock;
                    
                } else {
                    console.log('模型不包含動畫，使用基本旋轉');
                    // 基本動畫循環
                    function animate() {
                        requestAnimationFrame(animate);
                        
                        // 添加簡單的浮動動畫 - 調整浮動位置
                        model.position.y = -5 + Math.sin(Date.now() * 0.001) * 0.1;
                        
                        renderer.render(scene, camera);
                    }
                    
                    animate();
                    
                    // 將模型暴露給全局，以便後續更新
                    window.monsterModel = model;
                    window.monsterScene = scene;
                    window.monsterCamera = camera;
                    window.monsterRenderer = renderer;
                }
                
                console.log('怪物模型渲染完成');
                
                // 初始化怪物血量顯示
                updateMonsterHP(monsterHP);
            },
            // 進度回調
            function(xhr) {
                if (xhr.lengthComputable) {
                    const percent = Math.floor((xhr.loaded / xhr.total) * 100);
                    console.log(`模型載入進度: ${percent}%`);
                    monsterScene.innerHTML = `<div style="color: white; padding: 20px;">載入中: ${percent}%</div>`;
                }
            },
            // 錯誤回調
            function(error) {
                console.error('載入怪物模型時出錯:', error);
                monsterScene.innerHTML = `<div style="color: red; padding: 20px;">無法載入怪物模型：${error.message}</div>`;
                
                // 載入失敗時顯示替代內容
                const geometry = new THREE.BoxGeometry(2, 2, 2);
                const material = new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
                const cube = new THREE.Mesh(geometry, material);
                scene.add(cube);
                
                function animate() {
                    requestAnimationFrame(animate);
                    cube.rotation.x += 0.01;
                    cube.rotation.y += 0.01;
                    renderer.render(scene, camera);
                }
                
                animate();
            }
        );
    } catch (e) {
        console.error('初始化 3D 場景時出錯:', e);
        const monsterScene = document.getElementById('monster-scene');
        if (monsterScene) {
            monsterScene.innerHTML = `<div style="color: red; padding: 20px;">無法初始化 3D 場景：${e.message}</div>`;
        }
    }
}

// 更新怪物血量顯示
function updateMonsterHP(hp) {
    console.log(`更新怪物血量: ${hp}/${initialMonsterHP}`);
    
    // 獲取血量條和血量值元素
    const hpBarFill = document.getElementById('monster-hp-bar');
    const hpValue = document.getElementById('monster-hp');
    const maxHpValue = document.getElementById('monster-max-hp');
    
    if (!hpBarFill || !hpValue) {
        console.error('找不到怪物血量顯示元素，嘗試創建');
        createMonsterHPBar();
        return updateMonsterHP(hp); // 重新調用以更新新創建的元素
    }
    
    // 計算血量百分比
    const percentage = (hp / initialMonsterHP) * 100;
    
    // 更新血量條寬度
    hpBarFill.style.width = `${percentage}%`;
    
    // 更新血量數值
    hpValue.textContent = Math.max(0, Math.floor(hp));
    if (maxHpValue) maxHpValue.textContent = initialMonsterHP;
    
    // 根據血量百分比改變顏色
    if (percentage < 20) {
        hpBarFill.style.backgroundColor = '#e74c3c'; // 紅色
    } else if (percentage < 50) {
        hpBarFill.style.backgroundColor = '#f39c12'; // 橙色
    } else {
        hpBarFill.style.backgroundColor = '#2ecc71'; // 綠色
    }
    
    // 更新全局變量
    monsterHP = hp;
}


// 新增函數：創建怪物護盾條
function createMonsterShieldBar() {
    console.log('創建怪物護盾條');
    
    // 獲取怪物區域容器
    const monsterArea = document.querySelector('.monster-area');
    if (!monsterArea) {
        console.error('找不到怪物區域容器');
        return;
    }
    
    // 檢查是否已存在護盾條
    if (document.getElementById('monster-shield-bar')) {
        console.log('護盾條已存在，跳過創建');
        return;
    }
    
    // 創建護盾條容器
    const shieldContainer = document.createElement('div');
    shieldContainer.className = 'hp-container';
    shieldContainer.style.marginBottom = '10px';
    shieldContainer.style.backgroundColor = 'rgba(0, 0, 0, 0.2)';
    shieldContainer.style.borderRadius = '5px';
    shieldContainer.style.padding = '8px';
    
    // 創建護盾標籤
    const shieldLabel = document.createElement('div');
    shieldLabel.className = 'hp-label';
    shieldLabel.textContent = '怪物護盾:';
    shieldLabel.style.fontSize = '14px';
    shieldLabel.style.marginBottom = '5px';
    shieldLabel.style.fontWeight = '600';
    
    // 創建護盾條
    const shieldBar = document.createElement('div');
    shieldBar.className = 'hp-bar';
    shieldBar.style.height = '20px';
    shieldBar.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
    shieldBar.style.borderRadius = '10px';
    shieldBar.style.overflow = 'hidden';
    shieldBar.style.margin = '5px 0';
    shieldBar.style.position = 'relative';
    
    // 創建護盾條填充
    const shieldBarFill = document.createElement('div');
    shieldBarFill.className = 'hp-bar-fill shield-bar-fill';
    shieldBarFill.id = 'monster-shield-bar';
    shieldBarFill.style.height = '100%';
    shieldBarFill.style.backgroundColor = '#3498db';
    shieldBarFill.style.width = '100%';
    shieldBarFill.style.transition = 'width 0.3s ease';
    
    // 創建護盾值顯示
    const shieldValue = document.createElement('div');
    shieldValue.className = 'hp-value';
    shieldValue.style.fontSize = '14px';
    shieldValue.style.textAlign = 'right';
    shieldValue.style.color = '#ecf0f1';
    shieldValue.innerHTML = '<span id="monster-shield">0</span>/<span id="monster-max-shield">0</span>';
    
    // 組裝護盾條
    shieldBar.appendChild(shieldBarFill);
    shieldContainer.appendChild(shieldLabel);
    shieldContainer.appendChild(shieldBar);
    shieldContainer.appendChild(shieldValue);
    
    // 獲取血量條容器
    const hpContainer = document.querySelector('.monster-area .hp-container');
    
    // 將護盾條添加到血量條之後
    if (hpContainer) {
        hpContainer.parentNode.insertBefore(shieldContainer, hpContainer.nextSibling);
    } else {
        // 如果找不到血量條，則添加到怪物區域的最前面
        if (monsterArea.firstChild) {
            monsterArea.insertBefore(shieldContainer, monsterArea.firstChild);
        } else {
            monsterArea.appendChild(shieldContainer);
        }
    }
    
    // 如果沒有護盾，則隱藏護盾條
    if (initialMonsterShield <= 0) {
        shieldContainer.style.display = 'none';
    }
    
    console.log('怪物護盾條創建完成');
}

// 更新怪物護盾顯示
function updateMonsterShield(shield) {
    console.log(`更新怪物護盾: ${shield}/${initialMonsterShield}`);
    
    const shieldBarFill = document.getElementById('monster-shield-bar');
    const shieldValue = document.getElementById('monster-shield');
    const maxShieldValue = document.getElementById('monster-max-shield');
    
    if (!shieldBarFill || !shieldValue) {
        console.error('找不到護盾顯示元素，嘗試創建');
        createMonsterShieldBar();
        return updateMonsterShield(shield); // 重新調用以更新新創建的元素
    }
    
    // 避免除以零錯誤
    const percentage = initialMonsterShield > 0 ? (shield / initialMonsterShield) * 100 : 0;
    shieldBarFill.style.width = `${percentage}%`;
    shieldValue.textContent = shield;
    if (maxShieldValue) maxShieldValue.textContent = initialMonsterShield;
    
    // 根據是否有護盾顯示或隱藏護盾條
    const shieldContainer = shieldBarFill.closest('.hp-container');
    if (shieldContainer) {
        if (initialMonsterShield > 0) {
            shieldContainer.style.display = 'block';
        } else {
            shieldContainer.style.display = 'none';
        }
    }
    
    // 更新全局變量
    monsterShield = shield;
}

function createMonsterHPBar() {
    console.log('創建怪物血量條');
    
    // 獲取怪物區域容器
    const monsterArea = document.querySelector('.monster-area');
    if (!monsterArea) {
        console.error('找不到怪物區域容器');
        return;
    }
    
    // 檢查是否已存在血量條
    if (document.getElementById('monster-hp-bar')) {
        console.log('血量條已存在，跳過創建');
        return;
    }
    
    // 創建血量條容器
    const hpContainer = document.createElement('div');
    hpContainer.className = 'hp-container';
    hpContainer.style.marginBottom = '10px';
    hpContainer.style.backgroundColor = 'rgba(0, 0, 0, 0.2)';
    hpContainer.style.borderRadius = '5px';
    hpContainer.style.padding = '8px';
    
    // 創建血量標籤
    const hpLabel = document.createElement('div');
    hpLabel.className = 'hp-label';
    hpLabel.textContent = '怪物血量:';
    hpLabel.style.fontSize = '14px';
    hpLabel.style.marginBottom = '5px';
    hpLabel.style.fontWeight = '600';
    
    // 創建血量條
    const hpBar = document.createElement('div');
    hpBar.className = 'hp-bar';
    hpBar.style.height = '20px';
    hpBar.style.backgroundColor = 'rgba(0, 0, 0, 0.3)';
    hpBar.style.borderRadius = '10px';
    hpBar.style.overflow = 'hidden';
    hpBar.style.margin = '5px 0';
    hpBar.style.position = 'relative';
    
    // 創建血量條填充
    const hpBarFill = document.createElement('div');
    hpBarFill.className = 'hp-bar-fill';
    hpBarFill.id = 'monster-hp-bar';
    hpBarFill.style.height = '100%';
    hpBarFill.style.backgroundColor = '#2ecc71';
    hpBarFill.style.width = '100%';
    hpBarFill.style.transition = 'width 0.3s ease';
    
    // 創建血量值顯示
    const hpValue = document.createElement('div');
    hpValue.className = 'hp-value';
    hpValue.style.fontSize = '14px';
    hpValue.style.textAlign = 'right';
    hpValue.style.color = '#ecf0f1';
    hpValue.innerHTML = '<span id="monster-hp">100</span>/<span id="monster-max-hp">100</span>';
    
    // 組裝血量條
    hpBar.appendChild(hpBarFill);
    hpContainer.appendChild(hpLabel);
    hpContainer.appendChild(hpBar);
    hpContainer.appendChild(hpValue);
    
    // 將血量條添加到怪物區域的最前面
    if (monsterArea.firstChild) {
        monsterArea.insertBefore(hpContainer, monsterArea.firstChild);
    } else {
        monsterArea.appendChild(hpContainer);
    }
    
    console.log('怪物血量條創建完成');
}


// 初始化護盾控件
function initShieldControls() {
    console.log('初始化护盾控制');
    

    
    // 更新护盾显示
    updateShieldDisplay();
}

// 更新护盾显示
function updateShieldDisplay() {
    console.log('更新護盾顯示');
    
    // 更新护盾值显示
    const shieldValueElement = document.getElementById('shield-value');
    if (shieldValueElement) {
        shieldValueElement.textContent = initialMonsterShield;
    } else {
        console.error('找不到護盾值顯示元素');
    }
    
    // 更新护盾权重显示
    const shieldWeightElement = document.getElementById('shield-weight');
    if (shieldWeightElement) {
        shieldWeightElement.textContent = shieldWeightFactor.toFixed(1);
    } else {
        console.error('找不到護盾權重顯示元素');
    }
}


// 新增函數：根據運動參數更新護盾值
function updateShieldFromExerciseParams() {
    // 获取用户输入的运动参数
    const weightInput = document.getElementById('weight');
    const repsInput = document.getElementById('reps');
    const setsInput = document.getElementById('sets');
    
    if (!weightInput || !repsInput || !setsInput) {
        console.error('無法取得運動參數控件');
        return;
    }
    
    // 获取输入值
    const weight = parseFloat(weightInput.value) || 0;
    const reps = parseInt(repsInput.value) || 0;
    const sets = parseInt(setsInput.value) || 0;
    
    console.log(`運動參數: 重量=${weight}kg, 次數=${reps}, 組數=${sets}`);
    
    // 计算护盾值 - 使用次数乘以组数作为护盾值
    const newShieldValue = reps * sets;
    
    // 使用重量作为护盾重量系数 (限制在合理范围内)
    // 如果重量为0，则使用1作为默认值
    const newWeightFactor = weight > 0 ? Math.min(5, Math.max(0.1, weight / 20)) : 1;
    
    console.log(`根據運動參數計算: 护盾值=${newShieldValue}, 重量系数=${newWeightFactor.toFixed(2)}`);
    
    // 更新护盾值和重量系数
    initialMonsterShield = newShieldValue;
    monsterShield = newShieldValue;
    shieldWeightFactor = newWeightFactor;
    
    // 更新护盾显示
    updateMonsterShield(monsterShield);
    updateShieldDisplay(); // 确保更新UI显示
    
    // 显示确认消息
    if (newShieldValue > 0) {
        showMonsterDialogue(`我獲得了 ${monsterShield} 點護盾！重量係數為 ${shieldWeightFactor.toFixed(1)}`);
    } else {
        showMonsterDialogue('我沒有護盾，直接攻擊我吧！');
    }
}



// 添加一個新函數來處理運動次數增加時減少怪物血量
function decreaseMonsterHP(count) {
    // 靜態變量，記錄上次的計數
    if (decreaseMonsterHP.lastCount === undefined) {
        decreaseMonsterHP.lastCount = 0;
    }
    
    // 計算新增的計數
    const increment = count - decreaseMonsterHP.lastCount;
    decreaseMonsterHP.lastCount = count;
    
    // 如果沒有新增計數，則不處理
    if (increment <= 0) return;
    
    console.log(`減少怪物血量，新增計數: ${increment}`);
    
    // 先處理護盾
    if (monsterShield > 0) {
        // 護盾減少量 = 新增計數 * 護盾減少係數
        const shieldDecrease = Math.min(monsterShield, increment);
        monsterShield -= shieldDecrease;
        
        // 更新護盾顯示
        updateMonsterShield(monsterShield);
        
        // 如果護盾被擊破，顯示提示
        if (monsterShield === 0) {
            showMonsterDialogue('我的護盾被擊破了！');
        }
        
        // 如果護盾吸收了所有傷害，則不減少血量
        if (shieldDecrease >= increment) {
            return;
        }
        
        // 計算剩餘傷害
        const remainingDamage = increment - shieldDecrease;
        
        // 減少怪物血量
        monsterHP = Math.max(0, monsterHP - remainingDamage);
    } else {
        // 沒有護盾，直接減少血量
        monsterHP = Math.max(0, monsterHP - increment);
    }
    
    // 更新血量顯示
    updateMonsterHP(monsterHP);
    
    // 檢查怪物是否被擊敗
    if (monsterHP <= 0) {
        // 怪物被擊敗
        console.log('怪物被擊敗！');
        
        // 調用怪物被擊敗函數
        monsterDefeated();
    } else if (monsterHP < initialMonsterHP * 0.3) {
        // 血量低於30%，顯示快要被擊敗的對話
        showMonsterDialogue('我快撐不住了...');
    } else if (monsterHP < initialMonsterHP * 0.5) {
        // 血量低於50%，顯示受傷的對話
        showMonsterDialogue('好痛！你很強！');
    }
}


// 顯示怪物對話
function showMonsterDialogue(text) {
    console.log('显示怪物对话:', text);
    
    // 确保样式已添加
    addMonsterDialogueStyle();
    
    // 获取怪物区域
    const monsterArea = document.querySelector('.monster-area');
    if (!monsterArea) {
        console.error('找不到怪物区域');
        return;
    }
    
    // 检查是否已存在对话框
    let dialogue = monsterArea.querySelector('.monster-dialogue');
    
    // 如果不存在或者有问题，创建新的对话框
    if (!dialogue || dialogue.style.top === '-60px') {
        // 如果存在旧的对话框，先移除
        if (dialogue) {
            monsterArea.removeChild(dialogue);
        }
        
        dialogue = document.createElement('div');
        dialogue.className = 'monster-dialogue';
        
        // 设置明确的样式，避免被其他CSS覆盖
        dialogue.style.position = 'absolute';
        dialogue.style.top = '20px'; // 调整位置，避免太高
        dialogue.style.left = '50%';
        dialogue.style.transform = 'translateX(-50%)';
        dialogue.style.backgroundColor = '#fff';
        dialogue.style.borderRadius = '10px';
        dialogue.style.padding = '10px 15px';
        dialogue.style.boxShadow = '0 3px 10px rgba(0, 0, 0, 0.2)';
        dialogue.style.maxWidth = '200px';
        dialogue.style.textAlign = 'center';
        dialogue.style.fontSize = '14px';
        dialogue.style.color = '#333';
        dialogue.style.zIndex = '100';
        dialogue.style.opacity = '0';
        dialogue.style.transition = 'opacity 0.3s, transform 0.3s';
        dialogue.style.pointerEvents = 'none';
        
        // 添加伪元素的替代方案
        const arrow = document.createElement('div');
        arrow.style.position = 'absolute';
        arrow.style.bottom = '-10px';
        arrow.style.left = '50%';
        arrow.style.transform = 'translateX(-50%)';
        arrow.style.borderWidth = '10px 10px 0';
        arrow.style.borderStyle = 'solid';
        arrow.style.borderColor = '#fff transparent transparent';
        
        dialogue.appendChild(arrow);
        monsterArea.appendChild(dialogue);
    }
    
    // 设置对话内容
    dialogue.textContent = text;
    
    // 显示对话框
    setTimeout(() => {
        dialogue.style.opacity = '1';
        dialogue.style.transform = 'translateX(-50%) translateY(-5px)';
    }, 10);
    
    // 5秒后隐藏对话框
    setTimeout(() => {
        dialogue.style.opacity = '0';
        dialogue.style.transform = 'translateX(-50%) translateY(0)';
    }, 5000);
}


// 修改 showErrorMessage 函數，確保它能正確顯示
function showErrorMessage(message, duration = 5000) {
    console.error(message);
    
    // 檢查是否已存在錯誤訊息元素
    let errorMessage = document.querySelector('.error-message');
    
    // 如果不存在，則創建一個
    if (!errorMessage) {
        errorMessage = document.createElement('div');
        errorMessage.className = 'error-message';
        document.body.appendChild(errorMessage);
    }
    
    // 設置訊息內容
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    
    // 添加動畫效果
    errorMessage.style.animation = 'fadeIn 0.5s ease-in-out';
    
    // 設置自動消失
    setTimeout(function() {
        errorMessage.style.animation = 'fadeOut 0.5s ease-in-out';
        setTimeout(function() {
            errorMessage.style.display = 'none';
        }, 500);
    }, duration);
}


// 開始偵測函數
function startDetection() {
    if (isDetecting) {
        console.log('檢測已經在進行中');
        return;
    }
    
    console.log('開始檢測...');
    
    // 檢查 Socket.IO 連接
    if (!checkSocketConnection()) {
        showErrorMessage('無法連接到伺服器，請刷新頁面重試');
        return;
    }
    isDetecting = true;
    hasReceivedResponse = false;
    
    // 更新UI
    if (startButton) {
        startButton.disabled = true;
        console.log('禁用开始按钮');
    } else {
        console.error('找不到开始按钮元素');
        // 尝试重新获取按钮
        startButton = document.getElementById('start-btn') || 
                     document.getElementById('start-detection') ||
                     document.querySelector('.start-btn') ||
                     document.querySelector('button[data-action="start"]');
        if (startButton) {
            startButton.disabled = true;
            console.log('重新获取并禁用开始按钮');
        }
    }
    
    if (stopButton) {
        stopButton.disabled = false;
        console.log('启用停止按钮');
    } else {
        console.error('找不到停止按钮元素');
        // 尝试重新获取按钮
        stopButton = document.getElementById('stop-btn') || 
                    document.getElementById('stop-detection') ||
                    document.querySelector('.stop-btn') ||
                    document.querySelector('button[data-action="stop"]');
        if (stopButton) {
            stopButton.disabled = false;
            console.log('重新获取并启用停止按钮');
        }
    }
    
    const detectionStatus = document.querySelector('.detection-status');
    if (detectionStatus) {
        detectionStatus.textContent = '检测中';
        detectionStatus.classList.remove('inactive');
        detectionStatus.classList.add('active');
        console.log('更新检测状态显示为检测中');
    }
    
    // 获取当前选择的运动类型
    if (exerciseSelect) {
        currentExerciseType = exerciseSelect.value || 'squat';
    } else {
        currentExerciseType = 'squat'; // 默认使用深蹲
    }
    
    // 確保當前關卡已初始化，如果沒有則初始化為第一關
    if (currentLevel === null) {
        console.log('關卡未初始化，默認設置為第一關');
        initLevel(1);
    } else {
        console.log(`使用當前關卡: ${currentLevel}, 怪物血量: ${monsterHP}/${initialMonsterHP}`);
    }

    // 确保Socket连接已初始化
    if (!socket || !socket.connected) {
        console.log('Socket未连接，尝试重新初始化');
        socket = initSocketConnection();
        
        // 等待Socket连接成功后再发送请求
        setTimeout(function() {
            if (socket && socket.connected) {
                sendStartDetectionRequest();
            } else {
                console.error('无法连接到服务器');
                showErrorMessage('无法连接到服务器，请刷新页面重试');
                stopDetection();
            }
        }, 1000);
    } else {
        sendStartDetectionRequest();
    }
}

// 停止偵測
function stopDetection() {
    console.log('停止检测函数被调用');
    
    if (!isDetecting) {
        console.log('当前未在检测状态，忽略停止请求');
        return;
    }
    
    console.log('停止检测运动');
    isDetecting = false;
    
    // 更新UI
    if (startButton) {
        startButton.disabled = false;
        console.log('启用开始按钮');
    } else {
        console.error('找不到开始按钮元素');
        // 尝试重新获取按钮
        startButton = document.getElementById('start-btn') || 
                     document.getElementById('start-detection') ||
                     document.querySelector('.start-btn') ||
                     document.querySelector('button[data-action="start"]');
        if (startButton) {
            startButton.disabled = false;
            console.log('重新获取并启用开始按钮');
        }
    }
    
    if (stopButton) {
        stopButton.disabled = true;
        console.log('禁用停止按钮');
    } else {
        console.error('找不到停止按钮元素');
        // 尝试重新获取按钮
        stopButton = document.getElementById('stop-btn') || 
                    document.getElementById('stop-detection') ||
                    document.querySelector('.stop-btn') ||
                    document.querySelector('button[data-action="stop"]');
        if (stopButton) {
            stopButton.disabled = true;
            console.log('重新获取并禁用停止按钮');
        }
    }
    
    const detectionStatus = document.querySelector('.detection-status');
    if (detectionStatus) {
        detectionStatus.textContent = '未检测';
        detectionStatus.classList.add('inactive');
        detectionStatus.classList.remove('active');
        console.log('更新检测状态显示为未检测');
    }
    
    // 发送停止检测请求
    if (socket && socket.connected) {
        console.log('发送停止检测请求到服务器');
        socket.emit('stop_detection');
    } else {
        console.error('Socket未连接，无法发送停止检测请求');
    }
}

// 重置計數
function resetCount() {
    exerciseCounter = 0;
    updateExerciseCount();
    
    // 重置怪物血量
    monsterHP = initialMonsterHP;
    updateMonsterHP(monsterHP);
    
    // 重置怪物護盾 - 恢復到初始護盾值
    monsterShield = initialMonsterShield;
    updateMonsterShield(monsterShield);
    
    // 重置 decreaseMonsterHP 的静态变量
    decreaseMonsterHP.lastCount = 0;
    
    // 发送重置计数请求
    if (socket) {
        socket.emit('reset_count');
    }
    
    console.log(`重置完成，怪物血量: ${monsterHP}/${initialMonsterHP}, 護盾: ${monsterShield}/${initialMonsterShield}`);
}


// 顯示完成訊息
function showCompletionMessage() {
    console.log('運動完成！');
    
    // 創建完成訊息元素
    const completionMessage = document.createElement('div');
    completionMessage.className = 'completion-message';
    completionMessage.innerHTML = `
        <div class="completion-content">
            <h2>恭喜完成訓練！</h2>
            <p>你已經完成了所有設定的組數</p>
            <button class="button accent" id="close-completion">繼續</button>
        </div>
    `;
    
    // 添加到頁面
    document.body.appendChild(completionMessage);
    
    // 添加關閉按鈕事件
    document.getElementById('close-completion').addEventListener('click', function() {
        completionMessage.remove();
    });
    
    // 停止偵測
    stopDetection();
}


// 怪物被擊敗時的處理函數
function monsterDefeated() {
    console.log('怪物被擊敗！');
    
    // 停止偵測
    stopDetection();
    
    // 計算經驗值獎勵 (基於護盾值和重量係數)
    let expReward = 50; // 基礎經驗值
    
    if (initialMonsterShield > 0) {
        // 如果怪物有護盾，增加經驗值獎勵
        expReward += Math.round(initialMonsterShield * shieldWeightFactor);
        console.log(`基於護盾計算的額外經驗值: ${Math.round(initialMonsterShield * shieldWeightFactor)}`);
    }
    
    console.log(`總經驗值獎勵: ${expReward}`);
    
    // 顯示通關消息
    showNotification(`恭喜！你擊敗了怪物，獲得 ${expReward} 經驗值！`, 'success');
    
    // 顯示怪物對話
    showMonsterDialogue('啊！我被打敗了...');
    
    // 顯示關卡完成訊息 (包含下一關選項)
    showLevelCompleteMessage();
    
    // 注意：不再自動發送關卡完成數據，而是在用戶選擇後發送
}


// 顯示關卡完成訊息
function showLevelCompleteMessage() {
    console.log('顯示關卡完成訊息');
    
    // 計算經驗值獎勵 (基於護盾值和重量係數)
    let expReward = 50; // 基礎經驗值
    let shieldBonus = 0;
    
    if (initialMonsterShield > 0) {
        // 如果怪物有護盾，增加經驗值獎勵
        shieldBonus = Math.round(initialMonsterShield * shieldWeightFactor);
        console.log(`護盾經驗值加成: ${shieldBonus} (初始護盾: ${initialMonsterShield}, 重量係數: ${shieldWeightFactor})`);
        expReward += shieldBonus;
    }
    
    console.log(`關卡 ${currentLevel} 完成，獲得經驗值: ${expReward} (基礎: 50, 護盾加成: ${shieldBonus})`);
    
    // 創建通關通知元素
    const notification = document.createElement('div');
    notification.className = 'level-complete-notification';
    notification.innerHTML = `
        <div class="level-complete-content">
            <h2>關卡完成！</h2>
            <p>恭喜你擊敗了怪物！</p>
            <p>獲得經驗值: ${expReward}</p>
            <div class="level-complete-buttons">
                <button id="next-level-btn">下一關</button>
                <button id="continue-btn">返回</button>
            </div>
        </div>
    `;
    
    // 設置樣式
    notification.style.position = 'fixed';
    notification.style.top = '0';
    notification.style.left = '0';
    notification.style.width = '100%';
    notification.style.height = '100%';
    notification.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    notification.style.display = 'flex';
    notification.style.justifyContent = 'center';
    notification.style.alignItems = 'center';
    notification.style.zIndex = '1000';
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.5s';
    
    // 設置內容樣式
    const content = notification.querySelector('.level-complete-content');
    if (content) {
        content.style.backgroundColor = '#fff';
        content.style.borderRadius = '10px';
        content.style.padding = '20px 30px';
        content.style.textAlign = 'center';
        content.style.maxWidth = '400px';
        content.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.3)';
    }
    
    // 設置按鈕容器樣式
    const buttonsContainer = notification.querySelector('.level-complete-buttons');
    if (buttonsContainer) {
        buttonsContainer.style.display = 'flex';
        buttonsContainer.style.justifyContent = 'center';
        buttonsContainer.style.gap = '10px';
        buttonsContainer.style.marginTop = '15px';
    }
    
    // 設置下一關按鈕樣式
    const nextLevelButton = notification.querySelector('#next-level-btn');
    if (nextLevelButton) {
        nextLevelButton.style.backgroundColor = '#3498db';
        nextLevelButton.style.color = 'white';
        nextLevelButton.style.border = 'none';
        nextLevelButton.style.padding = '10px 20px';
        nextLevelButton.style.borderRadius = '5px';
        nextLevelButton.style.cursor = 'pointer';
        nextLevelButton.style.fontSize = '16px';
        
        // 添加下一關按鈕點擊事件
        nextLevelButton.addEventListener('click', function() {
            // 先發送關卡完成數據到伺服器
            if (currentLevel) {
                // 確保在這裡發送數據
                sendLevelCompletionToServer(currentLevel, expReward);
                console.log(`已發送關卡 ${currentLevel} 完成數據，經驗值: ${expReward}`);
            }
            
            // 淡出通知
            notification.style.opacity = '0';
            
            // 移除通知
            setTimeout(function() {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                
                // 進入下一關
                const nextLevel = currentLevel + 1;
                console.log(`準備進入下一關: ${nextLevel}`);
                loadLevel(nextLevel);
            }, 500);
        });
    }
    
    // 設置返回按鈕樣式
    const continueButton = notification.querySelector('#continue-btn');
    if (continueButton) {
        continueButton.style.backgroundColor = '#2ecc71';
        continueButton.style.color = 'white';
        continueButton.style.border = 'none';
        continueButton.style.padding = '10px 20px';
        continueButton.style.borderRadius = '5px';
        continueButton.style.cursor = 'pointer';
        continueButton.style.fontSize = '16px';
        
        // 添加返回按鈕點擊事件
        continueButton.addEventListener('click', function() {
            // 先發送關卡完成數據到伺服器
            if (currentLevel) {
                // 確保在這裡發送數據
                sendLevelCompletionToServer(currentLevel, expReward);
                console.log(`已發送關卡 ${currentLevel} 完成數據，經驗值: ${expReward}`);
            }
            
            // 淡出通知
            notification.style.opacity = '0';
            
            // 移除通知
            setTimeout(function() {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                
                // 重置怪物
                resetMonster();
            }, 500);
        });
    }
    
    // 添加到頁面
    document.body.appendChild(notification);
    
    // 淡入通知
    setTimeout(function() {
        notification.style.opacity = '1';
    }, 10);
    
    // 同時顯示通知訊息
    showNotification(`關卡 ${currentLevel} 完成！獲得 ${expReward} 經驗值`, 'success');
}


// 加載指定關卡
function loadLevel(levelId) {
    console.log(`加載關卡: ${levelId}`);
    
    // 更新當前關卡
    currentLevel = levelId;
    
    // 顯示加載中訊息
    showNotification(`正在加載關卡 ${levelId}...`, 'info');
    
    // 重置運動計數器
    exerciseCounter = 0;
    decreaseMonsterHP.lastCount = 0;
    
    // 更新UI顯示
    updateLevelDisplay(levelId);
    
    // 根據關卡難度設置怪物屬性
    const difficulty = Math.min(2, Math.max(0.5, 1 + (levelId - 1) * 0.1));
    console.log(`關卡 ${levelId} 難度係數: ${difficulty.toFixed(2)}`);
    
    // 設置怪物血量 (隨關卡增加)
    initialMonsterHP = Math.round(100 * difficulty);
    monsterHP = initialMonsterHP;
    
    // 獲取用戶設定的運動參數
    const weightInput = document.getElementById('weight');
    const repsInput = document.getElementById('reps');
    const setsInput = document.getElementById('sets');
    
    if (weightInput && repsInput && setsInput) {
        // 獲取輸入值
        const weight = parseFloat(weightInput.value) || 0;
        const reps = parseInt(repsInput.value) || 0;
        const sets = parseInt(setsInput.value) || 0;
        
        // 計算護盾值 - 使用次數乘以組數作為護盾值
        initialMonsterShield = reps * sets;
        
        // 使用重量作為護盾重量係數 (限制在合理範圍內)
        shieldWeightFactor = weight > 0 ? Math.min(5, Math.max(0.1, weight / 20)) : 1;
    } else {
        // 如果找不到輸入控件，使用默認值
        initialMonsterShield = 10 * levelId;
        shieldWeightFactor = 0.1 * levelId;
    }
    
    // 設置怪物護盾
    monsterShield = initialMonsterShield;
    
    // 更新怪物顯示
    updateMonsterHP(monsterHP);
    updateMonsterShield(monsterShield);
    
    // 更新護盾顯示
    updateShieldDisplay();
    
    // 重置剩餘組數
    if (setsInput) {
        remainingSets = parseInt(setsInput.value) || 3;
    } else {
        remainingSets = 3;
    }
    
    // 更新剩餘組數顯示
    updateRemainingSetsDisplay();
    
    // 顯示關卡開始訊息
    showNotification(`關卡 ${levelId} 開始！`, 'success');
    
    // 顯示怪物對話
    if (levelId === 1) {
        showMonsterDialogue('我是第一關的怪物，準備接受挑戰吧！');
    } else {
        showMonsterDialogue(`我是第 ${levelId} 關的怪物，比上一關更強！`);
    }
    
    // 開始偵測
    startDetection();
}



function updateRemainingSetsDisplay() {
    if (remainingSetsDisplay) {
        remainingSetsDisplay.textContent = remainingSets;
    } else {
        console.error('找不到剩餘組數顯示元素');
        // 嘗試重新獲取元素
        remainingSetsDisplay = document.getElementById('remaining-sets') || 
                              document.querySelector('.remaining-sets');
        if (remainingSetsDisplay) {
            remainingSetsDisplay.textContent = remainingSets;
        }
    }
}






function initMonsterSystem() {
    console.log('初始化怪物系統...');
    
    // 初始化怪物模型
    loadMonsterModel();
    
    // 初始化護盾控件
    initShieldControls();
    
    // 初始化怪物血量顯示
    updateMonsterHP(monsterHP);
    
    // 初始化怪物護盾顯示
    updateMonsterShield(monsterShield);
    
    // 初始化第一關
    initLevel(1);
    
    console.log('怪物系統初始化完成');
}


// 發送關卡完成數據到伺服器
function sendLevelCompletionToServer(levelId, expReward) {
    console.log(`發送關卡完成數據: 關卡 ${levelId}, 經驗值 ${expReward}, 初始護盾 ${initialMonsterShield}, 重量係數 ${shieldWeightFactor}`);

    // 獲取用戶ID，如果沒有則使用默認值
    const userId = document.getElementById('user-id') ? 
                  document.getElementById('user-id').value : 
                  (document.getElementById('student-id') ? 
                   document.getElementById('student-id').value : 'C111151146');
    
    console.log(`用戶ID: ${userId}`);

    // 獲取用戶設定的重量和組數
    const weight = document.getElementById('weight') ? 
                  parseInt(document.getElementById('weight').value) || 0 : 0;

    const reps = document.getElementById('reps') ? 
                parseInt(document.getElementById('reps').value) || 10 : 10;

    const sets = document.getElementById('sets') ? 
               parseInt(document.getElementById('sets').value) || 3 : 3;
    
    // 計算已完成的組數
    const completedSets = remainingSets !== undefined ? (sets - remainingSets) : 0;
    
    console.log(`運動參數: 重量=${weight}kg, 次數=${reps}, 組數=${sets}, 已完成組數=${completedSets}`);
    
    // 發送請求到後端
    fetch('/api/game/complete_level', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,
            level_id: levelId,
            exp_reward: expReward,
            exercise_type: currentExerciseType || 'squat',
            exercise_count: exerciseCounter || 0,
            shield_value: initialMonsterShield,
            shield_weight: shieldWeightFactor,
            weight: weight,
            reps: reps,
            sets: sets,
            completed_sets: completedSets
        })
    })
    .then(response => {
        console.log(`API響應狀態: ${response.status}`);
        if (!response.ok) {
            throw new Error(`HTTP錯誤! 狀態: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('關卡完成數據已保存:', data);
            
            // 顯示成功通知
            showNotification(`關卡 ${levelId} 完成！獲得 ${expReward} 經驗值`, 'success');
            
            // 顯示成就通知（如果有）
            if (data.new_achievements && data.new_achievements.length > 0) {
                data.new_achievements.forEach(achievement => {
                    showNotification(`獲得成就: ${achievement.name}`, 'achievement');
                });
            }
            
            // 更新用戶進度顯示（如果有相關元素）
            if (data.progress) {
                updateUserProgress(data.progress);
            }
        } else {
            console.error('關卡完成數據保存失敗:', data.message);
            showNotification('關卡數據保存失敗: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('發送關卡完成請求時出錯:', error);
        showNotification('網絡錯誤，無法保存關卡數據', 'error');
        
        // 嘗試重新發送
        setTimeout(() => {
            console.log('嘗試重新發送關卡完成數據...');
            retryLevelCompletion(userId, levelId, expReward);
        }, 2000);
    });
}


// 更新用戶進度顯示
function updateUserProgress(progress) {
    console.log('更新用戶進度顯示:', progress);
    
    // 更新等級顯示
    const levelDisplay = document.getElementById('user-level');
    if (levelDisplay && progress.current_level) {
        levelDisplay.textContent = progress.current_level;
    }
    
    // 更新經驗值顯示
    const expDisplay = document.getElementById('user-exp');
    if (expDisplay && progress.total_exp) {
        expDisplay.textContent = progress.total_exp;
    }
    
    // 更新進度條
    const progressBar = document.querySelector('.progress-bar-fill');
    if (progressBar && progress.total_exp) {
        // 假設每100經驗值為一個等級
        const expPercentage = (progress.total_exp % 100) / 100 * 100;
        progressBar.style.width = `${expPercentage}%`;
    }
}


//用於在用戶完成所有設定的組數時記錄到資料庫
function recordExerciseCompletion() {
    console.log('記錄運動完成數據');
    
    // 獲取用戶ID
    const userId = document.getElementById('user-id') ? 
                  document.getElementById('user-id').value : 
                  (document.getElementById('student-id') ? 
                   document.getElementById('student-id').value : 'C111151146');
    
    console.log(`用戶ID: ${userId}`);
    
    // 獲取用戶設定的重量和組數
    const weight = document.getElementById('weight') ? 
                  parseInt(document.getElementById('weight').value) || 0 : 0;
    
    const reps = document.getElementById('reps') ? 
                parseInt(document.getElementById('reps').value) || 10 : 10;
    
    const sets = document.getElementById('sets') ? 
               parseInt(document.getElementById('sets').value) || 3 : 3;
    
    console.log(`運動參數: 重量=${weight}kg, 次數=${reps}, 組數=${sets}, 總計數=${exerciseCounter}`);
    
    // 發送請求到後端
    fetch('/api/exercise/record', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            student_id: userId,
            exercise_type: currentExerciseType || 'squat',
            weight: weight,
            reps: reps,
            sets: sets,
            total_count: exerciseCounter || 0
        })
    })
    .then(response => {
        console.log(`API響應狀態: ${response.status}`);
        if (!response.ok) {
            throw new Error(`HTTP錯誤! 狀態: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('運動完成數據已保存:', data);
            showNotification('運動記錄已保存', 'success');
        } else {
            console.error('運動完成數據保存失敗:', data.message);
            showNotification('運動記錄保存失敗: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('發送運動完成請求時出錯:', error);
        showNotification('網絡錯誤，無法保存運動記錄', 'error');
    });
}


// 添加關卡完成樣式
function addLevelCompleteStyles() {
    // 檢查是否已存在樣式
    if (document.getElementById('level-complete-styles')) {
        return;
    }
    
    // 創建樣式元素
    const style = document.createElement('style');
    style.id = 'level-complete-styles';
    style.textContent = `
        .level-complete-message {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .level-complete-content {
            background-color: white;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            max-width: 500px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            position: relative;
            z-index: 1001;
        }
        
        .level-rewards {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
        }
        
        .reward-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            min-width: 100px;
        }
        
        .reward-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #3498db;
        }
        
        .reward-label {
            font-size: 0.9rem;
            color: #7f8c8d;
            margin-top: 5px;
        }
        
        .level-complete-buttons {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-top: 20px;
            position: relative;
            z-index: 1100;
        }
        
        .level-complete-buttons button {
            padding: 10px 20px;
            border-radius: 5px;
            border: none;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
            position: relative;
            z-index: 1101;
        }
        
        .level-complete-buttons button.accent {
            background-color: #3498db;
            color: white;
        }
        
        .level-complete-buttons button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .level-complete-buttons button:active {
            transform: translateY(0);
        }
        
        .level-complete-buttons button:disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }
    `;
    
    // 添加到頁面
    document.head.appendChild(style);
}


// 初始化關卡
function initLevel(level) {
    console.log(`初始化關卡 ${level}`);
    
    // 更新当前关卡
    currentLevel = level;
    
    // 根据关卡设置怪物血量和护盾
    switch(level) {
        case 1:
            initialMonsterHP = 10;
            initialMonsterShield = 0;
            shieldWeightFactor = 0;
            break;
        case 2:
            initialMonsterHP = 15;
            initialMonsterShield = 5;
            shieldWeightFactor = 1;
            break;
        case 3:
            initialMonsterHP = 20;
            initialMonsterShield = 10;
            shieldWeightFactor = 1.5;
            break;
        case 4:
            initialMonsterHP = 25;
            initialMonsterShield = 15;
            shieldWeightFactor = 2;
            break;
        case 5:
            initialMonsterHP = 30;
            initialMonsterShield = 20;
            shieldWeightFactor = 2.5;
            break;
        default:
            // 超过5关的难度设置
            initialMonsterHP = 30 + (level - 5) * 10;
            initialMonsterShield = 20 + (level - 5) * 5;
            shieldWeightFactor = 2.5 + (level - 5) * 0.5;
    }
    
    // 重置当前怪物血量和护盾
    monsterHP = initialMonsterHP;
    monsterShield = initialMonsterShield;
    
    // 更新UI显示
    updateMonsterHP(monsterHP);
    updateMonsterShield(monsterShield);
    
    // 更新关卡显示
    const levelDisplay = document.getElementById('current-level');
    if (levelDisplay) {
        levelDisplay.textContent = level;
    }
    
    // 重置运动计数器
    exerciseCounter = 0;
    decreaseMonsterHP.lastCount = 0;
    updateExerciseCount();
    
    // 显示关卡开始对话
    showLevelStartMessage(level);
    
}



// 显示关卡开始信息
function showLevelStartMessage(level) {
    console.log(`顯示關卡 ${level} 开始信息`);
    
    // 根据关卡显示不同的对话
    let message = '';
    switch(level) {
        case 1:
            message = '歡迎來到第一關！完成10個深蹲擊敗怪物吧！';
            break;
        case 2:
            message = '第二關！這個怪物有護盾，需要更多運動才能打敗它！';
            break;
        case 3:
            message = '第三關！怪物變得更強了，加油！';
            break;
        case 4:
            message = '第四關！挑戰自我，堅持就是勝利！';
            break;
        case 5:
            message = '第五關！最終挑戰，全力以赴吧！';
            break;
        default:
            message = `挑戰關卡 ${level}！你已經超越了大多數人，繼續前進！`;
    }
    
    // 显示怪物对话
    showMonsterDialogue(message);
    
    // 移除了创建和显示 level-info 元素的代码
}



// 初始化頁面
function initPage() {
    console.log('初始化页面');
    
    // 初始化全局变量
    currentLevel = 1;
    initialMonsterHP = 10;
    monsterHP = initialMonsterHP;
    initialMonsterShield = 0;
    monsterShield = initialMonsterShield;
    shieldWeightFactor = 0;
    exerciseCounter = 0;
    lastQuality = 0;
    isDetecting = false;
    
    // 初始化UI元素引用
    initUIElements();
    
    // 初始化Socket连接
    socket = initSocketConnection();
    
    // 初始化怪物血量显示
    initMonsterHPDisplay();
    
    // 添加怪物对话框样式
    addMonsterDialogueStyle();
    
    // 重新绑定按钮事件
    rebindButtonEvents();
    
    console.log('页面初始化完成');
}

function debugGameState() {
    console.log('游戏状态:');
    console.log('- 当前關卡:', currentLevel);
    console.log('- 怪物血量:', monsterHP, '/', initialMonsterHP);
    console.log('- 怪物护盾:', monsterShield, '/', initialMonsterShield);
    console.log('- 护盾权重因子:', shieldWeightFactor);
    console.log('- 运动计数:', exerciseCounter);
    console.log('- 最后质量分数:', lastQuality);
    console.log('- 当前运动类型:', currentExerciseType);
    console.log('- 检测状态:', isDetecting ? '正在检测' : '未检测');
    
    // 检查Socket连接状态
    if (socket) {
        console.log('- Socket连接状态:', socket.connected ? '已连接' : '未连接');
        console.log('- Socket ID:', socket.id);
    } else {
        console.log('- Socket未初始化');
    }
    
    // 返回状态对象，方便在控制台查看
    return {
        currentLevel,
        monsterHP,
        initialMonsterHP,
        monsterShield,
        initialMonsterShield,
        shieldWeightFactor,
        exerciseCounter,
        lastQuality,
        currentExerciseType,
        isDetecting,
        socketConnected: socket ? socket.connected : false,
        socketId: socket ? socket.id : null
    };
}


// 添加怪物對話框樣式
function addMonsterDialogueStyle() {
    console.log('添加怪物对话框样式');
    
    // 检查是否已存在样式
    if (document.getElementById('monster-dialogue-style')) {
        console.log('怪物对话框样式已存在，移除旧样式');
        const oldStyle = document.getElementById('monster-dialogue-style');
        oldStyle.parentNode.removeChild(oldStyle);
    }
    
    // 创建样式元素
    const style = document.createElement('style');
    style.id = 'monster-dialogue-style';
    style.textContent = `
        .monster-dialogue {
            position: absolute;
            top: -60px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #fff;
            border-radius: 10px;
            padding: 10px 15px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.2);
            max-width: 200px;
            text-align: center;
            font-size: 14px;
            color: #333;
            z-index: 100;
            opacity: 0;
            transition: opacity 0.3s, transform 0.3s;
            pointer-events: none;
        }
        
        .monster-dialogue:after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            border-width: 10px 10px 0;
            border-style: solid;
            border-color: #fff transparent transparent;
        }
        
        .monster-dialogue.show {
            opacity: 1;
            transform: translateX(-50%) translateY(-5px);
        }
    `;
    
    // 添加到页面
    document.head.appendChild(style);
    console.log('怪物对话框样式已添加');
}


// 設置偵測線
function setDetectionLine() {
    // 獲取當前視頻畫面中的位置
    console.log('設置偵測線');
    
    // 發送設置偵測線請求
    if (socket) {
        socket.emit('set_detection_line', {
            line_position: detectionLine
        });
    }
}

function exportToExcel() {
    console.log('匯出運動數據到Excel');
    
    // 發送匯出Excel請求
    if (socket) {
        socket.emit('export_excel', {
            exercise_type: currentExerciseType,
            count: exerciseCounter,
            quality: lastQuality
        });
    }
}

// 更新運動計數
function updateExerciseCount() {
    console.log('更新運動計數 UI，當前計數:', exerciseCounter);
    
    // 嘗試多種方式獲取元素，以防元素不存在
    if (!exerciseCount) {
        exerciseCount = document.getElementById('exercise-count');
    }
    
    if (!exerciseCountStats) {
        exerciseCountStats = document.getElementById('exercise-count-stats');
    }
    
    if (exerciseCount) {
        console.log('找到運動計數元素，更新為:', exerciseCounter);
        exerciseCount.textContent = exerciseCounter;
    } else {
        console.error('找不到運動計數元素 (exercise-count)');
    }
    
    if (exerciseCountStats) {
        exerciseCountStats.textContent = exerciseCounter;
    }
    
    // 更新剩餘組數
    if (exerciseCounter > 0 && exerciseCounter % 10 === 0) {
        remainingSets = Math.max(0, remainingSets - 1);
        
        if (!remainingSetsDisplay) {
            remainingSetsDisplay = document.getElementById('remaining-sets');
        }
        
        if (remainingSetsDisplay) {
            remainingSetsDisplay.textContent = remainingSets;
        }
        
        // 檢查是否完成所有組數
        if (remainingSets === 0) {
            // 只有在非遊戲模式下才顯示完成訓練的通知
            if (currentLevel === null) {
                showCompletionMessage();
                // 記錄運動完成數據
                recordExerciseCompletion();
            }
        }
    }
}


// 初始化運動檢測
function initializeExerciseDetection() {
    console.log('初始化運動檢測...');
    
    // 獲取UI元素引用
    videoFeed = document.getElementById('video-feed');
    startButton = document.getElementById('start-button');
    stopButton = document.getElementById('stop-button');
    resetButton = document.getElementById('reset-button');
    exerciseCount = document.getElementById('exercise-count');
    exerciseCountStats = document.getElementById('exercise-count-stats');
    qualityScore = document.getElementById('quality-score');
    remainingSetsDisplay = document.getElementById('remaining-sets');
    coachTipText = document.getElementById('coach-tip-text');
    qualityDisplay = document.querySelector('.quality-display');
    qualityTitle = document.querySelector('.quality-title');
    exerciseSelect = document.getElementById('exercise-select');
    
    // 記錄UI元素是否成功獲取
    console.log('UI元素獲取狀態:');
    console.log('- videoFeed:', !!videoFeed);
    console.log('- qualityScore:', !!qualityScore);
    console.log('- qualityDisplay:', !!qualityDisplay);
    console.log('- qualityTitle:', !!qualityTitle);
    
    // 初始化 Socket.IO 連接
    if (!socket) {
        console.log('初始化 Socket.IO 連接...');
        socket = io();
        
        // 添加連接事件監聽
        socket.on('connect', function() {
            console.log('Socket.IO 連接成功，ID:', socket.id);
        });
        
        socket.on('connect_error', function(error) {
            console.error('Socket.IO 連接錯誤:', error);
        });
        
        // 監聽品質分數事件
        socket.on('pose_quality', function(data) {
            console.log('收到姿勢質量評分:', data);
            
            // 確保數據有效
            if (data && data.score !== undefined) {
                console.log('更新品質分數:', data.score);
                updateQualityScore(data.score);
            } else {
                console.warn('收到的品質分數數據無效:', data);
            }
        });
        
        // ... 其他事件監聽 ...
    }


    // 初始化 /exercise 命名空間連接
    if (!exerciseSocket) {
        console.log('初始化 /exercise 命名空間連接...');
        exerciseSocket = io('/exercise');
        
        exerciseSocket.on('connect', function() {
            console.log('/exercise 命名空間連接成功，ID:', exerciseSocket.id);
        });
        
        // 監聽品質分數事件 (/exercise 命名空間)
        exerciseSocket.on('pose_quality', function(data) {
            console.log('收到姿勢質量評分 (/exercise 命名空間):', data);
            
            // 確保數據有效
            if (data && data.score !== undefined) {
                updateQualityScore(data.score);
                
                // 如果有反饋信息，更新教練提示
                if (data.feedback) {
                    updateCoachTip(data.feedback);
                }
            } else {
                console.warn('收到的品質分數數據無效:', data);
            }
        });
        
        // ... 其他事件監聽 ...
    }


}
// 更新品質分數
function updateQualityScore(quality) {
    console.log('更新品質分數:', quality);
    
    // 確保品質分數是數字
    if (quality === undefined || quality === null || isNaN(quality)) {
        console.warn('收到非數字品質分數:', quality);
        quality = 0;
    }
    
    // 將品質分數轉換為整數
    quality = parseInt(quality);
    
    // 保存最後的品質分數
    lastQuality = quality;
    
    // 確保獲取正確的 DOM 元素
    if (!qualityScore) {
        qualityScore = document.getElementById('quality-score');
        console.log('重新獲取 quality-score 元素:', !!qualityScore);
    }
    
    if (!qualityDisplay) {
        qualityDisplay = document.querySelector('.quality-display');
        console.log('重新獲取 quality-display 元素:', !!qualityDisplay);
    }
    
    if (!qualityTitle) {
        qualityTitle = document.querySelector('.quality-title');
        console.log('重新獲取 quality-title 元素:', !!qualityTitle);
    }
    
    // 更新分數顯示
    if (qualityScore) {
        qualityScore.textContent = quality;
        console.log('已更新品質分數顯示為:', quality);
    } else {
        console.error('找不到品質分數元素 (quality-score)');
    }
    
    // 根據品質分數更新顏色和文字 (使用5分制)
    if (qualityDisplay && qualityTitle) {
        console.log('更新品質顯示樣式');
        if (quality >= 4) {
            qualityTitle.textContent = '優秀';
            qualityDisplay.style.backgroundColor = 'rgba(46, 204, 113, 0.8)';
        } else if (quality >= 3) {
            qualityTitle.textContent = '良好';
            qualityDisplay.style.backgroundColor = 'rgba(241, 196, 15, 0.8)';
        } else if (quality >= 2) {
            qualityTitle.textContent = '一般';
            qualityDisplay.style.backgroundColor = 'rgba(230, 126, 34, 0.8)';
        } else if (quality >= 1) {
            qualityTitle.textContent = '需改進';
            qualityDisplay.style.backgroundColor = 'rgba(231, 76, 60, 0.8)';
        } else {
            qualityTitle.textContent = '未評分';
            qualityDisplay.style.backgroundColor = 'rgba(149, 165, 166, 0.8)';
        }
    }
}

function checkSocketConnection() {
    if (!socket) {
        console.error('Socket.IO 未初始化');
        return false;
    }
    
    console.log('Socket狀態:', {
        connected: socket.connected,
        id: socket.id
    });
    
    if (!socket.connected) {
        console.warn('Socket.IO 未連接，嘗試重新連接...');
        socket.connect();
    }
    
    return socket.connected;
}

// 更新教練提示
function updateCoachTip(tip) {
    if (coachTipText) {
        if (typeof tip === 'string') {
            coachTipText.textContent = tip;
        } else {
            // 根據運動類型設置默認提示
            switch (currentExerciseType) {
                case 'squat':
                    coachTipText.textContent = '下蹲時保持背部挺直，膝蓋不要超過腳尖';
                    break;
                case 'pushup':
                case 'push-up':
                    coachTipText.textContent = '保持身體成一直線，肘部靠近身體';
                    break;
                case 'situp':
                    coachTipText.textContent = '上身抬起時保持腹部緊張，避免用力過猛';
                    break;
                case 'bicep-curl':
                    coachTipText.textContent = '保持上臂固定，只移動前臂';
                    break;
                default:
                    coachTipText.textContent = '選擇一種運動開始訓練';
            }
        }
    }
}


function updateAngles(angles) {
    // 檢查角度數據是否有效
    if (!angles) {
        console.warn('收到空的角度數據');
        // 即使角度数据为空，也尝试更新教练提示
        if (coachTipText) {
            const exerciseType = currentExerciseType || 'squat';
            const generatedTip = generateCoachTips({}, exerciseType); // 传递空对象
            coachTipText.textContent = generatedTip;
        }
        return;
    }
    
    try {
        // 將中文角度名稱映射到英文名稱，以便generateCoachTips函數能正確處理
        const mappedAngles = {
            knee: 0,
            hip: 0,
            back: 0,
            elbow: 0,
            shoulder: 0,
            body: 180
        };
        
        // 映射膝蓋角度 (取左右膝蓋的平均值)
        if ('左膝蓋' in angles && '右膝蓋' in angles) {
            mappedAngles.knee = (angles['左膝蓋'] + angles['右膝蓋']) / 2;
        } else if ('左膝蓋' in angles) {
            mappedAngles.knee = angles['左膝蓋'];
        } else if ('右膝蓋' in angles) {
            mappedAngles.knee = angles['右膝蓋'];
        } else if ('左膝盖' in angles && '右膝盖' in angles) {
            mappedAngles.knee = (angles['左膝盖'] + angles['右膝盖']) / 2;
        }
        
        // 映射髖部角度 (取左右髖部的平均值)
        if ('左髖部' in angles && '右髖部' in angles) {
            mappedAngles.hip = (angles['左髖部'] + angles['右髖部']) / 2;
        } else if ('左髖部' in angles) {
            mappedAngles.hip = angles['左髖部'];
        } else if ('右髖部' in angles) {
            mappedAngles.hip = angles['右髖部'];
        } else if ('左髋部' in angles && '右髋部' in angles) {
            mappedAngles.hip = (angles['左髋部'] + angles['右髋部']) / 2;
        }
        
        // 映射肘部角度 (取左右肘部的平均值)
        if ('左手肘' in angles && '右手肘' in angles) {
            mappedAngles.elbow = (angles['左手肘'] + angles['右手肘']) / 2;
        } else if ('左手肘' in angles) {
            mappedAngles.elbow = angles['左手肘'];
        } else if ('右手肘' in angles) {
            mappedAngles.elbow = angles['右手肘'];
        }
        
        // 映射肩部角度 (取左右肩部的平均值)
        if ('左肩膀' in angles && '右肩膀' in angles) {
            mappedAngles.shoulder = (angles['左肩膀'] + angles['右肩膀']) / 2;
        } else if ('左肩膀' in angles) {
            mappedAngles.shoulder = angles['左肩膀'];
        } else if ('右肩膀' in angles) {
            mappedAngles.shoulder = angles['右肩膀'];
        }
        
        // 更新角度顯示（如果有相應的元素）
        for (const [joint, angle] of Object.entries(angles)) {
            const angleElement = document.getElementById(`${joint}-angle`);
            if (angleElement) {
                angleElement.textContent = `${Math.round(angle)}°`;
            }
        }
        
        // 確保教練提示更新 - 使用映射後的角度數據
        if (coachTipText) {
            const exerciseType = currentExerciseType || 'squat';
            const generatedTip = generateCoachTips(mappedAngles, exerciseType);
            coachTipText.textContent = generatedTip;
        } else {
            // 如果coachTipText不存在，尝试重新获取
            coachTipText = document.getElementById('coach-tip-text');
            if (coachTipText) {
                const exerciseType = currentExerciseType || 'squat';
                const generatedTip = generateCoachTips(mappedAngles, exerciseType);
                coachTipText.textContent = generatedTip;
            }
        }
    } catch (error) {
        console.error('更新角度顯示時出錯:', error);
    }
}

// 添加請求角度數據函數
function requestAngleData() {
    if (!socket || !isDetecting) return;
    
    console.log('請求角度數據');
    socket.emit('request_angle_data');
    
    // 設置定時器，每2秒請求一次角度數據
    if (isDetecting) {
        setTimeout(requestAngleData, 2000);
    }
}




function initMonsterHPDisplay() {
    console.log('初始化怪物血量和護盾顯示');
    
    // 创建血量条
    createMonsterHPBar();
    
    // 创建护盾条
    createMonsterShieldBar();
    
    // 更新血量显示
    updateMonsterHP(monsterHP);
    
    // 更新护盾显示
    updateMonsterShield(monsterShield);
    
    // 添加怪物对话框样式
    addMonsterDialogueStyle();
    
    // 初始化护盾控制
    initShieldControls();
    
    console.log('怪物血量和護盾顯示初始化完成');
}


function bindShieldUpdateEvents() {
    console.log('绑定護盾更新事件');
    
    // 获取运动参数输入元素
    const weightInput = document.getElementById('weight');
    const repsInput = document.getElementById('reps');
    const setsInput = document.getElementById('sets');
    
    // 绑定输入事件
    if (weightInput) {
        weightInput.addEventListener('change', updateShieldFromExerciseParams);
    }
    
    if (repsInput) {
        repsInput.addEventListener('change', updateShieldFromExerciseParams);
    }
    
    if (setsInput) {
        setsInput.addEventListener('change', updateShieldFromExerciseParams);
    }
    
    // 查找更新按钮并绑定事件
    const updateButton = document.querySelector('.update-shield-btn') || 
                         document.getElementById('update-shield') ||
                         document.querySelector('button[data-action="update-shield"]');
    
    if (updateButton) {
        updateButton.addEventListener('click', updateShieldFromExerciseParams);
    } else {
        // 如果没有找到更新按钮，创建一个
        const shieldControls = document.querySelector('.shield-controls');
        if (shieldControls) {
            const updateBtn = document.createElement('button');
            updateBtn.className = 'update-shield-btn';
            updateBtn.textContent = '更新護盾';
            updateBtn.style.marginTop = '10px';
            updateBtn.style.padding = '5px 10px';
            updateBtn.style.backgroundColor = '#3498db';
            updateBtn.style.color = '#fff';
            updateBtn.style.border = 'none';
            updateBtn.style.borderRadius = '5px';
            updateBtn.style.cursor = 'pointer';
            
            updateBtn.addEventListener('click', updateShieldFromExerciseParams);
            shieldControls.appendChild(updateBtn);
        }
    }
    
    console.log('護盾更新事件绑定完成');
}

// 初始化UI元素引用
function initUIElements() {
    console.log('初始化UI元素引用');

    // 獲取視頻和按鈕元素
    videoFeed = document.getElementById('video-feed');
    
    // 獲取計數和品質相關元素
    qualityScore = document.getElementById('quality-score');

    // 獲取品質顯示元素
    qualityDisplay = document.querySelector('.quality-display');
    qualityTitle = document.querySelector('.quality-title');
    
    // 尝试多种可能的按钮ID和类名
    startButton = document.getElementById('start-btn') || 
                 document.getElementById('start-detection') || 
                 document.querySelector('.start-btn') ||
                 document.querySelector('button[data-action="start"]');
    
    stopButton = document.getElementById('stop-btn') || 
                document.getElementById('stop-detection') || 
                document.querySelector('.stop-btn') ||
                document.querySelector('button[data-action="stop"]');
    
    resetButton = document.getElementById('reset-btn') || 
                 document.getElementById('reset-count') || 
                 document.querySelector('.reset-btn');
    

    // 获取其他UI元素
   
    exerciseCount = document.getElementById('exercise-count');
    exerciseCountStats = document.getElementById('exercise-count-stats');
    remainingSetsDisplay = document.getElementById('remaining-sets');
    coachTipText = document.getElementById('coach-tip') || document.getElementById('coach-tip-text');
    exerciseSelect = document.getElementById('exercise-type');    
   

    // 记录找到的按钮元素
    console.log('UI 元素初始化完成:',
        '\n- videoFeed:', !!videoFeed,
        '\n- startButton:', !!startButton,
        '\n- stopButton:', !!stopButton,
        '\n- exerciseCount:', !!exerciseCount,
        '\n- qualityScore:', !!qualityScore,
        '\n- qualityDisplay:', !!qualityDisplay,
        '\n- qualityTitle:', !!qualityTitle
    );
    
    // 如果找不到按钮，尝试查找所有按钮并根据文本内容识别
    if (!startButton || !stopButton) {
        console.log('尝试通过按钮文本内容识别按钮');
        const allButtons = document.querySelectorAll('button');
        
        allButtons.forEach(button => {
            const buttonText = button.textContent.toLowerCase().trim();
            console.log('发现按钮:', buttonText);
            
            if (buttonText.includes('开始') || buttonText.includes('開始') || buttonText.includes('start')) {
                startButton = button;
                console.log('通过文本内容识别到开始按钮');
            } else if (buttonText.includes('停止') || buttonText.includes('stop')) {
                stopButton = button;
                console.log('通过文本内容识别到停止按钮');
            } else if (buttonText.includes('重置') || buttonText.includes('reset')) {
                resetButton = button;
                console.log('通过文本内容识别到重置按钮');
            }
        });
    }
    

    
    // 绑定按钮事件 - 使用更可靠的方式
    if (startButton) {
        console.log('绑定开始按钮事件');
        // 移除可能存在的旧事件监听器
        startButton.removeEventListener('click', startDetection);
        // 添加新的事件监听器
        startButton.addEventListener('click', startDetection);
    } else {
        console.error('找不到开始按钮元素，将创建一个虚拟按钮');
        // 创建一个虚拟按钮并添加到页面
        startButton = document.createElement('button');
        startButton.id = 'virtual-start-btn';
        startButton.textContent = '开始检测';
        startButton.className = 'button primary-button';
        startButton.style.position = 'fixed';
        startButton.style.bottom = '20px';
        startButton.style.right = '20px';
        startButton.style.zIndex = '9999';
        startButton.addEventListener('click', startDetection);
        document.body.appendChild(startButton);
        console.log('已创建虚拟开始按钮');
    }
    
    if (stopButton) {
        console.log('绑定停止按钮事件');
        // 移除可能存在的旧事件监听器
        stopButton.removeEventListener('click', stopDetection);
        // 添加新的事件监听器
        stopButton.addEventListener('click', stopDetection);
    } else {
        console.error('找不到停止按钮元素，将创建一个虚拟按钮');
        // 创建一个虚拟按钮并添加到页面
        stopButton = document.createElement('button');
        stopButton.id = 'virtual-stop-btn';
        stopButton.textContent = '停止检测';
        stopButton.className = 'button secondary-button';
        stopButton.style.position = 'fixed';
        stopButton.style.bottom = '20px';
        stopButton.style.right = '150px';
        stopButton.style.zIndex = '9999';
        stopButton.addEventListener('click', stopDetection);
        document.body.appendChild(stopButton);
        console.log('已创建虚拟停止按钮');
    }

    if (!qualityScore) {
        console.warn('無法找到 quality-score 元素，嘗試使用其他選擇器');
        // 嘗試其他可能的選擇器
        qualityScore = document.querySelector('.quality-value') || 
                      document.querySelector('[id^="quality"]') ||
                      document.querySelector('[class^="quality"]');
        
        if (qualityScore) {
            console.log('使用替代選擇器找到品質分數元素');
        } else {
            console.error('無法找到品質分數元素，請檢查HTML結構');
        }
    }
    
    // 初始状态设置
    if (stopButton) stopButton.disabled = true;
    if (startButton) startButton.disabled = false;
}



// 添加地圖相關功能
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面已加载，准备初始化');
    
    // 初始化UI元素引用
    initUIElements();
    // 初始化 Socket.IO 连接
    socket = initSocketConnection();
    
    initMapScroll();

    // 設置地圖模態視窗事件
    setupMapModal();
    
    initLevel(1);

    // 添加怪物对话框样式
    addMonsterDialogueStyle();
    
    // 初始化怪物血量显示
    initMonsterHPDisplay();
    
    // 初始化页面
    initPage();

    // 使用延时确保DOM完全加载
    setTimeout(function() {
        // 初始化护盾系统
        initShieldControls();
        
        // 绑定护盾更新事件
        bindShieldUpdateEvents();
        
        // 初始化第一关
        initLevel(1);
        
        // 尝试显示一个初始对话，测试对话框是否正常
        showMonsterDialogue('准备好开始挑战了吗？');
    }, 500);
    

    // 暴露全局函数，以便在控制台调试
    window.startDetection = startDetection;
    window.stopDetection = stopDetection;
    window.resetCount = resetCount;
    window.updateMonsterHP = updateMonsterHP;
    window.showMonsterDialogue = showMonsterDialogue;
    window.initLevel = initLevel;
    window.debugGameState = debugGameState;
    window.updateShieldFromExerciseParams = updateShieldFromExerciseParams;
    
    // 初始化 Socket.IO 連接 - 修改連接方式
    socket = io('/exercise', {
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
    });

    if (!socket) {
        socket = io.connect('/exercise');
        console.log('Socket.IO 連接初始化');
        
        // 添加連接事件處理
        socket.on('connect', function() {
            console.log('Socket.IO 已連接');
        });
        
        socket.on('connect_error', function(error) {
            console.error('Socket.IO 連接錯誤:', error);
        });
    }
    
    // 获取UI元素引用
    videoFeed = document.getElementById('video-feed');
    startButton = document.getElementById('start-detection');
    stopButton = document.getElementById('stop-detection');
    resetButton = document.getElementById('reset-count');
    // 確保獲取運動計數元素
    exerciseCount = document.getElementById('exercise-count');
    if (!exerciseCount) {
        console.error('找不到運動計數元素 (exercise-count)');
    } else {
        console.log('成功獲取運動計數元素');
    }

    exerciseCount = document.getElementById('exercise-count');
    exerciseCountStats = document.getElementById('exercise-count-stats');
    qualityScore = document.getElementById('quality-score');
    remainingSetsDisplay = document.getElementById('remaining-sets');
    coachTipText = document.getElementById('coach-tip-text');
    qualityDisplay = document.querySelector('.quality-display');
    qualityTitle = document.querySelector('.quality-title');
    exerciseSelect = document.getElementById('exercise-type');
    
    // 获取可能不存在的UI元素
    const resetCountButton = document.getElementById('reset-count');
    const setDetectionLineButton = document.getElementById('set-detection-line');
    const exportExcelButton = document.getElementById('export-excel');

    if (videoFeed) {
        videoFeed.style.width = '100%';
        videoFeed.style.height = 'auto';
        videoFeed.style.objectFit = 'contain';
        videoFeed.style.maxHeight = '100%';
        
        // 確保父容器設置正確
        const videoContainer = videoFeed.closest('.video-container');
        if (videoContainer) {
            videoContainer.style.display = 'flex';
            videoContainer.style.justifyContent = 'center';
            videoContainer.style.alignItems = 'center';
            videoContainer.style.overflow = 'hidden';
        }
    }


    // 断开连接事件
    socket.on('disconnect', function() {
        console.log('與伺服器斷開連接');
        
        // 更新连接状态UI
        const detectionStatus = document.querySelector('.detection-status');
        if (detectionStatus) {
            detectionStatus.textContent = '未連接';
            detectionStatus.classList.add('inactive');
        }
        
        // 如果正在检测，则停止检测
        if (isDetecting) {
            stopDetection();
        }
    });



    // 添加視頻幀更新事件監聽
    socket.on('video_frame', function(data) {
        console.log('收到視頻幀');
        if (videoFeed) {
            if (data.frame) {
                videoFeed.src = 'data:image/jpeg;base64,' + data.frame;
                
                // 確保影像適應容器大小
                videoFeed.style.width = '100%';
                videoFeed.style.height = 'auto';
                videoFeed.style.objectFit = 'contain';
                videoFeed.style.maxHeight = '100%';
                
                // 確保父容器設置正確
                const videoContainer = videoFeed.closest('.video-container');
                if (videoContainer) {
                    videoContainer.style.display = 'flex';
                    videoContainer.style.justifyContent = 'center';
                    videoContainer.style.alignItems = 'center';
                    videoContainer.style.overflow = 'hidden';
                }
            } else {
                console.error('收到的視頻幀數據為空');
            }
        } else {
            console.error('找不到視頻顯示元素');
        }
    });

    // 添加姿势质量评分事件监听
    socket.on('pose_quality', function(data) {
        console.log('收到姿勢質量評分:', data);
        
        // 詳細記錄收到的數據結構
        console.log('姿勢質量評分數據結構:', JSON.stringify(data));
        
        // 檢查不同可能的屬性名稱
        if (data.score !== undefined) {
            console.log('使用 data.score 更新品質分數:', data.score);
            updateQualityScore(parseInt(data.score));
        } else if (data.quality !== undefined) {
            console.log('使用 data.quality 更新品質分數:', data.quality);
            updateQualityScore(parseInt(data.quality));
        } else if (data.quality_score !== undefined) {
            console.log('使用 data.quality_score 更新品質分數:', data.quality_score);
            updateQualityScore(parseInt(data.quality_score));
        } else {
            console.warn('無法從數據中找到品質分數:', data);
        }
        
        // 更新教練提示
        if (data.feedback && coachTipText) {
            coachTipText.textContent = data.feedback;
        }
    });

    // 添加角度数据事件监听
    socket.on('angle_data', function(data) {
        console.log('收到角度數據:', data);
        
        // 檢查數據格式
        if (data) {
            // 如果data本身就是角度數據對象（不包含angles屬性）
            if (typeof data === 'object' && !data.angles && Object.keys(data).some(key => key.includes('膝') || key.includes('肘') || key.includes('肩') || key.includes('髖'))) {
                // 直接使用data作為angles
                updateCoachTip('', data);
                updateAngles(data);
            }
            // 如果data包含angles屬性
            else if (data.angles) {
                updateCoachTip('', data.angles);
                updateAngles(data.angles);
            } 
            else {
                console.warn('收到無效的角度數據格式:', data);
                // 即使没有有效的角度数据，也尝试更新教练提示
                if (coachTipText) {
                    const exerciseType = currentExerciseType || 'squat';
                    coachTipText.textContent = generateCoachTips({}, exerciseType);
                }
            }
        } else {
            console.warn('收到空的角度數據');
            // 即使没有有效的角度数据，也尝试更新教练提示
            if (coachTipText) {
                const exerciseType = currentExerciseType || 'squat';
                coachTipText.textContent = generateCoachTips({}, exerciseType);
            }
        }
    });

    // 添加检测结果事件监听
    socket.on('detection_result', function(data) {
        console.log('收到偵測結果:', data);
        console.log('偵測結果數據結構:', JSON.stringify(data));
        
        if (!isDetecting) return;
        
        // 更新計數
        if (data.count !== undefined && data.count > exerciseCounter) {
            exerciseCounter = data.count;
            updateExerciseCount();
            
            // 使用decreaseMonsterHP函數來處理怪物血量減少和擊敗邏輯
            decreaseMonsterHP(data.count);
        }
        
        // 更新質量評分
        if (data.quality !== undefined) {
            console.log('從 detection_result 更新品質分數 (quality):', data.quality);
            updateQualityScore(parseInt(data.quality));
        } else if (data.score !== undefined) {
            console.log('從 detection_result 更新品質分數 (score):', data.score);
            updateQualityScore(parseInt(data.score));
        } else if (data.quality_score !== undefined) {
            console.log('從 detection_result 更新品質分數 (quality_score):', data.quality_score);
            updateQualityScore(parseInt(data.quality_score));
        }
        
        // 更新教練提示 - 使用角度數據
        if (data.angles) {
            updateCoachTip(data.tip || '', data.angles);
        } else if (data.tip) {
            updateCoachTip(data.tip);
        }
        
        // 更新角度顯示
        if (data.angles) {
            updateAngles(data.angles);
        }
    });
    
    // 添加模型狀態事件監聽
    socket.on('model_status', function(data) {
        console.log('收到模型狀態:', data);
        
        if (data.loaded) {
            console.log('模型已加載');
        } else {
            console.warn('模型未加載');
            showErrorMessage('模型未加載，請稍後再試');
        }
    });
    // 添加調試事件監聽
    socket.on('debug', function(data) {
        console.log('調試信息:', data);
    });






    // 確保 THREE.js 和 GLTFLoader 已載入
    if (typeof THREE === 'undefined') {
        console.error('THREE.js 未載入，嘗試動態載入');
        
        // 動態載入 THREE.js
        const threeScript = document.createElement('script');
        threeScript.src = 'https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js';
        threeScript.onload = function() {
            console.log('THREE.js 已動態載入');
            
            // 載入 GLTFLoader
            const loaderScript = document.createElement('script');
            loaderScript.src = 'https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/GLTFLoader.js';
            loaderScript.onload = function() {
                console.log('GLTFLoader 已動態載入');
                setTimeout(loadMonsterModel, 500);
            };
            document.head.appendChild(loaderScript);
        };
        document.head.appendChild(threeScript);
    } else if (typeof THREE.GLTFLoader === 'undefined' && typeof window.GLTFLoader === 'undefined') {
        console.error('GLTFLoader 未載入，嘗試動態載入');
        
        // 動態載入 GLTFLoader
        const loaderScript = document.createElement('script');
        loaderScript.src = 'https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/GLTFLoader.js';
        loaderScript.onload = function() {
            console.log('GLTFLoader 已動態載入');
            setTimeout(loadMonsterModel, 500);
        };
        document.head.appendChild(loaderScript);
    } else {
        // 延遲載入怪物模型，確保 DOM 已完全載入
        setTimeout(loadMonsterModel, 1000);
    }
    
    // 初始化怪物血量顯示
    updateMonsterHP(monsterHP);
    
    // 事件監聽器 - 開始偵測
    if (startButton) {
        startButton.addEventListener('click', function() {
            if (!isDetecting) {
                startDetection();
            }
        });
    }
    
    // 事件監聽器 - 停止偵測
    if (stopButton) {
        stopButton.addEventListener('click', function() {
            if (isDetecting) {
                stopDetection();
            }
        });
    }
    
    // 事件監聽器 - 重置計數
    if (resetCountButton) {
        resetCountButton.addEventListener('click', function() {
            resetCount();
        });
    }
    
    // 事件監聽器 - 設置偵測線
    if (setDetectionLineButton) {
        setDetectionLineButton.addEventListener('click', function() {
            setDetectionLine();
        });
    }
    
    // 事件監聽器 - 匯出Excel
    if (exportExcelButton) {
        exportExcelButton.addEventListener('click', function() {
            exportToExcel();
        });
    }
    
    // 事件監聽器 - 運動類型變更
    if (exerciseSelect) {
        exerciseSelect.addEventListener('change', function() {
            currentExerciseType = exerciseSelect.value;
            resetCount();
            
            // 更新教練提示，但不傳入角度數據（因為還沒有開始檢測）
            updateCoachTip('');
        });
        
        // 初始化運動類型
        currentExerciseType = exerciseSelect.value;
        updateCoachTip('');
    }






});


// 初始化Socket连接
function initSocketConnection() {
    console.log('初始化Socket连接');
    
    // 检查是否已存在Socket连接
    if (socket && socket.connected) {
        console.log('Socket已连接，跳过初始化');
        return socket;
    }
    
    // 如果socket存在但未连接，尝试重新连接
    if (socket) {
        console.log('Socket存在但未连接，尝试重新连接');
        socket.connect();
        return socket;
    }
    
    // 创建Socket连接 - 尝试多种连接方式
    try {
        console.log('创建新的Socket连接');
        
        // 尝试使用命名空间连接
        try {
            socket = io('/exercise', {
                reconnection: true,
                reconnectionAttempts: 5,
                reconnectionDelay: 1000,
                timeout: 10000
            });
            console.log('使用 /exercise 命名空间连接');
        } catch (err) {
            console.warn('使用命名空间连接失败，尝试默认连接:', err);
            socket = io({
                reconnection: true,
                reconnectionAttempts: 5,
                reconnectionDelay: 1000,
                timeout: 10000
            });
            console.log('使用默认连接');
        }
        
        // 移除所有现有事件监听器，避免重复绑定
        socket.off('connect');
        socket.off('connect_error');
        socket.off('disconnect');
        socket.off('exercise_count');
        socket.off('detection_result');
        socket.off('error');
        socket.off('start_detection_response');
        
        // 连接成功事件
        socket.on('connect', function() {
            console.log('Socket连接成功，ID:', socket.id);
            
            // 在连接成功后，重新获取 DOM 元素
            if (!exerciseCount) {
                exerciseCount = document.getElementById('exercise-count');
            }
            
            if (!exerciseCountStats) {
                exerciseCountStats = document.getElementById('exercise-count-stats');
            }
        });
        
        // 连接错误事件
        socket.on('connect_error', function(error) {
            console.error('Socket连接错误:', error);
            showErrorMessage('无法连接到服务器，请检查网络连接');
        });
        
        // 断开连接事件
        socket.on('disconnect', function(reason) {
            console.log('Socket断开连接:', reason);
            if (isDetecting) {
                stopDetection();
                showErrorMessage('与服务器的连接已断开，检测已停止');
            }
        });
        
        // 监听运动计数更新事件
        socket.on('exercise_count', function(data) {
            console.log('收到运动计数更新:', data);
            hasReceivedResponse = true;
            
            // 更新计数
            exerciseCounter = data.count;
            updateExerciseCount();
            
            // 更新怪物血量 - 只有在还有怪物需要击败时才减少血量
            if (currentMonsterIndex < totalMonsters) {
                decreaseMonsterHP(exerciseCounter);
            } else {
                console.log('所有怪物已击败，忽略血量更新');
            }
            
            // 更新质量分数
            if (data.quality !== undefined) {
                updateQualityScore(data.quality);
            }
            
            // 更新教练提示
            if (data.tip) {
                updateCoachTip(data.tip);
            }
        });
    
        
        // 监听错误事件
        socket.on('error', function(data) {
            console.error('收到错误消息:', data);
            showErrorMessage(data.message || '发生错误，请重试');
        });
        
        // 添加开始检测响应事件监听
        socket.on('start_detection_response', function(data) {
            console.log('收到开始检测响应:', data);
            hasReceivedResponse = true;
            
            if (data.status === 'success') {
                console.log('成功开始检测');
            } else {
                showErrorMessage('开始检测失败: ' + (data.message || '未知错误'));
                stopDetection();
            }
        });
        
        console.log('Socket事件监听器设置完成');
        return socket;
    } catch (e) {
        console.error('初始化Socket时出错:', e);
        showErrorMessage('初始化Socket连接失败: ' + e.message);
        return null;
    }
}

// 新增函数：重新绑定按钮事件
function rebindButtonEvents() {
    console.log('重新绑定按钮事件');
    
    // 获取按钮元素
    startButton = document.getElementById('start-btn') || 
                 document.getElementById('start-detection') || 
                 document.querySelector('.start-btn') ||
                 document.querySelector('button[data-action="start"]');
    
    stopButton = document.getElementById('stop-btn') || 
                document.getElementById('stop-detection') || 
                document.querySelector('.stop-btn') ||
                document.querySelector('button[data-action="stop"]');
    
    resetButton = document.getElementById('reset-btn') || 
                 document.getElementById('reset-count') || 
                 document.querySelector('.reset-btn');
    
    // 记录找到的按钮元素
    console.log('找到的按钮元素:', {
        startButton: startButton ? '存在' : '不存在',
        stopButton: stopButton ? '存在' : '不存在',
        resetButton: resetButton ? '存在' : '不存在'
    });
    
    // 绑定按钮事件
    if (startButton) {
        console.log('绑定开始按钮事件');
        // 移除可能存在的旧事件监听器
        startButton.removeEventListener('click', startDetection);
        // 添加新的事件监听器
        startButton.addEventListener('click', startDetection);
    }
    
    if (stopButton) {
        console.log('绑定停止按钮事件');
        // 移除可能存在的旧事件监听器
        stopButton.removeEventListener('click', stopDetection);
        // 添加新的事件监听器
        stopButton.addEventListener('click', stopDetection);
    }
    
    if (resetButton) {
        console.log('绑定重置按钮事件');
        // 移除可能存在的旧事件监听器
        resetButton.removeEventListener('click', resetCount);
        // 添加新的事件监听器
        resetButton.addEventListener('click', resetCount);
    }
    
    // 初始状态设置
    if (stopButton) stopButton.disabled = true;
    if (startButton) startButton.disabled = false;
}

function sendStartDetectionRequest() {
    console.log('发送开始检测请求');
    
    const requestData = {
        exercise_type: currentExerciseType,
        detection_line: detectionLine || 0.5,
        client_timestamp: Date.now(),
        current_level: currentLevel,  // 添加當前關卡信息
        monster_hp: monsterHP,        // 添加當前怪物血量
        initial_monster_hp: initialMonsterHP  // 添加初始怪物血量
    };
    
    console.log('请求数据:', requestData);
    
    // 发送请求
    socket.emit('start_detection', requestData);
    console.log('已发送开始检测请求，运动类型:', currentExerciseType, '關卡:', currentLevel);
    
    // 设置超时检查 - 增加超时时间并改进处理逻辑
    setTimeout(function() {
        if (isDetecting && !hasReceivedResponse) {
            console.warn('开始检测请求等待响应中...');
            
            // 检查socket状态
            console.log('Socket状态:', {
                connected: socket.connected,
                id: socket.id
            });
            
            // 尝试重新发送请求
            console.log('尝试重新发送请求...');
            socket.emit('start_detection', requestData);
            
            // 设置第二次超时检查
            setTimeout(function() {
                if (isDetecting && !hasReceivedResponse) {
                    console.error('服务器响应延迟，但继续等待...');
                    showErrorMessage('服务器响应较慢，请耐心等待或检查网络连接');
                    // 继续尝试第三次请求
                    socket.emit('start_detection', requestData);
                }
            }, 8000);
        }
    }, 8000);
}

function initMapScroll() {
    const scrollContainer = document.getElementById('map-scroll-container');
    const scrollLeftBtn = document.getElementById('scroll-left-btn');
    const scrollRightBtn = document.getElementById('scroll-right-btn');
    
    if (!scrollContainer || !scrollLeftBtn || !scrollRightBtn) {
        console.error('找不到小地圖滑動元素');
        return;
    }
    
    // 設置滑動按鈕事件
    scrollLeftBtn.addEventListener('click', () => {
        scrollContainer.scrollBy({
            left: -100,
            behavior: 'smooth'
        });
    });
    
    scrollRightBtn.addEventListener('click', () => {
        scrollContainer.scrollBy({
            left: 100,
            behavior: 'smooth'
        });
    });
    
    // 添加觸摸滑動支持
    let startX, scrollLeft;
    let isDragging = false;
    
    scrollContainer.addEventListener('touchstart', (e) => {
        startX = e.touches[0].pageX - scrollContainer.offsetLeft;
        scrollLeft = scrollContainer.scrollLeft;
    });
    
    scrollContainer.addEventListener('touchmove', (e) => {
        if (!startX) return;
        const x = e.touches[0].pageX - scrollContainer.offsetLeft;
        const walk = (x - startX) * 2; // 滑動速度
        scrollContainer.scrollLeft = scrollLeft - walk;
        
        // 如果滑動距離超過5px，標記為拖動
        if (Math.abs(scrollLeft - scrollContainer.scrollLeft) > 5) {
            isDragging = true;
        }
        
        e.preventDefault();
    });
    
    scrollContainer.addEventListener('touchend', () => {
        startX = null;
        // 300ms後重置拖動狀態，允許點擊
        setTimeout(() => {
            isDragging = false;
        }, 300);
    });
    
    // 為小地圖關卡點添加點擊事件
    const mapLevelItems = scrollContainer.querySelectorAll('.map-level-item');
    mapLevelItems.forEach((item, index) => {
        item.addEventListener('click', (e) => {
            // 如果是拖動，不處理點擊
            if (isDragging) return;
            
            // 設置當前關卡並初始化
            const newLevel = index + 1;
            console.log(`小地圖點擊: 選擇關卡 ${newLevel}`);
            
            // 初始化新關卡
            initLevel(newLevel);
            
            // 阻止事件冒泡
            e.stopPropagation();
        });
    });
    
    // 初始化詳細地圖滑動功能
    initFullMapScroll();
    
    // 高亮當前關卡
    highlightCurrentLevel();
}

// 修改高亮當前關卡函數，確保正確顯示當前關卡
function highlightCurrentLevel() {
    if (currentLevel === null) {
        currentLevel = 1; // 默認設置為第1關
    }
    
    console.log(`高亮當前關卡: ${currentLevel}`);
    
    // 更新小地圖
    const mapLevelDots = document.querySelectorAll('.map-level-dot');
    
    mapLevelDots.forEach((dot, index) => {
        // 移除所有狀態
        dot.classList.remove('completed', 'active');
        
        // 設置狀態
        if (index + 1 < currentLevel) {
            dot.classList.add('completed');
        } else if (index + 1 === currentLevel) {
            dot.classList.add('active');
        }
    });
    
    // 更新詳細地圖
    const fullMapNodes = document.querySelectorAll('.level-node');
    
    fullMapNodes.forEach((node, index) => {
        // 移除所有狀態
        node.classList.remove('completed', 'active');
        
        // 設置狀態
        if (index + 1 < currentLevel) {
            node.classList.add('completed');
        } else if (index + 1 === currentLevel) {
            node.classList.add('active');
        }
    });
}

// 初始化詳細地圖滑動功能
function initFullMapScroll() {
    const fullMapContainer = document.getElementById('full-map-scroll-container');
    const fullScrollLeftBtn = document.getElementById('full-scroll-left-btn');
    const fullScrollRightBtn = document.getElementById('full-scroll-right-btn');
    
    if (!fullMapContainer || !fullScrollLeftBtn || !fullScrollRightBtn) {
        console.error('找不到詳細地圖滑動元素');
        return;
    }
    
    // 設置滑動按鈕事件
    fullScrollLeftBtn.addEventListener('click', () => {
        fullMapContainer.scrollBy({
            left: -200,
            behavior: 'smooth'
        });
    });
    
    fullScrollRightBtn.addEventListener('click', () => {
        fullMapContainer.scrollBy({
            left: 200,
            behavior: 'smooth'
        });
    });
    
    // 添加觸摸滑動支持
    let startX, scrollLeft;
    let isDragging = false;
    
    fullMapContainer.addEventListener('touchstart', (e) => {
        startX = e.touches[0].pageX - fullMapContainer.offsetLeft;
        scrollLeft = fullMapContainer.scrollLeft;
    });
    
    fullMapContainer.addEventListener('touchmove', (e) => {
        if (!startX) return;
        const x = e.touches[0].pageX - fullMapContainer.offsetLeft;
        const walk = (x - startX) * 2; // 滑動速度
        fullMapContainer.scrollLeft = scrollLeft - walk;
        
        // 如果滑動距離超過5px，標記為拖動
        if (Math.abs(scrollLeft - fullMapContainer.scrollLeft) > 5) {
            isDragging = true;
        }
        
        e.preventDefault();
    });
    
    fullMapContainer.addEventListener('touchend', () => {
        startX = null;
        // 300ms後重置拖動狀態，允許點擊
        setTimeout(() => {
            isDragging = false;
        }, 300);
    });
    
    // 為詳細地圖關卡點添加點擊事件
    const fullMapLevelItems = fullMapContainer.querySelectorAll('.full-map-level-item');
    fullMapLevelItems.forEach((item, index) => {
        item.addEventListener('click', (e) => {
            // 如果是拖動，不處理點擊
            if (isDragging) return;
            
            // 設置當前關卡並初始化
            const newLevel = index + 1;
            console.log(`詳細地圖點擊: 選擇關卡 ${newLevel}`);
            
            // 初始化新關卡
            initLevel(newLevel);
            
            // 關閉模態視窗
            const mapModal = document.getElementById('map-modal');
            if (mapModal) {
                mapModal.classList.remove('active');
            }
            
            // 阻止事件冒泡
            e.stopPropagation();
        });
    });
    
    // 初始滾動到當前關卡
    setTimeout(() => {
        const activeNode = fullMapContainer.querySelector('.level-node.active');
        if (activeNode) {
            const parentItem = activeNode.closest('.full-map-level-item');
            if (parentItem) {
                const scrollPosition = parentItem.offsetLeft - (fullMapContainer.clientWidth / 2) + (parentItem.clientWidth / 2);
                fullMapContainer.scrollTo({
                    left: scrollPosition,
                    behavior: 'smooth'
                });
            }
        }
    }, 300);
}



// 設置地圖模態視窗事件
function setupMapModal() {
    const mapModal = document.getElementById('map-modal');
    const showMapBtn = document.getElementById('show-map-btn');
    const closeMapBtn = document.getElementById('close-map-btn');
    const closeMapModalBtn = document.getElementById('close-map-modal');
    const startLevelBtn = document.getElementById('start-level-btn');
    
    if (!mapModal || !showMapBtn || !closeMapBtn || !closeMapModalBtn || !startLevelBtn) {
        console.error('找不到地圖模態視窗元素');
        return;
    }
    
    showMapBtn.addEventListener('click', () => {
        mapModal.classList.add('active');
        // 初始滾動到當前關卡
        const fullMapContainer = document.getElementById('full-map-scroll-container');
        if (fullMapContainer) {
            const activeNode = fullMapContainer.querySelector('.level-node.active');
            if (activeNode) {
                const parentItem = activeNode.closest('.full-map-level-item');
                if (parentItem) {
                    const scrollPosition = parentItem.offsetLeft - (fullMapContainer.clientWidth / 2) + (parentItem.clientWidth / 2);
                    fullMapContainer.scrollTo({
                        left: scrollPosition,
                        behavior: 'smooth'
                    });
                }
            }
        }
    });
    
    closeMapBtn.addEventListener('click', () => {
        mapModal.classList.remove('active');
    });
    
    closeMapModalBtn.addEventListener('click', () => {
        mapModal.classList.remove('active');
    });
    
    startLevelBtn.addEventListener('click', () => {
        // 獲取當前選中的關卡
        const activeNode = document.querySelector('.full-map-levels .level-node.active');
        if (activeNode) {
            const levelIndex = Array.from(document.querySelectorAll('.full-map-levels .level-node')).indexOf(activeNode) + 1;
            if (levelIndex > 0) {
                console.log(`開始挑戰按鈕點擊: 選擇關卡 ${levelIndex}`);
                
                // 初始化選中的關卡
                initLevel(levelIndex);
                
                // 關閉模態視窗
                mapModal.classList.remove('active');
                
                // 停止當前偵測（如果有）
                if (isDetecting) {
                    stopDetection();
                }
                
                // 延遲一段時間後自動開始偵測
                setTimeout(() => {
                    startDetection();
                }, 1000);
            }
        }
    });
}


// 顯示關卡開始提示
function showLevelStartNotification(levelIndex) {
    // 獲取關卡名稱
    const levelNames = ['森林入口', '山脈地帶', '神秘湖泊', '古老洞窟', '龍之巢穴'];
    const levelName = levelNames[levelIndex - 1] || `第 ${levelIndex} 關`;
    
    // 創建通知元素
    const notification = document.createElement('div');
    notification.className = 'level-start-notification';
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-icon">
                <i class="fas fa-play-circle"></i>
            </div>
            <div class="notification-text">
                <h3>開始挑戰</h3>
                <p>${levelName}</p>
            </div>
        </div>
    `;
    
    // 添加到頁面
    document.body.appendChild(notification);
    
    // 顯示動畫
    setTimeout(() => {
        notification.classList.add('show');
        
        // 3秒後移除
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 500);
        }, 3000);
    }, 100);
}

// 更新關卡顯示
function updateLevelDisplay(level) {
    // 更新關卡標題
    const levelTitle = document.querySelector('.level-title');
    if (levelTitle) {
        levelTitle.textContent = `關卡 ${level}`;
    }
    
    // 更新怪物計數顯示
    const monsterCount = document.getElementById('monster-count');
    if (monsterCount) {
        monsterCount.textContent = `關卡 ${level} 怪物`;
    }
    
    // 更新關卡描述
    const levelDesc = document.querySelector('.level-description');
    if (levelDesc) {
        // 根據關卡設置不同的描述
        switch(level) {
            case 1:
                levelDesc.textContent = '森林入口 - 初始關卡，適合新手挑戰';
                break;
            case 2:
                levelDesc.textContent = '山脈地帶 - 中級難度，需要更多力量';
                break;
            case 3:
                levelDesc.textContent = '神秘湖泊 - 需要耐力與平衡';
                break;
            case 4:
                levelDesc.textContent = '古老洞窟 - 高難度，需要全面技能';
                break;
            case 5:
                levelDesc.textContent = '龍之巢穴 - 最終挑戰，考驗極限';
                break;
            default:
                levelDesc.textContent = `第 ${level} 關 - 挑戰更高難度`;
        }
    }
}



// 新增函數：發送關卡完成請求到伺服器
function updateLevelCompletion(levelId, expReward) {
    console.log(`發送關卡完成請求: 關卡 ${levelId}, 經驗值 ${expReward}`);
    
    // 獲取用戶ID (從頁面元素或使用默認值)
    const userId = document.getElementById('student-id') ? 
                  document.getElementById('student-id').value : 'C111151146';
    
    console.log(`用戶ID: ${userId}, 關卡ID: ${levelId}, 經驗值: ${expReward}, 運動類型: ${currentExerciseType}, 運動計數: ${exerciseCounter}`);
    
    // 發送請求到伺服器
    fetch('/api/game/complete_level', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,
            level_id: levelId,
            exp_reward: expReward,
            exercise_type: currentExerciseType || 'squat',
            exercise_count: exerciseCounter || 0
        })
    })
    .then(response => {
        console.log(`API響應狀態: ${response.status}`);
        if (!response.ok) {
            throw new Error(`HTTP錯誤! 狀態: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('關卡完成API響應數據:', data);
        if (data.success) {
            console.log('關卡完成數據已保存:', data);
            
            // 顯示成功訊息
            showNotification(`關卡 ${levelId} 完成！獲得 ${expReward} 經驗值`, 'success');
            
            // 如果有新解鎖的成就，顯示成就通知
            if (data.new_achievements && data.new_achievements.length > 0) {
                data.new_achievements.forEach(achievement => {
                    showAchievementNotification(achievement.name, achievement.description);
                });
            }
        } else {
            console.error('關卡完成數據保存失敗:', data.message);
            showNotification(`關卡數據保存失敗: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('關卡完成請求錯誤:', error);
        showNotification(`關卡完成請求錯誤: ${error.message}`, 'error');
        
        // 嘗試重新發送請求
        setTimeout(() => {
            console.log('嘗試重新發送關卡完成請求...');
            retryLevelCompletion(userId, levelId, expReward);
        }, 2000);
    });
}


// 添加重試函數
function retryLevelCompletion(userId, levelId, expReward) {
    console.log(`重試發送關卡完成數據: 用戶 ${userId}, 關卡 ${levelId}, 經驗值 ${expReward}`);
    
    // 獲取用戶設定的重量和組數
    const weight = document.getElementById('weight') ? 
                  parseInt(document.getElementById('weight').value) || 0 : 0;

    const reps = document.getElementById('reps') ? 
                parseInt(document.getElementById('reps').value) || 10 : 10;

    const sets = document.getElementById('sets') ? 
               parseInt(document.getElementById('sets').value) || 3 : 3;
    
    // 計算已完成的組數
    const completedSets = remainingSets !== undefined ? (sets - remainingSets) : 0;
    
    // 發送請求到後端
    fetch('/api/game/complete_level', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,
            level_id: levelId,
            exp_reward: expReward,
            exercise_type: currentExerciseType || 'squat',
            exercise_count: exerciseCounter || 0,
            shield_value: initialMonsterShield,
            shield_weight: shieldWeightFactor,
            weight: weight,
            reps: reps,
            sets: sets,
            completed_sets: completedSets
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('重試成功: 關卡完成數據已保存');
            showNotification('關卡數據已成功保存', 'success');
        } else {
            console.error('重試失敗: 關卡完成數據保存失敗');
            showNotification('關卡數據保存失敗，請稍後再試', 'error');
        }
    })
    .catch(error => {
        console.error('重試發送關卡完成請求時出錯:', error);
    });
}


// 添加通知函數
// 顯示通知訊息
function showNotification(message, type = 'info') {
    console.log(`顯示通知: ${message} (類型: ${type})`);
    
    // 檢查是否已存在通知容器
    let notificationContainer = document.querySelector('.notification-container');
    
    // 如果不存在，則創建一個
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.className = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '9999';
        document.body.appendChild(notificationContainer);
    }
    
    // 創建通知元素
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 設置樣式
    notification.style.backgroundColor = type === 'success' ? '#4CAF50' : 
                                        type === 'error' ? '#f44336' : 
                                        type === 'warning' ? '#ff9800' : '#2196F3';
    notification.style.color = 'white';
    notification.style.padding = '15px 20px';
    notification.style.marginBottom = '10px';
    notification.style.borderRadius = '5px';
    notification.style.boxShadow = '0 2px 5px rgba(0, 0, 0, 0.2)';
    notification.style.opacity = '0';
    notification.style.transition = 'opacity 0.3s, transform 0.3s';
    notification.style.transform = 'translateX(50px)';
    
    // 添加到容器
    notificationContainer.appendChild(notification);
    
    // 淡入通知
    setTimeout(function() {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // 5秒後淡出通知
    setTimeout(function() {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(50px)';
        
        // 移除通知
        setTimeout(function() {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}



function initGameUI() {
    console.log('初始化遊戲UI');
    
    // 獲取關卡顯示元素
    const levelDisplay = document.getElementById('current-level');
    if (levelDisplay) {
        // 如果已設置當前關卡，則顯示
        if (currentLevel) {
            levelDisplay.textContent = currentLevel;
        } else {
            // 否則設置為第一關
            currentLevel = 1;
            levelDisplay.textContent = '1';
        }
    } else {
        console.error('找不到關卡顯示元素');
    }
    
    // 創建怪物血量條
    createMonsterHPBar();
    
    // 創建怪物護盾條
    createMonsterShieldBar();
    
    // 初始化護盾控件
    initShieldControls();
    
    // 更新怪物血量和護盾顯示
    updateMonsterHP(monsterHP);
    updateMonsterShield(monsterShield);
    
    // 更新剩餘組數顯示
    updateRemainingSetsDisplay();
    
    console.log('遊戲UI初始化完成');
}


function resetMonster() {
    console.log('重置怪物');
    
    // 重置怪物血量
    monsterHP = initialMonsterHP;
    
    // 重置怪物護盾
    monsterShield = initialMonsterShield;
    
    // 更新顯示
    updateMonsterHP(monsterHP);
    updateMonsterShield(monsterShield);
    
    // 重置運動計數器
    exerciseCounter = 0;
    decreaseMonsterHP.lastCount = 0;
    
    // 更新運動計數顯示
    updateExerciseCount(0);
    
    // 重置剩餘組數
    const setsInput = document.getElementById('sets');
    if (setsInput) {
        remainingSets = parseInt(setsInput.value) || 3;
    } else {
        remainingSets = 3;
    }
    
    // 更新剩餘組數顯示
    updateRemainingSetsDisplay();
    
    // 顯示重置訊息
    showNotification('怪物已重置', 'info');
    
    // 顯示怪物對話
    showMonsterDialogue('我恢復了力量，再來挑戰吧！');
}