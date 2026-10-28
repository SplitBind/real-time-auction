# FastAPI Production Deployment Guide (Ubuntu + PostgreSQL + Nginx + Systemd)

This guide walks through deploying a FastAPI application (`real_time_auction`) on a fresh Ubuntu server using `uv` as the package manager, PostgreSQL as the database, Systemd for process management, and Nginx as a reverse proxy with WebSocket support.

---

## Step 1: Install System Dependencies & Tools

First, update system packages and install PostgreSQL, Nginx, Git, and essential build tools.

```bash
# Update Ubuntu package index and upgrade installed packages
sudo apt update && sudo apt upgrade -y

# Install required system tools and runtime services
sudo apt install -y postgresql postgresql-contrib nginx git curl build-essential
```

Next, install Astral's `uv` package manager globally for your user:

```bash
# Install uv via the official installer script
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload your shell configuration to make uv accessible in PATH
source $HOME/.cargo/env
```

---

## Step 2: Configure PostgreSQL Database

Log into the default `postgres` superuser role to create your application database and database user.

```bash
# Access the PostgreSQL shell as the postgres system user
sudo -u postgres psql
```

Execute the following SQL commands in the PostgreSQL prompt:

```sql
-- Create the production database matching your configuration
CREATE DATABASE auction_db;

-- Create the database user with password
CREATE USER postgres WITH ENCRYPTED PASSWORD 'postgres';

-- Grant full database permissions to the created user
GRANT ALL PRIVILEGES ON DATABASE auction_db TO postgres;

-- Exit the psql interactive shell
\q
```

---

## Step 3: Clone Project & Prepare Application Directory

Set up your application directory inside `/var/www/` and assign ownership to your regular user account (e.g., `eye`).

```bash
# Create the parent web root directory if it does not exist
sudo mkdir -p /var/www

# Clone your project repository into /var/www/real-time-auction
sudo git clone <YOUR_GIT_REPOSITORY_URL> /var/www/real-time-auction

# Change file ownership to your current non-root system user
sudo chown -R $USER:$USER /var/www/real-time-auction

# Navigate into the project root directory
cd /var/www/real-time-auction
```

---

## Step 4: Configure Environment Variables

Create your production `.env` file in the root directory (`/var/www/real-time-auction/.env`).

```bash
# Create and edit the environment configuration file
nano .env
```

Add your environment variables:

```env
# Database connection string using asyncpg driver targeting local PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/auction_db

# Security & JWT Token configuration
SECRET_KEY=c1aa464e6155cb11f2e6bd4fcd34183cf269324f1aa5924c2e2a0f8dae918
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Static file uploads directory path
UPLOAD_DIR=static/uploads
```

---

## Step 5: Install Application Dependencies with `uv`

Sync project dependencies into a local virtual environment (`.venv`) using `uv`.

```bash
# Create .venv and install exact dependencies locked in uv.lock
uv sync --frozen --no-dev
```

---

## Step 6: Set Up Systemd Service for Process Management

To keep your FastAPI app running continuously in the background and survive server reboots, create a Systemd unit file.

```bash
# Create a new systemd unit configuration file
sudo nano /etc/systemd/system/fastapi-auction.service
```

Paste the following service configuration:

```ini
[Unit]
Description=FastAPI Real-Time Auction Server
After=network.target postgresql.service

[Service]
# Non-root system user running the process
User=eye

# Absolute path to the project root containing your code and .env
WorkingDirectory=/var/www/real-time-auction

# Explicit path to python inside .venv running uvicorn as a module
# This avoids PATH lookup errors with uv in systemd daemons
ExecStart=/var/www/real-time-auction/.venv/bin/python -m uvicorn real_time_auction.main:app --host 127.0.0.1 --port 8000 --workers 4

# Automatically restart the application on unexpected crashes
Restart=always

# Path to environment file
EnvironmentFile=/var/www/real-time-auction/.env

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Reload systemd manager configuration to recognize new service file
sudo systemctl daemon-reload

# Enable the service to launch automatically on system boot
sudo systemctl enable fastapi-auction

# Start the service immediately
sudo systemctl start fastapi-auction

# Check active status of the service
sudo systemctl status fastapi-auction
```

---

## Step 7: Configure Nginx as Reverse Proxy

Create an Nginx configuration file to manage public HTTP traffic, proxy real-time WebSocket connections, and serve static upload assets efficiently.

```bash
# Create site configuration in Nginx sites-available
sudo nano /etc/nginx/sites-available/auction
```

Add the following Nginx server block:

```nginx
server {
    listen 80;
    server_name your_domain_or_server_ip;

    # Set maximum allowed client request body size (for image uploads)
    client_max_body_size 50M;

    # Serve static assets directly from disk via Nginx for high performance
    location /static/ {
        alias /var/www/real-time-auction/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Proxy all other requests to internal Uvicorn server on port 8000
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        
        # Headers required for handling WebSocket connections (real-time bidding)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Preserve original client request headers
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Extended timeouts for long-lived WebSocket connections
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

Enable the configuration and restart Nginx:

```bash
# Create a symbolic link to enable the site configuration
sudo ln -s /etc/nginx/sites-available/auction /etc/nginx/sites-enabled/

# Test Nginx configuration for syntax errors
sudo nginx -t

# Restart Nginx web server to apply changes
sudo systemctl restart nginx
```

---

## Step 8: Useful Operational Commands

```bash
# View live application logs
sudo journalctl -u fastapi-auction.service -f

# Restart FastAPI service after pulling code updates
sudo systemctl restart fastapi-auction

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log
```
