export const SYSTEM_VARIABLE_OPTIONS = [
  { description: 'YYYYMMDD 格式，适合分区字段', label: '当前日期', value: '{{current_date}}' },
  { description: '当前日期前 7 天，适合近 7 天起始分区', label: '当前日期 - 7 天', value: '{{current_date-7}}' },
  { description: 'YYYY-MM-DD 格式，适合 API 日期参数', label: '当前日期 ISO', value: '{{date_iso}}' },
  { description: 'ISO 日期前 7 天', label: '当前日期 ISO - 7 天', value: '{{date_iso-7}}' },
  { description: '当前时间，带时区偏移', label: '当前时间', value: '{{now}}' },
  { description: '今天 00:00:00', label: '今天开始', value: '{{today.start}}' },
  { description: '今天 00:00:00 前 7 天', label: '今天开始 - 7 天', value: '{{today.start-7}}' },
  { description: '上一完整自然周周一 00:00:00', label: '上一完整周开始', value: '{{last_full_week.start}}' },
  { description: '本周一 00:00:00', label: '上一完整周结束', value: '{{last_full_week.end}}' },
];
