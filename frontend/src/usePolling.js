/**
 * usePolling.js
 * =============
 * A reusable React hook that fetches data from an API endpoint
 * and re-fetches it every few seconds (polling).
 *
 * Why a custom hook? Every part of the dashboard needs the same
 * pattern: "fetch this URL, keep it fresh, give me the latest data."
 * Instead of repeating that logic in every component, we write it
 * once here and reuse it everywhere.
 *
 * Usage:
 *   const data = usePolling("/api/services", 4000);
 */

import { useState, useEffect } from "react";

const API_URL = import.meta.env.VITE_API_URL;

export function usePolling(path, intervalMs = 4000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isActive = true; // prevents updating state after component unmounts

    const fetchData = async () => {
      try {
        const response = await fetch(`${API_URL}${path}`);
        const json = await response.json();
        if (isActive) {
          setData(json);
          setError(null);
        }
      } catch (err) {
        if (isActive) {
          setError(err.message);
        }
      }
    };

    fetchData(); // fetch immediately on mount
    const intervalId = setInterval(fetchData, intervalMs); // then every intervalMs

    // cleanup: stop polling when component unmounts
    return () => {
      isActive = false;
      clearInterval(intervalId);
    };
  }, [path, intervalMs]);

  return { data, error };
}