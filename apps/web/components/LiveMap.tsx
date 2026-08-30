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
  const popupsRef = useRef<Map<string, any>>(new Map());

  const initMap = useCallback(async () => {
    const maplibregl = (await import("maplibre-gl")) as any;
    const maplibreglInstance = maplibregl.default || maplibregl;
    await import("maplibre-gl/dist/maplibre-gl.css");

    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibreglInstance.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          "osm-tiles": {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          {
            id: "osm",
            type: "raster",
            source: "osm-tiles",
            paint: {
              "raster-opacity": 0.3,  // dark overlay feel
              "raster-saturation": -0.8,
              "raster-brightness-min": 0,
              "raster-brightness-max": 0.3,
            },
          },
        ],
      },
      center: [82.0, 23.5], // centre of India
      zoom: 4.5,
      maxZoom: 16,
    });

    mapRef.current = map;
  }, []);

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

  // Update markers whenever trains change
  useEffect(() => {
    const updateMarkers = async () => {
      const map = mapRef.current;
      if (!map) return;
      const maplibregl = (await import("maplibre-gl")) as any;
      const maplibreglInstance = maplibregl.default || maplibregl;

      const seen = new Set<string>();

      for (const train of trains) {
        if (train.latitude == null || train.longitude == null) continue;
        const key = train.train_number;
        seen.add(key);

        const color = DELAY_COLORS[train.status as keyof typeof DELAY_COLORS] ?? DELAY_COLORS.unknown;

        if (markersRef.current.has(key)) {
          // Move existing marker
          markersRef.current.get(key)!.setLngLat([train.longitude, train.latitude]);
          // Update colour by replacing element
          const el = markersRef.current.get(key)!.getElement();
          el.querySelector("img")!.src = trainSvg(color);
        } else {
          // Create new marker
          const el = document.createElement("div");
          el.style.cssText = "cursor:pointer;width:28px;height:28px;";
          const img = document.createElement("img");
          img.src = trainSvg(color);
          img.style.cssText = "width:28px;height:28px;transition:transform 0.15s;";
          img.onmouseenter = () => { img.style.transform = "scale(1.25)"; };
          img.onmouseleave = () => { img.style.transform = "scale(1)"; };
          el.appendChild(img);

          el.addEventListener("click", () => onTrainSelect(train));

          const marker = new maplibreglInstance.Marker({ element: el })
            .setLngLat([train.longitude, train.latitude])
            .addTo(map);
          markersRef.current.set(key, marker);
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
      style={{ background: "#080b14" }}
      id="map-container"
    />
  );
}
