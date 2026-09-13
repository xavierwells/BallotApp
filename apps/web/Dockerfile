FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
# Keep downloaded archives between dependency changes; npm ci still validates
# package-lock.json and creates a clean installation on every uncached run.
RUN --mount=type=cache,id=ballot-web-npm,target=/root/.npm,sharing=locked \
    npm ci --omit=dev --omit=optional --prefer-offline

FROM node:24-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,id=ballot-web-npm,target=/root/.npm,sharing=locked \
    npm ci --omit=optional --prefer-offline
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_TELEMETRY_DISABLED=1
# Source edits invalidate this RUN layer, but not these BuildKit-owned caches.
# Cache only .next/cache, never all of .next: the built pages and assets must
# remain in the image so the unchanged production runner can copy them.
RUN --mount=type=cache,id=ballot-web-swc,target=/root/.cache/next-swc,sharing=locked \
    --mount=type=cache,id=ballot-web-next,target=/app/.next/cache,sharing=locked \
    npm test && npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
# npm is needed only while building.  Removing its global installation keeps
# package-manager-only dependencies out of the production image.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx \
    && addgroup --system --gid 10001 appgroup \
    && adduser --system --uid 10001 appuser
COPY --from=builder --chown=appuser:appgroup /app/.next ./.next
COPY --from=builder --chown=appuser:appgroup /app/public ./public
COPY --from=deps --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/package.json ./package.json
USER appuser
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start"]
