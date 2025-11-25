import { useEffect, useRef, useState, useCallback } from 'react';

const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://localhost:8080';

/**
 * Custom hook for WebSocket connection with auto-reconnect and heartbeat
 * @param {string} url - WebSocket URL path (e.g., '/ws/dashboard')
 * @param {function} onMessage - Callback for received messages
 * @returns {object} - { connectionStatus, error }
 */
export function useWebSocket(url, onMessage) {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000; // 1 second

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    try {
      setConnectionStatus('connecting');
      const ws = new WebSocket(`${WS_BASE}${url}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setConnectionStatus('connected');
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle heartbeat ping
          if (data.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }

          // Pass other messages to callback
          if (onMessage) {
            onMessage(data);
          }
        } catch (err) {
          console.error('[WebSocket] Error parsing message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('[WebSocket] Error:', err);
        setError('WebSocket error occurred');
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Closed', event.code, event.reason);
        setConnectionStatus('disconnected');
        wsRef.current = null;

        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(
            baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
            30000 // Max 30 seconds
          );
          
          reconnectAttemptsRef.current++;
          setConnectionStatus('reconnecting');
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setError('Max reconnection attempts reached');
          console.error('[WebSocket] Max reconnection attempts reached');
        }
      };

    } catch (err) {
      console.error('[WebSocket] Connection error:', err);
      setError(err.message);
      setConnectionStatus('disconnected');
    }
  }, [url, onMessage]);

  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { connectionStatus, error };
}

/**
 * Fetch data from API
 * @param {string} endpoint - API endpoint path
 * @returns {Promise} - Response data
 */
export async function fetchAPI(endpoint, options = {}) {
  const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080';
  const response = await fetch(`${BASE}${endpoint}`, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}
