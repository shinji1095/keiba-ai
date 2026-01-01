import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SyncControlCard } from "./SyncControlCard";

const baseStatus = {
  enabled: false,
  interval_days: 2,
  diff_enabled: true,
  last_synced_at: null,
  next_scheduled_at: null,
  last_fingerprint: null,
  last_attempted_at: null,
  last_status: "success",
  last_error: null,
  last_trigger: "manual",
  schedule_updated_at: null,
};

describe("SyncControlCard", () => {
  it("calls onSave with updated schedule", async () => {
    const onSave = vi.fn();
    const onTrigger = vi.fn();
    const onRefresh = vi.fn();
    render(
      <SyncControlCard
        status={baseStatus}
        isLoading={false}
        onSave={onSave}
        onTrigger={onTrigger}
        onRefresh={onRefresh}
      />,
    );

    const checkbox = screen.getByRole("checkbox");
    await userEvent.click(checkbox);

    const intervalInput = screen.getByRole("spinbutton");
    await userEvent.clear(intervalInput);
    await userEvent.type(intervalInput, "3");

    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith({
      enabled: true,
      interval_days: 3,
      diff_enabled: true,
    });
  });

  it("fires manual sync action", async () => {
    const onSave = vi.fn();
    const onTrigger = vi.fn();
    const onRefresh = vi.fn();
    render(
      <SyncControlCard
        status={baseStatus}
        isLoading={false}
        onSave={onSave}
        onTrigger={onTrigger}
        onRefresh={onRefresh}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Manual Sync" }));
    expect(onTrigger).toHaveBeenCalledTimes(1);
  });
});
