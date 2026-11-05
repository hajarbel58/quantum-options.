"""Application Flask de démonstration - QUANTUM OPTIONS."""
import ast
import math
import operator
import os
from flask import Flask, request, render_template
import yfinance as yf
import numpy as np
from scipy.stats import norm
import plotly.graph_objs as go
import plotly.io as pio
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

def bs_price(S, K, T, r, sigma, option_type='call'):
    if T <= 0:
        return max(S-K,0) if option_type=='call' else max(K-S,0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T)/(sigma * np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    if option_type=='call':
        return S*norm.cdf(d1) - K*np.exp(-r*T)*norm.cdf(d2)
    else:
        return K*np.exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)

def numeric(name, default, low, high, integer=False):
    raw = request.form.get(name, "").strip() or str(default)
    value = float(raw)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} doit être compris entre {low} et {high}.")
    if integer:
        if not value.is_integer():
            raise ValueError(f"{name} doit être entier.")
        return int(value)
    return value


def monte_carlo_price(S, K, T, r, sigma, N=100000, option_type="call"):
    # Prix avec variable de contrôle, sans calcul des Greeks.
    rng = np.random.default_rng()
    terminal = S * np.exp((r - .5*sigma**2)*T + sigma*np.sqrt(T)*rng.normal(size=N))
    payoff = np.maximum(terminal-K, 0) if option_type == "call" else np.maximum(K-terminal, 0)
    variance = np.var(terminal)
    if variance > 0:
        beta = np.mean((payoff-payoff.mean())*(terminal-terminal.mean())) / variance
        payoff = payoff-beta*(terminal-S*np.exp(r*T))
    return float(np.exp(-r*T)*payoff.mean())


def american_option_longstaff_schwartz(S0, K, T, r, sigma, M=50, N=10000, option_type="call"):
    rng = np.random.default_rng()
    dt = T / M
    stock = np.empty((N, M+1))
    stock[:, 0] = S0
    for t in range(1, M+1):
        stock[:, t] = stock[:, t-1]*np.exp((r-.5*sigma**2)*dt+sigma*np.sqrt(dt)*rng.normal(size=N))
    intrinsic = lambda x: np.maximum(x-K, 0) if option_type == "call" else np.maximum(K-x, 0)
    cashflow = intrinsic(stock[:, -1])
    discount = np.exp(-r*dt)
    for t in range(M-1, 0, -1):
        cashflow *= discount
        exercise_value = intrinsic(stock[:, t])
        itm = exercise_value > 0
        if np.count_nonzero(itm) < 3:
            continue
        x = stock[itm, t] / K
        features = np.column_stack((x, x*x))
        reg = LinearRegression().fit(features, cashflow[itm])
        exercise = exercise_value[itm] > reg.predict(features)
        ids = np.flatnonzero(itm)[exercise]
        cashflow[ids] = exercise_value[ids]
    return float(max(intrinsic(np.array([S0]))[0], discount*cashflow.mean()))


@app.route("/pricing", methods=["GET", "POST"])
def pricing():
    price = spot = currency = model = None
    if request.method == "POST":
        try:
            model = request.form.get("model", "Black-Scholes")
            option_type = request.form.get("option_type", "call")
            style = request.form.get("option_style", "european")
            if model not in ("Black-Scholes", "Monte Carlo"):
                raise ValueError("Modèle indisponible.")
            if option_type not in ("call", "put") or style not in ("european", "american"):
                raise ValueError("Type ou style invalide.")
            if style == "american" and model != "Monte Carlo":
                raise ValueError("Choisissez Monte Carlo pour une option américaine.")
            K = numeric("strike", 100, .000001, 10000000)
            T = numeric("maturity", 365, 1, 3650) / 365
            r = numeric("rate", .05, -.2, 1)
            sigma = numeric("vol", .2, .0001, 5)
            steps = numeric("steps", 50, 2, 200, integer=True)
            manual = request.form.get("spot", "").strip()
            if manual:
                spot = numeric("spot", 100, .000001, 10000000)
                currency = request.form.get("currency", "USD").strip().upper()[:8] or "USD"
            else:
                ticker_input = request.form.get("ticker", "").strip().upper()
                if not ticker_input or len(ticker_input) > 30:
                    raise ValueError("Renseignez un ticker ou un prix du sous-jacent.")
                try:
                    ticker = yf.Ticker(ticker_input)
                    hist = ticker.history(period="5d", timeout=10)
                    if hist.empty:
                        raise ValueError("Aucune donnée disponible.")
                    spot = float(hist["Close"].iloc[-1])
                    currency = ticker.history_metadata.get("currency", "USD")
                except Exception:
                    raise ValueError("Données de marché indisponibles. Saisissez le prix du sous-jacent manuellement.")
            if model == "Black-Scholes":
                price = float(bs_price(spot, K, T, r, sigma, option_type))
            elif style == "american":
                price = american_option_longstaff_schwartz(spot, K, T, r, sigma, M=steps, option_type=option_type)
            else:
                price = monte_carlo_price(spot, K, T, r, sigma, option_type=option_type)
        except (ValueError, TypeError, OverflowError) as exc:
            price = f"Erreur : {exc}"
    return render_template("pricing.html", price=price, model=model, spot=spot,
                           currency=currency, greeks=None, tree_img=None)


def simulate_brownian(T=1., n=1000, sigma=1., mu=0., drift_type="standard", n_paths=5):
    rng = np.random.default_rng()
    t = np.linspace(0, T, n+1)
    W = np.zeros((n_paths, n+1))
    W[:, 1:] = np.cumsum(np.sqrt(T/n)*rng.normal(size=(n_paths, n)), axis=1)
    if drift_type == "geometric":
        paths = np.exp((mu-.5*sigma**2)*t+sigma*W)
    elif drift_type == "standard":
        paths = mu*t+sigma*W
    else:
        raise ValueError("Type de processus inconnu.")
    return t, paths


# Interprétation d'expressions mathématiques par liste autorisée, sans eval/sympify.
FUNCTIONS = {"sin": np.sin, "cos": np.cos, "tan": np.tan, "exp": np.exp,
             "log": np.log, "ln": np.log, "sqrt": np.sqrt, "abs": np.abs}
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow}

def expression(text, x=0.):
    if len(text) > 200:
        raise ValueError("Expression trop longue.")
    tree = ast.parse(text.replace("^", "**"), mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ValueError("Expression trop complexe.")
    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = float(node.value)
            if not math.isfinite(value) or abs(value) > 1e12:
                raise ValueError("Constante trop grande.")
            return value
        if isinstance(node, ast.Name) and node.id in ("x", "pi", "e"):
            return {"x": x, "pi": np.pi, "e": np.e}[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = visit(node.operand)
            return -val if isinstance(node.op, ast.USub) else val
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and (np.ndim(right) != 0 or abs(right) > 20):
                raise ValueError("Exposant trop grand ou non constant.")
            return OPS[type(node.op)](left, right)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in FUNCTIONS and len(node.args) == 1 and not node.keywords):
            return FUNCTIONS[node.func.id](visit(node.args[0]))
        raise ValueError("Expression non autorisée. Exemple : sin(x), exp(x), x**2.")
    with np.errstate(all="raise"):
        result = visit(tree)
    if not np.all(np.isfinite(result)):
        raise ValueError("Résultat non fini.")
    return result


def integration(fonction, a, b, taille_echantillon=10000):
    a, b = float(expression(str(a))), float(expression(str(b)))
    if not -1e6 <= a < b <= 1e6:
        raise ValueError("Bornes invalides : a doit être inférieur à b.")
    if not 100 <= taille_echantillon <= 200000:
        raise ValueError("Utilisez entre 100 et 200000 échantillons.")
    points = np.random.default_rng().uniform(a, b, taille_echantillon)
    return float((b-a)*np.mean(expression(fonction, points)))


@app.route("/quant-tools", methods=["GET", "POST"])
def quant_tools():
    brownian_result = integral_result = None
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "brownian":
                T = numeric("T", 1, .001, 20)
                n = numeric("n", 1000, 10, 3000, integer=True)
                sigma = numeric("sigma", 1, 0, 5)
                mu = numeric("mu", 0, -5, 5)
                n_paths = numeric("n_paths", 5, 1, 20, integer=True)
                drift_type = request.form.get("drift_type", "standard")
                t, paths = simulate_brownian(T, n, sigma, mu, drift_type, n_paths)
                fig = go.Figure()
                for i, path in enumerate(paths):
                    fig.add_trace(go.Scatter(x=t, y=path, mode="lines", name=f"Trajectoire {i+1}"))
                fig.update_layout(title="Simulation de trajectoires", xaxis_title="Temps", yaxis_title="Valeur",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                brownian_result = {"type": drift_type, "graph_html": pio.to_html(fig, full_html=False, include_plotlyjs="cdn")}
            elif action == "integral":
                samples = numeric("n_samples", 100000, 100, 200000, integer=True)
                integral_result = integration(request.form.get("fonction", "x**2"), request.form.get("a", "0"),
                                              request.form.get("b", "1"), samples)
        except (ValueError, TypeError, SyntaxError, ArithmeticError, RecursionError) as exc:
            if action == "brownian":
                brownian_result = {"error": str(exc)}
            else:
                integral_result = f"Erreur : {exc}"
    return render_template("try.html", brownian_result=brownian_result, integral_result=integral_result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
