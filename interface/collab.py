import websocket
import json
import time
from pymongo import MongoClient
from datetime import datetime

# Configuration
WEBSOCKET_URL = "wss://gait-soles-interface.onrender.com/ws"
MONGO_URI = "mongodb+srv://Harshad:gaitsoles12345@cluster0.s5ksuc8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "sensorData"
COLLECTION_NAME = "readings"
RECONNECT_DELAY = 5  # Seconds between connection attempts

class SensorProcessor:
    def __init__(self):
        self.ws = None
        self.mongo_client = None
        self.db = None
        self.collection = None
        self.connected = False

    def connect_mongo(self):
        """Connect to MongoDB Atlas"""
        try:
            # Default Atlas SRV URI uses TLS by default
            self.mongo_client = MongoClient(MONGO_URI)

            # If you need to disable TLS validation (development only), use:
            # self.mongo_client = MongoClient(
            #     MONGO_URI,
            #     tls=True,
            #     tlsAllowInvalidCertificates=True
            # )

            self.db = self.mongo_client[DB_NAME]
            self.collection = self.db[COLLECTION_NAME]
            print("Successfully connected to MongoDB")
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
            raise

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            if data.get('type') == 'sensor':
                print(f"Received sensor data: {data['timestamp']}")

                # Process data
                processed_data = self.process_data(data)

                # Store in MongoDB
                self.store_data(processed_data)

                # Send acknowledgement
                ack = {
                    "type": "ack",
                    "original_timestamp": data['timestamp'],
                    "processed_timestamp": datetime.utcnow().isoformat()
                }
                ws.send(json.dumps(ack))

        except Exception as e:
            print(f"Message handling error: {e}")

    def process_data(self, raw_data):
        """Process raw sensor data"""
        processed = {
            "metadata": {
                "received_at": datetime.utcnow().isoformat(),
                "processing_note": "Basic conversion"
            },
            "sensors": raw_data['data'],
            "original_timestamp": raw_data['timestamp'],
            "status": "processed"
        }

        # Simple stats
        values = list(raw_data['data'].values())
        processed['stats'] = {
            "average": sum(values) / len(values) if values else 0,
            "max": max(values) if values else 0,
            "min": min(values) if values else 0
        }

        return processed

    def store_data(self, data):
        """Store processed data in MongoDB"""
        try:
            result = self.collection.insert_one(data)
            print(f"Stored document ID: {result.inserted_id}")
            return True
        except Exception as e:
            print(f"Database storage error: {e}")
            return False

    def on_error(self, ws, error):
        print(f"WebSocket Error: {error}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed: {close_msg} (code: {close_status_code})")
        self.connected = False

    def on_open(self, ws):
        print("Connected to WebSocket server")
        self.connected = True
        # Register as processor
        ws.send(json.dumps({
            "type": "register",
            "role": "processor"
        }))

    def connect_websocket(self):
        """Initialize WebSocket connection"""
        self.ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

    def run(self):
        """Main processing loop"""
        print("Starting sensor processor...")

        # Connect to MongoDB first
        self.connect_mongo()

        # Maintain connection
        while True:
            try:
                if not self.connected:
                    print("Connecting to WebSocket server...")
                    self.connect_websocket()
                    # Run WebSocket in blocking mode (TLS defaults)
                    self.ws.run_forever()
                else:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Shutting down...")
                break
            except Exception as e:
                print(f"Connection error: {e}")
                print(f"Reconnecting in {RECONNECT_DELAY} seconds...")
                time.sleep(RECONNECT_DELAY)

if __name__ == "__main__":
    processor = SensorProcessor()
    processor.run()
