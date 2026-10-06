# ---- build: type-check + bundle do Vite ----
FROM node:26-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- runtime: nginx sem root servindo os estáticos e fazendo proxy de /api ----
FROM nginxinc/nginx-unprivileged:1.29-alpine
ENV API_URL=http://backend:8000
# A imagem oficial roda envsubst em /etc/nginx/templates/*.template na inicialização.
# Restringimos à variável API_URL para não tocar em $host, $uri etc.
ENV NGINX_ENVSUBST_FILTER=API_URL
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
