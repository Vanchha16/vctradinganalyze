"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthStore } from "@/store/auth-store";

export type WebSocketStatus = "connecting" | "open" | "closed" | "error";

interface UseWebSocketOptions<T> {
  path: string; // e.g. "/ws/signals" or "/ws/prices"
  params?: Record<string, string | undefined>;
  enabled?: boolean;
  onMessage?: (data: T) => void;
  reconnectIntervalMs?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket<T = unknown>({
  path,
  params = {},
  enabled = true,
  onMessage,
  reconnectIntervalMs = 3000,
  maxReconnectAttempts = 5,
}: UseWebSocketOptions<T>) {
  const [status, setStatus] = useState<WebSocketStatus>("closed");
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const accessToken = useAuthStore((state) => state.accessToken);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const buildWsUrl = useCallback(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const wsBase = apiBase.replace(/^http/, "ws");
    const url = new URL(`${wsBase}${path}`);

    if (accessToken) {
      url.searchParams.set("token", accessToken);
    }
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, value);
      }
    }
    return url.toString();
  }, [path, params, accessToken]);

  const connect = useCallback(() => {
    if (!enabled || !accessToken) {
      return;
    }

    try {
      setStatus("connecting");
      const wsUrl = buildWsUrl();
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setStatus("open");
        reconnectAttemptsRef.current = 0;

        // Start ping heartbeat every 30s
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        if (event.data === "pong") return;
        try {
          const parsed = JSON.parse(event.data) as T;
          setLastMessage(parsed);
          onMessageRef.current?.(parsed);
        } catch {
          // Non-JSON payload
        }
      };

      ws.onclose = (event) => {
        setStatus("closed");
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

        // Reconnect if not cleanly closed and within attempt limit
        if (enabled && !event.wasClean && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const backoff = Math.min(
            reconnectIntervalMs * Math.pow(1.5, reconnectAttemptsRef.current),
            30000
          );
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(connect, backoff);
        }
      };

      ws.onerror = () => {
        setStatus("error");
      };
    } catch {
      setStatus("error");
    }
  }, [enabled, accessToken, buildWsUrl, reconnectIntervalMs, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setStatus("closed");
  }, []);

  const sendMessage = useCallback((message: string | object) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const payload = typeof message === "string" ? message : JSON.stringify(message);
      socketRef.current.send(payload);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    status,
    lastMessage,
    sendMessage,
    reconnect: connect,
    disconnect,
  };
}
