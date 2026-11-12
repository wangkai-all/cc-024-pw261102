# 订阅收入 MRR 变动与首付月份留存

从 **合同事件流** 还原客户层 MRR，按月拆解收入变化，并用 ECharts 展示瀑布图与首付月份留存表。后端以 DuckDB 为唯一事实来源，FastAPI 在启动时重建全部月份快照。

- 报告窗口：`2025-01` 至 `2026-10`（22 个完整月份）
- 当前未结束月份：`2026-11`（留存表中留空）
- 截至日期：`2026-11-12`
- 金额单位：人民币（CNY）；计算保留 4 位小数，展示保留 2 位小数

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11、FastAPI、DuckDB |
| 前端 | React 19、Vite 8、ECharts 6 |
| 测试 | pytest、FastAPI TestClient |

## 目录

```
backend/
  app/
    config.py       报告日历、分类与口径常量
    seed_data.py    确定性的客户 / 合同 / 事件示例数据
    db.py           DuckDB 建表、种子数据、连接
    engine.py       事件还原、月度快照、桥接、留存、客户明细
    main.py         FastAPI 路由与前端静态资源托管
  tests/test_engine.py
  requirements.txt
frontend/
  src/
    App.jsx         仪表盘布局与交互
    api.js          API 客户端
    theme.js        明暗主题、色阶、极性颜色
    format.js       金额 / 百分比 / 月份格式化
    components/     瀑布图、留存表、抽屉等
```

## 运行

### 1. 后端

```bash
cd /workspace
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

cd backend
../.venv/bin/uvicorn app.main:app --reload --port 8000
```

首次启动会在 `backend/data/mrr.duckdb` 创建数据库并写入示例事件；再次启动复用已有数据。需要全新数据库时删除该文件，或通过 `MRR_DB_PATH` 指向其他路径：

```bash
MRR_DB_PATH=/tmp/mrr-demo.duckdb ../.venv/bin/uvicorn app.main:app --port 8000
```

接口文档：<http://127.0.0.1:8000/docs>

### 2. 前端

开发模式（Vite 把 `/api` 代理到 `127.0.0.1:8000`）：

```bash
cd /workspace/frontend
npm install
npm run dev
```

生产构建后，FastAPI 会直接托管 `frontend/dist`：

```bash
cd /workspace/frontend
npm run build
# 访问 http://127.0.0.1:8000/
```

### 3. 测试

```bash
cd /workspace/backend
../.venv/bin/python -m pytest -q tests/test_engine.py
```

## 业务规则

### MRR

- 只计算 **已生效的付费合同**。`trial_start` 不产生 MRR；试用转付费时从 `paid_start` 生效。
- 月付合同取周期金额；年付合同取 `金额 ÷ 12`。
- MRR 是 **月末时点值**，不做月内按天摊销，也不做跨月补差。
- 合同状态由事件流按 `effective_date` 重建；同一天的事件按 `event_order` 顺序处理。
- `cancel_scheduled` 只登记待取消；到 `effective_date` 才结束合同并减少 MRR。
- `pause` / `resume` 按生效日期处理；暂停期间该合同 MRR 为 0。
- 退款 `refund` 是独立现金指标，只进入退款列表与 `refund_total_rmb`，不修改合同 MRR。

### 客户层聚合

先把同一客户的所有合同 MRR 加总为 **客户层 MRR**，再做桥接分类。这样在升级时“旧合同结束 + 新合同同日生效”不会因为单份合同归零而被误判为客户流失。

### 月度桥接

对每个客户比较 **上月末** 与 **本月末** 的客户层 MRR：

| 上月末 | 本月末 | 判定 |
| --- | --- | --- |
| 0 | > 0 | 本月有恢复事件 → `resume`；月初前曾经付费 → `reactivation`；否则 → `new` |
| > 0 | 0 | 月末处于暂停状态 → `pause`；否则 → `churn` |
| > 0 | > 0 | 差额 > 0 → `upgrade`；差额 < 0 → `downgrade` |
| 0 | 0 | 没有桥接项；若月内有净额为零的事件变动，进入“月内抵消”事件流水 |

`resume` / `pause` 是独立展示分类，避免把临时暂停误报为回流或流失；它们仍然计入精确桥接。

### 精确闭合与显示尾差

内部用 4 位小数计算：

```
期初 + 所有桥接分项 = 期末          # difference_rmb == 0
```

展示时各金额按分四舍五入。若“期初显示值 + 分项显示值之和”与“期末显示值”相差 0.01，瀑布图会插入 **舍入尾差** 步骤，例如 `2026-02` 的 `+¥0.01`。该步骤只解释展示舍入，不是业务事件。

### 月内抵消

客户月内先升级再降级、或先暂停再恢复，月末回到月初 MRR，则桥接净变化为零。这类事件不进入桥接分项，而进入 **月内抵消事件流水**，保留完整事件链与前后 MRR。

### 首付月份留存

- 首付月份 = 客户第一次产生正 MRR 的月份（试用月份不算）。
- 每个单元格 = 该首付月份客户中，在观察月末客户层 MRR 仍 > 0 的比例。
- 首付月份之前的单元格显示 `—`，不适用。
- `2026-11` 尚未结束，未来月份留空。
- 留存下降后再次上升是可能的：客户流失后回流会重新变为正 MRR。

## 示例场景

页面顶部提供 8 个可点击场景，点击后切换到对应月份并打开客户明细：

| 场景 | 客户 / 月份 | 预期 |
| --- | --- | --- |
| 预约取消，到期才减少 | C003 · 2026-06 → 2026-07 | 6 月末仍为 8,000 且标记待取消；7 月才记流失 −8,000 |
| 同月多次升降级 | C008 · 2025-10 / 2025-11 | 10 月净记 +500；11 月升降相抵，进入抵消流水 |
| 年付与舍入尾差 | C002 / C029 · 2026-02 | 100,000 年付月化为 8,333.3333；显示尾差 +0.01 单列 |
| 多合同升级不算流失 | C004 · 2026-04 | 客户层 10,000 → 16,000，记升级 +6,000，不记流失 |
| 试用不计 MRR | C005 · 2025-02 | 1 月试用 MRR=0；2 月转付费记新增 5,000，首付月 2025-02 |
| 暂停与恢复按生效时间 | C007 · 2025-07 / 2025-09 | 7 月暂停 −5,500；9 月恢复 +5,500 |
| 流失后回流 | C027 · 2026-03 | 月初前曾付费，零转正记回流 |
| 退款只进现金指标 | C018 · 2025-12 | 退款 2,000 进入现金指标，合同 MRR 仍为 8,000 |

## API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 数据规模、币种与健康状态 |
| GET | `/api/meta` | 月份列表、分类、口径说明、场景 |
| GET | `/api/mrr/bridge?month=YYYY-MM` | 月度桥接：分项、客户明细、瀑布步骤、抵消流水、待生效变更、退款、闭合校验 |
| GET | `/api/retention` | 首付月份留存矩阵；未来月份为空 |
| GET | `/api/retention/cell?cohort=YYYY-MM&month=YYYY-MM` | 某留存单元格的活跃 / 零 MRR 客户名单 |
| GET | `/api/customers/{customer_id}/detail?month=YYYY-MM` | 客户月初 / 月末快照、合同对比、当月事件、12 个月趋势 |
| GET | `/api/scenarios` | 示例场景列表 |
| GET | `/api/refunds?month=YYYY-MM` | 退款现金指标（不改 MRR） |

## 数据模型

DuckDB 中的原始表：

- `customers`：客户主数据
- `contracts`：合同主数据与标准周期金额
- `contract_events`：append-only 事件流，字段包括 `event_date`、`effective_date`、`event_order`、`event_type`、`amount_rmb`、`billing_cycle`

启动时由事件流重建并物化以下表，API 与留存 SQL 都从这些结果读取：

- `monthly_contract_mrr`：每个合同每月末的状态与 MRR
- `monthly_customer_mrr`：客户层月末 MRR
- `event_effects`：每个 MRR 事件对客户层 MRR 的前后值与差额
- `customer_cohorts`：客户首付月份
- `month_dim`：报告月份维度

所有金额字段使用 `DECIMAL(18, 4)`；接口输出统一为保留 2 位小数的数值，并同时提供 4 位精度的闭合校验字段。
