// The Socket.IO connection for presence and chat, served from our own origin.
import { io } from "/vendor/socket.io-4.8.4.esm.min.js";

// WebSocket first (one connection, no polling round trips); polling if it is blocked.
export const socket = io({ transports: ["websocket", "polling"] });
