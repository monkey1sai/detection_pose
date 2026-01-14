FROM node:20-alpine AS build
WORKDIR /app
COPY web_client/package.json ./
RUN npm install
COPY web_client ./
RUN npm run build

FROM nginx:1.27-alpine
RUN rm -f /etc/nginx/conf.d/default.conf
COPY docker/web_default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
