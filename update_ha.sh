#!/bin/bash
# Script to update Home Assistant with latest integration files

echo "ČEZ PND Integration Update Script"
echo "=================================="
echo ""

# Find HA config directory
if [ -d "/config/custom_components/cez_pnd" ]; then
    HA_DIR="/config/custom_components/cez_pnd"
elif [ -d "/usr/share/hassio/homeassistant/custom_components/cez_pnd" ]; then
    HA_DIR="/usr/share/hassio/homeassistant/custom_components/cez_pnd"
elif [ -d "$HOME/.homeassistant/custom_components/cez_pnd" ]; then
    HA_DIR="$HOME/.homeassistant/custom_components/cez_pnd"
else
    echo "❌ Could not find Home Assistant cez_pnd directory!"
    echo ""
    echo "Please manually specify the path:"
    echo "  bash update_ha.sh /path/to/config/custom_components/cez_pnd"
    exit 1
fi

# Allow override
if [ ! -z "$1" ]; then
    HA_DIR="$1"
fi

echo "📂 Home Assistant directory: $HA_DIR"
echo "📂 Source directory: $(pwd)/custom_components/cez_pnd"
echo ""

# Backup
echo "📦 Creating backup..."
BACKUP_DIR="${HA_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
cp -r "$HA_DIR" "$BACKUP_DIR"
echo "✅ Backup created at: $BACKUP_DIR"
echo ""

# Update files
echo "📝 Updating files..."
cp -v custom_components/cez_pnd/api.py "$HA_DIR/"
cp -v custom_components/cez_pnd/config_flow.py "$HA_DIR/"
cp -v custom_components/cez_pnd/__init__.py "$HA_DIR/"
cp -v custom_components/cez_pnd/sensor.py "$HA_DIR/"
cp -v custom_components/cez_pnd/const.py "$HA_DIR/"
cp -v custom_components/cez_pnd/manifest.json "$HA_DIR/"
cp -v custom_components/cez_pnd/strings.json "$HA_DIR/"
echo ""

# Clear cache
echo "🗑️  Clearing Python cache..."
rm -rf "$HA_DIR/__pycache__"
rm -f "$HA_DIR"/*.pyc
echo "✅ Cache cleared"
echo ""

# Show what changed
echo "📊 File sizes:"
ls -lh "$HA_DIR"/*.py | awk '{print $9, $5}'
echo ""

echo "✅ Update complete!"
echo ""
echo "Next steps:"
echo "1. Restart Home Assistant: ha core restart"
echo "2. Remove old integration: Settings → Integrations → ČEZ PND → Remove"
echo "3. Re-add integration with credentials:"
echo "   Username: jiri.mull@gmail.com"
echo "   Password: B2.5dXJ5Ruj5VNG"
echo "   Device ID: 86180"
echo ""
echo "To restore backup if needed:"
echo "  rm -rf $HA_DIR && mv $BACKUP_DIR $HA_DIR"
