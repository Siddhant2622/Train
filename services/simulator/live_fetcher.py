import asyncio
import httpx
import logging
import os
import json
from datetime import datetime, timezone, date
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] fetcher: %(message)s")
logger = logging.getLogger(__name__)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
INTERNAL_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-key-change-in-production")
FETCH_INTERVAL = 45  # seconds

RAILRADAR_API_KEY = os.getenv("RAILRADAR_API_KEY", "rg_34e07a358bde431c8be60a796a7edd89")
RAPIDAPI_KEYS = [k.strip() for k in os.getenv("RAPIDAPI_KEYS", "").split(",") if k.strip()]


async def fetch_train_live_status(client: httpx.AsyncClient, train_number: str) -> dict | None:
    """Fetch live train status from RailRadar (Tier 1) or RapidAPI (Tier 2)."""
    # 1. Try RailRadar
    if RAILRADAR_API_KEY:
        try:
            url = f"https://api.railradar.in/v1/trains/{train_number}/live"
            resp = await client.get(url, headers={"Authorization": f"Bearer {RAILRADAR_API_KEY}"}, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                if data and data.get("currentLocation"):
                    cur = data["currentLocation"]
                    st_status = cur.get("status") or "departed"
                    is_h = st_status == "at-station"
                    avg_sp = float(data.get("train", {}).get("avgSpeed") or 82.0)
                    delay = float(data.get("delayMinutes") or cur.get("delayMinutes") or 0.0)
                    next_h = data.get("nextHalt") or {}
                    
                    return {
                        "delay_minutes": delay,
                        "current_station_code": cur.get("stationCode"),
                        "next_station_code": next_h.get("stationCode"),
                        "distance_to_next_km": max(1.0, float(next_h.get("distance") or 30.0) - float(cur.get("distanceFromOriginKm") or 0.0)),
                        "speed_kmh": 0.0 if is_h else avg_sp,
                        "is_halted": is_h,
                        "source": "railradar_live"
                    }
        except Exception as e:
            logger.debug(f"RailRadar fetch for {train_number} failed: {e}")

    # 2. Try RapidAPI IRCTC
    if RAPIDAPI_KEYS:
        for key in RAPIDAPI_KEYS:
            for start_day in (0, 1):
                try:
                    url = f"https://irctc1.p.rapidapi.com/api/v1/liveTrainStatus?trainNo={train_number}&startDay={start_day}"
                    headers = {
                        "X-RapidAPI-Key": key,
                        "X-RapidAPI-Host": "irctc1.p.rapidapi.com"
                    }
                    resp = await client.get(url, headers=headers, timeout=8.0)
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        if data and (data.get("success") or data.get("train_number")):
                            return {
                                "latitude": float(data.get("cur_stn_lat") or 0.0),
                                "longitude": float(data.get("cur_stn_lng") or 0.0),
                                "speed_kmh": float(data.get("avg_speed") or 78.0),
                                "delay_minutes": float(data.get("delay") or 0.0),
                                "current_station_code": data.get("current_station_code") or data.get("current_station_name"),
                                "next_station_code": data.get("upcoming_stations", [{}])[0].get("station_code") if data.get("upcoming_stations") else None,
                                "distance_to_next_km": float(data.get("ahead_distance") or (data.get("upcoming_stations", [{}])[0].get("distance_from_current_station") or 30.0)),
                                "is_halted": bool(data.get("at_src") or data.get("at_dstn") or (data.get("halt", 0) > 0)),
                                "source": "rapidapi_live"
                            }
                    elif resp.status_code in (403, 429):
                        break
                except Exception as e:
                    logger.debug(f"RapidAPI fetch for {train_number} failed: {e}")

    return None


async def process_live_data(client: httpx.AsyncClient):
    """Fetches real live data for active trains and broadcasts updates."""
    today = date.today().isoformat()
    now = datetime.now(timezone.utc)

    try:
        trains_resp = await client.get(f"{API_BASE}/api/v1/trains?page_size=50")
        trains_resp.raise_for_status()
        trains_list = trains_resp.json().get("trains", [])
    except Exception as e:
        logger.error(f"Failed to fetch train list from API: {e}")
        return

    if not trains_list:
        logger.warning("No trains found to track.")
        return

    for t in trains_list:
        t_num = t["train_number"]
        # Trigger detailed live fetch via API
        try:
            detail_resp = await client.get(f"{API_BASE}/api/v1/trains/{t_num}", timeout=10.0)
            if detail_resp.status_code == 200:
                d = detail_resp.json()
                pos = d.get("position")
                if pos:
                    logger.info(f"Live Track {t_num} ({d.get('name')}): {pos.get('speed_kmh')} km/h, {pos.get('current_delay_min')}m delay at {pos.get('last_station')} (Next: {pos.get('next_station')})")
        except Exception as e:
            logger.debug(f"Error refreshing {t_num}: {e}")
        
        await asyncio.sleep(0.2)


async def main():
    logger.info("Starting RailPredict Live Telemetry Daemon...")
    async with httpx.AsyncClient() as client:
        while True:
            await process_live_data(client)
            await asyncio.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
