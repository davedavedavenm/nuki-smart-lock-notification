#!/bin/bash
# Make all Nuki token troubleshooting scripts executable

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# List of scripts to make executable
SCRIPTS=(
    "token_curl_test.sh"
    "token_validator.py"
    "token_refresher.py"
    "token_manager.py"
)

echo "Making troubleshooting scripts executable..."

for script in "${SCRIPTS[@]}"; do
    script_path="${SCRIPT_DIR}/${script}"
    
    if [ -f "$script_path" ]; then
        chmod +x "$script_path"
        echo "✅ Made executable: $script"
    else
        echo "❌ Not found: $script"
    fi
done

echo -e "\nDone! You can now run these scripts directly:"
echo -e "- ./token_curl_test.sh        # Basic curl test for token validity"
echo -e "- ./token_validator.py        # Comprehensive token validation"
echo -e "- ./token_refresher.py        # Interactive token update utility"
echo -e "- ./token_manager.py          # Original token management tool\n"
