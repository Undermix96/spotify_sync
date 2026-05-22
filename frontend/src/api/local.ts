import { api } from './client';

export interface LocalTrack {
  id: number;
  file_path: string;
  artist: string | null;
  album: string | null;
  title: string | null;
  track_number: number | null;
  duration_ms: number | null;
  format: string | null;
  file_size: number | null;
}

export interface LocalPlaylistFile {
  name: string;
  file_path: string;
  size_bytes: number;
  modified_at: number;
}

export interface LocalPlaylistContent {
  name: string;
  file_path: string;
  tracks: { extinf: string | null; file_path: string }[];
}

export const localApi = {
  tracks: (artist?: string, album?: string) =>
    api.get<LocalTrack[]>(`/local/tracks${artist ? `?artist=${artist}` : ''}${album ? `${artist ? '&' : '?'}album=${album}` : ''}`),
  playlists: () => api.get<LocalPlaylistFile[]>('/local/playlists'),
  playlistContent: (name: string) => api.get<LocalPlaylistContent>(`/local/playlists/${encodeURIComponent(name)}`),
};