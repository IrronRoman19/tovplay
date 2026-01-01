import { createContext, useContext } from "react";

export const SocketContext = createContext();

export const useSocketContext = () => useContext(SocketContext);
