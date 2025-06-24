module.exports = {
  apps: [
    {
      name: 'virtual-agent',
      script: '/home/siacasa/projects/siacasa/venv/bin/python3',
      args: '-m bot_siacasa.main',
      cwd: '/home/siacasa/projects/siacasa/SIACASA',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/siacasa/projects/siacasa',
        HOST: '0.0.0.0',
        PORT: '3200'
      },
      time: true,
      watch: false
    },
    {
      name: 'siacasa-admin-panel',
      script: '/home/siacasa/projects/siacasa/venv/bin/python3',
      args: '-m admin_panel.main',
      cwd: '/home/siacasa/projects/siacasa/SIACASA',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/siacasa/projects/siacasa',
        ADMIN_HOST: '0.0.0.0',
        ADMIN_PORT: '4545',
        ADMIN_DEBUG: 'false'
      },
      time: true,
      watch: false
    }
  ]
};
