export type NavItem = {
  label: string;
  to: string;
};

export const navItems: NavItem[] = [
  { label: "Overview", to: "/" },
  { label: "Venues", to: "/venues" },
  { label: "Races", to: "/races" },
  { label: "Today Races", to: "/races/today" },
  { label: "Past Races", to: "/races/past" },
  { label: "Race Results", to: "/results" },
  { label: "OAuth Clients", to: "/admin/oauth-clients" },
  { label: "Scrape Console", to: "/scrape" },
  { label: "Scrape Schedule", to: "/scrape-schedule" },
  { label: "Test Data", to: "/test-data" },
  { label: "Settings", to: "/settings" },
];
