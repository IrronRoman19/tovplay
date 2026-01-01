# Frontend

## ✨ Features

- **🤝 Player Discovery**: Find & connect with fellow gamers
- **🗓️ Session Scheduling**: Organize your upcoming game sessions effortlessly  
- **📬 Game Requests**: Send and receive game invites with ease
- **👤 Personalized Profiles**: Customize and explore detailed player profiles
- **🌐 Multi-language Support**: Experience the app in your preferred language

## 🛠️ Tech Stack

- **Framework**: React.js with Vite
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn UI
- **State Management**: Redux Toolkit
- **HTTP Client**: Axios
- **Testing**: Vitest, Cypress
- **Containerization**: Docker with Nginx

## 📋 Prerequisites

- Node.js 18+
- npm

## 🔧 Installation

### Local Development

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Run the application**
   ```bash
   # Option 1: Using npm
   npm run dev
   ```

3. **Access the application**: http://localhost:3000

### Docker Development

1. **Build and run with Docker**
   ```bash
   docker build -t frontend .
   docker run -p 80:80 frontend
   ```

## 🧪 Testing

```bash
# Run unit tests
npm run test

# Run E2E tests
npm run test:e2e

# Run tests with coverage
npm run test:coverage
```

## 🔍 Code Quality

```bash
# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Type checking
npm run type-check

# Format code
npm run format:write
```

## 🏗️ Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```
