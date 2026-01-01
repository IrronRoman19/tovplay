/**
 * Consolidated hooks module
 * Combines: useAuth, useCheckAvailability, useCheckGames, use-mobile, useSocket
 */

import * as React from "react";
import { useEffect, useRef, useState, useCallback } from "react";
import { useSelector } from "react-redux";
import { io } from "socket.io-client";
import { apiService } from "@/api";

// ============================================================================
// useAuth - Authentication state hook
// ============================================================================

export function useAuth() {
  const authState = useSelector(state => state.auths);
  return {
    user: authState.user,
    isLoggedIn: authState.isLoggedIn,
    isDiscordRegistered: authState.isDiscordRegistered
  };
}

// ============================================================================
// useCheckAvailability - Check if user has availability set
// ============================================================================

export const useCheckAvailability = () => {
  const checkAvailability = useCallback(async () => {
    try {
      const response = await apiService.get('/availability/');
      return response.data && (response.data.slots?.length > 0 || response.data.length > 0);
    } catch (error) {
      console.error('Error checking availability:', error);
      return false;
    }
  }, []);

  return { checkAvailability };
};

// ============================================================================
// useCheckGames - Check if user has games selected
// ============================================================================

export const useCheckGames = () => {
  const checkGames = useCallback(async () => {
    try {
      const response = await apiService.get('/user_game_preferences/');
      return response.data && response.data.length > 0;
    } catch (error) {
      console.error('Error checking user games:', error);
      return false;
    }
  }, []);

  return { checkGames };
};

// ============================================================================
// useIsMobile - Mobile breakpoint detection hook
// ============================================================================

const MOBILE_BREAKPOINT = 768;

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState(undefined);

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };
    mql.addEventListener("change", onChange);
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return !!isMobile;
}

// ============================================================================
// useSocket - Socket.IO connection hook
// ============================================================================

/**
 * A generic hook to manage a Socket.IO connection.
 * @returns {{socket: import('socket.io-client').Socket, isConnected: boolean, error: boolean}}
 */
export const useSocket = () => {
  const socketRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectError, setConnectError] = useState(false);

  useEffect(() => {
    if (socketRef.current) {
      return;
    }

    const wsUrl = import.meta.env.VITE_WS_URL || 'http://localhost:5001';
    console.log("CLIENT: Socket connecting to:", wsUrl);

    const socket = io(wsUrl, {
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 5000,
      transports: ["websocket", "polling"],
      autoConnect: true,
      withCredentials: true,
      secure: process.env.NODE_ENV === 'production',
      rejectUnauthorized: process.env.NODE_ENV === 'production'
    });

    socket.on('connect', () => {
      console.log('Socket connected successfully');
      setIsConnected(true);
      setConnectError(false);
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error.message);
      setConnectError(true);
    });

    socket.on('reconnect_attempt', (attempt) => {
      console.log(`Socket reconnection attempt ${attempt}`);
    });

    socket.on('reconnect_failed', () => {
      console.error('Socket reconnection failed');
    });

    socket.on("disconnect", reason => {
      console.log(`CLIENT: Socket disconnected. Reason: ${reason}`);
      setIsConnected(false);
    });

    socketRef.current = socket;

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, []);

  return { socket: socketRef.current, isConnected, connectError };
};

/**
 * A hook to register a listener for a specific Socket.IO event.
 * @param {import('socket.io-client').Socket} socket
 * @param {string} event
 * @param {(...args: any[]) => void} callback
 */
export const useSocketOn = (socket, event, callback) => {
  useEffect(() => {
    if (!socket) {
      return;
    }

    socket.on(event, callback);

    return () => {
      socket.off(event, callback);
    };
  }, [socket, event, callback]);
};
