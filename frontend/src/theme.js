export const chartThemes = {
  light: {
    mode: 'light',
    surface: '#fcfcfb',
    page: '#f9f9f7',
    text: '#0b0b0b',
    secondary: '#52514e',
    muted: '#898781',
    grid: '#e1e0d9',
    axis: '#c3c2b7',
    border: 'rgba(11,11,11,0.10)',
    positive: '#2a78d6',
    negative: '#d03b3b',
    total: '#184f95',
    rounding: '#898781',
    tooltipBg: '#ffffff',
    tooltipBorder: '#e1e0d9',
    softPositive: 'rgba(42,120,214,0.12)',
    softNegative: 'rgba(208,59,59,0.12)',
    heatRamp: [
      '#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec',
      '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab',
      '#184f95', '#104281', '#0d366b',
    ],
    heatInk: '#0b0b0b',
    heatInkOnDark: '#ffffff',
    emptyBefore: '#f0efec',
    emptyFuture: 'rgba(252,252,251,0)',
  },
  dark: {
    mode: 'dark',
    surface: '#1a1a19',
    page: '#0d0d0d',
    text: '#f0efec',
    secondary: '#c3c2b7',
    muted: '#898781',
    grid: '#2c2c2a',
    axis: '#383835',
    border: 'rgba(255,255,255,0.10)',
    positive: '#3987e5',
    negative: '#e66767',
    total: '#86b6ef',
    rounding: '#898781',
    tooltipBg: '#232322',
    tooltipBorder: '#383835',
    softPositive: 'rgba(57,135,229,0.18)',
    softNegative: 'rgba(230,103,103,0.18)',
    heatRamp: [
      '#184f95', '#1c5cab', '#256abf', '#2a78d6', '#3987e5',
      '#5598e7', '#6da7ec', '#86b6ef', '#9ec5f4', '#b7d3f6',
      '#cde2fb',
    ],
    heatInk: '#ffffff',
    heatInkOnDark: '#0b0b0b',
    emptyBefore: '#2c2c2a',
    emptyFuture: 'rgba(26,26,25,0)',
  },
}

export function getChartTheme(dark) {
  return dark ? chartThemes.dark : chartThemes.light
}

export function heatColor(theme, ratePct) {
  if (ratePct == null || Number.isNaN(ratePct)) return null
  const clamped = Math.max(0, Math.min(100, Number(ratePct)))
  const ramp = theme.heatRamp
  const index = Math.min(ramp.length - 1, Math.floor((clamped / 100) * (ramp.length - 1) + 0.0001))
  return { color: ramp[index], index, last: ramp.length - 1 }
}

export function inkForHeat(theme, index, last) {
  // Dark steps need white ink; light steps need near-black ink.
  if (theme.mode === 'dark') {
    return index <= last * 0.55 ? theme.heatInk : theme.heatInkOnDark
  }
  return index >= last * 0.52 ? theme.heatInkOnDark : theme.heatInk
}
