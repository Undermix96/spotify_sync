import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Container, Title, Text, Group, Button, Table, Loader } from '@mantine/core';
import { IconArrowLeft } from '@tabler/icons-react';
import { localApi, LocalPlaylistContent } from '../api/local';

export default function LocalPlaylistDetail() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [content, setContent] = useState<LocalPlaylistContent | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (name) {
      localApi.playlistContent(name)
        .then(setContent)
        .catch(() => setContent(null))
        .finally(() => setLoading(false));
    }
  }, [name]);

  if (loading) return <Container fluid><Loader /></Container>;
  if (!content) return <Container fluid><Text c="red">Playlist not found</Text></Container>;

  return (
    <Container fluid>
      <Group mb="lg">
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={18} />}
          onClick={() => navigate('/local')}
        >
          Back
        </Button>
        <Title order={3}>{content.name}</Title>
      </Group>

      <Text size="sm" c="dimmed" mb="md">File: {content.file_path}</Text>

      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>#</Table.Th>
            <Table.Th>Track</Table.Th>
            <Table.Th>File Path</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {content.tracks.map((track, idx) => (
            <Table.Tr key={idx}>
              <Table.Td>{idx + 1}</Table.Td>
              <Table.Td>
                <Text size="sm">
                  {track.extinf ? track.extinf.replace('#EXTINF:', '').split(',')[1] || track.extinf : '-'}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c="dimmed">{track.file_path}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      {content.tracks.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">No tracks in this playlist.</Text>
      )}
    </Container>
  );
}