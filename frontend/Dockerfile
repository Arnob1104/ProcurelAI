FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
# The proxy target is read at build time.
ARG API_URL=http://backend:8000
ENV API_URL=$API_URL
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
