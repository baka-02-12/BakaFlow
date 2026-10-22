# ⛩️ BakaFlow

A lightweight, modern Easing Curve Editor for **EffectCraft**. 

BakaFlow lets you visually design cubic-bezier easing curves, preview them in real-time, and instantly apply them to your keyframes.

---

## ⚠️ Important: How to Start
For BakaFlow to communicate with EffectCraft, **you must launch EffectCraft from BakaFlow first.**

1. Open **BakaFlow** from your app menu.
2. Click the **"Launch EffectCraft"** button inside BakaFlow. 
3. This starts EffectCraft with the secure control channel (`--control 9877`) needed for them to talk to each other.
*(If you open EffectCraft normally without BakaFlow, the app won't connect and the status bar will say "No EC connection").*

---

## ✨ Features
- **Live Preview:** See exactly how your animation will feel with the built-in playback tool before applying it.
- **28 Built-in Presets:** Includes standard easings like Linear, Sine, Quad, Cubic, Expo, Circ, and Back.
- **Custom Presets:** Save your own curves and use them later.
- **Import / Export:** Share your custom curves with friends via JSON files.
- **Axis Control:** Apply easing to specific axes (X, Y, Z) without messing up the others.
- **Built-in Dark Mode:** A clean, Tokyo Night-inspired UI.

---

## 🎯 How the X / Y / Z Checkboxes Work
The axis checkboxes at the bottom let you control exactly what gets affected. 

- **All three checked (X, Y, Z):** Applies the curve directly to the property in place. **No separation.** (Perfect for 2D layers or when you want one curve for everything).
- **Partial (e.g., X and Y only):** BakaFlow will **separate** the vector dimensions in EffectCraft, and apply the curve *only* to the checked axes.
- **Already separated:** If you already separated the X, Y, Z tracks in EffectCraft, checking only "Y" will apply the curve *only* to the Y track. X and Z will keep whatever curve they had previously. 

*(Note: For 2D layers, if you want to apply the exact same curve to X and Y without separating the layer into 3 tracks, just check all three: X, Y, and Z).*

---

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

---

## 📥 Installation (Linux)

You can install BakaFlow with a single terminal command. 

Open your terminal and paste this:
```bash
curl -sL https://raw.githubusercontent.com/baka-02-12/BakaFlow/main/install.sh | bash
