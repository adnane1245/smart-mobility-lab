import time
import traci
import orjson
import paho.mqtt.client as mqtt

CFG = "sumo/casablanca/casa_mini.sumocfg"

# MQTT (broker dans Docker, exposé sur 1883)
MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "casa/vehicles"  # casa/vehicles/<vehId>

def main():
    # 0) MQTT
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    print(f"📡 MQTT connected to {MQTT_HOST}:{MQTT_PORT}")

    # 1) SUMO via TraCI (Python contrôle, ne pas cliquer Play)
    sumo_cmd = [
        "sumo-gui",
        "-c", CFG,
        "--start",
        "--quit-on-end",
        "--step-length", "1.0",
    ]

    print("🚀 Starting SUMO from Python (TraCI)...")
    traci.start(sumo_cmd)
    print("✅ Connected. Running simulation (DO NOT click Play).")

    step = 0
    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            step += 1

            veh_ids = traci.vehicle.getIDList()

            # Etat toutes les 10s
            if step % 10 == 0:
                print(f"t={step:04d} | vehicles={len(veh_ids)}")

            for vid in veh_ids:
                speed_kmh = traci.vehicle.getSpeed(vid) * 3.6
                x, y = traci.vehicle.getPosition(vid)
                lon, lat = traci.simulation.convertGeo(x, y)  # (lon, lat)
                co2 = traci.vehicle.getCO2Emission(vid)
                waiting = traci.vehicle.getWaitingTime(vid)

                payload = {
                    "t": step,
                    "vehId": vid,
                    "speed_kmh": round(speed_kmh, 2),
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "co2_mg_s": round(co2, 2),
                    "waiting_s": round(waiting, 1),
                }

                topic = f"{MQTT_TOPIC_PREFIX}/{vid}"
                client.publish(topic, orjson.dumps(payload), qos=0)

            # preuve de publish toutes les 10s
            if step % 10 == 0 and veh_ids:
                print(f"📤 MQTT published for {len(veh_ids)} vehicles (sample topic: {MQTT_TOPIC_PREFIX}/{veh_ids[0]})")

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    finally:
        traci.close()
        client.loop_stop()
        client.disconnect()
        print("🔌 TraCI + MQTT closed")

if __name__ == "__main__":
    main()
