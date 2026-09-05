import type { Metadata } from "next";
import { TradingLab } from "./trading-lab";

export const metadata: Metadata = {
  title: "VolForge — Options Market-Making Lab",
  description: "Step through a synthetic earnings market and explain every inventory, hedge, and P&L change.",
};

export default function Home() {
  return <TradingLab />;
}
