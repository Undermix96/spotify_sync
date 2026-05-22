import { api } from './client';

export interface Settings {
  slskd_url: string;
  slskd_api_key: string;
  prowlarr_url: string;
  prowlarr_api_key: string;
  qbittorrent_url: string;
  qbittorrent_username: string;
  qbittorrent_password: string;
  music_path: string;
  playlists_path: string;
  db_path: string;
  log_level: string;
  interval_sync_playlists: number;
  interval_scan_disk: number;
  interval_search_missing: number;
  interval_monitor_downloads: number;
  interval_build_playlists: number;
  interval_cleanup_queue: number;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
}

export interface Stats {
  total_playlists: number;
  total_tracks_spotify: number;
  total_tracks_downloaded: number;
  active_downloads: number;
  pending_downloads: number;
  failed_downloads: number;
  local_tracks: number;
  disk_usage_bytes: number;
}

export const settingsApi = {
  get: () => api.get<Settings>('/settings'),
  update: (data: Partial<Settings>) => api.put<Settings>('/settings', data),
  testSlskd: () => api.post<ConnectionTestResult>('/settings/test-slskd'),
  testProwlarr: () => api.post<ConnectionTestResult>('/settings/test-prowlarr'),
  testQbittorrent: () => api.post<ConnectionTestResult>('/settings/test-qbittorrent'),
};

export const statsApi = {
  get: () => api.get<Stats>('/stats'),
};