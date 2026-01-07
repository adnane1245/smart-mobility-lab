import os
import json
import paho.mqtt.client as mqtt
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WritePrecision

# MQTT
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "casa/vehicles/#")

# InfluxDB v2
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_ORG = os.getenv("INFLUX_ORG", "smartmobility")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "casablanca")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")

if not INFLUX_TOKEN:
    raise SystemExit("❌ INFLUX_TOKEN is empty. Do: export INFLUX_TOKEN='...token...'")

client_influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client_influx.write_api(write_options=SYNCHRONOUS)


def on_connect(client, userdata, flags, reason_code, properties):
    print("✅ MQTT connected -> subscribe")
    client.subscribe(MQTT_TOPIC)
    print(f"📥 Subscribed to {MQTT_TOPIC}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))

        # Debug RX
        print("�� RX", msg.topic, payload.get("vehId"), payload.get("t"))

        # t en secondes -> timestamp ns (démo)
        t = int(payload["t"])
        ts_ns = time.time_ns()

        p = (
            Point("vehicle_telemetry")
            .tag("vehId", str(payload["vehId"]))
            .field("speed_kmh", float(payload["speed_kmh"]))
            .field("lat", float(payload["lat"]))
            .field("lon", float(payload["lon"]))
            .field("co2_mg_s", float(payload["co2_mg_s"]))
            .field("waiting_s", float(payload["waiting_s"]))
            .time(ts_ns, WritePrecision.NS)
        )

        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=p,
            write_precision=WritePrecision.NS,
        )

        print("✅ WROTE", payload.get("vehId"), payload.get("t"))

    except Exception as e:
        print("❌ error:", repr(e))


def main():
    m = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    m.on_connect = on_connect
    m.on_message = on_message

    m.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    print(f"📥 MQTT listen {MQTT_HOST}:{MQTT_PORT} topic={MQTT_TOPIC}")
    print(f"🧱 Writing to InfluxDB {INFLUX_URL} org={INFLUX_ORG} bucket={INFLUX_BUCKET}")

    m.loop_forever()


if __name__ == "__main__":
    main()
