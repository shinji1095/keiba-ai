import { Venue } from "@/api/generated";

export const VENUE_MASTER: ReadonlyArray<Venue> = [
  { baba_code: 3, venue_name: "帯広ば" },
  { baba_code: 10, venue_name: "盛岡" },
  { baba_code: 11, venue_name: "水沢" },
  { baba_code: 18, venue_name: "浦和" },
  { baba_code: 19, venue_name: "船橋" },
  { baba_code: 20, venue_name: "大井" },
  { baba_code: 21, venue_name: "川崎" },
  { baba_code: 22, venue_name: "金沢" },
  { baba_code: 23, venue_name: "笠松" },
  { baba_code: 24, venue_name: "名古屋" },
  { baba_code: 27, venue_name: "園田" },
  { baba_code: 28, venue_name: "姫路" },
  { baba_code: 31, venue_name: "高知" },
  { baba_code: 32, venue_name: "佐賀" },
  { baba_code: 36, venue_name: "門別" },
];

const VENUE_NAME_BY_BABA_CODE = new Map<number, string>(VENUE_MASTER.map((v) => [v.baba_code, v.venue_name]));
const PLACEHOLDER_RE = /^baba_\d+$/;

export function normalizeVenueName(babaCode: number, venueName?: string | null): string {
  const trimmed = (venueName ?? "").trim();
  const masterName = VENUE_NAME_BY_BABA_CODE.get(babaCode);
  if (!trimmed) return masterName ?? "";
  if (PLACEHOLDER_RE.test(trimmed) && masterName) return masterName;
  return trimmed;
}

export function mergeVenues(apiItems?: Venue[] | null): Venue[] {
  const byCode = new Map<number, Venue>();

  for (const v of apiItems ?? []) {
    byCode.set(v.baba_code, { ...v, venue_name: normalizeVenueName(v.baba_code, v.venue_name) });
  }

  for (const v of VENUE_MASTER) {
    const existing = byCode.get(v.baba_code);
    if (existing) {
      byCode.set(v.baba_code, { ...existing, venue_name: normalizeVenueName(existing.baba_code, existing.venue_name) });
    } else {
      byCode.set(v.baba_code, v);
    }
  }

  return Array.from(byCode.values()).sort((a, b) => a.baba_code - b.baba_code);
}
