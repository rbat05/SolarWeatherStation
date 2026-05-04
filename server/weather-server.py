from flask import Flask, request

app = Flask(__name__)

@app.route('/api/weather', methods=['POST'])
def receive_weather_data():
    # The ESP8266 sends the raw CSV string:
    # Example: "Mon 10/02/2025 - 13:38:57,30.46,37.74,1012.07,4.13,98.00"
    raw_data = request.data.decode('utf-8')
    
    print(f"Received Weather Data: {raw_data}")
    
    # --- ADD YOUR CUSTOM LOGIC HERE ---
    # E.g., Split the string by commas and insert it into an SQLite or InfluxDB database!
    
    return "Data saved successfully", 200

if __name__ == '__main__':
    # Listen on all network interfaces on port 5000
    app.run(host='0.0.0.0', port=5000)
