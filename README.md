# ⛩️ BakaFlow

A lightweight, modern Easing Curve Editor for **EffectCraft**. BakaFlow lets you visually design cubic-bezier curves and instantly apply them to your keyframes.

## ⚠️ Important: How to Start
For BakaFlow to communicate with EffectCraft, **you must launch EffectCraft from BakaFlow first.**
1. Open **BakaFlow**.
2. Click the **"Launch EffectCraft"** button inside BakaFlow.
3. If you open EffectCraft normally, BakaFlow won't be able to connect.

## ✨ Features
- **Live Preview:** See exactly how your animation will feel.
- **28 Built-in Presets:** Linear, Sine, Quad, Cubic, Expo, Circ, Back, etc.
- **Custom Presets:** Save your own curves and share them as `.json` files.
- **Axis Control:** Apply easing to specific axes (X, Y, Z).
- **Dark Mode:** Clean, Tokyo Night-inspired UI.

## 🎯 How the X / Y / Z Checkboxes Work
- **All three checked:** Applies the curve in place. No separation.
- **Partial (e.g., X and Y):** Separates the vector dimensions in EffectCraft and applies the curve *only* to those axes.
- **Already separated:** Checking only "Y" will apply the curve *only* to the Y track. X and Z keep their previous curves.

## 💾 Saving & Sharing Presets
- **Save:** Adjust the curve, click **Save Preset** (bottom right).
- **Location:** `~/.config/bakaflow/custom_presets.json`
- **Share:** Go to the **Import/Export** tab, click **Export Library to File...**, and send the `.json` file to a friend.

## 📥 Installation

### 🐧 Linux (Easiest)
Open your terminal and paste this:
```bash
curl -sL https://raw.githubusercontent.com/baka-02-12/BakaFlow/main/install.sh | bash
```
*(It will ask for your password to install GTK).* Once done, search for **BakaFlow** in your app menu!

### 🍎 macOS
macOS does not have GTK installed by default. You will need [Homebrew](https://brew.sh/). 
Open your terminal and run:
```bash
brew install python3 gtk+3 pygobject3
```
Download `bakaflow_zoom.py` and run:
```bash
python3 bakaflow_zoom.py
```

### 🪟 Windows
Windows does not have Python or GTK installed by default.
1. Install [Python](https://www.python.org/downloads/) (Make sure to check **"Add Python to PATH"**).
2. Install GTK3 for Windows (via [MSYS2](https://www.msys2.org/)).
3. Download `bakaflow_zoom.py` and run it in Command Prompt:
```cmd
python bakaflow_zoom.py
```

---

## 🚀 Quick Start
1. Open **BakaFlow** and click **"Launch EffectCraft"**.
2. Select keyframes in EffectCraft.
3. Shape your curve in BakaFlow and pick your axes.
4. Click **APPLY EASING**.
