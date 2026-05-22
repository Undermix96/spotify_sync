import { api } from './client';

export interface Playlist {
  id: number;
  spotify_id: string;
  name: string;
  description: string | null;
  image_url: string | null;
  owner_name: string | null;
  track_count: number;
  downloaded_count: number;
  last_synced: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Track {
  id: number;
  playlist_id: number;
  spotify_track_id: string;
  title: string;
  artist: string;
  album: string | null;
  duration_ms: number | null;
  position: number;
  is_available: boolean;
  removed_from_spotify: boolean;
  download_status: string | null;
}

export interface PlaylistDetail {
  playlist: Playlist;
  tracks: Track[];
}

export interface PlaylistStatus {
  id: number;
  name: string;
  track_count: number;
  downloaded_count: number;
  last_synced: string | null;
  status: string;
}

export const playlistsApi = {
  list: () => api.get<Playlist[]>('/playlists'),
  add: (url: string) => api.post<Playlist>('/playlists', { url }),
  get: (id: number) => api.get<PlaylistDetail>(`/playlists/${id}`),
  remove: (id: number) => api.delete<void>(`/playlists/${id}`),
  sync: (id: number) => api.post<PlaylistStatus>(`/playlists/${id}/sync`),
};