# 6thGear - GitHub Actions Build Guide

## 🚀 How to Build Your APK Automatically

### Step 1: Create a GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `sixthgear` (or anything you want)
3. Make it **Public** or **Private**
4. Click **Create repository**

### Step 2: Upload This Project

```bash
# In your terminal, navigate to this project folder
cd 6thgear_flutter_project

# Initialize git
git init
git add .
git commit -m "Initial 6thGear commit"

# Connect to your GitHub repo (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/sixthgear.git
git branch -M main
git push -u origin main
```

### Step 3: Add Your Google Maps API Key (Required for Maps)

1. Get a free API key from [Google Cloud Console](https://console.cloud.google.com/)
2. In your GitHub repo, go to **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `GOOGLE_MAPS_API_KEY`
5. Value: Paste your actual API key
6. Click **Add secret**

### Step 4: Trigger the Build

**Option A - Push to main:**
```bash
git push origin main
```

**Option B - Manual trigger:**
1. Go to your GitHub repo
2. Click **Actions** tab
3. Click **6thGear - Build Android APK**
4. Click **Run workflow** → **Run workflow**

### Step 5: Download Your APK

1. Wait ~10 minutes for the build to complete
2. Go to **Actions** tab → Click the latest workflow run
3. Scroll down to **Artifacts**
4. Download `6thGear-APK-1` (or whatever the build number is)
5. Unzip it → You now have `app-release.apk`

### Step 6: Install on Your Phone

1. Transfer `app-release.apk` to your Android phone
2. Enable **Install from Unknown Sources** in Settings
3. Tap the APK to install

---

## 📦 What Gets Built

| Output | Location | Purpose |
|---|---|---|
| `app-release.apk` | Download from Artifacts | Install directly on any Android phone |
| `app-release.aab` | Download from Artifacts | Upload to Google Play Store |

---

## 🔧 Optional: Add Firebase (for push notifications, analytics)

1. Create a Firebase project at [firebase.google.com](https://firebase.google.com)
2. Add an Android app with package name: `com.sixthgear.app`
3. Download `google-services.json`
4. In GitHub repo: **Settings → Secrets → New repository secret**
5. Name: `FIREBASE_OPTIONS`
6. Value: Open `google-services.json` in a text editor, copy ALL contents, paste here
7. Next build will include Firebase

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| Build fails with "No GOOGLE_MAPS_API_KEY" | Add the secret in GitHub Settings |
| "flutter analyze" fails | I need to finish the remaining screen files first |
| APK won't install | Enable "Install from Unknown Sources" in Android Settings |
| Maps show blank | Your API key needs Maps SDK enabled in Google Cloud Console |

---

## 📱 App Features

- **Smart Navigation** - Real-time traffic, speed cameras, pothole alerts
- **Safety First** - One-tap SOS, fake call, live location sharing
- **Women Safety** - Emergency features designed for women drivers
- **Drive Analytics** - Score tracking, fuel efficiency, trip history
- **Fuel Prices** - Live prices across all Indian cities
- **Toll Calculator** - Route-based toll costs with FASTag support
- **Night Mode HUD** - Heads-up display for safe night driving
- **RTO Documents** - Track expiry dates, renewals, DigiLocker integration

---

**Built with ❤️ for Bharat**
