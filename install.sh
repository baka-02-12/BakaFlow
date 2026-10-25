#!/bin/bash
echo "⛩️ Installing BakaFlow..."

if command -v apt-get &> /dev/null; then
    sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0
fi

mkdir -p ~/.local/share/bakaflow
mkdir -p ~/.local/share/applications

echo "Downloading BakaFlow script..."
curl -sL https://raw.githubusercontent.com/baka-02-12/BakaFlow/main/bakaflow.py -o ~/.local/share/bakaflow/bakaflow.py

cat > ~/.local/share/applications/bakaflow.desktop << EOF
[Desktop Entry]
Type=Application
Name=BakaFlow
Comment=Easing Curve Editor for EffectCraft
Exec=python3 $HOME/.local/share/bakaflow/bakaflow.py
Icon=applications-graphics
Terminal=false
EOF

chmod +x ~/.local/share/applications/bakaflow.desktop
update-desktop-database ~/.local/share/applications 2>/dev/null

echo "✅ Done! BakaFlow is now in your app menu."
