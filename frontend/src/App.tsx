import { Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/Layout/AppShell';
import Dashboard from './pages/Dashboard';
import PlaylistDetail from './pages/PlaylistDetail';
import LocalPlaylists from './pages/LocalPlaylists';
import LocalPlaylistDetail from './pages/LocalPlaylistDetail';
import Downloads from './pages/Downloads';
import Settings from './pages/Settings';

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/playlist/:id" element={<PlaylistDetail />} />
        <Route path="/local" element={<LocalPlaylists />} />
        <Route path="/local/:name" element={<LocalPlaylistDetail />} />
        <Route path="/downloads" element={<Downloads />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}