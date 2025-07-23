import numpy as np
import scipy.stats as stats  # scipy.stats provides functions for probability distributions

class BS:
    """
    BS stands for Black–Scholes.
    This class computes option prices and Greeks for European calls and puts.
    """

    def __init__(self, spot, strike, rate, days, volatility, multiplier=100):
        # spot: current price of the underlying asset (must be > 0)
        if spot <= 0:
            raise ValueError("Spot price must be positive")
        self.spot = spot

        # strike: exercise price of the option (must be > 0)
        if strike <= 0:
            raise ValueError("Strike price must be positive")
        self.strike = strike

        # rate: continuously compounded risk-free interest rate (as decimal, e.g. 0.05 for 5%)
        if rate < 0:
            raise ValueError("Interest rate cannot be negative")
        self.rate = rate

        # days: time to expiration in calendar days; convert to fraction of year
        if days <= 0:
            raise ValueError("Time to expiration must be positive")
        self.days = days / 365.0

        # volatility: annualised standard deviation of returns (must be >= 0)
        if volatility < 0:
            raise ValueError("Volatility cannot be negative")
        self.volatility = volatility

        # multiplier: contract size (e.g. 100 for equity options)
        if multiplier <= 0:
            raise ValueError("Multiplier must be positive")
        self.multiplier = multiplier

        # Pre-compute d1 and d2 for Black–Scholes formulas:
        # d1 = [ln(S/K) + (r + 0.5σ²) T] / (σ √T)
        numerator = np.log(self.spot / self.strike) + (self.rate + 0.5 * self.volatility ** 2) * self.days
        denominator = self.volatility * np.sqrt(self.days)
        self.d1 = numerator / denominator

        # d2 = d1 – σ √T
        self.d2 = self.d1 - denominator

        # N'(d1): standard normal probability density at d1 (used in Gamma, Vega)
        self.N_prime_d1 = np.exp(-0.5 * self.d1 ** 2) / np.sqrt(2 * np.pi)


    def call_price(self):
        """
        Returns the Black–Scholes price of a European call option.
        Formula: C = S N(d1) – K e^(–rT) N(d2)
        """
        # a = S * N(d1)
        a = self.spot * stats.norm.cdf(self.d1)
        # b = K * e^(–rT) * N(d2)
        b = np.exp(-self.rate * self.days) * self.strike * stats.norm.cdf(self.d2)
        # price per contract, rounded to 2 decimals, then scaled by multiplier
        return round(a - b, 2) * self.multiplier

    def put_price(self):
        """
        Returns the Black–Scholes price of a European put option.
        Formula: P = K e^(–rT) N(–d2) – S N(–d1)
        """
        a = self.strike * np.exp(-self.rate * self.days) * stats.norm.cdf(-self.d2)
        b = self.spot * stats.norm.cdf(-self.d1)
        return round(a - b, 2) * self.multiplier

    def call_delta(self):
        """
        Returns Delta of a call: ∂C/∂S = N(d1)
        """
        return round(stats.norm.cdf(self.d1), 2)

    def put_delta(self):
        """
        Returns Delta of a put: ∂P/∂S = N(d1) – 1
        """
        return round(stats.norm.cdf(self.d1) - 1, 2)

    def call_gamma(self):
        """
        Returns Gamma for calls (same for puts): ∂²C/∂S² = N'(d1) / (S σ √T)
        """
        gamma = self.N_prime_d1 / (self.spot * self.volatility * np.sqrt(self.days))
        return round(gamma, 4)

    def put_gamma(self):
        """
        Gamma of a put equals Gamma of a call.
        """
        return self.call_gamma()

    def call_vega(self):
        """
        Returns Vega: ∂C/∂σ = S √T N'(d1)
        (Here scaled by 1, not by multiplier or percent)
        """
        # √T * S * N'(d1)
        vega_unscaled = self.spot * np.sqrt(self.days) * self.N_prime_d1
        return round(vega_unscaled, 2)

    def put_vega(self):
        """
        Vega of a put equals Vega of a call.
        """
        return self.call_vega()

    def call_theta(self):
        """
        Returns Theta of a call (time decay) per day:
        Θ = –[S σ N'(d1)] / [2 √T] – r K e^(–rT) N(d2)
        """
        term1 = -(self.spot * self.volatility * self.N_prime_d1) / (2 * np.sqrt(self.days))
        term2 = -self.rate * self.strike * np.exp(-self.rate * self.days) * stats.norm.cdf(self.d2)
        theta = term1 + term2
        return round(theta, 2)

    def put_theta(self):
        """
        Returns Theta of a put per day:
        Θ = –[S σ N'(d1)] / [2 √T] + r K e^(–rT) N(–d2)
        """
        term1 = -(self.spot * self.volatility * self.N_prime_d1) / (2 * np.sqrt(self.days))
        term2 = self.rate * self.strike * np.exp(-self.rate * self.days) * stats.norm.cdf(-self.d2)
        theta = term1 + term2
        return round(theta, 2)

    def call_rho(self):
        """
        Returns Rho of a call: ∂C/∂r = T K e^(–rT) N(d2)
        """
        rho = self.days * self.strike * np.exp(-self.rate * self.days) * stats.norm.cdf(self.d2)
        return round(rho, 2)

    def put_rho(self):
        """
        Returns Rho of a put: ∂P/∂r = –T K e^(–rT) N(–d2)
        """
        rho = -self.days * self.strike * np.exp(-self.rate * self.days) * stats.norm.cdf(-self.d2)
        return round(rho, 2)