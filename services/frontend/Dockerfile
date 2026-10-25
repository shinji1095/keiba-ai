FROM mcr.microsoft.com/playwright:v1.57.0-jammy AS development
WORKDIR /app
COPY services/frontend/package.json services/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY services/frontend/ ./
# Source docs are authoritative; do not maintain a second checked-in copy.
COPY docs/test/data/ ./public/docs/test/data/
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM development AS build
RUN npm run build

FROM nginx:1.27-alpine AS production
COPY infra/nginx/nginx.conf /etc/nginx/nginx.conf
COPY infra/nginx/conf.d/app.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
