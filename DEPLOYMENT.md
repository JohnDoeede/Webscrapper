# ContactCleaner - Deployment Guide

This guide covers deploying the ContactCleaner application to cloud platforms like Render, Heroku, Railway, and others.

## Quick Deploy to Render

### Option 1: One-Click Deploy (Recommended)

1. **Fork this repository** to your GitHub account
2. **Connect to Render**:
   - Go to [render.com](https://render.com)
   - Sign up/login with your GitHub account
   - Click "New +" → "Web Service"
   - Connect your forked repository

3. **Configure the deployment**:
   - **Name**: `contactcleaner` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - **Plan**: Free (or Starter for better performance)

4. **Environment Variables** (Render will auto-detect most):
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secret-key-here (auto-generated)
   UPLOAD_FOLDER=/tmp/uploads
   PYTHONUNBUFFERED=1
   ```

5. **Deploy**: Click "Create Web Service"

### Option 2: Using render.yaml (Auto-Deploy)

If you have the `render.yaml` file in your repository, Render will automatically configure everything:

1. Push the code with `render.yaml` to your GitHub repository
2. Connect the repository to Render
3. Render will automatically use the configuration from `render.yaml`

## Deployment to Other Platforms

### Heroku

1. **Install Heroku CLI** and login:
   ```bash
   heroku login
   ```

2. **Create Heroku app**:
   ```bash
   heroku create your-app-name
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex())')
   heroku config:set UPLOAD_FOLDER=/tmp/uploads
   ```

4. **Deploy**:
   ```bash
   git push heroku main
   ```

### Railway

1. **Connect GitHub repository** at [railway.app](https://railway.app)
2. **Deploy** - Railway will auto-detect Python and use requirements.txt
3. **Set environment variables** in Railway dashboard:
   - `FLASK_ENV=production`
   - `SECRET_KEY=your-secret-key`

### DigitalOcean App Platform

1. **Create new app** in DigitalOcean App Platform
2. **Connect GitHub repository**
3. **Configure**:
   - **Source Directory**: `/` (root)
   - **Build Command**: `pip install -r requirements.txt`
   - **Run Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`

## Troubleshooting Common Deployment Issues

### 1. Pandas Compilation Error (Main Issue)

**Problem**: `error: metadata-generation-failed` with pandas compilation

**Solutions**:

#### A. Use Pre-compiled Wheels (Implemented)
```txt
# Use older, stable versions with pre-compiled wheels
pandas==1.5.3
numpy==1.24.3
```

#### B. Alternative: Use Lightweight Dependencies
If pandas still fails, create a `requirements-minimal.txt`:
```txt
Flask==2.3.3
phonenumbers==8.13.11
gunicorn==21.2.0
```

Then use a pandas-free version with basic CSV processing.

#### C. Force Binary Installation
Add to requirements.txt:
```txt
--only-binary=all
```

### 2. Memory Issues During Build

**Problem**: Build runs out of memory

**Solutions**:
- Use smaller dependencies
- Upgrade to paid plan with more memory
- Split requirements into essential vs optional

### 3. Build Timeout

**Problem**: Build takes too long and times out

**Solutions**:
- Use pre-compiled wheels (already implemented)
- Cache dependencies (platform-specific)
- Remove unnecessary dependencies

### 4. File Upload Issues in Production

**Problem**: File uploads don't work in production

**Solutions**:
- Use `/tmp` directory for uploads (implemented)
- Set proper environment variables:
  ```
  UPLOAD_FOLDER=/tmp/uploads
  ```

### 5. Application Crashes on Startup

**Problem**: App fails to start

**Debug steps**:
1. Check logs: `heroku logs --tail` or Render dashboard
2. Verify all environment variables are set
3. Check Python version compatibility
4. Ensure gunicorn is installed

## Performance Optimization

### For Production Use

1. **Use a CDN** for static files (CSS, JS)
2. **Enable compression** in your web server
3. **Set up monitoring** (Sentry, etc.)
4. **Use environment-specific configs**:

```python
# In app.py
import os

# Production optimizations
if os.environ.get('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
```

### Database Alternative (Optional)

For high-traffic scenarios, consider replacing CSV storage with a database:

```python
# Example: PostgreSQL with SQLAlchemy
DATABASE_URL = os.environ.get('DATABASE_URL')
```

## Security Considerations

### Environment Variables (Required)

```bash
# Generate a secure secret key
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex())')
```

### File Upload Security

- File size limits (implemented: 16MB)
- File type validation (implemented: CSV only)
- Temporary file cleanup (implemented)

### HTTPS

All major platforms (Render, Heroku, Railway) provide HTTPS by default.

## Monitoring and Logs

### View Logs

**Render**: Dashboard → Service → Logs tab
**Heroku**: `heroku logs --tail`
**Railway**: Dashboard → Deployments → View Logs

### Common Log Messages

- `✅ Successfully read CSV with dtype=str` - CSV processing working
- `❌ Error reading CSV file` - Check file format
- `🚀 Running on port XXXX` - App started successfully

## Support

If you encounter deployment issues:

1. **Check the logs** first
2. **Verify environment variables** are set correctly
3. **Test locally** with production settings:
   ```bash
   FLASK_ENV=production python app.py
   ```
4. **Try minimal requirements** if pandas fails to install

## Cost Estimation

### Free Tiers
- **Render**: Free tier available (with limitations)
- **Heroku**: Free tier discontinued (paid plans start at $7/month)
- **Railway**: $5/month for starter plan
- **DigitalOcean**: $5/month for basic app

### Recommended for Production
- **Render Starter**: $7/month
- **Railway Pro**: $20/month
- **DigitalOcean Basic**: $5/month

Choose based on your traffic and storage needs.

---

## Quick Checklist

- [ ] Requirements.txt with compatible versions
- [ ] Runtime.txt with Python version
- [ ] Environment variables configured
- [ ] Gunicorn as WSGI server
- [ ] Upload folder set to `/tmp`
- [ ] Secret key generated
- [ ] Repository connected to platform
- [ ] Build and start commands specified

**Ready to deploy!** 🚀 