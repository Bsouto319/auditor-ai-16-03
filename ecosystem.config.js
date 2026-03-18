module.exports = {
  apps: [
    {
      name: 'nexus-backend',
      script: 'python3',
      args: '-m uvicorn server:app --host 0.0.0.0 --port 8000',
      cwd: './backend',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: 8000
      }
    },
    {
      name: 'nexus-frontend',
      script: 'serve',
      args: '-s build -l 3000',
      cwd: './frontend',
      env: {
        NODE_ENV: 'production'
      }
    }
  ]
};
