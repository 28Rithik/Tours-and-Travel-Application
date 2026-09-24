import random

class GenericGPSMockAPI:
    """
    Mocks a generic GPS provider API (like LocoNav, Fleetilla, etc).
    In a real scenario, this would fetch data based on vehicle.gps_imei.
    """
    
    @staticmethod
    def get_live_location(gps_imei):
        if not gps_imei:
            return {"status": "error", "message": "No GPS IMEI provided for this vehicle."}
            
        # Mocking a JSON response from a generic GPS tracking provider
        # Returning coordinates somewhere near Bangalore/Chennai
        lat = 12.9716 + random.uniform(-0.5, 0.5)
        lng = 77.5946 + random.uniform(-0.5, 0.5)
        speed = random.randint(0, 80)
        
        status = "moving" if speed > 0 else "parked"
        
        return {
            "status": "success",
            "data": {
                "imei": gps_imei,
                "latitude": lat,
                "longitude": lng,
                "speed_kmh": speed,
                "ignition_on": speed > 0,
                "vehicle_status": status,
                "last_updated": "Just now",
                "map_link": f"https://maps.google.com/?q={lat},{lng}"
            }
        }
