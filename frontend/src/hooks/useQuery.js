import { useEffect, useState } from 'react';

export function useQuery(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const base = 'http://localhost:8000';
    const fetchData = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${base}${path}`);
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => {
      cancelled = true;
    };
  }, [path]);

  return { data, loading };
}

