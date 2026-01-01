import { describe, it, expect } from "vitest";

// Mock utility functions for testing
const formatDate = date => {
  if (!date) {
    return "Invalid date";
  }
  return new Date(date).toLocaleDateString();
};

const validateEmail = email => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const truncateString = (str, maxLength) => {
  if (!str || typeof str !== "string") {
    return "";
  }

  if (str.length <= maxLength) {
    return str;
  }
  return str.substring(0, maxLength) + "...";
};

const isValidUrl = string => {
  try {
    new URL(string);
    return true;
  } catch (error) {
    return false;
  }
};

describe("Helper Functions", () => {
  describe("formatDate", () => {
    it("formats valid date correctly", () => {
      const date = "2024-01-15";
      const result = formatDate(date);
      expect(result).toBe("1/15/2024");
    });

    it('returns "Invalid date" for null input', () => {
      expect(formatDate(null)).toBe("Invalid date");
    });

    it('returns "Invalid date" for undefined input', () => {
      expect(formatDate(undefined)).toBe("Invalid date");
    });
  });

  describe("validateEmail", () => {
    it("validates correct email format", () => {
      expect(validateEmail("test@example.com")).toBe(true);
      expect(validateEmail("user.name@domain.co.uk")).toBe(true);
    });

    it("rejects invalid email formats", () => {
      expect(validateEmail("invalid-email")).toBe(false);
      expect(validateEmail("test@")).toBe(false);
      expect(validateEmail("@example.com")).toBe(false);
      expect(validateEmail("")).toBe(false);
    });
  });

  describe("truncateString", () => {
    it("truncates long strings correctly", () => {
      const longString = "This is a very long string that needs to be truncated";
      expect(truncateString(longString, 20)).toBe("This is a very long ...");
    });

    it("returns original string if under limit", () => {
      const shortString = "Short";
      expect(truncateString(shortString, 20)).toBe("Short");
    });

    it("handles null/undefined inputs", () => {
      expect(truncateString(null, 10)).toBe("");
      expect(truncateString(undefined, 10)).toBe("");
    });

    it("handles non-string inputs", () => {
      expect(truncateString(123, 10)).toBe("");
      expect(truncateString([], 10)).toBe("");
    });
  });

  describe("isValidUrl", () => {
    it("validates correct URLs", () => {
      expect(isValidUrl("https://example.com")).toBe(true);
      expect(isValidUrl("http://localhost:3000")).toBe(true);
      expect(isValidUrl("ftp://files.example.com")).toBe(true);
    });

    it("rejects invalid URLs", () => {
      expect(isValidUrl("invalid-url")).toBe(false);
      expect(isValidUrl("")).toBe(false);
      expect(isValidUrl("just-a-string")).toBe(false);
    });
  });
});
