from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
import random, sqlite3, time

Window.size = (360, 640)

KV = """
ScreenManager:
    MainScreen:
    PortfolioScreen:

<MainScreen>:
    name: 'main'
    BoxLayout:
        orientation: 'vertical'
        padding: 8
        spacing: 8
        BoxLayout:
            size_hint_y: None
            height: '48dp'
            Label:
                text: app.title
                bold: True
            Button:
                text: 'Portfolio'
                size_hint_x: None
                width: '100dp'
                on_release: root.manager.current = 'portfolio'
        BoxLayout:
            size_hint_y: None
            height: '40dp'
            Label:
                text: 'User:'
                size_hint_x: None
                width: '60dp'
            TextInput:
                id: username
                multiline: False
                hint_text: 'Enter username and Login'
            Button:
                text: 'Login'
                size_hint_x: None
                width: '80dp'
                on_release: app.login(username.text)
        BoxLayout:
            size_hint_y: None
            height: '40dp'
            Label:
                text: 'Balance:'
                size_hint_x: None
                width: '80dp'
            Label:
                id: balance
                text: '₹ 0'
        BoxLayout:
            size_hint_y: None
            height: '40dp'
            Label:
                text: 'Watchlist'
        ScrollView:
            GridLayout:
                id: watchlist
                cols: 1
                size_hint_y: None
                height: self.minimum_height
        BoxLayout:
            size_hint_y: None
            height: '48dp'
            Button:
                text: 'Save'
                on_release: app.save_state()
            Button:
                text: 'Exit'
                on_release: app.stop_app()

<PortfolioScreen>:
    name: 'portfolio'
    BoxLayout:
        orientation: 'vertical'
        padding: 8
        spacing: 8
        BoxLayout:
            size_hint_y: None
            height: '48dp'
            Button:
                text: 'Back'
                size_hint_x: None
                width: '80dp'
                on_release: root.manager.current = 'main'
            Label:
                text: 'Portfolio & Trades'
        ScrollView:
            GridLayout:
                id: portfolio_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
"""

WATCHLIST = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "SBIN.NS"]
DB = "simulator_kivy.db"
INITIAL_BALANCE = 1000000.0

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, balance REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, ts INTEGER, symbol TEXT, side TEXT, qty INTEGER, price REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS positions (username TEXT, symbol TEXT, qty INTEGER, avg_price REAL, PRIMARY KEY(username,symbol))')
    conn.commit()
    conn.close()

def create_user(username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users(username,balance) VALUES(?,?)', (username, INITIAL_BALANCE))
    conn.commit()
    conn.close()

def get_balance(username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE username=?', (username,))
    r = c.fetchone()
    conn.close()
    return float(r[0]) if r else None

def update_balance(username, newbal):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('UPDATE users SET balance=? WHERE username=?', (newbal, username))
    conn.commit()
    conn.close()

def record_trade(username, symbol, side, qty, price):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('INSERT INTO trades(username,ts,symbol,side,qty,price) VALUES(?,?,?,?,?,?)', (username, int(time.time()*1000), symbol, side, qty, price))
    conn.commit()
    conn.close()

def upsert_position(username, symbol, qty_delta, price):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT qty, avg_price FROM positions WHERE username=? AND symbol=?', (username, symbol))
    r = c.fetchone()
    if r is None:
        if qty_delta>0:
            c.execute('INSERT INTO positions(username,symbol,qty,avg_price) VALUES(?,?,?,?)', (username, symbol, qty_delta, price))
    else:
        qty, avg = r
        new_qty = qty + qty_delta
        if new_qty==0:
            c.execute('DELETE FROM positions WHERE username=? AND symbol=?', (username, symbol))
        elif qty_delta>0:
            new_avg = ((avg*qty) + (price*qty_delta))/new_qty
            c.execute('UPDATE positions SET qty=?, avg_price=? WHERE username=? AND symbol=?', (new_qty, new_avg, username, symbol))
        else:
            c.execute('UPDATE positions SET qty=? WHERE username=? AND symbol=?', (new_qty, username, symbol))
    conn.commit()
    conn.close()

def get_positions(username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT symbol,qty,avg_price FROM positions WHERE username=?', (username,))
    rows = c.fetchall()
    conn.close()
    return [{'symbol':r[0],'qty':r[1],'avg_price':r[2]} for r in rows]

def get_trades(username):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT ts,symbol,side,qty,price FROM trades WHERE username=? ORDER BY ts DESC LIMIT 200', (username,))
    rows = c.fetchall()
    conn.close()
    return [{'ts':r[0],'symbol':r[1],'side':r[2],'qty':r[3],'price':r[4]} for r in rows]

class MainScreen(Screen):
    pass

class PortfolioScreen(Screen):
    pass

class TradingApp(App):
    title = 'Virtual Stock Pro - Trade Simulator'
    def build(self):
        init_db()
        self.sm = Builder.load_string(KV)
        self.market = {s: random.uniform(100,1000) for s in WATCHLIST}
        # set some sensible defaults
        presets = {'RELIANCE.NS':2500.0,'TCS.NS':3200.0,'INFY.NS':1600.0,'HDFCBANK.NS':1500.0,'SBIN.NS':720.0}
        for k,v in presets.items():
            if k in self.market: self.market[k]=v
        self.username = None
        Clock.schedule_interval(self.tick, 1.0)
        return self.sm

    def tick(self, dt):
        # random walk
        for s in list(self.market.keys()):
            p = self.market[s]
            vol = max(0.2, abs(p)*0.0015)
            rnd = (random.random()-0.5)*vol*2.0
            self.market[s] = max(1.0, round(p + rnd, 2))
        self.update_watchlist()
        self.update_portfolio_view()

    def update_watchlist(self):
        wl = self.sm.get_screen('main').ids.watchlist
        wl.clear_widgets()
        for s in WATCHLIST:
            price = self.market.get(s, 0.0)
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.label import Label
            from kivy.uix.button import Button
            row = BoxLayout(size_hint_y=None, height='40dp', spacing=6)
            row.add_widget(Label(text=s, size_hint_x=0.4))
            row.add_widget(Label(text=f'₹ {price:,.2f}', size_hint_x=0.3))
            buy = Button(text='Buy', size_hint_x=0.15)
            sell = Button(text='Sell', size_hint_x=0.15)
            buy.bind(on_release=lambda _, sym=s: self.place_order(sym, 'buy'))
            sell.bind(on_release=lambda _, sym=s: self.place_order(sym, 'sell'))
            row.add_widget(buy); row.add_widget(sell)
            wl.add_widget(row)

    def login(self, name):
        if not name:
            return
        self.username = name.strip()
        create_user(self.username)
        bal = get_balance(self.username)
        self.sm.get_screen('main').ids.balance.text = f'₹ {bal:,.2f}'
        self.update_portfolio_view()

    def place_order(self, symbol, side):
        if not self.username:
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            p = Popup(title='Not logged in', content=Label(text='Please enter username and login'), size_hint=(0.6,0.4))
            p.open(); return
        qty = 1
        price = self.market.get(symbol, 0.0)
        bal = get_balance(self.username)
        cost = price * qty
        if side=='buy':
            if bal < cost:
                from kivy.uix.popup import Popup
                from kivy.uix.label import Label
                p = Popup(title='Insufficient funds', content=Label(text='Not enough balance to buy'), size_hint=(0.6,0.4))
                p.open(); return
            update_balance(self.username, bal - cost)
            record_trade(self.username, symbol, side, qty, price)
            upsert_position(self.username, symbol, qty, price)
        else:
            pos = None
            for p in get_positions(self.username):
                if p['symbol']==symbol:
                    pos = p; break
            if not pos or pos['qty'] < qty:
                from kivy.uix.popup import Popup
                from kivy.uix.label import Label
                pop = Popup(title='No Quantity', content=Label(text='Not enough quantity to sell'), size_hint=(0.6,0.4))
                pop.open(); return
            update_balance(self.username, bal + cost)
            record_trade(self.username, symbol, side, qty, price)
            upsert_position(self.username, symbol, -qty, price)
        # refresh
        self.sm.get_screen('main').ids.balance.text = f'₹ {get_balance(self.username):,.2f}'
        self.update_portfolio_view()

    def update_portfolio_view(self):
        pg = self.sm.get_screen('portfolio').ids.portfolio_grid
        pg.clear_widgets()
        if not self.username:
            return
        pos = get_positions(self.username)
        for p in pos:
            from kivy.uix.label import Label
            pg.add_widget(Label(text=f"{p['symbol']}  Qty:{p['qty']}  Avg:{p['avg_price']}  Value:₹ {self.market.get(p['symbol'], p['avg_price'])*p['qty']:,.2f}"))
        trades = get_trades(self.username)
        if trades:
            from kivy.uix.label import Label
            pg.add_widget(Label(text='--- Trades ---'))
            for t in trades[:20]:
                ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t['ts']/1000.0))
                pg.add_widget(Label(text=f"{ts} | {t['symbol']} | {t['side']} | {t['qty']} @ ₹{t['price']}"))

    def save_state(self):
        # state saved in sqlite automatically via DB ops
        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        p = Popup(title='Saved', content=Label(text='State persisted to local DB'), size_hint=(0.6,0.4))
        p.open()

    def stop_app(self):
        App.get_running_app().stop()

if __name__ == '__main__':
    TradingApp().run()
