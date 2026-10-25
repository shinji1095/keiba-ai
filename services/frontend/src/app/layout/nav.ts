export type NavItem = {
  label: string;
  to: string;
};

export const navItems: NavItem[] = [
  { label: "ホーム", to: "/" },
  { label: "競馬場一覧", to: "/venues" },
  { label: "レース一覧", to: "/races" },
  { label: "本日の出走表", to: "/races/today" },
  { label: "過去のレース", to: "/races/past" },
  { label: "競走成績", to: "/results" },
  { label: "外部連携", to: "/admin/oauth-clients" },
  { label: "データ収集", to: "/scrape" },
  { label: "稼働モニター", to: "/scrape/status" },
  { label: "収集スケジュール", to: "/scrape-schedule" },
  { label: "テストデータ", to: "/test-data" },
  { label: "設定", to: "/settings" },
];
