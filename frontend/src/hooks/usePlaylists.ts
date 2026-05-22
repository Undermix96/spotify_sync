import { useState, useEffect, useCallback } from 'react';
import { Playlist, PlaylistDetail, playlistsApi } from '../api/playlists';

export function usePlaylists() {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const data = await playlistsApi.list();
      setPlaylists(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  const add = async (url: string) => {
    const pl = await playlistsApi.add(url);
    setPlaylists(prev => [...prev, pl]);
    return pl;
  };

  const remove = async (id: number) => {
    await playlistsApi.remove(id);
    setPlaylists(prev => prev.filter(p => p.id !== id));
  };

  const sync = async (id: number) => {
    return playlistsApi.sync(id);
  };

  return { playlists, loading, error, refetch: fetch, add, remove, sync };
}

export function usePlaylistDetail(id: number) {
  const [detail, setDetail] = useState<PlaylistDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const data = await playlistsApi.get(id);
      setDetail(data);
    } catch {
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetch(); }, [fetch]);

  return { detail, loading, refetch: fetch };
}