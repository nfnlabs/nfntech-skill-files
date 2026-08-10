---
name: backend-server-optimization
description: Server optimization standards for production Node.js applications — rate limiting, traffic handling, PM2 process management, Nginx configuration, caching, and performance tuning.
triggers:
  - user
  - model
---

# Backend Server Optimization Standards

You are a senior DevOps/backend engineer. Optimize applications for production: handle traffic efficiently, prevent abuse, manage processes reliably, and configure reverse proxies correctly.

---

## 0. Optimization Checklist

Before deploying to production:

- [ ] Rate limiting configured on public endpoints
- [ ] Request timeout set on all external calls
- [ ] Connection pooling configured for databases
- [ ] Caching strategy implemented (Redis/in-memory)
- [ ] Gzip compression enabled
- [ ] Static assets cached with proper headers
- [ ] PM2 configured with proper restart policies
- [ ] Nginx reverse proxy configured
- [ ] Load balancing across multiple instances
- [ ] Monitoring and alerting in place
- [ ] Database indexes optimized
- [ ] Memory leaks checked
- [ ] Logging doesn't impact performance

---

## 1. Rate Limiting

### Prevent Abuse & DDoS

Rate limiting protects endpoints from abuse and ensures fair resource usage.

```js
// Using express-rate-limit
const rateLimit = require('express-rate-limit');

// Strict limit for auth endpoints
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 requests per window
  message: 'Too many login attempts, please try again later',
  standardHeaders: true,
  legacyHeaders: false,
  skip: (req) => req.user && req.user.isAdmin // Skip for admins
});

// Moderate limit for API endpoints
const apiLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100, // 100 requests per minute
  keyGenerator: (req) => req.user?.id || req.ip, // Rate limit per user or IP
  handler: (req, res) => {
    res.status(429).json({
      success: false,
      message: 'Too many requests, please try again later'
    });
  }
});

// Loose limit for public endpoints
const publicLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 1000,
  skip: (req) => req.ip === '127.0.0.1' // Skip localhost
});

// Apply limiters
app.post('/auth/login', authLimiter, loginController);
app.post('/auth/register', authLimiter, registerController);
app.get('/api/users', apiLimiter, getUsersController);
app.get('/public/posts', publicLimiter, getPostsController);
```

### Store-Based Rate Limiting (Distributed)

For multiple server instances, use Redis:

```js
const RedisStore = require('rate-limit-redis');
const redis = require('redis');
const client = redis.createClient({
  host: process.env.REDIS_HOST,
  port: process.env.REDIS_PORT
});

const limiter = rateLimit({
  store: new RedisStore({
    client: client,
    prefix: 'rate-limit:'
  }),
  windowMs: 15 * 60 * 1000,
  max: 100
});

app.use(limiter);
```

### Custom Rate Limiting Logic

```js
const requestCounts = new Map();

function customRateLimiter(req, res, next) {
  const key = req.user?.id || req.ip;
  const now = Date.now();
  const windowStart = now - 60 * 1000; // 1 minute window

  if (!requestCounts.has(key)) {
    requestCounts.set(key, []);
  }

  const requests = requestCounts.get(key);
  const recentRequests = requests.filter(time => time > windowStart);

  if (recentRequests.length >= 100) {
    return res.status(429).json({ error: 'Too many requests' });
  }

  recentRequests.push(now);
  requestCounts.set(key, recentRequests);
  next();
}

app.use(customRateLimiter);
```

---

## 2. Traffic Handling & Load Balancing

### Connection Pooling

Reuse database connections instead of creating new ones.

```js
// PostgreSQL with pg pool
const { Pool } = require('pg');

const pool = new Pool({
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  max: 20, // Maximum connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000
});

// Use pool for queries
pool.query('SELECT * FROM users', (err, result) => {
  if (err) console.error(err);
  else console.log(result.rows);
});
```

### Request Timeout

Prevent hanging requests from consuming resources.

```js
// Global timeout middleware
app.use((req, res, next) => {
  req.setTimeout(30000); // 30 seconds
  res.setTimeout(30000);
  next();
});

// Per-route timeout
app.get('/api/heavy-operation', (req, res) => {
  req.setTimeout(60000); // 60 seconds for this route
  // ... operation
});

// External API call timeout
const axios = require('axios');

const client = axios.create({
  timeout: 5000 // 5 seconds
});

try {
  const response = await client.get('https://api.example.com/data');
} catch (err) {
  if (err.code === 'ECONNABORTED') {
    console.error('Request timeout');
  }
}
```

### Graceful Shutdown

Handle shutdown signals properly to avoid data loss.

```js
const server = app.listen(PORT);
let isShuttingDown = false;

process.on('SIGTERM', async () => {
  if (isShuttingDown) return;
  isShuttingDown = true;

  console.log('SIGTERM received, shutting down gracefully...');

  // Stop accepting new requests
  server.close(async () => {
    // Close database connections
    await db.close();
    // Close cache connections
    await redis.quit();
    console.log('Server shut down');
    process.exit(0);
  });

  // Force exit after timeout
  setTimeout(() => {
    console.error('Forced shutdown after timeout');
    process.exit(1);
  }, 30000);
});
```

### Load Balancing with Multiple Instances

```js
// app.js
const cluster = require('cluster');
const os = require('os');

if (cluster.isMaster) {
  const numCPUs = os.cpus().length;

  // Fork workers
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();
  }

  // Restart crashed workers
  cluster.on('exit', (worker, code, signal) => {
    console.log(`Worker ${worker.process.pid} died`);
    cluster.fork();
  });
} else {
  // Worker process
  app.listen(PORT, () => {
    console.log(`Worker ${process.pid} listening on port ${PORT}`);
  });
}
```

---

## 3. PM2 Process Management

### Basic PM2 Configuration

```js
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'api-server',
      script: './server.js',
      instances: 'max', // Use all CPU cores
      exec_mode: 'cluster',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      },
      error_file: './logs/err.log',
      out_file: './logs/out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      max_memory_restart: '500M', // Restart if memory exceeds 500MB
      watch: false, // Don't watch files in production
      ignore_watch: ['node_modules', 'logs'],
      max_restarts: 10,
      min_uptime: '10s'
    }
  ]
};
```

### PM2 Commands

```bash
# Start application
pm2 start ecosystem.config.js

# Start with specific environment
pm2 start ecosystem.config.js --env production

# Monitor processes
pm2 monit

# View logs
pm2 logs api-server
pm2 logs api-server --lines 100
pm2 logs api-server --err

# Restart/reload
pm2 restart api-server
pm2 reload api-server # Graceful reload

# Stop/delete
pm2 stop api-server
pm2 delete api-server

# List all processes
pm2 list

# Save PM2 configuration
pm2 save

# Resurrect saved configuration on reboot
pm2 startup
```


### Health Check Endpoint

```js
// Health check for PM2 monitoring
app.get('/health', (req, res) => {
  const health = {
    status: 'UP',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    database: 'connected' // Check actual DB connection
  };
  res.json(health);
});
```

---

## 4. Nginx Configuration

### Basic Reverse Proxy Setup

```nginx
# /etc/nginx/sites-available/api-server
upstream api_backend {
  least_conn; # Load balancing strategy
  server 127.0.0.1:3000;
  server 127.0.0.1:3001;
  server 127.0.0.1:3002;
  server 127.0.0.1:3003;
  keepalive 32; # Connection pooling
}

server {
  listen 80;
  server_name api.example.com;

  # Redirect HTTP to HTTPS
  return 301 https://$server_name$request_uri;
}

server {
  listen 443 ssl http2;
  server_name api.example.com;

  # SSL certificates
  ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

  # SSL configuration
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers HIGH:!aNULL:!MD5;
  ssl_prefer_server_ciphers on;

  # Gzip compression
  gzip on;
  gzip_types text/plain text/css application/json application/javascript;
  gzip_min_length 1000;
  gzip_comp_level 6;

  # Request size limits
  client_max_body_size 10M;

  # Timeouts
  proxy_connect_timeout 60s;
  proxy_send_timeout 60s;
  proxy_read_timeout 60s;

  # Proxy headers
  location / {
    proxy_pass http://api_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    
    # Buffering
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
  }

  # Static assets caching
  location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    proxy_pass http://api_backend;
  }

  # Health check endpoint
  location /health {
    access_log off;
    proxy_pass http://api_backend;
  }
}
```

### Rate Limiting in Nginx

```nginx
# Rate limiting configuration
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

server {
  listen 443 ssl http2;
  server_name api.example.com;

  # Apply rate limits
  location /auth/login {
    limit_req zone=auth burst=2 nodelay;
    proxy_pass http://api_backend;
  }

  location /api/ {
    limit_req zone=api burst=10 nodelay;
    proxy_pass http://api_backend;
  }

  location / {
    limit_req zone=general burst=20 nodelay;
    proxy_pass http://api_backend;
  }
}
```


---

## 5. Caching Strategies

### Redis Caching with TTL

```js
const redis = require('redis');
const client = redis.createClient({
  host: process.env.REDIS_HOST,
  port: process.env.REDIS_PORT
});

app.get('/api/posts', async (req, res) => {
  const cacheKey = 'posts:all';
  const cached = await client.get(cacheKey);

  if (cached) {
    return res.json({ data: JSON.parse(cached), source: 'cache' });
  }

  const posts = await Post.find().limit(100);
  await client.setex(cacheKey, 600, JSON.stringify(posts)); // 10 min TTL
  res.json({ data: posts, source: 'db' });
});

// Invalidate on update
app.put('/api/posts/:id', async (req, res) => {
  const post = await Post.findByIdAndUpdate(req.params.id, req.body);
  await client.del('posts:all'); // Clear cache
  res.json(post);
});
```

---

## 6. Database Optimization

**Connection Pooling**: Reuse connections instead of creating new ones.

```js
const sequelize = new Sequelize(database, username, password, {
  host: hostname,
  dialect: 'postgres',
  pool: { max: 20, min: 5, acquire: 30000, idle: 10000 }
});
```

**Query Optimization**: Use eager loading, avoid N+1 queries.

```js
// Bad — N+1
const orders = await Order.findAll();
for (const order of orders) {
  order.customer = await Customer.findByPk(order.customerId);
}

// Good — eager load
const orders = await Order.findAll({
  include: [{ model: Customer }],
  attributes: ['id', 'total', 'customerId']
});
```

**Indexing**: Index frequently queried columns.

```sql
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_customer_status ON orders(customer_id, status);
```

---

## 7. Monitoring & Logging

**Structured Logging**: Log with context, no PII/secrets.

```js
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' })
  ]
});

logger.info('Order created', {
  orderId: order.id,
  customerId: order.customerId,
  total: order.total,
  duration: Date.now() - startTime
});
```

---

## 8. Performance Checklist

Before production deployment:

- [ ] Rate limiting configured on all public endpoints
- [ ] Request timeouts set (30-60 seconds)
- [ ] Database connection pooling enabled
- [ ] Gzip compression enabled in Nginx
- [ ] Static assets cached (1 year expiry)
- [ ] PM2 configured with proper restart policies
- [ ] Nginx reverse proxy configured with load balancing
- [ ] Health check endpoint implemented
- [ ] Graceful shutdown handling in place
- [ ] Memory limits set (max_memory_restart in PM2)
- [ ] Logging doesn't block request handling
- [ ] Database indexes optimized
- [ ] N+1 queries eliminated
- [ ] Caching strategy implemented
- [ ] Monitoring and alerting configured

