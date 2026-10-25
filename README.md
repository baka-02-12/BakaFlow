# ⛩️ BakaFlow

A lightweight, modern Easing Curve Editor for **EffectCraft**. 

BakaFlow lets you visually design cubic-bezier easing curves, preview them in real-time, and instantly apply them to your keyframes. It features a dual-graph system, allowing you to switch between **Value** (position) and **Speed** (velocity) graphs.

## ⚠️ Important: How to Start
For BakaFlow to communicate with EffectCraft, **you must launch EffectCraft from BakaFlow first.**

1. Open **BakaFlow** from your app menu.
2. Click the **"Launch EffectCraft"** button inside BakaFlow. 
3. This starts EffectCraft with the secure control channel (`--control 9877`) needed for them to talk to each other.

*(If you open EffectCraft normally without BakaFlow, the app won't connect and the status bar will say "No EC connection").*

## ✨ Features

### 📊 Dual Graph System
- **Value Graph:** Control the visual position curve. Features standard draggable handles (Blue for Out, Orange for In).
- **Speed Graph:** Control the velocity (derivative) curve. Perfect for creating snappy physics, impacts, and smooth motion.
- **Auto-Sync:** Changes made in the Value Graph instantly update the Speed Graph (and vice versa) using precise mathematical derivatives.

### 🎬 Professional Animation Tools
- **Interactive Playhead:** Click and drag anywhere on the graph to scrub through the animation and see live speed readings at any frame.
- **Play/Pause Preview:** Built-in animation preview with smooth 60fps playback.
- **Speed Presets:** Includes exclusive velocity-based presets like *Whip (Fast Start)*, *Slam (Fast End)*, *Hit Stop*, and *Elastic Bounce*.
- **28 Standard Presets:** Includes Linear, Sine, Quad, Cubic, Expo, Circ, and Back.
- **Axis Control:** Apply easing to specific axes (X, Y, Z) without messing up the others.

### ⚙️ Interface & Workflow
- **Advanced Controls:** Lock handles to the graph bounds, snap to grid (0.1), and Mirror mode for symmetric easing.
- **Custom Presets:** Save your own curves, import/export them as JSON files, and share them with others.
- **Scalable UI:** Built-in UI zoom (+ / -) and "Keep on Top" toggle.
- **Built-in Dark Mode:** A clean, Tokyo Night-inspired UI.

## 🎯 How the X / Y / Z Checkboxes Work
The axis checkboxes let you control exactly what gets affected. 

- **All three checked (X, Y, Z):** Applies the curve directly to the property in place. **No separation.** (Perfect for 2D layers or when you want one curve for everything).
- **Partial (e.g., X and Y only):** BakaFlow will **separate** the vector dimensions in EffectCraft, and apply the curve *only* to the checked axes.
- **Already separated:** If you already separated the X, Y, Z tracks in EffectCraft, checking only "Y" will apply the curve *only* to the Y track. X and Z will keep whatever curve they had previously. 

*(Note: For 2D layers, if you want to apply the exact same curve to X and Y without separating the layer into 3 tracks, just check all three: X, Y, and Z).*

## 💾 Saving & Sharing Presets
You can save your custom curves and share them with the community.

**How to Save:**
Adjust the curve in the graph, then click the **Save Preset** button in the bottom right corner. Give it a name, and it will appear in your "Presets" tab.

**Where is it saved?**
Your custom presets are safely stored on your computer at: 
`~/.config/bakaflow/custom_presets.json`

**How to Share with Friends:**
1. Go to the **Import/Export** tab in BakaFlow.
2. Click **Export Library to File...** 
3. Save the `.json` file and send it to your friend.
4. Your friend can go to their **Import/Export** tab and click **Import Library from File...** to instantly get all your curves!

## 📥 Installation

### 🐧 Linux (Easiest)
Open your terminal and paste this single command:
```bash
curl -sL https://raw.githubusercontent.com/baka-02-12/BakaFlow/main/install.sh | bash
```
*(It will ask for your password to install the required GTK dependencies).* Once it finishes, simply search for **BakaFlow** in your application menu to open it!

### 🍎 macOS
macOS does not have GTK installed by default. You will need [Homebrew](https://brew.sh/). 
Open your terminal and run:
```bash
brew install python3 gtk+3 pygobject3
```
Download `bakaflow.py` and run:
```bash
python3 bakaflow.py
```

### 🪟 Windows
Windows does not have Python or GTK installed by default.
1. Install [Python](https://www.python.org/downloads/) (Make sure to check **"Add Python to PATH"**).
2. Install GTK3 for Windows (via [MSYS2](https://www.msys2.org/)).
3. Download `bakaflow.py` and run it in Command Prompt:
```cmd
python bakaflow.py
```

## 🚀 Quick Start Guide
1. Open **BakaFlow** and click **"Launch EffectCraft"**.
2. Select the keyframes you want to edit in EffectCraft.
3. Choose your tab: **Value** (position) or **Speed** (velocity).
4. Drag the handles to shape your curve (or pick a preset).
5. Choose which axes you want to apply it to.
6. Click **APPLY VALUE** or **APPLY SPEED**.
