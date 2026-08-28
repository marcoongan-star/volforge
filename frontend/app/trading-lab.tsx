"use client";

import { useEffect, useMemo, useState } from "react";

type LabEvent = {
  kind: string;
  time: string;
  title: string;
  explanation: string;
  spot: number;
  option: number;
  delta: number;
  inventory: number;
  stock: number;
  optionPnl: number;
  hedgePnl: number;
  fees: number;
};

const events: LabEvent[] = [
  { kind: "SESSION", time: "09:29:58", title: "Synthetic earnings session opened", explanation: "The lab fixes the starting state so every run is replayable. No live market data is implied.", spot: 100, option: 4.25, delta: .52, inventory: 0, stock: 0, optionPnl: 0, hedgePnl: 0, fees: 0 },
  { kind: "QUOTE", time: "09:30:00", title: "Market maker publishes 4.15 / 4.35", explanation: "The 20¢ spread pays for uncertainty. Inventory is flat, so the quote is symmetric around theoretical value.", spot: 100, option: 4.25, delta: .52, inventory: 0, stock: 0, optionPnl: 0, hedgePnl: 0, fees: 0 },
  { kind: "FILL", time: "09:30:04", title: "Customer buys 5 calls at the ask", explanation: "Selling calls makes the market maker short 5 contracts and short delta. The fill earns spread but creates directional risk.", spot: 100.2, option: 4.35, delta: .52, inventory: -5, stock: 0, optionPnl: 50, hedgePnl: 0, fees: -2 },
  { kind: "HEDGE", time: "09:30:06", title: "Agent buys 260 shares", explanation: "−5 contracts × 0.52 delta × 100 shares gives −260 delta, so buying 260 shares approximately neutralizes the position.", spot: 100.2, option: 4.35, delta: .52, inventory: -5, stock: 260, optionPnl: 50, hedgePnl: 0, fees: -6 },
  { kind: "MOVE", time: "09:31:12", title: "Spot jumps after the synthetic release", explanation: "As spot rises, call delta increases. The old hedge is no longer exact—this is gamma risk in action.", spot: 101.5, option: 5.1, delta: .58, inventory: -5, stock: 260, optionPnl: -325, hedgePnl: 338, fees: -6 },
  { kind: "MARK", time: "09:31:13", title: "Portfolio is marked to market", explanation: "The short calls lose $375 from the post-fill mark; spread capture and the stock hedge offset most, but not all, of that loss.", spot: 101.5, option: 5.1, delta: .58, inventory: -5, stock: 260, optionPnl: -325, hedgePnl: 338, fees: -6 },
];

export function TradingLab() {
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [risk, setRisk] = useState<"balanced" | "tight" | "defensive">("balanced");
  const [agent, setAgent] = useState<"maker" | "directional">("maker");
  const [sync, setSync] = useState<"connected" | "offline" | "recovering">("connected");
  const current = events[cursor];
  const totalPnl = current.optionPnl + current.hedgePnl + current.fees;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setCursor((value) => {
        if (value >= events.length - 1) {
          setPlaying(false);
          return value;
        }
        return value + 1;
      });
    }, 1400);
    return () => window.clearInterval(timer);
  }, [playing]);

  const quote = useMemo(() => {
    const width = risk === "tight" ? .14 : risk === "defensive" ? .34 : .2;
    const skew = current.inventory < 0 ? -.05 : current.inventory > 0 ? .05 : 0;
    return { bid: current.option - width / 2 + skew, ask: current.option + width / 2 + skew };
  }, [current.inventory, current.option, risk]);
  const directional = useMemo(() => {
    const forecast = 5.0;
    const confidence = 0.9;
    const scenarioVolatility = 0.5;
    const cost = 0.02;
    const penalty = risk === "defensive" ? 1 : risk === "tight" ? 0.25 : 0.6;
    const rawEdge = forecast - current.option;
    const hurdle = cost + (1 - confidence) * scenarioVolatility * penalty;
    const edgeAfterHurdle = Math.abs(rawEdge * confidence) - hurdle;
    return {
      action: edgeAfterHurdle <= 0 ? "HOLD" : rawEdge > 0 ? "BUY" : "SELL",
      forecast,
      edgeAfterHurdle,
    };
  }, [current.option, risk]);

  function reset() { setPlaying(false); setCursor(0); }
  function step() { setPlaying(false); setCursor((value) => Math.min(events.length - 1, value + 1)); }
  function disconnect() { setPlaying(false); setSync("offline"); }
  function reconnect() {
    setSync("recovering");
    window.setTimeout(() => setSync("connected"), 650);
  }

  return (
    <main className="lab-shell">
      <header className="lab-nav">
        <a className="vf-brand" href="#top"><span>V</span><div><strong>VOLFORGE</strong><small>OPTIONS LEARNING LAB</small></div></a>
        <div className="scenario-label"><span /> SYNTHETIC SCENARIO · REPLAYABLE</div>
        <a className="about-link" href="#method">Method</a>
      </header>

      <section className="lab-hero" id="top">
        <div><p className="lab-kicker">Earnings market · Session VF-014</p><h1>Can you quote risk<br />before it <em>moves?</em></h1><p>Step through an options market-maker’s decisions. Watch a customer fill change inventory, delta, the hedge, and finally P&amp;L.</p></div>
        <div className="control-deck">
          <div><small>REPLAY CONTROL</small><strong>{playing ? "AUTOPLAYING" : cursor === events.length - 1 ? "SESSION COMPLETE" : "PAUSED AT EVENT " + (cursor + 1)}</strong></div>
          <div className="controls"><button onClick={reset}>↺ Reset</button><button className="step" onClick={step} disabled={cursor === events.length - 1}>Step →</button><button className={playing ? "playing" : ""} onClick={() => setPlaying((value) => !value)}>{playing ? "Ⅱ Pause" : "▶ Autoplay"}</button></div>
          <div className="progress-track"><span style={{ width: `${(cursor / (events.length - 1)) * 100}%` }} /></div>
        </div>
      </section>

      <section className="market-strip">
        <MarketStat label="UNDERLYING" value={`$${current.spot.toFixed(2)}`} change={`${(((current.spot / 100) - 1) * 100).toFixed(2)}%`} />
        <MarketStat label="CALL THEO" value={`$${current.option.toFixed(2)}`} change={`Δ ${current.delta.toFixed(2)}`} />
        <MarketStat label="YOUR QUOTE" value={`${quote.bid.toFixed(2)} / ${quote.ask.toFixed(2)}`} change={`${Math.round((quote.ask - quote.bid) * 100)}¢ wide`} />
        <MarketStat label="OPTION INVENTORY" value={`${current.inventory}`} change="contracts" negative={current.inventory < 0} />
        <MarketStat label="STOCK HEDGE" value={`${current.stock}`} change="shares" />
      </section>

      <section className="lab-grid">
        <article className="event-panel">
          <div className="section-head"><div><small>SERVER-OWNED EVENT LOG</small><h2>What happened</h2></div><span>{cursor + 1} / {events.length}</span></div>
          <div className={`event-sync ${sync}`}><span /><div><small>WEBSOCKET NOTIFY · HTTP RECOVER</small><strong>{sync === "connected" ? `Confirmed through sequence ${cursor + 1}` : sync === "recovering" ? `Fetching events after ${cursor + 1}` : `Offline after sequence ${cursor + 1}`}</strong><p>{sync === "offline" ? "Local state is frozen until canonical events are recovered." : "The socket announces new work; the event endpoint restores canonical state."}</p></div>{sync === "connected" ? <button onClick={disconnect}>Simulate disconnect</button> : <button onClick={reconnect} disabled={sync === "recovering"}>{sync === "recovering" ? "Recovering…" : "Resume from cursor"}</button>}</div>
          <div className="event-list">
            {events.map((event, index) => <button key={event.time} onClick={() => { setPlaying(false); setCursor(index); }} className={`${index === cursor ? "current" : ""} ${index > cursor ? "future" : ""}`}><span className="event-time">{event.time}</span><span className="event-kind">{event.kind}</span><strong>{event.title}</strong><i /></button>)}
          </div>
        </article>

        <article className="explain-panel">
          <div className="section-head"><div><small>FIRST-PRINCIPLES EXPLANATION</small><h2>Why it matters</h2></div><span className="event-number">0{cursor + 1}</span></div>
          <p className="current-title">{current.title}</p><p className="current-explanation">{current.explanation}</p>
          <div className="agent-switch" role="group" aria-label="Trading agent objective"><button className={agent === "maker" ? "active" : ""} onClick={() => setAgent("maker")}>Market maker</button><button className={agent === "directional" ? "active" : ""} onClick={() => setAgent("directional")}>Directional</button></div>
          <div className="agent-decision">
            <small>{agent === "maker" ? "TWO-SIDED OBJECTIVE" : "ONE-SIDED OBJECTIVE"}</small>
            <strong>{agent === "maker" ? `QUOTE ${quote.bid.toFixed(2)} / ${quote.ask.toFixed(2)}` : `${directional.action} · FORECAST $${directional.forecast.toFixed(2)}`}</strong>
            <p>{agent === "maker" ? "Earn spread while moving inventory back toward zero; no directional forecast is required." : directional.action === "HOLD" ? "The confidence-weighted forecast edge does not clear costs and uncertainty, so the agent stays flat." : `The confidence-weighted edge clears the risk hurdle by $${directional.edgeAfterHurdle.toFixed(2)} per option unit.`}</p>
          </div>
          <div className="delta-equation"><small>CURRENT NET DELTA</small><div><span>{current.inventory} contracts</span><b>×</b><span>{current.delta.toFixed(2)} Δ</span><b>×</b><span>100</span><b>+</b><span>{current.stock} shares</span><b>=</b><strong>{Math.round(current.inventory * current.delta * 100 + current.stock)}</strong></div></div>
          <fieldset><legend>QUOTE RISK PRESET</legend>{(["tight", "balanced", "defensive"] as const).map((item) => <button key={item} className={risk === item ? "active" : ""} onClick={() => setRisk(item)}>{item}</button>)}</fieldset>
        </article>

        <article className="pnl-panel">
          <div className="section-head"><div><small>MARK-TO-MARKET ATTRIBUTION</small><h2>P&amp;L bridge</h2></div><strong className={totalPnl < 0 ? "loss" : "gain"}>{totalPnl >= 0 ? "+" : ""}${totalPnl}</strong></div>
          <PnlBar label="Option + spread" value={current.optionPnl} max={400} />
          <PnlBar label="Stock hedge" value={current.hedgePnl} max={400} />
          <PnlBar label="Fees" value={current.fees} max={400} />
          <div className="pnl-total"><span>Total marked P&amp;L</span><strong>{totalPnl >= 0 ? "+" : ""}${totalPnl}</strong></div>
          <p>Attribution separates trading edge from hedge results. A good outcome in one replay is not evidence of a profitable strategy.</p>
        </article>
      </section>

      <section className="distribution-section">
        <div className="distribution-head"><div><small>500 PAIRED SYNTHETIC PATHS · BASE SEED 14000</small><h2>One replay is not evidence.</h2></div><p>Both agents face the same generated terminal markets. Compare average P&amp;L with the left tail before judging the result.</p></div>
        <div className="distribution-table">
          <div className="distribution-row distribution-labels"><span>AGENT</span><span>MEAN</span><span>PROFIT PATHS</span><span>5TH PERCENTILE</span><span>EXPECTED SHORTFALL · 5%</span></div>
          <div className="distribution-row"><strong>Market maker<small>Delta-hedged · alternating customer side</small></strong><b>+$7.43</b><span>49.60%</span><span className="loss">−$459.46</span><span className="loss">−$640.30</span></div>
          <div className="distribution-row"><strong>Directional<small>Buy 5 · 85% confidence input</small></strong><b>+$30.30</b><span>33.00%</span><span className="loss">−$2,090.54</span><span className="loss">−$2,090.54</span></div>
        </div>
        <div className="paired-note"><strong>PAIRED INFERENCE</strong><span>Mean difference: +$22.88</span><span>95% interval: −$263.08 to +$308.83</span><span>Standard error: $145.90</span><span>Paired effect: 0.0070</span><span>Directional outperformed on 32.60% of paths</span><i>Synthetic comparison, not expected live performance · interval crosses zero</i></div>
        <div className="sensitivity-block">
          <header><div><small>ASSUMPTION STRESS TEST · 500 PAIRED PATHS PER LEVEL</small><h3>Does the answer survive volatility?</h3></div><span>Conclusion changes</span></header>
          <div className="sensitivity-row sensitivity-labels"><span>EARNINGS JUMP VOL</span><span>MEAN DIFFERENCE</span><span>95% INTERVAL</span><span>MAKER ES · 5%</span><span>DIRECTIONAL ES · 5%</span><span>CONCLUSION</span></div>
          <div className="sensitivity-row"><strong>4%</strong><b>−$551.82</b><span>−$758.16 to −$345.47</span><span>−$442.77</span><span>−$2,090.54</span><i className="maker-result">Maker advantage</i></div>
          <div className="sensitivity-row"><strong>8%</strong><b>+$22.88</b><span>−$263.08 to +$308.83</span><span>−$640.30</span><span>−$2,090.54</span><i>Inconclusive</i></div>
          <div className="sensitivity-row"><strong>12%</strong><b>+$800.65</b><span>+$407.90 to +$1,193.40</span><span>−$962.57</span><span>−$2,090.54</span><i className="directional-result">Directional advantage</i></div>
          <p>These measured synthetic results reverse across tested assumptions. That instability is the finding: one calibrated scenario is not enough to support a general agent claim.</p>
        </div>
      </section>

      <section className="method" id="method"><span>THE MODEL</span><h2>Quote. Predict. Hedge. Explain.</h2><p>The market maker earns spread while controlling inventory. The directional agent trades only when a confidence-weighted forecast clears costs and an uncertainty hurdle. The browser explains both; the API owns the tested calculations, accepted orders, fills, hedges, and append-only history.</p><div><b>01</b> Synthetic inputs only <b>02</b> Decimal accounting <b>03</b> Competing agent objectives <b>04</b> WebSocket + cursor recovery <b>05</b> No profit claims</div></section>
      <footer><strong>VOLFORGE</strong><span>Educational simulation · not investment advice · no live market data</span></footer>
    </main>
  );
}

function MarketStat({ label, value, change, negative = false }: { label: string; value: string; change: string; negative?: boolean }) { return <div className="market-stat"><small>{label}</small><strong className={negative ? "loss" : ""}>{value}</strong><span>{change}</span></div>; }
function PnlBar({ label, value, max }: { label: string; value: number; max: number }) { const width = Math.min(100, Math.abs(value) / max * 100); return <div className="pnl-row"><div><span>{label}</span><strong className={value < 0 ? "loss" : "gain"}>{value >= 0 ? "+" : ""}${value}</strong></div><div className="pnl-track"><i className={value < 0 ? "negative" : "positive"} style={{ width: `${width}%` }} /></div></div>; }
