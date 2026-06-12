# Stage 1: Build the React app
FROM node:18 AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve the build with Nginx
FROM nginx:alpine

# Copy the build output to Nginx's html directory
COPY --from=build /app/dist /usr/share/nginx/html

# Install our SPA + /v1 reverse-proxy config. It's a `server {}` block, so it
# goes in conf.d (included by the stock nginx http{} context) — NOT the
# top-level nginx.conf.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Optionally pass environment variables to the frontend (see below)