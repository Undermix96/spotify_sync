import { useState, useEffect, useCallback } from 'react';
import { Download, downloadsApi } from '../api/downloads';

export function useDownloads(status?: string) {
  const [downloads, setDownloads] = useState<Download[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const data = await downloadsApi.list(status);
      setDownloads(data);
    } catch {
      setDownloads([]);
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 10000);
    return () => clearInterval(interval);
  }, [fetch]);

  const retry = async (id: number) => {
    await downloadsApi.retry(id);
    await fetch();
  };

  const cancel = async (id: number) => {
    await downloadsApi.cancel(id);
    await fetch();
  };

  return { downloads, loading, refetch: fetch, retry, cancel };
}