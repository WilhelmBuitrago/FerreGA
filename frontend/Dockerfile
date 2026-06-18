# frontend/Dockerfile
FROM node:20-alpine AS builder

# Instalar pnpm y dependencias para compilación nativa (si se necesitan)
RUN apk add --no-cache python3 make g++ && npm i -g pnpm

WORKDIR /app

# Copiar manifiestos de dependencias
COPY package.json pnpm-lock.yaml* ./

# Instalar dependencias (ignorar scripts de paquetes de dev como cypress/esbuild)
RUN pnpm install --frozen-lockfile --ignore-scripts || pnpm install --ignore-scripts

# Copiar código fuente explícitamente (evita problemas con .dockerignore)
COPY vite.config.ts tsconfig.json index.html ./
COPY src/ src/
COPY public/ public/
RUN pnpm build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173
CMD ["nginx", "-g", "daemon off;"]