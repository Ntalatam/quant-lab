FROM node:20-slim AS builder

ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN npm run build


FROM node:20-slim AS runner

ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app

RUN groupadd --system quantlab && useradd --system --gid quantlab --create-home quantlab

COPY --from=builder --chown=quantlab:quantlab /app/.next/standalone ./
COPY --from=builder --chown=quantlab:quantlab /app/.next/static ./.next/static
COPY --from=builder --chown=quantlab:quantlab /app/public ./public

USER quantlab

EXPOSE 3000

CMD ["node", "server.js"]
