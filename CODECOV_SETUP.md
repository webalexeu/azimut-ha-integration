# Codecov Setup Guide

The coverage badge in the README will show "unknown" until you set up Codecov for your repository. Here's how to do it:

## Step 1: Sign up for Codecov

1. Go to https://codecov.io
2. Click "Sign up with GitHub"
3. Authorize Codecov to access your GitHub account

## Step 2: Add Your Repository

1. Once logged in, click on "Add new repository" or the "+" button
2. Find and select `azimut/azimut-ha-integration` from your repository list
3. Click to enable it

## Step 3: Get Your Upload Token

1. In Codecov, go to your repository settings
2. Navigate to the "General" tab
3. Copy the "Repository Upload Token"

## Step 4: Add Token to GitHub Secrets

1. Go to your GitHub repository: https://github.com/azimut/azimut-ha-integration
2. Click on **Settings** (top menu)
3. In the left sidebar, click on **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Set:
   - Name: `CODECOV_TOKEN`
   - Value: [paste the token you copied from Codecov]
6. Click **Add secret**

## Step 5: Push Your Changes

Once the token is added:

```bash
git add .
git commit -m "Add test coverage and badges"
git push
```

The CI will run, upload coverage to Codecov, and the badge will update automatically!

## Verification

After the CI completes:

1. Check the Actions tab on GitHub to see if the workflow succeeded
2. Visit https://codecov.io/gh/azimut/azimut-ha-integration to see your coverage report
3. The badge in README.md should now show your actual coverage percentage (86%)

## Optional: Alternative Badge URL

If you prefer not to set up Codecov right now, you can replace the Codecov badge in README.md with a static badge:

```markdown
[![Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen)](https://github.com/azimut/azimut-ha-integration)
```

This will show the current coverage without requiring Codecov setup.
