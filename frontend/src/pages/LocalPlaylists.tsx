import { useState, useEffect } from 'react';
import { Container, Title, Table, Text, Group, Loader } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import { localApi, LocalPlaylistFile } from '../api/local';

export default function LocalPlaylists() {
  const [playlists, setPlaylists] = useState<LocalPlaylistFile[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    localApi.playlists()
      .then(setPlaylists)
      .catch(() => setPlaylists([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Container fluid><Loader /></Container>;

  return (
    <Container fluid>
      <Title order={3} mb="lg">Local Playlists</Title>

      {playlists.length === 0 ? (
        <Text c="dimmed" ta="center" py="xl">No playlists generated yet.</Text>
      ) : (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Size</Table.Th>
              <Table.Th>Modified</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {playlists.map((pl) => (
              <Table.Tr
                key={pl.name}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/local/${encodeURIComponent(pl.name)}`)}
              >
                <Table.Td>
                  <Text fw={500}>{pl.name}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">{Math.round(pl.size_bytes / 1024)} KB</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">{new Date(pl.modified_at * 1000).toLocaleString()}</Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Container>
  );
}