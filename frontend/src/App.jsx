import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import BucketDrawer from './components/BucketDrawer'
import CustomerDrawer from './components/CustomerDrawer'
import RetentionCellDrawer from './components/RetentionCellDrawer'
import RetentionTable from './components/RetentionTable'
import WaterfallChart from './components/WaterfallChart'
import { getChartTheme } from './theme'
import {
  categoryIcon,
  deltaClass,
  fmtMoney,
  fmtMonth,
  fmtSignedPct,
} from './format'

function KpiCard({ label, value, meta, tone = '', extra = null }) {
  return (
    <div className={`kpi-card ${tone}`}>
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{value}</strong>
      {meta ? <span className="kpi-meta">{meta}</span> : null}
      {extra}
    </div>
  )
}

function ComponentList({ bridge, onSelect }) {
  const visible = bridge.components.filter((component) => component.count > 0)
  const maxAbs = Math.max(1, ...visible.map((component) => Math.abs(component.amount_rmb)))
  if (!visible.length) {
    return <div className="empty-note">本月客户层 MRR 没有桥接类别变动。</div>
  }
  return (
    <div className="component-list">
      {visible.map((component) => {
        const positive = component.amount_rmb >= 0
        return (
          <button
            className="component-row"
            key={component.key}
            onClick={() => onSelect(component.key)}
            title={`查看 ${component.label} 的客户明细`}
          >
            <span className={`category-icon category-${component.key}`}>
              {categoryIcon(component.key)}
            </span>
            <span className="component-main">
              <span className="component-label">
                {component.label}
                <span className="muted small">{component.count} 个客户</span>
              </span>
              <span className="component-bar-track">
                <span
                  className={`component-bar ${positive ? 'positive' : 'negative'}`}
                  style={{ width: `${(Math.abs(component.amount_rmb) / maxAbs) * 100}%` }}
                />
              </span>
            </span>
            <span className={`component-amount mono ${positive ? 'is-positive' : 'is-negative'}`}>
              {fmtMoney(component.amount_rmb, { sign: true })}
            </span>
          </button>
        )
      })}
    </div>
  )
}

function JourneyTable({ bridge, filter, onFilter, onSelectCustomer }) {
  const categories = bridge.components.filter((component) => component.count > 0)
  const items = categories.flatMap((component) =>
    component.items.map((item) => ({ ...item, categoryKey: component.key })),
  )
  const visible = filter === 'all' ? items : items.filter((item) => item.categoryKey === filter)

  return (
    <section className="card bridge-table-card">
      <div className="card-header">
        <div>
          <div className="eyebrow">Customer-level bridge</div>
          <h2>桥接明细 · 每个客户一项</h2>
          <p className="card-subtitle">
            多合同客户先加总到客户层；点击任意一行查看该月月初/月末快照与合同事件。
          </p>
        </div>
      </div>
      <div className="filter-row" role="tablist" aria-label="按桥接类别筛选">
        <button
          className={`filter-chip ${filter === 'all' ? 'active' : ''}`}
          onClick={() => onFilter('all')}
        >
          全部 <span>{items.length}</span>
        </button>
        {categories.map((component) => (
          <button
            key={component.key}
            className={`filter-chip ${filter === component.key ? 'active' : ''}`}
            onClick={() => onFilter(component.key)}
          >
            {component.label} <span>{component.count}</span>
          </button>
        ))}
      </div>
      <div className="table-scroll">
        <table className="data-table journey-table">
          <thead>
            <tr>
              <th>客户</th>
              <th>类别</th>
              <th className="num">上月 MRR</th>
              <th className="num">本月 MRR</th>
              <th className="num">变化</th>
              <th className="num">事件</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visible.map((item) => (
              <tr key={item.customer_id} className="clickable-row" onClick={() => onSelectCustomer(item.customer_id)}>
                <td>
                  <strong>{item.customer_name}</strong>
                  <div className="muted small">
                    {item.city} · {item.segment}
                  </div>
                </td>
                <td>
                  <span className={`category-badge category-${item.categoryKey}`}>
                    <span className="category-icon">{categoryIcon(item.categoryKey)}</span>
                    {item.category_label}
                  </span>
                  <div className="muted small reason-text">{item.reason}</div>
                </td>
                <td className="num mono">{fmtMoney(item.mrr_before_rmb)}</td>
                <td className="num mono">{fmtMoney(item.mrr_after_rmb)}</td>
                <td className={`num mono ${deltaClass(item.delta_rmb)}`}>
                  {fmtMoney(item.delta_rmb, { sign: true })}
                </td>
                <td className="num mono">{item.event_count}</td>
                <td className="row-arrow-cell">›</td>
              </tr>
            ))}
            {!visible.length ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-note">没有符合筛选的客户。</div>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function OffsetLedger({ groups, onSelectCustomer }) {
  if (!groups.length) return null
  return (
    <section className="card offset-card">
      <div className="card-header">
        <div>
          <div className="eyebrow">Offsetting movements</div>
          <h2>月内抵消 · 单独事件流水</h2>
          <p className="card-subtitle">
            月内先升后降（或先开后停）回到原点，净变化为零，不进入桥接，只在这里留痕。
          </p>
        </div>
      </div>
      <div className="offset-list">
        {groups.map((group) => (
          <button
            className="offset-row"
            key={group.customer_id}
            onClick={() => onSelectCustomer(group.customer_id)}
          >
            <div className="offset-head">
              <strong>{group.customer_name}</strong>
              <span className="muted small">
                月初 {fmtMoney(group.mrr_before_rmb)} → 月末 {fmtMoney(group.mrr_after_rmb)}
              </span>
              <span className="tag">抵消 {fmtMoney(group.offset_rmb)}</span>
            </div>
            <div className="offset-events">
              {group.events.map((event) => (
                <span className="offset-event" key={event.event_id}>
                  <span className={deltaClass(event.delta_rmb)}>{fmtMoney(event.delta_rmb, { sign: true })}</span>
                  <span className="muted">{event.event_type_label}</span>
                  <span className="mono muted">{event.effective_date}</span>
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}

function PendingCard({ changes, onSelectCustomer }) {
  if (!changes.length) return null
  return (
    <section className="card pending-card">
      <div className="card-header">
        <div>
          <div className="eyebrow">Scheduled changes</div>
          <h2>待生效 · 预约取消</h2>
          <p className="card-subtitle">已预约但尚未到期的合同，在本月末仍计入 MRR。</p>
        </div>
      </div>
      <div className="compact-list">
        {changes.map((change) => (
          <button
            className="compact-row"
            key={`${change.contract_id}-${change.effective_date}`}
            onClick={() => onSelectCustomer(change.customer_id)}
          >
            <div>
              <strong>{change.customer_name}</strong>
              <div className="muted small">
                {change.plan_name} · {change.contract_id}
              </div>
            </div>
            <div className="right-align">
              <div className="mono">{fmtMoney(change.mrr_rmb)}</div>
              <div className="muted small">到期 {change.effective_date}</div>
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}

function RefundCard({ refunds, total }) {
  return (
    <section className="card refund-card">
      <div className="card-header">
        <div>
          <div className="eyebrow">Cash metric</div>
          <h2>退款 · 现金指标</h2>
          <p className="card-subtitle">退款计入现金，不修改合同 MRR。</p>
        </div>
        <div className="refund-total">{fmtMoney(total)}</div>
      </div>
      {refunds.length ? (
        <div className="compact-list">
          {refunds.map((refund) => (
            <div className="compact-row static" key={refund.event_id}>
              <div>
                <strong>{refund.customer_name}</strong>
                <div className="muted small">
                  {refund.contract_id} · {refund.event_date}
                </div>
                <div className="muted small">{refund.note}</div>
              </div>
              <div className="right-align mono">{fmtMoney(refund.amount_rmb)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-note">本月无退款。</div>
      )}
    </section>
  )
}

function ReconciliationStrip({ bridge }) {
  const components = bridge.components.filter((component) => component.count > 0)
  const rounding = bridge.reconciliation.rounding_adjustment_rmb
  return (
    <div className="recon-strip" aria-label="桥接闭合校验">
      <div className="recon-equation">
        <span className="recon-item total">
          <span>期初</span>
          <b>{fmtMoney(bridge.beginning_mrr_rmb)}</b>
        </span>
        {components.map((component) => (
          <span className="recon-item" key={component.key}>
            <span>{component.amount_rmb >= 0 ? '+' : '−'} {component.label}</span>
            <b className={component.amount_rmb >= 0 ? 'is-positive' : 'is-negative'}>
              {fmtMoney(Math.abs(component.amount_rmb))}
            </b>
          </span>
        ))}
        {rounding !== 0 ? (
          <span className="recon-item">
            <span>{rounding > 0 ? '+' : '−'} 舍入尾差</span>
            <b>{fmtMoney(Math.abs(rounding))}</b>
          </span>
        ) : null}
        <span className="recon-equals">=</span>
        <span className="recon-item total">
          <span>期末</span>
          <b>{fmtMoney(bridge.ending_mrr_rmb)}</b>
        </span>
      </div>
      <div className={`recon-check ${rounding !== 0 ? 'has-rounding' : ''}`}>
        <span className="check-dot" />
        {rounding !== 0
          ? `显示金额尾差 ${fmtMoney(rounding, { sign: true })} 已单列`
          : '桥接精确闭合'}
      </div>
      <p className="recon-note">{bridge.reconciliation.note}</p>
    </div>
  )
}

function ScenarioStrip({ scenarios, activeMonth, onSelect }) {
  return (
    <section className="scenario-strip" aria-label="示例场景">
      <div className="scenario-label">示例场景</div>
      <div className="scenario-scroll">
        {scenarios.map((scenario) => (
          <button
            key={scenario.id}
            className={`scenario-card ${scenario.month === activeMonth ? 'active' : ''}`}
            onClick={() => onSelect(scenario)}
          >
            <span className="scenario-tag">{scenario.tag}</span>
            <strong>{scenario.title}</strong>
            <span className="scenario-desc">{scenario.description}</span>
            <span className="scenario-month mono">{scenario.month}</span>
          </button>
        ))}
      </div>
    </section>
  )
}

function Definitions({ definitions }) {
  return (
    <section className="card definitions-card">
      <details>
        <summary>
          <span>口径说明</span>
          <span className="muted small">MRR / 桥接 / 留存 / 退款</span>
        </summary>
        <div className="def-grid">
          {Object.entries(definitions).map(([key, value]) => (
            <div className="def-item" key={key}>
              <span className="def-key mono">{key}</span>
              <p>{value}</p>
            </div>
          ))}
        </div>
      </details>
    </section>
  )
}

export default function App() {
  const [meta, setMeta] = useState(null)
  const [retention, setRetention] = useState(null)
  const [month, setMonth] = useState(null)
  const [bridge, setBridge] = useState(null)
  const [filter, setFilter] = useState('all')
  const [drawer, setDrawer] = useState(null)
  const [dark, setDark] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : false,
  )
  const [initialError, setInitialError] = useState(null)
  const [bridgeError, setBridgeError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const theme = getChartTheme(dark)

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  }, [dark])

  useEffect(() => {
    let mounted = true
    Promise.all([api.meta(), api.retention()])
      .then(([metaData, retentionData]) => {
        if (!mounted) return
        setMeta(metaData)
        setRetention(retentionData)
        setMonth(metaData.last_completed_month)
      })
      .catch((error) => mounted && setInitialError(error.message))
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!month) return undefined
    let mounted = true
    setRefreshing(true)
    setBridgeError(null)
    api
      .bridge(month)
      .then((data) => {
        if (!mounted) return
        setBridge(data)
        setFilter('all')
      })
      .catch((error) => mounted && setBridgeError(error.message))
      .finally(() => mounted && setRefreshing(false))
    return () => {
      mounted = false
    }
  }, [month])

  const componentsByKey = useMemo(() => {
    const map = {}
    if (bridge) bridge.components.forEach((component) => (map[component.key] = component))
    return map
  }, [bridge])

  const newComponent = componentsByKey.new
  const churnComponent = componentsByKey.churn
  const pauseComponent = componentsByKey.pause

  const openCustomer = useCallback((customerId, customerMonth = month) => {
    setDrawer({ type: 'customer', customerId, month: customerMonth })
  }, [month])

  const openBucket = useCallback((category) => {
    setDrawer({ type: 'bucket', category })
  }, [])

  const selectMonth = (nextMonth) => {
    setMonth(nextMonth)
    setDrawer(null)
  }

  const handleScenario = (scenario) => {
    setMonth(scenario.month)
    setDrawer({
      type: 'customer',
      customerId: scenario.customer_id,
      month: scenario.month,
    })
  }

  if (initialError) {
    return (
      <div className="app-shell">
        <div className="fatal-error">
          <h1>无法加载数据</h1>
          <p>{initialError}</p>
          <p className="muted">请确认 FastAPI 后端已运行在 8000 端口。</p>
        </div>
      </div>
    )
  }

  if (!meta || !month) {
    return (
      <div className="app-shell">
        <div className="loading-screen">
          <div className="loading-mark">M</div>
          <p>正在从 DuckDB 合同事件还原 MRR…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-block">
          <div className="brand-mark">M</div>
          <div>
            <div className="eyebrow">Subscription revenue analytics</div>
            <h1>MRR 变动与首付月份留存</h1>
            <p className="brand-subtitle">合同事件 → 客户层 MRR → 月度桥接 → 首付月份留存</p>
          </div>
        </div>
        <div className="header-controls">
          <label className="month-control">
            <span>报告月份</span>
            <select value={month} onChange={(event) => selectMonth(event.target.value)}>
              {meta.months.map((key) => (
                <option key={key} value={key}>
                  {fmtMonth(key)}
                </option>
              ))}
            </select>
          </label>
          <button
            className="theme-toggle"
            aria-label={dark ? '切换到浅色模式' : '切换到深色模式'}
            onClick={() => setDark((value) => !value)}
          >
            {dark ? '☀' : '☾'}
          </button>
          <div className="as-of">
            <span>截至</span>
            <b className="mono">{meta.as_of}</b>
          </div>
        </div>
      </header>

      <ScenarioStrip scenarios={meta.scenarios} activeMonth={month} onSelect={handleScenario} />

      <main className="dashboard">
        {bridgeError ? (
          <div className="error-panel">
            <strong>加载 {month} 桥接失败：</strong> {bridgeError}
            <button className="text-button" onClick={() => selectMonth(month)}>重试</button>
          </div>
        ) : null}

        <div className={`content-stack ${refreshing ? 'refreshing' : ''}`}>
          {bridge ? (
            <>
              <section className="kpi-grid" aria-label="本月关键指标">
                <div className="kpi-card kpi-hero">
                  <span className="kpi-label">期末 MRR · {fmtMonth(month)}末</span>
                  <strong className="hero-value">{fmtMoney(bridge.ending_mrr_rmb)}</strong>
                  <div className="hero-meta">
                    <span className={deltaClass(bridge.net_change_rmb)}>
                      {fmtMoney(bridge.net_change_rmb, { sign: true })}
                    </span>
                    <span className="muted">
                      较上月末 {fmtSignedPct(bridge.net_change_pct)}
                    </span>
                  </div>
                  <div className="hero-foot">
                    期初 {fmtMoney(bridge.beginning_mrr_rmb)} · {meta.currency}
                  </div>
                </div>
                <KpiCard
                  label="净变化"
                  value={fmtMoney(bridge.net_change_rmb, { sign: true })}
                  meta={`较上月末 ${fmtSignedPct(bridge.net_change_pct)}`}
                  tone={deltaClass(bridge.net_change_rmb)}
                />
                <KpiCard
                  label="新增客户"
                  value={newComponent ? fmtMoney(newComponent.amount_rmb, { sign: true }) : '¥0.00'}
                  meta={newComponent ? `${newComponent.count} 个客户首次付费` : '本月无新增'}
                  tone="is-positive"
                />
                <KpiCard
                  label="流失客户"
                  value={churnComponent ? fmtMoney(churnComponent.amount_rmb, { sign: true }) : '¥0.00'}
                  meta={
                    churnComponent
                      ? `${churnComponent.count} 个客户 MRR 归零${pauseComponent?.count ? ` · 另有 ${pauseComponent.count} 个暂停` : ''}`
                      : '本月无流失'
                  }
                  tone="is-negative"
                />
                <KpiCard
                  label="退款（现金）"
                  value={fmtMoney(bridge.refund_total_rmb)}
                  meta={`${bridge.refunds.length} 笔 · 不改合同 MRR`}
                  tone="is-neutral"
                />
              </section>

              <div className="top-grid">
                <section className="card waterfall-card">
                  <div className="card-header">
                    <div>
                      <div className="eyebrow">MRR movement</div>
                      <h2>MRR 变动瀑布图</h2>
                      <p className="card-subtitle">
                        上月末 → 本月末；每个分项都加到期初，尾差单列。
                      </p>
                    </div>
                    <div className="period-pill">
                      <span>{bridge.period.previous_month}</span>
                      <span>→</span>
                      <span>{bridge.month}</span>
                    </div>
                  </div>
                  <WaterfallChart bridge={bridge} theme={theme} onSelectCategory={openBucket} />
                  <ReconciliationStrip bridge={bridge} />
                </section>

                <section className="card components-card">
                  <div className="card-header">
                    <div>
                      <div className="eyebrow">Bridge components</div>
                      <h2>桥接分项</h2>
                      <p className="card-subtitle">点击分项查看客户名单。</p>
                    </div>
                  </div>
                  <ComponentList bridge={bridge} onSelect={openBucket} />
                  <div className="bridge-equation-mini">
                    <span>期初</span>
                    <b className="mono">{fmtMoney(bridge.beginning_mrr_rmb)}</b>
                    <span>→</span>
                    <span>期末</span>
                    <b className="mono">{fmtMoney(bridge.ending_mrr_rmb)}</b>
                  </div>
                </section>
              </div>

              <JourneyTable
                bridge={bridge}
                filter={filter}
                onFilter={setFilter}
                onSelectCustomer={(customerId) => openCustomer(customerId, month)}
              />

              <div className="secondary-grid">
                <OffsetLedger groups={bridge.offset_ledger} onSelectCustomer={(id) => openCustomer(id, month)} />
                <PendingCard changes={bridge.pending_changes} onSelectCustomer={(id) => openCustomer(id, month)} />
                <RefundCard refunds={bridge.refunds} total={bridge.refund_total_rmb} />
              </div>

              <section className="card retention-card">
                <div className="card-header">
                  <div>
                    <div className="eyebrow">First-payment cohort retention</div>
                    <h2>首付月份留存表</h2>
                    <p className="card-subtitle">
                      行 = 首付月份；列 = 各月末；值为月末仍为正 MRR 的客户比例。未来月份留空。
                    </p>
                  </div>
                  <div className="retention-meta">
                    <span>{retention?.cohorts.length || 0} 个首付月份</span>
                    <span>未来月份 {retention?.future_months?.join('、') || '—'}</span>
                  </div>
                </div>
                {retention ? (
                  <RetentionTable
                    report={retention}
                    theme={theme}
                    onSelectCell={(cohort, cellMonth) =>
                      setDrawer({ type: 'retention', cohort, month: cellMonth })
                    }
                  />
                ) : null}
              </section>

              <Definitions definitions={meta.definitions} />
            </>
          ) : (
            <div className="loading-panel">{refreshing ? '正在计算月度桥接…' : '暂无数据'}</div>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <span>数据源：DuckDB 合同事件</span>
        <span>金额单位：人民币（CNY）</span>
        <span>计算 4 位小数 · 展示 2 位小数</span>
      </footer>

      {drawer?.type === 'customer' ? (
        <CustomerDrawer
          customerId={drawer.customerId}
          month={drawer.month}
          theme={theme}
          onClose={() => setDrawer(null)}
        />
      ) : null}
      {drawer?.type === 'bucket' && bridge ? (
        <BucketDrawer
          bridge={bridge}
          category={drawer.category}
          onClose={() => setDrawer(null)}
          onOpenCustomer={(customerId) => openCustomer(customerId, month)}
        />
      ) : null}
      {drawer?.type === 'retention' ? (
        <RetentionCellDrawer
          cohort={drawer.cohort}
          month={drawer.month}
          onClose={() => setDrawer(null)}
          onOpenCustomer={(customerId, customerMonth) => openCustomer(customerId, customerMonth)}
        />
      ) : null}
    </div>
  )
}
