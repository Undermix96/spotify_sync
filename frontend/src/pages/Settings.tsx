import { useState, useEffect } from 'react';
import {
  Container, Title, Text, TextInput, PasswordInput, Paper, Button,
  Group, NumberInput, Select, Divider, Loader, Alert,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconCheck, IconX } from '@tabler/icons-react';
import { useSettings } from '../hooks/useSettings';
import { settingsApi, Settings as SettingsType } from '../api/settings';

export default function SettingsPage() {
  const { settings, loading, update } = useSettings();
  const [form, setForm] = useState<Partial<SettingsType>>({});
  const [testingSlskd, setTestingSlskd] = useState(false);
  const [testingProwlarr, setTestingProwlarr] = useState(false);
  const [testingQbit, setTestingQbit] = useState(false);

  useEffect(() => {
    if (settings) {
      setForm(settings);
    }
  }, [settings]);

  const handleUpdate = async () => {
    try {
      await update(form);
      notifications.show({
        title: 'Saved',
        message: 'Settings updated successfully',
        color: 'green',
        icon: <IconCheck size={18} />,
      });
    } catch (e: any) {
      notifications.show({
        title: 'Error',
        message: e.message || 'Failed to save settings',
        color: 'red',
        icon: <IconX size={18} />,
      });
    }
  };

  const testSlskd = async () => {
    setTestingSlskd(true);
    const result = await settingsApi.testSlskd();
    notifications.show({
      title: result.success ? 'Connected' : 'Failed',
      message: result.message,
      color: result.success ? 'green' : 'red',
    });
    setTestingSlskd(false);
  };

  const testProwlarr = async () => {
    setTestingProwlarr(true);
    const result = await settingsApi.testProwlarr();
    notifications.show({
      title: result.success ? 'Connected' : 'Failed',
      message: result.message,
      color: result.success ? 'green' : 'red',
    });
    setTestingProwlarr(false);
  };

  const testQbit = async () => {
    setTestingQbit(true);
    const result = await settingsApi.testQbittorrent();
    notifications.show({
      title: result.success ? 'Connected' : 'Failed',
      message: result.message,
      color: result.success ? 'green' : 'red',
    });
    setTestingQbit(false);
  };

  if (loading) return <Container fluid><Loader /></Container>;

  return (
    <Container fluid>
      <Title order={3} mb="lg">Settings</Title>

      {/* Integration Settings */}
      <Paper withBorder p="md" mb="lg">
        <Title order={5} mb="md">slskd</Title>
        <TextInput
          label="URL"
          placeholder="http://slskd:5030"
          value={form.slskd_url || ''}
          onChange={(e) => setForm({ ...form, slskd_url: e.currentTarget.value })}
          mb="sm"
        />
        <PasswordInput
          label="API Key"
          placeholder="slskd API key"
          value={form.slskd_api_key || ''}
          onChange={(e) => setForm({ ...form, slskd_api_key: e.currentTarget.value })}
          mb="sm"
        />
        <Button variant="light" size="xs" onClick={testSlskd} loading={testingSlskd}>
          Test Connection
        </Button>
      </Paper>

      <Paper withBorder p="md" mb="lg">
        <Title order={5} mb="md">Prowlarr</Title>
        <TextInput
          label="URL"
          placeholder="http://prowlarr:9696"
          value={form.prowlarr_url || ''}
          onChange={(e) => setForm({ ...form, prowlarr_url: e.currentTarget.value })}
          mb="sm"
        />
        <PasswordInput
          label="API Key"
          placeholder="Prowlarr API key"
          value={form.prowlarr_api_key || ''}
          onChange={(e) => setForm({ ...form, prowlarr_api_key: e.currentTarget.value })}
          mb="sm"
        />
        <Button variant="light" size="xs" onClick={testProwlarr} loading={testingProwlarr}>
          Test Connection
        </Button>
      </Paper>

      <Paper withBorder p="md" mb="lg">
        <Title order={5} mb="md">qBittorrent</Title>
        <TextInput
          label="URL"
          placeholder="http://qbittorrent:8080"
          value={form.qbittorrent_url || ''}
          onChange={(e) => setForm({ ...form, qbittorrent_url: e.currentTarget.value })}
          mb="sm"
        />
        <TextInput
          label="Username"
          placeholder="admin"
          value={form.qbittorrent_username || ''}
          onChange={(e) => setForm({ ...form, qbittorrent_username: e.currentTarget.value })}
          mb="sm"
        />
        <PasswordInput
          label="Password"
          placeholder="adminadmin"
          value={form.qbittorrent_password || ''}
          onChange={(e) => setForm({ ...form, qbittorrent_password: e.currentTarget.value })}
          mb="sm"
        />
        <Button variant="light" size="xs" onClick={testQbit} loading={testingQbit}>
          Test Connection
        </Button>
      </Paper>

      {/* Intervals */}
      <Paper withBorder p="md" mb="lg">
        <Title order={5} mb="md">Scheduler Intervals (seconds)</Title>
        <Group grow>
          <NumberInput
            label="Sync Playlists"
            value={form.interval_sync_playlists ?? 21600}
            onChange={(v) => setForm({ ...form, interval_sync_playlists: typeof v === 'string' ? parseInt(v) : v })}
            min={60}
            step={60}
          />
          <NumberInput
            label="Scan Disk"
            value={form.interval_scan_disk ?? 43200}
            onChange={(v) => setForm({ ...form, interval_scan_disk: typeof v === 'string' ? parseInt(v) : v })}
            min={60}
            step={60}
          />
          <NumberInput
            label="Search Missing"
            value={form.interval_search_missing ?? 1800}
            onChange={(v) => setForm({ ...form, interval_search_missing: typeof v === 'string' ? parseInt(v) : v })}
            min={60}
            step={60}
          />
        </Group>
        <Group grow mt="sm">
          <NumberInput
            label="Monitor Downloads"
            value={form.interval_monitor_downloads ?? 300}
            onChange={(v) => setForm({ ...form, interval_monitor_downloads: typeof v === 'string' ? parseInt(v) : v })}
            min={10}
            step={10}
          />
          <NumberInput
            label="Build Playlists"
            value={form.interval_build_playlists ?? 900}
            onChange={(v) => setForm({ ...form, interval_build_playlists: typeof v === 'string' ? parseInt(v) : v })}
            min={60}
            step={60}
          />
          <NumberInput
            label="Cleanup Queue"
            value={form.interval_cleanup_queue ?? 3600}
            onChange={(v) => setForm({ ...form, interval_cleanup_queue: typeof v === 'string' ? parseInt(v) : v })}
            min={60}
            step={60}
          />
        </Group>
      </Paper>

      {/* Paths */}
      <Paper withBorder p="md" mb="lg">
        <Title order={5} mb="md">Paths</Title>
        <TextInput
          label="Music Path"
          value={form.music_path || '/music'}
          onChange={(e) => setForm({ ...form, music_path: e.currentTarget.value })}
          mb="sm"
        />
        <TextInput
          label="Playlists Path"
          value={form.playlists_path || '/playlists'}
          onChange={(e) => setForm({ ...form, playlists_path: e.currentTarget.value })}
          mb="sm"
        />
        <TextInput
          label="Log Level"
          value={form.log_level || 'INFO'}
          onChange={(e) => setForm({ ...form, log_level: e.currentTarget.value })}
          mb="sm"
        />
      </Paper>

      <Group justify="flex-end" mb="xl">
        <Button size="md" onClick={handleUpdate}>Save Settings</Button>
      </Group>
    </Container>
  );
}