import Drawer from './Drawer'
import { categoryIcon, deltaClass, fmtMoney, fmtMonth } from '../format'

export default function BucketDrawer({ bridge, category, onClose, onOpenCustomer }) {
  const component = bridge.components.find((item) => item.key === category)
  const items = component?.items || []
  const sign = Number(component?.amount_rmb || 0) >= 0 ? 'positive' : 'negative'

  return (
    <Drawer
      eyebrow={`桥接分项 · ${fmtMonth(bridge.month)}`}
      title={component ? `${component.label} · ${component.count} 个客户` : '桥接分项'}
      subtitle={component ? `本月净额 ${fmtMoney(component.amount_rmb, { sign: true })}，点击客户查看月初/月末快照与合同事件` : ''}
      onClose={onClose}
    >
      {component ? (
        <>
          <div className={`bucket-hero bucket-${sign}`}>
            <span className="category-icon">{categoryIcon(component.key)}</span>
            <div>
              <div className="bucket-hero-label">{component.label}</div>
              <div className="bucket-hero-value">{fmtMoney(component.amount_rmb, { sign: true })}</div>
            </div>
            <div className="bucket-hero-count">{component.count} 个客户</div>
          </div>
          <div className="bucket-list">
            {items.map((item) => (
              <button
                className="bucket-row"
                key={item.customer_id}
                onClick={() => onOpenCustomer(item.customer_id)}
              >
                <div className="bucket-customer">
                  <strong>{item.customer_name}</strong>
                  <span className="muted small">
                    {item.city} · {item.segment}
                  </span>
                  <span className="bucket-reason">{item.reason}</span>
                </div>
                <div className="bucket-mrr">
                  <span className="mono muted">
                    {fmtMoney(item.mrr_before_rmb)} → {fmtMoney(item.mrr_after_rmb)}
                  </span>
                  <span className={`mono ${deltaClass(item.delta_rmb)}`}>
                    {fmtMoney(item.delta_rmb, { sign: true })}
                  </span>
                </div>
                <div className="bucket-events">
                  {item.event_count} 个事件
                  <span className="row-arrow">›</span>
                </div>
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="muted">该分项没有客户明细。</div>
      )}
    </Drawer>
  )
}
