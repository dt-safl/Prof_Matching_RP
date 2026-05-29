# Deployment Guide

## Files Required for Deployment

### Essential Files
- `app.py` - Main Streamlit application
- `requirements.txt` - Python dependencies
- `Procfile` - Heroku deployment configuration
- `.streamlit/config.toml` - Streamlit configuration for deployment
- All Python modules: `config.py`, `agenda.py`, `utils.py`, etc.

### Configuration Files
- `.env.production` - Template for environment variables (don't commit real keys)
- `.gitignore` - Excludes sensitive files from Git

### Data Files (if needed)
- `data/enriched_profiles.json` - Your processed data (if static)
- `data/iith_cse_faculty.csv` - Faculty data (if needed)

## Deployment Options

### 1. Streamlit Cloud (Recommended for Streamlit apps)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set environment variables in the Streamlit Cloud dashboard:
   - `GROQ_API_KEY`: Your Groq API key
   - `OPENALEX_MAILTO`: Your email for OpenAlex API

### 2. Heroku

1. Install Heroku CLI
2. Create a new Heroku app: `heroku create your-app-name`
3. Set environment variables:
   ```bash
   heroku config:set GROQ_API_KEY=your_actual_key
   heroku config:set OPENALEX_MAILTO=your_email@domain.com
   ```
4. Deploy: `git push heroku main`

### 3. Railway

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Railway will auto-detect and deploy your Streamlit app

## Before Deployment

1. **Test locally**: `streamlit run app.py`
2. **Remove sensitive data**: Ensure no API keys are in code
3. **Check data paths**: Make sure all file paths work in deployment environment
4. **Test with production environment variables**

## Environment Variables Required

- `GROQ_API_KEY`: Required for LLM functionality
- `OPENALEX_MAILTO`: Optional, for OpenAlex API politeness

## Post-Deployment

1. Test all functionality in the deployed app
2. Monitor logs for any errors
3. Update data files as needed

## Troubleshooting

- If imports fail: Check all Python files are included
- If data not found: Verify file paths and data directory structure
- If API errors: Check environment variables are set correctly