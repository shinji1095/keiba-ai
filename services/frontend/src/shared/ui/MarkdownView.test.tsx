import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarkdownView } from "./MarkdownView";

describe("MarkdownView", () => {
  it("renders heading", () => {
    render(<MarkdownView content="## Test Heading" />);
    expect(screen.getByText("Test Heading")).toBeInTheDocument();
  });

  it("renders table rows", () => {
    const md = `| col1 | col2 |
|---|---|
| A | B |
| C | D |`;
    render(<MarkdownView content={md} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("D")).toBeInTheDocument();
  });

  it("escapes HTML in content", () => {
    render(<MarkdownView content="<script>alert('xss')</script>" />);
    expect(screen.queryByText("<script>alert('xss')</script>")).toBeInTheDocument();
  });
});





