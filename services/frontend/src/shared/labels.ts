// Translate display values only; API requests keep their original codes.
const betTypes = new Map<string, string>([
  ["tansho", "単勝"],
  ["fukusho", "複勝"],
  ["wakuren", "枠連"],
  ["wakutan", "枠単"],
  ["umaren", "馬連"],
  ["umatan", "馬単"],
  ["wide", "ワイド"],
  ["sanrenpuku", "三連複"],
  ["sanrentan", "三連単"],
]);

const snapshotKinds = new Map<string, string>([
  ["final", "発走直前"],
  ["t_minus_60m", "発走60分前"],
  ["t_minus_30m", "発走30分前"],
  ["t_minus_5m", "発走5分前"],
  ["t_minus_1m", "発走1分前"],
]);

const statuses = new Map<string, string>([
  ["ok", "正常"],
  ["unknown", "不明"],
  ["scheduled", "開催予定"],
  ["closed", "終了"],
  ["finished", "終了"],
  ["cancelled", "中止"],
  ["canceled", "中止"],
  ["accepted", "受付済み"],
  ["idle", "待機中"],
  ["pending", "待機中"],
  ["running", "実行中"],
  ["success", "成功"],
  ["failed", "失敗"],
  ["skipped", "スキップ"],
]);

const scrapeTargets = new Map<string, string>([
  ["deba_table", "出走表"],
  ["odds", "オッズ"],
  ["race_mark", "競走成績"],
  ["refund", "払戻金"],
  ["TodayRaceInfoTop", "本日の開催情報"],
  ["RaceList", "レース一覧"],
  ["DebaTable", "出走表"],
  ["RaceMarkTable", "競走成績"],
  ["RefundMoneyList", "払戻金"],
  ["OddsTanFuku", "単勝・複勝オッズ"],
  ["OddsWakuLenFukuTan", "枠連・枠単オッズ"],
  ["OddsUmLenFuku", "馬連オッズ"],
  ["OddsUmLenTan", "馬単オッズ"],
  ["OddsWide", "ワイドオッズ"],
  ["Odds3LenFuku", "三連複オッズ"],
  ["Odds3LenTan", "三連単オッズ"],
]);

export function betTypeLabel(value: string): string {
  return betTypes.get(value) ?? value;
}

export function snapshotKindLabel(value: string): string {
  return snapshotKinds.get(value) ?? value;
}

export function statusLabel(value?: string | null): string {
  return value ? (statuses.get(value) ?? value) : "不明";
}

export function scrapeTargetLabel(value: string): string {
  return scrapeTargets.get(value) ?? value;
}
