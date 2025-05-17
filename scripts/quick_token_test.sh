#!/bin/bash
# Quick Nuki API token test using curl
# Safer implementation for older Python versions

# Find the config directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_DIR="${SCRIPT_DIR}/../config"

# Allow overriding config directory with environment variable
if [ -n "$CONFIG_DIR" ]; then
  CONFIG_DIR="$CONFIG_DIR"
fi

# Check if credentials file exists
CREDS_FILE="${CONFIG_DIR}/credentials.ini"
if [ ! -f "$CREDS_FILE" ]; then
  echo "Error: Credentials file not found at $CREDS_FILE"
  exit 1
fi

# Extract token from credentials file
TOKEN=$(grep api_token "$CREDS_FILE" | cut -d '=' -f 2 | tr -d ' \t\r\n')

# Check if token was found
if [ -z "$TOKEN" ]; then
  echo "Error: No API token found in credentials file"
  exit 1
fi

# Display token info (masked for security)
TOKEN_LENGTH=${#TOKEN}
if [ $TOKEN_LENGTH -ge 10 ]; then
  MASKED_TOKEN="${TOKEN:0:5}...${TOKEN: -5}"
else
  MASKED_TOKEN="${TOKEN:0:2}...${TOKEN: -2}"
fi
echo "Using Token: $MASKED_TOKEN (length: $TOKEN_LENGTH)"

# Test various API endpoints
echo -e "\n=== Testing GET /smartlock ==="
HTTP_CODE=$(curl -s -o /tmp/nuki_response.txt -w "%{http_code}" -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" \
  https://api.nuki.io/smartlock)
echo "Response Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Smartlock endpoint test: SUCCESS"
  SMARTLOCK_COUNT=$(grep -o "smartlockId" /tmp/nuki_response.txt | wc -l)
  echo "Found $SMARTLOCK_COUNT smartlocks in your account"
  
  # If we found smartlocks, try to get logs for the first one
  if [ $SMARTLOCK_COUNT -gt 0 ]; then
    # Extracting the first smartlock ID is complex in bash
    # Use a simplified approach for this script
    echo -e "\n=== Testing GET /smartlock/ID/log (using explicit ID) ==="
    HTTP_CODE=$(curl -s -o /tmp/nuki_logs.txt -w "%{http_code}" -X GET \
      -H "Authorization: Bearer $TOKEN" \
      -H "Accept: application/json" \
      https://api.nuki.io/smartlock/18255246837/log)
    echo "Response Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
      echo "✅ Logs endpoint test: SUCCESS"
      LOG_COUNT=$(grep -o "{" /tmp/nuki_logs.txt | wc -l)
      echo "Retrieved approximately $LOG_COUNT log entries"
    else
      echo "❌ Logs endpoint test: FAILED"
      cat /tmp/nuki_logs.txt
    fi
  fi
else
  echo "❌ Smartlock endpoint test: FAILED"
  cat /tmp/nuki_response.txt
fi

# Cleanup temp files
rm -f /tmp/nuki_response.txt /tmp/nuki_logs.txt

# Print recommendations based on results
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "\n✅ BASIC API ACCESS IS WORKING"
  echo "The token has access to the Nuki API and can retrieve smartlock information."
else
  echo -e "\n❌ API ACCESS IS NOT WORKING"
  echo -e "\nRECOMMENDED ACTIONS:"
  echo "1. Generate a new token in the Nuki Web portal (https://web.nuki.io/)"
  echo "2. When generating the token, ensure ALL permissions are checked"
  echo "3. Copy the token carefully (use the copy button if available)"
  echo "4. Run './token_refresher.py' to update your token"
  echo "5. Restart Docker containers: 'docker compose down && docker compose up -d'"
fi
