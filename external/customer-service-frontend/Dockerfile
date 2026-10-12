# syntax=docker/dockerfile:1
# ============================================================
# 电商客服前端（Vue 3 + Vite） → nginx 托管
# 端口：8080（宿主机） → 80（容器）
#   · 静态资源：/ 
#   · 后端接口：/api/       → customer-service-backend:18082
#   · 商城接口：/commerce/  → ecommerce-service:18081
# ============================================================

# ---------- 阶段 1：构建前端静态资源 ----------
FROM node:22-alpine AS build

WORKDIR /app

# 先装依赖，利用 layer cache
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# 再拷贝源码并构建
COPY . .
RUN npm run build

# ---------- 阶段 2：nginx 托管 + 反向代理 ----------
FROM nginx:1.27-alpine

ENV TZ=Asia/Shanghai

# 反向代理配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 构建产物
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
