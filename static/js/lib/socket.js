// The Socket.IO connection for presence and chat, served from our own origin.
import { io } from "/vendor/socket.io-4.8.4.esm.min.js";

export const socket = io();
