#!/bin/bash
set -e

# Configuration
API_BASE_URL="http://localhost:8000/api/v1"
EMAIL="admin@example.com"
PASSWORD="change-this-password"
# Use environment variable TEST_URL if set, otherwise default
TEST_URL="${TEST_URL:-https://example.com}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing Doogie Chat Bot API with Fetch Tool${NC}"
echo "=================================="

# Function to check if jq is installed
check_dependencies() {
  if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed. Please install it to run this script.${NC}"
    echo "On Ubuntu/Debian: sudo apt-get install jq"
    echo "On macOS: brew install jq"
    exit 1
  fi
}

# Step 1: Login to get token
login() {
  echo -e "${BLUE}Step 1: Logging in to get auth token...${NC}"
  
  echo "Attempting login using form data..."
  LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE_URL}/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${EMAIL}&password=${PASSWORD}")
  
  echo "Debug - Form login response: ${LOGIN_RESPONSE}"
  TOKEN=$(echo $LOGIN_RESPONSE | jq -r .access_token)
  
  if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
    echo -e "${RED}Login failed. Response:${NC}"
    echo $LOGIN_RESPONSE | jq .
    exit 1
  fi
  
  echo -e "${GREEN}Successfully logged in${NC}"
}

# Step 2: Create a new chat
create_chat() {
  echo -e "${BLUE}Step 2: Creating a new chat...${NC}"
  
  # Create a temporary file for the JSON payload
  PAYLOAD_FILE=$(mktemp)
  echo "{\"title\":\"Fetch Tool Test\"}" > $PAYLOAD_FILE
  
  CHAT_RESPONSE=$(curl -s -X POST "${API_BASE_URL}/chats" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    --data @$PAYLOAD_FILE)
  
  # Clean up
  rm $PAYLOAD_FILE
  
  CHAT_ID=$(echo $CHAT_RESPONSE | jq -r .id)
  
  if [[ -z "$CHAT_ID" || "$CHAT_ID" == "null" ]]; then
    echo -e "${RED}Failed to create chat. Response:${NC}"
    echo $CHAT_RESPONSE | jq .
    exit 1
  fi
  
  echo -e "${GREEN}Successfully created chat with ID: ${CHAT_ID}${NC}"
}

# Step 3: Send a message that should trigger the fetch tool
test_fetch_tool() {
  echo -e "${BLUE}Step 3: Testing fetch tool with URL ${TEST_URL}...${NC}"
  
  MESSAGE="I need you to use your fetch tool to retrieve the content from ${TEST_URL}. Do not explain JavaScript fetch API, use your actual fetch tool capability."
  
  echo "Sending message: \"${MESSAGE}\""
  
  # This uses the GET stream endpoint which works well with curl
  STREAM_URL="${API_BASE_URL}/chats/${CHAT_ID}/stream?content=$(echo "$MESSAGE" | jq -sRr @uri)"
  
  echo "Requesting stream from: ${STREAM_URL}"
  
  echo -e "${BLUE}Processing stream response...${NC}"
  
  # Process the entire stream
  stream_output=$(curl -s -N \
    -H "Authorization: Bearer ${TOKEN}" \
    "${STREAM_URL}")
    
  # Check for errors during curl
  if [ $? -ne 0 ]; then
      echo -e "${RED}Curl command failed to connect or timed out.${NC}"
      exit 1
  fi

  # Use process substitution and jq to analyze the stream
  found_tool_call=false
  stream_completed=false
  final_content=""
  
  echo "$stream_output" | while IFS= read -r line; do
      if [[ $line == data:* ]]; then
          json_data=${line#data: }
          echo "Stream Event: $json_data" # Log each event
          
          # Check for tool call delta
          if echo "$json_data" | jq -e '.tool_calls_delta | length > 0' > /dev/null; then
              echo -e "${GREEN}Tool call delta detected in stream.${NC}"
              found_tool_call=true
          fi
          
          # Accumulate content from delta chunks
          content_delta=$(echo "$json_data" | jq -r '.content // ""')
          if [[ -n "$content_delta" ]]; then
              final_content+="$content_delta"
          fi

          # Check for final 'done' flag
          if echo "$json_data" | jq -e '.done == true' > /dev/null; then
              echo -e "${GREEN}Stream completed.${NC}"
              stream_completed=true
              # Optionally capture final usage stats or finish reason here
              finish_reason=$(echo "$json_data" | jq -r '.finish_reason // "unknown"')
              echo "Finish Reason: $finish_reason"
          fi
      fi
  done
  
  if [ "$stream_completed" = false ]; then
      echo -e "${RED}Stream did not complete properly.${NC}"
      # Optionally exit or continue to verification anyway
  fi

  # --- Add delay before verification ---
  echo -e "${BLUE}Waiting 8 seconds for background task to complete...${NC}" # Increased wait
  sleep 8 # Increased wait
  # --- End delay ---

  # --- Verification Step (After Stream Completion) ---
  echo -e "${BLUE}Verifying database messages after stream completion...${NC}"

  MESSAGES_RESPONSE=$(curl -s -X GET "${API_BASE_URL}/chats/${CHAT_ID}/messages" \
    -H "Authorization: Bearer ${TOKEN}")
    
  echo "Full messages response from DB:"
  echo "$MESSAGES_RESPONSE" | jq .
  
  # Verify expected messages using jq
  user_message_exists=$(echo "$MESSAGES_RESPONSE" | jq -e '.[] | select(.role=="user") | length > 0')
  assistant_tool_call_exists=$(echo "$MESSAGES_RESPONSE" | jq -e '.[] | select(.role=="assistant" and .tool_calls != null) | length > 0')
  tool_result_exists=$(echo "$MESSAGES_RESPONSE" | jq -e '.[] | select(.role=="tool") | length > 0')
  final_assistant_message_exists=$(echo "$MESSAGES_RESPONSE" | jq -e '.[] | select(.role=="assistant" and .tool_calls == null and .content != null and .content != "") | length > 0')

  verification_passed=true
  
  if [ "$user_message_exists" != "true" ]; then
      echo -e "${RED}Verification FAILED: User message not found.${NC}"
      verification_passed=false
  else
      echo -e "${GREEN}Verification PASSED: User message found.${NC}"
  fi
  
  if [ "$found_tool_call" = true ]; then
      if [ "$assistant_tool_call_exists" != "true" ]; then
          echo -e "${RED}Verification FAILED: Assistant message with tool_calls not found in DB.${NC}"
          verification_passed=false
      else
           echo -e "${GREEN}Verification PASSED: Assistant message with tool_calls found.${NC}"
      fi
      
      if [ "$tool_result_exists" != "true" ]; then
          echo -e "${RED}Verification FAILED: Tool result message not found in DB.${NC}"
          verification_passed=false
      else
           echo -e "${GREEN}Verification PASSED: Tool result message found.${NC}"
      fi
      
      if [ "$final_assistant_message_exists" != "true" ]; then
          echo -e "${RED}Verification FAILED: Final assistant message (after tool execution) not found in DB.${NC}"
          verification_passed=false
      else
           echo -e "${GREEN}Verification PASSED: Final assistant message found.${NC}"
      fi
  else
      echo -e "${YELLOW}Verification SKIPPED for tool messages as no tool call was detected in stream.${NC}"
      # Check if at least a simple assistant response exists if no tool call happened
      if [ "$final_assistant_message_exists" != "true" ]; then
           echo -e "${RED}Verification FAILED: No final assistant message found (and no tool call occurred).${NC}"
           verification_passed=false
      else
           echo -e "${GREEN}Verification PASSED: Simple assistant message found.${NC}"
      fi
  fi
  
  if [ "$verification_passed" = false ]; then
      echo -e "${RED}Overall verification failed.${NC}"
      exit 1 # Exit with error if verification fails
  fi
}

# Run the test
check_dependencies
login
create_chat
test_fetch_tool

echo -e "${GREEN}Test completed!${NC}"
echo "=================================="
echo "To continue testing, visit the chat in the UI:"
echo "Chat ID: ${CHAT_ID}"
