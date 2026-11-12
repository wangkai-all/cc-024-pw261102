import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

export default function EChart({ option, height = 340, className = '', onClick, ariaLabel }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return undefined
    const chart = echarts.init(containerRef.current, null, { renderer: 'canvas' })
    chartRef.current = chart
    const resize = () => chart.resize()
    const observer = new ResizeObserver(resize)
    observer.observe(containerRef.current)
    window.addEventListener('resize', resize)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', resize)
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!chartRef.current) return
    chartRef.current.setOption(option, true)
  }, [option])

  useEffect(() => {
    const chart = chartRef.current
    if (!chart) return undefined
    chart.off('click')
    if (onClick) chart.on('click', onClick)
    return () => chart.off('click')
  }, [onClick, option])

  return (
    <div
      ref={containerRef}
      className={`echart ${className}`}
      style={{ height }}
      role="img"
      aria-label={ariaLabel}
    />
  )
}
