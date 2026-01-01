import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";

import PropTypes from "prop-types";

// Mock Button component for testing
const Button = ({ children, onClick, disabled, variant = "default", ...props }) => {
  return (
    <button 
      onClick={onClick} 
      disabled={disabled} 
      className={`btn btn-${variant}`}
      {...props}
    >
      {children}
    </button>
  );
};

Button.propTypes = {
  children: PropTypes.node.isRequired,
  onClick: PropTypes.func,
  disabled: PropTypes.bool,
  variant: PropTypes.string
};

describe("Button Component", () => {
  it("renders button with correct text", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument();
  });

  it("calls onClick handler when clicked", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    const button = screen.getByRole("button", { name: /click me/i });
    fireEvent.click(button);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled when disabled prop is true", () => {
    render(<Button disabled>Disabled</Button>);
    const button = screen.getByRole("button", { name: /disabled/i });
    expect(button).toBeDisabled();
  });

  it("applies correct variant class", () => {
    render(<Button variant="primary">Primary</Button>);
    const button = screen.getByRole("button", { name: /primary/i });
    expect(button).toHaveClass("btn-primary");
  });

  it("does not call onClick when disabled", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick} disabled>Disabled</Button>);
    
    const button = screen.getByRole("button", { name: /disabled/i });
    fireEvent.click(button);
    
    expect(handleClick).not.toHaveBeenCalled();
  });
});
