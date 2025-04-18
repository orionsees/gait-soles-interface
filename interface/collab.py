import json
import asyncio
import websockets
import pandas as pd
from datetime import datetime
from google.colab import output

# WebSocket server URL
SERVER_URL = "wss://gait-soles-interface.onrender.com/ws"

# Create an empty DataFrame to store the data
data_log = pd.DataFrame(columns=['timestamp', 'client_id', 'message', 'value'])

async def connect_websocket():
    global data_log
    print("Connecting to WebSocket server...")
    try:
        async with websockets.connect(SERVER_URL) as websocket:
            # Register as a processor client
            register_message = {
                "type": "register",
                "role": "processor"
            }
            await websocket.send(json.dumps(register_message))
            print("✅ Registered as processor client")
            print("Waiting for real-time messages from ESP32...")
            
            # Keep listening for messages in real-time
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                # Get current timestamp
                current_time = datetime.now()
                timestamp_str = current_time.strftime('%H:%M:%S')
                
                # Extract data
                client_id = data.get('clientId', 'unknown')
                msg = data.get('message', 'No message')
                value = data.get('value', 'No value')
                
                # Add data to DataFrame
                new_row = pd.DataFrame({
                    'timestamp': [current_time],
                    'client_id': [client_id],
                    'message': [msg],
                    'value': [value]
                })
                data_log = pd.concat([data_log, new_row], ignore_index=True)
                
                # Clear previous output for cleaner display
                output.clear()
                
                # Print received data
                print(f"⏰ {timestamp_str} - Real-time message received:")
                print(f"  From sensor: {client_id}")
                print(f"  Message: {msg}")
                print(f"  Value: {value}")
                print("-" * 50)
                
                # Display the last 5 entries in the data log
                print("\nData Log (Last 5 entries):")
                display(data_log.tail(5))
                
                # Optional: Process and send back results immediately
                processed_data = {
                    "type": "processed",
                    "message": f"Processed: {msg}",
                    "originalValue": value,
                    "processedValue": value * 2 if isinstance(value, (int, float)) else value  # Simple processing
                }
                
                # Send processed data back to server
                await websocket.send(json.dumps(processed_data))
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Save the complete data log to CSV when connection ends
        if not data_log.empty:
            filename = f"gait_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            data_log.to_csv(filename, index=False)
            print(f"Data log saved to {filename}")

# Run the async function in a separate thread
from IPython.display import display, HTML

print("Starting WebSocket client...")
display(HTML("""
<div>
    <button onclick='google.colab.kernel.invokeFunction("button_click", [], {})' 
            style="background-color:#f44336;color:white;padding:10px 15px;border:none;border-radius:4px;cursor:pointer;">
        Stop Connection
    </button>
    <button onclick='google.colab.kernel.invokeFunction("save_data", [], {})' 
            style="background-color:#4CAF50;color:white;padding:10px 15px;border:none;border-radius:4px;cursor:pointer;margin-left:10px;">
        Save Data Now
    </button>
</div>
"""))

def button_click():
    import os
    print("Stopping connection and saving data...")
    os._exit(0)  # Force stop the execution

def save_data():
    global data_log
    if not data_log.empty:
        filename = f"gait_data_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        data_log.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
    else:
        print("No data to save yet")

output.register_callback('button_click', button_click)
output.register_callback('save_data', save_data)

# Run the WebSocket client
await connect_websocket()
