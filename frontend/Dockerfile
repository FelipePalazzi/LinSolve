# Dockerfile.frontend - LinSolve Frontend (Astro + React)
# Build stage para producción

FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 astro

COPY --from=builder --chown=astro:nodejs /app/dist ./dist
COPY --from=builder --chown=astro:nodejs /app/package.json ./

USER astro

EXPOSE 4321

CMD ["node", "dist/server/entry.mjs"]