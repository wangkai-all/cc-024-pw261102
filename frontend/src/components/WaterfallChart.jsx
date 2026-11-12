import { useMemo } from 'react'
import EChart from './EChart'
import { fmtCompactMoney, fmtMoney, fmtMonth } from '../format'

function signedCompact(value) {
  if (value > 0) return `+${fmtCompactMoney(value)}`
  if (value < 0) return fmtCompactMoney(value)
  return fmtCompactMoney(0)
}

export default function WaterfallChart({ bridge, theme, onSelectCategory }) {
  const option = useMemo(() => {
    const steps = bridge.waterfall
    const begin = bridge.beginning_mrr_rmb
    let running = begin

    const placeholders = []
    const bars = []
    const tooltipByIndex = []

    steps.forEach((step, index) => {
      const value = Number(step.value_rmb)
      if (step.key === 'beginning' || step.key === 'ending') {
        placeholders.push({ value: 0, itemStyle: { color: 'transparent' } })
        bars.push({
          value,
          itemStyle: { color: theme.total, borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', color: theme.secondary },
        })
        tooltipByIndex.push(
          step.key === 'beginning'
            ? { title: '期初 MRR', detail: `${fmtMonth(bridge.period.previous_month)}末` }
            : { title: '期末 MRR', detail: `${fmtMonth(bridge.month)}末` },
        )
        running = value
        return
      }

      let base
      let height
      if (value >= 0) {
        base = running
        height = value
        running += value
      } else {
        base = running + value
        height = -value
        running += value
      }
      const color =
        step.key === 'rounding'
          ? theme.rounding
          : value >= 0
            ? theme.positive
            : theme.negative
      placeholders.push({ value: base, itemStyle: { color: 'transparent' } })
      bars.push({
        value: height,
        itemStyle: { color, borderRadius: value >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4] },
        label: {
          show: true,
          position: value >= 0 ? 'top' : 'bottom',
          color: theme.secondary,
          distance: 4,
        },
      })
      tooltipByIndex.push({
        title: `${step.label}${step.count != null ? ` · ${step.count} 个客户` : ''}`,
        detail: `净额 ${fmtMoney(value, { sign: true })} · 累计 ${fmtMoney(running)}`,
      })
    })

    return {
      backgroundColor: 'transparent',
      animationDuration: 650,
      animationEasing: 'cubicOut',
      aria: { enabled: true, decal: { show: false } },
      grid: { left: 68, right: 24, top: 38, bottom: 70, containLabel: false },
      tooltip: {
        trigger: 'item',
        confine: true,
        backgroundColor: theme.tooltipBg,
        borderColor: theme.tooltipBorder,
        borderWidth: 1,
        padding: [10, 12],
        textStyle: { color: theme.text, fontSize: 12 },
        formatter: (params) => {
          const step = steps[params.dataIndex]
          const info = tooltipByIndex[params.dataIndex]
          if (!step || !info) return ''
          const valueText = fmtMoney(step.value_rmb, {
            sign: step.key !== 'beginning' && step.key !== 'ending',
          })
          return `
            <div style="font-weight:600;margin-bottom:4px">${info.title}</div>
            <div style="font-variant-numeric:tabular-nums;font-size:15px;margin-bottom:2px">${valueText}</div>
            <div style="color:${theme.muted};font-size:11px">${info.detail}</div>
            ${step.count ? `<div style="color:${theme.muted};font-size:11px;margin-top:2px">点击查看客户明细</div>` : ''}
          `
        },
      },
      xAxis: {
        type: 'category',
        data: steps.map((step) => step.label),
        axisLine: { lineStyle: { color: theme.axis } },
        axisTick: { show: false },
        axisLabel: {
          color: theme.secondary,
          fontSize: 11,
          interval: 0,
          rotate: steps.length > 7 ? 24 : 0,
          margin: 14,
        },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: theme.grid, width: 1 } },
        axisLabel: {
          color: theme.muted,
          fontSize: 11,
          formatter: (value) => fmtCompactMoney(value),
        },
      },
      series: [
        {
          name: 'placeholder',
          type: 'bar',
          stack: 'waterfall',
          silent: true,
          barMaxWidth: 24,
          barCategoryGap: '38%',
          itemStyle: { color: 'transparent' },
          emphasis: { itemStyle: { color: 'transparent' } },
          data: placeholders,
        },
        {
          name: 'MRR 变动',
          type: 'bar',
          stack: 'waterfall',
          barMaxWidth: 24,
          barCategoryGap: '38%',
          label: {
            show: true,
            fontSize: 10,
            formatter: (params) => {
              const step = steps[params.dataIndex]
              if (!step) return ''
              if (step.key === 'beginning' || step.key === 'ending') {
                return fmtCompactMoney(step.value_rmb)
              }
              return signedCompact(step.value_rmb)
            },
          },
          data: bars,
        },
      ],
    }
  }, [bridge, theme])

  const handleClick = (params) => {
    const step = bridge.waterfall[params.dataIndex]
    if (!step || !step.category || step.category === 'rounding' || !step.count) return
    onSelectCategory(step.category)
  }

  const legend = [
    { label: '增加 MRR', color: theme.positive },
    { label: '减少 MRR', color: theme.negative },
    { label: '期初 / 期末', color: theme.total },
  ]
  if (bridge.reconciliation.rounding_adjustment_rmb !== 0) {
    legend.push({ label: '舍入尾差', color: theme.rounding })
  }

  return (
    <div className="chart-block">
      <div className="chart-legend" aria-label="瀑布图图例">
        {legend.map((entry) => (
          <span key={entry.label} className="legend-item">
            <span className="legend-swatch" style={{ background: entry.color }} />
            {entry.label}
          </span>
        ))}
        <span className="legend-hint">悬停查看数值 · 点击分项查看客户</span>
      </div>
      <EChart
        option={option}
        height={380}
        onClick={handleClick}
        ariaLabel={`${bridge.month} MRR 变动瀑布图：期初 ${fmtMoney(bridge.beginning_mrr_rmb)}，期末 ${fmtMoney(bridge.ending_mrr_rmb)}`}
      />
    </div>
  )
}
