import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

sted_wl = 725
ex_wl = 532
NA = 1.2

def psf(wl,na,x0=0.0, xmin=-1000,xmax=1000,num=100):
    x = np.linspace(xmin,xmax,num)
    return x, np.exp(-2*na**2*(x-x0)**2/wl**2)

x, sted_psf = psf(sted_wl,NA)
sted_psf *= 1.5
_, ex_psf = psf(ex_wl,NA)
eff_psf = ex_psf/(1+sted_psf/ex_psf)

def gauss(x, *p):
    A, mu, sigma = p
    return A*np.exp(-(x-mu)**2/(2.*sigma**2))

# p0 is the initial guess for the fitting coefficients (A, mu and sigma above)
p0 = [1.0, 0., 200.0]

#coeff, var_matrix = curve_fit(gauss, x, ex_psf-eff_psf, p0=p0)
#print coeff
#plt.plot(x, gauss(x,*coeff),'.')
plt.plot(x,eff_psf)
plt.plot(x,ex_psf-eff_psf,color='k')
#plt.plot(x,sted_psf,color='r')
#plt.plot(x,ex_psf,color='g')
plt.show()