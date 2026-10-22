# ⛩️ BakaFlow

A lightweight, modern Easing Curve Editor for **EffectCraft**. 

BakaFlow lets you visually design cubic-bezier easing curves and instantly apply them to your keyframes.

## ⚠️ Important: How to Start
For BakaFlow to communicate with EffectCraft, **you must launch EffectCraft from BakaFlow first.**

1. Open **BakaFlow** from your app menu.
2. Click the **"Launch EffectCraft"** button inside BakaFlow.
3. This starts EffectCraft with the secure control channel (`--control 9877`) needed for them to talk to each other.
*(If you open EffectCraft normally without BakaFlow, it won't connect!)*

## ✨ Features
- **Live Preview:** See exactly how your animation will feel with the built-in playback tool.
- **28 Built-in Presets:** Includes Linear, Sine, Quad, Cubic, Expo, Circ, and Back easings.
- **Custom Presets:** Save your own curves, import/export them as JSON, and share them with others.
- **Built-in Dark Mode:** Easy on the eyes.

## 🎯 How the X / Y / Z Checkboxes Work
The axis checkboxes let you apply different curves to different axes without overwriting your work.

- **All three checked (X, Y, Z):** Applies the curve directly to the property in place. **No separation.** (Use this for 2D layers or when you want one curve for everything).
- **Partial (e.g., X and Y only):** BakaFlow will **separate** the vector dimensions in EffectCraft, and apply the curve *only* to the checked axes.
- **Already separated:** If you already separated the X, Y, Z tracks, checking only "Y" will apply the curve *only* to the Y track. X and Z will keep whatever curve they had previously.

## 📥 Installation (Linux)

You can install BakaFlow with a single terminal command. 

Open your terminal and paste this:
```bash
curl -sL https://raw.githubusercontent.com/baka-02-12/BakaFlow/main/install.sh | bash
