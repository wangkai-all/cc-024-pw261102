import { useMemo } from 'react'
import EChart from './EChart'
import { fmtMonth, fmtPct } from '../format'
import { heatColor, inkForHeat } from '../theme'

export default function RetentionTable({ report, theme, onSelectCell }) {
  const height = Math.max(320, report.cohorts.length * 30 + 100)

  const option = useMemo(() => {
    const months = report.months
    const cohorts = report.cohorts
    const data = []
    cohorts.forEach((cohort, y) => {
      cohort.cells.forEach((cell, x) => {
        const statusCode = cell.status === 'ok' ? 1 : cell.status === 'before' ? 2 : 3
        data.push({
          value: [
            x,
            y,
            cell.rate_pct ?? -1,
            cell.active_count ?? -1,
            cell.cohort_size,
            statusCode,
          ],
          cell,
          cohort: cohort.cohort,
        })
      })
    })

    const renderItem = (params, api) => {
      const x = api.coord([api.value(0), api.value(1)])
      const size = api.size([1, 1])
      const gap = 2
      const width = Math.max(1, size[0] - gap)
      const cellHeight = Math.max(1, size[1] - gap)
      const statusCode = api.value(5)
      const rate = api.value(2)
      const cell = params.data?.cell

      let fill = theme.emptyFuture
      let label = ''
      let ink = theme.muted
      if (statusCode === 1) {
        const heat = heatColor(theme, rate)
        fill = heat.color
        ink = inkForHeat(theme, heat.index, heat.last)
        label = `${Number(rate).toFixed(Number(rate) % 1 === 0 ? 0 : 1)}%`
      } else if (statusCode === 2) {
        fill = theme.emptyBefore
        label = '—'
      }

      return {
        type: 'group',
        children: [
          {
            type: 'rect',
            shape: {
              x: x[0] - width / 2 + gap / 2,
              y: x[1] - cellHeight / 2 + gap / 2,
              width,
              height: cellHeight,
              r: 2,
            },
            style: { fill },
          },
          ...(label
            ? [
                {
                  type: 'text',
                  style: {
                    x: x[0],
                    y: x[1],
                    text: label,
                    fill: ink,
                    font: '11px system-ui, -apple-system, "Segoe UI", sans-serif',
                    fontSize: 11,
                    align: 'center',
                    verticalAlign: 'middle',
                    textAlign: 'center',
                    textVerticalAlign: 'middle',
                  },
                },
              ]
            : []),
        ],
      }
    }

    return {
      backgroundColor: 'transparent',
      animationDuration: 500,
      aria: { enabled: true },
      grid: { left: 92, right: 20, top: 16, bottom: 72 },
      tooltip: {
        trigger: 'item',
        confine: true,
        backgroundColor: theme.tooltipBg,
        borderColor: theme.tooltipBorder,
        borderWidth: 1,
        padding: [9, 11],
        textStyle: { color: theme.text, fontSize: 12 },
        formatter: (params) => {
          const item = params.data
          if (!item) return ''
          const cell = item.cell
          if (cell.status === 'before') {
            return `<b>${item.cohort}</b><br/>${cell.month}<br/><span style="color:${theme.muted}">首付月份之前，不适用</span>`
          }
          if (cell.status === 'future') {
            return `<b>${item.cohort}</b><br/>${cell.month}<br/><span style="color:${theme.muted}">月份尚未结束，留空</span>`
          }
          return `
            <div style="font-weight:600;margin-bottom:3px">${item.cohort} 首付 · ${fmtMonth(cell.month)}末</div>
            <div style="font-size:16px;font-variant-numeric:tabular-nums;margin-bottom:2px">${fmtPct(cell.rate_pct, 2)}</div>
            <div style="color:${theme.muted};font-size:11px">${cell.active_count} / ${cell.cohort_size} 客户仍为正 MRR</div>
            <div style="color:${theme.muted};font-size:11px;margin-top:2px">点击查看客户名单</div>
          `
        },
      },
      xAxis: {
        type: 'category',
        data: months,
        axisLine: { lineStyle: { color: theme.axis } },
        axisTick: { show: false },
        axisLabel: {
          color: theme.secondary,
          fontSize: 10,
          interval: 0,
          rotate: 38,
          margin: 12,
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'category',
        data: cohorts.map((cohort) => cohort.cohort),
        axisLine: { lineStyle: { color: theme.axis } },
        axisTick: { show: false },
        axisLabel: { color: theme.secondary, fontSize: 11, margin: 12 },
        splitLine: { show: false },
      },
      series: [
        {
          type: 'custom',
          renderItem,
          encode: { x: 0, y: 1 },
          data,
          clip: false,
          silent: false,
          hoverAnimation: false,
        },
      ],
    }
  }, [report, theme])

  const handleClick = (params) => {
    const cell = params.data?.cell
    if (!cell || cell.status !== 'ok') return
    onSelectCell(params.data.cohort, cell.month)
  }

  return (
    <div className="retention-block">
      <div className="chart-legend retention-legend" aria-label="留存率色阶">
        <span className="legend-item">
          <span className="legend-gradient" style={{ background: `linear-gradient(90deg, ${theme.heatRamp.join(', ')})` }} />
        </span>
        <span className="legend-scale">0%</span>
        <span className="legend-scale">100%</span>
        <span className="legend-hint">单元格 = 该月末正 MRR 客户占比；点击查看名单</span>
      </div>
      <EChart
        option={option}
        height={height}
        onClick={handleClick}
        ariaLabel="首付月份留存表，行是首付月份，列是月末，单元格为仍为正 MRR 的客户比例"
      />
      <p className="chart-note">{report.note}</p>
    </div>
  )
}
