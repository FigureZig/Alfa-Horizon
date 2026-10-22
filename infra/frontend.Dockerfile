# Фронт для общего стенда: собирается из frontend/ как есть — в frontend/ ничего не правим.
# Сборка без проверки типов (vue-tsc): стенд не падает из-за типов фронта, их проверка — `pnpm build` у фронта.
# VITE_API_BASE_URL=/api: браузер ходит на тот же адрес, nginx проксирует /api на сервис api — CORS не нужен.
FROM node:20.11.1-alpine AS build
WORKDIR /app
RUN npm install -g pnpm@10.29.2
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY index.html vite.config.ts tsconfig.json tsconfig.node.json ./
COPY src ./src
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm exec vite build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# resolver + переменная: nginx стартует, даже если api ещё поднимается, и находит его по имени сервиса.
# X-Request-Id: свой у клиента — пробрасываем, нет своего — nginx выдаёт новый (docs/api/README.md).
RUN printf '%s\n' \
    'map $http_x_request_id $rid { default $http_x_request_id; "" $request_id; }' \
    'server {' \
    '  listen 80;' \
    '  root /usr/share/nginx/html;' \
    '  resolver 127.0.0.11 valid=10s ipv6=off;' \
    '  set $api http://api:8000;' \
    '  location /api/ { proxy_pass $api; proxy_set_header Host $host; proxy_set_header X-Request-Id $rid; }' \
    '  location / { try_files $uri $uri/ /index.html; }' \
    '}' > /etc/nginx/conf.d/default.conf
EXPOSE 80
