import { useState, useEffect } from 'react';

export function useSessionState(key, initialValue) {
  const [state, setState] = useState(() => {
    const saved = sessionStorage.getItem(key);
    if (saved !== null) {
      try {
        const parsed = JSON.parse(saved);
        if (initialValue instanceof Map && Array.isArray(parsed)) {
          return new Map(parsed);
        }
        return parsed;
      } catch (e) {
        return saved; // fallback for plain strings
      }
    }
    return initialValue;
  });

  useEffect(() => {
    if (state === null || state === undefined) {
      sessionStorage.removeItem(key);
    } else if (state instanceof Map) {
      sessionStorage.setItem(key, JSON.stringify(Array.from(state.entries())));
    } else {
      sessionStorage.setItem(key, typeof state === 'string' ? state : JSON.stringify(state));
    }
  }, [key, state]);

  return [state, setState];
}
