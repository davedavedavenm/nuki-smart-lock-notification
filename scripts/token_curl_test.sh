#!/bin/bash
# Direct curl test for Nuki API token
# Usage: ./token_curl_test.sh [TOKEN_VALUE_HERE]

# If token provided as argument, use it
if [ -n "$1" ]; then
  TOKEN="$1"
else
  # Otherwise, try to extract from credentials.ini
  CREDS_FILE="../config/credentials.ini"
  if [ -f "$CREDS_FILE" ]; then
    TOKEN=$(grep api_token "$CREDS_FILE" | cut -d '=' -f 2 | tr -d ' ')
    echo "Using token from credentials.ini"
  else
    echo "Error: No token provided and credentials.ini not found"
    exit 1
  fi
fi

# Display token info (masked for security)
TOKEN_LENGTH=${#TOKEN}
if [ $TOKEN_LENGTH -ge 10 ]; then
  MASKED_TOKEN="${TOKEN:0:5}...${TOKEN: -5}"
else
  MASKED_TOKEN="${TOKEN:0:2}...${TOKEN: -2}"
fi
echo "Using Token: $MASKED_TOKEN (length: $TOKEN_LENGTH)"

# Test API endpoints with curl
echo "=== Testing GET /account ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" \
  https://api.nuki.io/account)
echo "Response Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Account endpoint test: SUCCESS"
  ACCOUNT_SUCCESS=true
else
  echo "❌ Account endpoint test: FAILED"
  ACCOUNT_SUCCESS=false
fi

echo -e "\n=== Testing GET /smartlock ==="
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" \
  https://api.nuki.io/smartlock)
echo "Response Status: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Smartlock endpoint test: SUCCESS"
  SMARTLOCK_SUCCESS=true
else
  echo "❌ Smartlock endpoint test: FAILED"
  SMARTLOCK_SUCCESS=false
fi

# If at least one endpoint succeeded
if [ "$ACCOUNT_SUCCESS" = true ] || [ "$SMARTLOCK_SUCCESS" = true ]; then
  echo -e "\n✅ TOKEN APPEARS VALID, THE ISSUE MAY BE IN THE APPLICATION CODE"
else
  echo -e "\n❌ TOKEN APPEARS INVALID, PLEASE VERIFY ON NUKI WEB PORTAL"
  
  # Suggestions
  echo -e "\nSuggested steps:"
  echo "1. Login to Nuki Web (https://web.nuki.io/)"
  echo "2. Go to your account menu and select 'API'"
  echo "3. Verify existing tokens or generate a new one"
  echo "4. When generating a token, ensure ALL permissions are checked"
  echo "5. Copy the token carefully and update credentials.ini"
  echo "6. After updating, restart containers with 'docker compose down && docker compose up -d'"
fi
