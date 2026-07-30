FROM node:22-alpine AS base
WORKDIR /app

FROM base AS dependencies
COPY package*.json ./
RUN npm ci

FROM base AS development
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
EXPOSE 3000

FROM base AS builder
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
