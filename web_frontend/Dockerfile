# WebFrontend Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY web_frontend/package.json web_frontend/package-lock.json* ./
RUN npm install
COPY web_frontend ./
RUN npm run build
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]

