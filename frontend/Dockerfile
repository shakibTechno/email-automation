# ---------------------------------------------------------------------------
# Frontend image: Vite/React build served by nginx, which also reverse-proxies
# the Django-owned paths so the whole app is same-origin.
# ---------------------------------------------------------------------------

# ---- deps ----------------------------------------------------------------
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- dev -----------------------------------------------------------------
# Target used by docker-compose.override.yml for the hot-reloading dev server.
FROM deps AS dev
WORKDIR /app
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# ---- build ---------------------------------------------------------------
FROM deps AS build
WORKDIR /app
COPY . .

# Vite inlines env vars at build time. A relative base URL keeps the bundle
# portable: nginx proxies /api to the backend on whatever host it is served from.
ARG VITE_API_URL=/api/v1
ARG VITE_APP_NAME="Email Marketing Platform"
ENV VITE_API_URL=$VITE_API_URL \
    VITE_APP_NAME=$VITE_APP_NAME

RUN npm run build

# ---- runtime -------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
