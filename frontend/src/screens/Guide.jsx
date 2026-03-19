import { Link } from 'react-router-dom'
import HelpTooltip from '../components/HelpTooltip'

export default function Guide() {
  return (
    <div className="max-w-3xl">
      <h2 className="text-2xl font-bold mb-2">Guide</h2>
      <p className="text-sm text-gray-500 mb-8">Everything you need to know about Forex Sentinel, in plain language.</p>

      {/* 1. How the System Works */}
      <GuideSection title="How the System Works" id="overview">
        <p>
          Forex Sentinel is an automated paper trading system that analyzes financial markets and places
          virtual trades on a demo account. No real money is at risk — it uses Capital.com's free demo
          account with €1,000 in virtual funds.
        </p>
        <p>
          The system runs <strong>three independent trading streams</strong>, each with its own pool
          of capital (default €100 each):
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
          <StreamCard
            color="#4c6ef5"
            title="News Stream"
            desc="An AI reads live news headlines and generates trading signals based on whether the news is bullish or bearish for each currency pair."
            link="/news"
          />
          <StreamCard
            color="#37b24d"
            title="Strategy Stream"
            desc="Five mechanical strategies based on academic research analyze price charts using technical indicators like momentum, Bollinger Bands, and RSI."
            link="/strategies"
          />
          <StreamCard
            color="#f59f00"
            title="Hybrid Stream"
            desc="Custom recipes you create that combine news analysis with mechanical strategies. For example: only trade when both AI and momentum agree."
            link="/hybrid"
          />
        </div>
        <p>
          Each stream generates <strong>signals</strong> (buy, sell, or neutral), checks them against
          <strong> risk management rules</strong>, and if approved, places <strong>paper trades</strong> on
          the demo account. Results are tracked on the <Link to="/dashboard" className="text-blue-400 hover:text-blue-300 underline">Dashboard</Link>.
        </p>
      </GuideSection>

      {/* 2. What Happens Automatically */}
      <GuideSection title="What Happens Automatically" id="automation">
        <p>Every hour, a scheduled job runs automatically. Here's what happens:</p>
        <ol className="list-decimal list-inside space-y-2 my-3 text-gray-300">
          <li><strong>Market check</strong> — Is the forex market open? (Sunday 22:00 UTC through Friday 22:00 UTC). If closed, the cycle is skipped.</li>
          <li><strong>Pause check</strong> — Is the scheduler paused in Settings? If so, the cycle is skipped.</li>
          <li><strong>News Stream runs</strong> — Fetches headlines from BBC, CNBC, GDELT, and the economic calendar. The AI analyzes them and generates signals.</li>
          <li><strong>Strategy Stream runs</strong> — Each enabled strategy analyzes recent price data (200 hourly candles) and generates signals.</li>
          <li><strong>Hybrid Streams run</strong> — Any active hybrid recipes combine signals from news and strategies.</li>
          <li><strong>Risk checks</strong> — Each signal is checked against position limits, daily loss limits, and correlation rules.</li>
          <li><strong>Trades are placed</strong> — Approved signals become paper trades with automatic stop loss and take profit levels.</li>
          <li><strong>Equity recorded</strong> — A snapshot of each stream's account value is saved for the equity curve.</li>
          <li><strong>Dashboard updated</strong> — All data is exported to the frontend.</li>
        </ol>
        <p>
          At <strong>22:00 UTC daily</strong> (after the New York session closes), a performance review
          is automatically generated with detailed analysis of the day's trading.
        </p>
        <p className="text-gray-500 text-sm mt-2">
          You can also trigger any of these steps manually from the relevant pages — you don't have to wait for the hourly cycle.
        </p>
      </GuideSection>

      {/* 3. Your First Steps */}
      <GuideSection title="Your First Steps" id="first-steps">
        <div className="space-y-4 my-3">
          <Step number={1} title="Review your risk settings">
            <p>
              Go to <Link to="/settings" className="text-blue-400 hover:text-blue-300 underline">Settings</Link> and
              check your risk parameters. The defaults are moderate (1% risk per trade, max 5 open positions).
              If you're new, click the <strong>"Conservative" preset</strong> to start with lower risk.
            </p>
            <p className="text-gray-500 text-sm">
              Key settings: <em>Max Risk Per Trade</em> controls how much you can lose on a single trade.
              <em> Max Daily Loss</em> is a safety net that stops trading if losses pile up.
            </p>
          </Step>

          <Step number={2} title="Explore the News Stream">
            <p>
              Go to <Link to="/news" className="text-blue-400 hover:text-blue-300 underline">News Stream</Link> and
              click <strong>"Fetch News & Generate Signals"</strong>. This pulls live headlines and shows you
              what the AI thinks — no trades are placed, just analysis.
            </p>
            <p className="text-gray-500 text-sm">
              You'll see confidence scores, reasoning, and key factors for each signal. The white marker on each
              confidence bar shows your minimum threshold — signals below it won't become trades.
            </p>
          </Step>

          <Step number={3} title="Run your first trading cycle">
            <p>
              Go to the <Link to="/dashboard" className="text-blue-400 hover:text-blue-300 underline">Dashboard</Link> and
              click <strong>"Run All Streams"</strong>. This runs news analysis, all 5 strategies, and any hybrids.
              Approved signals will become paper trades on the demo account.
            </p>
            <p className="text-gray-500 text-sm">
              This triggers a GitHub Actions workflow that takes about 2 minutes to complete.
              You'll see a status banner tracking progress.
            </p>
          </Step>

          <Step number={4} title="Read the results">
            <p>
              After the cycle completes, the <Link to="/dashboard" className="text-blue-400 hover:text-blue-300 underline">Dashboard</Link> will
              show equity curves, trade history, and stream comparison metrics. Click any trade row to see
              the full details of why it was taken.
            </p>
          </Step>

          <Step number={5} title="Experiment">
            <p>
              Try disabling strategies, adjusting the confidence threshold, tuning strategy parameters,
              or building a <Link to="/hybrid" className="text-blue-400 hover:text-blue-300 underline">custom hybrid</Link>.
              Each change affects the next trading cycle. Compare results over time to see what works.
            </p>
          </Step>
        </div>
      </GuideSection>

      {/* 4. Understanding the Streams */}
      <GuideSection title="Understanding the Streams" id="streams">
        <h4 className="font-semibold text-gray-200 mb-2 flex items-center">
          News Stream <HelpTooltip text="AI-powered analysis of live financial headlines" />
        </h4>
        <p>
          The AI reads headlines from four free sources (BBC Business, CNBC, GDELT, Economic Calendar),
          matches them to currency pairs using keyword lists, and decides if the news is bullish (buy),
          bearish (sell), or neutral. Each signal gets a confidence score from 0-100%.
        </p>
        <p className="text-gray-500 text-sm mb-4">
          The primary model is Groq's Llama 3.3 70B. Comparison models (Mistral, DeepSeek) are logged
          but don't generate trades — they help you evaluate model quality on the <Link to="/models" className="text-blue-400 hover:text-blue-300 underline">Models</Link> page.
        </p>

        <h4 className="font-semibold text-gray-200 mb-2 flex items-center">
          Strategy Stream <HelpTooltip text="Five mechanical trading strategies backed by academic research" />
        </h4>
        <p>Five independent strategies, each based on a published academic paper:</p>
        <ul className="list-disc list-inside space-y-1 my-2 text-gray-300 text-sm">
          <li><strong>Momentum</strong> — follows trends. If a currency has been rising, buy it. <HelpTooltip term="momentum" /></li>
          <li><strong>Carry</strong> — profits from interest rate differences between currencies. <HelpTooltip term="carry" /></li>
          <li><strong>Breakout</strong> — trades when price breaks out of the overnight range at London/NY open. <HelpTooltip term="breakout" /></li>
          <li><strong>Mean Reversion</strong> — bets that extreme moves will bounce back to average. <HelpTooltip term="mean_reversion" /></li>
          <li><strong>Volatility Breakout</strong> — enters when calm markets suddenly become volatile. <HelpTooltip term="volatility_breakout" /></li>
        </ul>
        <p className="text-gray-500 text-sm mb-4">
          Each strategy can be enabled/disabled and its parameters tuned in <Link to="/settings" className="text-blue-400 hover:text-blue-300 underline">Settings</Link>.
        </p>

        <h4 className="font-semibold text-gray-200 mb-2 flex items-center">
          Hybrid Stream <HelpTooltip text="Custom combinations of news and strategies" />
        </h4>
        <p>
          Hybrids combine multiple signal sources into one recipe. You choose which modules to include
          (News AI, any of the 5 strategies), set weights for each, and pick a combiner mode that controls
          how disagreements are resolved.
        </p>
        <p className="text-gray-500 text-sm">
          Example: "News (weight 0.6, must participate) + Momentum (weight 0.4)" with "Weighted Score"
          combiner. This requires news to have an opinion, then blends it with momentum for the final decision.
        </p>
      </GuideSection>

      {/* 5. Key Concepts */}
      <GuideSection title="Key Concepts" id="concepts">
        <h4 className="font-semibold text-gray-200 mb-2 flex items-center">
          Risk Management <HelpTooltip term="max_risk_per_trade" />
        </h4>
        <p>
          Every trade has a <strong>stop loss</strong> (limits your loss) and a <strong>take profit</strong> (locks in gains).
          The <strong>R:R ratio</strong> controls the balance — at 1.5:1, your take profit is 1.5x further than your stop loss.
        </p>
        <p className="text-gray-500 text-sm mb-4">
          The system also enforces daily loss limits and position limits per stream, plus correlation checks
          to prevent overexposure to related currency pairs.
        </p>

        <h4 className="font-semibold text-gray-200 mb-2 flex items-center">
          Position Sizing <HelpTooltip term="position_size" />
        </h4>
        <p>
          The system automatically calculates how much to trade based on your risk percentage and the stop loss distance.
          At 1% risk with €100 capital and a 50-pip stop loss, it calculates the exact number of units
          so that if the stop loss is hit, you lose exactly €1 (1%).
        </p>

        <h4 className="font-semibold text-gray-200 mb-2 flex items-center">
          Confidence Threshold <HelpTooltip term="min_confidence" />
        </h4>
        <p>
          Signals below your minimum confidence threshold are ignored. A higher threshold means fewer trades
          but each one has stronger conviction. A lower threshold generates more trades but includes weaker signals.
        </p>

        <h4 className="font-semibold text-gray-200 mb-2 flex items-center">
          Market Sessions <HelpTooltip term="market_session" />
        </h4>
        <p>
          Forex trades 24 hours a day, Monday to Friday, across four overlapping sessions:
          Sydney (22:00-07:00 UTC), Tokyo (00:00-09:00 UTC), London (07:00-16:00 UTC),
          and New York (12:00-22:00 UTC). The London + New York overlap (12:00-16:00 UTC)
          has the highest trading volume.
        </p>
      </GuideSection>

      {/* 6. What Can Go Wrong */}
      <GuideSection title="What Can Go Wrong" id="troubleshooting">
        <div className="space-y-3">
          <TroubleshootItem
            status="MARKET CLOSED"
            color="text-yellow-300 bg-yellow-500/20"
            desc="The forex market is closed (weekends or Friday after 22:00 UTC). No analysis or trading happens. The system will resume when the market opens."
          />
          <TroubleshootItem
            status="PAUSED"
            color="text-yellow-300 bg-yellow-500/20"
            desc='You paused the scheduler in Settings. Manual runs from the UI still work. Un-pause in Settings when ready.'
          />
          <TroubleshootItem
            status="RISK REJECTED"
            color="text-amber-300 bg-amber-500/20"
            desc="A signal was generated but rejected by risk management. Common reasons: max open positions reached, daily loss limit hit, or too many correlated positions. Check the Dashboard risk overview."
          />
          <TroubleshootItem
            status="BELOW THRESHOLD"
            color="text-gray-300 bg-gray-500/20"
            desc="The AI generated a signal but its confidence was below your minimum threshold. Lower the threshold in Settings to accept weaker signals, or wait for stronger news."
          />
          <TroubleshootItem
            status="FAILED"
            color="text-red-300 bg-red-500/20"
            desc="A trade could not be executed due to a broker API error or network issue. These are automatically cleaned up. If persistent, check the Capital.com demo account status."
          />
        </div>
      </GuideSection>
    </div>
  )
}

function GuideSection({ title, id, children }) {
  return (
    <section id={id} className="mb-8">
      <h3 className="text-lg font-semibold text-gray-100 mb-3 pb-2 border-b border-gray-800">{title}</h3>
      <div className="text-sm text-gray-300 leading-relaxed space-y-2">
        {children}
      </div>
    </section>
  )
}

function StreamCard({ color, title, desc, link }) {
  return (
    <Link to={link} className="block bg-gray-800/50 rounded-lg border border-gray-700/50 p-4 hover:border-gray-600/50 transition-colors">
      <div className="w-3 h-3 rounded-full mb-2" style={{ backgroundColor: color }} />
      <h4 className="font-semibold text-sm mb-1">{title}</h4>
      <p className="text-xs text-gray-400">{desc}</p>
    </Link>
  )
}

function Step({ number, title, children }) {
  return (
    <div className="flex gap-4">
      <div className="w-8 h-8 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center text-sm font-bold shrink-0 mt-0.5">
        {number}
      </div>
      <div>
        <h4 className="font-semibold text-gray-200 mb-1">{title}</h4>
        <div className="text-sm text-gray-300 space-y-1">{children}</div>
      </div>
    </div>
  )
}

function TroubleshootItem({ status, color, desc }) {
  return (
    <div className="flex items-start gap-3">
      <span className={`text-[10px] font-medium px-2 py-0.5 rounded shrink-0 mt-0.5 ${color}`}>
        {status}
      </span>
      <p className="text-sm text-gray-400">{desc}</p>
    </div>
  )
}
