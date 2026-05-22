import { useParams, useNavigate } from 'react-router-dom';
import { Container, Title, Text, Group, Button, Loader, Paper, Progress } from '@mantine/core';
import { IconArrowLeft } from '@tabler/icons-react';
import { usePlaylistDetail } from '../hooks/usePlaylists';
import { TrackTable } from '../components/TrackTable';

export default function PlaylistDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const playlistId = parseInt(id || '0', 10);
  const { detail, loading } = usePlaylistDetail(playlistId);

  if (loading) return <Container fluid><Loader /></Container>;
  if (!detail) return <Container fluid><Text c="red">Playlist not found</Text></Container>;

  const { playlist, tracks } = detail;
  const percent = playlist.track_count > 0
    ? Math.round((playlist.downloaded_count / playlist.track_count) * 100)
    : 0;

  return (
    <Container fluid>
      <Group mb="lg">
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={18} />}
          onClick={() => navigate('/')}
        >
          Back
        </Button>
        <Title order={3}>{playlist.name}</Title>
      </Group>

      <Paper withBorder p="md" mb="lg">
        <Group gap="xl">
          <div>
            <Text size="sm" c="dimmed">Owner: {playlist.owner_name || 'unknown'}</Text>
            <Text size="sm" c="dimmed">Spotify ID: {playlist.spotify_id}</Text>
            <Text size="sm" c="dimmed">
              Last sync: {playlist.last_synced ? new Date(playlist.last_synced).toLocaleString() : 'Never'}
            </Text>
          </div>
          <div>
            <Text size="lg" fw={700}>{playlist.downloaded_count}/{playlist.track_count}</Text>
            <Text size="xs" c="dimmed">tracks downloaded</Text>
            <Progress value={percent} color={percent === 100 ? 'green' : 'blue'} size="sm" mt={4} style={{ minWidth: 150 }} />
          </div>
        </Group>
      </Paper>

      <TrackTable tracks={tracks} />
    </Container>
  );
}