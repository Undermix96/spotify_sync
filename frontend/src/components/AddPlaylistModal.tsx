import { useState } from 'react';
import { Modal, TextInput, Button, Group } from '@mantine/core';

interface AddPlaylistModalProps {
  opened: boolean;
  onClose: () => void;
  onSubmit: (url: string) => Promise<void>;
}

export function AddPlaylistModal({ opened, onClose, onSubmit }: AddPlaylistModalProps) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!url.trim()) return;
    try {
      setLoading(true);
      setError(null);
      await onSubmit(url.trim());
      setUrl('');
      onClose();
    } catch (e: any) {
      setError(e.message || 'Failed to add playlist');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Add Spotify Playlist" centered>
      <TextInput
        label="Spotify Playlist URL"
        placeholder="https://open.spotify.com/playlist/..."
        value={url}
        onChange={(e) => setUrl(e.currentTarget.value)}
        error={error}
        mb="md"
      />
      <Group justify="flex-end">
        <Button variant="subtle" onClick={onClose}>Cancel</Button>
        <Button onClick={handleSubmit} loading={loading}>Add</Button>
      </Group>
    </Modal>
  );
}