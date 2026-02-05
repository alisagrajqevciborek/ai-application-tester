FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm install

# Copy the rest of the application
COPY . .

# Build the Next.js app
RUN pnpm build

# Expose port 3000
EXPOSE 3000

# Start the production server
CMD ["pnpm", "start"]