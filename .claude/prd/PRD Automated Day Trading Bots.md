
**Each trading bot should have**
- The logic of the strategy
- Frequency and timing to execute
	- Fetch information
	- Execution
- Connected to Alpaca API for placing trades

**Other components**
- Database which stores trades by each agent, date and time when position was opened, entry price
- System which fetches latest price information when refreshed
- A way to define strategy
- APIs connection
	- yfinance
	- alpaca
	- quiver
- A consistent way to add on trading strategies and to have them integrate easily with the rest of the system (backend, frontend dashboard etc).

**Instantiate these trading agent**
- Transportation and Infra Committee (House) Agent: 
	- Refer to docs/CONGRESSIONAL_FILTER_README.md and congressional_filter.py for logic and how to work with quiver api
	- Names are in inputs/committee-transportation-infra.json
	- Let's change logic to whatever they buy, buy
- Josh Gottheimer Agent: 
	- logic to whatever this person buy, buy
	- Refer to docs/CONGRESSIONAL_FILTER_README.md and congressional_filter.py for logic and how to work with quiver api
- Sheldon Whitehouse Agent:
	- logic to whatever this person buy, buy
	- Refer to docs/CONGRESSIONAL_FILTER_README.md and congressional_filter.py for logic and how to work with quiver api
- Nancy Pelosi Agent: 
	- logic to whatever this person buy, buy
	- Refer to docs/CONGRESSIONAL_FILTER_README.md and congressional_filter.py for logic and how to work with quiver api
- Dan Meuser Agent: 
	- logic to whatever this person buy, buy
	- Refer to docs/CONGRESSIONAL_FILTER_README.md and congressional_filter.py for logic and how to work with quiver api
- For all of these, I think should fetch data from quiver api daily at 9.30pm  EST and place gtc orders. Learn how quiver api works using this reference script: /Users/admin/github/trading-automation/.claude/docs/live-congress-trading

**Visuals**
![[Screenshot 2025-09-09 at 3.16.34 PM.png]]
- **Overall level**
	- Dashboard. Each row is a trading bot which follows a specific trading strategy.
	- Columns (for this don't follow the picture attached): Strategy Name, Return (1d) - this is in %, Return (Since Open) - this is in %
	- Clicking on each row (e.g. Dan Meuser) will link to the second image which will list this strategy's holdings

![[Screenshot 2025-09-09 at 3.07.50 PM.png]]
**Trading bot level**
	- Dashboard. Each row is a holding
	- Columns: Ticker, Amount ($), % of NAV, Return (1d), Return (Since Open)
	- This is accomplished with Alpaca API - fetching of positions, and involves some computations such as 'Qty' * 'Market Value' for Amount etc, 'Today's P/L (%)' for Return (1d), 'Total P/L (%)' for Return (Since Open). % of NAV is simply each holdings's 'Amount' divided by the total 'Amount' of all holdings under a trading bot
