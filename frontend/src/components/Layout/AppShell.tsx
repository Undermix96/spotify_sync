import { AppShell as MantineShell, Group, Title, Text, Anchor } from '@mantine/core';
import { Navbar } from './Navbar';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <MantineShell
      header={{ height: 50 }}
      navbar={{ width: 220, breakpoint: 'sm' }}
      padding="md"
    >
      <MantineShell.Header>
        <Group h="100%" px="md">
          <Title order={4} c="spotifyGreen.5">Spotify Sync</Title>
        </Group>
      </MantineShell.Header>

      <MantineShell.Navbar>
        <Navbar />
      </MantineShell.Navbar>

      <MantineShell.Main>
        {children}
      </MantineShell.Main>
    </MantineShell>
  );
}