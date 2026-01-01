import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ScrapeScheduleCard } from "./ScrapeScheduleCard";

const baseStatus = {
  enabled: false,
  baba_codes: [1],
  mode: null,
  updated_at: "2025-01-01T00:00:00Z",
  note: null,
};

describe("ScrapeScheduleCard", () => {
  it("calls onSave with updated schedule", async () => {
    const onSave = vi.fn();
    const onRefresh = vi.fn();
    render(
      <ScrapeScheduleCard
        status={baseStatus}
        isLoading={false}
        onSave={onSave}
        onRefresh={onRefresh}
      />,
    );

    await userEvent.click(screen.getByRole("checkbox"));

    const input = screen.getByLabelText("baba_codes");
    await userEvent.clear(input);
    await userEvent.type(input, "3, 4");

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith({ enabled: true, baba_codes: [3, 4] });
  });
});
