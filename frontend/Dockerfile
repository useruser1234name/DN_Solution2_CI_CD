# React Frontend Dockerfile - DN_SOLUTION2
# Multi-stage build for development and production

# Development stage
FROM node:18-alpine as development
WORKDIR /app

# Package files 복사
COPY package*.json ./

# 의존성 설치
RUN npm install --legacy-peer-deps

# 소스 코드 복사
COPY . .

# 개발 서버 포트 노출
EXPOSE 3000

# 개발 서버 시작
CMD ["npm", "start"]

# Build stage
FROM node:18-alpine as builder
WORKDIR /app

# Package files 복사
COPY package*.json ./

# 의존성 설치 (dev dependencies 포함)
RUN npm ci

# 소스 코드 복사
COPY . .

# 프로덕션 빌드
RUN npm run build

# Production stage
FROM nginx:alpine as production

# 빌드된 파일 복사
COPY --from=builder /app/build /usr/share/nginx/html

# Custom nginx 설정 (있는 경우)
COPY nginx.conf /etc/nginx/nginx.conf

# 포트 노출
EXPOSE 80

# Nginx 시작
CMD ["nginx", "-g", "daemon off;"]
