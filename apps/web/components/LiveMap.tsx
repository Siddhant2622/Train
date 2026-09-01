"use client";

import { useEffect, useRef, useCallback } from "react";
import { TrainSummary } from "@/lib/api";

interface LiveMapProps {
  trains: TrainSummary[];
  onTrainSelect: (train: TrainSummary) => void;
}

const DELAY_COLORS = {
  on_time: "#059669",
  delayed: "#d97706",
  severely_delayed: "#dc2626",
  unknown: "#475569",
};

// Minimal SVG train icon for markers
function trainSvg(color: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
      <circle cx="14" cy="14" r="13" fill="${color}" fill-opacity="0.9" stroke="white" stroke-width="1.5"/>
      <path d="M8 10h12a1 1 0 011 1v5a1 1 0 01-1 1H8a1 1 0 01-1-1v-5a1 1 0 011-1zm2 7v1m8-1v1M9 13h10" 
        stroke="white" stroke-width="1.4" stroke-linecap="round" fill="none"/>
    </svg>
  `)}`;
}

export default function LiveMap({ trains, onTrainSelect }: LiveMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<Map<string, any>>(new Map());

  const initMap = useCallback(async () => {
    const maplibregl = (await import("maplibre-gl")) as any;
    const maplibreglInstance = maplibregl.default || maplibregl;
    await import("maplibre-gl/dist/maplibre-gl.css");

    if (!mapContainerRef.current || mapRef.current) return;

    // If single train with valid coords, start centered on it
    const singleValid = trains.length === 1 && trains[0].latitude && trains[0].longitude && trains[0].latitude !== 0;
    const initialCenter: [number, number] = singleValid 
      ? [trains[0].longitude!, trains[0].latitude!] 
      : [79.5, 22.0];
    const initialZoom = singleValid ? 8.0 : 4.6;

    const map = new maplibreglInstance.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          "light-tiles": {
            type: "raster",
            tiles: [
              "https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
              "https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
              "https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
              "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            ],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors, © CARTO",
          },
        },
        layers: [
          {
            id: "light-base",
            type: "raster",
            source: "light-tiles",
            paint: {
              "raster-opacity": 1.0,
              "raster-saturation": 0.05,
              "raster-contrast": 0.05,
            },
          },
        ],
      },
      center: initialCenter,
      zoom: initialZoom,
      maxZoom: 17,
      minZoom: 3.5,
    });

    // Add navigation controls
    map.addControl(new maplibreglInstance.NavigationControl({ showCompass: false }), "top-right");

    mapRef.current = map;
  }, [trains]);

  // Initialise map once
  useEffect(() => {
    initMap();
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [initMap]);

  // Update markers and view whenever trains change
  useEffect(() => {
    const updateMarkers = async () => {
      const map = mapRef.current;
      if (!map) return;
      const maplibregl = (await import("maplibre-gl")) as any;
      const maplibreglInstance = maplibregl.default || maplibregl;

      const seen = new Set<string>();

      for (const train of trains) {
        if (train.latitude == null || train.longitude == null || (train.latitude === 0 && train.longitude === 0)) continue;
        const key = train.train_number;
        seen.add(key);

        const color = DELAY_COLORS[train.status as keyof typeof DELAY_COLORS] ?? DELAY_COLORS.unknown;
        const speedText = train.speed_kmh != null ? `${Math.round(train.speed_kmh)} km/h` : "Live";
        const titleText = `${train.train_number} ${train.name} (${speedText}) | Delay: +${Math.round(train.current_delay_min)}m`;

        if (markersRef.current.has(key)) {
          // Move existing marker
          markersRef.current.get(key)!.setLngLat([train.longitude, train.latitude]);
          const el = markersRef.current.get(key)!.getElement();
          const img = el.querySelector("img");
          if (img) img.src = trainSvg(color);
          el.title = titleText;
        } else {
          // Create new marker with pulsing shadow
          const el = document.createElement("div");
          el.style.cssText = "cursor:pointer;width:32px;height:32px;display:flex;align-items:center;justify-content:center;filter:drop-shadow(0 2px 6px rgba(0,0,0,0.35));";
          el.title = titleText;
          
          const img = document.createElement("img");
          img.src = trainSvg(color);
          img.style.cssText = "width:32px;height:32px;transition:transform 0.15s ease-out;";
          img.onmouseenter = () => { img.style.transform = "scale(1.3)"; };
          img.onmouseleave = () => { img.style.transform = "scale(1)"; };
          el.appendChild(img);

          el.addEventListener("click", () => onTrainSelect(train));

          const marker = new maplibreglInstance.Marker({ element: el })
            .setLngLat([train.longitude, train.latitude])
            .addTo(map);
          markersRef.current.set(key, marker);
        }

        // If single train detail view, smoothly ease map to train position
        if (trains.length === 1 && train.latitude && train.longitude) {
          map.easeTo({
            center: [train.longitude, train.latitude],
            duration: 1000,
          });
        }
      }

      // Remove stale markers
      for (const [key, marker] of markersRef.current) {
        if (!seen.has(key)) {
          marker.remove();
          markersRef.current.delete(key);
        }
      }
    };

    updateMarkers();
  }, [trains, onTrainSelect]);

  return (
    <div
      ref={mapContainerRef}
      className="h-full w-full"
      style={{ background: "#e2e8f0" }}
      id="map-container"
    />
  );
}
