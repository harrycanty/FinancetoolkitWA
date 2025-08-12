import numpy as np
import scipy.stats as stats

class BS():
    def __init__(self, spot, strike, rate, days, volatility, multiplier=100):
        self.S = spot
        self.K = strike
        self.r = rate
        self.t = days / 365 # Time in years
        self.V = volatility
        self.M = multiplier

        # Avoid division errors
        if self.t <=0 or self.V <=0 or self.S <=0 or self.K <=0:
            raise ValueError("Time to expiry and/or volatility must be greater than 0")
        
        # d1 and d2 calculations
        self.d1 = (np.log(self.S/self.K)+(self.r+0.5*self.V**2)*(self.t)) / (self.V*np.sqrt(self.t))

        self.d2 = self.d1 - self.V*np.sqrt(self.t)

        # Extra variables (Optional)
        self.phi_d1 = np.exp(-0.5*self.d1**2) / (np.sqrt(2*np.pi))
        self.Nd1 = stats.norm.cdf(self.d1)
        self.Nd2 = stats.norm.cdf(self.d2)
        self.Nm_d1 = stats.norm.cdf(-self.d1)
        self.Nm_d2 = stats.norm.cdf(-self.d2)



    # ------------------ Prices (per contract, scaled by M ------------------
    def call_price(self):
        return self.M * (self.S * self.Nd1 - self.K * np.exp(-self.r * self.t) * self.Nd2)
    
    def put_price(self):
        return self.M * (self.K * np.exp(-self.r * self.t) * self.Nm_d2 - self.S * self.Nm_d1)
    
    # ------------------ Delta ------------------
    def call_delta(self):
         return (self.Nd1) * self.M
    
    def put_delta(self):
        return (self.Nd1 -1.0) * self.M
    
    # ------------------ Gamma (same for call and put) ------------------
    def gamma(self):
        return (self.phi_d1 / (self.S * self.V * np.sqrt(self.t)))*self.M
    
    # ------------------ Vega (per 1 vol point, scaled by M) ------------------
    def vega(self):
         return self.M * (self.S * self.phi_d1 * np.sqrt(self.t) / 100.0) # Per 1 vol point
    
    # ------------------ Theta (per year) For per day divide by 365 ------------------
    def call_theta(self):
        return (-(self.S*self.V*self.phi_d1)/(2*np.sqrt(self.t))-self.r * self.K *np.exp(-self.r * self.t)* self.Nd2)*self.M
    
    def put_theta(self):
        return (-(self.S*self.V*self.phi_d1)/(2*np.sqrt(self.t))+self.r * self.K *np.exp(-self.r * self.t)* self.Nm_d2)*self.M
    
    # ------------------ Rho (per 1% rate change) ------------------
    def call_rho(self):
        return (self.K *self.t * np.exp(-self.r*self.t)*self.Nd2 /100 ) * self.M # per 1% change
                                                                                    
    def put_rho(self):
        return (-self.K *self.t*np.exp(-self.r*self.t)*self.Nm_d2 /100) * self.M # per 1% change
    
    
    


    
