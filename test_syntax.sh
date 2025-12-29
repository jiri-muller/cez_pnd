#!/bin/bash
# Test script to verify Python syntax for all integration files

echo "Testing Python syntax for all files..."
echo ""

errors=0

for file in custom_components/cez_pnd/*.py; do
    if [ -f "$file" ]; then
        echo -n "Testing $file... "
        if python3 -m py_compile "$file" 2>/dev/null; then
            echo "✅"
        else
            echo "❌"
            python3 -m py_compile "$file"
            errors=$((errors + 1))
        fi
    fi
done

echo ""
if [ $errors -eq 0 ]; then
    echo "✅ All files passed syntax check!"
    exit 0
else
    echo "❌ $errors file(s) failed syntax check"
    exit 1
fi
