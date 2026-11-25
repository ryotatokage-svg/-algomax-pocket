import React, { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet
} from "react-native";

export default function Home() {
  const [running, setRunning] = useState(false);
  const [symbol, setSymbol] = useState("XAUUSD");

  const symbols = ["XAUUSD", "USDJPY", "NAS100", "US30"];

  return (
    <ScrollView style={s.bg}>
      <View style={s.container}>

        <Text style={s.logo}>✦ ALGOMAX</Text>
        <Text style={s.subtitle}>POCKET TRADER</Text>

        <View style={s.hero}>
          <Text style={s.purple}>AI TRADING CONTROL</Text>
          <Text style={s.title}>Trading Robot</Text>

          <View style={s.robot}>
            <Text style={s.robotTitle}>
              ◉ LIQUIDITY HUNTER
            </Text>
            <Text style={s.muted}>
              {running ? "RUNNING · DEMO" : "STOPPED · DEMO"}
            </Text>
          </View>

          <TouchableOpacity
            style={s.start}
            disabled={running}
            onPress={() => setRunning(true)}
          >
            <Text style={s.buttonText}>▶ START</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={s.stop}
            disabled={!running}
            onPress={() => setRunning(false)}
          >
            <Text style={s.buttonText}>■ STOP</Text>
          </TouchableOpacity>

          <Text style={s.warning}>
            DEMO MODE · 実口座注文は無効
          </Text>
        </View>

        <View style={s.card}>
          <Text style={s.label}>DEMO BALANCE</Text>
          <Text style={s.value}>¥100,000</Text>
          <Text style={s.muted}>仮想残高</Text>
        </View>

        <View style={s.card}>
          <Text style={s.label}>TODAY PROFIT</Text>
          <Text style={s.value}>¥0</Text>
          <Text style={s.muted}>本日の損益（デモ）</Text>
        </View>

        <View style={s.card}>
          <Text style={s.label}>TRADING SYMBOL</Text>

          <View style={s.symbols}>
            {symbols.map(item => (
              <TouchableOpacity
                key={item}
                style={[
                  s.symbol,
                  symbol === item && s.selected
                ]}
                onPress={() => setSymbol(item)}
              >
                <Text style={s.buttonText}>{item}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={s.card}>
          <Text style={s.label}>CONNECTION STATUS</Text>
          <Text style={s.warning}>NOT CONNECTED</Text>
          <Text style={s.muted}>
            MT5 SERVER · DISCONNECTED
          </Text>
        </View>

        <Text style={s.footer}>
          ALGOMAX POCKET TRADER v1.0
        </Text>

      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  bg: {
    flex: 1,
    backgroundColor: "#080b1d"
  },
  container: {
    padding: 20,
    paddingTop: 65
  },
  logo: {
    color: "white",
    fontSize: 28,
    fontWeight: "900",
    letterSpacing: 3
  },
  subtitle: {
    color: "#8993bd",
    letterSpacing: 4,
    fontSize: 10,
    marginBottom: 30
  },
  hero: {
    backgroundColor: "#171c43",
    borderRadius: 22,
    padding: 20,
    borderWidth: 1,
    borderColor: "#454c91"
  },
  purple: {
    color: "#aaaaff",
    fontSize: 11,
    letterSpacing: 3
  },
  title: {
    color: "white",
    fontSize: 29,
    fontWeight: "bold",
    marginVertical: 12
  },
  robot: {
    backgroundColor: "#090d21",
    padding: 18,
    borderRadius: 15,
    marginVertical: 15
  },
  robotTitle: {
    color: "white",
    fontWeight: "bold"
  },
  muted: {
    color: "#929cbd",
    fontSize: 11,
    marginTop: 8
  },
  start: {
    backgroundColor: "#6654ed",
    padding: 16,
    borderRadius: 12,
    marginTop: 10
  },
  stop: {
    backgroundColor: "#343954",
    padding: 16,
    borderRadius: 12,
    marginTop: 10
  },
  buttonText: {
    color: "white",
    textAlign: "center",
    fontWeight: "bold"
  },
  warning: {
    color: "#ffc77d",
    fontSize: 11,
    marginTop: 15
  },
  card: {
    backgroundColor: "#151a32",
    borderRadius: 17,
    padding: 20,
    marginTop: 15,
    borderWidth: 1,
    borderColor: "#30385d"
  },
  label: {
    color: "#929cbd",
    fontSize: 10,
    letterSpacing: 2
  },
  value: {
    color: "white",
    fontSize: 27,
    fontWeight: "bold",
    marginTop: 12
  },
  symbols: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 15,
    gap: 8
  },
  symbol: {
    backgroundColor: "#303858",
    padding: 12,
    borderRadius: 9
  },
  selected: {
    backgroundColor: "#6654ed"
  },
  footer: {
    color: "#657092",
    textAlign: "center",
    marginVertical: 30,
    fontSize: 10
  }
});