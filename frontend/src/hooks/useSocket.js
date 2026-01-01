// Debug: Log the actual WebSocket URL used at runtime
import { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";

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

    // Get WebSocket URL from environment or use default
    const wsUrl = import.meta.env.VITE_WS_URL || 'http://localhost:5001';
    console.log("CLIENT: Socket connecting to:", wsUrl);
    
    const socket = io(wsUrl, {
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 5000,
      transports: ["websocket", "polling"], // Try both WebSocket and polling
      autoConnect: true,
      withCredentials: true,
      secure: process.env.NODE_ENV === 'production',
      rejectUnauthorized: process.env.NODE_ENV === 'production'
    });
    
    // Log connection status changes
    socket.on('connect', () => {
      console.log('Socket connected successfully');
    });
    
    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error.message);
    });
    
    socket.on('reconnect_attempt', (attempt) => {
      console.log(`Socket reconnection attempt ${attempt}`);
    });
    
    socket.on('reconnect_failed', () => {
      console.error('Socket reconnection failed');
    });

    socket.on("connect", () => {
      console.log("!!! CLIENT: Socket connected successfully!");
      setIsConnected(true);
      setConnectError(false); // Reset error on successful connection
    });

    socket.on("disconnect", reason => {
      console.log(`!!! CLIENT: Socket disconnected. Reason: ${reason}`);
      setIsConnected(false);
    });

    socket.on("connect_error", err => {
      console.error(`!!! CLIENT: Socket connection error: ${err.message}`);
      setConnectError(true);
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
