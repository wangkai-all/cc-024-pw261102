import { useEffect } from 'react'

export default function Drawer({ title, subtitle, onClose, children, eyebrow = '明细' }) {
  useEffect(() => {
    const handleKey = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    document.body.classList.add('drawer-open')
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.classList.remove('drawer-open')
    }
  }, [onClose])

  return (
    <div className="drawer-layer">
      <button className="drawer-backdrop" aria-label="关闭明细" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={title}>
        <div className="drawer-header">
          <div>
            <div className="drawer-eyebrow">{eyebrow}</div>
            <h2>{title}</h2>
            {subtitle ? <p className="drawer-subtitle">{subtitle}</p> : null}
          </div>
          <button className="icon-button" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  )
}
