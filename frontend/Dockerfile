FROM node:20-alpine

WORKDIR /app

# Copy package files (repo uses npm + package-lock.json)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the Next.js app
RUN npm run build

# Expose port 3000
EXPOSE 3000

# Start the production server
CMD ["npm", "run", "start"]