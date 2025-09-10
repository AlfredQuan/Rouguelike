Roguelike Survivor — 架构设计文档（v0.1）

本文件是项目的唯一架构规范（Single Source of Truth）。后续所有编码需严格遵循此文档；如需调整，请先修改本架构文档，再据此更新实现。

1. 目标与设计原则
- 目标
  - 提升稳定性与可测试性，减少“状态不同步”和偶发性 Bug。
  - 数据驱动与热插拔内容：新增/调整角色、敌人、武器、波次只需改数据。
  - 单向数据流：UI → 命令（Command）→ 逻辑/ECS → 事件（Event）→ UI，确保状态一致。
  - 渐进式重构：在不推翻现有代码的前提下分阶段落地。
- 原则
  - 单一事实来源（SSOT）：局外（MetaState）与对局（RunState）分离管理。
  - 明确边界：ECS 只做世界逻辑；UI 不直接改逻辑；商店/存档走服务层。
  - 不变式守护：关键状态集中校验（如主武器必存在，fire_rate>0）。
  - 优先采用成熟库：UI/状态机/数据校验/依赖注入/测试均用社区成熟方案。

2. 技术路线（尽量采用成熟库）
- 渲染/输入/音频：pygame、pygame.mixer
- UI：pygame_gui（主题在 assets/ui/theme.json）
- ECS：esper
- 状态机（FSM）：transitions（或第一阶段使用轻量 Enum + 表驱动）
- 数据校验：pydantic（从 YAML 加载后做模型验证与默认值填充）
- 依赖注入（可选）：dependency-injector
- 持久化：json + Pydantic 序列化（ProfileStore/SaveManager）
- 日志：loguru（或 Python logging）
- 测试：pytest（单元/集成/快照测试）

3. 目录结构
roguelike/
  app.py 或 game.py            # 应用组装与主循环（UI、Bus、Systems）
  ecs/
    components.py              # 或按领域拆分多个文件
    systems/
      input.py                 # 输入意图
      movement.py              # 移动
      ai.py                    # 敌人 AI / 射击
      combat.py                # 武器开火/碰撞/伤害/弹丸寿命
      spawner.py               # 刷怪/波次/掉落（消费命令/事件，不直接读 UI）
      cleanup.py               # 弹丸/拾取上限、过期清理
      audit.py                 # 不变式审计（主武器合法、速度残留清零等）
      render.py                # 纯世界绘制（不绘 UI）
  ui/
    ui_manager.py              # pygame_gui 统一管理
    views/
      meta_menu.py             # 商店/成就/存档
      pause.py                 # 暂停/作弊
      hud.py                   # 血条/经验/武器/波次计时
      levelup.py               # 选卡UI
      results.py               # 结算
  state/
    fsm.py                     # transitions 定义：MainMenu/Meta/Running/Paused/LevelUp/Results
    store.py                   # StateStore：MetaState/RunState（单一入口）
    command.py                 # 命令定义与DTO
    event.py                   # 事件定义与DTO
    bus.py                     # CommandBus/EventBus 分发
  services/
    content.py                 # YAML→Pydantic 模型加载与校验
    profile.py                 # ProfileStore / SaveManager
    shop.py                    # 商店服务：扣费/解锁/升级
    wave.py                    # WaveScheduler 纯函数
    assets.py                  # 资源管理：UI/精灵/场景/音频（带缺省方案）
    rng.py                     # 统一 RNG 注入

数据文件：data/*.yaml（characters/enemies/weapons_main/weapons_sub/cards/waves/upgrades）
主题与素材：assets/ui/theme.json、assets/images/*、assets/audio/*。

4. 状态与数据模型
4.1 MetaState（局外）
currency: int
unlocked_mains: list[str]    # 默认 ['basic_bolt']
unlocked_subs: list[str]     # 默认 ['orbital_blade']
main_switch_unlocked: bool
selected_main: str
achievements: dict[str,bool]
upgrades: dict[str,int]      # 局外成长（如 move_speed_lv）

4.2 RunState（对局）
time_sec: float, kills: int, score: float
paused: bool, in_levelup: bool
current_wave_idx: int, surge_timer: float
banner_text: str, banner_time_left: float

4.3 Pydantic 模型（示例）
- WeaponMain/WeaponSub：行为、颜色、尺寸、数值范围校验；给默认值（fire_rate>0 等）。
- Enemy：behavior in {'chase','shooter'}；射手类必须包含 proj_* 字段。
- Wave：start>=0、duration>=0、spawn_interval>0；weights 非负；可选 boss {key, at|at_end}。
- Card/Upgrade：effect 为枚举；requires/repeatable/amount 按语义校验。

5. 命令/事件接口（API）
- 命令（UI→Bus）：
  UnlockMain{key} / UnlockSub{key} / UnlockUpgrade{key}
  SelectMain{key}
  ApplyCard{key}
  StartRun{} / EndRun{stats}
  Cheat{kind, payload}（开发模式）
- 事件（逻辑→UI）：
  ProfileChanged{}、UpgradesChanged{}
  WaveStarted{idx}、HordeIncoming{in_seconds}、BossSpawned{key}
  Banner{text, seconds}（UI 可直接渲染）

处理约定：
- ShopService 处理解锁命令（余额校验→扣费→更新 MetaState→发 ProfileChanged）。
- WaveScheduler 提供 step/time_to_next，Spawner 只消费“SpawnEnemy(key)”命令或事件。
- ApplyCard 集中做 clamp（如 fire_rate>0），不在系统里分散补丁。

6. ECS 系统合同（读写约定与顺序）
1) InputSystem：读键盘→产出 MoveIntent
2) Gate（Pause/LevelUp）：屏蔽意图；帧尾清零 Velocity
3) WeaponFireSystem：读 Loadout+WeaponInstance→生成 Projectile
4) EnemyAISystem：移动/射击意图（含 Shooter）
5) MovementSystem：消耗 Velocity/Intent 更新 Position（世界边界/障碍处理）
6) CollisionSystem：弹丸/敌人/玩家/拾取碰撞
7) Damage/DeathSystem：结算伤害、掉落经验/回血/金币
8) SpawnerSystem：按命令/事件生成敌人/掉落/波次推进
9) CleanupSystem：弹丸/拾取上限与过期回收
10) AuditSystem：不变式校验（主武器存在、fire_rate>0、速度残留清零）
11) RenderSystem：只绘制世界（UI 由 ui_manager 负责）

7. UI 规范（pygame_gui）
- 主题文件：assets/ui/theme.json（颜色、边框、圆角、字体等统一）。
- 视图与事件：UI 只发命令（如 Unlock/Select/ApplyCard），订阅事件来刷新（ProfileChanged/WaveStarted 等）。
- HUD：左上角紧凑；波次计时单独右上角；武器状态并入 HUD。
- 暂停：按钮式作弊（通过 Cheat 命令转业务层，不直改逻辑）。
- 选卡：三卡面板（无外框），按 1/2/3 或点击；应用后关闭并清零速度。

8. 资源接口（美术与音乐）
8.1 资源路径与注册
- 图像：assets/images/（ui/、sprites/、tiles/ 等子文件夹）
- 音频：assets/audio/（sfx/、bgm/）
- UI 主题：assets/ui/theme.json
- 资源注册（可选 YAML）：data/assets.yaml（key→file path、默认颜色/半径等）

8.2 AssetManager（services/assets.py，接口约定）
class AssetManager:
    def __init__(self, base_dir='assets')
    def load_image(self, key: str) -> Optional[pygame.Surface]
    def load_sound(self, key: str) -> Optional[pygame.mixer.Sound]
    def sprite_for_enemy(self, enemy_key: str) -> Union[Surface, Fallback]
    def sprite_for_player(self, char_key: str) -> Union[Surface, Fallback]
    def ui_theme(self) -> Optional[path]

- Fallback 策略（当资源缺失时）：
  - 图像：用纯色圆/矩形（当前项目样式）+ 可选描边代替。
  - 字体：用 pygame 默认字体。
  - 音效：缺失则静默（或用短促 beep 代替，开发开关）。
  - 背景音乐：缺失则不播放。
- 场景/地图：预留 tilemap（CSV/JSON/TMX）加载接口；缺失则使用网格背景（当前方案）。

9. 商店/解锁/存档（命令化）
- ShopService：
  unlock_main(key) / unlock_sub(key) / unlock_upgrade(key) → 扣费、检查已解锁、更新 MetaState、发 ProfileChanged。
  UI 列表只展示“锁/解锁”状态，点击按钮发送命令，不直接改 Profile。
- 存档槽位（SaveManager）：
  list_slots() / save_to_slot() / load_from_slot() / delete_slot()
  Save 页提供三个槽位按钮，显示摘要（货币/总击杀/时间/解锁数）。

10. 经济与结算
- config/settings.yaml：economy.score_to_currency / kills_to_currency / time_to_currency 可调。
- EndRun 命令计算收入，累加 MetaState totals 与成就；发 ProfileChanged 与 AchievementUpdated。

11. 日志与错误处理
- loguru：
  内容加载失败→报错定位文件与字段。
  Boss 生成/波次切换/解锁/选卡→INFO 级日志，便于回溯。
- 开发模式开关（DEV）：显示调试 HUD（主武器 key/fire_rate/cooldown、当前波次等）。

12. 测试
- 单元测试（pytest）：WaveScheduler、ApplyCard、WeaponCooldown、ShopService。
- 集成测试：命令流模拟（StartRun→Unlock→SelectMain→ApplyCard），断言状态与 ECS 输出。
- UI 冒烟：关键按钮触发命令，事件返回刷新；使用 monkeypatch 或假 Bus。

13. 迁移计划（三阶段）
1) 第一阶段（主干）：
   引入 StateStore + CommandBus + FSM（暂停/选卡/结算命令化）。
   Input→MoveIntent，帧尾清零残速；AuditSystem 保障主武器不变式。
2) 第二阶段（内容/波次/商店）：
   抽出 WaveScheduler；Spawner 消费 Spawn 命令；Boss at_end/at 由调度派发。
   ShopService 替代 UI 直改；Meta Menu 改命令/事件。
3) 第三阶段（数据/测试/资源）：
   Pydantic 校验；tests 覆盖主路径；AssetManager 引入与替换图形/音频访问。

14. 编码约定
- 任何架构/流程变更先更新本文件，再提交实现。
- 系统间不要跨层调用：UI 不改 ECS/State；ECS 不读 UI/存档。
- 所有命令/事件应归档（central registry），避免“字符串魔法”。

---
（NOTE）当前项目暂未完全迁移到该架构；迁移中优先保证：
- 选卡后清零残速
- 主武器不变式校验与自愈
- Boss 波次触发的可靠性
- 商店解锁→选主武器一致
