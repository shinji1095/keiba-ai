import { describe, expect, it } from "vitest";
import { chartPaths } from "./chartUtils";
import { HistoryPoint } from "@/api/monitoring";

function point(seconds: number, value: number | null): HistoryPoint {
  return {
    at: new Date(seconds * 1000).toISOString(),
    values: { cpu: value },
    max_values: { cpu: value },
    sample_counts: { cpu: value == null ? 0 : 1 },
  };
}
describe("resource chart missing intervals", () => {
  it("breaks lines across missing samples and null observations", () => {
    const values = [point(10, 40), point(20, 50), point(70, 60), point(80, null), point(90, 20)];
    const paths = chartPaths(values, "cpu", "values", 0, 100_000, 100, 10);
    expect(paths).toHaveLength(3);
    expect(paths[0]).toContain(" L");
    expect(paths[1]).not.toContain(" L");
  });
  it("does not draw zero-valued lines for unavailable readings", () => {
    expect(chartPaths([point(10, null)], "cpu", "values", 0, 100_000, 100, 10)).toEqual([]);
  });
});
