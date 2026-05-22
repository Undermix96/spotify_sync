import { Stack, NavLink } from '@mantine/core';
import { IconDashboard, IconPlaylist, IconDownload, IconSettings, IconMusic } from '@tabler/icons-react';
import { useLocation, useNavigate } from 'react-router-dom';

const links = [
  { label: 'Dashboard', icon: IconDashboard, path: '/' },
  { label: 'Downloads', icon: IconDownload, path: '/downloads' },
  { label: 'Local Playlists', icon: IconMusic, path: '/local' },
  { label: 'Settings', icon: IconSettings, path: '/settings' },
];

export function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Stack p="xs" gap={0}>
      {links.map(link => (
        <NavLink
          key={link.path}
          label={link.label}
          leftSection={<link.icon size={20} />}
          active={location.pathname === link.path}
          onClick={() => navigate(link.path)}
          variant="light"
          style={{ borderRadius: 4 }}
        />
      ))}
    </Stack>
  );
}