# 🚀 SwasthAI Production Deployment Guide

## Overview

SwasthAI Anemia Detection API is now ready for production deployment. This guide covers deployment options on various platforms.

---

## 📋 Quick Start (Windows)

### 1. Start the Production Server

```bash
.\start_server.bat
```

The server will start on `http://0.0.0.0:5000` with:
- **Server**: Waitress WSGI (Windows-optimized)
- **Workers**: 4 threads
- **Timeout**: 120 seconds

### 2. Test the API

```bash
python test_comprehensive.py
```

Expected output:
```
✅ Status: 200
   Service: SwasthAI Anemia Detection API
   Model Loaded: True
```

---

## 🐧 Linux/Raspberry Pi Deployment

### 1. Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3-pip python3-venv

# Raspberry Pi (Raspberry Pi OS)
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv libatlas-base-dev libjasper-dev libharfbuzz0b
```

### 2. Setup Virtual Environment

```bash
cd SwasthAI_AnemiaModel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn waitress
```

### 3. Start the Server

```bash
chmod +x start_server.sh
./start_server.sh
```

Server will run on `http://0.0.0.0:5000` with Gunicorn (4 workers).

### 4. (Optional) Setup as Systemd Service

Create `/etc/systemd/system/swasthai-api.service`:

```ini
[Unit]
Description=SwasthAI Anemia Detection API
After=network.target

[Service]
Type=notify
User=swasthai
WorkingDirectory=/home/swasthai/SwasthAI_AnemiaModel
Environment="PATH=/home/swasthai/SwasthAI_AnemiaModel/.venv/bin"
ExecStart=/home/swasthai/SwasthAI_AnemiaModel/.venv/bin/gunicorn \
    --workers=4 \
    --bind=0.0.0.0:5000 \
    --timeout=120 \
    wsgi:app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable swasthai-api
sudo systemctl start swasthai-api
sudo systemctl status swasthai-api
```

---

## 🐳 Docker Deployment

### 1. Build Docker Image

```bash
docker build -t swasthai-api:latest .
```

### 2. Run Docker Container

**Single container:**
```bash
docker run -p 5000:5000 --name swasthai-api swasthai-api:latest
```

**With docker-compose:**
```bash
docker-compose up -d
docker-compose logs -f
```

### 3. Health Check

```bash
curl http://localhost:5000/health
```

---

## ☁️ Cloud Deployment

### AWS (EC2 + ECS)

1. **Create AMI with trained model**
```bash
# On EC2 instance
./start_server.sh
```

2. **Create ECS task definition**
```json
{
  "family": "swasthai-api",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "swasthai-api",
      "image": "YOUR_ECR_REPO/swasthai-api:latest",
      "portMappings": [{"containerPort": 5000}],
      "essential": true
    }
  ]
}
```

3. **Deploy**
```bash
aws ecs run-task --cluster swasthai --task-definition swasthai-api
```

### Google Cloud Run

```bash
gcloud run deploy swasthai-api \
    --source . \
    --platform managed \
    --memory 2Gi \
    --timeout 120 \
    --port 5000
```

### Heroku

```bash
heroku create swasthai-api
git push heroku main
heroku config:set FLASK_ENV=production
```

---

## 📊 API Endpoints

All endpoints are now available under the production server:

### Health Check
```bash
GET http://localhost:5000/health
```

### Single Prediction
```bash
POST http://localhost:5000/predict
  - image: <file>
  - scan_type: conjunctiva | fingernail
  - patient_id: <string>
```

### Base64 Prediction (Mobile)
```bash
POST http://localhost:5000/predict/b64
  - image_b64: <base64 string>
  - scan_type: conjunctiva | fingernail
  - patient_id: <string>
```

### Comprehensive Report
```bash
POST http://localhost:5000/report
  - conjunctiva_b64: <base64 image>
  - fingernail_b64: <base64 image>
  - patient_name: <string>
  - patient_age: <integer>
  - patient_gender: female | male
  - symptoms: [<list of symptoms>]
```

---

## 🔧 Configuration

### Production Settings (config.prod.ini)

```ini
DEBUG = False
TESTING = False
ENV = production
HOST = 0.0.0.0
PORT = 5000
WORKERS = 4
TIMEOUT = 120
```

### Performance Tuning

| Platform | Workers | Threads | Memory | Notes |
|----------|---------|---------|--------|-------|
| **Windows (Desktop)** | 1 | 4 | 2 GB | Use Waitress |
| **Linux (CPU: 2 cores)** | 2 | 2 | 2 GB | Use Gunicorn |
| **Linux (CPU: 4+ cores)** | 4 | 2 | 4 GB | Use Gunicorn |
| **Raspberry Pi 4** | 2 | 1 | 1 GB | Reduced workers |
| **Docker (High Performance)** | 8 | 2 | 4 GB | Scale replicas |

---

## 📈 Monitoring

### Health Checks

```bash
# Check API health
curl http://localhost:5000/health

# Docker health check
docker ps | grep swasthai-api

# Systemd status
sudo systemctl status swasthai-api
```

### Logs

```bash
# Windows
type nul > logs\api.log

# Linux/Raspberry Pi
tail -f logs/api.log

# Docker
docker-compose logs -f swasthai-api
```

### Performance Metrics

Monitor:
- **Response Time**: Should be 10-30ms per prediction
- **Memory Usage**: ~500 MB - 1 GB
- **CPU Usage**: 20-40% under normal load
- **Inference Throughput**: ~100-200 predictions/sec per worker

---

## 🔒 Security Best Practices

### 1. Use Environment Variables

```bash
export FLASK_ENV=production
export API_KEY=your_secret_key  # If implementing auth
```

### 2. Enable HTTPS (Production)

Use nginx as reverse proxy:

```nginx
upstream swasthai {
    server 127.0.0.1:5000;
}

server {
    listen 443 ssl;
    server_name api.swasthai.com;
    
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    
    location / {
        proxy_pass http://swasthai;
    }
}
```

### 3. Rate Limiting

```bash
# Install nginx rate limiting module
sudo apt-get install libnginx-mod-http-limit-conn-module
```

### 4. CORS Configuration

```python
# In api/app.py
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": ["https://yourdomain.com"]}})
```

---

## ✅ Deployment Checklist

- [ ] Virtual environment created and dependencies installed
- [ ] Model artifacts in `models/` directory
- [ ] `requirements.txt` updated for target platform
- [ ] Tested locally: `python test_comprehensive.py`
- [ ] All 4 endpoints returning 200 OK
- [ ] Production server starts without errors
- [ ] Health check endpoint responds
- [ ] Inference time < 50ms
- [ ] Logs are being written
- [ ] Memory usage monitored
- [ ] HTTPS configured (if public)
- [ ] Rate limiting enabled
- [ ] CORS configured
- [ ] Backup strategy in place

---

## 🆘 Troubleshooting

### "Module not found" Error

```bash
# Ensure you're in the correct directory
cd SwasthAI_AnemiaModel

# Verify virtual environment
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate.bat  # Windows
```

### "Port 5000 already in use"

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux
lsof -i :5000
kill -9 <PID>
```

### Low Inference Performance

- Check CPU usage (should be < 80%)
- Reduce batch size if processing multiple images
- Increase worker count (up to 2x CPU cores)
- Enable GPU acceleration if available

### Memory Leaks

```bash
# Monitor memory usage
watch -n 1 'ps aux | grep python'

# Restart service if needed
sudo systemctl restart swasthai-api
```

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Test API: `python test_comprehensive.py`
3. Verify model: `ls -lh models/swasthai_anemia.tflite`
4. Review docs: This guide

---

## 📄 License

SwasthAI © 2026. All rights reserved.

---

**Last Updated**: 2026-06-16
**Version**: 1.0.0
**Status**: ✅ Production Ready
