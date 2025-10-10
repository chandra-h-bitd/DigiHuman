# Environment Configuration

This project supports multiple environments with automatic CI/CD deployment.

## Environments

### Development
- **Branch**: `integratedWithCICD` 
- **URL**: Auto-deployed to Vercel preview URL
- **Purpose**: Testing new features and bug fixes

### Production  
- **Branch**: `master`
- **URL**: https://your-app.vercel.app (main production URL)
- **Purpose**: Live application for users

## Automatic Deployment

### When Code is Updated:

1. **Push to `integratedWithCICD`**:
   - ✅ Runs backend tests
   - ✅ Runs frontend tests  
   - ✅ Deploys to Vercel preview URL
   - ✅ You get a preview link to test changes

2. **Push to `master`**:
   - ✅ Runs all tests
   - ✅ Deploys to production URL
   - ✅ Live app is updated automatically

### CI/CD Pipeline:
```
Code Push → Tests Run → Tests Pass → Auto Deploy → Live URL Updated
```

## Local Development

### Backend:
```bash
cd backend
python app/main.py
```

### Frontend:  
```bash
cd frontend
npm start
```

## Configuration Files

### For Vercel Deployment:
- `vercel.json` - Deployment configuration
- `requirements.txt` - Python dependencies
- `package.json` - Build scripts

### For CI/CD:
- `.github/workflows/ci-cd.yml` - GitHub Actions pipeline
- Tests run automatically on every push
- Deployment happens only after tests pass

## API Configuration

The frontend automatically detects the environment:
- **Local**: Uses `http://localhost:8000`
- **Deployed**: Uses `/api` (relative URLs)

## Benefits

✅ **Automatic Testing**: Every code change is tested
✅ **Safe Deployments**: Only tested code goes live  
✅ **Preview Links**: Test changes before going live
✅ **Zero Downtime**: Seamless updates to live app
✅ **Rollback Ready**: Easy to revert if issues arise