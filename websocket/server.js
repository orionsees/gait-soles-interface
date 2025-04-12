const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');
const wss = new WebSocket.Server({ port: process.env.PORT || 8080 });

// Client groups
const clients = {
  sensors: new Map(),    // ESP32 devices
  processors: new Map(), // Google Colab instances
  dashboards: new Map()  // Web dashboards
};

wss.on('connection', (ws) => {
  const clientId = uuidv4();
  let clientType = 'unknown';

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      
      // Client registration
      if (data.type === 'register') {
        clientType = data.role;
        switch(data.role) {
          case 'sensor':
            clients.sensors.set(clientId, ws);
            break;
          case 'processor':
            clients.processors.set(clientId, ws);
            break;
          case 'dashboard':
            clients.dashboards.set(clientId, ws);
            break;
        }
        console.log(`Registered ${clientType} client: ${clientId}`);
        return;
      }

      // Route sensor data to processors
      if (data.type === 'sensor') {
        clients.processors.forEach((processor, id) => {
          if (processor.readyState === WebSocket.OPEN) {
            processor.send(JSON.stringify({
              ...data,
              clientId,
              timestamp: Date.now()
            }));
          }
        });
      }

      // Route processed data to dashboards
      if (data.type === 'processed') {
        clients.dashboards.forEach((dashboard, id) => {
          if (dashboard.readyState === WebSocket.OPEN) {
            dashboard.send(JSON.stringify({
              ...data,
              processorId: clientId,
              timestamp: Date.now()
            }));
          }
        });
      }

    } catch (error) {
      console.error('Error processing message:', error);
    }
  });

  ws.on('close', () => {
    switch(clientType) {
      case 'sensor':
        clients.sensors.delete(clientId);
        break;
      case 'processor':
        clients.processors.delete(clientId);
        break;
      case 'dashboard':
        clients.dashboards.delete(clientId);
        break;
    }
    console.log(`${clientType} client disconnected: ${clientId}`);
  });
});

console.log(`WebSocket server running on port ${process.env.PORT || 8080}`);