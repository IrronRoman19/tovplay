import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  base: "/",
  plugins: [react()],
  server: {
    host: "0.0.0.0", // Allow access from any host
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:5001",
        changeOrigin: true,
        secure: false,
        ws: true
      }
    },
    cors: {
      origin: ["http://localhost:3000", "http://0.0.0.0:3000", "http://localhost:5001"],
      credentials: false
    }
  },
  preview: {
    host: "0.0.0.0",
    port: 3000
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src")
    },
    extensions: [".mjs", ".js", ".jsx", ".ts", ".tsx", ".json"]
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        ".js": "jsx"
      }
    }
  },
  build: {
    target: 'esnext',
    minify: 'terser',
    cssCodeSplit: true,
    chunkSizeWarningLimit: 500,
    sourcemap: false,
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug']
      },
      format: {
        comments: false
      }
    },
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // React core libraries
          if (id.includes('node_modules/react/') ||
              id.includes('node_modules/react-dom/') ||
              id.includes('node_modules/scheduler/')) {
            return 'react-core';
          }

          // React Router
          if (id.includes('node_modules/react-router') ||
              id.includes('node_modules/@remix-run')) {
            return 'react-router';
          }

          // UI Component libraries (Material UI, Ant Design, etc.)
          if (id.includes('node_modules/@mui/') ||
              id.includes('node_modules/@emotion/') ||
              id.includes('node_modules/antd/') ||
              id.includes('node_modules/@ant-design/')) {
            return 'ui-library';
          }

          // Form libraries
          if (id.includes('node_modules/formik') ||
              id.includes('node_modules/yup') ||
              id.includes('node_modules/react-hook-form')) {
            return 'forms';
          }

          // HTTP clients
          if (id.includes('node_modules/axios') ||
              id.includes('node_modules/fetch')) {
            return 'http-client';
          }

          // Date libraries
          if (id.includes('node_modules/date-fns') ||
              id.includes('node_modules/dayjs') ||
              id.includes('node_modules/moment')) {
            return 'date-utils';
          }

          // Utility libraries
          if (id.includes('node_modules/lodash') ||
              id.includes('node_modules/ramda') ||
              id.includes('node_modules/underscore')) {
            return 'utils';
          }

          // State management
          if (id.includes('node_modules/redux') ||
              id.includes('node_modules/@reduxjs') ||
              id.includes('node_modules/zustand') ||
              id.includes('node_modules/recoil')) {
            return 'state-mgmt';
          }

          // Icons
          if (id.includes('node_modules/react-icons') ||
              id.includes('node_modules/@fortawesome') ||
              id.includes('node_modules/@heroicons')) {
            return 'icons';
          }

          // Animation libraries
          if (id.includes('node_modules/framer-motion') ||
              id.includes('node_modules/react-spring')) {
            return 'animations';
          }

          // All other node_modules
          if (id.includes('node_modules/')) {
            return 'vendor';
          }
        },
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId ? chunkInfo.facadeModuleId.split('/').slice(-1)[0] : 'chunk';
          return `assets/js/[name]-[hash].js`;
        },
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.');
          const ext = info[info.length - 1];
          if (/\.(png|jpe?g|svg|gif|tiff|bmp|ico)$/i.test(assetInfo.name)) {
            return `assets/images/[name]-[hash].${ext}`;
          }
          if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name)) {
            return `assets/fonts/[name]-[hash].${ext}`;
          }
          if (/\.css$/i.test(assetInfo.name)) {
            return `assets/css/[name]-[hash].${ext}`;
          }
          return `assets/[name]-[hash].${ext}`;
        }
      }
    },
    assetsInlineLimit: 4096,
    reportCompressedSize: true,
    commonjsOptions: {
      include: [/node_modules/],
      transformMixedEsModules: true
    }
  }
});
