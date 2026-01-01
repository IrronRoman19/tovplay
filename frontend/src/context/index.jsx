/**
 * Consolidated context module
 * Combines: SocketContext, ThemeContext
 */

import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { useSocket } from '@/hooks';
import { applyTheme, applyFontSize, applyReducedMotion } from '@/utils';

// ============================================================================
// SocketContext - WebSocket connection context
// ============================================================================

export const SocketContext = createContext();

export const SocketProvider = ({ children }) => {
  const { socket, isConnected, connectError } = useSocket();

  const contextValue = useMemo(() => ({
    socket,
    isConnected,
    isError: connectError,
    safeEmit: (event, data, callback) => {
      if (isConnected && socket) {
        if (callback) {
          return socket.emit(event, data, callback);
        }
        return socket.emit(event, data);
      }
      console.warn(`Cannot emit ${event}: Socket not connected`);
      return false;
    }
  }), [socket, isConnected, connectError]);

  useEffect(() => {
    if (isConnected && socket) {
      console.log("CLIENT: Emitting user_online event.");
      const pingInterval = setInterval(() => {
        socket.volatile.emit('ping', { timestamp: Date.now() });
      }, 30000);

      socket.emit('user_online');

      return () => {
        clearInterval(pingInterval);
        if (socket.connected) {
          socket.emit('user_offline');
        }
      };
    }
  }, [isConnected, socket]);

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  );
};

export const useSocketContext = () => useContext(SocketContext);

// ============================================================================
// ThemeContext - Theme, font size, and motion preferences context
// ============================================================================

const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  const [fontSize, setFontSize] = useState('medium');
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem('tovplay-theme') || 'light';
    const savedFontSize = localStorage.getItem('tovplay-font-size') || 'medium';
    const savedReduceMotion = localStorage.getItem('tovplay-reduce-motion') === 'true';

    setTheme(savedTheme);
    setFontSize(savedFontSize);
    setReduceMotion(savedReduceMotion);

    applyTheme(savedTheme);
    applyFontSize(savedFontSize);
    applyReducedMotion(savedReduceMotion);

    document.body.classList.add('theme-loaded');

    return () => {
      document.body.classList.remove('theme-loaded');
    };
  }, []);

  const updateTheme = (newTheme) => {
    const validTheme = ['light', 'dark', 'system'].includes(newTheme) ? newTheme : 'light';
    setTheme(validTheme);
    applyTheme(validTheme);

    window.dispatchEvent(
      new StorageEvent('storage', {
        key: 'tovplay-theme',
        newValue: validTheme,
        storageArea: localStorage
      })
    );
  };

  const updateFontSize = (newSize) => {
    setFontSize(newSize);
    applyFontSize(newSize);
  };

  const updateReduceMotion = (newValue) => {
    setReduceMotion(newValue);
    applyReducedMotion(newValue);
  };

  return (
    <ThemeContext.Provider
      value={{
        theme,
        fontSize,
        reduceMotion,
        updateTheme,
        updateFontSize,
        updateReduceMotion,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
