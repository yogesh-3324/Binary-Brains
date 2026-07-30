# Build Stage
FROM node:18-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_IMAGE_API_URL=http://localhost:8000
ARG VITE_VIDEO_API_URL=http://localhost:8001
ENV VITE_IMAGE_API_URL=$VITE_IMAGE_API_URL
ENV VITE_VIDEO_API_URL=$VITE_VIDEO_API_URL

RUN npm run build

# Production Stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
