module.exports = {
  apps: [
    {
      name: 'virtual-agent',
      script: '/home/sebas/projects/siacasa/siacasa/venv/bin/python',
      args: '-m bot_siacasa.main',
      cwd: '/home/sebas/projects/siacasa/siacasa/SIACASA',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/sebas/projects/siacasa/siacasa/SIACASA',
        HOST: '0.0.0.0',
        PORT: '3200'
      },
      error_file: '/home/sebas/projects/siacasa/siacasa/logs/bot-error.log',
      out_file: '/home/sebas/projects/siacasa/siacasa/logs/bot-out.log',
      log_file: '/home/sebas/projects/siacasa/siacasa/logs/bot-combined.log',
      time: true,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    },
    {
      name: 'siacasa-admin-panel',
      script: '/home/sebas/projects/siacasa/siacasa/venv/bin/python',
      args: '-m admin_panel.main',
      cwd: '/home/sebas/projects/siacasa/siacasa/SIACASA',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/sebas/projects/siacasa/siacasa/SIACASA',
        ADMIN_HOST: '0.0.0.0',
        ADMIN_PORT: '4545',
        ADMIN_DEBUG: 'false'
      },
      error_file: '/home/sebas/projects/siacasa/siacasa/logs/admin-error.log',
      out_file: '/home/sebas/projects/siacasa/siacasa/logs/admin-out.log',
      log_file: '/home/sebas/projects/siacasa/siacasa/logs/admin-combined.log',
      time: true,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    },
    {
      name: 'siacasa-web-demo',
      script: '/home/sebas/projects/siacasa/siacasa/venv/bin/python',
      args: '-m http.server 4040',
      cwd: '/home/sebas/projects/siacasa/siacasa/SIACASA/web_integration/demo-landing',
      env: {
        NODE_ENV: 'production'
      },
      error_file: '/home/sebas/projects/siacasa/siacasa/logs/web-demo-error.log',
      out_file: '/home/sebas/projects/siacasa/siacasa/logs/web-demo-out.log',
      log_file: '/home/sebas/projects/siacasa/siacasa/logs/web-demo-combined.log',
      time: true,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M'
    }
  ]
};
