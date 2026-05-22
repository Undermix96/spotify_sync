import { useState, useEffect, useCallback } from 'react';
import { Settings, settingsApi } from '../api/settings';

export function useSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const data = await settingsApi.get();
      setSettings(data);
    } catch {
      setSettings(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const update = async (data: Partial<Settings>) => {
    const updated = await settingsApi.update(data);
    setSettings(updated);
    return updated;
  };

  return { settings, loading, refetch: fetch, update };
}