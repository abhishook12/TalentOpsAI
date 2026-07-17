import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ComposableMap, Geographies, Geography, Marker, Annotation } from "react-simple-maps";
import { scaleLinear } from "d3-scale";
import { geoCentroid } from "d3-geo";
import api from "../services/api";

const geoUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

// FIPS to State Abbreviation
const fipsToState = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
  "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
  "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
  "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
  "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
  "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
  "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
  "55": "WI", "56": "WY"
};

const offsets = {
  VT: [50, -8],
  NH: [34, 2],
  MA: [30, -1],
  RI: [28, 2],
  CT: [35, 10],
  NJ: [34, 1],
  DE: [33, 0],
  MD: [47, 10],
  DC: [49, 21]
};

export default function USHeatmap() {
  const tooltipRef = React.useRef(null);
  const tooltipTitleRef = React.useRef(null);
  const tooltipValueRef = React.useRef(null);

  const { data: stateData, isLoading } = useQuery({
    queryKey: ["recruiters-by-state"],
    queryFn: async () => {
      const { data } = await api.get("/analytics/recruiters-by-state");
      return data;
    },
    staleTime: 60000,
  });

  const { dataMap, maxCount } = useMemo(() => {
    if (!stateData || !Array.isArray(stateData)) return { dataMap: {}, maxCount: 0 };
    const map = {};
    let max = 0;
    stateData.forEach((item) => {
      map[item.state] = item.count;
      if (item.count > max) max = item.count;
    });
    return { dataMap: map, maxCount: max };
  }, [stateData]);

  const colorScale = scaleLinear()
    .domain([0, maxCount || 1])
    .range(["#1e3a5f", "#f59e0b"]);

  const handleMouseMove = (e) => {
    // Keep tooltip relative to the map container by using nativeEvent offset
    const rect = e.currentTarget.getBoundingClientRect();
    let x = e.clientX - rect.left + 15;
    let y = e.clientY - rect.top + 15;

    if (tooltipRef.current) {
      // Use fixed generous dimensions because bounding rect might be stale before text paints
      const tooltipWidth = 140;
      const tooltipHeight = 60;

      if (x + tooltipWidth > rect.width) {
        x = e.clientX - rect.left - tooltipWidth - 10;
      }
      if (y + tooltipHeight > rect.height) {
        y = e.clientY - rect.top - tooltipHeight - 10;
      }
      
      // Prevent going off top or left edges
      if (x < 0) x = 10;
      if (y < 0) y = 10;

      tooltipRef.current.style.left = `${x}px`;
      tooltipRef.current.style.top = `${y}px`;
    }
  };

  return (
    <div 
      onMouseMove={handleMouseMove}
      style={{ 
        position: "relative", 
        width: "100%", 
        minHeight: "450px", 
        background: "#0b1221", 
        borderRadius: "14px", 
        border: "1px solid var(--card-border)", 
        display: "flex",
        flexDirection: "column"
      }}
    >
      <div style={{ padding: "18px 24px 0", flexShrink: 0 }}>
        <p style={{ margin: 0, fontSize: "10px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-muted)" }}>Geography</p>
        <h2 style={{ margin: "2px 0 0", fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>Recruiter Coverage by State</h2>
        <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-secondary)" }}>Choropleth of live recruiter density across the United States.</p>
        <div style={{ position: "absolute", top: 20, right: 20 }}>
          <span style={{ fontSize: "10px", fontWeight: "bold", border: "1px solid var(--card-border)", padding: "4px 8px", borderRadius: "100px", color: "var(--warning)" }}>LIVE</span>
        </div>
      </div>

      <div style={{ position: "relative", flexGrow: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {isLoading && <div style={{ position: "absolute", color: "var(--text-muted)", fontSize: "13px" }}>Scanning regions...</div>}
        
        <ComposableMap projection="geoAlbersUsa" style={{ width: "100%", height: "100%", maxHeight: "500px" }}>
          <Geographies geography={geoUrl}>
            {({ geographies }) => (
              <>
                {geographies.map((geo) => {
                  const stateAbbr = fipsToState[geo.id];
                  const count = dataMap[stateAbbr] || 0;
                  const fill = count > 0 ? colorScale(count) : "#141a25";

                  return (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      fill={fill}
                      stroke="#0b1221"
                      strokeWidth={1.5}
                      onMouseEnter={() => {
                        if (tooltipRef.current && tooltipTitleRef.current && tooltipValueRef.current) {
                          tooltipTitleRef.current.innerText = geo.properties.name;
                          tooltipValueRef.current.innerText = `${count} recruiter${count === 1 ? '' : 's'}`;
                          tooltipRef.current.style.opacity = 1;
                        }
                      }}
                      onMouseLeave={() => {
                        if (tooltipRef.current) {
                          tooltipRef.current.style.opacity = 0;
                        }
                      }}
                      style={{
                        default: { outline: "none", transition: "fill 250ms" },
                        hover: { fill: "#fcd34d", outline: "none", cursor: "pointer", transition: "fill 150ms" },
                        pressed: { outline: "none" },
                      }}
                    />
                  );
                })}
                
                {/* Overlay State Abbreviations */}
                {geographies.map((geo) => {
                  const centroid = geoCentroid(geo);
                  const stateAbbr = fipsToState[geo.id];
                  if (!stateAbbr) return null;

                  return (
                    <g key={`${geo.rsmKey}-name`} style={{ pointerEvents: 'none' }}>
                      {offsets[stateAbbr] ? (
                        <Annotation
                          subject={centroid}
                          dx={offsets[stateAbbr][0]}
                          dy={offsets[stateAbbr][1]}
                          connectorProps={{
                            stroke: "rgba(255,255,255,0.4)",
                            strokeWidth: 1,
                            strokeLinecap: "round"
                          }}
                        >
                          <text x={4} fontSize={8.5} fontWeight={700} alignmentBaseline="middle" fill="rgba(255,255,255,0.7)">
                            {stateAbbr}
                          </text>
                        </Annotation>
                      ) : (
                        <Marker coordinates={centroid}>
                          <text y="2" fontSize={10} fontWeight={800} textAnchor="middle" fill="rgba(255,255,255,0.7)">
                            {stateAbbr}
                          </text>
                        </Marker>
                      )}
                    </g>
                  );
                })}
              </>
            )}
          </Geographies>
        </ComposableMap>

        {/* Floating Tooltip */}
        <div
          ref={tooltipRef}
          style={{
            position: "absolute",
            background: "#0d1527",
            color: 'var(--text-primary)',
            padding: "8px 12px",
            borderRadius: "8px",
            fontSize: "12px",
            pointerEvents: "none",
            fontWeight: "600",
            border: "1px solid #1c2741",
            boxShadow: "0 8px 16px rgba(0,0,0,0.5)",
            whiteSpace: "pre-line",
            textAlign: "center",
            zIndex: 10,
            opacity: 0,
            transition: "opacity 150ms ease-in-out"
          }}
        >
          <span ref={tooltipTitleRef} style={{ color: "#94a3b8", fontSize: "10px", display: "block", marginBottom: "2px", textTransform: "uppercase" }}></span>
          <span ref={tooltipValueRef} style={{ color: "#f59e0b", fontSize: "13px" }}></span>
        </div>
      </div>

      {/* Legend */}
      <div style={{ position: "absolute", top: 56, right: 20, display: "flex", flexDirection: "column", alignItems: "center", gap: "8px", fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>
        <span>High ({maxCount})</span>
        <div style={{ width: "8px", height: "140px", background: "linear-gradient(to bottom, #f59e0b, #1e3a5f)", borderRadius: "8px" }} />
        <span>Low</span>
      </div>
    </div>
  );
}
