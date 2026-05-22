import { api } from './client';

export interface Download {
  id: number;
  playlist_track_id: number | null;
  source: string | null;
  status: string;
  external_id: string | null;
  progress: number;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  track_title: string | null;
  track_artist: string | null;
  playlist_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface DownloadAction {
  success: boolean;
  message: string;
}

export const downloadsApi = {
  list: (status?: string) => api.get<Download[]>(`/downloads${status ? `?status=${status}` : ''}`),
  retry: (id: number) => api.post<DownloadAction>(`/downloads/${id}/retry`),
  cancel: (id: number) => api.post<DownloadAction>(`/downloads/${id}/cancel`),
};