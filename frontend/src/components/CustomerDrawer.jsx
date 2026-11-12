import { useEffect, useMemo, useState } from 'react'
import Drawer from './Drawer'
import EChart from './EChart'
import { api } from '../api'
import {
  categoryIcon,
  deltaClass,
  fmtMoney,
  fmtMonth,
  fmtPct,
  statusLabel,
} from '../format'

function cycleLabel(cycle) {
  if (cycle === 'annual') return '年付'
  if (cycle === 'monthly') return '月付'
  return '—'
}

function SnapshotCard({ title, date, snapshot, theme }) {
  if (!snapshot) return null
  return (
    <div className="snapshot-card">
      <div className="snapshot-head">
        <span>{title}</span>
        <span className="mono muted">{date}</span>
      </div>
      <div className="snapshot-mrr">{fmtMoney(snapshot.mrr_rmb)}</div>
      <div className="snapshot-contracts">
        {snapshot.contracts.map((contract) => (
          <span className={`mini-contract ${contract.status}`} key={contract.contract_id}>
            <strong>{contract.plan_name}</strong>
            <span>{fmtMoney(contract.mrr_rmb)}</span>
            <span className="mini-status">{statusLabel(contract.status)}</span>
          </span>
        ))}
        {!snapshot.contracts.length ? <span className="muted">无合同</span> : null}
      </div>
    </div>
  )
}

export default function CustomerDrawer({ customerId, month, theme, onClose }) {
  const [state, setState] = useState({ loading: true, error: null, data: null })

  useEffect(() => {
    let mounted = true
    setState({ loading: true, error: null, data: null })
    api
      .customerDetail(customerId, month)
      .then((data) => mounted && setState({ loading: false, error: null, data }))
      .catch((error) => mounted && setState({ loading: false, error: error.message, data: null }))
    return () => {
      mounted = false
    }
  }, [customerId, month])

  const trendOption = useMemo(() => {
    const trend = state.data?.trend || []
    if (!trend.length) return null
    const last = trend[trend.length - 1]
    return {
      backgroundColor: 'transparent',
      animationDuration: 450,
      aria: { enabled: true },
      grid: { left: 56, right: 18, top: 18, bottom: 34 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: theme.tooltipBg,
        borderColor: theme.tooltipBorder,
        borderWidth: 1,
        textStyle: { color: theme.text, fontSize: 12 },
        formatter: (params) => {
          const point = params[0]
          return `${point.axisValue}<br/><b>${fmtMoney(point.value)}</b>`
        },
      },
      xAxis: {
        type: 'category',
        data: trend.map((point) => point.month),
        boundaryGap: false,
        axisLine: { lineStyle: { color: theme.axis } },
        axisTick: { show: false },
        axisLabel: { color: theme.muted, fontSize: 10, interval: 'auto' },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: theme.grid } },
        axisLabel: {
          color: theme.muted,
          fontSize: 10,
          formatter: (value) => (value >= 1000 ? `${(value / 10000).toFixed(1)}万` : value),
        },
      },
      series: [
        {
          type: 'line',
          data: trend.map((point) => point.mrr_rmb),
          smooth: false,
          showSymbol: false,
          lineStyle: { width: 2, color: theme.positive },
          areaStyle: { color: theme.positive, opacity: 0.1 },
          markPoint: {
            symbol: 'circle',
            symbolSize: 10,
            itemStyle: { color: theme.positive, borderColor: theme.surface, borderWidth: 2 },
            label: { show: false },
            data: [{ coord: [last.month, last.mrr_rmb] }],
          },
        },
      ],
    }
  }, [state.data, theme])

  const data = state.data
  const title = data ? data.customer.name : customerId

  return (
    <Drawer
      eyebrow={`客户明细 · ${month}`}
      title={title}
      subtitle={
        data
          ? `${data.customer.city} · ${data.customer.segment} · 首付月份 ${data.customer.cohort_month || '—'}`
          : '从合同事件还原的客户层月度快照'
      }
      onClose={onClose}
    >
      {state.loading ? <div className="loading-panel">正在还原客户快照…</div> : null}
      {state.error ? <div className="error-panel">{state.error}</div> : null}
      {data ? (
        <>
          <div className="detail-kpis">
            <div className="detail-kpi">
              <span>月初 MRR</span>
              <strong>{fmtMoney(data.mrr_before_rmb)}</strong>
            </div>
            <div className="detail-kpi-arrow">→</div>
            <div className="detail-kpi">
              <span>月末 MRR</span>
              <strong>{fmtMoney(data.mrr_after_rmb)}</strong>
            </div>
            <div className={`detail-kpi delta ${deltaClass(data.delta_rmb)}`}>
              <span>本月变化</span>
              <strong>{fmtMoney(data.delta_rmb, { sign: true })}</strong>
            </div>
          </div>

          <div className="detail-meta-row">
            <span className={`category-badge category-${data.category}`}>
              <span className="category-icon">{categoryIcon(data.category)}</span>
              {data.category_label}
            </span>
            <span className="muted">{data.reason}</span>
            {data.category === 'none' && data.pending_changes.length ? (
              <span className="pending-pill">有待生效变更</span>
            ) : null}
          </div>

          <div className="snapshot-grid">
            <SnapshotCard
              title="月初快照"
              date={data.period.previous_month_end}
              snapshot={data.snapshot_before}
              theme={theme}
            />
            <SnapshotCard
              title="月末快照"
              date={data.period.month_end}
              snapshot={data.snapshot_after}
              theme={theme}
            />
          </div>

          {data.pending_changes.map((change) => (
            <div className="notice-card notice-pending" key={`${change.contract_id}-${change.effective_date}`}>
              <div className="notice-title">待生效 · 预约取消</div>
              <div>
                {change.plan_name}（{change.contract_id}）将于 <b>{change.effective_date}</b> 到期停止计费；
                当前 MRR {fmtMoney(change.mrr_rmb)}，到期前仍计入。
              </div>
              <div className="notice-note">{change.note}</div>
            </div>
          ))}

          {data.refunds.map((refund) => (
            <div className="notice-card notice-refund" key={refund.event_id}>
              <div className="notice-title">现金指标 · 退款</div>
              <div>
                {refund.event_date} 退款 <b>{fmtMoney(refund.amount_rmb)}</b>。
                退款不改合同 MRR，客户当月 MRR 仍为 {fmtMoney(data.mrr_after_rmb)}。
              </div>
              <div className="notice-note">{refund.note}</div>
            </div>
          ))}

          <section className="detail-section">
            <div className="section-header">
              <h3>合同层快照</h3>
              <span className="muted">先把多份合同加总到客户层，再看桥接类别</span>
            </div>
            <div className="table-scroll">
              <table className="data-table compact-table">
                <thead>
                  <tr>
                    <th>合同 / 方案</th>
                    <th>周期 / 金额</th>
                    <th>月初 MRR</th>
                    <th>月末 MRR</th>
                    <th>变化</th>
                  </tr>
                </thead>
                <tbody>
                  {data.contracts.map((contract) => {
                    const before = contract.before
                    const after = contract.after
                    const delta = Number(after?.mrr_rmb ?? 0) - Number(before?.mrr_rmb ?? 0)
                    return (
                      <tr key={contract.contract_id}>
                        <td>
                          <strong>{contract.plan_name}</strong>
                          <div className="mono muted">{contract.contract_id}</div>
                          <div className="muted small">签约 {contract.signed_date}</div>
                        </td>
                        <td>
                          <div>{cycleLabel(contract.billing_cycle)}</div>
                          <div className="mono muted">{fmtMoney(contract.amount_rmb)} / 周期</div>
                        </td>
                        <td>
                          <div className="mono">{fmtMoney(before?.mrr_rmb ?? 0)}</div>
                          {before ? (
                            <span className={`status-chip status-${before.status}`}>
                              {statusLabel(before.status)}
                            </span>
                          ) : (
                            <span className="muted">—</span>
                          )}
                          {before?.scheduled_effective_date ? (
                            <div className="muted small">到期 {before.scheduled_effective_date}</div>
                          ) : null}
                        </td>
                        <td>
                          <div className="mono">{fmtMoney(after?.mrr_rmb ?? 0)}</div>
                          {after ? (
                            <span className={`status-chip status-${after.status}`}>
                              {statusLabel(after.status)}
                            </span>
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                        <td className={deltaClass(delta)}>
                          <span className="mono">{fmtMoney(delta, { sign: true })}</span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="detail-section">
            <div className="section-header">
              <h3>合同事件</h3>
              <span className="muted">事件日期 / 生效日期 / 客户层 MRR 前后</span>
            </div>
            <div className="event-timeline">
              {data.events.length ? (
                data.events.map((event) => (
                  <div className="event-row" key={event.event_id}>
                    <div className="event-date">
                      <div className="mono">{event.event_date}</div>
                      {event.effective_date !== event.event_date ? (
                        <div className="muted small">生效 {event.effective_date}</div>
                      ) : (
                        <div className="muted small">即时生效</div>
                      )}
                    </div>
                    <div className="event-main">
                      <div>
                        <span className="event-type">{event.event_type_label}</span>
                        <span className="muted small">
                          {' '}· {event.plan_name} / {event.contract_id}
                        </span>
                      </div>
                      {event.note ? <div className="event-note">{event.note}</div> : null}
                      <div className="event-tags">
                        {event.treatment ? <span className="tag">{event.treatment}</span> : null}
                        {event.effect_label ? <span className="tag">{event.effect_label}</span> : null}
                      </div>
                    </div>
                    <div className="event-mrr">
                      {event.event_type === 'refund' ? (
                        <div className="mono">{fmtMoney(event.amount_rmb)}</div>
                      ) : (
                        <>
                          <div className="mono muted">
                            {fmtMoney(event.before_mrr_rmb)} → {fmtMoney(event.after_mrr_rmb)}
                          </div>
                          <div className={`mono ${deltaClass(event.delta_rmb)}`}>
                            {fmtMoney(event.delta_rmb, { sign: true })}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="muted empty-note">本月没有记录到该客户的合同事件。</div>
              )}
            </div>
          </section>

          {trendOption ? (
            <section className="detail-section">
              <div className="section-header">
                <h3>近 12 个月客户 MRR</h3>
                <span className="muted">截至 {fmtMonth(month)}</span>
              </div>
              <EChart option={trendOption} height={190} ariaLabel={`${title} 近 12 个月 MRR 趋势`} />
            </section>
          ) : null}
        </>
      ) : null}
    </Drawer>
  )
}
