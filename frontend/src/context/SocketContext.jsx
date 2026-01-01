import React, { createContext, useEffect, useMemo } from 'react';
import { useSocket } from '../hooks/useSocket';

export const SocketContext = createContext();

export const SocketProvider = ({ children }) => {
  const { socket, isConnected, connectError } = useSocket();

  // Memoize the context value to prevent unnecessary re-renders
  const contextValue = useMemo(() => ({
    socket,
    isConnected,
    isError: connectError,
    // Add a helper method to safely emit events
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

  // Handle user online status
  useEffect(() => {
    if (isConnected && socket) {
      console.log("CLIENT: Emitting user_online event.");
      const pingInterval = setInterval(() => {
        socket.volatile.emit('ping', { timestamp: Date.now() });
      }, 30000); // Send ping every 30 seconds

      // Initial user_online event
      socket.emit('user_online');

      return () => {
        clearInterval(pingInterval);
        // Optionally notify server that user is going offline
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