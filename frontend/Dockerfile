# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files (lock files are optional)
COPY package.json ./
COPY package-lock.json* npm-shrinkwrap.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Accept build arguments for staging
ARG VITE_NODE_ENV=production
ARG VITE_API_BASE_URL
ARG VITE_WS_URL  
ARG VITE_ERROR_REPORTING_ENDPOINT
ARG VITE_GOOGLE_CLIENT_ID

ENV VITE_NODE_ENV=$VITE_NODE_ENV
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_ERROR_REPORTING_ENDPOINT=$VITE_ERROR_REPORTING_ENDPOINT
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration if exists
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]