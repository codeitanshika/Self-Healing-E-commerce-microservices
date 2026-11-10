import { useEffect, useRef, useState } from "react";
import { API_URL, getJson } from "./api";

/**
 * Fetch `path` now and then every `intervalMs`. Pass a changing
 * `refreshKey` to force an immediate refetch (e.g. when the live
 * stream reports a new event) so the UI never waits for the next tick.
 */
export function usePolling(path, intervalMs = 4000, refreshKey = 0) {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    const controller = new AbortController();
    let alive = true;

    const load = async () => {
      try {
        const data = await getJson(path, controller.signal);
        if (alive) setState({ data, error: null, loading: false });
      } catch (err) {
        if (alive && err.name !== "AbortError") {
          setState((s) => ({ ...s, error: err.message, loading: false }));
        }
      }
    };

    load();
    const id = setInterval(load, intervalMs);
    return () => {
      alive = false;
      controller.abort();
      clearInterval(id);
    };
  }, [path, intervalMs, refreshKey]);

  return state;
}

/**
 * Subscribe to the backend's Server-Sent Events stream. EventSource
 * reconnects by itself; `connected` reflects the current state so the
 * UI can show an honest live/offline indicator.
 */
export function useEventStream(limit = 120) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const seen = useRef(new Set());

  useEffect(() => {
    const source = new EventSource(`${API_URL}/api/stream`);
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.addEventListener("pipeline", (e) => {
      const msg = JSON.parse(e.data);
      if (seen.current.has(msg.seq)) return; // replay after reconnect
      seen.current.add(msg.seq);
      setEvents((prev) => [...prev, msg].slice(-limit));
    });
    return () => source.close();
  }, [limit]);

  return { events, connected };
}

/** Re-render every `ms` so elapsed-time counters tick smoothly. */
export function useNow(ms = 250) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000), ms);
    return () => clearInterval(id);
  }, [ms]);
  return now;
}
