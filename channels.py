###############################################################################
##  Laboratorio de Engenharia de Computadores (LECOM)                        ##
##  Departamento de Ciencia da Computacao (DCC)                              ##
##  Universidade Federal de Minas Gerais (UFMG)                              ##
##                                                                           ##
##  Implementation of both acoustic and optical channels used in the         ##
##  simulator.                                                               ##
##                                                                           ##
##  TODO:                                                                    ##
##                                                                           ##
##  Author: Eduardo Pinto (epmcj@dcc.ufmg.br)                                ##
###############################################################################

from random import random
from math   import log10, sqrt, erfc, cos, pi, e

class Channel:
    def use(self):
        raise NotImplementedError

class AcousticChannel(Channel):
    # Implementation based on the acoustic channel model described in:
    # Stojanovic, Milica. "On the relationship between capacity and distance 
    # in an underwater acoustic communication channel." ACM SIGMOBILE Mobile 
    # Computing and Communications Review 11.4 (2007): 34-43.

    # Code based on PER from ns2.
    __kvalues = [1.0, 1.5, 2.0] 
    soundSpeed = 1500 # Sound speed in water, in m/s
    def __init__(self, k, s, w):
        assert (k in self.__kvalues), 'k = 1.0 or 1.5 or 2.0'
        assert (s >= 0 and s <= 1), '0 <= s <= 1'
        assert (w >= 0), 'wind speed must be positive'
        self.k = k
        self.s = s
        self.w = w
    
    def get_propagation_time(self, distance):
        return distance / self.soundSpeed

    def use(self, frequency, power, distance, packetSize):
        #
        per = self.perRF(distance, frequency, power, packetSize)
        return not (random() < per)

    def pathloss(self, distance, frequency):
        # Transmission loss that occurs in a underwater acoustic channel.
        # distance in meters
        # frequency in kHz
        # k, the spreading factor
        #
        return 10.0 * self.k * log10(distance) \
               + distance * self.thorp(frequency)
        

    def thorp(self, frequency):
        # Thorp's attenuation in dB/m (dB re uPa) 
        # frequency in kHz
        #
        f = frequency ** 2
        if f > 0.4:
            atten = 0.11 * f / (1 + f) + (
                    44 * (f / (4100 + frequency))) + (
                    2.75 * pow(10,(-4)) * f + 0.003)
        else:
            atten = 0.002 + 0.11 * (f / (1 + f)) + 0.011 * f
        return atten/1000

    def noise(self, frequency):
        # Noise in an underwater acoustic channel, in dB re uPa
        # "Priniciples of Underwater Sound" by Robert J. Urick
        # frequency in kHz
        #
        nTurbulence = 17 - 30 * log10(frequency)
        nTurbulence = 10 ** (nTurbulence * 0.1)
        nShipping = 40 + 20 * (self.s - 0.5) + (
                    26 * log10(frequency)) - ( 
                    60 * log10(frequency + 0.03))
        nShipping = 10 ** (nShipping * 0.1)
        nWind = 50 + 7.5 * sqrt(self.w) + 20 * log10(frequency) - ( 
                40 * log10(frequency + 0.4))
        nWind = 10 ** (nWind * 0.1)
        nThermal = 20 * log10(frequency) - 15
        nThermal = 10 ** (nThermal * 0.1)
        noise = 10 * log10(nTurbulence + nShipping + nWind + nThermal)
        return noise

    def snr_dB(self, distance, frequency, Pt, psize, noise_bw):
        # Packet error rate
        # distance in meters
        # frequency in kHz
        # Pt, the transmission power in dB re uPa
        # psize, the packet size in bytes
        # noise_bw, receiver bandwidth in dB re uPa
        #
        pl = self.pathloss(distance, frequency)
        nf = noise_bw * self.noise(frequency)
        snrdB = Pt - pl - nf
        return snrdB

    def snr(self, distance, frequency, Pt, psize, noise_bw):
        # Packet error rate
        # distance in meters
        # frequency in kHz
        # Pt, the transmission power in dB re uPa
        # psize, the packet size in bytes
        # noise_bw, receiver bandwidth in dB re uPa
        #
        snr = 10 ** (self.snr_dB(distance, frequency, Pt, size, noise_bw)/10)

    def per(self, distance, frequency, Pt, psize, noise_bw = 2.35):
        # Packet error rate
        # distance in meters
        # frequency in kHz
        # Pt, the transmission power in dB re uPa
        # psize, the packet size in bytes
        # noise_bw, receiver bandwidth in dB re uPa
        # (!) Does not use snr function for speed.
        #
        pl = self.pathloss(distance, frequency)
        nf = noise_bw * self.noise(frequency)
        snrdB = Pt - pl - nf
        snr = 10 ** (snrdB/10) 
        # using BPSK bit error rate w/ AWGN
        ber = 0.5 * erfc(sqrt(snr))
        return 1.0 - (1.0 - ber) ** (8 * psize)

    def perRF(self, distance, frequency, Pt, psize, noise_bw = 2.35):
        # Packet error rate
        # distance in meters
        # frequency in kHz
        # Pt, the transmission power in dB re uPa
        # psize, the packet size in bytes
        # noise_bw, receiver bandwidth in dB re uPa
        # (!) Does not use snr function for speed.
        #
        f = float(frequency)
        d = float(distance)
        # pl = self.pathloss(distance, frequency)
        pl = self.pathloss(d, f)
        # nf = noise_bw * self.noise(frequency)
        nf = noise_bw * self.noise(f)
        snrdB = Pt - pl - nf
        snr = 10 ** (snrdB/10)
        # using BPSK bit error rate w/ Rayleigh fading
        ber = 0.5 * (1 - sqrt(snr / (1 + snr)))
        return 1.0 - (1.0 - ber) ** (8 * psize)


class OpticalChannel(Channel):
    # Implementation based on the optical channel model described in: 
    # Anguita, Davide, et al. "Optical wireless underwater communication for 
    # AUV: Preliminary simulation and experimental results." OCEANS, 2011 
    # IEEE-Spain. IEEE, 2011.

    q     = 1.6e-19  # Electronic charge, in C
    K     = 1.38e-23 # Boltzmann constant, in J/K
    c     = None     # Beam light attenuation coefficient, in 1/m
    T     = None     # Temperature, in K
    S     = None     # Receiver sensitivity, in A/W
    R     = None     # Photodiode shunt resistance, in ohms
    Id    = None     # Photodiode dark current, in A 
    Il    = None     # Photodiode current generated by incident light, in A
    Ar    = None     # Receiver area, in m**2
    At    = None     # Transmitter size, in m**2
    bw    = None     # System bandwidth, in Hz
    theta = None     # Transmitter light beam diverge angle, in rad
    lightSpeed = 2.25e8 # Light speed in the water, in m/s 

    def __init__(self, c, T, S, R, Id, Il, Ar, At, bw, theta):
        self.c = c
        self.T = T
        self.S = S
        self.R = R
        self.Id = Id
        self.Il = Il
        self.Ar = Ar
        self.At = At
        self.bw = bw
        self.theta = theta

    def get_propagation_time(self, distance):
        return distance / self.lightSpeed
    
    def use(self, power, distance, d, beta, psize):
        per = self.perRF(power, distance, d, beta, psize)
        return not (random() < per)

    def snr_dB(self, P, distance, d, beta):
        return 10 * log10(self.snr(P, distance, d, beta))

    def snr(self, P, distance, d, beta):
        # Calculating the light power received
        p = 2 * P * self.Ar * cos(beta)
        p = p / (pi * (distance ** 2) * (1 - cos(self.theta)) + 2 * self.At)
        p = p * (e ** (-self.c * d)) 
        # Calculating SNR
        thermalNoise = (4 * self.K * self.T * self.bw) / self.R # squared
        currentNoise = 2 * self.q * (self.Id + self.Il) * self.bw # squared
        snr = ((self.S * p) ** 2) / (currentNoise + thermalNoise)
        return snr

    def per(self, P, distance, d, beta, psize):
        # Packet error rate
        # Pt, the transmission power  in dBm
        # distance in meters
        # d
        # beta, the inclination angle in rad
        # psize, the packet size in bytes
        # (!) Does not use snr function for speed.
        #
        # Calculating the light power received
        p = 2 * P * self.Ar * cos(beta)
        p = p / (pi * (distance ** 2) * (1 - cos(self.theta)) + 2 * self.At)
        p = p * (e ** (-self.c * d)) 
        # Calculating SNR
        thermalNoise = (4 * self.K * self.T * self.bw) / self.R # squared
        currentNoise = 2 * self.q * (self.Id + self.Il) * self.bw # squared
        snr = ((self.S * p) ** 2) / (currentNoise + thermalNoise)
        # using BPSK bit error rate w/ AWGN
        ber = 0.5 * erfc(sqrt(snr))
        per = 1.0 - (1.0 - ber) ** (8 * psize)
        return per

    def perRF(self, P, distance, d, beta, psize):
        # Packet error rate
        # Pt, the transmission power  in dBm
        # distance in meters
        # d
        # beta, the inclination angle in rad
        # psize, the packet size in bytes
        # (!) Does not use snr function for speed.
        #
        # Calculating the light power received
        p = 2 * P * self.Ar * cos(beta)
        p = p / (pi * (distance ** 2) * (1 - cos(self.theta)) + 2 * self.At)
        p = p * (e ** (-self.c * d)) 
        # Calculating SNR
        thermalNoise = (4 * self.K * self.T * self.bw) / self.R # squared
        currentNoise = 2 * self.q * (self.Id + self.Il) * self.bw # squared
        snr = ((self.S * p) ** 2) / (currentNoise + thermalNoise)
        # using BPSK bit error rate w/ Rayleigh fading
        ber = 0.5 * (1 - sqrt(snr / (1 + snr)))
        per = 1.0 - (1.0 - ber) ** (8 * psize)
        return per
