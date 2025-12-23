# frontend/Dockerfile
FROM node:18

WORKDIR /usr/src/app

# Copy package files for caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --silent

# Copy source
COPY . .

EXPOSE 3000
CMD ["npm", "start"]
