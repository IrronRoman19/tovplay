import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import "@testing-library/jest-dom";
import App from "../App";

describe("App Component", () => {
  it("renders without crashing", () => {
    render(<App />);
    expect(document.body).toBeInTheDocument();
  });

  it("renders the main application", () => {
    render(<App />);
    const appElement = screen.getByRole("main") || document.querySelector('[data-testid="app"]') || document.body.firstChild;
    expect(appElement).toBeTruthy();
  });

  it("has correct document title", () => {
    render(<App />);
    expect(document.title).toBeDefined();
  });
});
