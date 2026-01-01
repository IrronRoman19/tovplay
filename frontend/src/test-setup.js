import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom";

// Cleanup after each test case
afterEach(() => {
  cleanup();
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor(callback) {
    this.callback = callback;
  }
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {}
  })
});

// Mock scrollTo
global.scrollTo = () => {};

// Mock localStorage
const localStorageMock = {
  getItem: key => localStorageMock[key] || null,
  setItem: (key, value) => {
    localStorageMock[key] = value; 
  },
  removeItem: key => {
    delete localStorageMock[key]; 
  },
  clear: () => {
    Object.keys(localStorageMock).forEach(key => {
      if (key !== "getItem" && key !== "setItem" && key !== "removeItem" && key !== "clear") {
        delete localStorageMock[key];
      }
    });
  }
};

global.localStorage = localStorageMock;

// Mock sessionStorage
global.sessionStorage = {
  ...localStorageMock
};

// Mock fetch
global.fetch = async (url, options) => {
  console.log("Mock fetch called with:", url, options);
  return {
    ok: true,
    status: 200,
    json: async () => ({ message: "Mock response" }),
    text: async () => "Mock response"
  };
};
