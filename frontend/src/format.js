const moneyFormatter = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const integerFormatter = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 0,
})

export function fmtMoney(value, { sign = false, decimals = 2 } = {}) {
  const number = Number(value ?? 0)
  if (decimals === 0) {
    const text = integerFormatter.format(Math.abs(number))
    const prefix = sign ? (number > 0 ? '+' : number < 0 ? '-' : '') : number < 0 ? '-' : ''
    return `${prefix}¥${text}`
  }
  const text = moneyFormatter.format(Math.abs(number))
  const prefix = sign ? (number > 0 ? '+' : number < 0 ? '-' : '') : number < 0 ? '-' : ''
  return `${prefix}¥${text}`
}

export function fmtCompactMoney(value) {
  const number = Number(value ?? 0)
  const abs = Math.abs(number)
  const sign = number < 0 ? '-' : ''
  if (abs >= 10000) {
    const text = (abs / 10000).toFixed(abs >= 100000 ? 1 : 2).replace(/\.0+$/, '')
    return `${sign}¥${text}万`
  }
  if (abs >= 1000) {
    return `${sign}¥${integerFormatter.format(Math.round(abs))}`
  }
  return `${sign}¥${integerFormatter.format(Math.round(abs))}`
}

export function fmtPct(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  return `${Number(value).toFixed(digits)}%`
}

export function fmtSignedPct(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const number = Number(value)
  return `${number > 0 ? '+' : ''}${number.toFixed(digits)}%`
}

export function fmtMonth(key) {
  if (!key) return '—'
  const [year, month] = key.split('-')
  return `${year} 年 ${Number(month)} 月`
}

export function fmtMonthShort(key) {
  if (!key) return '—'
  return key
}

export function deltaClass(value) {
  const number = Number(value)
  if (number > 0) return 'is-positive'
  if (number < 0) return 'is-negative'
  return 'is-neutral'
}

export function statusLabel(status) {
  const labels = {
    active: '生效中',
    scheduled_cancel: '已预约取消',
    paused: '暂停中',
    ended: '已终止',
    trial: '试用中',
    not_started: '未开始',
    zero: '零 MRR',
  }
  return labels[status] || status
}

export function categoryIcon(key) {
  const icons = {
    new: '+',
    reactivation: '↺',
    resume: '▶',
    upgrade: '↑',
    downgrade: '↓',
    pause: 'Ⅱ',
    churn: '×',
    rounding: '≈',
    none: '·',
  }
  return icons[key] || '·'
}
