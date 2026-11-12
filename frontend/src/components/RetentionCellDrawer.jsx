import { useEffect, useState } from 'react'
import Drawer from './Drawer'
import { api } from '../api'
import { fmtMoney, fmtMonth, fmtPct } from '../format'

export default function RetentionCellDrawer({ cohort, month, onClose, onOpenCustomer }) {
  const [state, setState] = useState({ loading: true, error: null, data: null })

  useEffect(() => {
    let mounted = true
    setState({ loading: true, error: null, data: null })
    api
      .retentionCell(cohort, month)
      .then((data) => mounted && setState({ loading: false, error: null, data }))
      .catch((error) => mounted && setState({ loading: false, error: error.message, data: null }))
    return () => {
      mounted = false
    }
  }, [cohort, month])

  const data = state.data

  return (
    <Drawer
      eyebrow="留存单元格"
      title={`${cohort} 首付 · ${fmtMonth(month)}末`}
      subtitle="按客户层 MRR 是否为正判断留存；点击客户查看当月快照"
      onClose={onClose}
    >
      {state.loading ? <div className="loading-panel">正在读取留存名单…</div> : null}
      {state.error ? <div className="error-panel">{state.error}</div> : null}
      {data ? (
        <>
          <div className="retention-hero">
            <div>
              <span>留存率</span>
              <strong>{fmtPct(data.rate_pct, 2)}</strong>
            </div>
            <div>
              <span>活跃 / 首付客户</span>
              <strong>
                {data.active_count} / {data.cohort_size}
              </strong>
            </div>
            <div>
              <span>月末</span>
              <strong className="mono">{data.month_end}</strong>
            </div>
          </div>

          <section className="detail-section">
            <div className="section-header">
              <h3>为正 MRR 的客户</h3>
              <span className="muted">{data.active_customers.length} 个</span>
            </div>
            <div className="bucket-list">
              {data.active_customers.map((customer) => (
                <button
                  className="bucket-row retention-row"
                  key={customer.customer_id}
                  onClick={() => onOpenCustomer(customer.customer_id, month)}
                >
                  <div className="bucket-customer">
                    <strong>{customer.customer_name}</strong>
                    <span className="muted small">
                      {customer.city} · {customer.segment}
                    </span>
                  </div>
                  <div className="mono">{fmtMoney(customer.mrr_rmb)}</div>
                  <div className="bucket-events">
                    <span className="row-arrow">›</span>
                  </div>
                </button>
              ))}
              {!data.active_customers.length ? <div className="muted empty-note">无活跃客户</div> : null}
            </div>
          </section>

          <section className="detail-section">
            <div className="section-header">
              <h3>月末 MRR 为零的客户</h3>
              <span className="muted">{data.inactive_customers.length} 个</span>
            </div>
            <div className="bucket-list">
              {data.inactive_customers.map((customer) => (
                <button
                  className="bucket-row retention-row"
                  key={customer.customer_id}
                  onClick={() => onOpenCustomer(customer.customer_id, month)}
                >
                  <div className="bucket-customer">
                    <strong>{customer.customer_name}</strong>
                    <span className="muted small">
                      {customer.city} · {customer.segment}
                    </span>
                  </div>
                  <div className="mono muted">{fmtMoney(customer.mrr_rmb)}</div>
                  <div className="bucket-events">
                    <span className="row-arrow">›</span>
                  </div>
                </button>
              ))}
              {!data.inactive_customers.length ? <div className="muted empty-note">无零 MRR 客户</div> : null}
            </div>
          </section>
          <p className="chart-note">{data.note}</p>
        </>
      ) : null}
    </Drawer>
  )
}
