import React, { useEffect, useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  StatusBar,
  ActivityIndicator,
} from "react-native";

const SUPABASE_URL = "https://tnhvexohouzzycgzscxl.supabase.co";
const SUPABASE_KEY = "sb_publishable_WsWNdDvKgO5Tcuu6U0X30g_Xk_-xRtn";

const HEADERS = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
  "Content-Type": "application/json",
  Prefer: "return=representation",
};

type BotStatusRow = {
  is_active?: boolean;
  balance?: number;
  daily_profit?: number;
  positions?: number;
  current_price?: number;
  signal?: string;
  entry_price?: number;
  tp_price?: number;
  sl_price?: number;
  signal_reason?: string;
  last_log?: string;
  updated_at?: string;
};

export default function Home() {
  const [status, setStatus] = useState<BotStatusRow>({});
  const [connected, setConnected] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [symbol, setSymbol] = useState("XAUUSD");
  const [mode, setMode] = useState<"SCRIPT" | "LIVE">("LIVE");
  const [activeTab, setActiveTab] = useState<"HOME" | "SCRIPTS" | "SETTINGS">("HOME");
  const [localLogs, setLocalLogs] = useState<string[]>([
    "[bot.py] Neural core initialized...",
    "Connecting to Supabase telemetry...",
  ]);

  const symbols = ["XAUUSD", "USDJPY", "NAS100", "US30"];
  const isRunning = Boolean(status.is_active);

  const appendLog = (msg: string) => {
    const time = new Date().toTimeString().split(" ")[0];
    setLocalLogs((prev) => [...prev.slice(-4), `${time} ${msg}`]);
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${SUPABASE_URL}/rest/v1/bot_status?id=eq.1&select=*`, {
        headers: HEADERS,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data && data[0]) {
        setStatus(data[0]);
        setConnected(true);
      }
    } catch (e: any) {
      setConnected(false);
      appendLog(`Sync error: ${e?.message || "Connection failed"}`);
    }
  };

  useEffect(() => {
    fetchStatus();
    const timer = setInterval(fetchStatus, 5000);
    return () => clearInterval(timer);
  }, []);

  const toggleBot = async (nextActive: boolean) => {
    setLoading(true);
    try {
      const logMsg = nextActive
        ? "[bot.py] Started from ALGOMAX Pocket"
        : "[bot.py] Stopped from ALGOMAX Pocket";

      const res = await fetch(`${SUPABASE_URL}/rest/v1/bot_status?id=eq.1`, {
        method: "PATCH",
        headers: HEADERS,
        body: JSON.stringify({
          is_active: nextActive,
          last_log: logMsg,
          updated_at: new Date().toISOString(),
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data && data[0]) {
        setStatus(data[0]);
        setConnected(true);
        appendLog(logMsg);
      }
    } catch (e: any) {
      appendLog(`Command failed: ${e?.message || "Error"}`);
    } finally {
      setLoading(false);
    }
  };

  const balanceText = `$${Number(status.balance || 0).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

  const pnl = Number(status.daily_profit || 0);
  const pnlText = `${pnl >= 0 ? "+$" : "-$"}${Math.abs(pnl).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

  return (
    <SafeAreaView style={s.container}>
      <StatusBar barStyle="light-content" backgroundColor="#070b14" />

      <ScrollView contentContainerStyle={s.scroll}>
        {/* ヘッダー */}
        <View style={s.topHeader}>
          <View>
            <Text style={s.brand}>BOT-X // ALGOMAX</Text>
            <Text style={s.headerTitle}>Create & Deploy your Trading Bot</Text>
          </View>
          <View style={s.bellBadge}>
            <Text style={s.bellText}>AI</Text>
          </View>
        </View>

        {/* AIロボットビジュアルエリア */}
        <View style={s.heroCard}>
          <View style={s.hudGrid}>
            <View style={s.hudCol}>
              <Text style={s.hudLabel}>PAIR</Text>
              <Text style={s.hudValue}>{symbol}</Text>
              <Text style={s.hudLabel}>PRICE</Text>
              <Text style={s.hudValue}>
                {status.current_price ? status.current_price.toFixed(2) : "---"}
              </Text>
            </View>

            {/* ロボットコア（画像を置く場合はここを <Image source={require('../assets/robot.png')} style={s.robotImg} /> に変更） */}
            <View style={s.coreRingOuter}>
              <View style={s.coreRingInner}>
                <View style={s.eyeRow}>
                  <View style={s.cyberEye} />
                  <View style={s.cyberEye} />
                </View>
                <Text style={s.coreTag}>X-CORE</Text>
              </View>
            </View>

            <View style={s.hudCol}>
              <Text style={s.hudLabel}>SIGNAL</Text>
              <Text
                style={[
                  s.hudValue,
                  status.signal === "BUY"
                    ? s.green
                    : status.signal === "SELL"
                    ? s.red
                    : s.cyan,
                ]}
              >
                {status.signal || "WAIT"}
              </Text>
              <Text style={s.hudLabel}>MODE</Text>
              <Text style={s.hudValue}>{mode}</Text>
            </View>
          </View>
        </View>

        {/* メイン操作カード */}
        <View style={s.controlCard}>
          <View style={[s.statusPill, isRunning ? s.pillActive : s.pillStopped]}>
            <Text style={s.statusPillText}>{isRunning ? "ACTIVE" : "STOPPED"}</Text>
          </View>

          <Text style={s.botName}>AUTO TRADER X</Text>
          <Text style={s.botSub}>LIQUIDITY HUNTER · {symbol}</Text>

          {/* 3つのサブ操作ボタン */}
          <View style={s.actionRow}>
            <TouchableOpacity
              style={[s.chipBtn, mode === "SCRIPT" && s.chipBtnActive]}
              onPress={() => {
                setMode("SCRIPT");
                appendLog("Switched view: SCRIPT (bot.py)");
              }}
            >
              <Text style={s.chipText}>SCRIPT</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[s.chipBtn, mode === "LIVE" && s.chipBtnActive]}
              onPress={() => {
                setMode("LIVE");
                appendLog("Switched mode: LIVE TELEMETRY");
              }}
            >
              <Text style={s.chipText}>LIVE</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={s.chipBtnDanger}
              disabled={loading || !isRunning}
              onPress={() => toggleBot(false)}
            >
              <Text style={s.chipText}>STOP EA</Text>
            </TouchableOpacity>
          </View>

          {/* RUN BOT.PY メインボタン */}
          <TouchableOpacity
            style={[s.runButton, isRunning && s.runButtonActive]}
            disabled={loading}
            onPress={() => toggleBot(!isRunning)}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={s.runButtonText}>
                {isRunning ? "BOT.PY RUNNING (TAP TO PAUSE)" : "RUN BOT.PY"}
              </Text>
            )}
          </TouchableOpacity>

          {/* コンソールログ */}
          <View style={s.consoleBox}>
            {status.last_log ? (
              <Text style={s.consoleHighlight}>{status.last_log}</Text>
            ) : null}
            {status.signal_reason ? (
              <Text style={s.consoleLine}>• {status.signal_reason}</Text>
            ) : null}
            {localLogs.map((line, i) => (
              <Text key={i} style={s.consoleLine}>
                {line}
              </Text>
            ))}
          </View>

          <Text style={s.serverFooter}>
            {connected === true
              ? "● SERVER CONNECTED (SUPABASE LIVE)"
              : connected === false
              ? "● SERVER DISCONNECTED"
              : "● CONNECTING TO SERVER..."}
          </Text>
        </View>

        {/* 通貨ペア切替 */}
        <View style={s.sectionCard}>
          <Text style={s.sectionLabel}>TARGET SYMBOL</Text>
          <View style={s.symbolRow}>
            {symbols.map((item) => (
              <TouchableOpacity
                key={item}
                style={[s.symbolBtn, symbol === item && s.symbolBtnSelected]}
                onPress={() => {
                  setSymbol(item);
                  appendLog(`Target symbol set to ${item}`);
                }}
              >
                <Text style={s.symbolText}>{item}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* 口座・損益サマリー */}
        <View style={s.metricsRow}>
          <View style={s.metricBox}>
            <Text style={s.sectionLabel}>BALANCE</Text>
            <Text style={s.metricValue}>{balanceText}</Text>
          </View>
          <View style={s.metricBox}>
            <Text style={s.sectionLabel}>TODAY P&L</Text>
            <Text style={[s.metricValue, pnl >= 0 ? s.green : s.red]}>{pnlText}</Text>
          </View>
        </View>

        {/* シグナル詳細（TP / SL） */}
        {(status.entry_price || status.tp_price || status.sl_price) ? (
          <View style={s.sectionCard}>
            <Text style={s.sectionLabel}>ACTIVE ORDER LEVELS</Text>
            <View style={s.levelsRow}>
              <Text style={s.levelText}>ENTRY: {status.entry_price || "-"}</Text>
              <Text style={[s.levelText, s.green]}>TP: {status.tp_price || "-"}</Text>
              <Text style={[s.levelText, s.red]}>SL: {status.sl_price || "-"}</Text>
            </View>
          </View>
        ) : null}

        {/* 下部アクションボタン */}
        <TouchableOpacity
          style={s.neonAddBtn}
          onPress={() => {
            fetchStatus();
            appendLog("Manual sync triggered.");
          }}
        >
          <Text style={s.neonAddBtnText}>+  SYNC BOT / REFRESH TELEMETRY</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* ボトムナビゲーション */}
      <View style={s.bottomNav}>
        {(["HOME", "SCRIPTS", "SETTINGS"] as const).map((tab) => (
          <TouchableOpacity
            key={tab}
            style={s.navBtn}
            onPress={() => setActiveTab(tab)}
          >
            <Text style={[s.navText, activeTab === tab && s.navTextActive]}>{tab}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#070b14",
  },
  scroll: {
    padding: 16,
    paddingTop: 22,
    paddingBottom: 32,
  },
  topHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  brand: {
    color: "#38bdf8",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 2,
    marginBottom: 4,
  },
  headerTitle: {
    color: "#ffffff",
    fontSize: 19,
    fontWeight: "800",
  },
  bellBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#111b30",
    borderWidth: 1,
    borderColor: "#2b4270",
    alignItems: "center",
    justifyContent: "center",
  },
  bellText: {
    color: "#38bdf8",
    fontSize: 12,
    fontWeight: "800",
  },
  heroCard: {
    backgroundColor: "#0c1324",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#1e325c",
    paddingVertical: 18,
    paddingHorizontal: 14,
    marginBottom: 14,
  },
  hudGrid: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  hudCol: {
    width: 78,
    alignItems: "center",
  },
  hudLabel: {
    color: "#64748b",
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 1.2,
    marginTop: 4,
  },
  hudValue: {
    color: "#e2e8f0",
    fontSize: 14,
    fontWeight: "800",
    marginBottom: 4,
  },
  coreRingOuter: {
    width: 118,
    height: 118,
    borderRadius: 59,
    borderWidth: 2,
    borderColor: "#ff2a55",
    backgroundColor: "#160d1c",
    alignItems: "center",
    justifyContent: "center",
  },
  coreRingInner: {
    width: 94,
    height: 94,
    borderRadius: 47,
    borderWidth: 1,
    borderColor: "#38bdf8",
    backgroundColor: "#090f1d",
    alignItems: "center",
    justifyContent: "center",
  },
  eyeRow: {
    flexDirection: "row",
    gap: 16,
    marginBottom: 8,
  },
  cyberEye: {
    width: 16,
    height: 7,
    borderRadius: 4,
    backgroundColor: "#ff2a55",
  },
  coreTag: {
    color: "#94a3b8",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  controlCard: {
    backgroundColor: "#0e1629",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#2b3f6b",
    padding: 16,
    alignItems: "center",
    marginBottom: 14,
  },
  statusPill: {
    paddingHorizontal: 16,
    paddingVertical: 4,
    borderRadius: 999,
    marginBottom: 10,
  },
  pillActive: {
    backgroundColor: "#16a34a",
  },
  pillStopped: {
    backgroundColor: "#475569",
  },
  statusPillText: {
    color: "#ffffff",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.2,
  },
  botName: {
    color: "#ffffff",
    fontSize: 22,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  botSub: {
    color: "#7dd3fc",
    fontSize: 11,
    fontWeight: "600",
    letterSpacing: 1,
    marginTop: 2,
    marginBottom: 14,
  },
  actionRow: {
    flexDirection: "row",
    gap: 8,
    width: "100%",
    marginBottom: 10,
  },
  chipBtn: {
    flex: 1,
    backgroundColor: "#16213b",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  chipBtnActive: {
    borderColor: "#38bdf8",
    backgroundColor: "#172b4d",
  },
  chipBtnDanger: {
    flex: 1,
    backgroundColor: "#2a121d",
    borderWidth: 1,
    borderColor: "#7f1d1d",
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  chipText: {
    color: "#f1f5f9",
    fontSize: 11,
    fontWeight: "800",
  },
  runButton: {
    width: "100%",
    backgroundColor: "#2563eb",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    marginBottom: 12,
  },
  runButtonActive: {
    backgroundColor: "#0284c7",
  },
  runButtonText: {
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1,
  },
  consoleBox: {
    width: "100%",
    backgroundColor: "#050811",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#1e293b",
    padding: 10,
    marginBottom: 10,
  },
  consoleHighlight: {
    color: "#38bdf8",
    fontSize: 11,
    fontWeight: "700",
    marginBottom: 4,
  },
  consoleLine: {
    color: "#94a3b8",
    fontSize: 11,
    marginBottom: 2,
  },
  serverFooter: {
    color: "#38bdf8",
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 1,
  },
  sectionCard: {
    backgroundColor: "#0e1629",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#223254",
    padding: 14,
    marginBottom: 14,
  },
  sectionLabel: {
    color: "#64748b",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.5,
    marginBottom: 8,
  },
  symbolRow: {
    flexDirection: "row",
    gap: 8,
  },
  symbolBtn: {
    flex: 1,
    backgroundColor: "#16213b",
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#29395c",
  },
  symbolBtnSelected: {
    backgroundColor: "#4f46e5",
    borderColor: "#818cf8",
  },
  symbolText: {
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "700",
  },
  metricsRow: {
    flexDirection: "row",
    gap: 10,
    marginBottom: 14,
  },
  metricBox: {
    flex: 1,
    backgroundColor: "#0e1629",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#223254",
    padding: 14,
  },
  metricValue: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: "800",
  },
  levelsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  levelText: {
    color: "#e2e8f0",
    fontSize: 12,
    fontWeight: "700",
  },
  neonAddBtn: {
    backgroundColor: "#6d28d9",
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#c084fc",
  },
  neonAddBtnText: {
    color: "#ffffff",
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 0.8,
  },
  bottomNav: {
    flexDirection: "row",
    backgroundColor: "#090e1a",
    borderTopWidth: 1,
    borderTopColor: "#1e293b",
    paddingVertical: 11,
  },
  navBtn: {
    flex: 1,
    alignItems: "center",
  },
  navText: {
    color: "#64748b",
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1,
  },
  navTextActive: {
    color: "#38bdf8",
  },
  green: {
    color: "#22c55e",
  },
  red: {
    color: "#f43f5e",
  },
  cyan: {
    color: "#38bdf8",
  },
});
