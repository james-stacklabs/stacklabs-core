import { useState, useRef, useCallback } from "react";

const BOTS = [
  {
    id: "dot",
    name: "Dot",
    role: "Analytical",
    desc: "Stats, matchups, probabilities",
    color: "#00d4ff",
    bg: "rgba(0,212,255,0.08)",
    border: "rgba(0,212,255,0.25)",
    multi: true,
    icon: "◈",
  },
  {
    id: "barf",
    name: "B.A.R.F.",
    role: "Emotional homer",
    desc: "Pure Mets energy",
    color: "#FF6B35",
    bg: "rgba(255,107,53,0.08)",
    border: "rgba(255,107,53,0.25)",
    multi: false,
    teamLock: "NYM",
    icon: "🔥",
  },
  {
    id: "tomahawk",
    name: "Tom A. Hawk",
    role: "Braves loyalist",
    desc: "ATL through and through",
    color: "#CE1141",
    bg: "rgba(206,17,65,0.08)",
    border: "rgba(206,17,65,0.25)",
    multi: false,
    teamLock: "ATL",
    icon: "⚡",
  },
  {
    id: "phanatic",
    name: "Phanatic",
    role: "Chaos agent",
    desc: "Phillies tracker or Boggs mode",
    color: "#00C853",
    bg: "rgba(0,200,83,0.08)",
    border: "rgba(0,200,83,0.25)",
    multi: false,
    icon: "★",
    modes: ["phillies-track", "boggs-record"],
  },
  {
    id: "wavygravy",
    name: "Wavy Gravy",
    role: "NYM-SF specialist",
    desc: "Bay vibes meets Queens grit",
    color: "#B47AFF",
    bg: "rgba(180,122,255,0.08)",
    border: "rgba(180,122,255,0.25)",
    multi: false,
    icon: "〰",
  },
];

const ROOMS_INIT = [
  { id: "mets", name: "Mets Room", team: "NYM", color: "#FF5722", bots: [] },
  { id: "braves", name: "Braves Room", team: "ATL", color: "#CE1141", bots: [] },
];

const font = `'JetBrains Mono', monospace`;

const styles = {
  app: {
    fontFamily: font,
    minHeight: "100vh",
    background: "#08090d",
    color: "#e2e5ec",
    padding: "0",
  },
  header: {
    background: "linear-gradient(180deg, #101420 0%, #08090d 100%)",
    borderBottom: "1px solid #1a1f2e",
    padding: "20px 28px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "14px",
  },
  onAir: {
    background: "#ff1744",
    color: "#fff",
    fontSize: "9px",
    fontWeight: 700,
    letterSpacing: "2px",
    padding: "4px 10px",
    borderRadius: "2px",
    animation: "pulse 2s ease-in-out infinite",
  },
  title: {
    fontSize: "15px",
    fontWeight: 700,
    letterSpacing: "3px",
    textTransform: "uppercase",
    color: "#f0a500",
  },
  subtitle: {
    fontSize: "10px",
    color: "#555d74",
    letterSpacing: "1px",
  },
  gameInfo: {
    fontSize: "11px",
    color: "#8890a4",
    textAlign: "right",
  },
  body: {
    display: "flex",
    gap: "1px",
    background: "#1a1f2e",
    minHeight: "calc(100vh - 80px)",
  },
  bench: {
    width: "240px",
    background: "#0c0e14",
    padding: "16px",
    flexShrink: 0,
  },
  benchTitle: {
    fontSize: "9px",
    fontWeight: 600,
    color: "#555d74",
    letterSpacing: "1.5px",
    textTransform: "uppercase",
    marginBottom: "12px",
  },
  roomsArea: {
    flex: 1,
    display: "flex",
    gap: "1px",
    background: "#1a1f2e",
  },
  room: (color, isDragOver) => ({
    flex: 1,
    background: isDragOver ? "rgba(240,165,0,0.04)" : "#0c0e14",
    padding: "16px",
    borderTop: `3px solid ${isDragOver ? "#f0a500" : color}`,
    transition: "all 0.2s",
    minHeight: "400px",
  }),
  roomHeader: (color) => ({
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "16px",
    paddingBottom: "12px",
    borderBottom: "1px solid #1a1f2e",
  }),
  roomName: {
    fontSize: "13px",
    fontWeight: 600,
    letterSpacing: "1px",
    textTransform: "uppercase",
  },
  teamBadge: (color) => ({
    fontSize: "10px",
    fontWeight: 700,
    color: color,
    background: `${color}15`,
    border: `1px solid ${color}40`,
    padding: "3px 8px",
    borderRadius: "2px",
    letterSpacing: "1px",
  }),
  botCard: (bot, isDragging) => ({
    background: bot.bg,
    border: `1px solid ${isDragging ? bot.color : bot.border}`,
    padding: "12px 14px",
    marginBottom: "8px",
    cursor: "grab",
    transition: "all 0.15s",
    opacity: isDragging ? 0.5 : 1,
    borderRadius: "4px",
    position: "relative",
  }),
  botIcon: (color) => ({
    fontSize: "18px",
    marginRight: "10px",
    color: color,
    display: "inline-block",
    width: "24px",
    textAlign: "center",
  }),
  botName: (color) => ({
    fontSize: "12px",
    fontWeight: 600,
    color: color,
    letterSpacing: "0.5px",
  }),
  botRole: {
    fontSize: "10px",
    color: "#8890a4",
    marginTop: "2px",
  },
  botDesc: {
    fontSize: "10px",
    color: "#555d74",
    marginTop: "4px",
  },
  controls: {
    marginTop: "8px",
    display: "flex",
    gap: "6px",
    alignItems: "center",
    flexWrap: "wrap",
  },
  toggle: (active, color) => ({
    fontFamily: font,
    fontSize: "9px",
    fontWeight: 600,
    padding: "3px 8px",
    border: `1px solid ${active ? color : "#2a2f3e"}`,
    background: active ? `${color}20` : "transparent",
    color: active ? color : "#555d74",
    cursor: "pointer",
    letterSpacing: "0.5px",
    borderRadius: "2px",
    transition: "all 0.15s",
  }),
  select: {
    fontFamily: font,
    fontSize: "10px",
    padding: "3px 6px",
    background: "#08090d",
    border: "1px solid #2a2f3e",
    color: "#e2e5ec",
    borderRadius: "2px",
    cursor: "pointer",
  },
  dropHint: {
    border: "1px dashed #2a2f3e",
    borderRadius: "4px",
    padding: "20px",
    textAlign: "center",
    color: "#333a4d",
    fontSize: "10px",
    letterSpacing: "1px",
    textTransform: "uppercase",
  },
  footer: {
    background: "#0c0e14",
    borderTop: "1px solid #1a1f2e",
    padding: "14px 28px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  exportBtn: {
    fontFamily: font,
    fontSize: "11px",
    fontWeight: 600,
    padding: "8px 20px",
    border: "1px solid #f0a50040",
    background: "linear-gradient(135deg, rgba(240,165,0,0.12), rgba(240,165,0,0.04))",
    color: "#f0a500",
    cursor: "pointer",
    letterSpacing: "1px",
    textTransform: "uppercase",
    borderRadius: "2px",
    transition: "all 0.2s",
  },
  configPre: {
    fontFamily: font,
    fontSize: "10px",
    color: "#555d74",
    maxWidth: "500px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  statusDot: (active) => ({
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    background: active ? "#00d68f" : "#555d74",
    display: "inline-block",
    marginRight: "6px",
    animation: active ? "pulse 2s ease-in-out infinite" : "none",
  }),
  removeBtn: (color) => ({
    position: "absolute",
    top: "6px",
    right: "8px",
    background: "none",
    border: "none",
    color: "#555d74",
    cursor: "pointer",
    fontSize: "14px",
    padding: "2px 4px",
    lineHeight: 1,
    transition: "color 0.15s",
  }),
};

const BotCard = ({ bot, instanceId, location, onDragStart, onRemove, botState, onStateChange }) => {
  const [dragging, setDragging] = useState(false);
  const dragId = instanceId || bot.id;

  return (
    <div
      draggable
      onDragStart={(e) => {
        setDragging(true);
        e.dataTransfer.setData("text/plain", JSON.stringify({ botId: bot.id, from: location, instanceId: dragId }));
        onDragStart?.(dragId);
      }}
      onDragEnd={() => setDragging(false)}
      style={styles.botCard(bot, dragging)}
    >
      {location !== "bench" && (
        <button
          style={styles.removeBtn(bot.color)}
          onClick={() => onRemove?.(dragId, location)}
          title="Return to bench"
        >
          ×
        </button>
      )}
      <div style={{ display: "flex", alignItems: "center" }}>
        <span style={styles.botIcon(bot.color)}>{bot.icon}</span>
        <div>
          <div style={styles.botName(bot.color)}>{bot.name}</div>
          <div style={styles.botRole}>{bot.role}</div>
        </div>
      </div>
      <div style={styles.botDesc}>{bot.desc}</div>
      {location !== "bench" && (
        <div style={styles.controls}>
          <span style={styles.statusDot(botState?.active)} />
          <button
            style={styles.toggle(botState?.active, bot.color)}
            onClick={() => onStateChange(dragId, "active", !botState?.active)}
          >
            {botState?.active ? "LIVE" : "OFF"}
          </button>
          {bot.id === "dot" && (
            <select
              style={styles.select}
              value={botState?.teamContext || ""}
              onChange={(e) => onStateChange(dragId, "teamContext", e.target.value)}
            >
              <option value="NYM">NYM context</option>
              <option value="SF">SF context</option>
              <option value="ATL">ATL context</option>
            </select>
          )}
          {bot.id === "phanatic" && (
            <select
              style={styles.select}
              value={botState?.mode || "boggs-record"}
              onChange={(e) => onStateChange(dragId, "mode", e.target.value)}
            >
              <option value="phillies-track">Phillies tracker</option>
              <option value="boggs-record">Boggs record</option>
            </select>
          )}
          {bot.id === "dot" && (
            <select
              style={styles.select}
              value={botState?.model || "gemini-api"}
              onChange={(e) => onStateChange(dragId, "model", e.target.value)}
            >
              <option value="gemini-api">Gemini API</option>
              <option value="mistral">Mistral 7B</option>
              <option value="phi3">phi3:mini</option>
            </select>
          )}
          {bot.id !== "dot" && (
            <select
              style={styles.select}
              value={botState?.model || "gemini-api"}
              onChange={(e) => onStateChange(dragId, "model", e.target.value)}
            >
              <option value="gemini-api">Gemini API</option>
              <option value="mistral">Mistral 7B</option>
              <option value="phi3">phi3:mini</option>
            </select>
          )}
        </div>
      )}
    </div>
  );
};

const Room = ({ room, botInstances, onDrop, onRemove, botStates, onStateChange }) => {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      style={styles.room(room.color, dragOver)}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        try {
          const data = JSON.parse(e.dataTransfer.getData("text/plain"));
          onDrop(data, room.id);
        } catch {}
      }}
    >
      <div style={styles.roomHeader(room.color)}>
        <span style={styles.roomName}>{room.name}</span>
        <span style={styles.teamBadge(room.color)}>{room.team}</span>
      </div>
      {botInstances.length === 0 && (
        <div style={styles.dropHint}>Drag bots here</div>
      )}
      {botInstances.map((inst) => {
        const bot = BOTS.find((b) => b.id === inst.botId);
        if (!bot) return null;
        return (
          <BotCard
            key={inst.instanceId}
            bot={bot}
            instanceId={inst.instanceId}
            location={room.id}
            onRemove={onRemove}
            botState={botStates[inst.instanceId]}
            onStateChange={onStateChange}
          />
        );
      })}
    </div>
  );
};

export default function GreenRoom() {
  const [rooms, setRooms] = useState(ROOMS_INIT);
  const [assignments, setAssignments] = useState({});
  const [botStates, setBotStates] = useState({});
  const [exported, setExported] = useState(false);
  const idCounter = useRef(1);

  const getAssignedBotIds = useCallback(() => {
    const ids = [];
    Object.values(assignments).forEach((roomBots) => {
      roomBots.forEach((inst) => {
        if (!BOTS.find((b) => b.id === inst.botId)?.multi) {
          ids.push(inst.botId);
        }
      });
    });
    return ids;
  }, [assignments]);

  const handleDrop = useCallback(
    (data, targetRoom) => {
      const bot = BOTS.find((b) => b.id === data.botId);
      if (!bot) return;

      if (bot.teamLock) {
        const room = rooms.find((r) => r.id === targetRoom);
        if (room && room.team !== bot.teamLock) return;
      }

      if (data.from && data.from !== "bench") {
        setAssignments((prev) => {
          const next = { ...prev };
          next[data.from] = (next[data.from] || []).filter(
            (i) => i.instanceId !== data.instanceId
          );
          next[targetRoom] = [
            ...(next[targetRoom] || []),
            { botId: data.botId, instanceId: data.instanceId },
          ];
          return next;
        });
        return;
      }

      if (!bot.multi) {
        const assigned = getAssignedBotIds();
        if (assigned.includes(bot.id)) return;
      }

      const instanceId = `${bot.id}-${idCounter.current++}`;
      setAssignments((prev) => ({
        ...prev,
        [targetRoom]: [
          ...(prev[targetRoom] || []),
          { botId: bot.id, instanceId },
        ],
      }));
      const defaultTeam = rooms.find((r) => r.id === targetRoom)?.team || "NYM";
      setBotStates((prev) => ({
        ...prev,
        [instanceId]: {
          active: true,
          model: "gemini-api",
          teamContext: defaultTeam,
          mode: bot.modes ? bot.modes[0] : undefined,
        },
      }));
    },
    [rooms, getAssignedBotIds]
  );

  const handleRemove = useCallback((instanceId, roomId) => {
    setAssignments((prev) => ({
      ...prev,
      [roomId]: (prev[roomId] || []).filter((i) => i.instanceId !== instanceId),
    }));
    setBotStates((prev) => {
      const next = { ...prev };
      delete next[instanceId];
      return next;
    });
  }, []);

  const handleStateChange = useCallback((instanceId, key, value) => {
    setBotStates((prev) => ({
      ...prev,
      [instanceId]: { ...prev[instanceId], [key]: value },
    }));
  }, []);

  const assignedNonMulti = getAssignedBotIds();

  const buildConfig = () => {
    const config = { rooms: {} };
    rooms.forEach((room) => {
      config.rooms[room.id] = {
        name: room.name,
        team: room.team,
        bots: (assignments[room.id] || []).map((inst) => ({
          id: inst.botId,
          instanceId: inst.instanceId,
          ...botStates[inst.instanceId],
        })),
      };
    });
    return config;
  };

  const handleExport = async () => {
    const config = buildConfig();
    const json = JSON.stringify(config, null, 2);
    try {
      await fetch("http://clio.taila01894.ts.net:8006/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: json
      });
      setExported(true);
      setTimeout(() => setExported(false), 2000);
    } catch (err) {
      console.error("Failed to save config", err);
    }
  };

  return (
    <div style={styles.app}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { margin:0; padding:0; box-sizing:border-box; }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:#08090d; }
        ::-webkit-scrollbar-thumb { background:#2a2f3e; border-radius:2px; }
      `}</style>

      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.onAir}>PRE-GAME</span>
          <div>
            <div style={styles.title}>Green Room</div>
            <div style={styles.subtitle}>FanStack bot configuration</div>
          </div>
        </div>
        <div style={styles.gameInfo}>
          <div style={{ color: "#e2e5ec", fontWeight: 600 }}>NYM @ SF</div>
          <div>9:45 PM ET — Oracle Park</div>
        </div>
      </div>

      <div style={styles.body}>
        <div style={styles.bench}>
          <div style={styles.benchTitle}>Bot bench</div>
          {BOTS.map((bot) => {
            const isAssigned =
              !bot.multi && assignedNonMulti.includes(bot.id);
            return (
              <div
                key={bot.id}
                style={{ opacity: isAssigned ? 0.3 : 1, pointerEvents: isAssigned ? "none" : "auto" }}
              >
                <BotCard bot={bot} location="bench" />
              </div>
            );
          })}
        </div>

        <div style={styles.roomsArea}>
          {rooms.map((room) => (
            <Room
              key={room.id}
              room={room}
              botInstances={assignments[room.id] || []}
              onDrop={handleDrop}
              onRemove={handleRemove}
              botStates={botStates}
              onStateChange={handleStateChange}
            />
          ))}
        </div>
      </div>

      <div style={styles.footer}>
        <div style={styles.configPre}>
          {Object.entries(assignments).map(([roomId, bots]) => (
            <span key={roomId} style={{ marginRight: "16px" }}>
              <span style={{ color: "#8890a4" }}>
                {rooms.find((r) => r.id === roomId)?.name}:
              </span>{" "}
              <span style={{ color: "#e2e5ec" }}>
                {bots.map((b) => BOTS.find((x) => x.id === b.botId)?.name).join(", ") || "empty"}
              </span>
            </span>
          ))}
        </div>
        <button
          style={{
            ...styles.exportBtn,
            ...(exported ? { borderColor: "#00d68f40", color: "#00d68f" } : {}),
          }}
          onClick={handleExport}
        >
          {exported ? "Saved to disk" : "Save config"}
        </button>
      </div>
    </div>
  );
}
