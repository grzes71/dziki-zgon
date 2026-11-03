import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  site: 'https://grzes71.github.io',
  base: '/dziki-zgon',
  trailingSlash: 'always',
  integrations: [tailwind()],
});

