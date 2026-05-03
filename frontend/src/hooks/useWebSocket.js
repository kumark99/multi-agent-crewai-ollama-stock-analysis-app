import { useCallback, useEffect, useRef, useState } from 'react';

const WS_BASE = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

/**
 * useWebSocket – manages a WebSocket connection lifecycle.
 *
 * @param {string} sessionId  - unique session identifier (part of WS URL)
 * @param {Function} onMessage - callback invoked with parsed JSON messages
 * @returns {{ send, connect, disconnect, readyState }}
 */
export default function useWebSocket(sessionId, onMessage) {
  const wsRef = useRef(null);
  const [readyState, setReadyState] = useState(WebSocket.CLOSED);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setReadyState(WebSocket.CLOSED);
    }
  }, []);

  const connect = useCallback(() => {
    disconnect();

    const url = `${WS_BASE}/ws/${sessionId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    setReadyState(WebSocket.CONNECTING);

    ws.onopen = () => setReadyState(WebSocket.OPEN);
    ws.onclose = () => setReadyState(WebSocket.CLOSED);
    ws.onerror = () => setReadyState(WebSocket.CLOSED);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessageRef.current(data);
      } catch {
        // ignore parse errors
      }
    };
  }, [sessionId, disconnect]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => () => disconnect(), [disconnect]);

  return { connect, send, disconnect, readyState };
}
