import { createTheme, MantineColorsTuple } from '@mantine/core';

const spotifyGreen: MantineColorsTuple = [
  '#e8fce8',
  '#d0f4d0',
  '#a0e8a0',
  '#6ddb6d',
  '#40cf40',
  '#1db954',
  '#1a9e48',
  '#15823c',
  '#0f6630',
  '#0a4a24',
];

export const theme = createTheme({
  primaryColor: 'spotifyGreen',
  colors: {
    spotifyGreen,
  },
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  defaultRadius: 'sm',
  components: {
    Table: {
      defaultProps: {
        striped: true,
        highlightOnHover: true,
        withTableBorder: true,
      },
    },
    Card: {
      defaultProps: {
        shadow: 'sm',
        padding: 'lg',
        radius: 'md',
      },
    },
  },
});